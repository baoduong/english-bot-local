from __future__ import annotations

import sqlite3
import threading
import time

import pytest


def _hold_exclusive_lock(db_path: str, seconds: float) -> None:
    conn = sqlite3.connect(db_path, timeout=30)
    try:
        conn.execute("BEGIN EXCLUSIVE")
        time.sleep(seconds)
        conn.execute("COMMIT")
    finally:
        conn.close()


@pytest.mark.fault_injection
def test_db_lock_timeout_returns_503(client, clean_db, tmp_path, monkeypatch):
    del client, clean_db
    db_path = str(tmp_path / "test.db")
    monkeypatch.setenv("DB_PATH", db_path)

    from db.schema import init_db

    init_db()

    lock_thread = threading.Thread(target=_hold_exclusive_lock, args=(db_path, 7), daemon=True)
    lock_thread.start()
    time.sleep(0.5)

    from db.connection import get_db_connection

    conn2 = get_db_connection()
    started = time.perf_counter()
    try:
        with pytest.raises(sqlite3.OperationalError, match="locked"):
            conn2.execute("INSERT INTO users (user_id, username) VALUES ('test-lock', 'test-lock')")
            conn2.commit()
    finally:
        elapsed = time.perf_counter() - started
        conn2.close()
        lock_thread.join()

    assert elapsed >= 5
    assert elapsed < 7


@pytest.mark.fault_injection
def test_short_lock_succeeds_after_wait(client, clean_db, tmp_path, monkeypatch):
    del client, clean_db
    db_path = str(tmp_path / "test.db")
    monkeypatch.setenv("DB_PATH", db_path)

    from db.schema import init_db

    init_db()

    lock_thread = threading.Thread(target=_hold_exclusive_lock, args=(db_path, 2), daemon=True)
    lock_thread.start()
    time.sleep(0.5)

    from db.connection import get_db_connection

    conn2 = get_db_connection()
    started = time.perf_counter()
    try:
        conn2.execute("CREATE TABLE IF NOT EXISTS _test_lock (id INTEGER)")
        conn2.execute("INSERT INTO _test_lock (id) VALUES (1)")
        conn2.commit()
        row = conn2.execute("SELECT id FROM _test_lock").fetchone()
    finally:
        elapsed = time.perf_counter() - started
        conn2.close()
        lock_thread.join()

    assert elapsed >= 1.5
    assert elapsed < 5
    assert row[0] == 1
