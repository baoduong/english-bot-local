"""Backward-compatible wrapper — new code should import from db/ package directly.

This module re-exports functions from the db/ package for legacy callers
(primarily app.py, the Discord bot) that pre-date the db/ package split.
"""
# ruff: noqa: F401 — these ARE used, just via re-export

from db.sentences import (
    get_next_sentence,
    update_sentence_progress,
)
from db.users import (
    update_user_progress,
    adjust_user_level,
    increment_total_sessions,
)
from db.tracking import (
    save_failed_word,
    clear_failed_word,
    log_score,
    log_error_pattern,
    get_user_stats,
)
from db.word_stats import (
    record_word_attempts_batch,
)
from db.phoneme_tracking import (
    record_phoneme_errors_batch,
    get_weak_phonemes,
)
from db.patterns import (
    record_pattern_attempts_batch,
)
