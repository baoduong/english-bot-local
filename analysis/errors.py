import eng_to_ipa as ipa
from analysis.phonemes import clean_word


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

# Bảng màu ANSI dùng chung cho cả 2 engine
ANSI_GREEN = "\u001b[0;32m"
ANSI_YELLOW = "\u001b[0;33m"
ANSI_RED = "\u001b[0;31m"
ANSI_GRAY = "\u001b[0;30m"
ANSI_RESET = "\u001b[0m"
