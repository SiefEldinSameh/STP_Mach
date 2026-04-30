"""
Configuration for the table extraction pipeline.
All model paths, thresholds, and runtime settings.

Checkpoint root defaults to ``<backend>/ckpts``. Override with env ``STP_MACH_CKPTS``
(absolute path) if weights live elsewhere (e.g. Docker volume).
"""

import os
from pathlib import Path

import torch

# ── Base Paths (always resolved; independent of process cwd) ─────────────────
_BASE_DIR = Path(__file__).resolve().parent.parent
BASE_DIR = str(_BASE_DIR)

_CKPT_OVERRIDE = os.environ.get("STP_MACH_CKPTS", "").strip()
CKPTS_DIR = (
    str(Path(_CKPT_OVERRIDE).resolve())
    if _CKPT_OVERRIDE
    else str(_BASE_DIR / "ckpts")
)

TD_CHECKPOINT = os.path.join(CKPTS_DIR, "td")
TSR_CHECKPOINT = os.path.join(CKPTS_DIR, "tsr")
TROCR_CHECKPOINT = os.path.join(CKPTS_DIR, "ocr")

UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
OUTPUT_DIR = os.path.join(BASE_DIR, "outputs")

for _path in (TD_CHECKPOINT, TSR_CHECKPOINT, TROCR_CHECKPOINT, UPLOAD_DIR, OUTPUT_DIR):
    os.makedirs(_path, exist_ok=True)

# ── Detection Thresholds ─────────────────────────────────────────────────────
TD_CONF = 0.65       # table-detection confidence
TD_PAD = 10          # padding around detected tables
TSR_CONF = 0.3       # structure-recognition confidence
MAX_TEXT_LEN = 128   # max OCR tokens

# ── NMS Thresholds ───────────────────────────────────────────────────────────
Y_NMS_IOU = 0.1
X_NMS_IOU = 0.15

# ── Span Thresholds ──────────────────────────────────────────────────────────
SPAN_CONF_MIN = 0.50
SPAN_COVER = 0.80

# ── OCR Batch Size ───────────────────────────────────────────────────────────
OCR_BATCH = 32

# ── Device ───────────────────────────────────────────────────────────────────
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
PROCESSING_MAX_WORKERS = int(
    os.environ.get(
        "STP_MACH_MAX_WORKERS",
        "1" if DEVICE.type == "cuda" else str(min(4, os.cpu_count() or 2)),
    )
)

# ── Image Extensions ─────────────────────────────────────────────────────────
IMG_EXTENSIONS = (".jpg", ".jpeg", ".png", ".tif", ".tiff")
PDF_EXTENSIONS = (".pdf",)
ALLOWED_EXTENSIONS = IMG_EXTENSIONS + PDF_EXTENSIONS

# Optional URL shown in Excel export promo (Info sheet) and can be mirrored in the frontend.
SUBSCRIBE_URL = os.environ.get("STP_MACH_SUBSCRIBE_URL", "").strip()
