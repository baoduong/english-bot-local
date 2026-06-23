from __future__ import annotations

import pytest

from db.users import get_or_create_user


@pytest.mark.asyncio
async def test_resume_after_archive_starts_new_session(client, monkeypatch: pytest.MonkeyPatch) -> None:
    from api.routers import practice

    user_id = "resume-archived-curriculum"
    get_or_create_user(user_id, "User")
    monkeypatch.setattr(practice, "_require_user_sync", lambda uid: {"id": uid})
    monkeypatch.setattr(practice, "_load_session_sync", lambda _uid: {"mode": "curriculum_practice", "curriculum_id": 999, "current_phase_id": 999, "content_id": 7, "started_at": "2026-06-23T00:00:00", "round": 1, "max_rounds": 5, "sentence": "stale sentence", "new_word": None, "fail_count": 0, "drill_words": [], "drill_index": 0, "drill_attempts": {}, "drill_fails": 0, "drill_passed": 0, "drill_done": False, "session_stats": {"passed_first_try": 0, "needed_drill": 0, "skipped": 0}, "scores": [], "current_phase_number": 1, "phase_theme": "archived", "phase_total_content": 0, "phase_mastered_count": 0})
    monkeypatch.setattr(practice, "_build_state_response_sync", lambda *_args, **_kwargs: (_ for _ in ()).throw(practice._error(404, "SESSION_CONTEXT_MISSING", "Session curriculum or phase no longer exists.")))
    monkeypatch.setattr(practice, "needs_onboarding", lambda _uid: False)
    monkeypatch.setattr(practice, "get_active_curriculum", lambda _uid: None)
    monkeypatch.setattr(practice, "get_active_phase", lambda _cid: None)

    response = await client.post("/practice/session/start", json={"user_id": user_id})

    assert response.status_code == 409
    body = response.json()
    assert body["detail"]["error_code"] == "ONBOARDING_INCOMPLETE"
