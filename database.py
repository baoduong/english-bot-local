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
    seed_shadowing_items,
)
