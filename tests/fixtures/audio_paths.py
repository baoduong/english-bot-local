from pathlib import Path

_AUDIO_DIR = Path(__file__).parent / "audio"

AUDIO_FIXTURES: dict[str, Path] = {
    "silence": _AUDIO_DIR / "silence_1s.wav",
    "fix": _AUDIO_DIR / "fix_correct.wav",
    "six": _AUDIO_DIR / "six_correct.wav",
    "task": _AUDIO_DIR / "task_correct.wav",
    "throughout": _AUDIO_DIR / "throughout_correct.wav",
}
