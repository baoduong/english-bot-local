import sqlite3

DB_NAME = "english_learner.db"


def get_db_connection():
    """Tạo kết nối tới cơ sở dữ liệu SQLite"""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row  # Cho phép truy cập dữ liệu theo tên cột như Dictionary
    return conn
