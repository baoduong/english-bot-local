"""analysis package — Pronunciation analysis, phoneme comparison, error classification, and learning memory."""

from analysis.phonemes import clean_word, phoneme_similarity
from analysis.errors import classify_error, ERROR_TYPE_LABELS, ANSI_GREEN, ANSI_YELLOW, ANSI_RED, ANSI_GRAY, ANSI_RESET
from analysis.pronunciation import analyze_audio, analyze_single_word
from analysis.patterns import extract_patterns, KNOWN_PATTERNS
from analysis.learning_memory import (get_learner_profile, detect_trends,
                                      get_learning_insights, get_practice_recommendations)
from analysis.metrics import get_learning_progress, export_learning_profile
