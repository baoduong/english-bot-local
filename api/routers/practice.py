from __future__ import annotations

import asyncio
import subprocess
import tempfile
from contextlib import suppress
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Literal, cast
from uuid import uuid4

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from analysis.pronunciation import analyze_audio as analyze_audio_with_whisper
from analysis.errors import ERROR_TYPE_LABELS, classify_error, get_articulatory_tip
from analysis.phonemes import clean_word, phoneme_similarity
from api.models import (
    DrillInfo,
    NextActionHint,
    PhaseProgress,
    PracticeAudioResponse,
    PracticeContentItem,
    PracticeSessionActionRequest,
    PracticeSessionCurriculumContext,
    PracticeSessionStartRequest,
    PracticeSessionState,
    PracticeSessionStateResponse,
    PracticeSkipResponse,
    PracticeStopResponse,
    SampleAudio,
    ScoringResult,
    SessionEndSummary,
    WordScore,
)
from db.curriculum import (
    get_active_curriculum,
    get_active_phase,
    get_curriculum,
    get_next_practice_sentence,
    get_phase,
    get_phase_content,
    get_phase_progress,
    record_phase_content_attempt,
)
from db.sessions import delete_session, load_all_sessions, save_session
from db.tracking import log_error_pattern, log_score
from db.users import get_or_create_user, needs_onboarding
from db.word_stats import record_word_attempts_batch
from engines.tts import generate_sample_audio

router = APIRouter(prefix="/practice", tags=["Practice"])

_SAMPLE_TTL = timedelta(minutes=10)


def _error(status_code: int, code: str, message: str, detail: Any | None = None) -> HTTPException:
    payload: dict[str, Any] = {"error_code": code, "message": message}
    if detail is not None:
        payload["detail"] = detail
    return HTTPException(status_code=status_code, detail=payload)


def _load_session_sync(user_id: str) -> dict[str, Any] | None:
    return load_all_sessions().get(user_id)


def _save_session_sync(user_id: str, session: dict[str, Any]) -> None:
    save_session(user_id, session)


def _require_user_sync(user_id: str) -> dict[str, Any]:
    user = get_or_create_user(user_id, "User")
    if not user:
        raise _error(404, "USER_NOT_FOUND", "User not found.")
    return user


def _to_phase_progress(raw: dict[str, Any]) -> PhaseProgress:
    return PhaseProgress(
        total=raw.get("total") or 0,
        attempted=raw.get("attempted") or 0,
        mastered=raw.get("mastered") or 0,
        avg_score=float(raw.get("avg_score") or 0.0),
        struggling_words=list(raw.get("struggling_words") or []),
    )


def _to_content_item(content: dict[str, Any] | None) -> PracticeContentItem | None:
    if not content:
        return None
    return PracticeContentItem(
        content_id=content["id"],
        sentence=content["sentence"],
        target_phonemes=list(content.get("target_phonemes") or []),
        target_words=list(content.get("target_words") or []),
        difficulty_score=int(content.get("difficulty_score") or 0),
        attempt_count=content.get("attempt_count"),
        last_score=int(content["last_score"]) if content.get("last_score") is not None else None,
        mastered_at=content.get("mastered_at"),
    )


def _parse_started_at(value: Any) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    with suppress(ValueError, TypeError):
        return datetime.fromisoformat(str(value))
    return None


def _build_sample_audio(user_id: str, sentence: str | None = None, word: str | None = None) -> SampleAudio | None:
    text = word or sentence
    if not text:
        return None
    audio_id = str(uuid4())
    params = [f"user_id={user_id}"]
    if word:
        params.append(f"word={word}")
    else:
        params.append(f"expected_text={text}")
    return SampleAudio(
        audio_id=audio_id,
        content_type="audio/mpeg",
        duration_ms=max(1000, len(text.split()) * 700),
        url=f"/practice/audio/sample?{'&'.join(params)}",
        expires_at=datetime.now(timezone.utc) + _SAMPLE_TTL,
    )


