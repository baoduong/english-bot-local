"""
Progress router — /progress
Mirrors the Discord !me summary: user profile + curriculum + phase stats.
"""
from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from api.models import ProgressResponse

router = APIRouter(prefix="/progress", tags=["Progress"])


@router.get("", status_code=501)
async def get_progress(user_id: str) -> JSONResponse:
    """
    GET /progress?user_id=<uuid> — Learner progress overview.

    Placeholder: returns 501 until Task 6 implements reads from:
    - db.users.get_user()
    - db.curriculum.get_curriculum() + get_phase_progress()
    - db.word_stats (recent word scores)
    """
    return JSONResponse(
        status_code=501,
        content={"detail": "Not implemented"},
    )
