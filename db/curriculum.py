import json
from db.connection import get_db_connection


# ─────────────────────────────────────────────
# Curriculum CRUD
# ─────────────────────────────────────────────

def create_curriculum(user_id, goal_title, goal_description, interface_language='vi') -> int:
    """INSERT new curriculum, returns curriculum_id."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """INSERT INTO curriculums (user_id, goal_title, goal_description, interface_language)
           VALUES (?, ?, ?, ?)""",
        (user_id, goal_title, goal_description, interface_language)
    )
    conn.commit()
    curriculum_id = cursor.lastrowid
    conn.close()
    return curriculum_id


def get_active_curriculum(user_id) -> dict | None:
    """Return the active curriculum for user, or None."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM curriculums WHERE user_id = ? AND status = 'active' LIMIT 1",
        (user_id,)
    )
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def get_curriculum(curriculum_id) -> dict | None:
    """Return curriculum by id, or None."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM curriculums WHERE id = ?",
        (curriculum_id,)
    )
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def archive_curriculum(curriculum_id) -> None:
    """SET status='archived', completed_at=now."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """UPDATE curriculums
           SET status = 'archived', completed_at = datetime('now')
           WHERE id = ?""",
        (curriculum_id,)
    )
    conn.commit()
    conn.close()


def complete_curriculum(curriculum_id) -> None:
    """SET status='completed', completed_at=now."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """UPDATE curriculums
           SET status = 'completed', completed_at = datetime('now')
           WHERE id = ?""",
        (curriculum_id,)
    )
    conn.commit()
    conn.close()


def increment_phase_number(curriculum_id) -> int:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT COALESCE(MAX(phase_number), 0) AS max_phase_number FROM phases WHERE curriculum_id = ?",
        (curriculum_id,)
    )
    row = cursor.fetchone()
    new_phase_number = int(row["max_phase_number"] or 0) + 1

    cursor.execute(
        """UPDATE curriculums
           SET current_phase_number = ?
           WHERE id = ?""",
        (new_phase_number, curriculum_id)
    )
    conn.commit()
    conn.close()
    return new_phase_number


# ─────────────────────────────────────────────
# Phase CRUD
# ─────────────────────────────────────────────

def create_phase(curriculum_id, phase_number, theme, vocabulary, milestones) -> int:
    """INSERT new phase (vocabulary/milestones serialized as JSON). Returns phase_id.

    Handles UNIQUE(curriculum_id, phase_number) constraint by deleting any existing
    row with the same key and carrying forward the regeneration_count.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # Carry forward regeneration_count if a previous phase exists for this slot
    cursor.execute(
        "SELECT regeneration_count FROM phases WHERE curriculum_id = ? AND phase_number = ?",
        (curriculum_id, phase_number)
    )
    existing = cursor.fetchone()
    regen_count = (existing["regeneration_count"] + 1) if existing else 0

    if existing:
        cursor.execute(
            "DELETE FROM phases WHERE curriculum_id = ? AND phase_number = ?",
            (curriculum_id, phase_number)
        )

    cursor.execute(
        """INSERT INTO phases (curriculum_id, phase_number, theme, vocabulary, milestones, regeneration_count)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (
            curriculum_id,
            phase_number,
            theme,
            json.dumps(vocabulary, ensure_ascii=False),
            json.dumps(milestones, ensure_ascii=False),
            regen_count,
        )
    )
    conn.commit()
    phase_id = cursor.lastrowid
    conn.close()
    return phase_id


def _parse_phase_row(row) -> dict:
    """Convert a phases sqlite3.Row to dict and parse JSON columns."""
    d = dict(row)
    d["vocabulary"] = json.loads(d["vocabulary"]) if d.get("vocabulary") else []
    d["milestones"] = json.loads(d["milestones"]) if d.get("milestones") else []
    return d


def get_phase(phase_id) -> dict | None:
    """Return phase by id with parsed JSON columns, or None."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM phases WHERE id = ?", (phase_id,))
    row = cursor.fetchone()
    conn.close()
    return _parse_phase_row(row) if row else None


