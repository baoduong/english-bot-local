"""
Practice router — /practice
Manages practice sessions, audio scoring, and teacher sample streaming.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import JSONResponse

from api.models import (
    PracticeSessionStartRequest,
    PracticeSessionActionRequest,
    PracticeSessionStateResponse,
    PracticeSkipResponse,
    PracticeStopResponse,
    PracticeAudioResponse,
)
from api.dependencies import get_phase_engine
from analysis.phase_engine import PhaseEngine

router = APIRouter(prefix="/practice", tags=["Practice"])


@router.post("/session/start", status_code=501)
async def start_practice_session(
    body: PracticeSessionStartRequest,
    phase_engine: PhaseEngine = Depends(get_phase_engine),
) -> JSONResponse:
    """
    POST /practice/session/start — Start or resume a curriculum_practice session.

    Placeholder: returns 501 until Task 6 wires session state + PhaseEngine.
    Real behaviour: look up / create session in active_sessions, return current
    practice item with sample audio URL.
    """
    return JSONResponse(
        status_code=501,
        content={"detail": "Not implemented"},
    )


@router.get("/session/state", status_code=501)
async def get_practice_session_state(user_id: str) -> JSONResponse:
    """
    GET /practice/session/state?user_id=<uuid> — Current session state snapshot.

    Placeholder: returns 501 until Task 6 implements session state reads.
    """
    return JSONResponse(
        status_code=501,
        content={"detail": "Not implemented"},
    )


@router.post("/session/skip", status_code=501)
async def skip_practice_item(body: PracticeSessionActionRequest) -> JSONResponse:
    """
    POST /practice/session/skip — Skip current sentence or word-drill item.

    Placeholder: returns 501 until Task 6 implements session advance logic.
    """
    return JSONResponse(
        status_code=501,
        content={"detail": "Not implemented"},
    )


@router.post("/session/stop", status_code=501)
async def stop_practice_session(body: PracticeSessionActionRequest) -> JSONResponse:
    """
    POST /practice/session/stop — Terminate current practice session.

    Placeholder: returns 501 until Task 6 implements session cleanup.
    Real behaviour: call db.sessions.delete_session(user_id), return summary stats.
    """
    return JSONResponse(
        status_code=501,
        content={"detail": "Not implemented"},
    )


@router.post("/audio", status_code=501)
async def score_practice_audio(
    user_id: str = Form(...),
    audio_file: UploadFile = File(...),
    content_id: str = Form(None),
    expected_text: str = Form(None),
) -> JSONResponse:
    """
    POST /practice/audio — Upload learner audio (.m4a) for Whisper/Azure scoring.

    Placeholder: returns 501 until Task 6 implements:
    - multipart audio receive
    - ffmpeg transcode to 16 kHz mono WAV
    - Whisper/Azure scoring via engines/whisper.py or engines/azure.py
    - structured WordScore list (no ANSI codes)
    - session state update + next action determination
    """
    return JSONResponse(
        status_code=501,
        content={"detail": "Not implemented"},
    )


@router.get("/audio/sample", status_code=501)
async def get_practice_sample_audio(
    user_id: str,
    content_id: str | None = None,
    word: str | None = None,
) -> JSONResponse:
    """
    GET /practice/audio/sample — Stream teacher sample MP3.

    Placeholder: returns 501 until Task 8 implements TTS generation + audio serving.
    Real behaviour: call engines/tts.py to generate or retrieve cached teacher sample,
    return audio/mpeg bytes via StreamingResponse.
    """
    return JSONResponse(
        status_code=501,
        content={"detail": "Not implemented"},
    )
