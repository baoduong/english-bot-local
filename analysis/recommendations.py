import json
import re
from datetime import datetime
from db.connection import get_db_connection
from db.recommendations import get_recently_recommended_ids
from analysis.learning_memory import get_learner_profile
from analysis.phoneme_extraction import PHONEME_WORD_MAP

_WORD_PATTERN = re.compile(r"[a-zA-Z']+")


def get_candidate_segments(user_id, limit=50):
    recently_recommended = get_recently_recommended_ids(user_id, days=3)

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        """SELECT cs.id, cs.content_item_id, cs.text, cs.position,
                  cs.difficulty_score, cs.phoneme_metadata,
                  ci.title as item_title,
                  COUNT(cu.id) as usage_count,
                  MAX(cu.used_at) as last_used
           FROM content_segments cs
           JOIN content_items ci ON cs.content_item_id = ci.id
           LEFT JOIN content_usage cu ON cs.id = cu.segment_id
           WHERE cs.difficulty_score > 0
           GROUP BY cs.id
           ORDER BY usage_count ASC, cs.id
           LIMIT ?""",
        (limit * 2,)
    )
    rows = cursor.fetchall()
    conn.close()

    candidates = []
    for row in rows:
        item = dict(row)
        if item["id"] in recently_recommended:
            continue
        try:
            item["phoneme_metadata"] = json.loads(item["phoneme_metadata"] or "[]")
        except (json.JSONDecodeError, TypeError):
            item["phoneme_metadata"] = []
        candidates.append(item)
        if len(candidates) >= limit:
            break

    return candidates


def _compute_freshness(usage_count, last_used):
    if usage_count == 0:
        return 3
    if last_used is None:
        return 2
    try:
        last_dt = datetime.fromisoformat(last_used)
        days_ago = (datetime.now() - last_dt).days
    except (ValueError, TypeError):
        days_ago = 7

    if days_ago >= 14:
        return 3
    if days_ago >= 7:
        return 2
    if days_ago >= 3:
        return 1
    return 0


def _compute_usage_penalty(usage_count):
    if usage_count == 0:
        return 0
    if usage_count <= 2:
        return 2
    if usage_count <= 5:
        return 5
    return 8


def score_candidate(segment, profile):
    reasons = []
    score = 0

    hard_phoneme_set = {p["phoneme"] for p in profile.get("hard_phonemes", [])}
    segment_phonemes = set(segment.get("phoneme_metadata", []))
    phoneme_overlap = hard_phoneme_set & segment_phonemes
    if phoneme_overlap:
        score += len(phoneme_overlap) * 5
        for p in phoneme_overlap:
            reasons.append(f"contains {p}")

    hard_word_set = {w["word"].lower() for w in profile.get("hard_words", [])}
    segment_words = set(w.lower() for w in _WORD_PATTERN.findall(segment.get("text", "")))
    word_overlap = hard_word_set & segment_words
    if word_overlap:
        score += len(word_overlap) * 4
        for w in list(word_overlap)[:3]:
            reasons.append(f"contains difficult word '{w}'")

    hard_pattern_set = {p["pattern"].lower() for p in profile.get("hard_patterns", [])}
    text_lower = segment.get("text", "").lower()
    pattern_matches = [p for p in hard_pattern_set if p in text_lower]
    if pattern_matches:
        score += len(pattern_matches) * 3
        for p in pattern_matches[:2]:
            reasons.append(f"practices pattern '{p}'")

    freshness = _compute_freshness(segment.get("usage_count", 0), segment.get("last_used"))
    score += freshness * 2
    if freshness >= 2:
        reasons.append("not practiced recently")

    penalty = _compute_usage_penalty(segment.get("usage_count", 0))
    score -= penalty

    user_level = profile.get("user_level", 1)
    seg_diff = segment.get("difficulty_score", 1)
    if abs(seg_diff - user_level) <= 1:
        score += 2
        reasons.append("difficulty matches your level")
    elif abs(seg_diff - user_level) >= 3:
        score -= 3

    if not reasons:
        reasons.append("available content")

    return {"score": max(0, score), "reasons": reasons}


def get_recommended_content(user_id, limit=5):
    profile = get_learner_profile(user_id)

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT current_level FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    profile["user_level"] = row["current_level"] if row else 1

    candidates = get_candidate_segments(user_id, limit=50)

    scored = []
    for seg in candidates:
        result = score_candidate(seg, profile)
        scored.append({
            "segment_id": seg["id"],
            "content_item_id": seg["content_item_id"],
            "item_title": seg.get("item_title", ""),
            "text": seg["text"],
            "difficulty_score": seg["difficulty_score"],
            "phonemes": seg.get("phoneme_metadata", []),
            "score": result["score"],
            "reasons": result["reasons"],
        })

    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:limit]


def build_today_session(user_id, shadowing_count=3, word_count=5, phoneme_count=3, content_count=5):
    profile = get_learner_profile(user_id)
    recommendations = get_recommended_content(user_id, limit=content_count)

    hard_words = [w["word"] for w in profile.get("hard_words", [])[:word_count]]
    hard_phonemes = [p["phoneme"] for p in profile.get("hard_phonemes", [])[:phoneme_count]]

    shadowing_segments = []
    for rec in recommendations[:shadowing_count]:
        shadowing_segments.append({
            "segment_id": rec["segment_id"],
            "text": rec["text"],
            "difficulty_score": rec["difficulty_score"],
            "reasons": rec["reasons"],
        })

    return {
        "shadowing": shadowing_segments,
        "review_words": hard_words,
        "review_phonemes": hard_phonemes,
        "recommended_content": recommendations,
    }
