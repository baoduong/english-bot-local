"""engines package — Speech recognition, LLM, and TTS engines."""

from engines.ollama import assess_difficulty, _ollama_generate, _ollama_async, OLLAMA_MODEL
from engines.tts import generate_sample_audio
# Whisper and Azure are imported on-demand to avoid loading models unnecessarily
# Use: from engines.whisper import analyze_with_whisper, analyze_single_word_whisper
# Use: from engines.azure import analyze_with_azure, analyze_single_word_azure
