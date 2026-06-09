"""db package — Database models and queries for the English Learning Bot."""

from db.schema import init_db
from db.connection import get_db_connection, DB_NAME
from db.users import get_or_create_user, update_user_progress, adjust_user_level, increment_total_sessions
from db.sentences import get_next_sentence, update_sentence_progress
from db.tracking import save_failed_word, clear_failed_word, log_score, log_error_pattern, get_user_stats
from db.word_stats import record_word_attempt, record_word_attempts_batch, get_weak_words, get_strong_words
from db.phoneme_tracking import record_phoneme_error, record_phoneme_errors_batch, get_weak_phonemes
from db.patterns import (record_pattern_attempt, record_pattern_attempts_batch,
                         get_weak_patterns, get_strong_patterns, get_all_patterns)
from db.shadowing import (create_shadowing_item, get_shadowing_item, list_shadowing_items,
                          pick_shadowing_item, record_shadowing_attempt, get_shadowing_history,
                          seed_shadowing_items, pick_content_shadowing)
from db.content import (create_content_item, get_content_item, get_segments,
                        list_content_items, search_content, bulk_import,
                        compute_segment_metadata, find_segments_by_phoneme,
                        find_segments_by_difficulty, find_segments_by_keyword)
from db.content_usage import record_usage, get_usage_history, get_unused_segments
from db.recommendations import (record_recommendation, mark_completed, mark_skipped,
                                get_recent_recommendations, get_recently_recommended_ids)
from db.goals import get_learning_goals, set_learning_goals, get_primary_goal, clear_learning_goals
from db.sessions import save_session, load_all_sessions, delete_session

init_db()
seed_shadowing_items()


def _seed_content_if_empty():
    """Auto-seed content library on first run if content_items table is empty."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as n FROM content_items")
    count = cursor.fetchone()["n"]
    conn.close()

    if count == 0:
        from seed_content import get_seed_items
        items = get_seed_items()
        results = bulk_import(items)
        total_segments = sum(r["segment_count"] for r in results)
        print(f"[seed] Imported {len(results)} content items ({total_segments} segments)")


_seed_content_if_empty()
