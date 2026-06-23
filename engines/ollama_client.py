import asyncio
import json
import os
import time
from typing import Any, Callable

import requests


class OllamaUnavailableError(RuntimeError):
    """Raised when Ollama service is unreachable or all retries exhausted."""


class OllamaSchemaError(ValueError):
    """Raised when Ollama returns valid JSON but schema validation fails after retries."""


class OllamaClient:
    def __init__(
        self,
        model: str | None = None,
        host: str = "http://localhost:11434",
        timeout_seconds: int = 180,
        max_retries: int = 3,
    ):
        self.model = model or os.getenv("OLLAMA_MODEL", "gemma4:31b-cloud")
        self.host = host.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries

    @property
    def _chat_url(self) -> str:
        return f"{self.host}/api/chat"

    @property
    def _generate_url(self) -> str:
        return f"{self.host}/api/generate"

    @property
    def _tags_url(self) -> str:
        return f"{self.host}/api/tags"

    def _retry_sleep(self, attempt: int) -> None:
        delay = 2 ** (attempt - 1)
        time.sleep(delay)

    def _request_with_retries(self, method: str, url: str, **kwargs: Any) -> dict[str, Any]:
        last_error: Exception | None = None

        for attempt in range(1, self.max_retries + 1):
            try:
                response = requests.request(method, url, timeout=self.timeout_seconds, **kwargs)
                response.raise_for_status()
                if not response.text or not response.text.strip():
                    raise ValueError(f"Ollama returned empty response body (HTTP {response.status_code})")
                print(f"[OllamaClient] HTTP {response.status_code}, body length={len(response.text)}, first 200 chars: {response.text[:200]}")
                return response.json()
            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as exc:
                last_error = exc
                if attempt < self.max_retries:
                    print(f"[OllamaClient] Retry {attempt}/{self.max_retries}: {exc}")
                    self._retry_sleep(attempt)
                    continue
                raise OllamaUnavailableError(
                    f"Ollama unavailable after {self.max_retries} retries: {exc}"
                ) from exc
            except requests.exceptions.RequestException as exc:
                raise OllamaUnavailableError(f"Ollama request failed: {exc}") from exc
            except ValueError as exc:
                last_error = exc
                if attempt < self.max_retries:
                    print(f"[OllamaClient] Retry {attempt}/{self.max_retries}: {exc}")
                    self._retry_sleep(attempt)
                    continue
                raise OllamaUnavailableError(
                    f"Invalid JSON response from Ollama after {self.max_retries} retries: {exc}"
                ) from exc

        raise OllamaUnavailableError(
            f"Ollama unavailable after {self.max_retries} retries: {last_error}"
        )

    def chat_sync(self, messages: list[dict[str, Any]], **opts: Any) -> str:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "stream": False,
        }
        payload.update(opts)

        body = self._request_with_retries("post", self._chat_url, json=payload)

        try:
            content = body["message"]["content"]
        except (KeyError, TypeError) as exc:
            raise OllamaUnavailableError(
                "Ollama chat response missing message.content"
            ) from exc

        if not isinstance(content, str):
            raise OllamaUnavailableError("Ollama chat response content is not a string")

        return content

    async def chat(self, messages: list[dict[str, Any]], **opts: Any) -> str:
        return await asyncio.to_thread(self.chat_sync, messages, **opts)

    def generate_json_sync(
        self,
        prompt: str,
        schema_validator: Callable[[dict[str, Any]], Any],
        system: str | None = None,
        **opts: Any,
    ) -> dict[str, Any]:
        last_schema_error: Exception | None = None
        last_connection_error: Exception | None = None
        timeout_seconds = opts.pop("timeout_seconds", None)
        max_retries = opts.pop("max_retries", None)
        retries = max_retries if max_retries is not None else self.max_retries
        timeout = timeout_seconds if timeout_seconds is not None else self.timeout_seconds

        for attempt in range(1, retries + 1):
            messages: list[dict[str, Any]] = []
            if system is not None:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})

            payload: dict[str, Any] = {
                "model": self.model,
                "messages": messages,
                "format": "json",
                "stream": False,
            }

            try:
                body = self._request_with_retries("post", self._chat_url, json=payload, timeout=timeout)
            except OllamaUnavailableError as exc:
                last_connection_error = exc
                if attempt < retries:
                    print(f"[OllamaClient] Retry {attempt}/{retries}: {exc}")
                    self._retry_sleep(attempt)
                    continue
                raise

            try:
                raw = body["message"]["content"]
            except (KeyError, TypeError):
                raw = None

            if not isinstance(raw, str) or not raw.strip():
                err = OllamaSchemaError(f"Ollama JSON response empty or missing. Body keys: {list(body.keys()) if isinstance(body, dict) else type(body)}")
                last_schema_error = err
                if attempt < retries:
                    print(f"[OllamaClient] Retry {attempt}/{retries}: {err}")
                    self._retry_sleep(attempt)
                    continue
                raise err

            print(f"[OllamaClient] Raw response ({len(raw)} chars): {raw[:300]}")

            # Strip markdown code fences nếu model wrap JSON trong ```json ... ```
            stripped = raw.strip()
            if stripped.startswith("```"):
                # Bỏ dòng đầu (```json hoặc ```) và dòng cuối (```)
                lines = stripped.split("\n")
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines and lines[-1].strip() == "```":
                    lines = lines[:-1]
                stripped = "\n".join(lines)

            try:
                parsed = json.loads(stripped)
            except json.JSONDecodeError as exc:
                last_schema_error = exc
                if attempt < retries:
                    print(f"[OllamaClient] Retry {attempt}/{retries}: {exc}")
                    self._retry_sleep(attempt)
                    continue
                raise OllamaSchemaError(
                    f"Failed to parse Ollama JSON response after {retries} retries: {exc}"
                ) from exc

            if not isinstance(parsed, dict):
                err = OllamaSchemaError("Ollama JSON response is not an object")
                last_schema_error = err
                if attempt < retries:
                    print(f"[OllamaClient] Retry {attempt}/{retries}: {err}")
                    self._retry_sleep(attempt)
                    continue
                raise err

            try:
                schema_validator(parsed)
                return parsed
            except ValueError as exc:
                last_schema_error = exc
                if attempt < retries:
                    print(f"[OllamaClient] Retry {attempt}/{retries}: {exc}")
                    self._retry_sleep(attempt)
                    continue
                raise OllamaSchemaError(
                    f"Schema validation failed after {retries} retries: {exc}"
                ) from exc

        if last_schema_error is not None:
            if isinstance(last_schema_error, OllamaSchemaError):
                raise last_schema_error
            raise OllamaSchemaError(
                f"Schema validation failed after {retries} retries: {last_schema_error}"
            ) from last_schema_error

        if last_connection_error is not None:
            if isinstance(last_connection_error, OllamaUnavailableError):
                raise last_connection_error
            raise OllamaUnavailableError(
                f"Ollama unavailable after {retries} retries: {last_connection_error}"
            ) from last_connection_error

        raise OllamaUnavailableError("Ollama JSON generation failed with unknown error")

    async def generate_json(
        self,
        prompt: str,
        schema_validator: Callable[[dict[str, Any]], Any],
        system: str | None = None,
        **opts: Any,
    ) -> dict[str, Any]:
        return await asyncio.to_thread(
            self.generate_json_sync,
            prompt,
            schema_validator,
            system,
            **opts,
        )

    def is_available(self) -> bool:
        try:
            response = requests.get(self._tags_url, timeout=5)
            return response.status_code == 200
        except requests.exceptions.RequestException:
            return False
