from __future__ import annotations

import asyncio
import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from api.dependencies import get_curriculum_generator, get_onboarding_chat
from api.models import (
    CurriculumPhase,
    CurriculumSummary,
    GoalSynthesis,
    LoadingHint,
    OnboardingConfirmRequest,
    OnboardingConfirmResponse,
    OnboardingHistoryResponse,
    OnboardingMessage,
    OnboardingRespondRequest,
    OnboardingRespondResponse,
    OnboardingSessionState,
    OnboardingStartRequest,
    OnboardingTurnResponse,
    PhaseProgress,
    PracticeContentItem,
)
from db.curriculum import (
    clear_onboarding_conversation,
    create_curriculum,
    get_active_curriculum,
    get_active_phase,
    get_onboarding_conversation,
    get_phase,
    get_phase_content,
    get_phase_progress,
)
from db.sessions import delete_session, save_session
from db.users import get_or_create_user, mark_onboarding_complete, needs_onboarding
from engines.curriculum_generator import CurriculumGenerator
from engines.ollama_client import OllamaSchemaError, OllamaUnavailableError
from engines.onboarding_chat import OnboardingChat

router = APIRouter(prefix="/onboarding", tags=["Onboarding"])


def _ensure_user_exists(user: dict[str, Any] | None, user_id: str) -> dict[str, Any]:
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"User not found: {user_id}")
    return user


def _coerce_text(value: Any, default: str = "") -> str:
    return value if isinstance(value, str) else default


def _coerce_optional_text(value: Any) -> str | None:
    return value if isinstance(value, str) else None


def _coerce_int(value: Any, default: int = 0) -> int:
    return value if isinstance(value, int) else default


def _ensure_dict(value: Any, detail: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)
    return value


def _ensure_list(value: Any) -> list[dict[str, Any]]:
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def _to_goal_synthesis(goal: dict[str, Any] | None) -> GoalSynthesis | None:
    if not goal:
        return None
    return GoalSynthesis(**goal)


def _to_onboarding_messages(turns: list[dict[str, Any]]) -> list[OnboardingMessage]:
    return [
        OnboardingMessage(
            turn_number=turn["turn_number"],
            role=turn["role"],
            content=turn["content"],
        )
        for turn in turns
    ]


def _session_state(user_id: str, mode: str, onboarding_turn: int | None = None) -> OnboardingSessionState:
    return OnboardingSessionState(user_id=user_id, mode=mode, onboarding_turn=onboarding_turn)


def _to_curriculum_summary(curriculum: dict[str, Any]) -> CurriculumSummary:
    return CurriculumSummary(
        curriculum_id=_coerce_int(curriculum.get("id")),
        user_id=_coerce_optional_text(curriculum.get("user_id")),
        status=_coerce_text(curriculum.get("status")),
        goal_title=_coerce_text(curriculum.get("goal_title")),
        goal_description=_coerce_text(curriculum.get("goal_description")),
        interface_language=_coerce_text(curriculum.get("interface_language"), "vi"),
        current_phase_number=_coerce_int(curriculum.get("current_phase_number"), 1),
        created_at=curriculum.get("created_at"),
        completed_at=curriculum.get("completed_at"),
    )


def _to_phase_progress(progress: dict[str, Any] | None) -> PhaseProgress | None:
    if not progress:
        return None
    return PhaseProgress(
        total=_coerce_int(progress.get("total"), 0),
        attempted=_coerce_int(progress.get("attempted"), 0),
        mastered=_coerce_int(progress.get("mastered"), 0),
        avg_score=float(progress.get("avg_score") or 0.0),
        struggling_words=progress.get("struggling_words", []) if isinstance(progress.get("struggling_words"), list) else [],
    )


def _to_curriculum_phase(phase: dict[str, Any], progress: dict[str, Any] | None = None) -> CurriculumPhase:
    return CurriculumPhase(
        phase_id=_coerce_int(phase.get("id")),
        phase_number=_coerce_int(phase.get("phase_number"), 1),
        theme=_coerce_text(phase.get("theme")),
        status=_coerce_text(phase.get("status")),
        regeneration_count=_coerce_int(phase.get("regeneration_count"), 0),
        vocabulary=phase.get("vocabulary", []) if isinstance(phase.get("vocabulary"), list) else [],
        milestones=phase.get("milestones", []) if isinstance(phase.get("milestones"), list) else [],
        curriculum_id=_coerce_int(phase.get("curriculum_id"), 0) or None,
        progress=_to_phase_progress(progress),
    )


