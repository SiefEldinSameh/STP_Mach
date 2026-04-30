# Table Extraction Web App

Production-style table extraction app for MACHATHON 7.0.

## What it does

- Accepts image and PDF uploads
- Runs table detection, structure recognition, and OCR
- Returns structured JSON grouped as `job -> pages -> tables -> cells`
- Exports reconstructed table CSV files
- Saves cropped table images and offers them as a zip download
- Tracks request health, stage latency, and recent job history

## Manual model checkpoints

Model weights are a required manual prerequisite for both local runs and Docker runs.

Populate these folders before starting the backend:

- `backend/ckpts/td`
- `backend/ckpts/tsr`
- `backend/ckpts/ocr`

Each checkpoint directory already contains a `README.md` with the expected files.

## Local development

### Backend

1. Create and activate a Python environment.
2. Install dependencies:

```powershell
cd backend
pip install -r requirements.txt
```

3. Start the API:

```powershell
uvicorn app.main:app --reload
```

The backend runs on `http://localhost:8000`.

### Frontend

1. Install dependencies:

```powershell
cd frontend
npm install
```

2. Start the Vite app:

```powershell
npm run dev
```

The frontend runs on `http://localhost:5173`.

## Docker

Docker does not download checkpoints. It expects the host machine to already contain populated model folders under `backend/ckpts`.

Run:

```powershell
docker compose up --build
```

Services:

- Frontend: `http://localhost:4173`
- Backend API: `http://localhost:8000`

## Main API endpoints

- `POST /api/upload`
- `GET /api/results/{job_id}`
- `PATCH /api/results/{job_id}`
- `GET /api/results/{job_id}/csv?format=matrix|cells`
- `GET /api/results/{job_id}/xlsx?format=matrix|cells`
- `GET /api/results/{job_id}/crops`
- `GET /api/health`

## Non-blocking processing

- `POST /api/upload` returns quickly with a `job_id`; it does not wait for OCR/table extraction to finish.
- The heavy pipeline runs in a background `ThreadPoolExecutor`.
- Worker count is configurable with `STP_MACH_MAX_WORKERS`.
- On GPU, the default worker count is `1` to avoid unstable parallel inference; on CPU, the default is up to `4`.
- `GET /api/health` now shows `processing_max_workers`, `processing_active_jobs`, and `processing_queued_jobs`.

## How to test concurrency

1. Start the backend and frontend normally.
2. Open the Health page and keep it visible.
3. Upload two or more large files back-to-back.
4. Confirm the first upload returns a `job_id` immediately and the UI stays responsive while processing continues.
5. Confirm the Health page shows active workers and queued jobs instead of freezing the app.
6. Download results after completion and verify each detected table becomes its own Excel sheet.

For automated backend checks:

```powershell
cd backend
python -m unittest discover -s tests -v
```

## Notes

- Jobs and health history are stored in memory.
- Output crops are served from `backend/outputs`.
- If no tables are detected, the job still completes successfully, but CSV and crop downloads are disabled for that job.
