from datetime import datetime, timedelta
from db.connection import get_db_connection


def get_next_sentence(user_id, exclude_sentences=None):
    """Bốc câu hỏi thông minh dựa trên lịch sử lỗi sai và Hộp từ vựng.
    exclude_sentences: danh sách câu đã bốc trong phiên hiện tại, tránh trùng lặp."""
    if exclude_sentences is None:
        exclude_sentences = []
    conn = get_db_connection()
    cursor = conn.cursor()
    today_str = datetime.now().strftime("%Y-%m-%d")

    # Build điều kiện loại trừ câu đã dùng trong phiên
    exclude_placeholders = ",".join(["?"] * len(exclude_sentences)) if exclude_sentences else ""
    exclude_clause = f"AND s.sentence_text NOT IN ({exclude_placeholders})" if exclude_sentences else ""

    # ƯU TIÊN 1: Tìm trong "Sổ đen" xem có từ nào hôm qua sai nặng (>3 lần) cần phục thù không
    cursor.execute(
        "SELECT word FROM failed_words WHERE user_id = ? AND status = 'pending' LIMIT 1",
        (user_id,)
    )
    failed_row = cursor.fetchone()

    if failed_row:
        failed_word = failed_row["word"]
        query = f"SELECT * FROM sentences s WHERE s.keyword = ? {exclude_clause} LIMIT 1"
        params = [failed_word] + list(exclude_sentences)
        cursor.execute(query, params)
        sentence_row = cursor.fetchone()
        if sentence_row:
            conn.close()
            return {"sentence": sentence_row["sentence_text"], "new_word": sentence_row["keyword"]}

    # ƯU TIÊN 2: Tìm các câu đã học đến hạn phải review trong các Hộp (Box 1, 2, 3)
    query = f'''
        SELECT s.* FROM sentences s
        JOIN user_progress up ON s.id = up.sentence_id
        WHERE up.user_id = ? AND up.next_review_date <= ? {exclude_clause}
        ORDER BY up.box_level ASC LIMIT 1
    '''
    params = [user_id, today_str] + list(exclude_sentences)
    cursor.execute(query, params)
    due_sentence = cursor.fetchone()

    if due_sentence:
        conn.close()
        return {"sentence": due_sentence["sentence_text"], "new_word": None}

    # ƯU TIÊN 3: Bốc câu mới tinh, ưu tiên theo cấp độ user
    # Lấy level hiện tại của user
    cursor.execute("SELECT current_level FROM users WHERE user_id = ?", (user_id,))
    level_row = cursor.fetchone()
    user_level = level_row["current_level"] if level_row else 1

    # Ưu tiên câu đúng level, nếu hết thì mở rộng ±1
    new_sentence = None
    for target_levels in [[user_level], [max(1, user_level-1), min(3, user_level+1)], [1, 2, 3]]:
        level_placeholders = ",".join(["?"] * len(target_levels))
        query = f'''
            SELECT * FROM sentences s
            WHERE s.id NOT IN (SELECT sentence_id FROM user_progress WHERE user_id = ?)
            AND s.difficulty IN ({level_placeholders})
            {exclude_clause}
            ORDER BY RANDOM() LIMIT 1
        '''
        params = [user_id] + target_levels + list(exclude_sentences)
        cursor.execute(query, params)
        new_sentence = cursor.fetchone()
        if new_sentence:
            break

    if new_sentence:
        cursor.execute(
            "INSERT INTO user_progress (user_id, sentence_id, box_level, next_review_date) VALUES (?, ?, 1, ?)",
            (user_id, new_sentence["id"], today_str)
        )
        conn.commit()
        conn.close()
        return {"sentence": new_sentence["sentence_text"], "new_word": new_sentence["keyword"]}

    # PHƯƠNG ÁN PHÒNG HỜ: Nếu đã học hết sạch kho từ, bốc ngẫu nhiên 1 câu bất kỳ
    query = f"SELECT * FROM sentences s WHERE 1=1 {exclude_clause} ORDER BY RANDOM() LIMIT 1"
    params = list(exclude_sentences)
    cursor.execute(query, params)
    random_sentence = cursor.fetchone()

    if not random_sentence:
        # Thực sự hết câu → fallback không lọc
        cursor.execute("SELECT * FROM sentences ORDER BY RANDOM() LIMIT 1")
        random_sentence = cursor.fetchone()

    conn.close()
    return {"sentence": random_sentence["sentence_text"], "new_word": None}


def update_sentence_progress(user_id, sentence_text, success=True):
    """
    Tốt nghiệp câu cũ: Nếu đúng thì nâng cấp Hộp (Box) và đẩy ngày hẹn sang hôm sau.
    Nếu thất bại quá 3 lần thì reset về Box 1 và hẹn ngày mai làm lại.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. Tìm ID của câu dựa vào nội dung text
    cursor.execute("SELECT id FROM sentences WHERE sentence_text = ?", (sentence_text,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return
    sentence_id = row["id"]

    if success:
        # Lấy Box hiện tại của user cho câu này
        cursor.execute("SELECT box_level FROM user_progress WHERE user_id = ? AND sentence_id = ?", (user_id, sentence_id))
        progress = cursor.fetchone()

        current_box = progress["box_level"] if progress else 1
        new_box = min(current_box + 1, 3)  # Tối đa là Hộp 3

        # Tính ngày review tiếp theo: Box 1 -> mai học lại; Box 2 -> 3 ngày sau; Box 3 -> 7 ngày sau
        days_to_add = 1 if new_box == 1 else (3 if new_box == 2 else 7)
        next_date = (datetime.now() + timedelta(days=days_to_add)).strftime("%Y-%m-%d")

        cursor.execute(
            '''INSERT INTO user_progress (user_id, sentence_id, box_level, next_review_date)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(user_id, sentence_id) DO UPDATE SET box_level = ?, next_review_date = ?''',
            (user_id, sentence_id, new_box, next_date, new_box, next_date)
        )
    else:
        # Nếu thất bại, phạt quay về Box 1 và mai cấu hình học lại câu này
        tomorrow_str = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        cursor.execute(
            '''INSERT INTO user_progress (user_id, sentence_id, box_level, next_review_date)
               VALUES (?, ?, 1, ?)
               ON CONFLICT(user_id, sentence_id) DO UPDATE SET box_level = 1, next_review_date = ?''',
            (user_id, sentence_id, tomorrow_str, tomorrow_str)
        )

    conn.commit()
    conn.close()