def get_active_phase(curriculum_id) -> dict | None:
    """Return the active phase for curriculum, or None."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM phases WHERE curriculum_id = ? AND status = 'active' LIMIT 1",
        (curriculum_id,)
    )
    row = cursor.fetchone()
    conn.close()
    return _parse_phase_row(row) if row else None


def get_phases_for_curriculum(curriculum_id) -> list:
    """Return all phases for curriculum ordered by phase_number."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM phases WHERE curriculum_id = ? ORDER BY phase_number ASC",
        (curriculum_id,)
    )
    rows = cursor.fetchall()
    conn.close()
    return [_parse_phase_row(r) for r in rows]


def activate_phase(phase_id) -> None:
    """SET status='active'."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE phases SET status = 'active' WHERE id = ?",
        (phase_id,)
    )
    conn.commit()
    conn.close()


def complete_phase(phase_id) -> None:
    """SET status='completed', completed_at=now."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """UPDATE phases
           SET status = 'completed', completed_at = datetime('now')
           WHERE id = ?""",
        (phase_id,)
    )
    conn.commit()
    conn.close()


def mark_phase_regenerated(phase_id) -> None:
    """SET status='regenerated'."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE phases SET status = 'regenerated' WHERE id = ?",
        (phase_id,)
    )
    conn.commit()
    conn.close()


def get_phase_regeneration_count(curriculum_id, phase_number) -> int:
    """Return regeneration_count for the current phase row at (curriculum_id, phase_number)."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT regeneration_count FROM phases WHERE curriculum_id = ? AND phase_number = ? LIMIT 1",
        (curriculum_id, phase_number)
    )
    row = cursor.fetchone()
    conn.close()
    return row["regeneration_count"] if row else 0


# ─────────────────────────────────────────────
# Phase Content CRUD
# ─────────────────────────────────────────────

def add_phase_content(phase_id, items: list) -> None:
    """Bulk INSERT phase_content rows. Each item is a dict with keys:
    sentence, target_phonemes (list), target_words (list), difficulty_score.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    for item in items:
        cursor.execute(
            """INSERT INTO phase_content (phase_id, sentence, target_phonemes, target_words, difficulty_score)
               VALUES (?, ?, ?, ?, ?)""",
            (
                phase_id,
                item["sentence"],
                json.dumps(item.get("target_phonemes", []), ensure_ascii=False),
                json.dumps(item.get("target_words", []), ensure_ascii=False),
                item.get("difficulty_score"),
            )
        )
    conn.commit()
    conn.close()


def _parse_content_row(row) -> dict:
    """Convert a phase_content sqlite3.Row to dict and parse JSON columns."""
    d = dict(row)
    d["target_phonemes"] = json.loads(d["target_phonemes"]) if d.get("target_phonemes") else []
    d["target_words"] = json.loads(d["target_words"]) if d.get("target_words") else []
    return d


def get_phase_content(phase_id) -> list:
    """Return all content rows for phase with parsed JSON columns."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM phase_content WHERE phase_id = ?",
        (phase_id,)
    )
    rows = cursor.fetchall()
    conn.close()
    return [_parse_content_row(r) for r in rows]


def get_next_practice_sentence(phase_id, exclude_content_id=None) -> dict | None:
    """Return the next sentence to practice.

    Priority: unattempted first (attempt_count=0), then struggling (low last_score).
    ORDER BY attempt_count ASC, difficulty_score ASC NULLS LAST, last_score ASC NULLS FIRST LIMIT 1
    excludes mastered sentences (mastered_at IS NULL).
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    if exclude_content_id:
        cursor.execute(
            """SELECT * FROM phase_content
               WHERE phase_id = ? AND mastered_at IS NULL AND id != ?
               ORDER BY attempt_count ASC, difficulty_score ASC NULLS LAST, last_score ASC NULLS FIRST
               LIMIT 1""",
            (phase_id, exclude_content_id),
        )
    else:
        cursor.execute(
            """SELECT * FROM phase_content
               WHERE phase_id = ? AND mastered_at IS NULL
               ORDER BY attempt_count ASC, difficulty_score ASC NULLS LAST, last_score ASC NULLS FIRST
               LIMIT 1""",
            (phase_id,),
        )
    row = cursor.fetchone()
    conn.close()
    return _parse_content_row(row) if row else None


