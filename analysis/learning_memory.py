import json
from datetime import datetime, timedelta
from db.connection import get_db_connection


MASTERY_LEVELS = ("unknown", "learning", "familiar", "strong", "mastered")


def _word_mastery(attempt_count, success_rate):
    if attempt_count == 0:
        return "unknown"
    if attempt_count <= 2:
        return "learning"
    if success_rate < 40:
        return "learning"
    if success_rate < 70:
        return "familiar"
    if success_rate < 90:
        return "strong"
    return "mastered"


def _phoneme_mastery(error_count, days_since_last):
    if error_count <= 1:
        return "strong"
    if error_count >= 8 and days_since_last <= 7:
        return "learning"
    if error_count >= 4 and days_since_last <= 14:
        return "familiar"
    if days_since_last > 21:
        return "strong"
    return "familiar"


def get_learner_profile(user_id):
    """Aggregate all learning data into a unified learner profile.

    Returns dict with hard_words, hard_phonemes, hard_patterns,
    mastered_words, word_mastery_breakdown, phoneme_mastery_breakdown,
    pattern_mastery_breakdown.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    today = datetime.now().date()

    cursor.execute(
        """SELECT word, attempt_count, success_count, total_score
           FROM word_statistics WHERE user_id = ? AND attempt_count >= 2
           ORDER BY (CAST(success_count AS REAL) / attempt_count) ASC""",
        (user_id,)
    )
    words_data = cursor.fetchall()

    hard_words = []
    mastered_words = []
    word_mastery_breakdown = {"unknown": 0, "learning": 0, "familiar": 0, "strong": 0, "mastered": 0}

    for row in words_data:
        sr = (row["success_count"] / row["attempt_count"] * 100) if row["attempt_count"] > 0 else 0
        level = _word_mastery(row["attempt_count"], sr)
        word_mastery_breakdown[level] += 1
        if level in ("learning", "familiar"):
            hard_words.append({
                "word": row["word"],
                "mastery": level,
                "attempt_count": row["attempt_count"],
                "success_rate": round(sr),
            })
        elif level == "mastered":
            mastered_words.append(row["word"])

    cursor.execute(
        """SELECT phoneme, error_count, last_seen, example_words
           FROM phoneme_errors WHERE user_id = ?
           ORDER BY error_count DESC""",
        (user_id,)
    )
    phoneme_data = cursor.fetchall()

    hard_phonemes = []
    phoneme_mastery_breakdown = {"unknown": 0, "learning": 0, "familiar": 0, "strong": 0, "mastered": 0}

    for row in phoneme_data:
        try:
            last_str = row["last_seen"] or ""
            if " " in last_str:
                last_dt = datetime.strptime(last_str, "%Y-%m-%d %H:%M:%S").date()
            else:
                last_dt = datetime.strptime(last_str, "%Y-%m-%d").date()
            days_since = (today - last_dt).days
        except (ValueError, TypeError):
            days_since = 999
        level = _phoneme_mastery(row["error_count"], days_since)
        phoneme_mastery_breakdown[level] += 1
        if level in ("learning", "familiar"):
            try:
                examples = json.loads(row["example_words"]) if row["example_words"] else []
            except (json.JSONDecodeError, TypeError):
                examples = []
            hard_phonemes.append({
                "phoneme": row["phoneme"],
                "mastery": level,
                "error_count": row["error_count"],
                "example_words": examples,
            })

    cursor.execute(
        """SELECT pattern, attempt_count, total_score, mastery_level
           FROM speaking_patterns WHERE user_id = ?
           ORDER BY (total_score / attempt_count) ASC""",
        (user_id,)
    )
    pattern_data = cursor.fetchall()

    hard_patterns = []
    pattern_mastery_breakdown = {"unknown": 0, "learning": 0, "familiar": 0, "strong": 0, "mastered": 0}

    for row in pattern_data:
        level = row["mastery_level"] or "unknown"
        if level in pattern_mastery_breakdown:
            pattern_mastery_breakdown[level] += 1
        if level in ("learning", "familiar"):
            avg = (row["total_score"] / row["attempt_count"]) if row["attempt_count"] > 0 else 0
            hard_patterns.append({
                "pattern": row["pattern"],
                "mastery": level,
                "avg_score": round(avg),
            })

    conn.close()

    return {
        "hard_words": hard_words[:10],
        "hard_phonemes": hard_phonemes[:5],
        "hard_patterns": hard_patterns[:5],
        "mastered_words": mastered_words[:10],
        "word_mastery": word_mastery_breakdown,
        "phoneme_mastery": phoneme_mastery_breakdown,
        "pattern_mastery": pattern_mastery_breakdown,
    }


def detect_trends(user_id):
    """Compare recent 14 days vs previous 14 days for score and error trends.

    Returns dict with overall_trend, phoneme_trends, word_trends.
    Trend values: 'improving', 'stable', 'declining'.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT AVG(score) FROM score_history WHERE user_id = ? AND created_at >= date('now', '-14 days')",
        (user_id,)
    )
    recent_avg = cursor.fetchone()[0]

    cursor.execute(
        "SELECT AVG(score) FROM score_history WHERE user_id = ? AND created_at >= date('now', '-28 days') AND created_at < date('now', '-14 days')",
        (user_id,)
    )
    older_avg = cursor.fetchone()[0]

    if recent_avg is not None and older_avg is not None:
        diff = recent_avg - older_avg
        if diff >= 5:
            overall_trend = "improving"
        elif diff <= -5:
            overall_trend = "declining"
        else:
            overall_trend = "stable"
    else:
        overall_trend = "stable"

    cursor.execute(
        """SELECT error_type, SUM(count) as total
           FROM error_patterns WHERE user_id = ? AND last_seen >= date('now', '-14 days')
           GROUP BY error_type ORDER BY total DESC LIMIT 5""",
        (user_id,)
    )
    recent_errors = {r["error_type"]: r["total"] for r in cursor.fetchall()}

    cursor.execute(
        """SELECT error_type, SUM(count) as total
           FROM error_patterns WHERE user_id = ? AND last_seen >= date('now', '-28 days') AND last_seen < date('now', '-14 days')
           GROUP BY error_type ORDER BY total DESC LIMIT 5""",
        (user_id,)
    )
    older_errors = {r["error_type"]: r["total"] for r in cursor.fetchall()}

    error_trends = {}
    all_types = set(list(recent_errors.keys()) + list(older_errors.keys()))
    for et in all_types:
        recent = recent_errors.get(et, 0)
        older = older_errors.get(et, 0)
        if older == 0 and recent == 0:
            continue
        if older == 0:
            error_trends[et] = "needs_attention"
        elif recent <= older * 0.6:
            error_trends[et] = "improving"
        elif recent >= older * 1.4:
            error_trends[et] = "needs_attention"
        else:
            error_trends[et] = "stable"

    conn.close()

    return {
        "overall": overall_trend,
        "recent_avg": round(recent_avg, 1) if recent_avg else None,
        "older_avg": round(older_avg, 1) if older_avg else None,
        "error_trends": error_trends,
    }


