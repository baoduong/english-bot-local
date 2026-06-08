GOAL_PROFILES = {
    "software_engineering": {
        "tags": [
            "engineering", "code-review", "api", "database", "devops", "testing",
            "architecture", "debugging", "refactoring", "git", "docker", "kubernetes",
            "typescript", "performance", "observability", "tech-debt", "incidents",
            "agile", "docs", "dependencies", "security",
        ],
        "key_skills": ["technical vocabulary", "code review communication", "standup reporting"],
        "label": "Software Engineering",
    },
    "ai": {
        "tags": [
            "ai", "agents", "training", "search", "data", "cost",
            "engineering", "architecture", "security", "testing", "compliance",
        ],
        "key_skills": ["AI terminology", "technical presentations", "research discussion"],
        "label": "AI & Machine Learning",
    },
    "technical_communication": {
        "tags": [
            "meetings", "communication", "retro", "one-on-one", "feedback",
            "handoff", "email", "delegation", "docs", "agile",
        ],
        "key_skills": ["meeting facilitation", "async communication", "presentation delivery"],
        "label": "Technical Communication",
    },
    "business": {
        "tags": [
            "startup", "fundraising", "growth", "moat", "hiring", "metrics",
            "launch", "customer-success", "pitch", "discovery", "career",
            "leadership", "strategy",
        ],
        "key_skills": ["pitching", "negotiation", "stakeholder management"],
        "label": "Business & Startups",
    },
    "travel": {
        "tags": [
            "travel", "airport", "hotel", "food", "navigation", "emergency",
            "transport", "weather", "culture", "visa", "health", "shopping",
            "business",
        ],
        "key_skills": ["survival phrases", "polite requests", "emergency communication"],
        "label": "Travel & Daily Life",
    },
    "daily_conversation": {
        "tags": [
            "productivity", "focus", "planning", "priorities", "goals",
            "wellbeing", "feedback", "meetings", "communication",
        ],
        "key_skills": ["small talk", "expressing opinions", "active listening"],
        "label": "Daily Conversation",
    },
}

VALID_GOAL_TYPES = list(GOAL_PROFILES.keys())


def calculate_goal_alignment(segment_tags, user_goals):
    """Calculate how well a segment's tags align with user's learning goals.

    Args:
        segment_tags: list of tag strings from the content item
        user_goals: list of {"goal_type": str, "priority": "primary"|"secondary"}

    Returns:
        {"score": int 0-10, "matched_goal": str|None, "priority": str|None}
    """
    if not user_goals or not segment_tags:
        return {"score": 0, "matched_goal": None, "priority": None}

    segment_tag_set = set(segment_tags)
    best_score = 0
    best_goal = None
    best_priority = None

    for goal in user_goals:
        goal_type = goal["goal_type"]
        priority = goal.get("priority", "secondary")
        profile = GOAL_PROFILES.get(goal_type)
        if not profile:
            continue

        goal_tags = set(profile["tags"])
        overlap = segment_tag_set & goal_tags

        if not overlap:
            continue

        coverage = len(overlap) / max(len(segment_tag_set), 1)
        raw_score = min(10, int(coverage * 10) + len(overlap))

        weight = raw_score if priority == "primary" else int(raw_score * 0.5)

        if weight > best_score:
            best_score = weight
            best_goal = goal_type
            best_priority = priority

    return {"score": best_score, "matched_goal": best_goal, "priority": best_priority}


def get_goal_progress(user_id, user_goals, profile):
    """Calculate progress toward each goal based on practiced content with matching tags.

    Args:
        user_id: the learner's id
        user_goals: list of goal dicts
        profile: learner profile from get_learner_profile()

    Returns:
        list of {"goal_type", "label", "progress_pct", "key_skills", "status"}
    """
    import json
    from db.connection import get_db_connection

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT DISTINCT cu.segment_id, ci.tags
        FROM content_usage cu
        JOIN content_segments cs ON cs.id = cu.segment_id
        JOIN content_items ci ON ci.id = cs.item_id
        WHERE ci.tags IS NOT NULL
    """)
    practiced_rows = cursor.fetchall()
    conn.close()

    practiced_with_tags = []
    for row in practiced_rows:
        try:
            tags = json.loads(row[1]) if row[1] else []
        except (json.JSONDecodeError, TypeError):
            tags = []
        if tags:
            practiced_with_tags.append(set(tags))

    total_practiced_segments = len(practiced_with_tags)

    results = []
    for goal in user_goals:
        goal_type = goal["goal_type"]
        gp = GOAL_PROFILES.get(goal_type)
        if not gp:
            continue

        goal_tags = set(gp["tags"])

        relevant_count = sum(
            1 for seg_tags in practiced_with_tags if seg_tags & goal_tags
        )

        target = len(goal_tags) * 3
        progress_pct = min(100, int((relevant_count / max(target, 1)) * 100))

        if progress_pct >= 80:
            status = "strong"
        elif progress_pct >= 40:
            status = "developing"
        else:
            status = "beginning"

        results.append({
            "goal_type": goal_type,
            "label": gp["label"],
            "priority": goal.get("priority", "secondary"),
            "progress_pct": progress_pct,
            "relevant_practiced": relevant_count,
            "total_practiced": total_practiced_segments,
            "key_skills": gp["key_skills"],
            "status": status,
        })

    return results
