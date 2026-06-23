from __future__ import annotations

import json
import time

import pytest

from db.connection import get_db_connection


def _audio_payload(audio_bytes: bytes) -> tuple[str, bytes, str]:
    return ("practice.m4a", audio_bytes, "audio/mp4")


def _seed_practice_context(user_id: str = "user-pending-coaching") -> tuple[str, int]:
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
            ) VALUES (?, 1, 'I like cats', '[]', '[]', 1, 0, NULL, 0, NULL)
            """,
            (content_id,),
        )

        session = {
            "round": 1,
            "max_rounds": 5,
            "sentence": "I like cats",
            "new_word": None,
            "fail_count": 1,
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
        conn.execute(
            "INSERT INTO practice_audio_attempts (audio_hash, user_id, content_id, score, result_json) VALUES (?, ?, ?, ?, ?)",
            ("seed-hash", user_id, content_id, 0, json.dumps({"seed": True})),
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
        index = min(call_counter["count"], len(scores) - 1)
        call_counter["count"] += 1
        score = scores[index]
        return ("i like cats", score, "", "retry", ["cats"], [("cats", "final_consonant")], {"cats": {"score": score, "passed": False, "heard": "cat"}, "like": {"score": 100, "passed": True, "heard": "like"}, "i": {"score": 100, "passed": True, "heard": "i"}})

    monkeypatch.setattr(practice, "analyze_audio_with_whisper", _analyze)
    monkeypatch.setattr(
        practice,
        "analyze_phonemes_per_word",
        lambda *_args: {"cats": {"detected_ipa": "kæ", "phoneme_match_ratio": 0.4, "missing_phonemes": ["ts"]}},
    )

    class _Prosody:
        def analyze(self, *_args):
            return {}

    monkeypatch.setattr(practice, "get_prosody_analyzer", lambda: _Prosody())
    monkeypatch.setattr(practice, "_record_practice_metrics_sync", lambda *_args: None)
    monkeypatch.setattr(practice, "compute_word_difficulty", lambda *_args: 3)
    monkeypatch.setattr(practice, "compute_max_attempts", lambda *_args: 3)
    monkeypatch.setattr(practice, "record_phase_content_attempt", lambda *_args, **_kwargs: 0)
    monkeypatch.setattr(
        practice,
        "_maybe_generate_coaching_sync",
        lambda **kwargs: practice.CoachingHint(
            action="scaffold",
            message_vi="Mình đi qua một từ dễ hơn trước nhé, rồi quay lại từ khó sẽ nhẹ hơn nhiều.",
            scaffold_word="six",
            scaffold_reason_vi="Từ này giữ cụm âm gần giống nhưng ngắn hơn, giúp em ổn định khẩu hình trước.",
            syllables=[],
            articulatory_tip_vi="Mím môi nhẹ, giữ đầu lưỡi thấp và kéo âm /s/ thật gọn trước khi nối sang âm cuối.",
            difficulty=3,
            attempt_count=2,
            max_attempts=3,
        ),
    )
    monkeypatch.setattr(
        practice,
        "_build_word_scores",
        lambda *_args: (
            [
                practice.WordScore(
                    word="I",
                    accuracy=100,
                    color="green",
                    phoneme_similarity=1.0,
                ),
                practice.WordScore(
                    word="like",
                    accuracy=100,
                    color="green",
                    phoneme_similarity=1.0,
                ),
                practice.WordScore(
                    word="cats",
                    accuracy=50,
                    color="red",
                    phoneme_similarity=0.4,
                    tip="tip",
                    error_type="final_consonant",
                    error_label="Final consonant",
                    target_ipa="kæts",
                    practice_examples=["cats"],
                    detected_ipa="kæ",
                    phoneme_match_ratio=0.4,
                    missing_phonemes=["ts"],
                ),
            ],
            ["cats"],
            ["Final consonant"],
            {"cats": {"score": 50, "passed": False}, "like": {"score": 100, "passed": True}, "i": {"score": 100, "passed": True}},
        ),
    )
    return call_counter


async def _post_audio(client, user_id: str, audio_bytes: bytes = b"audio"):
    conn = get_db_connection()
    try:
        conn.execute("DELETE FROM practice_audio_attempts")
        conn.commit()
    finally:
        conn.close()
    return await client.post(
        "/practice/audio",
        data={"user_id": user_id},
        files={"audio_file": _audio_payload(audio_bytes)},
    )


async def _wait_for_pending_coaching(client, user_id: str, timeout_seconds: float = 3.0) -> dict:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        response = await client.get("/practice/coaching/pending", params={"user_id": user_id})
        assert response.status_code == 200
        payload = response.json()
        if payload["coaching"] is not None:
            return payload
        time.sleep(0.05)
    raise AssertionError("Timed out waiting for pending coaching")


async def _wait_for_new_pending_coaching(client, user_id: str, previous_ack_token: str, timeout_seconds: float = 3.0) -> dict:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        response = await client.get("/practice/coaching/pending", params={"user_id": user_id})
        assert response.status_code == 200
        payload = response.json()
        if payload["coaching"] is None:
            time.sleep(0.05)
            continue
        if payload["ack_token"] != previous_ack_token:
            return payload
        time.sleep(0.05)
    raise AssertionError("Timed out waiting for refreshed pending coaching")


@pytest.mark.asyncio
async def test_coaching_produced_via_background(client, clean_db: str, monkeypatch: pytest.MonkeyPatch, mock_ollama) -> None:
    user_id, _ = _seed_practice_context()
    _mock_analysis(monkeypatch, [50])
    mock_ollama.set_next_response("coaching_scaffold")

    response = await _post_audio(client, user_id)

    assert response.status_code == 200
    body = response.json()
    assert body["coaching"] is None

    pending = await _wait_for_pending_coaching(client, user_id)

    assert pending["coaching"] is not None
    assert pending["ack_token"]
    assert pending["content_id"] == 11


@pytest.mark.asyncio
async def test_ack_with_matching_token_clears(client, clean_db: str, monkeypatch: pytest.MonkeyPatch, mock_ollama) -> None:
    user_id, _ = _seed_practice_context()
    _mock_analysis(monkeypatch, [50])
    mock_ollama.set_next_response("coaching_scaffold")

    response = await _post_audio(client, user_id)
    assert response.status_code == 200
    pending = await _wait_for_pending_coaching(client, user_id)

    ack = await client.post(
        "/practice/coaching/ack",
        json={"user_id": user_id, "ack_token": pending["ack_token"]},
    )

    assert ack.status_code == 200
    assert ack.json() == {"cleared": True}

    after_ack = await client.get("/practice/coaching/pending", params={"user_id": user_id})
    assert after_ack.status_code == 200
    assert after_ack.json() == {"coaching": None, "ack_token": None, "content_id": None}


@pytest.mark.asyncio
async def test_ack_with_stale_token_noop(client, clean_db: str, monkeypatch: pytest.MonkeyPatch, mock_ollama) -> None:
    user_id, _ = _seed_practice_context()
    _mock_analysis(monkeypatch, [50, 45])
    mock_ollama.set_next_response("coaching_scaffold")
    mock_ollama.set_next_response("coaching_continue")

    first = await _post_audio(client, user_id, b"audio-one")
    assert first.status_code == 200
    first_pending = await _wait_for_pending_coaching(client, user_id)

    second = await _post_audio(client, user_id, b"audio-two")
    assert second.status_code == 200
    second_pending = await _wait_for_new_pending_coaching(client, user_id, first_pending["ack_token"])

    assert second_pending["ack_token"] != first_pending["ack_token"]

    ack = await client.post(
        "/practice/coaching/ack",
        json={"user_id": user_id, "ack_token": first_pending["ack_token"]},
    )

    assert ack.status_code == 200
    assert ack.json() == {"cleared": False}

    after_ack = await client.get("/practice/coaching/pending", params={"user_id": user_id})
    assert after_ack.status_code == 200
    assert after_ack.json()["ack_token"] == second_pending["ack_token"]
    assert after_ack.json()["coaching"] is not None


@pytest.mark.asyncio
async def test_session_state_excludes_coaching(client, clean_db: str, monkeypatch: pytest.MonkeyPatch, mock_ollama) -> None:
    user_id, _ = _seed_practice_context()
    _mock_analysis(monkeypatch, [50])
    mock_ollama.set_next_response("coaching_scaffold")

    response = await _post_audio(client, user_id)
    assert response.status_code == 200
    await _wait_for_pending_coaching(client, user_id)

    state = await client.get("/practice/session/state", params={"user_id": user_id})

    assert state.status_code == 200
    assert "pending_coaching" not in state.text
    assert "pending_coaching" not in state.json()["session"]