def _to_practice_content_item(item: dict[str, Any]) -> PracticeContentItem:
    return PracticeContentItem(
        content_id=_coerce_int(item.get("id")),
        sentence=_coerce_text(item.get("sentence")),
        target_phonemes=item.get("target_phonemes", []) if isinstance(item.get("target_phonemes"), list) else [],
        target_words=item.get("target_words", []) if isinstance(item.get("target_words"), list) else [],
        difficulty_score=_coerce_int(item.get("difficulty_score"), 0),
        attempt_count=item.get("attempt_count"),
        last_score=item.get("last_score"),
        mastered_at=item.get("mastered_at"),
    )


@router.post("/start", status_code=status.HTTP_201_CREATED, response_model=OnboardingTurnResponse)
async def start_onboarding(
    body: OnboardingStartRequest,
    chat: OnboardingChat = Depends(get_onboarding_chat),
) -> OnboardingTurnResponse:
    user = _ensure_user_exists(await asyncio.to_thread(get_or_create_user, body.user_id, body.user_id), body.user_id)

    if user.get("onboarding_completed_at") and not await asyncio.to_thread(needs_onboarding, body.user_id):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Onboarding already complete")

    history = _ensure_list(await asyncio.to_thread(get_onboarding_conversation, body.user_id))
    if body.resume_if_exists and history:
        messages = _to_onboarding_messages(history)
        assistant_message = next((m for m in reversed(messages) if m.role == "assistant"), None)
        if assistant_message is None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Onboarding history is incomplete")
        await asyncio.to_thread(save_session, body.user_id, {"mode": "onboarding", "onboarding_turn": assistant_message.turn_number})
        return OnboardingTurnResponse(
            session=_session_state(body.user_id, "onboarding", assistant_message.turn_number),
            assistant_message=assistant_message,
            history_preview=messages,
            pending_goal_synthesis=None,
        )

    greeting = await asyncio.to_thread(chat.start_conversation, body.user_id, _coerce_text(user.get("interface_language"), "vi"))
    history = _ensure_list(await asyncio.to_thread(get_onboarding_conversation, body.user_id))
    messages = _to_onboarding_messages(history)
    assistant_message = OnboardingMessage(turn_number=messages[-1].turn_number, role="assistant", content=greeting)
    await asyncio.to_thread(save_session, body.user_id, {"mode": "onboarding", "onboarding_turn": assistant_message.turn_number})

    return OnboardingTurnResponse(
        session=_session_state(body.user_id, "onboarding", assistant_message.turn_number),
        assistant_message=assistant_message,
        history_preview=messages,
        pending_goal_synthesis=None,
    )


@router.post("/respond", response_model=OnboardingRespondResponse)
async def respond_onboarding(
    body: OnboardingRespondRequest,
    chat: OnboardingChat = Depends(get_onboarding_chat),
) -> OnboardingRespondResponse:
    user = _ensure_user_exists(await asyncio.to_thread(get_or_create_user, body.user_id, body.user_id), body.user_id)
    if user.get("onboarding_completed_at") and not await asyncio.to_thread(needs_onboarding, body.user_id):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Onboarding already complete")

    result = _ensure_dict(await asyncio.to_thread(chat.submit_user_reply, body.user_id, body.message), "Onboarding response missing")
    result_type = _coerce_text(result.get("type"))

    if result_type == "question":
        assistant_message = OnboardingMessage(
            turn_number=_coerce_int(result.get("turn_number")),
            role="assistant",
            content=_coerce_text(result.get("text")),
        )
        mode = "onboarding"
        pending_goal_synthesis = None
    elif result_type == "synthesis":
        goal = _to_goal_synthesis(_ensure_dict(result.get("goal"), "Goal synthesis missing"))
        assistant_message = OnboardingMessage(
            turn_number=_coerce_int(result.get("turn_number")),
            role="assistant",
            content=goal.model_dump_json() if goal else "",
        )
        mode = "awaiting_goal_confirmation"
        pending_goal_synthesis = goal
    else:
        raise OllamaSchemaError(f"Unexpected onboarding result type: {result_type}")

    await asyncio.to_thread(
        save_session,
        body.user_id,
        {
            "mode": mode,
            "onboarding_turn": _coerce_int(result.get("turn_number")),
            "pending_goal_synthesis": pending_goal_synthesis.model_dump() if pending_goal_synthesis else None,
        },
    )

    return OnboardingRespondResponse(
        session=_session_state(body.user_id, mode, _coerce_int(result.get("turn_number"))),
        result_type=result_type,
        assistant_message=assistant_message,
        pending_goal_synthesis=pending_goal_synthesis,
    )


