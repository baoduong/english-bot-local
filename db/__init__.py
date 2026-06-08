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

init_db()
seed_shadowing_items()
