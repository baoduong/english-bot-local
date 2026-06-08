import whisper
import difflib
import eng_to_ipa as ipa
import ollama
import edge_tts
import discord
import os
from dotenv import load_dotenv

load_dotenv()

# ============================================================
# CẤU HÌNH ENGINE CHẤM ĐIỂM PHÁT ÂM
# Đặt USE_AZURE_SPEECH=true trong .env để dùng Azure Speech (chính xác hơn)
# Mặc định dùng Whisper local (không cần internet, không tốn tiền)
# ============================================================
USE_AZURE = os.getenv("USE_AZURE_SPEECH", "false").lower() == "true"
AZURE_KEY = os.getenv("AZURE_SPEECH_KEY", "")
AZURE_REGION = os.getenv("AZURE_SPEECH_REGION", "southeastasia")

# Luôn tải Whisper — dùng cho câu dễ ngay cả khi Azure được bật (tiết kiệm API)
print("🔄 Đang nạp mô hình Whisper vào RAM (Vui lòng đợi)...")
whisper_model = whisper.load_model("small")
print("🟩 Mô hình Whisper đã sẵn sàng!")

# Import Azure SDK nếu được bật
if USE_AZURE and AZURE_KEY:
    try:
        import azure.cognitiveservices.speech as speechsdk
        print("🔵 Azure Speech sẵn sàng (chỉ dùng cho câu/từ khó)")
    except ImportError:
        print("⚠️ Không tìm thấy azure-cognitiveservices-speech. Dùng Whisper cho tất cả.")
        USE_AZURE = False

# Cache kết quả phân tích độ khó — tránh gọi Ollama lại cho cùng câu
_difficulty_cache = {}

OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma4:31b-cloud")

def assess_difficulty(text):
    """
    Dùng Ollama phân tích độ khó phát âm của câu/từ cho người Việt.
    Trả về: "simple" hoặc "complex"
    Kết quả được cache để không gọi lại Ollama cho cùng text.
    """
    cache_key = text.strip().lower()
    if cache_key in _difficulty_cache:
        return _difficulty_cache[cache_key]
    
    # Heuristic nhanh cho từ đơn ngắn — không cần gọi LLM
    words = text.strip().split()
    if len(words) == 1 and len(words[0]) <= 6:
        _difficulty_cache[cache_key] = "simple"
        return "simple"
    
    prompt = f"""Analyze pronunciation difficulty of this English text for a Vietnamese speaker.
Text: "{text}"

Consider: silent letters, consonant clusters (th, str, ght), unusual vowel sounds, word length, stress patterns.

Reply with ONLY one word: "simple" or "complex". No explanation."""

    try:
        response = ollama.generate(model=OLLAMA_MODEL, prompt=prompt, options={"temperature": 0})
        answer = response["response"].strip().lower()
        result = "complex" if "complex" in answer else "simple"
    except Exception as e:
        print(f"⚠️ Ollama assess_difficulty error: {e}. Mặc định: simple")
        result = "simple"
    
    _difficulty_cache[cache_key] = result
    return result

def _should_use_azure(text):
    """Quyết định có nên dùng Azure không — chỉ dùng cho câu/từ khó"""
    if not USE_AZURE or not AZURE_KEY:
        return False
    return assess_difficulty(text) == "complex"

def clean_word(word):
    """Hàm phụ trợ để xóa dấu câu và viết thường nhằm so khớp chính xác"""
    return word.strip().lower().replace(".", "").replace(",", "").replace("?", "").replace("!", "")

def phoneme_similarity(word1, word2):
    """
    Tính độ tương đồng âm vị (IPA) giữa 2 từ, thang 0.0 - 1.0.
    Chính xác hơn so sánh ký tự vì phản ánh cách phát âm thực tế.
    Ví dụ: "negotiate" vs "negoshate" → ~0.85 (gần đúng, không bị đỏ oan)
    """
    p1 = ipa.convert(clean_word(word1))
    p2 = ipa.convert(clean_word(word2))
    # Fallback sang so sánh ký tự nếu từ không có trong từ điển IPA (có dấu *)
    if '*' in p1 or '*' in p2:
        return difflib.SequenceMatcher(None, clean_word(word1), clean_word(word2)).ratio()
    return difflib.SequenceMatcher(None, p1, p2).ratio()

