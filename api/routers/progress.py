from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException

from api.models import CurriculumSummary, PhaseProgress, ProgressResponse, SampleAudio, UserProfile, WordScore
from db.connection import get_db_connection
from db.curriculum import get_active_curriculum, get_active_phase, get_phase_progress
from db.users import get_or_create_user

router = APIRouter(prefix="/progress", tags=["Progress"])


def _error(status_code: int, code: str, message: str, detail: Any | None = None) -> HTTPException:
    payload: dict[str, Any] = {"error_code": code, "message": message}
    if detail is not None:
        payload["detail"] = detail
    return HTTPException(status_code=status_code, detail=payload)


def _get_user_row_sync(user_id: str) -> dict[str, Any] | None:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def _get_recent_word_scores_sync(user_id: str) -> list[dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT word,
               ROUND(total_score / NULLIF(attempt_count, 0), 1) AS avg_score,
               attempt_count,
               success_count
        FROM word_statistics
        WHERE user_id = ? AND attempt_count > 0
        ORDER BY last_attempt DESC
        LIMIT 10
        """,
        (user_id,),
    )
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows


def _to_user_profile(row: dict[str, Any]) -> UserProfile:
    return UserProfile(
        user_id=row["user_id"],
        username=row.get("username") or "User",
        display_name=None,
        interface_language=row.get("interface_language") or "vi",
        created_at=datetime.fromisoformat(row["created_at"]),
        onboarding_completed_at=datetime.fromisoformat(row["onboarding_completed_at"]) if row.get("onboarding_completed_at") else None,
        active_curriculum_id=row.get("active_curriculum_id"),
        current_level=int(row.get("current_level") or 1),
        total_sessions=int(row.get("total_sessions") or 0),
        streak_count=int(row.get("streak_count") or 0),
    )


def _to_curriculum_summary(curriculum: dict[str, Any] | None) -> CurriculumSummary | None:
    if not curriculum:
        return None
    return CurriculumSummary(
        curriculum_id=curriculum["id"],
        user_id=curriculum.get("user_id"),
        status=curriculum.get("status", "active"),
        goal_title=curriculum["goal_title"],
        goal_description=curriculum.get("goal_description") or "",
        interface_language=curriculum.get("interface_language") or "vi",
        current_phase_number=int(curriculum.get("current_phase_number") or 1),
        created_at=datetime.fromisoformat(curriculum["created_at"]) if curriculum.get("created_at") else None,
        completed_at=datetime.fromisoformat(curriculum["completed_at"]) if curriculum.get("completed_at") else None,
    )


def _to_word_score(row: dict[str, Any]) -> WordScore:
    accuracy = max(0, min(100, int(round(row.get("avg_score") or 0))))
    if accuracy >= 80:
        color = "green"
    elif accuracy >= 60:
        color = "yellow"
    else:
        color = "red"
    return WordScore(
        word=row["word"],
        accuracy=accuracy,
        color=color,
        phoneme_similarity=1.0 if color == "green" else 0.6 if color == "yellow" else 0.3,
        tip=None,
    )


def _to_phase_progress_model(raw: dict[str, Any] | None) -> PhaseProgress | None:
    if not raw:
        return None
    return PhaseProgress(
        total=int(raw.get("total") or 0),
        attempted=int(raw.get("attempted") or 0),
        mastered=int(raw.get("mastered") or 0),
        avg_score=float(raw.get("avg_score") or 0.0),
        struggling_words=list(raw.get("struggling_words") or []),
    )


@router.get("", response_model=ProgressResponse)
async def get_progress(user_id: str) -> ProgressResponse:
    await asyncio.to_thread(get_or_create_user, user_id, "User")
    user_row = await asyncio.to_thread(_get_user_row_sync, user_id)
    if not user_row:
        raise _error(404, "USER_NOT_FOUND", "User not found.")

    curriculum = await asyncio.to_thread(get_active_curriculum, user_id)
    phase_progress = None
    if curriculum:
        phase = await asyncio.to_thread(get_active_phase, curriculum["id"])
        if phase:
            phase_progress = await asyncio.to_thread(get_phase_progress, phase["id"])

    recent_word_rows = await asyncio.to_thread(_get_recent_word_scores_sync, user_id)
    return ProgressResponse(
        user=_to_user_profile(user_row),
        curriculum=_to_curriculum_summary(curriculum),
        phase_progress=_to_phase_progress_model(phase_progress),
        recent_word_scores=[_to_word_score(row) for row in recent_word_rows],
        last_sample_audio=SampleAudio(
            audio_id=f"progress-{user_id}",
            content_type="audio/mpeg",
            duration_ms=1000,
            url=f"/practice/audio/sample?user_id={user_id}",
            expires_at=datetime.now(),
        ) if curriculum else None,
    )
