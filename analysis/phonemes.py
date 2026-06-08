import difflib
import eng_to_ipa as ipa


def clean_word(word):
    """Xóa dấu câu và viết thường nhằm so khớp chính xác"""
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


# IPA consonant/vowel sets for Vietnamese speaker error detection
_IPA_CONSONANTS = set('bdfghjklmnprstvwzðθʃʒŋʧʤ')
_IPA_VOWELS = set('æɑɒɔəɛɜɪiɵʊuʌeɝoaɚ')


def extract_phoneme_errors(expected_word, heard_word):
    """Diff IPA transcriptions to find specific phoneme substitutions/deletions.
    Returns list of (expected_phoneme, heard_phoneme_or_empty) tuples.
    Only returns meaningful IPA characters, skipping stress marks and boundaries."""
    if not heard_word:
        return []

    ipa_exp = ipa.convert(clean_word(expected_word))
    ipa_hrd = ipa.convert(clean_word(heard_word))

    if '*' in ipa_exp or '*' in ipa_hrd:
        return []

    # Strip stress/syllable markers for cleaner diff
    strip_chars = "ˈˌ.ːˑ"
    for ch in strip_chars:
        ipa_exp = ipa_exp.replace(ch, "")
        ipa_hrd = ipa_hrd.replace(ch, "")

    errors = []
    matcher = difflib.SequenceMatcher(None, ipa_exp, ipa_hrd)
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == 'replace':
            for i in range(i1, min(i2, i1 + (j2 - j1))):
                exp_ph = ipa_exp[i]
                hrd_ph = ipa_hrd[j1 + (i - i1)] if (j1 + (i - i1)) < j2 else ""
                if exp_ph in _IPA_CONSONANTS or exp_ph in _IPA_VOWELS:
                    errors.append((exp_ph, hrd_ph))
            for i in range(i1 + (j2 - j1), i2):
                exp_ph = ipa_exp[i]
                if exp_ph in _IPA_CONSONANTS or exp_ph in _IPA_VOWELS:
                    errors.append((exp_ph, ""))
        elif tag == 'delete':
            for i in range(i1, i2):
                exp_ph = ipa_exp[i]
                if exp_ph in _IPA_CONSONANTS or exp_ph in _IPA_VOWELS:
                    errors.append((exp_ph, ""))

    return errors
