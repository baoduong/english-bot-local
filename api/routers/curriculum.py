"""
Curriculum router — /curriculum
Retrieves and manages the learner's AI-generated curriculum and phase data.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from api.models import (
    CurriculumGenerateRequest,
    CurriculumArchiveRequest,
    CurrentCurriculumResponse,
    CurriculumGenerateResponse,
    PhaseDetailResponse,
    CurriculumArchiveResponse,
)
from api.dependencies import get_curriculum_generator
from engines.curriculum_generator import CurriculumGenerator

router = APIRouter(prefix="/curriculum", tags=["Curriculum"])


@router.get("/current", status_code=501)
async def get_current_curriculum(user_id: str) -> JSONResponse:
    """
    GET /curriculum/current?user_id=<uuid> — Active curriculum + phase summary.

    Placeholder: returns 501 until Task 5 implements DB reads via
    db.curriculum.get_curriculum() + db.curriculum.get_phase().
    """
    return JSONResponse(
        status_code=501,
        content={"detail": "Not implemented"},
    )


@router.post("/generate", status_code=501)
async def generate_curriculum(
    body: CurriculumGenerateRequest,
    generator: CurriculumGenerator = Depends(get_curriculum_generator),
) -> JSONResponse:
    """
    POST /curriculum/generate — Generate or regenerate a curriculum phase.

    Placeholder: returns 501 until Task 5 wires CurriculumGenerator.
    Blocking in v1 — client must show a loading spinner while waiting (30-90 s).
    Real behaviour: call generator.generate_full_phase_async().
    """
    return JSONResponse(
        status_code=501,
        content={"detail": "Not implemented"},
    )


@router.get("/phase/{phase_id}", status_code=501)
async def get_curriculum_phase(phase_id: int) -> JSONResponse:
    """
    GET /curriculum/phase/{phase_id} — Detailed phase metadata + practice items.

    Placeholder: returns 501 until Task 5 implements DB reads via
    db.curriculum.get_phase() + db.curriculum.get_phase_content().
    """
    return JSONResponse(
        status_code=501,
        content={"detail": "Not implemented"},
    )


@router.post("/archive", status_code=501)
async def archive_curriculum(body: CurriculumArchiveRequest) -> JSONResponse:
    """
    POST /curriculum/archive — Archive current curriculum, reset onboarding state.

    Placeholder: returns 501 until Task 5 implements archive + goal-change flow.
    Real behaviour: mark curriculum as archived, clear active_curriculum_id on user,
    reset onboarding_completed_at so /onboarding/start is required again.
    """
    return JSONResponse(
        status_code=501,
        content={"detail": "Not implemented"},
    )
