"""
Configuration for the table extraction pipeline.
All model paths, thresholds, and runtime settings.
"""

import os
import torch

# ── Base Paths ────────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CKPTS_DIR = os.path.join(BASE_DIR, "ckpts")

TD_CHECKPOINT = os.path.join(CKPTS_DIR, "td")
TSR_CHECKPOINT = os.path.join(CKPTS_DIR, "tsr")
TROCR_CHECKPOINT = os.path.join(CKPTS_DIR, "ocr")

UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
OUTPUT_DIR = os.path.join(BASE_DIR, "outputs")

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

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

# ── Image Extensions ─────────────────────────────────────────────────────────
IMG_EXTENSIONS = (".jpg", ".jpeg", ".png", ".tif", ".tiff")
PDF_EXTENSIONS = (".pdf",)
ALLOWED_EXTENSIONS = IMG_EXTENSIONS + PDF_EXTENSIONS
