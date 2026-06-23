from __future__ import annotations

import json

import pytest

from analysis import pronunciation
from db.connection import get_db_connection


def _audio_payload() -> tuple[str, bytes, str]:
    return ("practice.m4a", b"fake-audio-bytes", "audio/mp4")


def _seed_practice_session(*, sentence: str = "hello world") -> str:
    user_id = "routing-user"
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
            ) VALUES (1, 1, 1, 'Routing', '[]', '[]', 'active')
            """
        )
        conn.execute(
            """
            INSERT INTO phase_content (
                id, phase_id, sentence, target_phonemes, target_words, difficulty_score,
                attempt_count, last_score, consecutive_passes, mastered_at
            ) VALUES (1, 1, ?, '[]', '["world"]', 1, 0, NULL, 0, NULL)
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
            "phase_theme": "Routing",
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


def _stub_practice_dependencies(monkeypatch: pytest.MonkeyPatch) -> None:
    from api.routers import practice

    monkeypatch.setattr(practice, "_transcode_to_wav_sync", lambda *_args: None)
    monkeypatch.setattr(practice, "analyze_phonemes_per_word", lambda *_args: {})
    monkeypatch.setattr(practice, "_record_practice_metrics_sync", lambda *_args: None)
    monkeypatch.setattr(practice, "_maybe_generate_coaching_sync", lambda **_kwargs: None)

    class _Prosody:
        def analyze(self, *_args):
            return {}

    monkeypatch.setattr(practice, "get_prosody_analyzer", lambda: _Prosody())


def test_uses_whisper_when_azure_off(
    monkeypatch: pytest.MonkeyPatch,
    mock_whisper,
    mock_azure,
) -> None:
    whisper_calls: list[str] = []

    def _spy_transcribe(audio_path: str, **kwargs: object):
        whisper_calls.append(audio_path)
        return {"text": "hello", "segments": [], "language": "en"}

    monkeypatch.setenv("USE_AZURE_SPEECH", "false")
    monkeypatch.setattr(mock_whisper, "transcribe", _spy_transcribe)
    mock_azure.set_failure(AssertionError("azure should not be called"))

    result = pronunciation.analyze_audio("sample.wav", "throughout")

    assert whisper_calls == ["sample.wav"]
    assert result[0] == "hello"
    assert result[1] == 0
    assert result[4] == ["throughout"]


def test_uses_azure_when_azure_on_and_complex(
    monkeypatch: pytest.MonkeyPatch,
    mock_whisper,
    mock_azure,
) -> None:
    monkeypatch.setenv("USE_AZURE_SPEECH", "true")
    monkeypatch.setattr(pronunciation, "AZURE_KEY", "fake-key")
    monkeypatch.setattr(pronunciation, "assess_difficulty", lambda _text: "complex")
    mock_azure.set_score(88, {"throughout": {"score": 88, "passed": True}})
    monkeypatch.setattr(
        mock_whisper,
        "transcribe",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("whisper should not be called")),
    )

    result = pronunciation.analyze_audio("sample.wav", "throughout")

    assert result[0] == "mock transcript"
    assert result[1] == 88


def test_uses_whisper_when_azure_on_but_simple(
    monkeypatch: pytest.MonkeyPatch,
    mock_whisper,
    mock_azure,
) -> None:
    whisper_calls: list[str] = []

    def _spy_transcribe(audio_path: str, **kwargs: object):
        whisper_calls.append(audio_path)
        return {"text": "hello", "segments": [], "language": "en"}

    monkeypatch.setenv("USE_AZURE_SPEECH", "true")
    monkeypatch.setattr(pronunciation, "AZURE_KEY", "fake-key")
    monkeypatch.setattr(pronunciation, "assess_difficulty", lambda _text: "simple")
    monkeypatch.setattr(mock_whisper, "transcribe", _spy_transcribe)
    mock_azure.set_failure(AssertionError("azure should not be called"))

    result = pronunciation.analyze_audio("sample.wav", "hello")

    assert whisper_calls == ["sample.wav"]
    assert result[0] == "hello"
    assert result[1] == 0


@pytest.mark.asyncio
async def test_engine_field_reflects_actual(
    client,
    clean_db: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    del clean_db
    from api.routers import practice

    _seed_practice_session()
    _stub_practice_dependencies(monkeypatch)

    monkeypatch.setattr(practice, "_get_scoring_engine", lambda _text: "azure")
    monkeypatch.setattr(
        practice,
        "analyze_audio_with_whisper",
        lambda *_args: ("heard hello", 90, "", "pass", [], [], {"hello": {"score": 100, "passed": True, "heard": "hello"}}),
    )

    response = await client.post(
        "/practice/audio",
        data={"user_id": "routing-user"},
        files={"audio_file": _audio_payload()},
    )

    assert response.status_code == 200
    assert response.json()["scoring"]["engine"] == "azure"
