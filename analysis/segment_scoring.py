import re

_WORD_PATTERN = re.compile(r"[a-zA-Z']+")

_HARD_WORDS = frozenset([
    "entrepreneurship", "prerequisite", "phenomenon", "simultaneously",
    "particularly", "unfortunately", "infrastructure", "representative",
    "communication", "responsibility", "approximately", "circumstances",
    "comprehensive", "determination", "characteristic", "implementation",
    "unprecedented", "administrative", "recommendation", "differentiate",
])


def score_segment_difficulty(text):
    words = _WORD_PATTERN.findall(text.lower())
    if not words:
        return 1

    word_count = len(words)
    char_length = len(text)
    unique_ratio = len(set(words)) / word_count
    avg_word_len = sum(len(w) for w in words) / word_count
    hard_word_count = sum(1 for w in words if w in _HARD_WORDS or len(w) >= 10)

    score = 0

    if word_count <= 5:
        score += 0
    elif word_count <= 10:
        score += 1
    elif word_count <= 15:
        score += 2
    else:
        score += 3

    if avg_word_len >= 7:
        score += 2
    elif avg_word_len >= 5:
        score += 1

    if hard_word_count >= 2:
        score += 2
    elif hard_word_count >= 1:
        score += 1

    if char_length > 80:
        score += 1

    difficulty = min(5, max(1, (score // 2) + 1))
    return difficulty
