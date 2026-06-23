from __future__ import annotations

import importlib
import sys
import types
from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator, Iterator
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest
from httpx import ASGITransport, AsyncClient

if TYPE_CHECKING:
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
else:
    FastAPI = Any
    TestClient = Any


def _stub_module(name: str, **attributes: object) -> None:
    module = types.ModuleType(name)
    for key, value in attributes.items():
        setattr(module, key, value)
    sys.modules[name] = module


def _load_test_app() -> FastAPI:
    def _load_model(*_args: object, **_kwargs: object) -> object:
        return object()

    class _DummyPhonemeRecognizer:
        def load(self) -> None:
            return None

    class _DummyProsodyAnalyzer:
        def load(self) -> None:
            return None

    _stub_module("whisper", load_model=_load_model)
    _stub_module(
        "engines.phoneme_recognizer",
        get_phoneme_recognizer=lambda: _DummyPhonemeRecognizer(),
    )
    _stub_module(
        "engines.prosody_analyzer",
        get_prosody_analyzer=lambda: _DummyProsodyAnalyzer(),
    )

    api_main = importlib.import_module("api.main")
    return api_main.app


@asynccontextmanager
async def _noop_lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    yield


@pytest.fixture(scope="session")
def _app():
    test_app = _load_test_app()
    test_app.router.lifespan_context = _noop_lifespan
    return test_app


@pytest.fixture
def db_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[str]:
    database_path = str(tmp_path / "test.db")
    monkeypatch.setattr("db.connection.DB_NAME", database_path)
    yield database_path


@pytest.fixture
def clean_db(db_path: str) -> str:
    import db.schema as schema

    schema.init_db()
    return db_path


@pytest.fixture
def app(_app: FastAPI, clean_db: str) -> Iterator[FastAPI]:
    from fastapi.testclient import TestClient

    with TestClient(_app) as test_client:
        yield test_client.app


@pytest.fixture(name="client")
async def client_fixture(app: FastAPI, clean_db: str) -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as async_client:
        yield async_client
