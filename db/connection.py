import os
import sqlite3

DB_NAME = os.getenv("DB_PATH", "english_learner.db")


def get_db_connection():
    """Tạo kết nối tới cơ sở dữ liệu SQLite"""
    db_path = os.getenv("DB_PATH", DB_NAME)
    conn = sqlite3.connect(db_path, timeout=30)
    _ = conn.execute("PRAGMA journal_mode=WAL;")
    _ = conn.execute("PRAGMA busy_timeout=5000;")
    _ = conn.execute("PRAGMA foreign_keys=ON;")
    conn.row_factory = sqlite3.Row  # Cho phép truy cập dữ liệu theo tên cột như Dictionary
    return conn