@router.post("/confirm", response_model=OnboardingConfirmResponse)
async def confirm_onboarding(
    body: OnboardingConfirmRequest,
    chat: OnboardingChat = Depends(get_onboarding_chat),
    generator: CurriculumGenerator = Depends(get_curriculum_generator),
) -> OnboardingConfirmResponse:
    user = _ensure_user_exists(await asyncio.to_thread(get_or_create_user, body.user_id, body.user_id), body.user_id)
    history = _ensure_list(await asyncio.to_thread(get_onboarding_conversation, body.user_id))
    if not history:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No onboarding conversation found")

    goal = _ensure_dict(await asyncio.to_thread(chat.synthesize_goal, body.user_id), "Goal synthesis missing")
    if not body.confirmed:
        await asyncio.to_thread(clear_onboarding_conversation, body.user_id)
        await asyncio.to_thread(delete_session, body.user_id)
        return OnboardingConfirmResponse(
            status="rejected",
            message="Goal confirmation rejected",
            onboarding_history_cleared=True,
        )

    if user.get("active_curriculum_id"):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Active curriculum already exists")

    curriculum_id = await asyncio.to_thread(
        create_curriculum,
        body.user_id,
        _coerce_text(goal.get("goal_title")),
        _coerce_text(goal.get("goal_description")),
        _coerce_text(user.get("interface_language"), "vi"),
    )
    await asyncio.to_thread(mark_onboarding_complete, body.user_id, curriculum_id)

    previous_phases: list[dict[str, Any]] = []
    phase_id, _ = await asyncio.to_thread(
        generator.generate_full_phase,
        curriculum_id,
        _coerce_text(goal.get("goal_title")),
        _coerce_text(goal.get("goal_description")),
        1,
        previous_phases,
        "",
    )

    curriculum = _ensure_dict(await asyncio.to_thread(get_active_curriculum, body.user_id), "Active curriculum not found")
    phase = _ensure_dict(await asyncio.to_thread(get_phase, phase_id), "Generated phase not found")
    phase_progress = _ensure_dict(await asyncio.to_thread(get_phase_progress, phase_id), "Phase progress not found")
    phase_content = _ensure_list(await asyncio.to_thread(get_phase_content, phase_id))
    await asyncio.to_thread(clear_onboarding_conversation, body.user_id)
    await asyncio.to_thread(delete_session, body.user_id)

    return OnboardingConfirmResponse(
        status="confirmed",
        loading=LoadingHint(blocking=True, message="Generating first curriculum phase", estimated_seconds=60),
        curriculum=_to_curriculum_summary(curriculum),
        phase=_to_curriculum_phase(phase, phase_progress),
        first_practice_item=_to_practice_content_item(phase_content[0]) if phase_content else None,
        message="Goal confirmed and curriculum generated",
        onboarding_history_cleared=True,
    )


@router.get("/history", response_model=OnboardingHistoryResponse)
async def get_onboarding_history(user_id: str) -> OnboardingHistoryResponse:
    _ensure_user_exists(await asyncio.to_thread(get_or_create_user, user_id, user_id), user_id)
    turns = _ensure_list(await asyncio.to_thread(get_onboarding_conversation, user_id))
    if not turns:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No onboarding history found")

    pending_goal = None
    if turns[-1]["role"] == "assistant" and "goal_title" in turns[-1]["content"]:
        try:
            pending_goal = GoalSynthesis(**json.loads(turns[-1]["content"]))
        except (ValueError, TypeError, json.JSONDecodeError):
            pending_goal = None

    mode = "awaiting_goal_confirmation" if pending_goal else "onboarding"
    return OnboardingHistoryResponse(
        user_id=user_id,
        mode=mode,
        turns=_to_onboarding_messages(turns),
        pending_goal_synthesis=pending_goal,
    )