def get_learning_insights(user_id):
    """Generate human-readable learning insights.

    Returns dict with top_weakness, most_improved, most_difficult_pattern,
    overall_status.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        """SELECT phoneme, error_count FROM phoneme_errors
           WHERE user_id = ? ORDER BY error_count DESC LIMIT 1""",
        (user_id,)
    )
    row = cursor.fetchone()
    top_weakness_phoneme = row["phoneme"] if row else None

    cursor.execute(
        """SELECT word, attempt_count, success_count,
                  ROUND(CAST(success_count AS REAL) / attempt_count * 100, 1) as success_rate
           FROM word_statistics
           WHERE user_id = ? AND attempt_count >= 3
           ORDER BY success_rate DESC LIMIT 1""",
        (user_id,)
    )
    row = cursor.fetchone()
    most_improved_word = row["word"] if row else None

    cursor.execute(
        """SELECT pattern, ROUND(total_score / attempt_count, 1) as avg_score
           FROM speaking_patterns
           WHERE user_id = ? AND attempt_count >= 2
           ORDER BY avg_score ASC LIMIT 1""",
        (user_id,)
    )
    row = cursor.fetchone()
    hardest_pattern = row["pattern"] if row else None

    cursor.execute(
        "SELECT COUNT(*) FROM score_history WHERE user_id = ? AND created_at >= date('now', '-7 days')",
        (user_id,)
    )
    recent_sessions = cursor.fetchone()[0]

    conn.close()

    return {
        "top_weakness_phoneme": top_weakness_phoneme,
        "most_improved_word": most_improved_word,
        "hardest_pattern": hardest_pattern,
        "sessions_this_week": recent_sessions,
    }


def get_practice_recommendations(user_id, limit=5):
    """Rule-based practice recommendations.

    Returns dict with recommended_words, recommended_phonemes, recommended_patterns.
    Prioritizes: lowest success rate words, highest error phonemes, lowest score patterns.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        """SELECT word FROM word_statistics
           WHERE user_id = ? AND attempt_count >= 2
           ORDER BY (CAST(success_count AS REAL) / attempt_count) ASC
           LIMIT ?""",
        (user_id, limit)
    )
    rec_words = [r["word"] for r in cursor.fetchall()]

    cursor.execute(
        """SELECT phoneme FROM phoneme_errors
           WHERE user_id = ? AND error_count >= 2
           ORDER BY error_count DESC
           LIMIT ?""",
        (user_id, limit)
    )
    rec_phonemes = [r["phoneme"] for r in cursor.fetchall()]

    cursor.execute(
        """SELECT pattern FROM speaking_patterns
           WHERE user_id = ? AND attempt_count >= 2 AND mastery_level IN ('learning', 'familiar')
           ORDER BY (total_score / attempt_count) ASC
           LIMIT ?""",
        (user_id, limit)
    )
    rec_patterns = [r["pattern"] for r in cursor.fetchall()]

    conn.close()

    return {
        "recommended_words": rec_words,
        "recommended_phonemes": rec_phonemes,
        "recommended_patterns": rec_patterns,
    }
