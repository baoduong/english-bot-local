"""
API configuration and logging setup.

Reads settings from environment variables (populated from .env via python-dotenv
or set directly in the launchd plist EnvironmentVariables dict).

Usage:
    from api.config import settings, configure_logging

    configure_logging()          # call once at process startup
    logger = logging.getLogger(__name__)
"""
from __future__ import annotations

import logging
import logging.handlers
import os
from pathlib import Path

# ─── Project root (one level above this file: api/config.py → project root) ──
PROJECT_ROOT = Path(__file__).resolve().parent.parent


# ─── Settings ─────────────────────────────────────────────────────────────────

class Settings:
    """
    Flat settings object backed by os.getenv().
    All values are read at import time so that misconfigured environments
    fail loudly at startup rather than mid-request.
    """

    # Network
    api_host: str = os.getenv("API_HOST", "0.0.0.0")
    api_port: int = int(os.getenv("API_PORT", "8000"))

    # Storage
    log_path: Path = Path(os.getenv("LOG_PATH", str(PROJECT_ROOT / "logs" / "api.log")))
    db_path: Path = Path(os.getenv("DB_PATH", str(PROJECT_ROOT / "english_learner.db")))

    # AI
    ollama_model: str = os.getenv("OLLAMA_MODEL", "gemma4:31b-cloud")

    # Azure Speech (optional — forwarded from existing .env)
    use_azure_speech: bool = os.getenv("USE_AZURE_SPEECH", "false").lower() == "true"
    azure_speech_key: str = os.getenv("AZURE_SPEECH_KEY", "")
    azure_speech_region: str = os.getenv("AZURE_SPEECH_REGION", "southeastasia")

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"Settings(host={self.api_host}:{self.api_port}, "
            f"db={self.db_path}, log={self.log_path}, "
            f"model={self.ollama_model})"
        )


settings = Settings()


# ─── Logging ──────────────────────────────────────────────────────────────────

_LOG_FORMAT_JSON = (
    '{"time":"%(asctime)s","level":"%(levelname)s",'
    '"logger":"%(name)s","message":%(message)s}'
)

# Fallback plain format for early-startup console messages
_LOG_FORMAT_PLAIN = "%(asctime)s  %(levelname)-8s  %(name)s  %(message)s"
_DATE_FORMAT = "%Y-%m-%dT%H:%M:%S"


class _JsonMessageFormatter(logging.Formatter):
    """
    Wraps the log record's message in JSON-safe double-quotes so that
    the outer JSON template remains valid even when the message contains
    special characters.

    Example output:
        {"time":"2026-06-17T10:00:00","level":"INFO",
         "logger":"api.main","message":"[startup] DB connection verified."}
    """

    def format(self, record: logging.LogRecord) -> str:
        # Let the base class interpolate %(message)s
        record.message = record.getMessage()
        # Escape backslashes and double-quotes inside the message text
        safe_msg = record.message.replace("\\", "\\\\").replace('"', '\\"')
        record.message = f'"{safe_msg}"'
        # Use the template from datefmt / fmt
        record.asctime = self.formatTime(record, self.datefmt)
        return self._style._fmt % record.__dict__


def configure_logging(level: int = logging.INFO) -> None:
    """
    Configure root logger with:
      - RotatingFileHandler  → JSON lines to LOG_PATH (10 MB × 5 backups)
      - StreamHandler        → plain text to stdout (useful when running interactively)

    Safe to call multiple times (idempotent via handler-type check).
    """
    root = logging.getLogger()
    if root.handlers:
        # Already configured — skip to avoid duplicate handlers on reload
        return

    root.setLevel(level)

    # ── File handler (JSON, rotating) ────────────────────────────────────────
    log_file = settings.log_path
    log_file.parent.mkdir(parents=True, exist_ok=True)

    file_handler = logging.handlers.RotatingFileHandler(
        filename=log_file,
        maxBytes=10 * 1024 * 1024,   # 10 MB
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(
        _JsonMessageFormatter(fmt=_LOG_FORMAT_JSON, datefmt=_DATE_FORMAT)
    )

    # ── Console handler (plain text) ─────────────────────────────────────────
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(
        logging.Formatter(fmt=_LOG_FORMAT_PLAIN, datefmt=_DATE_FORMAT)
    )

    root.addHandler(file_handler)
    root.addHandler(console_handler)

    root.info(
        "Logging initialised — file=%s level=%s",
        log_file,
        logging.getLevelName(level),
    )
