from db.connection import get_db_connection


def get_learning_goals(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT goal_type, priority, created_at FROM learning_goals WHERE user_id = ? ORDER BY priority ASC, created_at ASC",
        (user_id,)
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def set_learning_goals(user_id, goals):
    """Replace all goals for a user.

    Args:
        goals: list of {"goal_type": str, "priority": "primary"|"secondary"}
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM learning_goals WHERE user_id = ?", (user_id,))

    for g in goals:
        cursor.execute(
            "INSERT INTO learning_goals (user_id, goal_type, priority) VALUES (?, ?, ?)",
            (user_id, g["goal_type"], g.get("priority", "secondary"))
        )

    conn.commit()
    conn.close()


def get_primary_goal(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT goal_type FROM learning_goals WHERE user_id = ? AND priority = 'primary' LIMIT 1",
        (user_id,)
    )
    row = cursor.fetchone()
    conn.close()
    return row["goal_type"] if row else None


def clear_learning_goals(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM learning_goals WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()
