"""
Onboarding router — /onboarding
Manages the multi-turn goal-discovery conversation that replaces Discord !go for new users.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from api.models import (
    OnboardingStartRequest,
    OnboardingRespondRequest,
    OnboardingConfirmRequest,
    OnboardingTurnResponse,
    OnboardingRespondResponse,
    OnboardingConfirmResponse,
    OnboardingHistoryResponse,
)
from api.dependencies import get_onboarding_chat
from engines.onboarding_chat import OnboardingChat

router = APIRouter(prefix="/onboarding", tags=["Onboarding"])


@router.post("/start", status_code=501)
async def start_onboarding(
    body: OnboardingStartRequest,
    chat: OnboardingChat = Depends(get_onboarding_chat),
) -> JSONResponse:
    """
    POST /onboarding/start — Start or resume onboarding conversation.

    Placeholder: returns 501 until Task 5 implements OnboardingChat wiring.
    Real behaviour: call chat.start_conversation_async(user_id) or resume if
    resume_if_exists=True and an active onboarding session already exists.
    """
    return JSONResponse(
        status_code=501,
        content={"detail": "Not implemented"},
    )


@router.post("/respond", status_code=501)
async def respond_onboarding(
    body: OnboardingRespondRequest,
    chat: OnboardingChat = Depends(get_onboarding_chat),
) -> JSONResponse:
    """
    POST /onboarding/respond — Submit a user reply and get next question or synthesis.

    Placeholder: returns 501 until Task 5 implements OnboardingChat wiring.
    Real behaviour: call chat.submit_user_reply_async(user_id, message); if
    result_type='synthesis' transition session to 'awaiting_goal_confirmation'.
    """
    return JSONResponse(
        status_code=501,
        content={"detail": "Not implemented"},
    )


@router.post("/confirm", status_code=501)
async def confirm_onboarding(
    body: OnboardingConfirmRequest,
    chat: OnboardingChat = Depends(get_onboarding_chat),
) -> JSONResponse:
    """
    POST /onboarding/confirm — Confirm or reject synthesized goal.

    Placeholder: returns 501 until Task 5 implements full confirmation + curriculum
    generation flow.  Positive confirmation blocks in v1 (Ollama takes 30-90 s).
    Real behaviour: if confirmed, call chat.confirm_and_create_curriculum_async() then
    curriculum_generator.generate_full_phase_async() for phase 1.
    """
    return JSONResponse(
        status_code=501,
        content={"detail": "Not implemented"},
    )


@router.get("/history", status_code=501)
async def get_onboarding_history(user_id: str) -> JSONResponse:
    """
    GET /onboarding/history?user_id=<uuid> — Fetch ordered conversation turns.

    Placeholder: returns 501 until Task 5 implements DB read via
    db.curriculum.get_onboarding_conversation().
    """
    return JSONResponse(
        status_code=501,
        content={"detail": "Not implemented"},
    )
