from __future__ import annotations

import os
import shutil
import sys
import threading

_MODEL_NAME = "facebook/wav2vec2-lv-60-espeak-cv-ft"


def _ensure_espeak_ng_in_path() -> None:
    if shutil.which("espeak-ng") is not None:
        return

    candidates: list[str] = []
    if sys.platform == "darwin":
        candidates = ["/opt/homebrew/bin", "/usr/local/bin"]
    elif sys.platform == "win32":
        candidates = [
            r"C:\Program Files\eSpeak NG",
            r"C:\Program Files (x86)\eSpeak NG",
        ]
    elif sys.platform.startswith("linux"):
        candidates = ["/usr/bin", "/usr/local/bin"]

    current_path = os.environ.get("PATH", "")
    for candidate in candidates:
        if os.path.isdir(candidate) and candidate not in current_path:
            os.environ["PATH"] = candidate + os.pathsep + current_path
            if shutil.which("espeak-ng") is not None:
                return
            current_path = os.environ["PATH"]


_ensure_espeak_ng_in_path()


class PhonemeRecognizer:
    def __init__(self) -> None:
        self._processor = None
        self._model = None
        self._lock = threading.Lock()
        self._loaded = False

    def _ensure_loaded(self) -> None:
        if self._loaded:
            return
        with self._lock:
            if self._loaded:
                return
            from transformers import AutoModelForCTC, AutoProcessor

            self._processor = AutoProcessor.from_pretrained(_MODEL_NAME)
            self._model = AutoModelForCTC.from_pretrained(_MODEL_NAME)
            self._model.eval()
            self._loaded = True

    def load(self) -> None:
        self._ensure_loaded()

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    def recognize(self, audio_path: str) -> str:
        self._ensure_loaded()

        import librosa
        import torch

        audio, _ = librosa.load(audio_path, sr=16000)
        inputs = self._processor(audio, sampling_rate=16000, return_tensors="pt")
        with torch.no_grad():
            logits = self._model(inputs.input_values).logits
        ids = torch.argmax(logits, dim=-1)
        return self._processor.batch_decode(ids)[0].strip()


_singleton: PhonemeRecognizer | None = None


def get_phoneme_recognizer() -> PhonemeRecognizer:
    global _singleton
    if _singleton is None:
        _singleton = PhonemeRecognizer()
    return _singleton
