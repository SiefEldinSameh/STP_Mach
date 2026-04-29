"""
Model loader - loads TD, TSR, and TrOCR models once at startup.
Ported from the inference notebook with key remapping for DETR weights.
"""

import gc
import json
import logging
from pathlib import Path
from typing import List, Optional

import torch
from safetensors.torch import load_file
from transformers import (
    AutoImageProcessor,
    GenerationConfig,
    TableTransformerConfig,
    TableTransformerForObjectDetection,
    TrOCRProcessor,
    VisionEncoderDecoderModel,
)

from app.config import (
    DEVICE,
    MAX_TEXT_LEN,
    TD_CHECKPOINT,
    TROCR_CHECKPOINT,
    TSR_CHECKPOINT,
)

logger = logging.getLogger(__name__)


def validate_checkpoint_paths() -> None:
    """Verify local checkpoints exist before loading (clear errors vs NoneType downstream)."""
    errs: List[str] = []

    def tt_require(name: str, root: Path) -> None:
        root = root.resolve()
        if not root.is_dir():
            errs.append(f"{name}: directory missing - {root}")
            return
        for fn in ("config.json", "model.safetensors"):
            if not (root / fn).is_file():
                errs.append(f"{name}: missing file '{fn}' - {root}")
        has_preprocessor = (
            (root / "preprocessor_config.json").is_file() or (root / "preprocessor.json").is_file()
        )
        if not has_preprocessor:
            errs.append(
                f"{name}: AutoImageProcessor needs preprocessor_config.json (or preprocessor.json) - {root}"
            )

    tt_require("TD", Path(TD_CHECKPOINT))
    tt_require("TSR", Path(TSR_CHECKPOINT))

    oc = Path(TROCR_CHECKPOINT).resolve()
    if not oc.is_dir():
        errs.append(f"OCR: directory missing - {oc}")
    else:
        if not (oc / "config.json").is_file():
            errs.append(f"OCR: missing config.json - {oc}")
        has_weights = bool(list(oc.glob("*.safetensors"))) or (
            oc / "pytorch_model.bin").is_file()
        if not has_weights:
            errs.append(
                f"OCR: no weights (expect *.safetensors or pytorch_model.bin) - {oc}"
            )

    if errs:
        raise FileNotFoundError("; ".join(errs))


def remap_detr_to_hf(raw: dict) -> dict:
    """Remap original DETR keys to HuggingFace TableTransformer keys."""
    hf = {}
    embed_dim = None

    for key, value in raw.items():
        if key.startswith("backbone.0.body."):
            new_key = "model.backbone.conv_encoder.model." + key[len("backbone.0.body.") :]
            hf[new_key] = value
            continue

        if key.startswith("input_proj."):
            hf["model.input_projection." + key[len("input_proj.") :]] = value
            continue

        if key == "query_embed.weight":
            hf["model.query_position_embeddings.weight"] = value
            continue

        if key.startswith("bbox_embed."):
            hf["bbox_predictor." + key[len("bbox_embed.") :]] = value
            continue

        if key.startswith("class_embed."):
            hf["class_labels_classifier." + key[len("class_embed.") :]] = value
            continue

        if key.startswith("transformer.encoder.norm."):
            hf["model.encoder.layernorm." + key[len("transformer.encoder.norm.") :]] = value
            continue

        if key.startswith("transformer.decoder.norm."):
            hf["model.decoder.layernorm." + key[len("transformer.decoder.norm.") :]] = value
            continue

        if key.startswith("transformer.encoder.layers."):
            rest = key[len("transformer.encoder.layers.") :]
            idx, _, tail = rest.partition(".")
            tail = (
                tail.replace("norm1.", "self_attn_layer_norm.")
                .replace("norm2.", "final_layer_norm.")
                .replace("linear1.", "fc1.")
                .replace("linear2.", "fc2.")
            )
            if tail in ("self_attn.in_proj_weight", "self_attn.in_proj_bias"):
                embed_dim = embed_dim or value.shape[0] // 3
                suffix = "weight" if tail.endswith("weight") else "bias"
                hf[f"model.encoder.layers.{idx}.self_attn.q_proj.{suffix}"] = value[:embed_dim]
                hf[f"model.encoder.layers.{idx}.self_attn.k_proj.{suffix}"] = value[embed_dim : 2 * embed_dim]
                hf[f"model.encoder.layers.{idx}.self_attn.v_proj.{suffix}"] = value[2 * embed_dim :]
                continue
            hf[f"model.encoder.layers.{idx}.{tail}"] = value
            continue

        if key.startswith("transformer.decoder.layers."):
            rest = key[len("transformer.decoder.layers.") :]
            idx, _, tail = rest.partition(".")
            tail = (
                tail.replace("norm1.", "self_attn_layer_norm.")
                .replace("norm2.", "encoder_attn_layer_norm.")
                .replace("norm3.", "final_layer_norm.")
                .replace("linear1.", "fc1.")
                .replace("linear2.", "fc2.")
            )
            if tail in ("self_attn.in_proj_weight", "self_attn.in_proj_bias"):
                embed_dim = embed_dim or value.shape[0] // 3
                suffix = "weight" if tail.endswith("weight") else "bias"
                hf[f"model.decoder.layers.{idx}.self_attn.q_proj.{suffix}"] = value[:embed_dim]
                hf[f"model.decoder.layers.{idx}.self_attn.k_proj.{suffix}"] = value[embed_dim : 2 * embed_dim]
                hf[f"model.decoder.layers.{idx}.self_attn.v_proj.{suffix}"] = value[2 * embed_dim :]
                continue
            if tail in ("multihead_attn.in_proj_weight", "multihead_attn.in_proj_bias"):
                embed_dim = embed_dim or value.shape[0] // 3
                suffix = "weight" if tail.endswith("weight") else "bias"
                hf[f"model.decoder.layers.{idx}.encoder_attn.q_proj.{suffix}"] = value[:embed_dim]
                hf[f"model.decoder.layers.{idx}.encoder_attn.k_proj.{suffix}"] = value[embed_dim : 2 * embed_dim]
                hf[f"model.decoder.layers.{idx}.encoder_attn.v_proj.{suffix}"] = value[2 * embed_dim :]
                continue
            tail = tail.replace("multihead_attn.", "encoder_attn.")
            hf[f"model.decoder.layers.{idx}.{tail}"] = value
            continue

        hf[key] = value

    return hf


