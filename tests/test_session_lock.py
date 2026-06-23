from __future__ import annotations

import asyncio
import time

import pytest

from db.sessions import load_all_sessions, save_session
from api.locks import _user_locks
from db.users import get_or_create_user


def _audio_payload() -> tuple[str, bytes, str]:
    return ("practice.m4a", b"fake-audio-bytes", "audio/mp4")


@pytest.mark.asyncio
async def test_same_user_serialized(client, monkeypatch: pytest.MonkeyPatch) -> None:
    from api.routers import practice

    _user_locks.clear()
    user_id = "lock-same-user"
    get_or_create_user(user_id, "User")
    save_session(
        user_id,
        {
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
            "started_at": "2026-06-23T00:00:00",
            "scores": [],
            "curriculum_id": 1,
            "current_phase_id": 1,
            "current_phase_number": 1,
            "phase_theme": "theme",
            "phase_total_content": 1,
            "phase_mastered_count": 0,
            "content_id": 7,
        },
    )

    monkeypatch.setattr(practice, "_require_user_sync", lambda uid: {"id": uid})
    monkeypatch.setattr(practice, "_transcode_to_wav_sync", lambda *_args: None)
    monkeypatch.setattr(practice, "analyze_audio_with_whisper", lambda *_args: ("", 50, "", "retry", [], [], {}))
    monkeypatch.setattr(practice, "analyze_phonemes_per_word", lambda *_args: {})

    class _Prosody:
        def analyze(self, *_args):
            return {}

    monkeypatch.setattr(practice, "get_prosody_analyzer", lambda: _Prosody())
    monkeypatch.setattr(practice, "_record_practice_metrics_sync", lambda *_args: None)
    monkeypatch.setattr(practice, "record_phase_content_attempt", lambda *_args: 0)
    monkeypatch.setattr(practice, "get_phase_progress", lambda *_args: {"mastered": 0, "total": 1})
    monkeypatch.setattr(practice, "_maybe_generate_coaching_sync", lambda **_kwargs: None)

    original_get_user_lock = practice.get_user_lock

    async def instrumented_get_user_lock(uid: str):
        lock = await original_get_user_lock(uid)
        original_acquire = lock.acquire

        async def delayed_acquire() -> bool:
            await asyncio.sleep(0.05)
            return await original_acquire()

        monkeypatch.setattr(lock, "acquire", delayed_acquire, raising=False)
        return lock

    monkeypatch.setattr(practice, "get_user_lock", instrumented_get_user_lock)

    async def do_request() -> None:
        response = await client.post(
            "/practice/audio",
            data={"user_id": user_id},
            files={"audio_file": _audio_payload()},
        )
        assert response.status_code == 200

    await asyncio.gather(do_request(), do_request())

    session = load_all_sessions()[user_id]
    assert session["fail_count"] == 2
    assert session["scores"] == [50, 50]


@pytest.mark.asyncio
async def test_different_users_parallel(client, monkeypatch: pytest.MonkeyPatch) -> None:
    from api.routers import practice

    _user_locks.clear()
    for user_id in ("lock-user-a", "lock-user-b"):
        get_or_create_user(user_id, "User")
        save_session(
            user_id,
            {
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
                "started_at": "2026-06-23T00:00:00",
                "scores": [],
                "curriculum_id": 1,
                "current_phase_id": 1,
                "current_phase_number": 1,
                "phase_theme": "theme",
                "phase_total_content": 1,
                "phase_mastered_count": 0,
                "content_id": 7,
            },
        )

    monkeypatch.setattr(practice, "_require_user_sync", lambda uid: {"id": uid})
    monkeypatch.setattr(practice, "_load_session_sync", lambda uid: load_all_sessions()[uid])
    monkeypatch.setattr(practice, "_transcode_to_wav_sync", lambda *_args: None)

    def slow_analyze(_wav_path: str, _expected: str):
        time.sleep(0.2)
        return ("", 50, "", "retry", [], [], {})

    monkeypatch.setattr(practice, "analyze_audio_with_whisper", slow_analyze)
    monkeypatch.setattr(practice, "analyze_phonemes_per_word", lambda *_args: {})

    class _Prosody:
        def analyze(self, *_args):
            return {}

    monkeypatch.setattr(practice, "get_prosody_analyzer", lambda: _Prosody())
    monkeypatch.setattr(practice, "_record_practice_metrics_sync", lambda *_args: None)
    monkeypatch.setattr(practice, "record_phase_content_attempt", lambda *_args: 0)
    monkeypatch.setattr(practice, "get_phase_progress", lambda *_args: {"mastered": 0, "total": 1})
    monkeypatch.setattr(practice, "_maybe_generate_coaching_sync", lambda **_kwargs: None)

    async def do_request(user_id: str) -> None:
        response = await client.post(
            "/practice/audio",
            data={"user_id": user_id},
            files={"audio_file": _audio_payload()},
        )
        assert response.status_code == 200

    started = time.perf_counter()
    await asyncio.gather(do_request("lock-user-a"), do_request("lock-user-b"))
    elapsed = time.perf_counter() - started

    assert elapsed < 0.35
