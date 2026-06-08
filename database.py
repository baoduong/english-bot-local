"""Backward-compatible wrapper — new code should import from db/ package directly."""

from db import (
    get_db_connection, init_db,
    get_or_create_user, update_user_progress, adjust_user_level, increment_total_sessions,
    get_next_sentence, update_sentence_progress,
    save_failed_word, clear_failed_word, log_score, log_error_pattern, get_user_stats,
    record_word_attempt, record_word_attempts_batch, get_weak_words, get_strong_words,
    record_phoneme_error, record_phoneme_errors_batch, get_weak_phonemes,
    record_pattern_attempt, record_pattern_attempts_batch,
    get_weak_patterns, get_strong_patterns, get_all_patterns,
    create_shadowing_item, get_shadowing_item, list_shadowing_items,
    pick_shadowing_item, record_shadowing_attempt, get_shadowing_history,
    seed_shadowing_items, pick_content_shadowing,
    create_content_item, get_content_item, get_segments,
    list_content_items, search_content, bulk_import,
    compute_segment_metadata, find_segments_by_phoneme,
    find_segments_by_difficulty, find_segments_by_keyword,
    record_usage, get_usage_history, get_unused_segments,
    record_recommendation, mark_completed, mark_skipped,
    get_recent_recommendations, get_recently_recommended_ids,
)
