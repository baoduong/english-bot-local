from __future__ import annotations

import shutil
import subprocess
import tempfile
import uuid
from pathlib import Path
from fastapi import UploadFile


SUPPORTED_FORMATS = {".m4a", ".mp4", ".aac", ".wav", ".mp3"}
TEMP_DIR_PREFIX = "englishbot-audio-"


def _build_request_temp_dir() -> Path:
    request_id = str(uuid.uuid4())
    return Path(tempfile.gettempdir()) / f"{TEMP_DIR_PREFIX}{request_id}"


def _ensure_tool_available(tool_name: str) -> None:
    try:
        _ = subprocess.run(
            [tool_name, "-version"],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError as exc:
        raise RuntimeError(f"{{\"error_code\":\"MISSING_DEPENDENCY\",\"tool\":\"{tool_name}\"}}") from exc


def _structured_invalid_audio(message: str, **extra: object) -> ValueError:
    details = {"error_code": "INVALID_AUDIO", "message": message, **extra}
    return ValueError(str(details))


async def save_upload_to_temp(upload: UploadFile) -> str:
    original_name = upload.filename or "audio"
    suffix = Path(original_name).suffix.lower()
    request_dir = _build_request_temp_dir()
    request_dir.mkdir(parents=True, exist_ok=True)

    temp_path = request_dir / f"{uuid.uuid4()}-{Path(original_name).name}"

    try:
        with temp_path.open("wb") as temp_file:
            while chunk := await upload.read(1024 * 1024):
                _ = temp_file.write(chunk)
    except Exception:
        cleanup_temp_files(str(request_dir))
        raise
    finally:
        await upload.close()

    if suffix and temp_path.suffix.lower() != suffix:
        temp_path = temp_path.with_suffix(suffix)

    return str(temp_path)


def validate_audio_format(file_path: str) -> None:
    path = Path(file_path)
    if path.suffix.lower() not in SUPPORTED_FORMATS:
        raise _structured_invalid_audio(
            "Unsupported audio file extension",
            extension=path.suffix.lower(),
            supported_formats=sorted(SUPPORTED_FORMATS),
        )
    if not path.exists() or not path.is_file():
        raise _structured_invalid_audio("Audio file was not saved correctly", path=file_path)
    if path.stat().st_size == 0:
        raise _structured_invalid_audio("Uploaded audio file is empty", path=file_path)

    _ensure_tool_available("ffprobe")
    probe = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "a:0",
            "-show_entries",
            "stream=codec_type",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            file_path,
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if probe.returncode != 0 or "audio" not in probe.stdout.lower():
        raise _structured_invalid_audio(
            "File is not a valid audio stream",
            path=file_path,
            stderr=probe.stderr.strip(),
        )


def probe_audio_duration(file_path: str) -> float:
    _ensure_tool_available("ffprobe")
    probe = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            file_path,
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if probe.returncode != 0:
        raise _structured_invalid_audio(
            "Unable to probe audio duration",
            path=file_path,
            stderr=probe.stderr.strip(),
        )

    try:
        return float(probe.stdout.strip())
    except ValueError as exc:
        raise _structured_invalid_audio(
            "Audio duration metadata is invalid",
            path=file_path,
            stdout=probe.stdout.strip(),
        ) from exc


def transcode_to_wav_16k_mono(input_path: str) -> str:
    _ensure_tool_available("ffmpeg")

    input_file = Path(input_path)
    request_dir = input_file.parent
    output_path = request_dir / f"{uuid.uuid4()}-{input_file.stem}.wav"

    result = subprocess.run(
        [
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
            str(output_path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"{{\"error_code\":\"TRANSCRIPTION_FAILED\",\"message\":\"ffmpeg transcoding failed\",\"stderr\":{result.stderr.strip()!r}}}"
        )

    return str(output_path)


def cleanup_temp_files(*paths: str | None) -> None:
    seen_dirs: set[Path] = set()
    for raw_path in paths:
        if not raw_path:
            continue
        path = Path(raw_path)
        try:
            if path.is_dir():
                shutil.rmtree(path, ignore_errors=True)
                continue
            if path.exists():
                path.unlink(missing_ok=True)
            parent = path.parent
            if parent.name.startswith(TEMP_DIR_PREFIX) and parent not in seen_dirs:
                shutil.rmtree(parent, ignore_errors=True)
                seen_dirs.add(parent)
        except Exception:
            continue


def cleanup_audio_files(*paths: str | None) -> None:
    cleanup_temp_files(*paths)


async def validate_audio_file(upload: UploadFile) -> str:
    temp_path = await save_upload_to_temp(upload)
    try:
        validate_audio_format(temp_path)
        return temp_path
    except Exception:
        cleanup_temp_files(temp_path)
        raise


def transcode_m4a_to_wav(input_path: str) -> str:
    validate_audio_format(input_path)
    return transcode_to_wav_16k_mono(input_path)
