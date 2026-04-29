"""
Upload router — handles file uploads and starts async processing.
"""

import os
import uuid

from fastapi import APIRouter, HTTPException, UploadFile, File

from app.config import ALLOWED_EXTENSIONS, TD_CHECKPOINT, TROCR_CHECKPOINT, TSR_CHECKPOINT, UPLOAD_DIR
from app.models.loader import model_store
from app.schemas.responses import UploadResponse
from app.services.processing import submit_job

router = APIRouter(prefix="/api", tags=["upload"])


@router.post("/upload", response_model=UploadResponse)
async def upload_file(file: UploadFile = File(...)):
    """Upload an image or PDF for table extraction."""
    if not model_store.is_loaded:
        detail = (
            model_store.load_error
            or "Models are not loaded. Install deps (pip install timm), place weights under ckpts/td, ckpts/tsr, ckpts/ocr, and restart."
        )
        raise HTTPException(
            status_code=503,
            detail=(
                f"{detail} Checkpoint dirs: TD={TD_CHECKPOINT} TSR={TSR_CHECKPOINT} OCR={TROCR_CHECKPOINT}"
            ),
        )

    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{ext}'. Allowed: {ALLOWED_EXTENSIONS}",
        )

    # Save uploaded file
    file_id = str(uuid.uuid4())
    save_path = os.path.join(UPLOAD_DIR, f"{file_id}{ext}")
    content = await file.read()
    with open(save_path, "wb") as f:
        f.write(content)

    # Submit for async processing
    job_id = await submit_job(save_path, os.path.basename(file.filename or save_path))

    return UploadResponse(
        job_id=job_id,
        status="processing",
        message="File uploaded successfully. Processing started.",
    )