def classify_error(expected_word, heard_word):
    """
    Phân loại lỗi phát âm dựa trên pattern — phát hiện điểm yếu lặp lại.
    Trả về: error_type string mô tả dạng lỗi.
    Các pattern phổ biến của người Việt nói tiếng Anh.
    """
    expected = clean_word(expected_word)
    heard = clean_word(heard_word) if heard_word else ""
    
    if not heard:
        return "omission"  # Bỏ sót hoàn toàn
    
    # Nuốt phụ âm cuối (s, t, d, z, k, p) — lỗi phổ biến nhất của người Việt
    if expected.rstrip('stdzckp') == heard or (len(expected) > 2 and expected[:-1] == heard):
        return "final_consonant"
    
    # Lỗi âm /θ/ (th → t/f/s): think→tink, three→tree
    if 'th' in expected and ('th' not in heard or heard.replace('th', 't') == expected.replace('th', 't')):
        return "th_sound"
    
    # Lỗi r/l lẫn lộn
    if expected.replace('r', 'l') == heard or expected.replace('l', 'r') == heard:
        return "r_l_confusion"
    
    # Lỗi trọng âm / nguyên âm (từ nghe gần đúng nhưng méo nguyên âm)
    ipa_exp = ipa.convert(expected)
    ipa_hrd = ipa.convert(heard)
    if '*' not in ipa_exp and '*' not in ipa_hrd:
        consonants_match = ''.join(c for c in ipa_exp if c in 'bdfghjklmnprstvwzðθʃʒŋtʃdʒ') == \
                          ''.join(c for c in ipa_hrd if c in 'bdfghjklmnprstvwzðθʃʒŋtʃdʒ')
        if consonants_match and ipa_exp != ipa_hrd:
            return "vowel_stress"
    
    # Lỗi sh/ch (ship→sip, church→churt)
    if 'sh' in expected and 's' in heard and 'sh' not in heard:
        return "sh_sound"
    
    return "general"  # Lỗi không phân loại được cụ thể

# Mô tả lỗi bằng tiếng Việt để hiển thị trong !stats
ERROR_TYPE_LABELS = {
    "omission": "🔇 Nuốt/bỏ sót từ",
    "final_consonant": "🔚 Nuốt phụ âm cuối (s, t, d...)",
    "th_sound": "👅 Lỗi âm /θ/ (th → t/f)",
    "r_l_confusion": "🔄 Lẫn r/l",
    "vowel_stress": "🎵 Sai nguyên âm/trọng âm",
    "sh_sound": "💨 Lỗi âm sh/ch",
    "general": "❓ Lỗi phát âm chung",
}

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

# Bảng màu ANSI dùng chung cho cả 2 engine
ANSI_GREEN  = "\u001b[0;32m"
ANSI_YELLOW = "\u001b[0;33m"
ANSI_RED    = "\u001b[0;31m"
ANSI_GRAY   = "\u001b[0;30m"
ANSI_RESET  = "\u001b[0m"

def analyze_audio_with_whisper(audio_path, reference_sentence):
    """Entry point chính — smart routing: Ollama phân loại độ khó → Azure (khó) hoặc Whisper (dễ)"""
    if _should_use_azure(reference_sentence):
        print(f"🔵 Azure: \"{reference_sentence[:40]}...\"")
        return _analyze_with_azure(audio_path, reference_sentence)
    print(f"🟢 Whisper: \"{reference_sentence[:40]}...\"")
    return _analyze_with_whisper(audio_path, reference_sentence)

def analyze_single_word(audio_path, target_word):
    """Entry point cho Word Drill — smart routing theo độ khó từ"""
    if _should_use_azure(target_word):
        print(f"🔵 Azure drill: \"{target_word}\"")
        return _analyze_single_word_azure(audio_path, target_word)
    print(f"🟢 Whisper drill: \"{target_word}\"")
    return _analyze_single_word_whisper(audio_path, target_word)