def _patch_table_transformer_config_dict(config_data: dict) -> None:
    """In-place fixes for checkpoints whose config.json uses null where strict configs expect types."""
    if config_data.get("dilation") is None:
        config_data["dilation"] = False


def _load_table_transformer_model(
    checkpoint_dir: str,
    *,
    state_dict: dict,
    patch_config: bool = True,
) -> TableTransformerForObjectDetection:
    config_path = Path(checkpoint_dir) / "config.json"
    config_data = json.loads(config_path.read_text(encoding="utf-8"))

    if patch_config:
        # The local checkpoint works offline only when backbone kwargs are normalized.
        config_data["backbone_kwargs"] = {}
    _patch_table_transformer_config_dict(config_data)

    config = TableTransformerConfig(**config_data)
    model = TableTransformerForObjectDetection(config)
    missing, unexpected = model.load_state_dict(state_dict, strict=False)
    return model, missing, unexpected


class ModelStore:
    """Holds all three models. Call load() once at startup."""

    def __init__(self):
        self.td_model = None
        self.td_proc = None
        self.tsr_model = None
        self.tsr_proc = None
        self.ocr_model = None
        self.ocr_proc = None
        self.gen_cfg = None
        self.device = DEVICE
        self._loaded = False
        self.load_error: Optional[str] = None

    @property
    def is_loaded(self):
        return self._loaded

    def _reset_models(self) -> None:
        self.td_model = None
        self.td_proc = None
        self.tsr_model = None
        self.tsr_proc = None
        self.ocr_model = None
        self.ocr_proc = None
        self.gen_cfg = None
        self._loaded = False

    def load(self) -> bool:
        """Load TD, TSR, TrOCR. Returns True on success. On failure, sets load_error."""
        if self._loaded:
            return True

        self._reset_models()
        self.load_error = None

        td_r = Path(TD_CHECKPOINT).resolve()
        tsr_r = Path(TSR_CHECKPOINT).resolve()
        oc_r = Path(TROCR_CHECKPOINT).resolve()
        logger.info("Loading models on device: %s", self.device)
        logger.info("Checkpoint paths resolved: TD=%s TSR=%s OCR=%s", td_r, tsr_r, oc_r)

        try:
            validate_checkpoint_paths()
        except Exception as exc:
            self.load_error = f"{type(exc).__name__}: {exc}"
            logger.error("Checkpoint validation failed: %s", self.load_error)
            return False

        try:
            logger.info("Loading TD (Table Detection)...")
            self.td_proc = AutoImageProcessor.from_pretrained(TD_CHECKPOINT, local_files_only=True)
            raw_sd = load_file(str(Path(TD_CHECKPOINT) / "model.safetensors"))
            hf_sd = remap_detr_to_hf(raw_sd)
            self.td_model, missing, unexpected = _load_table_transformer_model(
                TD_CHECKPOINT,
                state_dict=hf_sd,
            )
            logger.info("TD: missing=%d, unexpected=%d", len(missing), len(unexpected))
            self.td_model = self.td_model.to(self.device).eval()
            logger.info("TD labels: %s", self.td_model.config.id2label)

            logger.info("Loading TSR (Table Structure Recognition)...")
            self.tsr_proc = AutoImageProcessor.from_pretrained(TSR_CHECKPOINT, local_files_only=True)
            self.tsr_proc.size = {"shortest_edge": 800, "longest_edge": 1000}
            tsr_sd = load_file(str(Path(TSR_CHECKPOINT) / "model.safetensors"))
            self.tsr_model, missing, unexpected = _load_table_transformer_model(
                TSR_CHECKPOINT,
                state_dict=tsr_sd,
            )
            logger.info("TSR: missing=%d, unexpected=%d", len(missing), len(unexpected))
            self.tsr_model.config.id2label = {
                0: "table",
                1: "table column",
                2: "table row",
                3: "table column header",
                4: "table projected row header",
                5: "table spanning cell",
                6: "no object",
            }
            self.tsr_model.config.label2id = {
                value: key for key, value in self.tsr_model.config.id2label.items()
            }
            self.tsr_model = self.tsr_model.to(self.device).eval()
            logger.info("TSR labels: %s", self.tsr_model.config.id2label)

            logger.info("Loading TrOCR (OCR)...")
            self.ocr_proc = TrOCRProcessor.from_pretrained(TROCR_CHECKPOINT, local_files_only=True)
            self.ocr_model = (
                VisionEncoderDecoderModel.from_pretrained(TROCR_CHECKPOINT, local_files_only=True)
                .to(self.device)
                .eval()
            )
            self.gen_cfg = GenerationConfig(
                max_new_tokens=MAX_TEXT_LEN,
                num_beams=1,
                no_repeat_ngram_size=3,
            )
            logger.info("TrOCR ready")

            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()

            self._loaded = True
            self.load_error = None
            logger.info("All models loaded and ready on %s", self.device)
            return True
        except Exception as exc:
            self.load_error = f"{type(exc).__name__}: {exc}"
            logger.exception("Model loading failed.")
            self._reset_models()
            return False


model_store = ModelStore()
