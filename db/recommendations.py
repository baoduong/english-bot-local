import json
from db.connection import get_db_connection


def record_recommendation(user_id, segment_id, reasons=None, score=0):
    conn = get_db_connection()
    cursor = conn.cursor()
    reasons_json = json.dumps(reasons or [], ensure_ascii=False)
    cursor.execute(
        """INSERT INTO recommendation_feedback
           (user_id, segment_id, recommendation_reasons, recommendation_score)
           VALUES (?, ?, ?, ?)""",
        (user_id, segment_id, reasons_json, score)
    )
    rec_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return rec_id


def mark_completed(rec_id, score=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE recommendation_feedback SET completed = 1, score_after_practice = ? WHERE id = ?",
        (score, rec_id)
    )
    conn.commit()
    conn.close()


def mark_skipped(rec_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE recommendation_feedback SET skipped = 1 WHERE id = ?",
        (rec_id,)
    )
    conn.commit()
    conn.close()


def get_recent_recommendations(user_id, limit=20):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """SELECT rf.*, cs.text as segment_text
           FROM recommendation_feedback rf
           JOIN content_segments cs ON rf.segment_id = cs.id
           WHERE rf.user_id = ?
           ORDER BY rf.recommended_at DESC LIMIT ?""",
        (user_id, limit)
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_recently_recommended_ids(user_id, days=3):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """SELECT segment_id FROM recommendation_feedback
           WHERE user_id = ? AND recommended_at >= datetime('now', ?)""",
        (user_id, f'-{days} days')
    )
    rows = cursor.fetchall()
    conn.close()
    return {row["segment_id"] for row in rows}