# ============================================================
# ENGINE 1: WHISPER LOCAL (mặc định)
# ============================================================

def _analyze_with_whisper(audio_path, reference_sentence):
    """Chấm điểm bằng Whisper small + phoneme similarity (chạy local, không cần internet)"""
    result = whisper_model.transcribe(audio_path, word_timestamps=True, language="en")
    
    detected_words = []
    for segment in result.get("segments", []):
        for w in segment.get("words", []):
            detected_words.append({
                "text": clean_word(w["word"]),
                "original": w["word"].strip(),
                "confidence": w["probability"] # Độ tự tin từ 0.0 đến 1.0 của AI
            })
            
    # Tách danh sách từ thô của câu gốc và câu AI nghe được
    ref_words_clean = [clean_word(w) for w in reference_sentence.split()]
    ref_words_original = reference_sentence.split()
    detected_texts_clean = [w["text"] for w in detected_words]
    
    # Sử dụng thuật toán so khớp chuỗi SequenceMatcher
    matcher = difflib.SequenceMatcher(None, ref_words_clean, detected_texts_clean)
    
    formatted_words = []
    error_list = []
    problem_words = []  # Danh sách các từ cần drill riêng lẻ (đỏ + vàng)
    error_types = []    # Danh sách (word, error_type) để track pattern
    
    # Các biến phục vụ tính điểm
    total_words = len(ref_words_clean)
    correct_points = 0
    
    # Duyệt qua các khối thay đổi (Opcodes) giữa 2 câu
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == 'equal':
            # TỪ ĐÚNG VỊ TRÍ TRONG CÂU -> Check tiếp độ tự tin (Confidence)
            for idx_ref, idx_det in zip(range(i1, i2), range(j1, j2)):
                word_data = detected_words[idx_det]
                orig_text = ref_words_original[idx_ref]
                
                if word_data["confidence"] >= 0.75:
                    # Phát âm tốt (Xanh lá) — ngưỡng hạ xuống 0.75 vì small model chính xác hơn
                    formatted_words.append(f"{ANSI_GREEN}{orig_text}{ANSI_RESET}")
                    correct_points += 1.0
                elif word_data["confidence"] >= 0.50:
                    # Phát âm hơi lài, yếu trọng âm (Vàng)
                    formatted_words.append(f"{ANSI_YELLOW}{orig_text}{ANSI_RESET}")
                    correct_points += 0.6
                    error_list.append(f"⚠️ Từ **{orig_text}**: Bạn phát âm chưa rõ trọng âm hoặc nuốt âm đuôi.")
                    problem_words.append(clean_word(orig_text))
                    error_types.append((clean_word(orig_text), classify_error(orig_text, word_data["text"])))
                else:
                    # Confidence thấp nhưng kiểm tra thêm bằng phoneme — tránh đỏ oan
                    phon_sim = phoneme_similarity(word_data["text"], orig_text)
                    if phon_sim >= 0.75:
                        # Whisper không chắc nhưng âm vị gần đúng → vàng
                        formatted_words.append(f"{ANSI_YELLOW}{orig_text}{ANSI_RESET}")
                        correct_points += 0.5
                        error_list.append(f"⚠️ Từ **{orig_text}**: Gần đúng nhưng cần phát âm rõ ràng hơn.")
                        problem_words.append(clean_word(orig_text))
                        error_types.append((clean_word(orig_text), classify_error(orig_text, word_data["text"])))
                    else:
                        # AI phân vân nặng và âm vị cũng lệch xa (Đỏ)
                        formatted_words.append(f"{ANSI_RED}{orig_text}{ANSI_RESET}")
                        correct_points += 0.1
                        error_list.append(f"❌ Từ **{orig_text}**: Phát âm sai hoặc méo tiếng, AI khó nhận diện.")
                        problem_words.append(clean_word(orig_text))
                        error_types.append((clean_word(orig_text), classify_error(orig_text, word_data["text"])))
                    
        elif tag == 'replace':
            # TỪ BỊ ĐỌC SAI — so sánh âm vị để tránh phạt oan vì accent
            pairs = list(zip(range(i1, i2), range(j1, j2)))
            for idx_ref, idx_det in pairs:
                expected = ref_words_original[idx_ref]
                heard_word = detected_words[idx_det]["text"]
                phon_sim = phoneme_similarity(heard_word, expected)
                if phon_sim >= 0.70:
                    # Gần đúng về âm vị → vàng (accent nhẹ, không phải sai hoàn toàn)
                    formatted_words.append(f"{ANSI_YELLOW}{expected}{ANSI_RESET}")
                    correct_points += 0.5
                    error_list.append(f"⚠️ Từ **{expected}**: Gần đúng (AI nghe thành *{heard_word}*), cần phát âm rõ hơn.")
                    problem_words.append(clean_word(expected))
                    error_types.append((clean_word(expected), classify_error(expected, heard_word)))
                else:
                    # Sai xa về âm vị → đỏ
                    formatted_words.append(f"{ANSI_RED}{expected}{ANSI_RESET}")
                    correct_points += 0.0
                    error_list.append(f"❌ Từ **{expected}**: Sai âm (AI nghe thành *{heard_word}*).")
                    problem_words.append(clean_word(expected))
                    error_types.append((clean_word(expected), classify_error(expected, heard_word)))
            # Nếu câu gốc dài hơn → phần dư bị nuốt hoàn toàn
            for idx in range(i1 + len(pairs), i2):
                missing_word = ref_words_original[idx]
                formatted_words.append(f"{ANSI_GRAY}[{missing_word}]{ANSI_RESET}")
                error_list.append(f"🔲 Từ **{missing_word}**: Bị nuốt hoàn toàn.")
                problem_words.append(clean_word(missing_word))
                error_types.append((clean_word(missing_word), "omission"))

        elif tag == 'delete':
            for idx in range(i1, i2):
                missing_word = ref_words_original[idx]
                formatted_words.append(f"{ANSI_GRAY}[{missing_word}]{ANSI_RESET}")
                error_list.append(f"🔲 Từ **{missing_word}**: Bạn bị bỏ sót hoặc nuốt chữ hoàn toàn.")
                problem_words.append(clean_word(missing_word))
                error_types.append((clean_word(missing_word), "omission"))
                
        elif tag == 'insert':
            # TỪ ĐỌC THỪA (Tự dưng nói thêm từ lạ hoặc phát âm quá sai khiến AI nghe nhầm ra từ khác)
            for idx in range(j1, j2):
                extra_word = detected_words[idx]["original"]
                formatted_words.append(f"{ANSI_RED}+{extra_word}{ANSI_RESET}")
                # Không tăng điểm cho từ thừa
                
    # 3. Tính toán điểm số tổng quan theo thang điểm 100
    if total_words > 0:
        final_score = int((correct_points / total_words) * 100)
    else:
        final_score = 0
        
    # Giới hạn điểm trong khoảng 0 - 100
    final_score = max(0, min(100, final_score))
    
    ansi_feedback = " ".join(formatted_words)
    error_details = "\n".join(error_list) if error_list else "🎉 Xuất sắc! Phát âm không tì vết."
    
    return final_score, ansi_feedback, error_details, problem_words, error_types

