from db.connection import get_db_connection


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
    except Exception:
        pass
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN total_sessions INTEGER DEFAULT 0")
    except Exception:
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
    except Exception:
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

    # 7. Bảng thống kê từng từ — theo dõi attempts/successes/avg_score per word (P0: C4)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS word_statistics (
            user_id TEXT,
            word TEXT,
            attempt_count INTEGER DEFAULT 0,
            success_count INTEGER DEFAULT 0,
            total_score REAL DEFAULT 0,
            last_attempt TEXT,
            PRIMARY KEY (user_id, word)
        )
    ''')

    # 8. Bảng theo dõi lỗi phoneme cụ thể — IPA-level tracking (P0: C5)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS phoneme_errors (
            user_id TEXT,
            phoneme TEXT,
            error_count INTEGER DEFAULT 1,
            last_seen TEXT,
            example_words TEXT DEFAULT '[]',
            PRIMARY KEY (user_id, phoneme)
        )
    ''')

    # 9. Bảng speaking patterns — theo dõi cấu trúc nói quen thuộc (P1: C6)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS speaking_patterns (
            user_id TEXT,
            pattern TEXT,
            attempt_count INTEGER DEFAULT 0,
            total_score REAL DEFAULT 0,
            mastery_level TEXT DEFAULT 'unknown',
            last_seen TEXT,
            PRIMARY KEY (user_id, pattern)
        )
    ''')

    # 10. Shadowing items — kho câu shadowing (P2: C8)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS shadowing_items (
            id TEXT PRIMARY KEY,
            text TEXT NOT NULL,
            difficulty INTEGER DEFAULT 1,
            source TEXT DEFAULT 'manual',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 11. Shadowing attempts — kết quả từng lần shadowing (P2: C8)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS shadowing_attempts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            shadowing_item_id TEXT NOT NULL,
            score REAL,
            completed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (shadowing_item_id) REFERENCES shadowing_items(id)
        )
    ''')

    # 12. Content items — kho nội dung học tập (P3: C1+C2)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS content_items (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            source_type TEXT DEFAULT 'manual',
            difficulty INTEGER DEFAULT 1,
            tags TEXT DEFAULT '[]',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 13. Content segments — câu/đoạn con thuộc content item (P3: C1+C2)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS content_segments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content_item_id TEXT NOT NULL,
            text TEXT NOT NULL,
            position INTEGER NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (content_item_id) REFERENCES content_items(id)
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
        print("Loaded sample sentences (3 difficulty levels)")
    else:
        # Migration: gán difficulty cho sentences cũ chưa có difficulty
        cursor.execute("UPDATE sentences SET difficulty = 2 WHERE difficulty IS NULL OR difficulty = 0")

    conn.commit()
    conn.close()
