import json
import uuid
from db.connection import get_db_connection
from analysis.segmentation import segment_text


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
        cursor.execute(
            "INSERT INTO content_segments (content_item_id, text, position) VALUES (?, ?, ?)",
            (item_id, segment, position)
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