def _analyze_single_word_whisper(audio_path, target_word):
    """Chấm 1 từ bằng Whisper + phoneme similarity"""
    target_clean = clean_word(target_word)
    
    # Hint cho Whisper biết user đang nói từ gì — giảm hallucination trên audio ngắn
    result = whisper_model.transcribe(
        audio_path,
        word_timestamps=True,
        language="en",
        initial_prompt=f"The speaker is practicing the word: {target_word}"
    )
    
    # Gom tất cả từ AI nghe được
    all_words = []
    for segment in result.get("segments", []):
        for w in segment.get("words", []):
            all_words.append({
                "text": clean_word(w["word"]),
                "confidence": w["probability"]
            })
    
    if not all_words:
        return False, 0.0, ""
    
    # Tìm từ khớp nhất với target trong những gì AI nghe được
    best_match = None
    best_prob = 0.0
    for w in all_words:
        if w["text"] == target_clean:
            best_match = w
            best_prob = w["confidence"]
            break
    
    # Nếu không tìm thấy chính xác, tìm từ có phoneme gần nhất
    if not best_match and all_words:
        best_phon = 0.0
        for w in all_words:
            ps = phoneme_similarity(w["text"], target_clean)
            if ps > best_phon:
                best_phon = ps
                best_match = w
                best_prob = w["confidence"]
    
    heard = best_match["text"] if best_match else ""
    
    # ── Tính combined score: kết hợp "nghe đúng từ" + "giọng rõ ràng" ──
    # Điều kiện CẦN: phoneme match (Whisper nghe có gần đúng không?)
    phon_score = 1.0 if heard == target_clean else phoneme_similarity(heard, target_clean)
    # Điều kiện ĐỦ: probability (giọng nói rõ ràng không?)
    prob_score = best_prob
    
    # Combined: phoneme chiếm 65% (quan trọng hơn), probability 35%
    # "brief" đúng + prob 2%:  1.0*0.65 + 0.02*0.35 = 0.657 → 65% → PASS
    # "live" sai + prob 90%:   0.4*0.65 + 0.90*0.35 = 0.575 → 57% → FAIL
    # "brief" đúng + prob 80%: 1.0*0.65 + 0.80*0.35 = 0.930 → 93% → PASS
    combined = phon_score * 0.65 + prob_score * 0.35
    
    # Pass khi combined ≥ 0.60 — cả 2 yếu tố đều phải đạt mức tối thiểu
    passed = combined >= 0.60
    
    return passed, best_confidence, heard


