from __future__ import annotations

import pytest

from tests.mocks.mock_engines import MockAzureScorer, MockPhonemeRecognizer, MockWhisper


def test_whisper_returns_scripted_transcript() -> None:
    mock = MockWhisper(
        scenarios={
            "fix_correct.wav": {
                "text": "fix",
                "segments": [{"words": [{"word": "fix", "probability": 0.95}]}],
            }
        }
    )

    result = mock.transcribe("/tmp/fix_correct.wav", word_timestamps=True, language="en")

    assert result["text"] == "fix"
    assert result["language"] == "en"


def test_whisper_failure_raises() -> None:
    mock = MockWhisper()
    mock.set_failure(RuntimeError("boom"))

    with pytest.raises(RuntimeError, match="boom"):
        mock.transcribe("/tmp/fix_correct.wav")


def test_azure_returns_configured_score() -> None:
    mock = MockAzureScorer()
    mock.set_score(85, {"fix": {"score": 90, "passed": True}})

    result = mock.analyze("/tmp/fix_correct.wav", "fix")

    assert result[0] == "mock transcript"
    assert result[1] == 85
    assert result[6]["fix"]["score"] == 90


def test_azure_failure_raises() -> None:
    mock = MockAzureScorer()
    mock.set_failure(ConnectionError("offline"))

    with pytest.raises(ConnectionError, match="offline"):
        mock.analyze("/tmp/fix_correct.wav", "fix")


def test_phoneme_returns_configured() -> None:
    mock = MockPhonemeRecognizer()
    mock.set_phonemes(["f", "ɪ", "k", "s"])

    result = mock.recognize("/tmp/fix_correct.wav")

    assert result["phonemes"] == ["f", "ɪ", "k", "s"]
    assert result["timestamps"] == [0.0, 1.0, 2.0, 3.0]


def test_phoneme_failure_raises() -> None:
    mock = MockPhonemeRecognizer()
    mock.set_failure(RuntimeError("phoneme failed"))

    with pytest.raises(RuntimeError, match="phoneme failed"):
        mock.recognize("/tmp/fix_correct.wav")
