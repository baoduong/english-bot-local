from __future__ import annotations

import json
import tempfile
from pathlib import Path
from uuid import uuid4

import pytest

from db.connection import get_db_connection
from db.users import get_or_create_user


def _audio_payload(audio_bytes: bytes = b"medium-audio-bytes") -> tuple[str, bytes, str]:
    return ("practice.m4a", audio_bytes, "audio/mp4")


def _seed_practice_user(*, user_id: str, content_id: int = 11, mode: str = "curriculum_practice") -> int:
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
            ) VALUES (?, 1, 'cat', '[]', '["cat"]', 1, 0, NULL, 0, NULL)
            """,
            (content_id,),
        )
        session = {
            "round": 1,
            "max_rounds": 5,
            "sentence": "cat",
            "new_word": None,
            "fail_count": 0,
            "mode": mode,
            "drill_words": ["cat"] if mode == "word_drill" else [],
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
    return content_id


@pytest.mark.asyncio
async def test_invalid_user_id_returns_400(client, clean_db: str) -> None:
    response = await client.post("/practice/session/start", json={"user_id": "bad-id!!"})

    assert response.status_code == 400
    assert response.json()["detail"]["error_code"] == "INVALID_USER_ID"


@pytest.mark.asyncio
async def test_unknown_user_returns_404(client, clean_db: str) -> None:
    response = await client.get(f"/practice/session/state?user_id={uuid4()}")

    assert response.status_code == 404
    assert response.json()["detail"]["error_code"] == "USER_NOT_FOUND"


@pytest.mark.asyncio
async def test_sample_audio_temp_cleaned(client, clean_db: str, monkeypatch: pytest.MonkeyPatch) -> None:
    user_id = "SampleUsr01"
    get_or_create_user(user_id, "User")

    from api.routers import practice

    created_paths: list[Path] = []

    async def _fake_generate_sample_audio(_text: str, output_path: str) -> bool:
        path = Path(output_path)
        created_paths.append(path)
        path.write_bytes(b"mp3-bytes")
        return True

    monkeypatch.setattr(practice, "generate_sample_audio", _fake_generate_sample_audio)

    before = {path.name for path in Path(tempfile.gettempdir()).glob("*_teacher_sample.mp3")}
    for _ in range(2):
        response = await client.get(f"/practice/audio/sample?user_id={user_id}&expected_text=hello")
        assert response.status_code == 200
        assert response.content == b"mp3-bytes"
    after = {path.name for path in Path(tempfile.gettempdir()).glob("*_teacher_sample.mp3")}

    assert after == before
    assert created_paths
    assert all(not path.exists() for path in created_paths)


@pytest.mark.asyncio
async def test_drill_phoneme_gate_skipped_low_count(client, clean_db: str, monkeypatch: pytest.MonkeyPatch) -> None:
    user_id = "DrillUser01"
    _seed_practice_user(user_id=user_id, mode="word_drill")

    from api.routers import practice

    monkeypatch.setattr(practice, "_transcode_to_wav_sync", lambda *_args: None)
    monkeypatch.setattr(
        practice,
        "analyze_audio_with_whisper",
        lambda *_args: ("cat", 82, "", "pass", [], [], {"cat": {"score": 100, "passed": True, "heard": "cat"}}),
    )
    monkeypatch.setattr(
        practice,
        "analyze_phonemes_per_word",
        lambda *_args: {"cat": {"phoneme_match_ratio": 0.2, "detected_ipa": "k"}},
    )

    class _Prosody:
        def analyze(self, *_args):
            return {}

    monkeypatch.setattr(practice, "get_prosody_analyzer", lambda: _Prosody())
    monkeypatch.setattr(practice, "_record_practice_metrics_sync", lambda *_args: None)
    monkeypatch.setattr(practice, "_maybe_generate_coaching_sync", lambda **_kwargs: None)

    response = await client.post(
        "/practice/audio",
        data={"user_id": user_id},
        files={"audio_file": _audio_payload(b"drill-low-phoneme")},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["next_action"]["action"] == "pass"
    assert body["session"]["mode"] == "curriculum_practice"
