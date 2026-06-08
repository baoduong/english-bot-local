import json
from datetime import datetime, timedelta
from db.connection import get_db_connection
from analysis.learning_memory import get_learner_profile


def get_recommendation_metrics(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT COUNT(*) as total FROM recommendation_feedback WHERE user_id = ?",
        (user_id,)
    )
    total = cursor.fetchone()["total"]

    if total == 0:
        conn.close()
        return {"total": 0, "completion_rate": 0, "acceptance_rate": 0, "skip_rate": 0}

    cursor.execute(
        "SELECT COUNT(*) as n FROM recommendation_feedback WHERE user_id = ? AND completed = 1",
        (user_id,)
    )
    completed = cursor.fetchone()["n"]

    cursor.execute(
        "SELECT COUNT(*) as n FROM recommendation_feedback WHERE user_id = ? AND skipped = 1",
        (user_id,)
    )
    skipped = cursor.fetchone()["n"]

    conn.close()

    acted_on = completed + skipped
    return {
        "total": total,
        "completed": completed,
        "skipped": skipped,
        "completion_rate": round(completed / total * 100, 1),
        "acceptance_rate": round(completed / acted_on * 100, 1) if acted_on > 0 else 0,
        "skip_rate": round(skipped / total * 100, 1),
    }


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


def get_session_analytics(user_id, days=30):
    conn = get_db_connection()
    cursor = conn.cursor()
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

    cursor.execute(
        """SELECT * FROM session_analytics
           WHERE user_id = ? AND started_at >= ?
           ORDER BY started_at DESC""",
        (user_id, cutoff)
    )
    sessions = cursor.fetchall()

    if not sessions:
        conn.close()
        return {"total_sessions": 0, "avg_completion_pct": 0, "avg_score": 0, "content_usage_rate": 0}

    total = len(sessions)
    completed_sessions = [s for s in sessions if s["completed_at"] is not None]

    completion_pcts = []
    scores = []
    content_used_total = 0

    for s in sessions:
        if s["rounds_total"] > 0:
            completion_pcts.append(s["rounds_completed"] / s["rounds_total"] * 100)
        if s["avg_score"] > 0:
            scores.append(s["avg_score"])
        content_used_total += s["content_segments_used"] or 0

    cursor.execute(
        "SELECT COUNT(*) as n FROM content_usage WHERE segment_id IN (SELECT id FROM content_segments)",
        ()
    )
    total_content_uses = cursor.fetchone()["n"]
    conn.close()

    return {
        "total_sessions": total,
        "completed_sessions": len(completed_sessions),
        "avg_completion_pct": round(sum(completion_pcts) / len(completion_pcts), 1) if completion_pcts else 0,
        "avg_score": round(sum(scores) / len(scores), 1) if scores else 0,
        "content_usage_rate": round(content_used_total / total, 1) if total > 0 else 0,
        "total_content_uses": total_content_uses,
    }


def get_content_effectiveness(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        """SELECT rf.segment_id, rf.score_after_practice, rf.recommendation_reasons,
                  cs.text, cs.phoneme_metadata, cs.difficulty_score
           FROM recommendation_feedback rf
           JOIN content_segments cs ON rf.segment_id = cs.id
           WHERE rf.user_id = ? AND rf.completed = 1 AND rf.score_after_practice IS NOT NULL
           ORDER BY rf.recommended_at DESC LIMIT 50""",
        (user_id,)
    )
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        return {"effective_content": [], "ineffective_content": [], "avg_score_after": 0}

    effective = []
    ineffective = []
    total_score = 0

    for row in rows:
        score = row["score_after_practice"]
        total_score += score
        try:
            phonemes = json.loads(row["phoneme_metadata"] or "[]")
        except (json.JSONDecodeError, TypeError):
            phonemes = []

        entry = {
            "segment_id": row["segment_id"],
            "text": row["text"][:60],
            "score_after": score,
            "difficulty": row["difficulty_score"],
            "phonemes": phonemes,
        }

        if score >= 75:
            effective.append(entry)
        elif score < 50:
            ineffective.append(entry)

    return {
        "effective_content": effective[:10],
        "ineffective_content": ineffective[:10],
        "avg_score_after": round(total_score / len(rows), 1),
        "total_practiced": len(rows),
    }


