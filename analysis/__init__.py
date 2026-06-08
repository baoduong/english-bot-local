"""analysis package — Pronunciation analysis, phoneme comparison, error classification, and learning memory."""

from analysis.phonemes import clean_word, phoneme_similarity
from analysis.errors import classify_error, ERROR_TYPE_LABELS, ANSI_GREEN, ANSI_YELLOW, ANSI_RED, ANSI_GRAY, ANSI_RESET
from analysis.pronunciation import analyze_audio, analyze_single_word
from analysis.patterns import extract_patterns, KNOWN_PATTERNS
from analysis.learning_memory import (get_learner_profile, detect_trends,
                                      get_learning_insights, get_practice_recommendations)
from analysis.drills import (generate_phoneme_drills, generate_word_drills,
                             generate_pattern_drills, generate_daily_practice)
from analysis.recommendations import (get_candidate_segments, score_candidate,
                                      get_recommended_content, build_today_session)
