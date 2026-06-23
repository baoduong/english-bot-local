from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.mocks.mock_ollama import MockOllamaClient


def _fixture_path(name: str) -> Path:
    return Path("tests/fixtures/ollama_responses") / f"{name}.json"


def _load_fixture(name: str) -> dict:
    return json.loads(_fixture_path(name).read_text(encoding="utf-8"))


def test_queue_returns_fixture() -> None:
    mock = MockOllamaClient(scenario_dir=Path("tests/fixtures/ollama_responses"))
    mock.set_next_response("coaching_scaffold")

    response = mock.generate_json_sync(prompt="Coach this learner")

    assert response == _load_fixture("coaching_scaffold")


def test_failure_raises() -> None:
    mock = MockOllamaClient(scenario_dir=Path("tests/fixtures/ollama_responses"))
    mock.set_failure(TimeoutError("mock timeout"))

    with pytest.raises(TimeoutError, match="mock timeout"):
        mock.generate_json_sync(prompt="This call should fail")


def test_call_history_records() -> None:
    mock = MockOllamaClient(scenario_dir=Path("tests/fixtures/ollama_responses"))
    mock.set_default_response("coaching_continue")

    prompts = ["prompt one", "prompt two", "prompt three"]

    for index, prompt in enumerate(prompts, start=1):
        mock.generate_json_sync(
            prompt=prompt,
            system_prompt=f"system {index}",
        )

    assert len(mock.call_history) == 3
    assert [entry["prompt"] for entry in mock.call_history] == prompts
    assert [entry["system_prompt"] for entry in mock.call_history] == [
        "system 1",
        "system 2",
        "system 3",
    ]
    assert all(entry["timestamp"] for entry in mock.call_history)
