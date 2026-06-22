from __future__ import annotations

import asyncio
from typing import Any, Literal, cast

from fastapi import APIRouter, Depends, HTTPException, status

from api.dependencies import get_curriculum_generator, get_phase_engine
from api.models import (
    AdvancePhaseRequest,
    AdvancePhaseResponse,
    CurriculumArchiveRequest,
    CurriculumArchiveResponse,
    CurriculumGenerateRequest,
    CurriculumGenerateResponse,
    CurriculumPhase,
    CurriculumSummary,
    CurrentCurriculumResponse,
    LoadingHint,
    PhaseDetailResponse,
    PhaseProgress,
    PracticeContentItem,
)
from analysis.phase_engine import PhaseEngine
from db.curriculum import (
    activate_phase,
    archive_curriculum,
    get_active_curriculum,
    get_active_phase,
    get_curriculum,
    get_next_practice_sentence,
    get_phase,
    get_phase_content,
    get_phase_progress,
    get_phases_for_curriculum,
)
from db.sessions import delete_session
from db.users import clear_active_curriculum, get_or_create_user
from engines.curriculum_generator import CurriculumGenerator

router = APIRouter(prefix="/curriculum", tags=["Curriculum"])


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


@router.get("/current", response_model=CurrentCurriculumResponse)
async def get_current_curriculum(user_id: str) -> CurrentCurriculumResponse:
    user = _ensure_user_exists(await asyncio.to_thread(get_or_create_user, user_id, user_id), user_id)
    curriculum_id = user.get("active_curriculum_id")
    if not curriculum_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No active curriculum found")

    curriculum = _ensure_dict(await asyncio.to_thread(get_curriculum, curriculum_id), "Curriculum not found")

    active_phase = _ensure_dict(await asyncio.to_thread(get_active_phase, curriculum_id), "No active phase found")

    progress = _ensure_dict(await asyncio.to_thread(get_phase_progress, _coerce_int(active_phase.get("id"))), "Phase progress not found")
    next_item = await asyncio.to_thread(get_next_practice_sentence, active_phase["id"])

    return CurrentCurriculumResponse(
        curriculum=_to_curriculum_summary(curriculum),
        active_phase=_to_curriculum_phase(active_phase, progress),
        next_item=_to_practice_content_item(next_item) if next_item else None,
    )


@router.post("/generate", status_code=status.HTTP_201_CREATED, response_model=CurriculumGenerateResponse)
async def generate_curriculum(
    body: CurriculumGenerateRequest,
    generator: CurriculumGenerator = Depends(get_curriculum_generator),
) -> CurriculumGenerateResponse:
    user = _ensure_user_exists(await asyncio.to_thread(get_or_create_user, body.user_id, body.user_id), body.user_id)
    if user.get("active_curriculum_id") != body.curriculum_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Curriculum not active for user")

    curriculum = _ensure_dict(await asyncio.to_thread(get_curriculum, body.curriculum_id), "Curriculum not found")

    previous_phases = _ensure_list(await asyncio.to_thread(get_phases_for_curriculum, body.curriculum_id))
    phase_id, _ = await asyncio.to_thread(
        generator.generate_full_phase,
        body.curriculum_id,
        _coerce_text(curriculum.get("goal_title")),
        _coerce_text(curriculum.get("goal_description")),
        body.phase_number,
        previous_phases,
        body.reason or "",
    )

    phase = _ensure_dict(await asyncio.to_thread(get_phase, phase_id), "Generated phase not found")
    progress = _ensure_dict(await asyncio.to_thread(get_phase_progress, phase_id), "Phase progress not found")
    content_items = _ensure_list(await asyncio.to_thread(get_phase_content, phase_id))

    return CurriculumGenerateResponse(
        loading=LoadingHint(blocking=True, message="Generating curriculum phase", estimated_seconds=60),
        curriculum=_to_curriculum_summary(curriculum),
        phase=_to_curriculum_phase(phase, progress),
        content_items=[_to_practice_content_item(item) for item in content_items],
    )


@router.get("/phase/{phase_id}", response_model=PhaseDetailResponse)
async def get_curriculum_phase(phase_id: int) -> PhaseDetailResponse:
    phase = _ensure_dict(await asyncio.to_thread(get_phase, phase_id), f"Phase not found: {phase_id}")

    progress = _ensure_dict(await asyncio.to_thread(get_phase_progress, phase_id), "Phase progress not found")
    content_items = _ensure_list(await asyncio.to_thread(get_phase_content, phase_id))
    return PhaseDetailResponse(
        phase=_to_curriculum_phase(phase, progress),
        content_items=[_to_practice_content_item(item) for item in content_items],
    )


