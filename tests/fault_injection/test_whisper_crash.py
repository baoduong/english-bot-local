from __future__ import annotations

import json

import pytest

from db.connection import get_db_connection
from tests.fixtures.audio_paths import AUDIO_FIXTURES


def _seed_practice_session(*, user_id: str = "fault-whisper-user", sentence: str = "fix") -> str:
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
            ) VALUES (1, 1, 1, 'Fault Injection', '[]', '[]', 'active')
            """
        )
        conn.execute(
            """
            INSERT INTO phase_content (
                id, phase_id, sentence, target_phonemes, target_words, difficulty_score,
                attempt_count, last_score, consecutive_passes, mastered_at
            ) VALUES (1, 1, ?, '[]', '["fix"]', 1, 0, NULL, 0, NULL)
            """,
            (sentence,),
        )
        session = {
            "round": 1,
            "max_rounds": 5,
            "sentence": sentence,
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
            "phase_theme": "Fault Injection",
            "phase_total_content": 1,
            "phase_mastered_count": 0,
            "content_id": 1,
        }
        conn.execute(
            "INSERT INTO active_sessions (user_id, session_data) VALUES (?, ?)",
            (user_id, json.dumps(session)),
        )
        conn.commit()
    finally:
        conn.close()
    return user_id


def _audio_payload() -> tuple[str, bytes, str]:
    return ("fix_correct.wav.m4a", AUDIO_FIXTURES["fix"].read_bytes(), "audio/mp4")


def _stub_non_whisper_dependencies(monkeypatch: pytest.MonkeyPatch) -> None:
    from api.routers import practice

    monkeypatch.setattr(practice, "_transcode_to_wav_sync", lambda *_args: None)
    monkeypatch.setattr(practice, "analyze_phonemes_per_word", lambda *_args: {})
    monkeypatch.setattr(practice, "_record_practice_metrics_sync", lambda *_args: None)
    monkeypatch.setattr(practice, "_maybe_generate_coaching_sync", lambda **_kwargs: None)

    class _Prosody:
        def analyze(self, *_args):
            return {}

    monkeypatch.setattr(practice, "get_prosody_analyzer", lambda: _Prosody())


@pytest.mark.asyncio
@pytest.mark.fault_injection
async def test_whisper_runtime_error_returns_500(client, clean_db, mock_whisper, monkeypatch: pytest.MonkeyPatch):
    del clean_db
    from api.main import app

    app.debug = False
    _seed_practice_session()
    _stub_non_whisper_dependencies(monkeypatch)
    mock_whisper.set_failure(RuntimeError("CUDA OOM simulated"))

    with pytest.raises(RuntimeError, match="CUDA OOM simulated"):
        await client.post(
            "/practice/audio",
            data={"user_id": "fault-whisper-user"},
            files={"audio_file": _audio_payload()},
        )


@pytest.mark.asyncio
@pytest.mark.fault_injection
async def test_whisper_malformed_dict_returns_500(client, clean_db, mock_whisper, monkeypatch: pytest.MonkeyPatch):
    del clean_db
    _seed_practice_session()
    _stub_non_whisper_dependencies(monkeypatch)
    mock_whisper.scenarios["fix_correct.wav"] = {
        "text": "fix",
        "segments": [{"words": [{"word": "fix", "probability": object()}]}],
        "language": "en",
    }

    response = await client.post(
        "/practice/audio",
        data={"user_id": "fault-whisper-user"},
        files={"audio_file": _audio_payload()},
    )
    assert response.status_code == 200


@pytest.mark.asyncio
@pytest.mark.fault_injection
async def test_whisper_empty_transcript_graceful(client, clean_db, mock_whisper, monkeypatch: pytest.MonkeyPatch):
    del clean_db
    _seed_practice_session()
    _stub_non_whisper_dependencies(monkeypatch)
    mock_whisper.scenarios["fix_correct.wav"] = {"text": "", "segments": [], "language": "en"}

    response = await client.post(
        "/practice/audio",
        data={"user_id": "fault-whisper-user"},
        files={"audio_file": _audio_payload()},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["scoring"]["overall_score"] == 0
    assert body["scoring"]["expected_text"] == "fix"
    assert body["scoring"]["word_scores"]
    assert body["scoring"]["word_scores"][0]["word"].lower() == "fix"
    assert body["scoring"]["word_scores"][0]["accuracy"] == 0
