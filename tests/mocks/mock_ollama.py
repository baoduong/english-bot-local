from __future__ import annotations

import json
from collections import deque
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol, TypeAlias, cast

JSONValue: TypeAlias = str | int | float | bool | None | list["JSONValue"] | dict[str, "JSONValue"]
JSONDict: TypeAlias = dict[str, JSONValue]


class SchemaValidator(Protocol):
    def __call__(self, payload: JSONDict) -> object: ...


class MockOllamaClient:
    scenario_dir: Path
    model: str
    host: str
    timeout_seconds: int
    max_retries: int
    call_history: list[dict[str, str]]
    def __init__(
        self,
        scenario_dir: Path,
        model: str | None = None,
        host: str = "http://localhost:11434",
        timeout_seconds: int = 180,
        max_retries: int = 3,
    ) -> None:
        self.scenario_dir = Path(scenario_dir)
        self.model = model or "mock-ollama"
        self.host = host.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.call_history = []
        self._queued_responses: deque[str] = deque()
        self._queued_failures: deque[Exception] = deque()
        self._default_response_name: str | None = None

    def set_next_response(self, scenario_name: str) -> None:
        self._assert_scenario_exists(scenario_name)
        self._queued_responses.append(scenario_name)

    def set_failure(self, exception: Exception) -> None:
        self._queued_failures.append(exception)

    def set_default_response(self, scenario_name: str) -> None:
        self._assert_scenario_exists(scenario_name)
        self._default_response_name = scenario_name

    def reset(self) -> None:
        self.call_history.clear()
        self._queued_responses.clear()
        self._queued_failures.clear()
        self._default_response_name = None

    def generate_json_sync(
        self,
        prompt: str,
        schema_validator: SchemaValidator | None = None,
        system: str | None = None,
        system_prompt: str = "",
        **_: object,
    ) -> JSONDict:
        effective_system = system if system is not None else system_prompt
        self._record_call(prompt=prompt, system_prompt=effective_system, method="generate_json_sync")
        self._raise_if_failure_queued()

        payload = self._load_response_payload()
        if schema_validator is not None:
            _ = schema_validator(payload)
        return payload

    def generate_text_sync(
        self,
        prompt: str,
        system: str | None = None,
        system_prompt: str = "",
        **_: object,
    ) -> str:
        effective_system = system if system is not None else system_prompt
        self._record_call(prompt=prompt, system_prompt=effective_system, method="generate_text_sync")
        self._raise_if_failure_queued()

        payload = self._load_response_payload()
        return json.dumps(payload, ensure_ascii=False)

    def _record_call(self, prompt: str, system_prompt: str, method: str) -> None:
        self.call_history.append(
            {
                "prompt": prompt,
                "system_prompt": system_prompt,
                "method": method,
                "timestamp": datetime.now(UTC).isoformat(),
            }
        )

    def _raise_if_failure_queued(self) -> None:
        if self._queued_failures:
            raise self._queued_failures.popleft()

    def _load_response_payload(self) -> JSONDict:
        scenario_name = self._queued_responses.popleft() if self._queued_responses else self._default_response_name
        if scenario_name is None:
            raise RuntimeError("MockOllamaClient has no queued or default response configured")
        payload = self._read_scenario_file(scenario_name)
        return deepcopy(payload)

    def _assert_scenario_exists(self, scenario_name: str) -> None:
        scenario_path = self.scenario_dir / f"{scenario_name}.json"
        if not scenario_path.exists():
            raise FileNotFoundError(f"Mock Ollama scenario not found: {scenario_path}")

    def _read_scenario_file(self, scenario_name: str) -> JSONDict:
        scenario_path = self.scenario_dir / f"{scenario_name}.json"
        with scenario_path.open("r", encoding="utf-8") as fixture_file:
            payload = cast(JSONValue, json.load(fixture_file))
        if not isinstance(payload, dict):
            raise ValueError(f"Mock Ollama scenario must contain a JSON object: {scenario_path}")
        return cast(JSONDict, payload)
