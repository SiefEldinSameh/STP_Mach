"""
Results router - get/edit job results and download exports.
"""

from typing import Literal

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import PlainTextResponse, StreamingResponse

from app.schemas.responses import EditRequest, JobStatus
from app.services.processing import (
    generate_crops_zip,
    generate_csv_for_result,
    get_job,
    job_has_tables,
    update_job_cell,
)

router = APIRouter(prefix="/api", tags=["results"])


@router.get("/results/{job_id}", response_model=JobStatus)
async def get_results(job_id: str):
    """Get the status and results of a processing job."""
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    response = JobStatus(
        job_id=job_id,
        status=job["status"],
        filename=job.get("filename"),
        total_latency_ms=job.get("total_latency_ms"),
        progress_stage=job.get("progress_stage"),
        started_at=job.get("started_at"),
        finished_at=job.get("finished_at"),
        error=job.get("error"),
    )

    if job["status"] == "completed" and job["result"]:
        response.pages = job["result"].get("pages", [])

    return response


@router.patch("/results/{job_id}")
async def edit_results(job_id: str, request: EditRequest):
    """Edit OCR text in completed results."""
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job["status"] != "completed":
        raise HTTPException(status_code=400, detail="Job not completed yet")

    updated = 0
    for edit in request.edits:
        if update_job_cell(job_id, edit.page, edit.table_id, edit.row, edit.col, edit.text):
            updated += 1

    return {"updated": updated, "total_edits": len(request.edits)}


@router.get("/results/{job_id}/csv")
async def download_csv(
    job_id: str,
    csv_format: Literal["matrix", "cells"] = Query("matrix", alias="format"),
):
    """Download the final CSV for a completed job."""
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job["status"] != "completed":
        raise HTTPException(status_code=400, detail="Job not completed yet")
    if not job_has_tables(job_id):
        raise HTTPException(status_code=400, detail="No tables detected for this job")

    csv_content = generate_csv_for_result(job["result"], csv_format=csv_format)
    if csv_content is None:
        raise HTTPException(status_code=500, detail="Failed to generate CSV")

    suffix = "cells" if csv_format == "cells" else "tables"
    filename = (job.get("filename") or "results").rsplit(".", 1)[0] + f"-{suffix}.csv"
    return PlainTextResponse(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/results/{job_id}/crops")
async def download_crops(job_id: str):
    """Download detected table crops as a zip archive."""
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job["status"] != "completed":
        raise HTTPException(status_code=400, detail="Job not completed yet")
    if not job_has_tables(job_id):
        raise HTTPException(status_code=400, detail="No tables detected for this job")

    archive = generate_crops_zip(job_id)
    if archive is None:
        raise HTTPException(status_code=500, detail="Failed to package table crops")

    filename = (job.get("filename") or "results").rsplit(".", 1)[0] + "-crops.zip"
    return StreamingResponse(
        archive,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
