"""Health & metrics tracking service."""

from collections import deque
import threading


def _avg(values):
    if not values:
        return 0.0
    return sum(values) / len(values)


class HealthTracker:
    """Thread-safe metrics tracker for system health monitoring."""

    def __init__(self):
        self._lock = threading.Lock()
        self._total_requests = 0
        self._successful = 0
        self._failed = 0
        self._latencies = deque(maxlen=1000)
        self._stage_timings = {
            "table_detection": deque(maxlen=1000),
            "table_structure": deque(maxlen=1000),
            "ocr": deque(maxlen=1000),
            "total": deque(maxlen=1000),
        }
        self._recent_jobs = deque(maxlen=20)

    def record_request(self, latency_ms: float, success: bool, stage_timings=None, job_summary=None):
        with self._lock:
            self._total_requests += 1
            if success:
                self._successful += 1
            else:
                self._failed += 1
            self._latencies.append(float(latency_ms or 0))
            for stage, bucket in self._stage_timings.items():
                if stage_timings and stage in stage_timings:
                    bucket.append(float(stage_timings[stage] or 0))
            if job_summary:
                self._recent_jobs.appendleft(dict(job_summary))

    @property
    def total_requests(self) -> int:
        return self._total_requests

    @property
    def successful_requests(self) -> int:
        return self._successful

    @property
    def failed_requests(self) -> int:
        return self._failed

    @property
    def average_latency_ms(self) -> float:
        with self._lock:
            return _avg(self._latencies)

    @property
    def success_rate(self) -> float:
        with self._lock:
            if self._total_requests == 0:
                return 100.0
            return (self._successful / self._total_requests) * 100

    @property
    def stage_average_ms(self) -> dict:
        with self._lock:
            return {
                stage: round(_avg(values), 2)
                for stage, values in self._stage_timings.items()
            }

    @property
    def recent_jobs(self) -> list[dict]:
        with self._lock:
            return list(self._recent_jobs)


# Global singleton
health_tracker = HealthTracker()
