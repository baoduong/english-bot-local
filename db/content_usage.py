from db.connection import get_db_connection


def record_usage(segment_id, usage_type):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO content_usage (segment_id, usage_type) VALUES (?, ?)",
        (segment_id, usage_type)
    )
    conn.commit()
    conn.close()


def get_usage_history(segment_id=None, usage_type=None, limit=50):
    conn = get_db_connection()
    cursor = conn.cursor()

    query = "SELECT * FROM content_usage"
    params = []
    conditions = []

    if segment_id is not None:
        conditions.append("segment_id = ?")
        params.append(segment_id)
    if usage_type is not None:
        conditions.append("usage_type = ?")
        params.append(usage_type)

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    query += " ORDER BY used_at DESC LIMIT ?"
    params.append(limit)

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_unused_segments(limit=20):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """SELECT cs.* FROM content_segments cs
           LEFT JOIN content_usage cu ON cs.id = cu.segment_id
           WHERE cu.id IS NULL
           ORDER BY cs.id LIMIT ?""",
        (limit,)
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]
