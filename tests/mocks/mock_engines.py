from __future__ import annotations

from pathlib import Path
from typing import Any

WhisperResponse = dict[str, Any]
AzureWordScores = dict[str, dict[str, int | bool]]
AzureAnalyzeResult = tuple[int, str, str, list[str], list[tuple[str, str]], AzureWordScores]
PhonemeRecognitionResult = dict[str, list[str] | list[float]]


class MockWhisper:
    def __init__(self, scenarios: dict[str, WhisperResponse] | None = None) -> None:
        self.scenarios = dict(scenarios or {})
        self.default_response: WhisperResponse = {"text": "hello", "segments": [], "language": "en"}
        self._next_failure: Exception | None = None

    def set_failure(self, exc: Exception) -> None:
        self._next_failure = exc

    def transcribe(self, audio_path: str, **kwargs: object) -> WhisperResponse:
        del kwargs
        if self._next_failure is not None:
            exc = self._next_failure
            self._next_failure = None
            raise exc

        filename = Path(audio_path).name
        response = self.scenarios.get(filename, self.default_response)
        merged = dict(self.default_response)
        merged.update(response)
        return merged


class MockAzureScorer:
    def __init__(self) -> None:
        self.response: AzureAnalyzeResult = (0, "", "", [], [], {})
        self._next_failure: Exception | None = None

    def set_score(self, overall: int, word_scores: AzureWordScores) -> None:
        self.response = (
            overall,
            "mock ansi feedback",
            "mock error details",
            [word for word, data in word_scores.items() if not data.get("passed", False)],
            [],
            word_scores,
        )

    def set_failure(self, exc: Exception) -> None:
        self._next_failure = exc

    def analyze(self, audio_path: str, expected_text: str) -> AzureAnalyzeResult:
        del audio_path, expected_text
        if self._next_failure is not None:
            exc = self._next_failure
            self._next_failure = None
            raise exc
        return self.response


class MockPhonemeRecognizer:
    def __init__(self) -> None:
        self.response: PhonemeRecognitionResult = {"phonemes": [], "timestamps": []}
        self._next_failure: Exception | None = None

    def set_phonemes(self, phonemes: list[str]) -> None:
        self.response = {
            "phonemes": phonemes,
            "timestamps": [float(index) for index, _ in enumerate(phonemes)],
        }

    def set_failure(self, exc: Exception) -> None:
        self._next_failure = exc

    def recognize(self, audio_path: str) -> PhonemeRecognitionResult:
        del audio_path
        if self._next_failure is not None:
            exc = self._next_failure
            self._next_failure = None
            raise exc
        return {
            "phonemes": list(self.response["phonemes"]),
            "timestamps": list(self.response["timestamps"]),
        }
