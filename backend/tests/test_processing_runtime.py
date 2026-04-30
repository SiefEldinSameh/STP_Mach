import asyncio
import tempfile
import threading
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest import mock

from app.services import processing


def _fake_result(filename: str) -> dict:
    return {
        "filename": filename,
        "pages": [
            {
                "page": 0,
                "tables": [],
                "latency_ms": 1,
                "stage_timings_ms": {
                    "table_detection": 1,
                    "table_structure": 0,
                    "ocr": 0,
                    "total": 1,
                },
                "status": "success",
                "error": None,
            }
        ],
        "total_latency_ms": 1,
        "stage_timings_ms": {
            "table_detection": 1,
            "table_structure": 0,
            "ocr": 0,
            "total": 1,
        },
    }


class ProcessingRuntimeTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.original_output_dir = processing.OUTPUT_DIR
        self.original_executor = processing._executor
        processing.OUTPUT_DIR = self.tmpdir.name
        processing._jobs.clear()
        processing._job_futures.clear()

    def tearDown(self):
        processing._jobs.clear()
        processing._job_futures.clear()
        processing.OUTPUT_DIR = self.original_output_dir
        processing._executor = self.original_executor
        self.tmpdir.cleanup()

    async def _wait_for_terminal_state(self, job_id: str, timeout: float = 2.0) -> dict:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            job = processing.get_job(job_id)
            if job and job.get("status") in {"completed", "error"}:
                return job
            await asyncio.sleep(0.02)
        self.fail(f"Job {job_id} did not reach a terminal state within {timeout} seconds")

    async def test_submit_job_returns_before_background_work_finishes(self):
        def slow_pipeline(file_path: str, output_dir: str | None = None, display_filename: str | None = None, stage_callback=None):
            if stage_callback:
                stage_callback("table_detection")
            time.sleep(0.2)
            return _fake_result(display_filename or "sample.png")

        with mock.patch.object(processing, "run_pipeline", side_effect=slow_pipeline):
            started = time.perf_counter()
            job_id = await processing.submit_job("fake-file.png", "sample.png")
            elapsed = time.perf_counter() - started

            self.assertLess(elapsed, 0.1, "submit_job should not wait for inference completion")

            job = processing.get_job(job_id)
            self.assertIsNotNone(job)
            self.assertEqual(job["status"], "processing")

            final_job = await self._wait_for_terminal_state(job_id)
            self.assertEqual(final_job["status"], "completed")
            self.assertEqual(final_job["filename"], "sample.png")

    async def test_runtime_metrics_report_active_and_queued_jobs(self):
        gate = threading.Event()

        def blocked_pipeline(file_path: str, output_dir: str | None = None, display_filename: str | None = None, stage_callback=None):
            if stage_callback:
                stage_callback("ocr")
            gate.wait(timeout=1.0)
            return _fake_result(display_filename or "queued.png")

        processing._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="test-pool")

        try:
            with mock.patch.object(processing, "run_pipeline", side_effect=blocked_pipeline):
                first_job = await processing.submit_job("first.png", "first.png")
                second_job = await processing.submit_job("second.png", "second.png")

                deadline = time.monotonic() + 1.0
                runtime = processing.get_processing_runtime()
                while time.monotonic() < deadline and runtime["queued_jobs"] == 0:
                    await asyncio.sleep(0.02)
                    runtime = processing.get_processing_runtime()

                self.assertEqual(runtime["max_workers"], 1)
                self.assertGreaterEqual(runtime["active_jobs"], 1)
                self.assertGreaterEqual(runtime["queued_jobs"], 1)

                gate.set()
                await self._wait_for_terminal_state(first_job)
                await self._wait_for_terminal_state(second_job)
        finally:
            processing._executor.shutdown(wait=True, cancel_futures=False)
