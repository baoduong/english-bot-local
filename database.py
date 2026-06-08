import sqlite3
from datetime import datetime, timedelta

DB_NAME = "english_learner.db"

def get_db_connection():
    """Tạo kết nối tới cơ sở dữ liệu SQLite"""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row  # Cho phép truy cập dữ liệu theo tên cột như Dictionary
    return conn

def init_db():
    """Khởi tạo các bảng dữ liệu nếu chưa tồn tại và nạp data mẫu"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Bảng quản lý User và Chuỗi ngày học (Streak)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            username TEXT,
            streak_count INTEGER DEFAULT 0,
            last_study_date TEXT,
            current_level INTEGER DEFAULT 1,
            total_sessions INTEGER DEFAULT 0
        )
    ''')
    # Migration: thêm cột mới cho database cũ
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN current_level INTEGER DEFAULT 1")
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN total_sessions INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass
    
    # 2. Bảng lưu trữ kho câu hỏi gốc — difficulty: 1 (dễ), 2 (trung bình), 3 (khó)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sentences (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sentence_text TEXT NOT NULL,
            keyword TEXT,
            difficulty INTEGER DEFAULT 1
        )
    ''')
    try:
        cursor.execute("ALTER TABLE sentences ADD COLUMN difficulty INTEGER DEFAULT 1")
    except sqlite3.OperationalError:
        pass
    
    # 3. Bảng quản lý tiến độ theo thuật toán Hộp từ vựng (Leitner System)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_progress (
            user_id TEXT,
            sentence_id INTEGER,
            box_level INTEGER DEFAULT 1,
            next_review_date TEXT,
            PRIMARY KEY (user_id, sentence_id)
        )
    ''')
    
    # 4. Bảng "Sổ đen" lưu các từ phát âm sai nặng
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS failed_words (
            user_id TEXT,
            word TEXT,
            fail_count INTEGER DEFAULT 1,
            status TEXT DEFAULT 'pending',
            PRIMARY KEY (user_id, word)
        )
    ''')
    
    # 5. Bảng lịch sử điểm số — theo dõi tiến trình dài hạn
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS score_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            sentence_text TEXT,
            score INTEGER,
            created_at TEXT DEFAULT (datetime('now', 'localtime'))
        )
    ''')
    
    # 6. Bảng pattern lỗi phát âm — phát hiện lỗi lặp đi lặp lại
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS error_patterns (
            user_id TEXT,
            error_type TEXT,
            word TEXT,
            count INTEGER DEFAULT 1,
            last_seen TEXT,
            PRIMARY KEY (user_id, error_type, word)
        )
    ''')
    
    # Nạp dữ liệu mẫu nếu kho câu hỏi đang trống
    cursor.execute("SELECT COUNT(*) FROM sentences")
    if cursor.fetchone()[0] == 0:
        sample_data = [
            # Cấp 1 — câu ngắn, từ đơn giản
            ("Thank you very much.", "thank", 1),
            ("Nice to meet you.", "nice", 1),
            ("Have a good day.", "good", 1),
            ("See you tomorrow.", "tomorrow", 1),
            # Cấp 2 — câu trung bình, 1 từ khó
            ("Let's review the project schedule.", "schedule", 2),
            ("Please send me the quarterly financial report.", "quarterly", 2),
            ("The marketing strategy needs to be adjusted.", "strategy", 2),
            ("Let's schedule a brief sync meeting tomorrow.", "sync", 2),
            # Cấp 3 — câu dài, từ phức tạp
            ("Good communication is a prerequisite for this job.", "prerequisite", 3),
            ("We need to negotiate the contract terms.", "negotiate", 3),
            ("We should prioritize tasks to meet the deadline.", "prioritize", 3),
            ("He is a successful tech entrepreneur.", "entrepreneur", 3),
        ]
        cursor.executemany(
            "INSERT INTO sentences (sentence_text, keyword, difficulty) VALUES (?, ?, ?)",
            sample_data
        )
        print("🎉 Đã nạp thành công kho câu hỏi mẫu tiếng Anh (3 cấp độ)!")
    else:
        # Migration: gán difficulty cho sentences cũ chưa có difficulty
        cursor.execute("UPDATE sentences SET difficulty = 2 WHERE difficulty IS NULL OR difficulty = 0")

    conn.commit()
    conn.close()

# ========================================================
# XỬ LÝ THÔNG TIN USER & STREAK (CHỐNG NẢN)
# ========================================================

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

# ========================================================
# THUẬT TOÁN HỘP TỪ VỰNG (SPACED REPETITION)
# ========================================================

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
        new_box = min(current_box + 1, 3) # Tối đa là Hộp 3
        
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

# ========================================================
# SCORE TRACKING & ANALYTICS
# ========================================================

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

# Tự động kích hoạt tạo bảng khi file này được gọi
init_db()