def _build_state_response_sync(user_id: str, session: dict[str, Any]) -> PracticeSessionStateResponse:
    curriculum = get_curriculum(session["curriculum_id"])
    phase = get_phase(session["current_phase_id"])
    if not curriculum or not phase:
        raise _error(404, "SESSION_CONTEXT_MISSING", "Session curriculum or phase no longer exists.")

    progress = _to_phase_progress(get_phase_progress(phase["id"]))
    content_map = {item["id"]: item for item in get_phase_content(phase["id"])}
    current_item = _to_content_item(content_map.get(session.get("content_id")))
    if not current_item and session.get("sentence"):
        current_item = PracticeContentItem(
            content_id=int(session.get("content_id") or 0),
            sentence=session["sentence"],
            target_phonemes=[],
            target_words=[],
            difficulty_score=0,
        )

    drill = None
    if session.get("mode") == "word_drill" and session.get("drill_words"):
        idx = int(session.get("drill_index") or 0)
        words = list(session.get("drill_words") or [])
        if words:
            active_word = words[min(idx, len(words) - 1)]
            drill = DrillInfo(active_word=active_word, drill_index=idx, total_words=len(words))

    return PracticeSessionStateResponse(
        session=PracticeSessionState(
            user_id=user_id,
            mode=session.get("mode", "curriculum_practice"),
            round=session.get("round"),
            fail_count=int(session.get("fail_count") or 0),
            drill_index=session.get("drill_index"),
            drill_words=list(session.get("drill_words") or []) or None,
            started_at=_parse_started_at(session.get("started_at")),
        ),
        curriculum=PracticeSessionCurriculumContext(
            curriculum_id=curriculum["id"],
            current_phase_number=phase["phase_number"],
            phase_theme=phase["theme"],
        ),
        current_item=current_item,
        progress=progress,
        sample_audio=_build_sample_audio(
            user_id,
            word=drill.active_word if drill else None,
            sentence=None if drill else (current_item.sentence if current_item else session.get("sentence")),
        ),
        drill=drill,
    )


def _build_new_session_sync(user_id: str) -> dict[str, Any]:
    if needs_onboarding(user_id):
        raise _error(409, "ONBOARDING_INCOMPLETE", "User must complete onboarding before practice.")

    curriculum = get_active_curriculum(user_id)
    if not curriculum:
        raise _error(409, "ONBOARDING_INCOMPLETE", "No active curriculum found for user.")

    phase = get_active_phase(curriculum["id"])
    if not phase:
        raise _error(404, "ACTIVE_PHASE_NOT_FOUND", "No active phase found for curriculum.")

    content = get_next_practice_sentence(phase["id"])
    if not content:
        raise _error(404, "NO_PRACTICE_CONTENT", "No practice content available for the active phase.")

    progress = get_phase_progress(phase["id"])
    return {
        "round": 1,
        "max_rounds": 5,
        "sentence": content["sentence"],
        "new_word": None,
        "fail_count": 0,
        "mode": "curriculum_practice",
        "drill_words": [],
        "drill_index": 0,
        "drill_fails": 0,
        "drill_passed": 0,
        "drill_done": False,
        "session_stats": {"passed_first_try": 0, "needed_drill": 0, "skipped": 0},
        "started_at": datetime.now().isoformat(),
        "scores": [],
        "curriculum_id": curriculum["id"],
        "current_phase_id": phase["id"],
        "current_phase_number": phase["phase_number"],
        "phase_theme": phase["theme"],
        "phase_total_content": progress["total"],
        "phase_mastered_count": progress["mastered"],
        "content_id": content["id"],
    }


