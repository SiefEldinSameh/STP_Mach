"""
FastAPI application entry point.
Loads models at startup, registers routers, configures CORS.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import OUTPUT_DIR, UPLOAD_DIR
from app.models.loader import model_store
from app.routers import health, results, upload
from app.services.processing import shutdown_processing_executor

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load models on startup, cleanup on shutdown."""
    logger.info("Starting up — loading models…")
    if model_store.load():
        logger.info("Models loaded successfully.")
    else:
        logger.error(
            "Models did not load (inference disabled). Reason: %s",
            model_store.load_error or "(unknown)",
        )
    yield
    shutdown_processing_executor()
    logger.info("Shutting down.")


app = FastAPI(
    title="Table Extraction API",
    description="MACHATHON 7.0 — Extract tables from images and PDFs",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — allow the React dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(upload.router)
app.include_router(results.router)
app.include_router(health.router)
app.mount("/outputs", StaticFiles(directory=OUTPUT_DIR), name="outputs")


@app.get("/")
async def root():
    return {
        "app": "Table Extraction API",
        "version": "1.0.0",
        "docs": "/docs",
    }