@router.post("/archive", response_model=CurriculumArchiveResponse)
async def archive_curriculum_route(body: CurriculumArchiveRequest) -> CurriculumArchiveResponse:
    user = _ensure_user_exists(await asyncio.to_thread(get_or_create_user, body.user_id, body.user_id), body.user_id)
    curriculum_id = user.get("active_curriculum_id")
    if not curriculum_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No active curriculum to archive")
    if not body.confirm:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Archive confirmation required")

    _ensure_dict(await asyncio.to_thread(get_curriculum, curriculum_id), "Curriculum not found")

    await asyncio.to_thread(archive_curriculum, curriculum_id)
    await asyncio.to_thread(clear_active_curriculum, body.user_id)
    await asyncio.to_thread(delete_session, body.user_id)

    return CurriculumArchiveResponse(
        archived_curriculum_id=curriculum_id,
        status="archived",
        onboarding_required=True,
        message="Curriculum archived and onboarding reset",
    )


@router.post("/advance-phase", response_model=AdvancePhaseResponse)
async def advance_phase(
    body: AdvancePhaseRequest,
    phase_engine: PhaseEngine = Depends(get_phase_engine),
    generator: CurriculumGenerator = Depends(get_curriculum_generator),
) -> AdvancePhaseResponse:
    _ensure_user_exists(await asyncio.to_thread(get_or_create_user, body.user_id, body.user_id), body.user_id)

    curriculum = _ensure_dict(await asyncio.to_thread(get_active_curriculum, body.user_id), "No active curriculum found")
    active_phase = _ensure_dict(await asyncio.to_thread(get_active_phase, curriculum["id"]), "No active phase found")

    decision = await phase_engine.evaluate_phase_async(_coerce_int(active_phase.get("id")))
    action = _coerce_text(decision.get("action"))

    if action == "repeat":
        progress = _ensure_dict(await asyncio.to_thread(get_phase_progress, _coerce_int(active_phase.get("id"))), "Phase progress not found")
        next_item = await asyncio.to_thread(get_next_practice_sentence, active_phase["id"])
        return AdvancePhaseResponse(
            action="repeat",
            message="Tiếp tục luyện phase hiện tại",
            curriculum=_to_curriculum_summary(curriculum),
            active_phase=_to_curriculum_phase(active_phase, progress),
            first_practice_item=_to_practice_content_item(next_item) if next_item else None,
        )

    result = await phase_engine.apply_decision_async(_coerce_int(active_phase.get("id")), decision)
    next_action = _coerce_text(result.get("next_action"))

    if next_action == "generate_next_phase":
        previous_phases = _ensure_list(await asyncio.to_thread(get_phases_for_curriculum, curriculum["id"]))
        new_phase_id, _ = await asyncio.to_thread(
            generator.generate_full_phase,
            curriculum["id"],
            _coerce_text(curriculum.get("goal_title")),
            _coerce_text(curriculum.get("goal_description")),
            _coerce_int(result.get("next_phase_number"), _coerce_int(active_phase.get("phase_number"), 1) + 1),
            previous_phases,
            _coerce_text(decision.get("reasoning")),
        )
        await asyncio.to_thread(activate_phase, new_phase_id)
        await asyncio.to_thread(delete_session, body.user_id)
        action = "advance"
    elif next_action == "phase_regenerated":
        await asyncio.to_thread(delete_session, body.user_id)
        action = "phase_regenerated"
    else:
        action = action or next_action

    curriculum = _ensure_dict(await asyncio.to_thread(get_curriculum, curriculum["id"]), "Curriculum not found")
    active_phase = _ensure_dict(await asyncio.to_thread(get_active_phase, curriculum["id"]), "No active phase found")
    progress = _ensure_dict(await asyncio.to_thread(get_phase_progress, _coerce_int(active_phase.get("id"))), "Phase progress not found")
    first_practice_item = await asyncio.to_thread(get_next_practice_sentence, active_phase["id"])

    message_map = {
        "advance": "Đã tạo phase tiếp theo thành công",
        "regenerate": "Đã tái tạo phase hiện tại",
        "phase_regenerated": "Đã tái tạo phase hiện tại",
    }

    resolved_action = cast(Literal["advance", "repeat", "regenerate", "phase_regenerated"], action)

    return AdvancePhaseResponse(
        action=resolved_action,
        message=message_map.get(action, "Đã cập nhật phase"),
        curriculum=_to_curriculum_summary(curriculum),
        active_phase=_to_curriculum_phase(active_phase, progress),
        first_practice_item=_to_practice_content_item(first_practice_item) if first_practice_item else None,
    )