def _advance_to_next_content_sync(session: dict[str, Any]) -> dict[str, Any] | None:
    current_id = session.get("content_id")
    next_content = get_next_practice_sentence(session["current_phase_id"], exclude_content_id=current_id)
    if not next_content:
        next_content = get_next_practice_sentence(session["current_phase_id"])
    if not next_content:
        return None
    session["sentence"] = next_content["sentence"]
    session["content_id"] = next_content["id"]
    session["fail_count"] = 0
    session["drill_done"] = False
    progress = get_phase_progress(session["current_phase_id"])
    session["phase_mastered_count"] = progress["mastered"]
    session["phase_total_content"] = progress["total"]
    return session


def _extract_expected_text_sync(session: dict[str, Any] | None, content_id: int | None, expected_text: str | None) -> tuple[str, dict[str, Any]]:
    if session and session.get("mode") == "word_drill" and session.get("drill_words"):
        idx = int(session.get("drill_index") or 0)
        words = list(session.get("drill_words") or [])
        if idx < len(words):
            return words[idx], {
                "id": int(session.get("content_id") or 0),
                "sentence": session.get("sentence") or words[idx],
                "target_phonemes": [],
                "target_words": words,
                "difficulty_score": 0,
            }

    if content_id is not None and session and session.get("current_phase_id"):
        for item in get_phase_content(session["current_phase_id"]):
            if item["id"] == content_id:
                return item["sentence"], item

    if session and session.get("sentence"):
        return session["sentence"], {
            "id": int(session.get("content_id") or content_id or 0),
            "sentence": session["sentence"],
            "target_phonemes": [],
            "target_words": [],
            "difficulty_score": 0,
        }

    if expected_text:
        return expected_text, {
            "id": int(content_id or 0),
            "sentence": expected_text,
            "target_phonemes": [],
            "target_words": [],
            "difficulty_score": 0,
        }

    raise _error(400, "EXPECTED_TEXT_REQUIRED", "Expected text could not be resolved for scoring.")


def _score_color_from_confidence(
    confidence: float, expected_word: str, heard_word: str | None
) -> tuple[Literal["green", "yellow", "red", "gray"], float, int]:
    if not heard_word:
        return "gray", 0.0, 0
    phon_sim = 1.0 if clean_word(heard_word) == clean_word(expected_word) else phoneme_similarity(heard_word, expected_word)
    if confidence >= 0.75:
        return "green", phon_sim, 100
    if confidence >= 0.50:
        return "yellow", phon_sim, 60
    if phon_sim >= 0.75:
        return "yellow", phon_sim, 50
    return "red", phon_sim, 10


def _build_word_scores(expected_text: str, analysis: tuple[Any, ...]) -> tuple[list[WordScore], list[str], list[str], dict[str, Any]]:
    _, _, _, _, error_types, raw_word_scores = analysis
    score_map: dict[str, Any] = raw_word_scores or {}
    words: list[WordScore] = []
    weak_words: list[str] = []
    labels: list[str] = []
    for token in expected_text.split():
        clean = clean_word(token)
        raw = score_map.get(clean)
        if not raw:
            words.append(WordScore(word=token, accuracy=0, color="gray", phoneme_similarity=0.0, tip=get_articulatory_tip("omission")))
            weak_words.append(clean)
            labels.append(ERROR_TYPE_LABELS["omission"])
            continue
        heard = clean if raw.get("passed") else clean
        confidence = 1.0 if raw.get("score") == 100 else (0.6 if raw.get("score") == 60 else 0.5 if raw.get("score") == 50 else 0.1)
        color, phon_sim, accuracy = _score_color_from_confidence(confidence, token, heard)
        if raw.get("score") == 0:
            color, phon_sim, accuracy = cast(Literal["gray"], "gray"), 0.0, 0
        tip = None
        if not raw.get("passed"):
            err_type = next((etype for word, etype in error_types if word == clean), classify_error(token, heard))
            labels.append(ERROR_TYPE_LABELS.get(err_type, ERROR_TYPE_LABELS["general"]))
            tip = get_articulatory_tip(err_type)
            weak_words.append(clean)
        words.append(
            WordScore(
                word=token,
                accuracy=int(raw.get("score", accuracy)),
                color=color,
                phoneme_similarity=float(phon_sim),
                tip=tip,
            )
        )
    return words, sorted(set(weak_words)), sorted(set(labels)), score_map


