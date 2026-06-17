"""
Health router — GET /health

Probes every gateway dependency and reports aggregate status.

Checks performed:
  - Ollama  : HTTP GET http://localhost:11434/api/tags (timeout 3 s)
  - Database: get_db_connection() + SELECT 1
  - Whisper : inspects _whisper_loaded flag set in api.main lifespan
  - ffmpeg  : subprocess.run(["ffmpeg", "-version"], timeout 3 s)
"""
from __future__ import annotations

import asyncio
import logging
import subprocess
import time

import requests
from fastapi import APIRouter
from fastapi.responses import JSONResponse

from db.connection import get_db_connection

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/health", tags=["System"])


# ─── Individual probe helpers (all blocking → run in thread pool) ─────────────

def _probe_ollama() -> str:
    """GET /api/tags with 3 s timeout → 'up' | 'down'."""
    try:
        resp = requests.get("http://localhost:11434/api/tags", timeout=3)
        return "up" if resp.status_code == 200 else "down"
    except Exception as exc:
        logger.debug("Ollama probe failed: %s", exc)
        return "down"


def _probe_database() -> str:
    """Open a connection and execute SELECT 1 → 'up' | 'down'."""
    try:
        conn = get_db_connection()
        conn.execute("SELECT 1")
        conn.close()
        return "up"
    except Exception as exc:
        logger.debug("DB probe failed: %s", exc)
        return "down"


def _probe_whisper() -> str:
    """
    Read the ``_whisper_loaded`` boolean set during app lifespan.
    Late-import api.main to avoid circular import at module level.
    """
    try:
        import api.main as _main  # noqa: PLC0415 — intentional late import
        return "loaded" if getattr(_main, "_whisper_loaded", False) else "not_loaded"
    except Exception:
        return "not_loaded"


def _probe_ffmpeg() -> str:
    """Run ``ffmpeg -version`` with 3 s timeout → 'available' | 'unavailable'."""
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True,
            timeout=3,
        )
        return "available" if result.returncode == 0 else "unavailable"
    except Exception as exc:
        logger.debug("ffmpeg probe failed: %s", exc)
        return "unavailable"


# ─── Endpoint ─────────────────────────────────────────────────────────────────

@router.get("", summary="Dependency health check")
async def get_health() -> JSONResponse:
    """
    Liveness + readiness probe.

    Runs Ollama, database, and ffmpeg probes concurrently in a thread pool,
    then reads the in-memory Whisper flag (no I/O).  Returns:

    ```json
    {
      "status": "ok" | "degraded",
      "checks": {
        "ollama":   "up" | "down",
        "database": "up" | "down",
        "whisper":  "loaded" | "not_loaded",
        "ffmpeg":   "available" | "unavailable"
      },
      "uptime_seconds": 123.4
    }
    ```

    ``status`` is ``"degraded"`` when Ollama or the database is down.
    """
    loop = asyncio.get_event_loop()

    # Concurrent blocking I/O probes
    ollama_status, db_status, ffmpeg_status = await asyncio.gather(
        loop.run_in_executor(None, _probe_ollama),
        loop.run_in_executor(None, _probe_database),
        loop.run_in_executor(None, _probe_ffmpeg),
    )

    # Whisper is a dict-lookup — no I/O, fine on the event loop
    whisper_status = _probe_whisper()

    # Uptime: read _start_time recorded at application boot in api.main
    try:
        import api.main as _main  # noqa: PLC0415
        uptime: float = time.monotonic() - getattr(_main, "_start_time", time.monotonic())
    except Exception:
        uptime = 0.0

    # Aggregate: any critical service down → degraded
    overall = "degraded" if (ollama_status == "down" or db_status == "down") else "ok"

    return JSONResponse(
        status_code=200,
        content={
            "status": overall,
            "checks": {
                "ollama": ollama_status,
                "database": db_status,
                "whisper": whisper_status,
                "ffmpeg": ffmpeg_status,
            },
            "uptime_seconds": round(uptime, 1),
        },
    )
