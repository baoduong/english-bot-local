"""
Users router — /users
Handles learner registration (UUID-based).
"""
from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from api.models import UserRegistrationRequest

router = APIRouter(prefix="/users", tags=["Users"])


@router.post("/register", status_code=501)
async def register_user(body: UserRegistrationRequest) -> JSONResponse:
    """
    POST /users/register — Register a new iPhone learner profile.

    Placeholder: returns 501 until Task 5 implements full registration logic.
    Expected real behaviour: create UUID user in `users` table, return UserProfile
    with next_action='onboarding_required'.
    """
    return JSONResponse(
        status_code=501,
        content={"detail": "Not implemented"},
    )