def _transcode_to_wav_sync(input_path: str, output_path: str) -> None:
    command = [
        "ffmpeg",
        "-y",
        "-i",
        input_path,
        "-ar",
        "16000",
        "-ac",
        "1",
        "-f",
        "wav",
        output_path,
    ]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        raise _error(400, "INVALID_AUDIO", "Audio transcoding failed.", detail=result.stderr.strip())


def _record_practice_metrics_sync(user_id: str, sentence: str, score: int, score_map: dict[str, Any], error_types: list[tuple[str, str]]) -> None:
    log_score(user_id, sentence, score)
    for word, err_type in error_types:
        log_error_pattern(user_id, err_type, word)
    if score_map:
        record_word_attempts_batch(user_id, score_map)


@router.post("/session/start", response_model=PracticeSessionStateResponse)
async def start_practice_session(body: PracticeSessionStartRequest) -> PracticeSessionStateResponse:
    await asyncio.to_thread(_require_user_sync, body.user_id)
    session = await asyncio.to_thread(_load_session_sync, body.user_id)
    if session and session.get("mode") in {"curriculum_practice", "word_drill"} and body.resume_if_exists:
        return await asyncio.to_thread(_build_state_response_sync, body.user_id, session)

    session = await asyncio.to_thread(_build_new_session_sync, body.user_id)
    await asyncio.to_thread(_save_session_sync, body.user_id, session)
    return await asyncio.to_thread(_build_state_response_sync, body.user_id, session)


@router.get("/session/state", response_model=PracticeSessionStateResponse)
async def get_practice_session_state(user_id: str) -> PracticeSessionStateResponse:
    await asyncio.to_thread(_require_user_sync, user_id)
    session = await asyncio.to_thread(_load_session_sync, user_id)
    if not session or session.get("mode") not in {"curriculum_practice", "word_drill"}:
        raise _error(404, "SESSION_NOT_FOUND", "No active practice session found.")
    return await asyncio.to_thread(_build_state_response_sync, user_id, session)


@router.post("/session/skip", response_model=PracticeSkipResponse)
async def skip_practice_item(body: PracticeSessionActionRequest) -> PracticeSkipResponse:
    await asyncio.to_thread(_require_user_sync, body.user_id)
    session = await asyncio.to_thread(_load_session_sync, body.user_id)
    if not session or session.get("mode") not in {"curriculum_practice", "word_drill"}:
        raise _error(404, "SESSION_NOT_FOUND", "No active practice session found.")

    session.setdefault("session_stats", {}).setdefault("skipped", 0)
    session["session_stats"]["skipped"] += 1

    if session.get("mode") == "word_drill" and session.get("drill_words"):
        session["drill_index"] = min(int(session.get("drill_index") or 0) + 1, len(session["drill_words"]))
        if session["drill_index"] >= len(session["drill_words"]):
            session["mode"] = "curriculum_practice"
            session["drill_words"] = []
            session["drill_index"] = 0
            session["drill_done"] = True
    else:
        advanced = await asyncio.to_thread(_advance_to_next_content_sync, session)
        if not advanced:
            raise _error(404, "NO_NEXT_CONTENT", "No next practice item available.")

    await asyncio.to_thread(_save_session_sync, body.user_id, session)
    next_state = await asyncio.to_thread(_build_state_response_sync, body.user_id, session)
    return PracticeSkipResponse(action="skipped", skipped_count=int(session["session_stats"]["skipped"]), next_state=next_state)


