from __future__ import annotations

import asyncio

from db.connection import get_db_connection


def test_wal_mode_enabled(tmp_path, monkeypatch) -> None:
    db_path = str(tmp_path / "wal_mode.db")
    monkeypatch.setenv("DB_PATH", db_path)

    conn = get_db_connection()
    try:
        result = conn.execute("PRAGMA journal_mode").fetchone()
        assert result[0] == "wal"
    finally:
        conn.close()


def test_busy_timeout_set(tmp_path, monkeypatch) -> None:
    db_path = str(tmp_path / "busy_timeout.db")
    monkeypatch.setenv("DB_PATH", db_path)

    conn = get_db_connection()
    try:
        result = conn.execute("PRAGMA busy_timeout").fetchone()
        assert result[0] == 5000
    finally:
        conn.close()


def test_concurrent_writes_no_lock(tmp_path, monkeypatch) -> None:
    db_path = str(tmp_path / "concurrent_writes.db")
    monkeypatch.setenv("DB_PATH", db_path)

    conn = get_db_connection()
    try:
        _ = conn.execute(
            "CREATE TABLE IF NOT EXISTS _test_concurrent (id INTEGER PRIMARY KEY, val TEXT)"
        )
        conn.commit()
    finally:
        conn.close()

    def insert_row(index: int) -> None:
        local_conn = get_db_connection()
        try:
            _ = local_conn.execute(
                "INSERT INTO _test_concurrent (val) VALUES (?)",
                (f"row-{index}",),
            )
            local_conn.commit()
        finally:
            local_conn.close()

    async def run_inserts() -> None:
        await asyncio.gather(*[asyncio.to_thread(insert_row, index) for index in range(5)])

    asyncio.run(run_inserts())

    verify_conn = get_db_connection()
    try:
        count = int(verify_conn.execute("SELECT COUNT(*) FROM _test_concurrent").fetchone()[0])
        assert count == 5
    finally:
        verify_conn.close()
