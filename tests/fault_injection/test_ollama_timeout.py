from __future__ import annotations

import asyncio
import json
import time
from typing import TYPE_CHECKING
from typing import TypedDict
from typing import cast

import pytest
from httpx import Response

from db.connection import get_db_connection

from tests.fixtures.audio_paths import AUDIO_FIXTURES

if TYPE_CHECKING:
    from httpx import AsyncClient
    from tests.mocks.mock_ollama import MockOllamaClient


class ScoringPayload(TypedDict):
    overall_score: int


class PracticeAudioPayload(TypedDict):
    coaching: object | None
    scoring: ScoringPayload


def _audio_payload_from_fixture(name: str = "fix") -> tuple[str, bytes, str]:
    audio_path = AUDIO_FIXTURES[name]
    return (audio_path.name, audio_path.read_bytes(), "audio/mp4")


def _seed_practice_context(user_id: str) -> tuple[str, int]:
    content_id = 21
    conn = get_db_connection()
    try:
        _ = conn.execute(
            """
            INSERT INTO users (
                user_id, username, streak_count, last_study_date, current_level, total_sessions,
                created_at, onboarding_completed_at, active_curriculum_id, interface_language
            ) VALUES (?, ?, 0, NULL, 1, 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, 1, 'vi')
            """,
            (user_id, "Fault Injection User"),
        )
        _ = conn.execute(
            """
            INSERT INTO curriculums (
                id, user_id, goal_title, goal_description, status, current_phase_number, interface_language
            ) VALUES (1, ?, 'Goal', 'Goal description', 'active', 1, 'vi')
            """,
            (user_id,),
        )
        _ = conn.execute(
            """
            INSERT INTO phases (
                id, curriculum_id, phase_number, theme, vocabulary, milestones, status
            ) VALUES (1, 1, 1, 'Repairs', '[]', '[]', 'active')
            """
        )
        _ = conn.execute(
            """
            INSERT INTO phase_content (
                id, phase_id, sentence, target_phonemes, target_words, difficulty_score,
                attempt_count, last_score, consecutive_passes, mastered_at
            ) VALUES (?, 1, 'fix', '[]', '["fix"]', 1, 0, NULL, 0, NULL)
            """,
            (content_id,),
        )

        session: dict[str, object] = {
            "round": 1,
            "max_rounds": 5,
            "sentence": "fix",
            "new_word": None,
            "fail_count": 2,
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
            "phase_theme": "Repairs",
            "phase_total_content": 1,
            "phase_mastered_count": 0,
            "content_id": content_id,
        }
        _ = conn.execute(
            "INSERT INTO active_sessions (user_id, session_data) VALUES (?, ?)",
            (user_id, json.dumps(session)),
        )
        conn.commit()
    finally:
        conn.close()
    return user_id, content_id


def _configure_fast_scoring(monkeypatch: pytest.MonkeyPatch) -> None:
    from api.routers import practice

    def _noop_transcode(*_args: object) -> None:
        return None

    def _analyze_audio(*_args: object) -> tuple[int, str, str, list[str], list[tuple[str, str]], dict[str, dict[str, int | bool]]]:
        return (
            90,
            "",
            "Scoring completed.",
            [],
            [("fix", "final_consonant")],
            {"fix": {"score": 70, "passed": False}},
        )

    def _phoneme_analysis(*_args: object) -> dict[str, dict[str, str | float | list[str]]]:
        return {"fix": {"detected_ipa": "fɪ", "phoneme_match_ratio": 0.5, "missing_phonemes": ["ks"]}}

    def _difficulty(*_args: object) -> int:
        return 3

    def _record_attempt(*_args: object, **_kwargs: object) -> int:
        return 1

    monkeypatch.setattr(practice, "_transcode_to_wav_sync", _noop_transcode)
    monkeypatch.setattr(
        practice,
        "analyze_audio_with_whisper",
        _analyze_audio,
    )
    monkeypatch.setattr(practice, "analyze_phonemes_per_word", _phoneme_analysis)

    class _Prosody:
        def analyze(self, *_args: object) -> dict[str, object]:
            return {}

    monkeypatch.setattr(practice, "get_prosody_analyzer", lambda: _Prosody())
    monkeypatch.setattr(practice, "_record_practice_metrics_sync", _noop_transcode)
    monkeypatch.setattr(practice, "compute_word_difficulty", _difficulty)
    monkeypatch.setattr(practice, "compute_max_attempts", _difficulty)
    monkeypatch.setattr(practice, "record_phase_content_attempt", _record_attempt)


async def _post_audio(client: AsyncClient, user_id: str) -> Response:
    return await client.post(
        "/practice/audio",
        data={"user_id": user_id},
        files={"audio_file": ("practice.m4a", _audio_payload_from_fixture()[1], "audio/mp4")},
    )


@pytest.mark.asyncio
@pytest.mark.fault_injection
async def test_scoring_succeeds_on_ollama_timeout(
    client: AsyncClient,
    clean_db: str,
    monkeypatch: pytest.MonkeyPatch,
    mock_ollama: MockOllamaClient,
) -> None:
    del clean_db
    user_id, _ = _seed_practice_context("user-ollama-timeout")
    _configure_fast_scoring(monkeypatch)
    mock_ollama.set_failure(asyncio.TimeoutError("Ollama connection timeout"))

    response = await _post_audio(client, user_id)

    assert response.status_code == 200, response.text
    data = cast(PracticeAudioPayload, response.json())
    assert data["coaching"] is None
    assert "scoring" in data
    assert data["scoring"]["overall_score"] == 90
    assert data["scoring"]["overall_score"] > 0

    await asyncio.sleep(0.1)
    pending = await client.get("/practice/coaching/pending", params={"user_id": user_id})
    assert pending.status_code == 200
    assert pending.json() == {"coaching": None, "ack_token": None, "content_id": None}


@pytest.mark.asyncio
@pytest.mark.fault_injection
async def test_scoring_not_blocked_by_slow_ollama(
    client: AsyncClient,
    clean_db: str,
    monkeypatch: pytest.MonkeyPatch,
    mock_ollama: MockOllamaClient,
) -> None:
    del clean_db
    user_id, _ = _seed_practice_context("user-ollama-slow")
    _configure_fast_scoring(monkeypatch)

    def _slow_failure(*_args: object, **_kwargs: object) -> None:
        time.sleep(25)
        raise asyncio.TimeoutError("Ollama connection timeout")

    monkeypatch.setattr(mock_ollama, "generate_json_sync", _slow_failure)

    start = time.perf_counter()
    response = await _post_audio(client, user_id)
    elapsed = time.perf_counter() - start

    assert response.status_code == 200, response.text
    assert elapsed < 5.0
    data = cast(PracticeAudioPayload, response.json())
    assert data["coaching"] is None
    assert data["scoring"]["overall_score"] == 90