@router.post("/session/stop", response_model=PracticeStopResponse)
async def stop_practice_session(body: PracticeSessionActionRequest) -> PracticeStopResponse:
    await asyncio.to_thread(_require_user_sync, body.user_id)
    session = await asyncio.to_thread(_load_session_sync, body.user_id)
    if not session or session.get("mode") not in {"curriculum_practice", "word_drill"}:
        return PracticeStopResponse(
            action="stopped",
            session_cleared=False,
            summary=SessionEndSummary(total_attempts=0, passed_first_try=0, needed_drill=0, skipped=0, final_mode="none"),
            message="No active practice session.",
        )

    stats = session.get("session_stats") or {}
    summary = SessionEndSummary(
        total_attempts=len(session.get("scores") or []),
        passed_first_try=int(stats.get("passed_first_try") or 0),
        needed_drill=int(stats.get("needed_drill") or 0),
        skipped=int(stats.get("skipped") or 0),
        final_mode=session.get("mode", "curriculum_practice"),
    )
    await asyncio.to_thread(delete_session, body.user_id)
    return PracticeStopResponse(
        action="stopped",
        session_cleared=True,
        summary=summary,
        message="Practice session stopped successfully.",
    )


@router.post("/audio", response_model=PracticeAudioResponse)
async def score_practice_audio(
    user_id: str = Form(...),
    audio_file: UploadFile = File(...),
    content_id: str | None = Form(None),
    expected_text: str | None = Form(None),
) -> PracticeAudioResponse:
    await asyncio.to_thread(_require_user_sync, user_id)
    session = await asyncio.to_thread(_load_session_sync, user_id)
    if not session or session.get("mode") not in {"curriculum_practice", "word_drill"}:
        raise _error(404, "SESSION_NOT_FOUND", "No active practice session found.")

    suffix = Path(audio_file.filename or "upload").suffix.lower()
    if suffix != ".m4a":
        raise _error(400, "INVALID_AUDIO", "Only .m4a uploads are supported.")

    resolved_content_id = int(content_id) if content_id else None
    expected, current_content = await asyncio.to_thread(_extract_expected_text_sync, session, resolved_content_id, expected_text)

    temp_dir = Path(tempfile.gettempdir())
    source_path = temp_dir / f"{uuid4()}_{Path(audio_file.filename or 'practice').name}"
    wav_path = temp_dir / f"{uuid4()}_practice.wav"

    try:
        payload = await audio_file.read()
        if not payload:
            raise _error(400, "INVALID_AUDIO", "Uploaded audio file is empty.")
        await asyncio.to_thread(source_path.write_bytes, payload)
        await asyncio.to_thread(_transcode_to_wav_sync, str(source_path), str(wav_path))

        analysis = await asyncio.to_thread(analyze_audio_with_whisper, str(wav_path), expected)
        overall_score, _ansi_feedback, feedback_message, problem_words, error_types, _word_scores = analysis
        word_scores, weak_words, error_labels, score_map = await asyncio.to_thread(_build_word_scores, expected, analysis)

        await asyncio.to_thread(_record_practice_metrics_sync, user_id, expected, int(overall_score), score_map, error_types)
        await asyncio.to_thread(record_phase_content_attempt, int(session["content_id"]), int(overall_score))

        session.setdefault("scores", []).append(int(overall_score))
        if overall_score >= 80:
            session.setdefault("session_stats", {}).setdefault("passed_first_try", 0)
            if int(session.get("fail_count") or 0) == 0:
                session["session_stats"]["passed_first_try"] += 1
            session["fail_count"] = 0
            await asyncio.to_thread(_advance_to_next_content_sync, session)
            next_action = NextActionHint(action="pass", message="Passed. Continue to the next sentence.")
        else:
            session["fail_count"] = int(session.get("fail_count") or 0) + 1
            if session["fail_count"] >= 4:
                await asyncio.to_thread(_advance_to_next_content_sync, session)
                session["fail_count"] = 0
                next_action = NextActionHint(
                    action="pass",
                    message="Moving on. You can revisit this sentence later.",
                    focus_words=weak_words or None,
                )
            elif session["fail_count"] >= 2 and weak_words:
                session.setdefault("session_stats", {}).setdefault("needed_drill", 0)
                session["session_stats"]["needed_drill"] += 1
                session["mode"] = "word_drill"
                session["drill_words"] = weak_words
                session["drill_index"] = 0
                next_action = NextActionHint(
                    action="word_drill",
                    message="Second failed attempt. Starting word drill.",
                    focus_words=weak_words,
                )
            else:
                next_action = NextActionHint(action="retry", message="Retry the same sentence.", focus_words=weak_words or None)

        progress = await asyncio.to_thread(get_phase_progress, session["current_phase_id"])
        session["phase_mastered_count"] = progress["mastered"]
        session["phase_total_content"] = progress["total"]
        await asyncio.to_thread(_save_session_sync, user_id, session)

        current_item_model = _to_content_item(current_content)
        if current_item_model is None:
            raise _error(404, "CONTENT_NOT_FOUND", "Current practice item could not be resolved.")

        return PracticeAudioResponse(
            scoring=ScoringResult(
                overall_score=int(overall_score),
                passed=overall_score >= 80,
                transcript=expected,
                expected_text=expected,
                engine="whisper",
                weak_words=weak_words,
                error_types=error_labels,
                feedback_message=feedback_message,
                word_scores=word_scores,
                sample_audio=_build_sample_audio(user_id, sentence=expected),
            ),
            next_action=next_action,
            session=PracticeSessionState(
                user_id=user_id,
                mode=session.get("mode", "curriculum_practice"),
                round=session.get("round"),
                fail_count=int(session.get("fail_count") or 0),
                drill_index=session.get("drill_index"),
                drill_words=list(session.get("drill_words") or []) or None,
                started_at=_parse_started_at(session.get("started_at")),
            ),
            current_item=current_item_model,
        )
    finally:
        with suppress(Exception):
            if source_path.exists():
                source_path.unlink()
        with suppress(Exception):
            if wav_path.exists():
                wav_path.unlink()


