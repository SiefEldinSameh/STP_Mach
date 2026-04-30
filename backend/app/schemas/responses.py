"""Pydantic response schemas for the API."""

from typing import Dict, List, Optional

from pydantic import BaseModel


class StructureConfidence(BaseModel):
    overall: Optional[float] = None
    rows_avg: Optional[float] = None
    cols_avg: Optional[float] = None
    spans_avg: Optional[float] = None


class CellSchema(BaseModel):
    bbox: List[int]
    row: int
    col: int
    rowspan: int
    colspan: int
    text: str


class TableSchema(BaseModel):
    table_id: int
    bbox: List[int]
    crop_url: Optional[str] = None
    detection_confidence: Optional[float] = None
    structure_confidence: Optional[StructureConfidence] = None
    cells: List[CellSchema]


class PageResult(BaseModel):
    page: int
    tables: List[TableSchema]
    latency_ms: int
    stage_timings_ms: Optional[Dict[str, int]] = None
    status: str
    error: Optional[str] = None


class UploadResponse(BaseModel):
    job_id: str
    status: str
    message: str


class JobStatus(BaseModel):
    job_id: str
    status: str  # "processing", "completed", "error"
    filename: Optional[str] = None
    pages: Optional[List[PageResult]] = None
    total_latency_ms: Optional[int] = None
    progress_stage: Optional[str] = None
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    error: Optional[str] = None


class CellEdit(BaseModel):
    page: int
    table_id: int
    row: int
    col: int
    text: str


class EditRequest(BaseModel):
    edits: List[CellEdit]


class RecentJob(BaseModel):
    job_id: str
    filename: Optional[str] = None
    status: str
    total_latency_ms: float
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    progress_stage: Optional[str] = None
    error: Optional[str] = None


class StageHealthRow(BaseModel):
    sample_count: int
    avg_ms: float
    min_ms: float
    max_ms: float
    p95_ms: float


class HealthResponse(BaseModel):
    status: str
    models_loaded: bool
    model_load_error: Optional[str] = None
    device: str
    processing_max_workers: int
    processing_active_jobs: int
    processing_queued_jobs: int
    processing_tracked_jobs: int
    total_requests: int
    successful_requests: int
    failed_requests: int
    average_latency_ms: float
    success_rate: float
    stage_average_ms: Dict[str, float]
    stage_health_matrix: Dict[str, StageHealthRow]
    recent_jobs: List[RecentJob]
