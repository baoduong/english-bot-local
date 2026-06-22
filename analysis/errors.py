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


ARTICULATORY_TIPS = {
    "omission": "Đọc chậm lại, chú ý phát âm rõ từng từ. Không bỏ sót từ nào trong câu.",
    "final_consonant": "Giữ âm cuối! Đặt lưỡi/môi đúng vị trí âm cuối (s, t, d, z, k, p) rồi thả hơi nhẹ. Người Việt thường 'nuốt' âm cuối — hãy kéo dài âm cuối thêm 1 giây.",
    "th_sound": "Đặt ĐẦU LƯỠI giữa 2 hàm răng (lộ ra ngoài), thổi hơi nhẹ. Khác với 't' tiếng Việt — lưỡi phải chạm RÌA răng, không phải sau răng.",
    "r_l_confusion": "Âm /r/: Cuộn đầu lưỡi về phía sau, KHÔNG chạm vào đâu cả, tròn môi nhẹ. Âm /l/: Đầu lưỡi chạm lợi trên (ngay sau răng cửa). Hai âm này hoàn toàn khác nhau!",
    "vowel_stress": "Chú ý TRỌNG ÂM! Âm tiết được nhấn phải đọc TO hơn + DÀI hơn + CAO hơn. Tiếng Việt dùng thanh điệu, tiếng Anh dùng trọng âm — cần tập phân biệt.",
    "sh_sound": "Âm /ʃ/ (sh): Tròn môi, lưỡi cong lên nhưng KHÔNG chạm lợi. Giống âm 'x' tiếng Việt nhưng môi tròn hơn và lưỡi lùi về sau hơn.",
    "general": "Nghe lại audio mẫu thật kỹ, chú ý nhịp điệu và cách nhấn nhá của từng từ.",
}

VIETNAMESE_L1_COMPARISON = {
    "final_consonant": "Tiếng Việt chỉ có âm cuối /p, t, k, m, n, ŋ/. Tiếng Anh có thêm /s, z, d, f, v, l, θ/ và cụm phụ âm cuối (-sts, -lth). Cần tập giữ âm cuối.",
    "th_sound": "Tiếng Việt KHÔNG có âm /θ/. Người Việt thường thay bằng 't' hoặc 'f'. Cần đặt lưỡi giữa răng — vị trí hoàn toàn mới.",
    "r_l_confusion": "Một số phương ngữ Việt không phân biệt r/l. Tiếng Anh phân biệt rõ: 'right' ≠ 'light', 'read' ≠ 'lead'.",
    "vowel_stress": "Tiếng Việt là ngôn ngữ có thanh điệu (6 dấu). Tiếng Anh dùng trọng âm (stress) — âm tiết nhấn phải to + dài + cao hơn.",
    "sh_sound": "Âm /ʃ/ gần giống 'x' trong 'xin' nhưng môi tròn hơn. Người Việt hay nói 's' thay vì 'sh'.",
}

ERROR_TYPE_EXAMPLES = {
    "omission": [],
    "final_consonant": ["cats", "books", "stopped", "wished", "wants", "needs"],
    "th_sound": ["think", "three", "throw", "thanks", "this", "those"],
    "r_l_confusion": ["right", "light", "read", "lead", "rice", "lice"],
    "vowel_stress": ["PHOtograph", "phoTOgraphy", "REcord (n)", "reCORD (v)"],
    "sh_sound": ["ship", "shop", "wish", "fish", "share", "shine"],
    "general": [],
}


def get_articulatory_tip(error_type):
    """Returns formatted articulatory tip for a given error type."""
    tip = ARTICULATORY_TIPS.get(error_type, ARTICULATORY_TIPS["general"])
    l1 = VIETNAMESE_L1_COMPARISON.get(error_type)
    result = f"💡 **Mẹo phát âm:** {tip}"
    if l1:
        result += f"\n🇻🇳 **So với tiếng Việt:** {l1}"
    return result


def get_error_examples(error_type: str) -> list[str]:
    return ERROR_TYPE_EXAMPLES.get(error_type, [])


def get_target_ipa(word: str) -> str | None:
    try:
        clean = clean_word(word)
        if not clean:
            return None
        result = ipa.convert(clean)
        if "*" in result:
            return None
        return f"/{result}/"
    except Exception:
        return None
