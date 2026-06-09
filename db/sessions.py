import json
from db.connection import get_db_connection


def save_session(user_id, session_data):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """INSERT OR REPLACE INTO active_sessions (user_id, session_data, updated_at)
           VALUES (?, ?, datetime('now'))""",
        (user_id, json.dumps(session_data, ensure_ascii=False))
    )
    conn.commit()
    conn.close()


def load_all_sessions():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, session_data FROM active_sessions")
    rows = cursor.fetchall()
    conn.close()

    sessions = {}
    for row in rows:
        try:
            sessions[row["user_id"]] = json.loads(row["session_data"])
        except (json.JSONDecodeError, TypeError):
            pass
    return sessions


def delete_session(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM active_sessions WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()
