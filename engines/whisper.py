import whisper
import difflib
from analysis.phonemes import clean_word, phoneme_similarity
from analysis.errors import classify_error, ANSI_GREEN, ANSI_YELLOW, ANSI_RED, ANSI_GRAY, ANSI_RESET, get_articulatory_tip

print("🔄 Đang nạp mô hình Whisper vào RAM (Vui lòng đợi)...")
whisper_model = whisper.load_model("small")
print("🟩 Mô hình Whisper đã sẵn sàng!")


def analyze_with_whisper(audio_path, reference_sentence):
    """Chấm điểm bằng Whisper small + phoneme similarity (chạy local, không cần internet)"""
    result = whisper_model.transcribe(audio_path, word_timestamps=True, language="en")

    detected_words = []
    for segment in result.get("segments", []):
        for w in segment.get("words", []):
            detected_words.append({
                "text": clean_word(w["word"]),
                "original": w["word"].strip(),
                "confidence": w["probability"]
            })

    ref_words_clean = [clean_word(w) for w in reference_sentence.split()]
    ref_words_original = reference_sentence.split()
    detected_texts_clean = [w["text"] for w in detected_words]

    matcher = difflib.SequenceMatcher(None, ref_words_clean, detected_texts_clean)

    formatted_words = []
    error_list = []
    problem_words = []
    error_types = []
    word_scores = {}

    total_words = len(ref_words_clean)
    correct_points = 0

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == 'equal':
            for idx_ref, idx_det in zip(range(i1, i2), range(j1, j2)):
                word_data = detected_words[idx_det]
                orig_text = ref_words_original[idx_ref]

                if word_data["confidence"] >= 0.75:
                    formatted_words.append(f"{ANSI_GREEN}{orig_text}{ANSI_RESET}")
                    correct_points += 1.0
                    word_scores[clean_word(orig_text)] = {"score": 100, "passed": True}
                elif word_data["confidence"] >= 0.50:
                    formatted_words.append(f"{ANSI_YELLOW}{orig_text}{ANSI_RESET}")
                    correct_points += 0.6
                    word_scores[clean_word(orig_text)] = {"score": 60, "passed": False}
                    err_type = classify_error(orig_text, word_data["text"])
                    error_types.append((clean_word(orig_text), err_type))
                    tip = get_articulatory_tip(err_type)
                    error_list.append(f"⚠️ Từ **{orig_text}**: Chưa chuẩn.\n{tip}")
                    problem_words.append(clean_word(orig_text))
                else:
                    phon_sim = phoneme_similarity(word_data["text"], orig_text)
                    if phon_sim >= 0.75:
                        formatted_words.append(f"{ANSI_YELLOW}{orig_text}{ANSI_RESET}")
                        correct_points += 0.5
                        word_scores[clean_word(orig_text)] = {"score": 50, "passed": False}
                        err_type = classify_error(orig_text, word_data["text"])
                        error_types.append((clean_word(orig_text), err_type))
                        tip = get_articulatory_tip(err_type)
                        error_list.append(f"⚠️ Từ **{orig_text}**: Gần đúng nhưng chưa rõ.\n{tip}")
                        problem_words.append(clean_word(orig_text))
                    else:
                        formatted_words.append(f"{ANSI_RED}{orig_text}{ANSI_RESET}")
                        correct_points += 0.1
                        word_scores[clean_word(orig_text)] = {"score": 10, "passed": False}
                        err_type = classify_error(orig_text, word_data["text"])
                        error_types.append((clean_word(orig_text), err_type))
                        tip = get_articulatory_tip(err_type)
                        error_list.append(f"❌ Từ **{orig_text}**: Phát âm sai.\n{tip}")
                        problem_words.append(clean_word(orig_text))

        elif tag == 'replace':
            pairs = list(zip(range(i1, i2), range(j1, j2)))
            for idx_ref, idx_det in pairs:
                expected = ref_words_original[idx_ref]
                heard_word = detected_words[idx_det]["text"]
                phon_sim = phoneme_similarity(heard_word, expected)
                if phon_sim >= 0.70:
                    formatted_words.append(f"{ANSI_YELLOW}{expected}{ANSI_RESET}")
                    correct_points += 0.5
                    word_scores[clean_word(expected)] = {"score": 50, "passed": False}
                    tip = get_articulatory_tip(classify_error(expected, heard_word))
                    error_list.append(f"⚠️ Từ **{expected}**: Gần đúng (AI nghe: *{heard_word}*).\n{tip}")
                    problem_words.append(clean_word(expected))
                    error_types.append((clean_word(expected), classify_error(expected, heard_word)))
                else:
                    formatted_words.append(f"{ANSI_RED}{expected}{ANSI_RESET}")
                    correct_points += 0.0
                    word_scores[clean_word(expected)] = {"score": 0, "passed": False}
                    tip = get_articulatory_tip(classify_error(expected, heard_word))
                    error_list.append(f"❌ Từ **{expected}**: Sai âm (AI nghe: *{heard_word}*).\n{tip}")
                    problem_words.append(clean_word(expected))
                    error_types.append((clean_word(expected), classify_error(expected, heard_word)))
            for idx in range(i1 + len(pairs), i2):
                missing_word = ref_words_original[idx]
                formatted_words.append(f"{ANSI_GRAY}[{missing_word}]{ANSI_RESET}")
                word_scores[clean_word(missing_word)] = {"score": 0, "passed": False}
                error_list.append(f"🔲 Từ **{missing_word}**: Bị nuốt hoàn toàn.\n{get_articulatory_tip('omission')}")
                problem_words.append(clean_word(missing_word))
                error_types.append((clean_word(missing_word), "omission"))

        elif tag == 'delete':
            for idx in range(i1, i2):
                missing_word = ref_words_original[idx]
                formatted_words.append(f"{ANSI_GRAY}[{missing_word}]{ANSI_RESET}")
                word_scores[clean_word(missing_word)] = {"score": 0, "passed": False}
                error_list.append(f"🔲 Từ **{missing_word}**: Bị nuốt hoàn toàn.\n{get_articulatory_tip('omission')}")
                problem_words.append(clean_word(missing_word))
                error_types.append((clean_word(missing_word), "omission"))

        elif tag == 'insert':
            for idx in range(j1, j2):
                extra_word = detected_words[idx]["original"]
                formatted_words.append(f"{ANSI_RED}+{extra_word}{ANSI_RESET}")

    if total_words > 0:
        final_score = int((correct_points / total_words) * 100)
    else:
        final_score = 0

    final_score = max(0, min(100, final_score))

    ansi_feedback = " ".join(formatted_words)
    error_details = "\n".join(error_list) if error_list else "🎉 Xuất sắc! Phát âm không tì vết."

    return final_score, ansi_feedback, error_details, problem_words, error_types, word_scores


