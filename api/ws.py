from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from api.dependencies import get_curriculum_generator, get_onboarding_chat
from api.models import GoalSynthesis
from db.curriculum import (
    clear_onboarding_conversation,
    create_curriculum,
    get_active_curriculum,
    get_active_phase,
    get_onboarding_conversation,
    get_phase,
    get_phase_content,
    get_phase_progress,
    get_next_practice_sentence,
)
from db.sessions import delete_session, load_all_sessions, save_session
from db.users import get_or_create_user, mark_onboarding_complete, needs_onboarding
from engines.ollama_client import OllamaSchemaError, OllamaUnavailableError

router = APIRouter()

HEARTBEAT_INTERVAL_SECONDS = 30
_user_locks: dict[str, asyncio.Lock] = {}


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _get_user_lock(user_id: str) -> asyncio.Lock:
    lock = _user_locks.get(user_id)
    if lock is None:
        lock = asyncio.Lock()
        _user_locks[user_id] = lock
    return lock


def _serialize_datetime(value: Any) -> Any:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")
        return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    return value


def _json_ready(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _json_ready(val) for key, val in value.items()}
    if isinstance(value, list):
        return [_json_ready(item) for item in value]
    return _serialize_datetime(value)


def _session_snapshot(user_id: str, session: dict[str, Any] | None) -> dict[str, Any]:
    current_session = session or {}
    return {
        "user_id": user_id,
        "mode": current_session.get("mode"),
        "onboarding_turn": current_session.get("onboarding_turn"),
        "current_phase_id": current_session.get("current_phase_id"),
        "current_phase_number": current_session.get("current_phase_number"),
        "phase_theme": current_session.get("phase_theme"),
        "phase_total_content": current_session.get("phase_total_content"),
        "phase_mastered_count": current_session.get("phase_mastered_count"),
        "pending_goal_synthesis": current_session.get("pending_goal_synthesis"),
        "started_at": current_session.get("started_at"),
    }


def _practice_state_payload(user_id: str, session: dict[str, Any]) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "session": _session_snapshot(user_id, session),
        "current_item": None,
        "progress": None,
    }

    phase_id = session.get("current_phase_id")
    if not phase_id:
        return payload

    phase = get_phase(phase_id)
    progress = get_phase_progress(phase_id)
    next_item = get_next_practice_sentence(phase_id)
    payload["current_item"] = _json_ready(next_item) if next_item else None
    payload["progress"] = _json_ready(progress) if progress else None
    if phase:
        payload["phase"] = {
            "phase_id": phase["id"],
            "phase_number": phase["phase_number"],
            "theme": phase["theme"],
            "status": phase["status"],
        }
    return payload


def _connected_payload(user_id: str, session: dict[str, Any] | None) -> dict[str, Any]:
    return {
        "user_id": user_id,
        "session": _session_snapshot(user_id, session),
        "resumed": bool(session),
    }


