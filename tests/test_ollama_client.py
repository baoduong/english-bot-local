import pytest
from unittest.mock import patch, MagicMock

from engines.ollama_client import OllamaClient


def test_generate_json_sync_passes_per_call_timeout(monkeypatch):
    """T16 introduced per-call timeout override; verify no collision with instance default."""
    captured_kwargs = {}

    def fake_request(method, url, **kwargs):
        captured_kwargs.update(kwargs)
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = {"message": {"content": '{"result": "ok"}'}}
        return resp

    monkeypatch.setattr("engines.ollama_client.requests.request", fake_request)

    client = OllamaClient(timeout_seconds=180)
    # Pass per-call override — must NOT cause TypeError
    result = client.generate_json_sync(
        "test prompt",
        lambda d: d,
        timeout_seconds=12,
        max_retries=1
    )

    # Verify override was used (timeout=12, not 180)
    assert captured_kwargs["timeout"] == 12
    assert result == {"result": "ok"}


def test_generate_json_sync_default_timeout_when_no_override(monkeypatch):
    """Backward compat: no override → use instance default."""
    captured_kwargs = {}

    def fake_request(method, url, **kwargs):
        captured_kwargs.update(kwargs)
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = {"message": {"content": '{"result": "ok"}'}}
        return resp

    monkeypatch.setattr("engines.ollama_client.requests.request", fake_request)

    client = OllamaClient(timeout_seconds=180)
    result = client.generate_json_sync(
        "test prompt",
        lambda d: d
    )

    # Instance default preserved
    assert captured_kwargs["timeout"] == 180
    assert result == {"result": "ok"}
