from engines.ollama import assess_difficulty
from engines.azure import USE_AZURE, AZURE_KEY, analyze_with_azure, analyze_single_word_azure
from engines.whisper import analyze_with_whisper, analyze_single_word_whisper


def _should_use_azure(text):
    """Quyết định có nên dùng Azure không — chỉ dùng cho câu/từ khó"""
    if not USE_AZURE or not AZURE_KEY:
        return False
    return assess_difficulty(text) == "complex"


def analyze_audio(audio_path, reference_sentence):
    """Entry point chính — smart routing: Ollama phân loại độ khó → Azure (khó) hoặc Whisper (dễ)"""
    if _should_use_azure(reference_sentence):
        print(f"🔵 Azure: \"{reference_sentence[:40]}...\"")
        return analyze_with_azure(audio_path, reference_sentence)
    print(f"🟢 Whisper: \"{reference_sentence[:40]}...\"")
    return analyze_with_whisper(audio_path, reference_sentence)


def analyze_single_word(audio_path, target_word):
    """Entry point cho Word Drill — smart routing theo độ khó từ"""
    if _should_use_azure(target_word):
        print(f"🔵 Azure drill: \"{target_word}\"")
        return analyze_single_word_azure(audio_path, target_word)
    print(f"🟢 Whisper drill: \"{target_word}\"")
    return analyze_single_word_whisper(audio_path, target_word)
