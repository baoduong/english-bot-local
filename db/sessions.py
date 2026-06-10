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


def cleanup_onboarding_sessions(max_age_seconds: int = 86400) -> int:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, session_data, updated_at FROM active_sessions")
    rows = cursor.fetchall()

    stale_user_ids = []
    onboarding_modes = (
        "onboarding",
        "awaiting_goal_confirmation",
        "awaiting_goal_change_confirmation",
    )

    for row in rows:
        user_id = row["user_id"]
        session_data_str = row["session_data"]
        updated_at = row["updated_at"]

        try:
            session_data = json.loads(session_data_str)
            mode = session_data.get("mode")

            if mode in onboarding_modes:
                check_cursor = conn.cursor()
                check_cursor.execute(
                    "SELECT (julianday('now') - julianday(?)) * 86400 as age_seconds",
                    (updated_at,)
                )
                age_row = check_cursor.fetchone()
                if age_row and age_row["age_seconds"] > max_age_seconds:
                    stale_user_ids.append(user_id)
        except (json.JSONDecodeError, TypeError):
            continue

    deleted_count = 0
    if stale_user_ids:
        cursor.execute(
            f"DELETE FROM active_sessions WHERE user_id IN ({','.join(['?'] * len(stale_user_ids))})",
            stale_user_ids
        )
        deleted_count = cursor.rowcount
        conn.commit()

    conn.close()
    return deleted_count


def get_session_by_mode(mode: str) -> list[str]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, session_data FROM active_sessions")
    rows = cursor.fetchall()
    conn.close()

    user_ids = []
    for row in rows:
        try:
            session_data = json.loads(row["session_data"])
            if session_data.get("mode") == mode:
                user_ids.append(row["user_id"])
        except (json.JSONDecodeError, TypeError):
            pass
    return user_ids


def delete_session(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM active_sessions WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()
