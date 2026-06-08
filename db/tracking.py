from datetime import datetime, timedelta
from db.connection import get_db_connection


def save_failed_word(user_id, word):
    """Lưu từ bị kẹt quá 3 lần vào 'Sổ đen' để ngày mai bắt luyện lại"""
    if not word:
        return
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        '''INSERT INTO failed_words (user_id, word, fail_count, status) 
           VALUES (?, ?, 1, 'pending')
           ON CONFLICT(user_id, word) DO UPDATE SET fail_count = fail_count + 1, status = 'pending' ''',
        (user_id, word)
    )
    conn.commit()
    conn.close()


def clear_failed_word(user_id, word):
    """Đánh dấu từ trong Sổ đen là đã chinh phục xong, không lặp lại nữa"""
    if not word:
        return
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE failed_words SET status = 'resolved' WHERE user_id = ? AND word = ?",
        (user_id, word)
    )
    conn.commit()
    conn.close()


def log_score(user_id, sentence_text, score):
    """Ghi lại điểm mỗi lần chấm để theo dõi tiến trình dài hạn"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO score_history (user_id, sentence_text, score) VALUES (?, ?, ?)",
        (user_id, sentence_text, score)
    )
    conn.commit()
    conn.close()


def log_error_pattern(user_id, error_type, word):
    """Ghi nhận lỗi phát âm để phát hiện pattern lặp lại"""
    conn = get_db_connection()
    cursor = conn.cursor()
    today_str = datetime.now().strftime("%Y-%m-%d")
    cursor.execute(
        '''INSERT INTO error_patterns (user_id, error_type, word, count, last_seen)
           VALUES (?, ?, ?, 1, ?)
           ON CONFLICT(user_id, error_type, word) DO UPDATE SET count = count + 1, last_seen = ?''',
        (user_id, error_type, word, today_str, today_str)
    )
    conn.commit()
    conn.close()


def get_user_stats(user_id):
    """Lấy thống kê học tập 30 ngày gần nhất"""
    conn = get_db_connection()
    cursor = conn.cursor()
    thirty_days_ago = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")

    # Điểm trung bình 30 ngày
    cursor.execute(
        "SELECT AVG(score), COUNT(*), MIN(score), MAX(score) FROM score_history WHERE user_id = ? AND created_at >= ?",
        (user_id, thirty_days_ago)
    )
    row = cursor.fetchone()
    avg_score = int(row[0]) if row[0] else 0
    total_attempts = row[1] or 0
    min_score = row[2] or 0
    max_score = row[3] or 0

    # Điểm trung bình tuần đầu vs tuần cuối (xu hướng)
    seven_days_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute(
        "SELECT AVG(score) FROM score_history WHERE user_id = ? AND created_at >= ?",
        (user_id, seven_days_ago)
    )
    recent_avg = cursor.fetchone()[0]
    recent_avg = int(recent_avg) if recent_avg else avg_score

    cursor.execute(
        "SELECT AVG(score) FROM score_history WHERE user_id = ? AND created_at >= ? AND created_at < ?",
        (user_id, thirty_days_ago, seven_days_ago)
    )
    old_avg = cursor.fetchone()[0]
    old_avg = int(old_avg) if old_avg else avg_score

    trend = recent_avg - old_avg

    # Số từ đã chinh phục (Box 3) vs tổng số từ đã học
    cursor.execute(
        "SELECT COUNT(*) FROM user_progress WHERE user_id = ? AND box_level = 3",
        (user_id,)
    )
    mastered = cursor.fetchone()[0]
    cursor.execute(
        "SELECT COUNT(*) FROM user_progress WHERE user_id = ?",
        (user_id,)
    )
    total_learned = cursor.fetchone()[0]

    # Top 5 lỗi hay gặp nhất
    cursor.execute(
        '''SELECT error_type, word, count FROM error_patterns 
           WHERE user_id = ? ORDER BY count DESC LIMIT 5''',
        (user_id,)
    )
    top_errors = [{"type": r["error_type"], "word": r["word"], "count": r["count"]} for r in cursor.fetchall()]

    # Level hiện tại
    cursor.execute("SELECT current_level, streak_count, total_sessions FROM users WHERE user_id = ?", (user_id,))
    user_row = cursor.fetchone()
    level = user_row["current_level"] if user_row else 1
    streak = user_row["streak_count"] if user_row else 0
    sessions = user_row["total_sessions"] if user_row else 0

    conn.close()
    return {
        "avg_score": avg_score, "total_attempts": total_attempts,
        "min_score": min_score, "max_score": max_score,
        "trend": trend, "recent_avg": recent_avg,
        "mastered": mastered, "total_learned": total_learned,
        "top_errors": top_errors, "level": level,
        "streak": streak, "total_sessions": sessions
    }
