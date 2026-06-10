import json
from datetime import datetime, timedelta
from db.connection import get_db_connection
from analysis.learning_memory import get_learner_profile


def get_learning_progress(user_id, days=30):
    conn = get_db_connection()
    cursor = conn.cursor()
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

    cursor.execute(
        """SELECT score, created_at FROM score_history
           WHERE user_id = ? AND created_at >= ?
           ORDER BY created_at ASC""",
        (user_id, cutoff)
    )
    scores = cursor.fetchall()

    pronunciation_trend = "stable"
    if len(scores) >= 4:
        first_half = [r["score"] for r in scores[:len(scores)//2] if r["score"] is not None]
        second_half = [r["score"] for r in scores[len(scores)//2:] if r["score"] is not None]
        if first_half and second_half:
            avg_first = sum(first_half) / len(first_half)
            avg_second = sum(second_half) / len(second_half)
        else:
            avg_first = avg_second = 0
        if avg_second - avg_first >= 5:
            pronunciation_trend = "improving"
        elif avg_first - avg_second >= 5:
            pronunciation_trend = "declining"

    cursor.execute(
        """SELECT word, attempt_count, success_count
           FROM word_statistics WHERE user_id = ? AND attempt_count >= 3
           ORDER BY attempt_count DESC LIMIT 20""",
        (user_id,)
    )
    words = cursor.fetchall()

    improving_words = []
    declining_words = []
    for w in words:
        rate = (w["success_count"] / w["attempt_count"] * 100) if w["attempt_count"] > 0 else 0
        if rate >= 70:
            improving_words.append(w["word"])
        elif rate < 40:
            declining_words.append(w["word"])

    cursor.execute(
        """SELECT phoneme, error_count FROM phoneme_errors
           WHERE user_id = ? ORDER BY error_count ASC""",
        (user_id,)
    )
    phonemes = cursor.fetchall()

    improving_phonemes = [p["phoneme"] for p in phonemes if p["error_count"] <= 2]
    struggling_phonemes = [p["phoneme"] for p in phonemes if p["error_count"] >= 6]

    conn.close()

    mastery_trend = "stable"
    if len(improving_words) > len(declining_words) * 2:
        mastery_trend = "improving"
    elif len(declining_words) > len(improving_words):
        mastery_trend = "declining"

    return {
        "pronunciation_trend": pronunciation_trend,
        "mastery_trend": mastery_trend,
        "score_count": len(scores),
        "avg_score": round(sum(r["score"] for r in scores if r["score"] is not None) / max(len([r for r in scores if r["score"] is not None]), 1), 1) if scores else 0,
        "phoneme_improvement": improving_phonemes,
        "phoneme_struggling": struggling_phonemes,
        "word_improvement": improving_words[:10],
        "word_declining": declining_words[:10],
    }


def export_learning_profile(user_id):
    profile = get_learner_profile(user_id)
    progress = get_learning_progress(user_id)

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user_row = cursor.fetchone()
    conn.close()

    user_info = dict(user_row) if user_row else {}

    return {
        "exported_at": datetime.now().isoformat(),
        "user": {
            "id": user_id,
            "level": user_info.get("current_level", 1),
            "streak": user_info.get("streak_count", 0),
            "total_sessions": user_info.get("total_sessions", 0),
        },
        "weaknesses": {
            "words": profile.get("hard_words", []),
            "phonemes": profile.get("hard_phonemes", []),
            "patterns": profile.get("hard_patterns", []),
        },
        "strengths": {
            "mastered_words": profile.get("mastered_words", []),
        },
        "mastery": {
            "word_breakdown": profile.get("word_mastery", {}),
            "phoneme_breakdown": profile.get("phoneme_mastery", {}),
            "pattern_breakdown": profile.get("pattern_mastery", {}),
        },
        "progress": progress,
    }
