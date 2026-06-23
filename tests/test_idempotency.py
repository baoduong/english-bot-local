from __future__ import annotations

import json

import pytest

from db.connection import get_db_connection


def _audio_payload(audio_bytes: bytes) -> tuple[str, bytes, str]:
    return ("practice.m4a", audio_bytes, "audio/mp4")


def _seed_practice_context() -> tuple[str, int]:
    user_id = "user-idempotency"
    content_id = 11
    conn = get_db_connection()
    try:
        conn.execute(
            """
            INSERT INTO users (
                user_id, username, streak_count, last_study_date, current_level, total_sessions,
                created_at, onboarding_completed_at, active_curriculum_id, interface_language
            ) VALUES (?, ?, 0, NULL, 1, 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, 1, 'vi')
            """,
            (user_id, "User"),
        )
        conn.execute(
            """
            INSERT INTO curriculums (
                id, user_id, goal_title, goal_description, status, current_phase_number, interface_language
            ) VALUES (1, ?, 'Goal', 'Goal description', 'active', 1, 'vi')
            """,
            (user_id,),
        )
        conn.execute(
            """
            INSERT INTO phases (
                id, curriculum_id, phase_number, theme, vocabulary, milestones, status
            ) VALUES (1, 1, 1, 'Animals', '[]', '[]', 'active')
            """
        )
        conn.execute(
            """
            INSERT INTO phase_content (
                id, phase_id, sentence, target_phonemes, target_words, difficulty_score,
                attempt_count, last_score, consecutive_passes, mastered_at
            ) VALUES (?, 1, 'I like cats', '[]', '["cats"]', 1, 0, NULL, 0, NULL)
            """,
            (content_id,),
        )

        session = {
            "round": 1,
            "max_rounds": 5,
            "sentence": "I like cats",
            "new_word": None,
            "fail_count": 0,
            "mode": "curriculum_practice",
            "drill_words": [],
            "drill_index": 0,
            "drill_attempts": {},
            "drill_fails": 0,
            "drill_passed": 0,
            "drill_done": False,
            "session_stats": {"passed_first_try": 0, "needed_drill": 0, "skipped": 0},
            "started_at": "2026-06-23T00:00:00",
            "scores": [],
            "curriculum_id": 1,
            "current_phase_id": 1,
            "current_phase_number": 1,
            "phase_theme": "Animals",
            "phase_total_content": 1,
            "phase_mastered_count": 0,
            "content_id": content_id,
        }
        conn.execute(
            "INSERT INTO active_sessions (user_id, session_data) VALUES (?, ?)",
            (user_id, json.dumps(session)),
        )
        conn.commit()
    finally:
        conn.close()
    return user_id, content_id


def _mock_analysis(monkeypatch: pytest.MonkeyPatch, scores: list[int]) -> dict[str, int]:
    from api.routers import practice

    call_counter = {"count": 0}

    monkeypatch.setattr(practice, "_transcode_to_wav_sync", lambda *_args: None)

    def _analyze(*_args):
        index = call_counter["count"]
        call_counter["count"] += 1
        score = scores[index]
        return (score, "", "pass", [], [], {"cats": {"score": 100, "passed": True}})

    monkeypatch.setattr(practice, "analyze_audio_with_whisper", _analyze)
    monkeypatch.setattr(practice, "analyze_phonemes_per_word", lambda *_args: {"cats": {"phoneme_match_ratio": 1.0}})

    class _Prosody:
        def analyze(self, *_args):
            return {}

    monkeypatch.setattr(practice, "get_prosody_analyzer", lambda: _Prosody())
    monkeypatch.setattr(practice, "_record_practice_metrics_sync", lambda *_args: None)
    monkeypatch.setattr(practice, "_maybe_generate_coaching_sync", lambda **_kwargs: None)
    return call_counter


def _get_phase_content_stats(content_id: int) -> dict[str, int | None]:
    conn = get_db_connection()
    try:
        row = conn.execute(
            "SELECT attempt_count, consecutive_passes, last_score FROM phase_content WHERE id = ?",
            (content_id,),
        ).fetchone()
        assert row is not None
        return {
            "attempt_count": row["attempt_count"],
            "consecutive_passes": row["consecutive_passes"],
            "last_score": row["last_score"],
        }
    finally:
        conn.close()


@pytest.mark.asyncio
async def test_duplicate_audio_returns_cached(client, clean_db: str, monkeypatch: pytest.MonkeyPatch) -> None:
    user_id, content_id = _seed_practice_context()
    calls = _mock_analysis(monkeypatch, [90])
    audio_bytes = b"same-audio"

    first = await client.post(
        "/practice/audio",
        data={"user_id": user_id},
        files={"audio_file": _audio_payload(audio_bytes)},
    )
    second = await client.post(
        "/practice/audio",
        data={"user_id": user_id},
        files={"audio_file": _audio_payload(audio_bytes)},
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json() == first.json()
    assert calls["count"] == 1

    stats = _get_phase_content_stats(content_id)
    assert stats["attempt_count"] == 1
    assert stats["consecutive_passes"] == 1
    assert stats["last_score"] == 90


@pytest.mark.asyncio
async def test_different_audio_new_attempt(client, clean_db: str, monkeypatch: pytest.MonkeyPatch) -> None:
    user_id, content_id = _seed_practice_context()
    calls = _mock_analysis(monkeypatch, [90, 90])

    first = await client.post(
        "/practice/audio",
        data={"user_id": user_id},
        files={"audio_file": _audio_payload(b"audio-one")},
    )
    second = await client.post(
        "/practice/audio",
        data={"user_id": user_id},
        files={"audio_file": _audio_payload(b"audio-two")},
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert calls["count"] == 2

    stats = _get_phase_content_stats(content_id)
    assert stats["attempt_count"] == 2
    assert stats["consecutive_passes"] == 2
    assert stats["last_score"] == 90