# ============================================================
# ENGINE 2: AZURE SPEECH PRONUNCIATION ASSESSMENT
# Yêu cầu: AZURE_SPEECH_KEY + AZURE_SPEECH_REGION trong .env
#          pip install azure-cognitiveservices-speech pydub
# Ưu điểm: điểm AccuracyScore thực sự đo chất lượng phát âm,
#           không phải confidence của ASR như Whisper
# ============================================================

def _analyze_with_azure(audio_path, reference_sentence):
    """Chấm điểm bằng Azure Pronunciation Assessment — chính xác nhất cho accent Việt"""
    wav_path = _ensure_wav(audio_path)
    try:
        speech_config = speechsdk.SpeechConfig(subscription=AZURE_KEY, region=AZURE_REGION)
        audio_config  = speechsdk.audio.AudioConfig(filename=wav_path)

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

    if result.reason != speechsdk.ResultReason.RecognizedSpeech:
        return 0, "[Không nhận diện được giọng nói]", "❌ Không nghe rõ. Hãy nói to và rõ hơn nhé!", [], []

    pron_result = speechsdk.PronunciationAssessmentResult(result)
    # Tạo dict tra nhanh: word_text → word_result
    word_map = {w.word.lower(): w for w in pron_result.words}

    formatted_words = []
    error_list = []
    problem_words = []
    error_types = []
    correct_points = 0
    ref_words = reference_sentence.split()

    for orig_word in ref_words:
        clean = clean_word(orig_word)
        wd = word_map.get(clean)

        if wd is None or wd.error_type == "Omission":
            formatted_words.append(f"{ANSI_GRAY}[{orig_word}]{ANSI_RESET}")
            error_list.append(f"🔲 Từ **{orig_word}**: Bị bỏ sót hoàn toàn.")
            problem_words.append(clean)
            error_types.append((clean, "omission"))
        elif wd.accuracy_score >= 80:
            formatted_words.append(f"{ANSI_GREEN}{orig_word}{ANSI_RESET}")
            correct_points += 1.0
        elif wd.accuracy_score >= 60:
            formatted_words.append(f"{ANSI_YELLOW}{orig_word}{ANSI_RESET}")
            correct_points += 0.6
            error_list.append(f"⚠️ Từ **{orig_word}**: Chưa chuẩn âm (Azure: {int(wd.accuracy_score)}/100).")
            problem_words.append(clean)
            error_types.append((clean, classify_error(orig_word, "")))
        else:
            formatted_words.append(f"{ANSI_RED}{orig_word}{ANSI_RESET}")
            correct_points += 0.1
            error_list.append(f"❌ Từ **{orig_word}**: Sai âm (Azure: {int(wd.accuracy_score)}/100).")
            problem_words.append(clean)
            error_types.append((clean, classify_error(orig_word, "")))

    total_words = len(ref_words)
    final_score = max(0, min(100, int((correct_points / total_words) * 100) if total_words > 0 else 0))
    ansi_feedback = " ".join(formatted_words)
    error_details = "\n".join(error_list) if error_list else "🎉 Xuất sắc! Phát âm không tì vết."
    return final_score, ansi_feedback, error_details, problem_words, error_types


