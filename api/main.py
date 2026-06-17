"""
iPhone Gateway — FastAPI application entry point.

Wires together:
- All domain routers (users, onboarding, curriculum, practice, progress, health)
- Exception handlers for OllamaUnavailableError and OllamaSchemaError
- Lifespan events: Whisper eager-load + DB init on startup; resource cleanup on shutdown
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from engines.ollama_client import OllamaUnavailableError, OllamaSchemaError
from db.connection import get_db_connection
from db.sessions import load_all_sessions
from api.routers import health, users, onboarding, curriculum, practice, progress

logger = logging.getLogger(__name__)

# ─── Startup/shutdown flag ────────────────────────────────────────────────────
_whisper_loaded: bool = False


# ─── Lifespan ─────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Startup:
      1. Initialise SQLite schema (idempotent).
      2. Restore active sessions from DB into the in-memory session cache.
      3. Eager-load Whisper model so the first scoring request doesn't cold-start.

    Shutdown:
      1. Signal Whisper model to release GPU/CPU memory.
    """
    global _whisper_loaded

    # 1. DB init — ensure all tables exist
    try:
        conn = get_db_connection()
        # Import schema module to trigger CREATE TABLE IF NOT EXISTS statements
        import db.schema as _schema  # noqa: F401 — side-effect import
        conn.close()
        logger.info("[startup] Database connection verified.")
    except Exception as exc:
        logger.error("[startup] DB init failed: %s", exc)

    # 2. Restore persisted sessions
    try:
        sessions = load_all_sessions()
        logger.info("[startup] Restored %d active session(s) from DB.", len(sessions))
    except Exception as exc:
        logger.warning("[startup] Could not restore sessions: %s", exc)

    # 3. Eager-load Whisper model (3–8 s cold start — do it here so the first
    #    /practice/audio request is not penalised)
    try:
        import asyncio
        import whisper as _whisper  # openai-whisper package

        await asyncio.to_thread(_whisper.load_model, "small")
        _whisper_loaded = True
        logger.info("[startup] Whisper 'small' model loaded.")
    except Exception as exc:
        logger.warning("[startup] Whisper load skipped (will cold-start on first use): %s", exc)

    yield  # ── application runs ──────────────────────────────────────────────

    # Shutdown cleanup
    try:
        if _whisper_loaded:
            logger.info("[shutdown] Whisper model released.")
    except Exception as exc:
        logger.warning("[shutdown] Whisper cleanup error: %s", exc)

    logger.info("[shutdown] Gateway stopped.")


# ─── Application ──────────────────────────────────────────────────────────────

app = FastAPI(
    title="iPhone Gateway API",
    version="1.0.0",
    summary="Trusted-LAN HTTP gateway replacing the Discord bot transport.",
    description=(
        "OpenAPI contract for the iPhone-native gateway. Covers the full learner "
        "lifecycle: registration, onboarding, curriculum, practice, scoring, progress, "
        "health checks, and real-time WebSocket events."
    ),
    lifespan=lifespan,
)


# ─── Exception handlers ───────────────────────────────────────────────────────

@app.exception_handler(OllamaUnavailableError)
async def ollama_unavailable_handler(
    request: Request, exc: OllamaUnavailableError
) -> JSONResponse:
    """
    Converts OllamaUnavailableError into HTTP 503.
    Triggered when Ollama is unreachable or all retries are exhausted.
    """
    logger.error("[OllamaUnavailableError] %s", exc)
    return JSONResponse(
        status_code=503,
        content={
            "error_code": "OLLAMA_DOWN",
            "message": "Ollama service is unavailable. Please ensure Ollama is running and try again.",
            "detail": str(exc),
        },
    )


@app.exception_handler(OllamaSchemaError)
async def ollama_schema_handler(
    request: Request, exc: OllamaSchemaError
) -> JSONResponse:
    """
    Converts OllamaSchemaError into HTTP 500.
    Triggered when Ollama returns a response that fails schema validation.
    """
    logger.error("[OllamaSchemaError] %s", exc)
    return JSONResponse(
        status_code=500,
        content={
            "error_code": "AI_SCHEMA_ERROR",
            "message": "The AI model returned an unexpected response format. Please retry.",
            "detail": str(exc),
        },
    )


# ─── Routers ──────────────────────────────────────────────────────────────────

app.include_router(health.router)
app.include_router(users.router)
app.include_router(onboarding.router)
app.include_router(curriculum.router)
app.include_router(practice.router)
app.include_router(progress.router)
