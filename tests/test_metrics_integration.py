"""Integration test: real _record_practice_metrics_sync gets called with real error_types shape."""
from __future__ import annotations

import json

import pytest

from db.connection import get_db_connection


def _seed_metrics_context(user_id: str, content_id: int = 77) -> None:
    conn = get_db_connection()
    try:
        conn.execute(
            """
            INSERT INTO users (
                user_id, username, streak_count, last_study_date, current_level, total_sessions,
                created_at, onboarding_completed_at, active_curriculum_id, interface_language
            ) VALUES (?, ?, 0, NULL, 1, 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, 1, 'vi')
            """,
            (user_id, "MetricsUser"),
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
            ) VALUES (1, 1, 1, 'Metrics', '[]', '[]', 'active')
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
            "phase_theme": "Metrics",
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
async def test_practice_audio_records_metrics_with_real_error_types(client, clean_db, monkeypatch):
    """Full round-trip: real error_types tuples flow from engine → metrics DB via _record_practice_metrics_sync."""
    user_id = "metrics-integration-user"
    _seed_metrics_context(user_id)

    from api.routers import practice

    monkeypatch.setattr(practice, "_transcode_to_wav_sync", lambda *_args: None)
    monkeypatch.setattr(
        practice,
        "analyze_audio_with_whisper",
        lambda *_args: (
            "hello wrold",
            60,
            "",
            "Keep trying",
            ["wrold"],
            [("wrold", "spelling"), ("wrold", "vowel_stress")],
            {
                "hello": {"score": 90, "passed": True, "heard": "hello"},
                "wrold": {"score": 30, "passed": False, "heard": "wrold"},
            },
        ),
    )
    monkeypatch.setattr(practice, "analyze_phonemes_per_word", lambda *_args: {})

    resp = await client.post(
        "/practice/audio",
        data={"user_id": user_id},
        files={"audio_file": ("practice.m4a", b"fake-audio-bytes", "audio/mp4")},
    )

    assert resp.status_code == 200, f"Endpoint failed ({resp.status_code}): {resp.text}"

    conn = get_db_connection()
    try:
        rows = conn.execute(
            "SELECT error_type, word FROM error_patterns WHERE user_id = ?",
            (user_id,),
        ).fetchall()
    finally:
        conn.close()

    assert len(rows) >= 2, f"Expected 2+ error_pattern rows, got {len(rows)}: {rows}"
    error_types_found = {(row["error_type"], row["word"]) for row in rows}
    assert ("spelling", "wrold") in error_types_found, f"Missing spelling/wrold in {error_types_found}"
    assert ("vowel_stress", "wrold") in error_types_found, f"Missing vowel_stress/wrold in {error_types_found}"