def analyze_single_word_whisper(audio_path, target_word):
    """Chấm 1 từ bằng Whisper + phoneme similarity"""
    target_clean = clean_word(target_word)

    result = whisper_model.transcribe(
        audio_path,
        word_timestamps=True,
        language="en",
        initial_prompt=f"The speaker is practicing the word: {target_word}"
    )

    all_words = []
    for segment in result.get("segments", []):
        for w in segment.get("words", []):
            all_words.append({
                "text": clean_word(w["word"]),
                "confidence": w["probability"]
            })

    if not all_words:
        return False, 0.0, ""

    best_match = None
    best_prob = 0.0
    for w in all_words:
        if w["text"] == target_clean:
            best_match = w
            best_prob = w["confidence"]
            break

    if not best_match and all_words:
        best_phon = 0.0
        for w in all_words:
            ps = phoneme_similarity(w["text"], target_clean)
            if ps > best_phon:
                best_phon = ps
                best_match = w
                best_prob = w["confidence"]

    heard = best_match["text"] if best_match else ""

    phon_score = 1.0 if heard == target_clean else phoneme_similarity(heard, target_clean)
    prob_score = best_prob

    combined = phon_score * 0.75 + prob_score * 0.25

    passed = combined >= 0.60

    return passed, combined, heard
