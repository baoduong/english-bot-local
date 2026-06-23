from __future__ import annotations

import os
import sqlite3
import tempfile
from contextlib import contextmanager
from typing import Iterator, cast

import pytest
from hypothesis import HealthCheck, given, settings, strategies as st

from db.connection import get_db_connection
from db.curriculum import record_phase_content_attempt
from db.schema import init_db


ATTEMPT = st.tuples(st.integers(min_value=0, max_value=100), st.booleans())


def _seed_phase_content() -> int:
    conn = get_db_connection()
    try:
        _ = conn.execute(
            "INSERT INTO curriculums (user_id, goal_title, goal_description) VALUES (?, ?, ?)",
            ("prop-user", "Goal", "Desc"),
        )
        curriculum_row = conn.execute("SELECT id FROM curriculums LIMIT 1").fetchone()
        assert curriculum_row is not None
        curriculum_id = int(curriculum_row[0])
        _ = conn.execute(
            "INSERT INTO phases (curriculum_id, phase_number, theme, vocabulary, milestones) VALUES (?, ?, ?, ?, ?)",
            (curriculum_id, 1, "Theme", "[]", "[]"),
        )
        phase_row = conn.execute("SELECT id FROM phases LIMIT 1").fetchone()
        assert phase_row is not None
        phase_id = int(phase_row[0])
        cursor = conn.execute(
            "INSERT INTO phase_content (phase_id, sentence, target_words, difficulty_score) VALUES (?, ?, ?, ?)",
            (phase_id, "test sentence", "[]", 5),
        )
        conn.commit()
        assert cursor.lastrowid is not None
        return int(cursor.lastrowid)
    finally:
        conn.close()


@contextmanager
def _isolated_db(monkeypatch: pytest.MonkeyPatch, name: str) -> Iterator[int]:
    with tempfile.TemporaryDirectory() as tmp_dir:
        db_path = os.path.join(tmp_dir, name)
        monkeypatch.setenv("DB_PATH", db_path)
        init_db()
        yield _seed_phase_content()


def _has_two_consecutive_quality_passes(attempts: list[tuple[int, bool]]) -> bool:
    consecutive = 0
    for score, target_words_passed in attempts:
        if score >= 80 and target_words_passed:
            consecutive += 1
            if consecutive >= 2:
                return True
        else:
            consecutive = 0
    return False


@pytest.mark.slow
@settings(max_examples=60, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(attempts=st.lists(ATTEMPT, min_size=1, max_size=15))
def test_mastery_requires_two_consecutive_quality_passes(
    attempts: list[tuple[int, bool]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with _isolated_db(monkeypatch, f"mastery_{abs(hash(tuple(attempts)))}.db") as content_id:
        final_consecutive = 0
        for score, target_words_passed in attempts:
            final_consecutive = record_phase_content_attempt(content_id, score, target_words_passed)

        conn = get_db_connection()
        try:
            row = conn.execute(
                "SELECT mastered_at, consecutive_passes, attempt_count, last_score FROM phase_content WHERE id = ?",
                (content_id,),
            ).fetchone()
        finally:
            conn.close()

    assert row is not None
    row = cast(sqlite3.Row, row)
    assert int(row["attempt_count"]) == len(attempts)
    assert int(row["consecutive_passes"]) == final_consecutive
    assert (row["mastered_at"] is not None) == _has_two_consecutive_quality_passes(attempts)
    assert int(row["last_score"]) == attempts[-1][0]


@pytest.mark.slow
@settings(max_examples=60, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(n_passes=st.integers(min_value=2, max_value=20), fail_score=st.integers(min_value=0, max_value=79))
def test_failure_resets_consecutive_pass_count(
    n_passes: int,
    fail_score: int,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with _isolated_db(monkeypatch, f"reset_{n_passes}_{fail_score}.db") as content_id:
        for _ in range(n_passes):
            assert record_phase_content_attempt(content_id, 90, True) >= 1

        failed_return = record_phase_content_attempt(content_id, fail_score, False)

        conn = get_db_connection()
        try:
            row = conn.execute(
                "SELECT consecutive_passes, attempt_count, mastered_at, last_score FROM phase_content WHERE id = ?",
                (content_id,),
            ).fetchone()
        finally:
            conn.close()

    assert row is not None
    row = cast(sqlite3.Row, row)
    assert failed_return == 0
    assert int(row["consecutive_passes"]) == 0
    assert int(row["attempt_count"]) == n_passes + 1
    assert int(row["last_score"]) == fail_score
    assert row["mastered_at"] is not None
