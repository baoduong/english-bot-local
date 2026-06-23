from __future__ import annotations

from pathlib import Path

import pytest
from httpx import AsyncClient

from db.users import get_or_create_user
from db.sessions import save_session


def _make_m4a(tmp_path: Path) -> Path:
    audio_path = tmp_path / "sample.m4a"
    audio_path.write_bytes(b"fake-m4a-data")
    return audio_path


@pytest.mark.usefixtures("clean_db")
async def test_none_content_id_no_crash(client: AsyncClient, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    calls: list[tuple[int, int, bool]] = []

    async def _fake_to_thread(func, *args, **kwargs):  # type: ignore[no-untyped-def]
        if func.__name__ == "record_phase_content_attempt":
            calls.append((args[0], args[1], args[2]))
            return 1
        return func(*args, **kwargs)

    monkeypatch.setattr("api.routers.practice.asyncio.to_thread", _fake_to_thread)
    monkeypatch.setattr("api.routers.practice.analyze_audio_with_whisper", lambda *_args, **_kwargs: ("hello world", 85, "", "", [], [], []))
    monkeypatch.setattr("api.routers.practice.analyze_phonemes_per_word", lambda *_args, **_kwargs: {})
    monkeypatch.setattr("api.routers.practice.get_prosody_analyzer", lambda: type("P", (), {"analyze": lambda self, *_args, **_kwargs: {}})())
    monkeypatch.setattr("api.routers.practice._transcode_to_wav_sync", lambda *_args, **_kwargs: None)
    monkeypatch.setattr("api.routers.practice._build_word_scores", lambda *_args, **_kwargs: ([], [], [], {}))
    monkeypatch.setattr("api.routers.practice._record_practice_metrics_sync", lambda *_args, **_kwargs: None)
    monkeypatch.setattr("api.routers.practice.generate_chunked_audio", lambda *_args, **_kwargs: b"audio")
    monkeypatch.setattr("api.routers.practice.generate_sample_audio", lambda *_args, **_kwargs: None)

    session = {
        "mode": "curriculum_practice",
        "content_id": None,
        "current_phase_id": 1,
        "sentence": "hello world",
        "scores": [],
        "drill_words": [],
        "drill_index": 0,
        "drill_attempts": {},
        "fail_count": 0,
    }
    get_or_create_user("validuser1", "User")
    save_session("validuser1", session)

    audio_path = _make_m4a(tmp_path)
    with audio_path.open("rb") as audio_file:
        response = await client.post(
            "/practice/audio",
            data={"user_id": "validuser1"},
            files={"audio_file": (audio_path.name, audio_file, "audio/mp4")},
        )

    assert response.status_code == 200
    assert calls == []


@pytest.mark.usefixtures("clean_db")
async def test_invalid_content_id_returns_400(client: AsyncClient, tmp_path: Path) -> None:
    session = {
        "mode": "curriculum_practice",
        "content_id": 1,
        "scores": [],
        "drill_words": [],
        "drill_index": 0,
        "drill_attempts": {},
        "fail_count": 0,
    }
    get_or_create_user("validuser2", "User")
    save_session("validuser2", session)

    audio_path = _make_m4a(tmp_path)
    with audio_path.open("rb") as audio_file:
        response = await client.post(
            "/practice/audio",
            data={"user_id": "validuser2", "content_id": "abc"},
            files={"audio_file": (audio_path.name, audio_file, "audio/mp4")},
        )

    assert response.status_code == 400
    body = response.json()
    assert body["detail"]["error_code"] == "INVALID_CONTENT_ID"
