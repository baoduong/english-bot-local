from datetime import datetime, timedelta
from db.connection import get_db_connection


def get_or_create_user(user_id, username):
    """Lấy thông tin học viên, nếu chưa có thì tạo mới"""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()

    if not user:
        cursor.execute(
            "INSERT INTO users (user_id, username, streak_count, last_study_date) VALUES (?, ?, 0, NULL)",
            (user_id, username)
        )
        conn.commit()
        user = {"user_id": user_id, "username": username, "streak": 0, "last_study_date": None}
    else:
        # Kiểm tra xem có bị đứt chuỗi (Streak) không
        # Nếu ngày học cuối cùng trước hôm qua -> Reset chuỗi về 0
        streak = user["streak_count"]
        if user["last_study_date"]:
            last_date = datetime.strptime(user["last_study_date"], "%Y-%m-%d").date()
            today = datetime.now().date()
            yesterday = today - timedelta(days=1)

            if last_date < yesterday and last_date != today:
                streak = 0
                cursor.execute("UPDATE users SET streak_count = 0 WHERE user_id = ?", (user_id,))
                conn.commit()

        user = {"user_id": user["user_id"], "username": user["username"], "streak": streak, "last_study_date": user["last_study_date"]}

    conn.close()
    return user


def update_user_progress(user_id, status="completed"):
    """Cập nhật Streak khi hoàn thành bài học ngày"""
    conn = get_db_connection()
    cursor = conn.cursor()

    today_str = datetime.now().strftime("%Y-%m-%d")
    user = get_or_create_user(user_id, "User")
    current_streak = user["streak"]
    last_study = user["last_study_date"]

    new_streak = current_streak
    if last_study != today_str:
        # Nếu hôm nay chưa học -> Tăng streak lên 1
        new_streak = current_streak + 1
        cursor.execute(
            "UPDATE users SET streak_count = ?, last_study_date = ? WHERE user_id = ?",
            (new_streak, today_str, user_id)
        )
        conn.commit()

    conn.close()
    return new_streak


def adjust_user_level(user_id):
    """
    Tự động điều chỉnh cấp độ dựa trên performance gần đây.
    Pass 3 lần liên tiếp với score cao → level up.
    Fail liên tiếp → level down.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # Lấy 5 lần chấm gần nhất
    cursor.execute(
        "SELECT score FROM score_history WHERE user_id = ? ORDER BY created_at DESC LIMIT 5",
        (user_id,)
    )
    recent_scores = [r["score"] for r in cursor.fetchall()]

    cursor.execute("SELECT current_level FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    current_level = row["current_level"] if row else 1
    new_level = current_level

    if len(recent_scores) >= 3:
        last_3 = recent_scores[:3]
        if all(s >= 85 for s in last_3) and current_level < 3:
            new_level = current_level + 1
        elif all(s < 60 for s in last_3) and current_level > 1:
            new_level = current_level - 1

    if new_level != current_level:
        cursor.execute("UPDATE users SET current_level = ? WHERE user_id = ?", (new_level, user_id))
        conn.commit()

    conn.close()
    return new_level, current_level


def increment_total_sessions(user_id):
    """Tăng số phiên học đã hoàn thành"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET total_sessions = total_sessions + 1 WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()