def record_phase_content_attempt(content_id, score, target_words_passed: bool = True) -> int:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT consecutive_passes, mastered_at FROM phase_content WHERE id = ?",
        (content_id,),
    )
    row = cursor.fetchone()
    if not row:
        conn.close()
        return 0

    current_consecutive = int(row["consecutive_passes"] or 0)
    already_mastered = row["mastered_at"] is not None
    high_quality = score >= 80 and target_words_passed

    if high_quality:
        new_consecutive = current_consecutive + 1
        if new_consecutive >= 2 and not already_mastered:
            cursor.execute(
                """UPDATE phase_content
                   SET attempt_count = attempt_count + 1,
                       last_score = ?,
                       consecutive_passes = ?,
                       mastered_at = datetime('now')
                   WHERE id = ?""",
                (int(score), new_consecutive, content_id)
            )
        else:
            cursor.execute(
                """UPDATE phase_content
                   SET attempt_count = attempt_count + 1,
                       last_score = ?,
                       consecutive_passes = ?
                   WHERE id = ?""",
                (int(score), new_consecutive, content_id)
            )
    else:
        new_consecutive = 0
        cursor.execute(
            """UPDATE phase_content
               SET attempt_count = attempt_count + 1,
                   last_score = ?,
                   consecutive_passes = ?
               WHERE id = ?""",
            (int(score), new_consecutive, content_id)
        )
    conn.commit()
    conn.close()
    return new_consecutive


def get_consecutive_passes(content_id) -> int:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT consecutive_passes FROM phase_content WHERE id = ?", (content_id,))
    row = cursor.fetchone()
    conn.close()
    return int(row["consecutive_passes"] or 0) if row else 0


def get_phase_progress(phase_id) -> dict:
    """Return progress summary for a phase.

    Returns:
        {
          total: int,
          attempted: int,
          mastered: int,
          avg_score: float | None,   # AVG of last_score where last_score IS NOT NULL
          struggling_words: list[str] # sentence text where last_score < 60
        }
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        """SELECT
               COUNT(*) as total,
               SUM(CASE WHEN attempt_count > 0 THEN 1 ELSE 0 END) as attempted,
               SUM(CASE WHEN mastered_at IS NOT NULL THEN 1 ELSE 0 END) as mastered,
               AVG(CASE WHEN last_score IS NOT NULL THEN last_score END) as avg_score
           FROM phase_content
           WHERE phase_id = ?""",
        (phase_id,)
    )
    stats = dict(cursor.fetchone())

    cursor.execute(
        "SELECT sentence FROM phase_content WHERE phase_id = ? AND last_score < 60",
        (phase_id,)
    )
    struggling_rows = cursor.fetchall()
    conn.close()

    return {
        "total": stats["total"] or 0,
        "attempted": stats["attempted"] or 0,
        "mastered": stats["mastered"] or 0,
        "avg_score": round(stats["avg_score"], 2) if stats["avg_score"] is not None else None,
        "struggling_words": [r["sentence"] for r in struggling_rows],
    }


# ─────────────────────────────────────────────
# Onboarding Conversation CRUD
# ─────────────────────────────────────────────

def add_onboarding_turn(user_id, turn_number, role, content) -> int:
    """INSERT onboarding turn, returns id."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """INSERT INTO onboarding_conversations (user_id, turn_number, role, content)
           VALUES (?, ?, ?, ?)""",
        (user_id, turn_number, role, content)
    )
    conn.commit()
    row_id = cursor.lastrowid
    conn.close()
    return row_id


def get_onboarding_conversation(user_id) -> list:
    """Return all turns for user ordered by turn_number."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM onboarding_conversations WHERE user_id = ? ORDER BY turn_number ASC",
        (user_id,)
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def clear_onboarding_conversation(user_id) -> None:
    """DELETE all turns for user."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM onboarding_conversations WHERE user_id = ?",
        (user_id,)
    )
    conn.commit()
    conn.close()


def count_onboarding_turns(user_id) -> int:
    """Return count of turns for user."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT COUNT(*) as cnt FROM onboarding_conversations WHERE user_id = ?",
        (user_id,)
    )
    row = cursor.fetchone()
    conn.close()
    return row["cnt"]
