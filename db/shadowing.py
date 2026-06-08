import uuid
from datetime import datetime
from db.connection import get_db_connection


def create_shadowing_item(text, difficulty=1, source="manual"):
    item_id = str(uuid.uuid4())[:8]
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO shadowing_items (id, text, difficulty, source) VALUES (?, ?, ?, ?)",
        (item_id, text, difficulty, source)
    )
    conn.commit()
    conn.close()
    return item_id


def get_shadowing_item(item_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM shadowing_items WHERE id = ?", (item_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return dict(row)
    return None


def list_shadowing_items(difficulty=None, limit=20):
    conn = get_db_connection()
    cursor = conn.cursor()
    if difficulty:
        cursor.execute(
            "SELECT * FROM shadowing_items WHERE difficulty = ? ORDER BY created_at DESC LIMIT ?",
            (difficulty, limit)
        )
    else:
        cursor.execute(
            "SELECT * FROM shadowing_items ORDER BY created_at DESC LIMIT ?",
            (limit,)
        )
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def pick_shadowing_item(user_id, difficulty=None):
    """Pick a shadowing item the user hasn't recently attempted, or least-attempted."""
    conn = get_db_connection()
    cursor = conn.cursor()

    if difficulty:
        cursor.execute(
            """SELECT si.* FROM shadowing_items si
               LEFT JOIN shadowing_attempts sa
                   ON si.id = sa.shadowing_item_id AND sa.user_id = ?
               WHERE si.difficulty = ?
               GROUP BY si.id
               ORDER BY COUNT(sa.id) ASC, RANDOM()
               LIMIT 1""",
            (user_id, difficulty)
        )
    else:
        cursor.execute(
            """SELECT si.* FROM shadowing_items si
               LEFT JOIN shadowing_attempts sa
                   ON si.id = sa.shadowing_item_id AND sa.user_id = ?
               GROUP BY si.id
               ORDER BY COUNT(sa.id) ASC, RANDOM()
               LIMIT 1""",
            (user_id,)
        )

    row = cursor.fetchone()
    conn.close()
    if row:
        return dict(row)
    return None


def record_shadowing_attempt(user_id, shadowing_item_id, score):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO shadowing_attempts (user_id, shadowing_item_id, score) VALUES (?, ?, ?)",
        (user_id, shadowing_item_id, score)
    )
    conn.commit()
    conn.close()


def get_shadowing_history(user_id, limit=20):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """SELECT sa.*, si.text, si.difficulty
           FROM shadowing_attempts sa
           JOIN shadowing_items si ON sa.shadowing_item_id = si.id
           WHERE sa.user_id = ?
           ORDER BY sa.completed_at DESC, sa.id DESC LIMIT ?""",
        (user_id, limit)
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def seed_shadowing_items():
    """Seed default shadowing items if table is empty."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM shadowing_items")
    if cursor.fetchone()[0] > 0:
        conn.close()
        return

    items = [
        ("Thank you for your help.", 1, "seed"),
        ("I appreciate your time.", 1, "seed"),
        ("Let me know if you need anything.", 1, "seed"),
        ("Could you repeat that please?", 1, "seed"),
        ("Have a wonderful weekend.", 1, "seed"),
        ("The meeting has been rescheduled to Thursday.", 2, "seed"),
        ("I'd like to discuss the project timeline.", 2, "seed"),
        ("We should schedule a follow-up call.", 2, "seed"),
        ("Please review the document before tomorrow.", 2, "seed"),
        ("I'll send you the updated version by end of day.", 2, "seed"),
        ("The quarterly results exceeded our expectations.", 3, "seed"),
        ("We need to restructure the organizational hierarchy.", 3, "seed"),
        ("The entrepreneurial spirit drives innovation forward.", 3, "seed"),
        ("Our competitive advantage lies in technological superiority.", 3, "seed"),
        ("The pharmaceutical industry requires rigorous testing.", 3, "seed"),
    ]

    for text, diff, source in items:
        item_id = str(uuid.uuid4())[:8]
        cursor.execute(
            "INSERT INTO shadowing_items (id, text, difficulty, source) VALUES (?, ?, ?, ?)",
            (item_id, text, diff, source)
        )

    conn.commit()
    conn.close()
