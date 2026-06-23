from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
from db.connection import get_db_connection
from db.curriculum import record_phase_content_attempt
from db.schema import init_db


def _insert_phase_content() -> int:
    conn = get_db_connection()
    try:
        conn.execute(
            "INSERT INTO curriculums (user_id, goal_title, goal_description) VALUES (?, ?, ?)",
            ("user-1", "Goal", "Desc"),
        )
        curriculum_id = conn.execute("SELECT id FROM curriculums LIMIT 1").fetchone()[0]
        conn.execute(
            "INSERT INTO phases (curriculum_id, phase_number, theme, vocabulary, milestones) VALUES (?, ?, ?, ?, ?)",
            (curriculum_id, 1, "Theme", "[]", "[]"),
        )
        phase_id = conn.execute("SELECT id FROM phases LIMIT 1").fetchone()[0]
        cursor = conn.execute(
            "INSERT INTO phase_content (phase_id, sentence, target_words, difficulty_score) VALUES (?, ?, ?, ?)",
            (phase_id, "test sentence", "[]", 5),
        )
        conn.commit()
        return int(cursor.lastrowid)
    finally:
        conn.close()


def test_record_attempt_atomic(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DB_PATH", str(tmp_path / "test.db"))
    init_db()
    content_id = _insert_phase_content()

    async def run_attempts() -> list[int]:
        return await asyncio.gather(
            *[asyncio.to_thread(record_phase_content_attempt, content_id, 90, True) for _ in range(5)]
        )

    _ = asyncio.run(run_attempts())

    conn = get_db_connection()
    try:
        row = conn.execute(
            "SELECT consecutive_passes, attempt_count, mastered_at FROM phase_content WHERE id = ?",
            (content_id,),
        ).fetchone()
    finally:
        conn.close()

    assert int(row["consecutive_passes"]) == 5
    assert int(row["attempt_count"]) == 5
    assert row["mastered_at"] is not None


def test_mastery_triggers_at_2(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DB_PATH", str(tmp_path / "test.db"))
    init_db()
    content_id = _insert_phase_content()

    first_pass = record_phase_content_attempt(content_id, 90, True)
    second_pass = record_phase_content_attempt(content_id, 90, True)

    conn = get_db_connection()
    try:
        mastered_row = conn.execute(
            "SELECT consecutive_passes, attempt_count, mastered_at FROM phase_content WHERE id = ?",
            (content_id,),
        ).fetchone()
    finally:
        conn.close()

    assert first_pass == 1
    assert second_pass == 2
    assert int(mastered_row["consecutive_passes"]) == 2
    assert int(mastered_row["attempt_count"]) == 2
    assert mastered_row["mastered_at"] is not None

    failed_attempt = record_phase_content_attempt(content_id, 50, False)

    conn = get_db_connection()
    try:
        failed_row = conn.execute(
            "SELECT consecutive_passes, attempt_count, mastered_at FROM phase_content WHERE id = ?",
            (content_id,),
        ).fetchone()
    finally:
        conn.close()

    assert failed_attempt == 0
    assert int(failed_row["consecutive_passes"]) == 0
    assert int(failed_row["attempt_count"]) == 3
    assert failed_row["mastered_at"] == mastered_row["mastered_at"]