@router.get("/audio/sample")
async def get_practice_sample_audio(
    user_id: str,
    content_id: str | None = None,
    word: str | None = None,
    expected_text: str | None = None,
) -> FileResponse:
    await asyncio.to_thread(_require_user_sync, user_id)
    session = await asyncio.to_thread(_load_session_sync, user_id)
    resolved_word = word
    resolved_text = expected_text

    if not resolved_word and not resolved_text and session:
        if session.get("mode") == "word_drill" and session.get("drill_words"):
            idx = int(session.get("drill_index") or 0)
            words = list(session.get("drill_words") or [])
            if idx < len(words):
                resolved_word = words[idx]
        else:
            resolved_text = session.get("sentence")

    if not resolved_word and not resolved_text and content_id and session and session.get("current_phase_id"):
        phase_items = await asyncio.to_thread(get_phase_content, session["current_phase_id"])
        target = next((item for item in phase_items if item["id"] == int(content_id)), None)
        resolved_text = target["sentence"] if target else None

    text = resolved_word or resolved_text
    if not text:
        raise _error(404, "SAMPLE_TEXT_NOT_FOUND", "No practice text found for sample generation.")

    tmp_path = Path(tempfile.gettempdir()) / f"{uuid4()}_teacher_sample.mp3"
    success = False
    try:
        success = await generate_sample_audio(text, str(tmp_path))
        if not success or not tmp_path.exists():
            raise _error(400, "SAMPLE_AUDIO_FAILED", "Failed to generate teacher sample audio.")
        return FileResponse(str(tmp_path), media_type="audio/mpeg", filename=f"sample-{uuid4()}.mp3")
    except HTTPException:
        with suppress(Exception):
            if tmp_path.exists():
                tmp_path.unlink()
        raise