def audit_recommendation_quality(user_id, limit=20):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        """SELECT rf.id, rf.segment_id, rf.recommended_at, rf.completed, rf.skipped,
                  rf.score_after_practice, rf.recommendation_reasons, rf.recommendation_score,
                  cs.text
           FROM recommendation_feedback rf
           JOIN content_segments cs ON rf.segment_id = cs.id
           WHERE rf.user_id = ?
           ORDER BY rf.recommended_at DESC LIMIT ?""",
        (user_id, limit)
    )
    rows = cursor.fetchall()
    conn.close()

    audits = []
    for row in rows:
        try:
            reasons = json.loads(row["recommendation_reasons"] or "[]")
        except (json.JSONDecodeError, TypeError):
            reasons = []

        outcome = "pending"
        if row["completed"] == 1:
            outcome = "completed"
        elif row["skipped"] == 1:
            outcome = "skipped"

        audits.append({
            "id": row["id"],
            "segment_id": row["segment_id"],
            "text": row["text"][:60],
            "recommended_at": row["recommended_at"],
            "recommendation_score": row["recommendation_score"],
            "reasons": reasons,
            "outcome": outcome,
            "score_after": row["score_after_practice"],
        })

    return audits


def validate_session_quality(session_plan):
    issues = []

    all_segments = session_plan.get("recommended_content", [])
    shadowing = session_plan.get("shadowing", [])

    segment_ids = [s.get("segment_id") for s in all_segments if s.get("segment_id")]
    shadow_ids = [s.get("segment_id") for s in shadowing if s.get("segment_id")]
    all_ids = segment_ids + shadow_ids

    if len(all_ids) != len(set(all_ids)):
        issues.append("duplicate_segments")

    difficulties = [s.get("difficulty_score", 0) for s in all_segments if s.get("difficulty_score")]
    if difficulties:
        avg_diff = sum(difficulties) / len(difficulties)
        if avg_diff > 4:
            issues.append("too_difficult")
        elif avg_diff < 1.5:
            issues.append("too_easy")
        spread = max(difficulties) - min(difficulties)
        if spread < 1 and len(difficulties) >= 3:
            issues.append("low_difficulty_variance")

    review_words = session_plan.get("review_words", [])
    review_phonemes = session_plan.get("review_phonemes", [])
    review_count = len(review_words) + len(review_phonemes)
    new_count = len(all_segments)
    total = review_count + new_count

    if total > 0:
        review_ratio = review_count / total
        if review_ratio > 0.8:
            issues.append("too_much_review")
        elif review_ratio < 0.1 and review_count > 0:
            issues.append("too_little_review")

    return {
        "valid": len(issues) == 0,
        "issues": issues,
        "stats": {
            "total_items": total,
            "review_items": review_count,
            "new_items": new_count,
            "difficulty_avg": round(sum(difficulties) / len(difficulties), 1) if difficulties else 0,
            "unique_segments": len(set(all_ids)),
        }
    }


def export_learning_profile(user_id):
    profile = get_learner_profile(user_id)
    progress = get_learning_progress(user_id)
    rec_metrics = get_recommendation_metrics(user_id)
    session_stats = get_session_analytics(user_id)
    effectiveness = get_content_effectiveness(user_id)

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
        "recommendations": rec_metrics,
        "sessions": session_stats,
        "content_effectiveness": effectiveness,
    }


def get_content_health():
    """Content supply metrics: how much content exists and how long it will last.
    Burn rate: ~2.5 segments/session (5 rounds × ~50% content-based).
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) as n FROM content_items")
    total_items = cursor.fetchone()["n"]

    cursor.execute("SELECT COUNT(*) as n FROM content_segments")
    total_segments = cursor.fetchone()["n"]

    cursor.execute(
        """SELECT COUNT(DISTINCT segment_id) as n FROM content_usage"""
    )
    segments_used = cursor.fetchone()["n"]

    conn.close()

    unused_segments = total_segments - segments_used
    burn_rate = 2.5
    coverage_days = round(unused_segments / burn_rate, 1) if burn_rate > 0 else 0

    return {
        "total_items": total_items,
        "total_segments": total_segments,
        "segments_used": segments_used,
        "unused_segments": unused_segments,
        "coverage_days": coverage_days,
    }
