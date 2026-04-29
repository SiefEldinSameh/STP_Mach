"""
Upload router — handles file uploads and starts async processing.
"""

import os
import uuid

from fastapi import APIRouter, HTTPException, UploadFile, File

from app.config import ALLOWED_EXTENSIONS, UPLOAD_DIR
from app.schemas.responses import UploadResponse
from app.services.processing import submit_job

router = APIRouter(prefix="/api", tags=["upload"])


@router.post("/upload", response_model=UploadResponse)
async def upload_file(file: UploadFile = File(...)):
    """Upload an image or PDF for table extraction."""
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
