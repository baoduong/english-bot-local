from __future__ import annotations

import threading
from typing import Any


class ProsodyAnalyzer:

    def __init__(self) -> None:
        self._loaded: bool = False
        self._lock: threading.Lock = threading.Lock()

    def _ensure_loaded(self) -> None:
        if self._loaded:
            return
        with self._lock:
            if self._loaded:
                return
            try:
                import librosa as _librosa  # type: ignore[import-not-found]
                import numpy as _numpy
            except ImportError as exc:
                raise RuntimeError("librosa is required for prosody analysis") from exc

            _ = (_librosa, _numpy)

            self._loaded = True

    def load(self) -> None:
        self._ensure_loaded()

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    def analyze(self, audio_path: str, expected_word_count: int) -> dict[str, Any]:
        self._ensure_loaded()
        import librosa  # type: ignore[import-not-found]
        import numpy as np

        try:
            y, sr = librosa.load(audio_path, sr=16000, mono=True)
        except Exception as exc:
            return {
                "fluency_score": None,
                "linking_score": None,
                "prosody_score": None,
                "pace_wpm": None,
                "pause_count": 0,
                "error": str(exc),
            }

        total_duration = len(y) / sr if sr else 0.0
        if total_duration < 0.3:
            return {
                "fluency_score": 0,
                "linking_score": 0,
                "prosody_score": 0,
                "pace_wpm": 0.0,
                "pause_count": 0,
            }

        frame_length = max(1, int(sr * 0.025))
        hop_length = max(1, int(sr * 0.010))
        rms = librosa.feature.rms(y=y, frame_length=frame_length, hop_length=hop_length)[0]
        energy_thresh = max(float(rms.max()) * 0.10, 1e-4)
        silent = rms < energy_thresh

        min_silence_frames = max(1, int(0.150 / 0.010))
        pauses: list[tuple[int, int]] = []
        i = 0
        while i < len(silent):
            if silent[i]:
                j = i
                while j < len(silent) and silent[j]:
                    j += 1
                if j - i >= min_silence_frames:
                    pauses.append((i, j))
                i = j
                continue
            i += 1

        pause_count = len(pauses)
        total_silent_seconds = sum((end - start) * 0.010 for start, end in pauses)
        speaking_seconds = max(0.01, total_duration - total_silent_seconds)
        pace_wpm = (expected_word_count / speaking_seconds) * 60.0 if expected_word_count else 0.0

        expected_pauses = max(1, expected_word_count // 6)
        excess_pauses = max(0, pause_count - expected_pauses)
        linking_score = max(0, min(100, int(100 - excess_pauses * 15)))

        if pace_wpm <= 0:
            pace_factor = 0
        elif pace_wpm < 60:
            pace_factor = max(0, int(100 - (60 - pace_wpm) * 2))
        elif pace_wpm > 200:
            pace_factor = max(0, int(100 - (pace_wpm - 200) * 2))
        else:
            pace_factor = 100

        try:
            energy_cv = float(np.std(rms) / max(float(np.mean(rms)), 1e-6)) if len(rms) else 0.0
        except Exception:
            energy_cv = 0.0
        energy_bonus = min(100, int(energy_cv * 120))
        fluency_score = max(0, min(100, int(0.5 * linking_score + 0.35 * pace_factor + 0.15 * energy_bonus)))

        try:
            f0 = librosa.yin(y, fmin=80, fmax=400, sr=sr)
            f0_clean = f0[np.isfinite(f0) & (f0 > 0)]
            if len(f0_clean) >= 10:
                pitch_std = float(np.std(f0_clean))
                pitch_mean = float(np.mean(f0_clean))
                cv = pitch_std / max(pitch_mean, 1.0)
                prosody_score = int(min(100, cv * 250))
            else:
                prosody_score = 0
        except Exception:
            prosody_score = None

        return {
            "fluency_score": fluency_score,
            "linking_score": linking_score,
            "prosody_score": prosody_score,
            "pace_wpm": round(pace_wpm, 1),
            "pause_count": pause_count,
        }


_singleton: ProsodyAnalyzer | None = None


def get_prosody_analyzer() -> ProsodyAnalyzer:
    global _singleton
    if _singleton is None:
        _singleton = ProsodyAnalyzer()
    return _singleton
