import json
from datetime import datetime
from db.connection import get_db_connection


def record_phoneme_error(user_id, phoneme, example_word):
    """UPSERT a phoneme error occurrence. Keeps up to 5 most recent example words."""
    if not phoneme or len(phoneme) > 3:
        return
    conn = get_db_connection()
    cursor = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d")

    cursor.execute(
        "SELECT error_count, example_words FROM phoneme_errors WHERE user_id = ? AND phoneme = ?",
        (user_id, phoneme)
    )
    row = cursor.fetchone()

    if row:
        try:
            examples = json.loads(row["example_words"])
        except (json.JSONDecodeError, TypeError):
            examples = []
        if example_word and example_word not in examples:
            examples.append(example_word)
            examples = examples[-5:]
        cursor.execute(
            "UPDATE phoneme_errors SET error_count = error_count + 1, last_seen = ?, example_words = ? WHERE user_id = ? AND phoneme = ?",
            (now, json.dumps(examples), user_id, phoneme)
        )
    else:
        examples = [example_word] if example_word else []
        cursor.execute(
            "INSERT INTO phoneme_errors (user_id, phoneme, error_count, last_seen, example_words) VALUES (?, ?, 1, ?, ?)",
            (user_id, phoneme, now, json.dumps(examples))
        )

    conn.commit()
    conn.close()


def record_phoneme_errors_batch(user_id, phoneme_error_list):
    """Record multiple phoneme errors from a single analysis.
    phoneme_error_list: list of (phoneme, example_word) tuples."""
    if not phoneme_error_list:
        return
    conn = get_db_connection()
    cursor = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d")

    for phoneme, example_word in phoneme_error_list:
        if not phoneme or len(phoneme) > 3:
            continue

        cursor.execute(
            "SELECT error_count, example_words FROM phoneme_errors WHERE user_id = ? AND phoneme = ?",
            (user_id, phoneme)
        )
        row = cursor.fetchone()

        if row:
            try:
                examples = json.loads(row["example_words"])
            except (json.JSONDecodeError, TypeError):
                examples = []
            if example_word and example_word not in examples:
                examples.append(example_word)
                examples = examples[-5:]
            cursor.execute(
                "UPDATE phoneme_errors SET error_count = error_count + 1, last_seen = ?, example_words = ? WHERE user_id = ? AND phoneme = ?",
                (now, json.dumps(examples), user_id, phoneme)
            )
        else:
            examples = [example_word] if example_word else []
            cursor.execute(
                "INSERT INTO phoneme_errors (user_id, phoneme, error_count, last_seen, example_words) VALUES (?, ?, 1, ?, ?)",
                (user_id, phoneme, now, json.dumps(examples))
            )

    conn.commit()
    conn.close()


def get_weak_phonemes(user_id, limit=10):
    """Return most error-prone phonemes sorted by error_count DESC."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """SELECT phoneme, error_count, last_seen, example_words
           FROM phoneme_errors
           WHERE user_id = ?
           ORDER BY error_count DESC
           LIMIT ?""",
        (user_id, limit)
    )
    results = []
    for r in cursor.fetchall():
        try:
            examples = json.loads(r["example_words"])
        except (json.JSONDecodeError, TypeError):
            examples = []
        results.append({
            "phoneme": r["phoneme"],
            "error_count": r["error_count"],
            "last_seen": r["last_seen"],
            "example_words": examples
        })
    conn.close()
    return results
