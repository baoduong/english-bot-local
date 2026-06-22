from __future__ import annotations

from typing import Any, cast

from db.connection import get_db_connection
from db.curriculum import get_phase, get_phase_content, get_phase_progress


def _format_score(value: Any) -> str:
    if value is None:
        return "N/A"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        rounded = round(value, 2)
        if rounded.is_integer():
            return str(int(rounded))
        return f"{rounded:.2f}".rstrip("0").rstrip(".")
    return str(value)


def _as_content_rows(content: list[object]) -> list[dict[str, Any]]:
    return [cast(dict[str, Any], item) for item in content if isinstance(item, dict)]


def build_phase_performance_summary(user_id: str, phase_id: int) -> str:
    progress = get_phase_progress(phase_id)
    content = _as_content_rows(get_phase_content(phase_id))
    phase = get_phase(phase_id) or {}

    scored_content = [item for item in content if item.get("last_score") is not None]
    scored_content.sort(key=lambda item: (float(item.get("last_score") or 0), -(int(item.get("attempt_count") or 0))))
    hardest_sentences = scored_content[:5]

    mastered_count = sum(1 for item in content if item.get("mastered_at"))
    attempted_count = sum(1 for item in content if int(item.get("attempt_count") or 0) > 0)
    total_count = len(content)

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """SELECT word,
                  ROUND(total_score / CAST(attempt_count AS REAL), 1) AS avg_score,
                  attempt_count,
                  success_count
           FROM word_statistics
           WHERE user_id = ? AND attempt_count >= 2
           ORDER BY avg_score ASC, attempt_count DESC, success_count ASC
           LIMIT 5""",
        (user_id,),
    )
    struggling_words = [dict(row) for row in cursor.fetchall()]

    cursor.execute(
        """SELECT error_type,
                  SUM(count) AS total_count,
                  GROUP_CONCAT(word, ', ') AS sample_words
           FROM error_patterns
           WHERE user_id = ?
           GROUP BY error_type
           ORDER BY total_count DESC, error_type ASC
           LIMIT 5""",
        (user_id,),
    )
    error_patterns = [dict(row) for row in cursor.fetchall()]
    conn.close()

    lines: list[str] = [
        f"Phase {phase.get('phase_number', '?')} performance summary:",
        f"- Average score: {_format_score(progress.get('avg_score'))}/100",
        f"- Mastered: {mastered_count}/{total_count} sentences",
        f"- Attempted: {attempted_count}/{total_count} sentences",
        f"- Total target sentences in phase: {total_count}",
    ]

    if hardest_sentences:
        lines.append("")
        lines.append("Hardest sentences for the learner (lowest scores, most attempts):")
        for item in hardest_sentences[:5]:
            lines.append(
                f"- score={_format_score(item.get('last_score'))}, "
                f"attempts={int(item.get('attempt_count') or 0)}: "
                f"\"{item.get('sentence', '')}\""
            )

    if struggling_words:
        lines.append("")
        lines.append("Top struggling words (lowest average scores across attempts):")
        for word in struggling_words:
            lines.append(
                f"- {word.get('word', '')}: avg={_format_score(word.get('avg_score'))}, "
                f"attempts={int(word.get('attempt_count') or 0)}, "
                f"success={int(word.get('success_count') or 0)}"
            )

    if error_patterns:
        lines.append("")
        lines.append("Most frequent pronunciation error patterns:")
        for error in error_patterns:
            sample_words = error.get("sample_words") or ""
            lines.append(
                f"- {error.get('error_type', 'unknown')}: {int(error.get('total_count') or 0)} occurrences"
                + (f" | examples: {sample_words}" if sample_words else "")
            )

    lines.extend(
        [
            "",
            "Guidance for generating the next phase:",
            "- Increase difficulty in small, incremental steps that match the learner's current ability.",
            "- Reuse words the learner did well on to build a sense of progress, but re-introduce struggling words in NEW sentence contexts (spaced repetition).",
            "- If the average score is below 75, prioritize small, achievable goals over ambitious ones.",
            "- Target the most frequent pronunciation error patterns above with vocabulary that practices those exact sounds (e.g., if 'th_sound' is frequent, include more /θ/ and /ð/ words).",
            "- Do NOT regress to material easier than what the learner already mastered.",
            "- Do NOT repeat the exact same sentences from previous phases; create new sentences that exercise the same skills in different contexts.",
        ]
    )

    return "\n".join(lines)
