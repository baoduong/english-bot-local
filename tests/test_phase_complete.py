from __future__ import annotations

from pathlib import Path

import pytest
from httpx import AsyncClient

from db.curriculum import activate_phase, add_phase_content, create_curriculum, create_phase, get_active_curriculum
from db.sessions import save_session
from db.users import get_or_create_user


def _make_m4a(tmp_path: Path) -> Path:
    audio_path = tmp_path / "sample.m4a"
    audio_path.write_bytes(b"fake-m4a-data")
    return audio_path


def _seed_phase_with_content(user_id: str, items: list[tuple[int, str]]) -> tuple[int, int]:
    get_or_create_user(user_id, "User")
    curriculum_id = create_curriculum(user_id, "Goal", "Description")
    phase_id = create_phase(curriculum_id, 1, "Theme", [], [])
    activate_phase(phase_id)
    for _content_id, sentence in items:
        add_phase_content(
            phase_id,
            [
                {
                    "sentence": sentence,
                    "target_phonemes": [],
                    "target_words": [],
                    "difficulty_score": 1,
                }
            ],
        )
    return curriculum_id, phase_id


@pytest.mark.usefixtures("clean_db")
async def test_last_item_mastery_signals_phase_complete(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _, phase_id = _seed_phase_with_content("u1", [(1, "hello world")])
    save_session(
        "u1",
        {
            "mode": "curriculum_practice",
            "content_id": 1,
            "current_phase_id": phase_id,
            "curriculum_id": get_active_curriculum("u1")["id"],
            "sentence": "hello world",
            "scores": [],
            "drill_words": [],
            "drill_index": 0,
            "drill_attempts": {},
            "fail_count": 0,
        },
    )

    monkeypatch.setattr("api.routers.practice.analyze_audio_with_whisper", lambda *_args, **_kwargs: (90, "", "", [], [], []))
    monkeypatch.setattr("api.routers.practice.analyze_phonemes_per_word", lambda *_args, **_kwargs: {})
    monkeypatch.setattr("api.routers.practice.get_prosody_analyzer", lambda: type("P", (), {"analyze": lambda self, *_args, **_kwargs: {}})())
    monkeypatch.setattr("api.routers.practice._transcode_to_wav_sync", lambda *_args, **_kwargs: None)
    monkeypatch.setattr("api.routers.practice._build_word_scores", lambda *_args, **_kwargs: ([], [], [], {}))
    monkeypatch.setattr("api.routers.practice._record_practice_metrics_sync", lambda *_args, **_kwargs: None)
    monkeypatch.setattr("api.routers.practice.record_phase_content_attempt", lambda *_args, **_kwargs: 2)
    monkeypatch.setattr("api.routers.practice._advance_to_next_content_sync", lambda *_args, **_kwargs: None)
    monkeypatch.setattr("api.routers.practice._maybe_generate_coaching_sync", lambda **_kwargs: None)

    audio_path = _make_m4a(tmp_path)
    with audio_path.open("rb") as audio_file:
        response = await client.post(
            "/practice/audio",
            data={"user_id": "u1"},
            files={"audio_file": (audio_path.name, audio_file, "audio/mp4")},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["next_action"]["action"] == "phase_complete"
    assert body["session"]["consecutive_passes"] == 2


@pytest.mark.usefixtures("clean_db")
async def test_non_last_item_advances_normally(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _, phase_id = _seed_phase_with_content("u2", [(1, "hello world"), (2, "good morning")])
    save_session(
        "u2",
        {
            "mode": "curriculum_practice",
            "content_id": 1,
            "current_phase_id": phase_id,
            "curriculum_id": get_active_curriculum("u2")["id"],
            "sentence": "hello world",
            "scores": [],
            "drill_words": [],
            "drill_index": 0,
            "drill_attempts": {},
            "fail_count": 0,
        },
    )

    monkeypatch.setattr("api.routers.practice.analyze_audio_with_whisper", lambda *_args, **_kwargs: (90, "", "", [], [], []))
    monkeypatch.setattr("api.routers.practice.analyze_phonemes_per_word", lambda *_args, **_kwargs: {})
    monkeypatch.setattr("api.routers.practice.get_prosody_analyzer", lambda: type("P", (), {"analyze": lambda self, *_args, **_kwargs: {}})())
    monkeypatch.setattr("api.routers.practice._transcode_to_wav_sync", lambda *_args, **_kwargs: None)
    monkeypatch.setattr("api.routers.practice._build_word_scores", lambda *_args, **_kwargs: ([], [], [], {}))
    monkeypatch.setattr("api.routers.practice._record_practice_metrics_sync", lambda *_args, **_kwargs: None)
    monkeypatch.setattr("api.routers.practice.record_phase_content_attempt", lambda *_args, **_kwargs: 2)
    monkeypatch.setattr("api.routers.practice._advance_to_next_content_sync", lambda session: {**session, "sentence": "good morning", "content_id": 2})
    monkeypatch.setattr("api.routers.practice._maybe_generate_coaching_sync", lambda **_kwargs: None)

    audio_path = _make_m4a(tmp_path)
    with audio_path.open("rb") as audio_file:
        response = await client.post(
            "/practice/audio",
            data={"user_id": "u2"},
            files={"audio_file": (audio_path.name, audio_file, "audio/mp4")},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["next_action"]["action"] != "phase_complete"
    assert body["current_item"]["sentence"] == "hello world"
