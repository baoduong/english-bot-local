from datetime import datetime
from db.connection import get_db_connection


def record_pattern_attempt(user_id, pattern, score):
    """UPSERT a speaking pattern attempt with score."""
    conn = get_db_connection()
    cursor = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute(
        "SELECT attempt_count, total_score FROM speaking_patterns WHERE user_id = ? AND pattern = ?",
        (user_id, pattern)
    )
    row = cursor.fetchone()

    if row:
        new_attempts = row["attempt_count"] + 1
        new_total = row["total_score"] + score
        avg = new_total / new_attempts
        mastery = _calc_pattern_mastery(new_attempts, avg)
        cursor.execute(
            """UPDATE speaking_patterns
               SET attempt_count = ?, total_score = ?, mastery_level = ?, last_seen = ?
               WHERE user_id = ? AND pattern = ?""",
            (new_attempts, new_total, mastery, now, user_id, pattern)
        )
    else:
        mastery = _calc_pattern_mastery(1, score)
        cursor.execute(
            "INSERT INTO speaking_patterns (user_id, pattern, attempt_count, total_score, mastery_level, last_seen) VALUES (?, ?, 1, ?, ?, ?)",
            (user_id, pattern, score, mastery, now)
        )

    conn.commit()
    conn.close()


def record_pattern_attempts_batch(user_id, patterns, score):
    """Record the same sentence score for multiple matched patterns."""
    if not patterns:
        return
    conn = get_db_connection()
    cursor = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for pattern in patterns:
        cursor.execute(
            "SELECT attempt_count, total_score FROM speaking_patterns WHERE user_id = ? AND pattern = ?",
            (user_id, pattern)
        )
        row = cursor.fetchone()

        if row:
            new_attempts = row["attempt_count"] + 1
            new_total = row["total_score"] + score
            avg = new_total / new_attempts
            mastery = _calc_pattern_mastery(new_attempts, avg)
            cursor.execute(
                """UPDATE speaking_patterns
                   SET attempt_count = ?, total_score = ?, mastery_level = ?, last_seen = ?
                   WHERE user_id = ? AND pattern = ?""",
                (new_attempts, new_total, mastery, now, user_id, pattern)
            )
        else:
            mastery = _calc_pattern_mastery(1, score)
            cursor.execute(
                "INSERT INTO speaking_patterns (user_id, pattern, attempt_count, total_score, mastery_level, last_seen) VALUES (?, ?, 1, ?, ?, ?)",
                (user_id, pattern, score, mastery, now)
            )

    conn.commit()
    conn.close()


def get_weak_patterns(user_id, limit=10):
    """Return patterns with lowest mastery, min 2 attempts."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """SELECT pattern, attempt_count,
                  ROUND(total_score / attempt_count, 1) as avg_score,
                  mastery_level, last_seen
           FROM speaking_patterns
           WHERE user_id = ? AND attempt_count >= 2
           ORDER BY (total_score / attempt_count) ASC
           LIMIT ?""",
        (user_id, limit)
    )
    results = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return results


def get_strong_patterns(user_id, limit=5):
    """Return patterns with highest mastery, min 3 attempts."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """SELECT pattern, attempt_count,
                  ROUND(total_score / attempt_count, 1) as avg_score,
                  mastery_level, last_seen
           FROM speaking_patterns
           WHERE user_id = ? AND attempt_count >= 3
           ORDER BY (total_score / attempt_count) DESC
           LIMIT ?""",
        (user_id, limit)
    )
    results = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return results


def get_all_patterns(user_id):
    """Return all tracked patterns for a user."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """SELECT pattern, attempt_count,
                  ROUND(total_score / attempt_count, 1) as avg_score,
                  mastery_level, last_seen
           FROM speaking_patterns
           WHERE user_id = ?
           ORDER BY attempt_count DESC""",
        (user_id,)
    )
    results = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return results


def _calc_pattern_mastery(attempt_count, avg_score):
    if attempt_count == 0:
        return "unknown"
    if attempt_count <= 2:
        return "learning"
    if avg_score < 60:
        return "learning"
    if avg_score < 75:
        return "familiar"
    if avg_score < 85:
        return "strong"
    return "mastered"
