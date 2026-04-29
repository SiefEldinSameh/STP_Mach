"""
Async job management - runs heavy inference in background threads.
"""

import asyncio
import csv
import io
import logging
import os
import threading
import uuid
import zipfile
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional

from app.config import OUTPUT_DIR
from app.pipeline.inference import run_pipeline
from app.services.health import health_tracker

logger = logging.getLogger(__name__)

_executor = ThreadPoolExecutor(max_workers=2)
_jobs: Dict[str, dict] = {}
_jobs_lock = threading.Lock()


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _set_job_fields(job_id: str, **fields):
    with _jobs_lock:
        job = _jobs.get(job_id)
        if job is not None:
            job.update(fields)


def _has_tables(result: Optional[dict]) -> bool:
    if not result:
        return False
    return any(page.get("tables") for page in result.get("pages", []))


def _run_inference_sync(job_id: str, file_path: str, original_filename: str):
    """Synchronous wrapper for the pipeline - runs in a worker thread."""
    try:
        _set_job_fields(job_id, progress_stage="loading")
        output_dir = _jobs[job_id]["output_dir"]
        result = run_pipeline(
            file_path,
            output_dir=output_dir,
            display_filename=original_filename,
            stage_callback=lambda stage: _set_job_fields(job_id, progress_stage=stage),
        )
        _set_job_fields(
            job_id,
            status="completed",
            result=result,
            filename=result["filename"],
            total_latency_ms=result["total_latency_ms"],
            finished_at=_utc_now(),
            progress_stage="completed",
            stage_timings_ms=result.get("stage_timings_ms", {}),
        )
        completed_job = _jobs[job_id]
        health_tracker.record_request(
            result["total_latency_ms"],
            True,
            stage_timings=result.get("stage_timings_ms", {}),
            job_summary={
                "job_id": job_id,
                "filename": result["filename"],
                "status": "completed",
                "total_latency_ms": result["total_latency_ms"],
                "started_at": completed_job["started_at"],
                "finished_at": completed_job["finished_at"],
                "progress_stage": completed_job["progress_stage"],
                "error": None,
            },
        )
    except Exception as exc:
        logger.exception("Job %s failed", job_id)
        _set_job_fields(
            job_id,
            status="error",
            error=str(exc),
            finished_at=_utc_now(),
            progress_stage="error",
        )
        failed_job = _jobs.get(job_id, {})
        health_tracker.record_request(
            0,
            False,
            stage_timings=failed_job.get("stage_timings_ms"),
            job_summary={
                "job_id": job_id,
                "filename": original_filename,
                "status": "error",
                "total_latency_ms": 0,
                "started_at": failed_job.get("started_at"),
                "finished_at": failed_job.get("finished_at"),
                "progress_stage": failed_job.get("progress_stage"),
                "error": str(exc),
            },
        )


async def submit_job(file_path: str, original_filename: str) -> str:
    """Submit a file for async processing. Returns job_id."""
    job_id = str(uuid.uuid4())
    output_dir = os.path.join(OUTPUT_DIR, job_id)
    os.makedirs(output_dir, exist_ok=True)

    with _jobs_lock:
        _jobs[job_id] = {
            "status": "processing",
            "file_path": file_path,
            "result": None,
            "error": None,
            "filename": original_filename,
            "total_latency_ms": None,
            "started_at": _utc_now(),
            "finished_at": None,
            "progress_stage": "queued",
            "output_dir": output_dir,
            "stage_timings_ms": {},
        }

    loop = asyncio.get_event_loop()
    loop.run_in_executor(_executor, _run_inference_sync, job_id, file_path, original_filename)
    return job_id


def get_job(job_id: str) -> Optional[dict]:
    """Get job status and results."""
    return _jobs.get(job_id)


def update_job_cell(job_id: str, page: int, table_id: int, row: int, col: int, text: str) -> bool:
    """Update a cell's text in the job results."""
    job = _jobs.get(job_id)
    if not job or job["status"] != "completed" or not job["result"]:
        return False

    for page_data in job["result"].get("pages", []):
        if page_data["page"] != page:
            continue
        for table in page_data["tables"]:
            if table["table_id"] != table_id:
                continue
            for cell in table["cells"]:
                if cell["row"] == row and cell["col"] == col:
                    cell["text"] = text
                    return True
    return False


def job_has_tables(job_id: str) -> bool:
    job = _jobs.get(job_id)
    if not job or job["status"] != "completed":
        return False
    return _has_tables(job.get("result"))


def _table_to_matrix(table: dict) -> list[list[str]]:
    cells = table.get("cells", [])
    if not cells:
        return []

    n_rows = max(cell["row"] + cell["rowspan"] for cell in cells)
    n_cols = max(cell["col"] + cell["colspan"] for cell in cells)
    matrix = [["" for _ in range(n_cols)] for _ in range(n_rows)]

    for cell in cells:
        row = cell["row"]
        col = cell["col"]
        matrix[row][col] = cell.get("text", "")
        for row_offset in range(cell["rowspan"]):
            for col_offset in range(cell["colspan"]):
                if row_offset == 0 and col_offset == 0:
                    continue
                matrix[row + row_offset][col + col_offset] = ""

    return matrix


def generate_csv_for_result(result: dict, csv_format: str = "matrix") -> Optional[str]:
    """Generate CSV content from structured results."""
    if not _has_tables(result):
        return None

    output = io.StringIO()
    writer = csv.writer(output)

    if csv_format == "cells":
        writer.writerow(["page", "table_id", "row", "col", "rowspan", "colspan", "text"])
        for page_data in result.get("pages", []):
            for table in page_data.get("tables", []):
                for cell in table.get("cells", []):
                    writer.writerow(
                        [
                            page_data["page"],
                            table["table_id"],
                            cell["row"],
                            cell["col"],
                            cell["rowspan"],
                            cell["colspan"],
                            cell["text"],
                        ]
                    )
        return output.getvalue()

    for page_data in result.get("pages", []):
        for table in page_data.get("tables", []):
            writer.writerow([f"Page {page_data['page'] + 1}", f"Table {table['table_id'] + 1}"])
            for row in _table_to_matrix(table):
                writer.writerow(row)
            writer.writerow([])

    return output.getvalue()


def generate_crops_zip(job_id: str) -> Optional[io.BytesIO]:
    job = _jobs.get(job_id)
    if not job or job["status"] != "completed":
        return None

    crops_dir = Path(job["output_dir"]) / "crops"
    crop_files = sorted(crops_dir.glob("*.png"))
    if not crop_files:
        return None

    archive = io.BytesIO()
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as zip_file:
        for crop_file in crop_files:
            zip_file.write(crop_file, arcname=crop_file.name)
    archive.seek(0)
    return archive
