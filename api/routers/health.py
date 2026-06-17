"""
Health router — GET /health
Checks liveness of DB, Ollama, Whisper, and ffmpeg.
"""
from __future__ import annotations

import shutil
import subprocess
from datetime import datetime, timezone

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from api.models import HealthDependencies, HealthResponse
from api.dependencies import get_ollama_client
from db.connection import get_db_connection

router = APIRouter(prefix="/health", tags=["System"])

APP_VERSION = "1.0.0"


@router.get("", response_model=HealthResponse)
async def get_health() -> HealthResponse:
    """Liveness + readiness probe for all gateway dependencies."""
    # DB
    try:
        conn = get_db_connection()
        conn.execute("SELECT 1")
        conn.close()
        db_status: str = "up"
    except Exception:
        db_status = "down"

    # Ollama
    try:
        ollama_up = get_ollama_client().is_available()
        ollama_status: str = "up" if ollama_up else "down"
    except Exception:
        ollama_status = "down"

    # Whisper — check if the module-level model was loaded (set during startup)
    try:
        import api.main as _main
        whisper_status: str = "loaded" if getattr(_main, "_whisper_loaded", False) else "not_loaded"
    except Exception:
        whisper_status = "not_loaded"

    # ffmpeg
    ffmpeg_status: str = "available" if shutil.which("ffmpeg") is not None else "unavailable"

    overall = "ok"
    if db_status == "down" or ollama_status == "down":
        overall = "degraded"

    return HealthResponse(
        status=overall,  # type: ignore[arg-type]
        app_version=APP_VERSION,
        timestamp=datetime.now(timezone.utc),
        dependencies=HealthDependencies(
            database=db_status,  # type: ignore[arg-type]
            ollama=ollama_status,  # type: ignore[arg-type]
            whisper=whisper_status,  # type: ignore[arg-type]
            ffmpeg=ffmpeg_status,  # type: ignore[arg-type]
        ),
    )
