from __future__ import annotations

import json

import pytest

from db.connection import get_db_connection


def _seed_regression_context(user_id: str, content_id: int = 99) -> None:
    conn = get_db_connection()
    try:
        conn.execute(
            """
            INSERT INTO users (
                user_id, username, streak_count, last_study_date, current_level, total_sessions,
                created_at, onboarding_completed_at, active_curriculum_id, interface_language
            ) VALUES (?, ?, 0, NULL, 1, 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, 1, 'vi')
            """,
            (user_id, "RegressionUser"),
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
            ) VALUES (1, 1, 1, 'Regression', '[]', '[]', 'active')
            """
        )
        conn.execute(
            """
            INSERT INTO phase_content (
                id, phase_id, sentence, target_phonemes, target_words, difficulty_score,
                attempt_count, last_score, consecutive_passes, mastered_at
            ) VALUES (?, 1, 'hello world', '[]', '[]', 1, 0, NULL, 0, NULL)
            """,
            (content_id,),
        )
        session = {
            "round": 1,
            "max_rounds": 5,
            "sentence": "hello world",
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
            "started_at": "2026-07-06T00:00:00",
            "scores": [],
            "curriculum_id": 1,
            "current_phase_id": 1,
            "current_phase_number": 1,
            "phase_theme": "Regression",
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


@pytest.mark.asyncio
async def test_practice_audio_survives_7tuple_engine_return(client, clean_db, monkeypatch):
    user_id = "regression-tuple-user"
    _seed_regression_context(user_id)

    from api.routers import practice

    monkeypatch.setattr(practice, "_transcode_to_wav_sync", lambda *_args: None)
    monkeypatch.setattr(
        practice,
        "analyze_audio_with_whisper",
        lambda *_args: (
            "hello world",
            85,
            "",
            "Good job",
            [],
            [("hello", "th_sound")],
            {"hello": {"score": 85, "passed": True, "heard": "hello"}, "world": {"score": 85, "passed": True, "heard": "world"}},
        ),
    )
    monkeypatch.setattr(practice, "analyze_phonemes_per_word", lambda *_args: {})

    resp = await client.post(
        "/practice/audio",
        data={"user_id": user_id},
        files={"audio_file": ("audio.wav", b"fake-audio-bytes", "audio/wav")},
    )

    assert resp.status_code != 500, f"Endpoint crashed with: {resp.text}"


def test_record_metrics_sync_handles_valid_error_types(clean_db):
    from api.routers.practice import _record_practice_metrics_sync

    _record_practice_metrics_sync("test-user", "hello world", 85, {}, [("hello", "th_sound")])


def test_record_metrics_sync_type_guard_skips_malformed_items(clean_db, capsys):
    from api.routers.practice import _record_practice_metrics_sync

    _record_practice_metrics_sync("test-user", "hello world", 85, {}, ["hello", "world"])

    captured = capsys.readouterr()
    assert "skipping malformed" in captured.out
