from __future__ import annotations

import os
import threading

_MODEL_NAME = "facebook/wav2vec2-lv-60-espeak-cv-ft"

if "/opt/homebrew/bin" not in os.environ.get("PATH", ""):
    os.environ["PATH"] = "/opt/homebrew/bin:" + os.environ.get("PATH", "")


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
