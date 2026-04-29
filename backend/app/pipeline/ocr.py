"""
OCR — batched TrOCR text recognition for cell crops.
"""

import torch
from PIL import Image

from app.config import DEVICE, OCR_BATCH
from app.models.loader import model_store


def safe_crop(page, bbox, W, H):
    """Safely crop a region from a PIL image, clamping to bounds."""
    x1, y1, x2, y2 = [int(v) for v in bbox]
    x1, y1 = max(0, x1), max(0, y1)
    x2, y2 = min(W, x2), min(H, y2)
    if x2 <= x1 or y2 <= y1:
        return None
    return page.crop((x1, y1, x2, y2))


def _blank():
    """Create a blank white image for invalid crops."""
    return Image.new("RGB", (32, 32), (255, 255, 255))


@torch.no_grad()
def predict_text_batch(crops):
    """Run TrOCR on a batch of cell crop images.
    Returns list of recognized text strings (same length as crops).
    """
    if not crops:
        return []

    ocr_proc = model_store.ocr_proc
    ocr_model = model_store.ocr_model
    gen_cfg = model_store.gen_cfg

    results = [""] * len(crops)
    valid_idx = [i for i, c in enumerate(crops) if c.width >= 5 and c.height >= 5]
    if not valid_idx:
        return results

    valid_crops = [crops[i] for i in valid_idx]
    texts = []
    for i in range(0, len(valid_crops), OCR_BATCH):
        batch = valid_crops[i : i + OCR_BATCH]
        pv = ocr_proc(images=batch, return_tensors="pt").pixel_values.to(DEVICE)
        ids = ocr_model.generate(pv, generation_config=gen_cfg)
        texts += ocr_proc.batch_decode(ids, skip_special_tokens=True)

    for idx, text in zip(valid_idx, texts):
        results[idx] = text.strip()

    return results
