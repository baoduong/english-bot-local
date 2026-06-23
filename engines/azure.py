import os
from dotenv import load_dotenv
from analysis.phonemes import clean_word
from analysis.errors import classify_error, ANSI_GREEN, ANSI_YELLOW, ANSI_RED, ANSI_GRAY, ANSI_RESET

load_dotenv()

USE_AZURE = os.getenv("USE_AZURE_SPEECH", "false").lower() == "true"
AZURE_KEY = os.getenv("AZURE_SPEECH_KEY", "")
AZURE_REGION = os.getenv("AZURE_SPEECH_REGION", "southeastasia")

speechsdk = None
if USE_AZURE and AZURE_KEY:
    try:
        import azure.cognitiveservices.speech as speechsdk
        print("🔵 Azure Speech sẵn sàng (chỉ dùng cho câu/từ khó)")
    except ImportError:
        print("⚠️ Không tìm thấy azure-cognitiveservices-speech. Dùng Whisper cho tất cả.")
        USE_AZURE = False


def _ensure_wav(audio_path):
    """Convert audio sang WAV 16kHz mono — định dạng Azure Speech yêu cầu"""
    if audio_path.lower().endswith('.wav'):
        return audio_path
    try:
        from pydub import AudioSegment
        wav_path = audio_path.rsplit('.', 1)[0] + '_az.wav'
        audio = AudioSegment.from_file(audio_path)
        audio = audio.set_frame_rate(16000).set_channels(1)
        audio.export(wav_path, format='wav')
        return wav_path
    except Exception as e:
        print(f"⚠️ Không thể convert sang WAV: {e}. Dùng file gốc.")
        return audio_path


def analyze_with_azure(audio_path, reference_sentence):
    """Chấm điểm bằng Azure Pronunciation Assessment — chính xác nhất cho accent Việt"""
    wav_path = _ensure_wav(audio_path)
    try:
        speech_config = speechsdk.SpeechConfig(subscription=AZURE_KEY, region=AZURE_REGION)
        audio_config = speechsdk.audio.AudioConfig(filename=wav_path)

        pron_config = speechsdk.PronunciationAssessmentConfig(
            reference_text=reference_sentence,
            grading_system=speechsdk.PronunciationAssessmentGradingSystem.HundredMark,
            granularity=speechsdk.PronunciationAssessmentGranularity.Word,
            enable_miscue=True
        )
        recognizer = speechsdk.SpeechRecognizer(
            speech_config=speech_config,
            audio_config=audio_config,
            language="en-US"
        )
        pron_config.apply_to(recognizer)
        result = recognizer.recognize_once()
    finally:
        if wav_path != audio_path and os.path.exists(wav_path):
            os.remove(wav_path)

    transcript = result.text.strip()

    if result.reason != speechsdk.ResultReason.RecognizedSpeech:
        return transcript, 0, "[Không nhận diện được giọng nói]", "❌ Không nghe rõ. Hãy nói to và rõ hơn nhé!", [], [], {}

    pron_result = speechsdk.PronunciationAssessmentResult(result)
    word_map = {w.word.lower(): w for w in pron_result.words}

    formatted_words = []
    error_list = []
    problem_words = []
    error_types = []
    word_scores = {}
    correct_points = 0
    ref_words = reference_sentence.split()

    for orig_word in ref_words:
        clean = clean_word(orig_word)
        wd = word_map.get(clean)

        if wd is None or wd.error_type == "Omission":
            formatted_words.append(f"{ANSI_GRAY}[{orig_word}]{ANSI_RESET}")
            word_scores[clean] = {"score": 0, "passed": False, "heard": ""}
            error_list.append(f"🔲 Từ **{orig_word}**: Bị bỏ sót hoàn toàn.")
            problem_words.append(clean)
            error_types.append((clean, "omission"))
        elif wd.accuracy_score >= 80:
            formatted_words.append(f"{ANSI_GREEN}{orig_word}{ANSI_RESET}")
            correct_points += 1.0
            word_scores[clean] = {"score": wd.accuracy_score, "passed": True, "heard": wd.word.lower()}
        elif wd.accuracy_score >= 60:
            formatted_words.append(f"{ANSI_YELLOW}{orig_word}{ANSI_RESET}")
            correct_points += 0.6
            word_scores[clean] = {"score": wd.accuracy_score, "passed": False, "heard": wd.word.lower()}
            error_list.append(f"⚠️ Từ **{orig_word}**: Chưa chuẩn âm (Azure: {int(wd.accuracy_score)}/100).")
            problem_words.append(clean)
            error_types.append((clean, classify_error(orig_word, "")))
        else:
            formatted_words.append(f"{ANSI_RED}{orig_word}{ANSI_RESET}")
            correct_points += 0.1
            word_scores[clean] = {"score": wd.accuracy_score, "passed": False, "heard": wd.word.lower()}
            error_list.append(f"❌ Từ **{orig_word}**: Sai âm (Azure: {int(wd.accuracy_score)}/100).")
            problem_words.append(clean)
            error_types.append((clean, classify_error(orig_word, "")))

    total_words = len(ref_words)
    final_score = max(0, min(100, int((correct_points / total_words) * 100) if total_words > 0 else 0))
    ansi_feedback = " ".join(formatted_words)
    error_details = "\n".join(error_list) if error_list else "🎉 Xuất sắc! Phát âm không tì vết."
    return transcript, final_score, ansi_feedback, error_details, problem_words, error_types, word_scores


def analyze_single_word_azure(audio_path, target_word):
    """Chấm 1 từ bằng Azure — dùng trong Word Drill Mode"""
    wav_path = _ensure_wav(audio_path)
    try:
        speech_config = speechsdk.SpeechConfig(subscription=AZURE_KEY, region=AZURE_REGION)
        audio_config = speechsdk.audio.AudioConfig(filename=wav_path)

        pron_config = speechsdk.PronunciationAssessmentConfig(
            reference_text=target_word,
            grading_system=speechsdk.PronunciationAssessmentGradingSystem.HundredMark,
            granularity=speechsdk.PronunciationAssessmentGranularity.Phoneme,
            enable_miscue=True
        )
        recognizer = speechsdk.SpeechRecognizer(
            speech_config=speech_config,
            audio_config=audio_config,
            language="en-US"
        )
        pron_config.apply_to(recognizer)
        result = recognizer.recognize_once()
    finally:
        if wav_path != audio_path and os.path.exists(wav_path):
            os.remove(wav_path)

    if result.reason != speechsdk.ResultReason.RecognizedSpeech:
        return False, 0.0, ""

    pron_result = speechsdk.PronunciationAssessmentResult(result)
    if not pron_result.words:
        return False, 0.0, result.text.strip().lower()

    accuracy = pron_result.words[0].accuracy_score  # thang 0-100
    passed = accuracy >= 70
    return passed, accuracy / 100.0, result.text.strip().lower()
