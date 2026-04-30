"""
Health router — system health and metrics endpoint.
"""

from fastapi import APIRouter

from app.config import DEVICE
from app.models.loader import model_store
from app.schemas.responses import HealthResponse
from app.services.health import health_tracker
from app.services.processing import get_processing_runtime

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def get_health():
    """Get system health metrics."""
    runtime = get_processing_runtime()
    return HealthResponse(
        status="healthy",
        models_loaded=model_store.is_loaded,
        model_load_error=(model_store.load_error if not model_store.is_loaded else None),
        device=str(DEVICE),
        processing_max_workers=runtime["max_workers"],
        processing_active_jobs=runtime["active_jobs"],
        processing_queued_jobs=runtime["queued_jobs"],
        processing_tracked_jobs=runtime["tracked_jobs"],
        total_requests=health_tracker.total_requests,
        successful_requests=health_tracker.successful_requests,
        failed_requests=health_tracker.failed_requests,
        average_latency_ms=round(health_tracker.average_latency_ms, 2),
        success_rate=round(health_tracker.success_rate, 2),
        stage_average_ms=health_tracker.stage_average_ms,
        stage_health_matrix=health_tracker.stage_health_matrix,
        recent_jobs=health_tracker.recent_jobs,
    )
