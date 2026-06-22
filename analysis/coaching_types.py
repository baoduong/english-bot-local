from __future__ import annotations

import re
from typing import Any


_VALID_ACTIONS = {"continue", "scaffold", "break_down", "skip_with_note"}
_ENGLISH_RE = re.compile(r"^[A-Za-z][A-Za-z\s'-]*$")


def _require_text(data: dict[str, Any], key: str, *, max_length: int = 200) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} must be a non-empty string")
    text = value.strip()
    if len(text) > max_length:
        raise ValueError(f"{key} must be <= {max_length} characters")
    return text


def _optional_text(data: dict[str, Any], key: str, *, max_length: int = 200) -> str | None:
    value = data.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"{key} must be a string when present")
    text = value.strip()
    if not text:
        return None
    if len(text) > max_length:
        raise ValueError(f"{key} must be <= {max_length} characters")
    return text


def _require_english_word(value: Any, key: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} must be a non-empty string")
    text = value.strip()
    if not _ENGLISH_RE.fullmatch(text):
        raise ValueError(f"{key} must be English text")
    return text


def validate_coaching_response(response: dict) -> dict:
    if not isinstance(response, dict):
        raise ValueError("response must be a dictionary")

    action = response.get("action")
    if action not in _VALID_ACTIONS:
        raise ValueError(f"action must be one of {_VALID_ACTIONS}")

    normalized: dict[str, Any] = {
        "action": action,
        "message_vi": _require_text(response, "message_vi"),
        "scaffold_word": None,
        "scaffold_reason_vi": None,
        "syllables": [],
        "articulatory_tip_vi": _optional_text(response, "articulatory_tip_vi"),
        "skip_reason_vi": None,
    }

    if action == "scaffold":
        normalized["scaffold_word"] = _require_english_word(response.get("scaffold_word"), "scaffold_word")
        normalized["scaffold_reason_vi"] = _require_text(response, "scaffold_reason_vi")

    if action == "break_down":
        syllables = response.get("syllables")
        if not isinstance(syllables, list) or not (1 <= len(syllables) <= 5):
            raise ValueError("syllables must be a list with 1-5 items")
        normalized_syllables: list[str] = []
        for syllable in syllables:
            normalized_syllables.append(_require_english_word(syllable, "syllables[]"))
        normalized["syllables"] = normalized_syllables

    if action == "skip_with_note":
        normalized["skip_reason_vi"] = _require_text(response, "skip_reason_vi")

    return normalized