def _analyze_single_word_azure(audio_path, target_word):
    """Chấm 1 từ bằng Azure — dùng trong Word Drill Mode"""
    wav_path = _ensure_wav(audio_path)
    try:
        speech_config = speechsdk.SpeechConfig(subscription=AZURE_KEY, region=AZURE_REGION)
        audio_config  = speechsdk.audio.AudioConfig(filename=wav_path)

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


async def generate_sample_audio(text, output_path, rate="-20%"):
    """Tạo file audio đọc mẫu bằng Edge-TTS. Trả về True nếu thành công."""
    try:
        communicate = edge_tts.Communicate(text, "en-US-ChristopherNeural", rate=rate)
        await communicate.save(output_path)
        return True
    except Exception as e:
        print(f"Lỗi sinh âm thanh mẫu Edge-TTS: {e}")
        return False


async def send_new_word_tutorial(channel, sentence, new_word):
    """
    Hàm Tiền giáo dục (Pre-teaching) cho từ mới hoặc từ bị kẹt:
    1. Gọi Llama 3.2 viết mẹo khẩu hình mỳ ăn liền.
    2. Gọi Edge-TTS tạo file âm thanh đọc mẫu chuẩn Microsoft Neural.
    3. Gửi cả 2 lên kênh Discord.
    """
    # 1. Sử dụng Llama 3.2 để lấy mẹo phát âm nhanh bằng Tiếng Việt
    prompt = f"""
    Học viên chuẩn bị luyện câu có chứa từ: "{new_word}".
    Hãy viết hướng dẫn phát âm từ "{new_word}" bằng tiếng Việt:
    - Cách bẻ nhỏ âm tiết và vị trí đánh trọng âm.
    - Một mẹo đặt lưỡi hoặc răng để phát âm đúng nhất.
    Viết cực kỳ ngắn gọn, dưới 50 từ, trình bày bằng các gạch đầu dòng rõ ràng.
    """
    try:
        response = ollama.generate(model=OLLAMA_MODEL, prompt=prompt)
        teacher_tip = response["response"]
    except Exception as e:
        print(f"Lỗi gọi Ollama: {e}")
        teacher_tip = f"• Hãy chú ý nhấn đúng trọng âm của từ: **{new_word}**."

    # 2. Tạo file audio đọc mẫu chất lượng cao (Giọng nam Mỹ: Christopher)
    output_audio_path = "teacher_sample.mp3"
    has_audio = await generate_sample_audio(sentence, output_audio_path)

    # 3. Gửi gói cứu trợ giao diện lên Discord
    await channel.send(
        f"🆕 **HỌC TỪ MỚI CÙNG GIÁO VIÊN AI:**\n"
        f"🎯 Từ tiêu điểm: **{new_word.upper()}**\n\n"
        f"{teacher_tip}\n"
        f"👇 *Nghe kỹ file phát âm mẫu dưới đây rồi giữ micro bắt chước đọc lại nhé:*"
    )
    
    await channel.send(f"👉 **`{sentence}`**")
    
    # Gửi đính kèm file nói mẫu MP3 nếu tạo thành công
    if has_audio and os.path.exists(output_audio_path):
        await channel.send(file=discord.File(output_audio_path))
        # Xóa file sau khi gửi để sạch thư mục
        try: os.remove(output_audio_path)
        except: pass
