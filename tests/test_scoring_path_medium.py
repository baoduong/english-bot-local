from __future__ import annotations

import pytest


def _audio_payload() -> tuple[str, bytes, str]:
    return ("practice.m4a", b"medium-audio-bytes", "audio/mp4")


@pytest.mark.asyncio
async def test_scratch_score_returns_recognized_transcript(client, clean_db: str, monkeypatch: pytest.MonkeyPatch) -> None:
    del clean_db
    from api.routers import practice

    monkeypatch.setattr(practice, "_require_user_sync", lambda _uid: {"id": "u1"})
    monkeypatch.setattr(practice, "_transcode_to_wav_sync", lambda *_args: None)
    monkeypatch.setattr(
        practice,
        "analyze_audio_with_whisper",
        lambda *_args: (
            "hello there",
            88,
            "ansi",
            "feedback",
            [],
            [],
            {"hello": {"score": 100, "passed": True, "heard": "hello"}},
        ),
    )
    monkeypatch.setattr(practice, "analyze_phonemes_per_word", lambda *_args: {})

    response = await client.post(
        "/practice/scratch-score",
        data={"user_id": "u1", "target_text": "expected words"},
        files={"audio_file": _audio_payload()},
    )

    assert response.status_code == 200
    assert response.json()["transcript"] == "hello there"


def test_build_word_scores_uses_accuracy_thresholds_for_color() -> None:
    from api.routers import practice

    analysis = (
        "cat",
        73,
        "ansi",
        "feedback",
        [],
        [],
        {"cat": {"score": 73, "passed": False, "heard": "cat"}},
    )

    word_scores, weak_words, error_labels, score_map = practice._build_word_scores("cat", analysis, {})

    assert word_scores[0].accuracy == 73
    assert word_scores[0].color == "yellow"
    assert weak_words == ["cat"]
    assert error_labels
    assert score_map["cat"]["score"] == 73


def test_build_word_scores_uses_real_heard_word_for_phoneme_similarity() -> None:
    from api.routers import practice

    analysis = (
        "cot",
        50,
        "ansi",
        "feedback",
        ["cat"],
        [("cat", "general")],
        {"cat": {"score": 50, "passed": False, "heard": "cot"}},
    )

    word_scores, weak_words, error_labels, _score_map = practice._build_word_scores("cat", analysis, {})

    assert word_scores[0].phoneme_similarity < 1.0
    assert word_scores[0].phoneme_similarity == pytest.approx(practice.phoneme_similarity("cot", "cat"))
    assert weak_words == ["cat"]
    assert error_labels == [practice.ERROR_TYPE_LABELS["general"]]
