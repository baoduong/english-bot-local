import json
import uuid
from db.connection import get_db_connection
from analysis.segmentation import segment_text
from analysis.segment_scoring import score_segment_difficulty
from analysis.phoneme_extraction import extract_target_phonemes


def create_content_item(title, text, difficulty=1, source_type="manual", tags=None):
    """Create a content item and auto-segment the text into sentences.

    Returns dict with item_id and segment_count.
    """
    item_id = str(uuid.uuid4())[:8]
    tags_json = json.dumps(tags or [])

    segments = segment_text(text)

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO content_items (id, title, source_type, difficulty, tags) VALUES (?, ?, ?, ?, ?)",
        (item_id, title, source_type, difficulty, tags_json)
    )

    for position, segment in enumerate(segments, start=1):
        diff_score = score_segment_difficulty(segment)
        phonemes = json.dumps(extract_target_phonemes(segment), ensure_ascii=False)
        cursor.execute(
            "INSERT INTO content_segments (content_item_id, text, position, difficulty_score, phoneme_metadata) VALUES (?, ?, ?, ?, ?)",
            (item_id, segment, position, diff_score, phonemes)
        )

    conn.commit()
    conn.close()

    return {"item_id": item_id, "segment_count": len(segments)}


def get_content_item(item_id):
    """Get a single content item by ID (without segments)."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM content_items WHERE id = ?", (item_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        result = dict(row)
        try:
            result["tags"] = json.loads(result["tags"])
        except (json.JSONDecodeError, TypeError):
            result["tags"] = []
        return result
    return None


def get_segments(item_id):
    """Get all segments for a content item, ordered by position."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM content_segments WHERE content_item_id = ? ORDER BY position",
        (item_id,)
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def list_content_items(limit=20, difficulty=None, tag=None):
    """List content items, optionally filtered by difficulty or tag."""
    conn = get_db_connection()
    cursor = conn.cursor()

    query = "SELECT * FROM content_items"
    params = []
    conditions = []

    if difficulty is not None:
        conditions.append("difficulty = ?")
        params.append(difficulty)

    if tag:
        conditions.append("tags LIKE ?")
        params.append(f'%"{tag}"%')

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    query += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    results = []
    for row in rows:
        item = dict(row)
        try:
            item["tags"] = json.loads(item["tags"])
        except (json.JSONDecodeError, TypeError):
            item["tags"] = []
        results.append(item)
    return results


def search_content(query_text, limit=20):
    """Full-text search across content items and segments."""
    conn = get_db_connection()
    cursor = conn.cursor()

    search_pattern = f"%{query_text}%"

    cursor.execute(
        """SELECT DISTINCT ci.* FROM content_items ci
           LEFT JOIN content_segments cs ON ci.id = cs.content_item_id
           WHERE ci.title LIKE ? OR cs.text LIKE ?
           ORDER BY ci.created_at DESC LIMIT ?""",
        (search_pattern, search_pattern, limit)
    )
    rows = cursor.fetchall()
    conn.close()

    results = []
    for row in rows:
        item = dict(row)
        try:
            item["tags"] = json.loads(item["tags"])
        except (json.JSONDecodeError, TypeError):
            item["tags"] = []
        results.append(item)
    return results


def bulk_import(items):
    """Import multiple content items at once.

    Args:
        items: list of dicts, each with keys: title, text, difficulty (optional), tags (optional)

    Returns:
        list of {item_id, segment_count} results.
    """
    results = []
    for item in items:
        result = create_content_item(
            title=item["title"],
            text=item["text"],
            difficulty=item.get("difficulty", 1),
            source_type=item.get("source_type", "manual"),
            tags=item.get("tags"),
        )
        results.append(result)
    return results


def compute_segment_metadata(item_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, text FROM content_segments WHERE content_item_id = ? ORDER BY position",
        (item_id,)
    )
    rows = cursor.fetchall()

    for row in rows:
        difficulty = score_segment_difficulty(row["text"])
        phonemes = extract_target_phonemes(row["text"])
        phonemes_json = json.dumps(phonemes, ensure_ascii=False)
        cursor.execute(
            "UPDATE content_segments SET difficulty_score = ?, phoneme_metadata = ? WHERE id = ?",
            (difficulty, phonemes_json, row["id"])
        )

    conn.commit()
    conn.close()
    return len(rows)


def find_segments_by_phoneme(phoneme, limit=20):
    conn = get_db_connection()
    cursor = conn.cursor()
    search_pattern = f'%"{phoneme}"%'
    cursor.execute(
        """SELECT cs.*, ci.title as item_title FROM content_segments cs
           JOIN content_items ci ON cs.content_item_id = ci.id
           WHERE cs.phoneme_metadata LIKE ?
           ORDER BY cs.difficulty_score ASC LIMIT ?""",
        (search_pattern, limit)
    )
    rows = cursor.fetchall()
    conn.close()
    results = []
    for row in rows:
        item = dict(row)
        try:
            item["phoneme_metadata"] = json.loads(item["phoneme_metadata"])
        except (json.JSONDecodeError, TypeError):
            item["phoneme_metadata"] = []
        results.append(item)
    return results


def find_segments_by_difficulty(min_difficulty=1, max_difficulty=5, limit=20):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """SELECT cs.*, ci.title as item_title FROM content_segments cs
           JOIN content_items ci ON cs.content_item_id = ci.id
           WHERE cs.difficulty_score >= ? AND cs.difficulty_score <= ?
           ORDER BY cs.difficulty_score ASC LIMIT ?""",
        (min_difficulty, max_difficulty, limit)
    )
    rows = cursor.fetchall()
    conn.close()
    results = []
    for row in rows:
        item = dict(row)
        try:
            item["phoneme_metadata"] = json.loads(item["phoneme_metadata"])
        except (json.JSONDecodeError, TypeError):
            item["phoneme_metadata"] = []
        results.append(item)
    return results


def find_segments_by_keyword(keyword, limit=20):
    conn = get_db_connection()
    cursor = conn.cursor()
    search_pattern = f"%{keyword}%"
    cursor.execute(
        """SELECT cs.*, ci.title as item_title FROM content_segments cs
           JOIN content_items ci ON cs.content_item_id = ci.id
           WHERE cs.text LIKE ?
           ORDER BY cs.difficulty_score ASC LIMIT ?""",
        (search_pattern, limit)
    )
    rows = cursor.fetchall()
    conn.close()
    results = []
    for row in rows:
        item = dict(row)
        try:
            item["phoneme_metadata"] = json.loads(item["phoneme_metadata"])
        except (json.JSONDecodeError, TypeError):
            item["phoneme_metadata"] = []
        results.append(item)
    return results
