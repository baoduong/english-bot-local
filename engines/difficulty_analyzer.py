from __future__ import annotations

from collections import Counter

from analysis.errors import get_target_ipa
from analysis.phonemes import clean_word
from db.connection import get_db_connection


_IPA_PATTERNS: dict[str, int] = {
    "θ": 2,
    "ð": 2,
    "ʃ": 2,
    "ʒ": 2,
    "ʧ": 2,
    "tʃ": 2,
    "ʤ": 2,
    "dʒ": 2,
    "ŋ": 1,
    "æ": 1,
    "sk": 1,
    "st": 1,
    "sp": 1,
    "str": 2,
    "spr": 2,
    "stre": 2,
    "skr": 2,
    "spl": 2,
    "θr": 2,
    "ks": 1,
    "ksts": 2,
    "l(d|t)": 1,
}


def _base_difficulty_from_ipa(target_ipa: str | None) -> int:
    if not target_ipa:
        return 1

    ipa = target_ipa.strip("/")
    score = 1
    literal_patterns = {
        key: value for key, value in _IPA_PATTERNS.items() if all(ch not in key for ch in "()|[]")
    }
    for pattern, weight in literal_patterns.items():
        if pattern in ipa:
            score += weight

    if ipa.endswith(("s", "t", "d", "k", "p", "z", "θ", "ʃ", "ʒ", "ʧ", "ʤ", "ks")):
        score += 1
    if len([ch for ch in ipa if ch not in "ˈˌ/"]) >= 5 and any(cluster in ipa for cluster in ("sk", "str", "ŋ", "θr", "dʒ", "tʃ")):
        score += 1
    if len([ch for ch in ipa if ch.isalpha()]) >= 6:
        score += 1
    return score


def _length_adjustment(word: str) -> int:
    length = len(clean_word(word))
    if length <= 3:
        return 0
    if length <= 6:
        return 1
    return 2


def _history_adjustment(word: str, user_id: str) -> int:
    normalized_word = clean_word(word)
    if not normalized_word:
        return 0

    target_ipa = get_target_ipa(normalized_word)
    phoneme_counter: Counter[str] = Counter()
    if target_ipa:
        ipa = target_ipa.strip("/")
        for phoneme in ("θ", "ð", "ʃ", "ʒ", "ʧ", "tʃ", "ʤ", "dʒ", "ŋ", "r", "l", "s", "z", "k"):
            if phoneme in ipa:
                phoneme_counter[phoneme] += 1

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            SELECT attempt_count, success_count
            FROM word_statistics
            WHERE user_id = ? AND word = ?
            """,
            (user_id, normalized_word),
        )
        row = cursor.fetchone()
        adjustment = 0
        if row:
            attempts = int(row["attempt_count"] or 0)
            successes = int(row["success_count"] or 0)
            failures = max(0, attempts - successes)
            adjustment += min(3, failures // 2)

        if phoneme_counter:
            phonemes = tuple(phoneme_counter.keys())
            placeholders = ",".join("?" for _ in phonemes)
            cursor.execute(
                f"""
                SELECT error_type, SUM(count) AS total_count
                FROM error_patterns
                WHERE user_id = ? AND (error_type IN ({placeholders}) OR word = ?)
                GROUP BY error_type
                """,
                (user_id, *phonemes, normalized_word),
            )
        else:
            cursor.execute(
                """
                SELECT error_type, SUM(count) AS total_count
                FROM error_patterns
                WHERE user_id = ? AND word = ?
                GROUP BY error_type
                """,
                (user_id, normalized_word),
            )

        for item in cursor.fetchall():
            total = int(item["total_count"] or 0)
            adjustment += min(2, total // 3)

        return adjustment
    finally:
        conn.close()


def compute_word_difficulty(word: str, user_id: str | None = None) -> int:
    normalized_word = clean_word(word)
    if not normalized_word:
        return 1

    target_ipa = get_target_ipa(normalized_word)
    difficulty = _base_difficulty_from_ipa(target_ipa)
    difficulty += _length_adjustment(normalized_word)

    if user_id:
        difficulty += _history_adjustment(normalized_word, user_id)

    return max(1, min(10, difficulty))


def compute_max_attempts(difficulty: int) -> int:
    if difficulty <= 3:
        return 4
    if difficulty <= 6:
        return 3
    return 2
