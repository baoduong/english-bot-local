from datetime import datetime
from db.connection import get_db_connection


def record_word_attempt(user_id, word, score, passed):
    """UPSERT per-word pronunciation stats: attempts, successes, running avg score."""
    conn = get_db_connection()
    cursor = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute(
        "SELECT attempt_count, success_count, total_score FROM word_statistics WHERE user_id = ? AND word = ?",
        (user_id, word)
    )
    row = cursor.fetchone()

    if row:
        new_attempts = row["attempt_count"] + 1
        new_successes = row["success_count"] + (1 if passed else 0)
        new_total = row["total_score"] + score
        cursor.execute(
            """UPDATE word_statistics
               SET attempt_count = ?, success_count = ?, total_score = ?, last_attempt = ?
               WHERE user_id = ? AND word = ?""",
            (new_attempts, new_successes, new_total, now, user_id, word)
        )
    else:
        cursor.execute(
            "INSERT INTO word_statistics (user_id, word, attempt_count, success_count, total_score, last_attempt) VALUES (?, ?, 1, ?, ?, ?)",
            (user_id, word, 1 if passed else 0, score, now)
        )

    conn.commit()
    conn.close()


def record_word_attempts_batch(user_id, word_scores):
    """Record multiple word attempts from a single sentence analysis.
    word_scores: dict {word: {"score": float 0-100, "passed": bool}}"""
    conn = get_db_connection()
    cursor = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for word, data in word_scores.items():
        score = data["score"]
        passed = data["passed"]

        cursor.execute(
            "SELECT attempt_count, success_count, total_score FROM word_statistics WHERE user_id = ? AND word = ?",
            (user_id, word)
        )
        row = cursor.fetchone()

        if row:
            cursor.execute(
                """UPDATE word_statistics
                   SET attempt_count = attempt_count + 1,
                       success_count = success_count + ?,
                       total_score = total_score + ?,
                       last_attempt = ?
                   WHERE user_id = ? AND word = ?""",
                (1 if passed else 0, score, now, user_id, word)
            )
        else:
            cursor.execute(
                "INSERT INTO word_statistics (user_id, word, attempt_count, success_count, total_score, last_attempt) VALUES (?, ?, 1, ?, ?, ?)",
                (user_id, word, 1 if passed else 0, score, now)
            )

    conn.commit()
    conn.close()


def get_weak_words(user_id, limit=10):
    """Return weakest words sorted by success rate ASC, min 2 attempts."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """SELECT word, attempt_count, success_count,
                  ROUND(total_score / attempt_count, 1) as avg_score,
                  ROUND(CAST(success_count AS REAL) / attempt_count * 100, 1) as success_rate,
                  last_attempt
           FROM word_statistics
           WHERE user_id = ? AND attempt_count >= 2
           ORDER BY success_rate ASC, attempt_count DESC
           LIMIT ?""",
        (user_id, limit)
    )
    results = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return results


def get_strong_words(user_id, limit=5):
    """Return strongest words sorted by success rate DESC, min 3 attempts."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """SELECT word, attempt_count, success_count,
                  ROUND(total_score / attempt_count, 1) as avg_score,
                  ROUND(CAST(success_count AS REAL) / attempt_count * 100, 1) as success_rate
           FROM word_statistics
           WHERE user_id = ? AND attempt_count >= 3
           ORDER BY success_rate DESC, avg_score DESC
           LIMIT ?""",
        (user_id, limit)
    )
    results = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return results