class ConnectionManager:
    def __init__(self) -> None:
        self.active_connections: dict[str, WebSocket] = {}

    async def connect(self, user_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        previous = self.active_connections.get(user_id)
        if previous and previous is not websocket:
            try:
                await previous.close(code=1000, reason="Replaced by newer connection")
            except RuntimeError:
                pass
        self.active_connections[user_id] = websocket

    async def disconnect(self, user_id: str) -> None:
        self.active_connections.pop(user_id, None)

    async def send_event(self, user_id: str, event: str, data: dict[str, Any]) -> None:
        websocket = self.active_connections.get(user_id)
        if websocket is None:
            return
        await websocket.send_json(
            {
                "event": event,
                "timestamp": _timestamp(),
                "data": _json_ready(data),
            }
        )


manager = ConnectionManager()


async def _send_error(user_id: str, code: str, message: str, detail: Any = None) -> None:
    payload: dict[str, Any] = {"error_code": code, "message": message}
    if detail is not None:
        payload["detail"] = detail
    await manager.send_event(user_id, "error", payload)


async def _heartbeat_loop(user_id: str) -> None:
    while True:
        await asyncio.sleep(HEARTBEAT_INTERVAL_SECONDS)
        await manager.send_event(user_id, "heartbeat", {})


async def _load_existing_session(user_id: str) -> dict[str, Any] | None:
    sessions = await asyncio.to_thread(load_all_sessions)
    return sessions.get(user_id)


async def _start_onboarding(user_id: str) -> dict[str, Any]:
    user = await asyncio.to_thread(get_or_create_user, user_id, user_id)
    interface_language = str(user.get("interface_language") or "vi")
    if user.get("onboarding_completed_at") and not await asyncio.to_thread(needs_onboarding, user_id):
        raise ValueError("Onboarding already complete")

    chat = get_onboarding_chat()
    history = await asyncio.to_thread(get_onboarding_conversation, user_id)
    if history:
        last_assistant = next((turn for turn in reversed(history) if turn.get("role") == "assistant"), None)
        turn_number = last_assistant.get("turn_number") if last_assistant else len(history)
        session = {"mode": "onboarding", "onboarding_turn": turn_number}
        await asyncio.to_thread(save_session, user_id, session)
        return {
            "event": "onboarding_message",
            "data": {
                "role": "assistant",
                "content": last_assistant.get("content", "") if last_assistant else "",
                "turn_number": turn_number,
                "history_preview": history,
                "session": _session_snapshot(user_id, session),
            },
        }

    greeting = await asyncio.to_thread(chat.start_conversation, user_id, interface_language)
    history = await asyncio.to_thread(get_onboarding_conversation, user_id)
    turn_number = history[-1]["turn_number"] if history else 0
    session = {"mode": "onboarding", "onboarding_turn": turn_number}
    await asyncio.to_thread(save_session, user_id, session)
    return {
        "event": "onboarding_message",
        "data": {
            "role": "assistant",
            "content": greeting,
            "turn_number": turn_number,
            "history_preview": history,
            "session": _session_snapshot(user_id, session),
        },
    }


async def _respond_onboarding(user_id: str, message: str) -> list[dict[str, Any]]:
    if not message or not message.strip():
        raise ValueError("Message is required")

    chat = get_onboarding_chat()
    result = await asyncio.to_thread(chat.submit_user_reply, user_id, message.strip())
    result_type = result.get("type")

    if result_type == "question":
        session = {"mode": "onboarding", "onboarding_turn": result["turn_number"]}
        await asyncio.to_thread(save_session, user_id, session)
        return [
            {
                "event": "onboarding_message",
                "data": {
                    "role": "assistant",
                    "content": result["text"],
                    "turn_number": result["turn_number"],
                    "session": _session_snapshot(user_id, session),
                },
            }
        ]

    if result_type == "synthesis":
        goal = GoalSynthesis(**result["goal"])
        session = {
            "mode": "awaiting_goal_confirmation",
            "onboarding_turn": result["turn_number"],
            "pending_goal_synthesis": goal.model_dump(),
        }
        await asyncio.to_thread(save_session, user_id, session)
        return [
            {
                "event": "onboarding_message",
                "data": {
                    "role": "assistant",
                    "content": goal.model_dump_json(),
                    "turn_number": result["turn_number"],
                    "session": _session_snapshot(user_id, session),
                },
            }
        ]

    raise OllamaSchemaError(f"Unexpected onboarding result type: {result_type}")


async def _confirm_onboarding(user_id: str, confirmed: bool) -> list[dict[str, Any]]:
    history = await asyncio.to_thread(get_onboarding_conversation, user_id)
    if not history:
        raise ValueError("Onboarding session expired")

    chat = get_onboarding_chat()
    generator = get_curriculum_generator()
    goal = await asyncio.to_thread(chat.synthesize_goal, user_id)

    if not confirmed:
        await asyncio.to_thread(clear_onboarding_conversation, user_id)
        await asyncio.to_thread(delete_session, user_id)
        return [
            {
                "event": "session_ended",
                "data": {
                    "reason": "goal_rejected",
                    "message": "Goal confirmation rejected",
                    "onboarding_history_cleared": True,
                },
            }
        ]

    user = await asyncio.to_thread(get_or_create_user, user_id, user_id)
    interface_language = str(user.get("interface_language") or "vi")
    if user.get("active_curriculum_id"):
        raise ValueError("Active curriculum already exists")

    curriculum_id = await asyncio.to_thread(
        create_curriculum,
        user_id,
        goal["goal_title"],
        goal.get("goal_description", ""),
        interface_language,
    )
    await asyncio.to_thread(mark_onboarding_complete, user_id, curriculum_id)
    phase_id, _ = await asyncio.to_thread(
        generator.generate_full_phase,
        curriculum_id,
        goal["goal_title"],
        goal.get("goal_description", ""),
        1,
        [],
        "",
    )

    curriculum = await asyncio.to_thread(get_active_curriculum, user_id)
    phase = await asyncio.to_thread(get_phase, phase_id)
    content = await asyncio.to_thread(get_phase_content, phase_id)
    progress = await asyncio.to_thread(get_phase_progress, phase_id)
    if not curriculum or not phase:
        raise ValueError("Session expired")

    session = {
        "mode": "curriculum_practice",
        "curriculum_id": curriculum_id,
        "current_phase_id": phase_id,
        "current_phase_number": phase["phase_number"],
        "phase_theme": phase["theme"],
        "phase_total_content": progress.get("total", 0),
        "phase_mastered_count": progress.get("mastered", 0),
        "started_at": _timestamp(),
    }
    await asyncio.to_thread(save_session, user_id, session)
    await asyncio.to_thread(clear_onboarding_conversation, user_id)

    return [
        {
            "event": "practice_state",
            "data": {
                "session": _session_snapshot(user_id, session),
                "curriculum": _json_ready(curriculum),
                "phase": _json_ready(phase),
                "progress": _json_ready(progress),
                "current_item": _json_ready(content[0]) if content else None,
            },
        }
    ]


async def _start_practice(user_id: str) -> dict[str, Any]:
    user = await asyncio.to_thread(get_or_create_user, user_id, user_id)
    if await asyncio.to_thread(needs_onboarding, user_id):
        raise ValueError("User must complete onboarding first")

    curriculum = await asyncio.to_thread(get_active_curriculum, user_id)
    if not curriculum:
        raise ValueError("No active curriculum found")

    phase = await asyncio.to_thread(get_active_phase, curriculum["id"])
    if not phase:
        raise ValueError("No active phase found")

    progress = await asyncio.to_thread(get_phase_progress, phase["id"])
    current_item = await asyncio.to_thread(get_next_practice_sentence, phase["id"])

    session = {
        "mode": "curriculum_practice",
        "curriculum_id": curriculum["id"],
        "current_phase_id": phase["id"],
        "current_phase_number": phase["phase_number"],
        "phase_theme": phase["theme"],
        "phase_total_content": progress.get("total", 0),
        "phase_mastered_count": progress.get("mastered", 0),
        "started_at": _timestamp(),
        "username": user.get("username"),
    }
    await asyncio.to_thread(save_session, user_id, session)

    return {
        "event": "practice_state",
        "data": {
            "session": _session_snapshot(user_id, session),
            "curriculum": _json_ready(curriculum),
            "phase": _json_ready(phase),
            "progress": _json_ready(progress),
            "current_item": _json_ready(current_item) if current_item else None,
        },
    }


async def _skip_practice(user_id: str, session: dict[str, Any]) -> dict[str, Any]:
    if session.get("mode") != "curriculum_practice":
        raise ValueError("No active practice session")
    return {
        "event": "practice_state",
        "data": _practice_state_payload(user_id, session),
    }


async def _stop_session(user_id: str, session: dict[str, Any] | None) -> dict[str, Any]:
    await asyncio.to_thread(delete_session, user_id)
    return {
        "event": "session_ended",
        "data": {
            "reason": "stopped",
            "final_mode": session.get("mode") if session else None,
            "session_cleared": True,
        },
    }


async def _handle_action(user_id: str, payload: dict[str, Any], session: dict[str, Any] | None) -> list[dict[str, Any]]:
    action = payload.get("action")
    if not action:
        raise ValueError("Missing action")

    if action == "start_onboarding":
        return [await _start_onboarding(user_id)]
    if action == "respond":
        return await _respond_onboarding(user_id, payload.get("message", ""))
    if action == "confirm":
        return await _confirm_onboarding(user_id, bool(payload.get("confirmed")))
    if action == "start_practice":
        return [await _start_practice(user_id)]
    if action == "skip":
        current_session = session or await _load_existing_session(user_id)
        return [await _skip_practice(user_id, current_session or {})]
    if action == "stop":
        current_session = session or await _load_existing_session(user_id)
        return [await _stop_session(user_id, current_session)]
    raise ValueError(f"Unsupported action: {action}")


@router.websocket("/ws/session")
async def websocket_session(websocket: WebSocket, user_id: str = Query(...)) -> None:
    if not user_id:
        await websocket.close(code=1008, reason="user_id is required")
        return

    user = await asyncio.to_thread(get_or_create_user, user_id, user_id)
    if not user:
        await websocket.accept()
        await websocket.send_json(
            {
                "event": "error",
                "timestamp": _timestamp(),
                "data": {"error_code": "SESSION_EXPIRED", "message": "User session expired"},
            }
        )
        await websocket.close(code=1008, reason="User not found")
        return

    await manager.connect(user_id, websocket)
    heartbeat_task = asyncio.create_task(_heartbeat_loop(user_id))

    try:
        session = await _load_existing_session(user_id)
        await manager.send_event(user_id, "connected", _connected_payload(user_id, session))
        if session and session.get("mode") == "curriculum_practice":
            await manager.send_event(user_id, "practice_state", _practice_state_payload(user_id, session))

        while True:
            payload = await websocket.receive_json()
            if not isinstance(payload, dict):
                raise ValueError("Invalid message format")

            async with _get_user_lock(user_id):
                current_session = await _load_existing_session(user_id)
                events = await _handle_action(user_id, payload, current_session)
                for event in events:
                    await manager.send_event(user_id, event["event"], event["data"])
                    if event["event"] == "practice_state" and event["data"].get("progress") is not None:
                        await manager.send_event(
                            user_id,
                            "scoring_result",
                            {
                                "status": "pending_audio",
                                "message": "Audio scoring remains on REST /practice/audio in v1",
                            },
                        )
    except WebSocketDisconnect:
        pass
    except OllamaUnavailableError as exc:
        await _send_error(user_id, "OLLAMA_DOWN", "Ollama service is unavailable", str(exc))
    except ValueError as exc:
        message = str(exc)
        error_code = "INVALID_MESSAGE"
        if "expired" in message.lower():
            error_code = "SESSION_EXPIRED"
        await _send_error(user_id, error_code, message)
    except Exception as exc:
        await _send_error(user_id, "INTERNAL_ERROR", "Unexpected websocket error", str(exc))
    finally:
        heartbeat_task.cancel()
        try:
            await heartbeat_task
        except asyncio.CancelledError:
            pass
        await manager.disconnect(user_id)
