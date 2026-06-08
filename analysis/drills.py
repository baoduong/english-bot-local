from db.word_stats import get_weak_words
from db.phoneme_tracking import get_weak_phonemes
from db.patterns import get_weak_patterns


PHONEME_WORD_BANK = {
    "θ": ["think", "thank", "thin", "three", "thirty", "thought", "through", "thumb", "therapy", "thunder"],
    "ð": ["the", "this", "that", "there", "these", "those", "them", "then", "other", "weather"],
    "ɹ": ["run", "right", "read", "river", "really", "around", "correct", "program", "road", "rain"],
    "l": ["live", "light", "learn", "little", "level", "listen", "total", "follow", "table", "pull"],
    "ʃ": ["she", "ship", "show", "should", "share", "shake", "shelter", "sure", "nation", "special"],
    "ʒ": ["measure", "pleasure", "vision", "decision", "usual", "casual", "garage", "massage", "beige", "rouge"],
    "tʃ": ["church", "chance", "change", "charge", "chapter", "challenge", "achieve", "match", "catch", "watch"],
    "dʒ": ["just", "job", "join", "judge", "journey", "gentle", "huge", "bridge", "edge", "age"],
    "ŋ": ["sing", "thing", "ring", "bring", "long", "wrong", "young", "strong", "among", "along"],
    "v": ["very", "voice", "value", "visit", "view", "never", "over", "have", "give", "save"],
    "w": ["well", "work", "want", "week", "would", "away", "always", "between", "power", "twelve"],
    "z": ["zero", "zone", "zip", "zoo", "zeal", "buzz", "jazz", "fizz", "was", "because"],
    "f": ["find", "first", "four", "feel", "fast", "phone", "enough", "offer", "staff", "proof"],
    "s": ["see", "say", "side", "some", "start", "center", "science", "since", "space", "source"],
    "C#": ["hand", "stand", "just", "fast", "next", "project", "product", "impact", "accept", "suggest"],
    "V": ["about", "important", "develop", "consider", "determine", "photograph", "economy", "category", "particular", "opportunity"],
}

PATTERN_SENTENCE_BANK = {
    "i'd like to": [
        "I'd like to order a coffee.",
        "I'd like to know more about this.",
        "I'd like to ask a quick question.",
        "I'd like to schedule a meeting.",
        "I'd like to confirm my reservation.",
    ],
    "could you": [
        "Could you help me with this?",
        "Could you repeat that please?",
        "Could you send me the file?",
        "Could you explain this concept?",
        "Could you check this for me?",
    ],
    "would you mind": [
        "Would you mind closing the door?",
        "Would you mind waiting a moment?",
        "Would you mind sharing your screen?",
        "Would you mind reviewing this document?",
        "Would you mind speaking more slowly?",
    ],
    "i'm going to": [
        "I'm going to finish this today.",
        "I'm going to call them tomorrow.",
        "I'm going to prepare the presentation.",
        "I'm going to take a break.",
        "I'm going to send you the details.",
    ],
    "do you think": [
        "Do you think we should proceed?",
        "Do you think this is correct?",
        "Do you think it will work?",
        "Do you think we need more time?",
        "Do you think they'll agree?",
    ],
    "i've been": [
        "I've been working on this all week.",
        "I've been thinking about your suggestion.",
        "I've been meaning to ask you.",
        "I've been waiting for the results.",
        "I've been trying to reach you.",
    ],
    "it seems like": [
        "It seems like a good idea.",
        "It seems like we need more data.",
        "It seems like the system is down.",
        "It seems like everyone agrees.",
        "It seems like rain is coming.",
    ],
    "i was wondering": [
        "I was wondering if you could help.",
        "I was wondering about the deadline.",
        "I was wondering what you think.",
        "I was wondering if we could meet.",
        "I was wondering about the budget.",
    ],
    "the reason is": [
        "The reason is we ran out of time.",
        "The reason is the data was incomplete.",
        "The reason is they changed the plan.",
        "The reason is it wasn't approved yet.",
        "The reason is we need more resources.",
    ],
    "what i mean is": [
        "What I mean is we should wait.",
        "What I mean is the approach is wrong.",
        "What I mean is we need to start over.",
        "What I mean is it's not that simple.",
        "What I mean is there's a better way.",
    ],
    "let me": [
        "Let me check on that for you.",
        "Let me think about it.",
        "Let me know if you need help.",
        "Let me explain the situation.",
        "Let me get back to you on that.",
    ],
    "i need to": [
        "I need to finish this report.",
        "I need to talk to you about something.",
        "I need to update the client.",
        "I need to review the numbers.",
        "I need to reschedule our meeting.",
    ],
    "we should": [
        "We should discuss this further.",
        "We should focus on the priorities.",
        "We should consider the alternatives.",
        "We should finalize the plan today.",
        "We should get everyone's input.",
    ],
    "have you ever": [
        "Have you ever tried this approach?",
        "Have you ever been to that conference?",
        "Have you ever worked with this tool?",
        "Have you ever considered changing teams?",
        "Have you ever dealt with this issue?",
    ],
    "i think we should": [
        "I think we should reconsider.",
        "I think we should move forward.",
        "I think we should ask for feedback.",
        "I think we should postpone the launch.",
        "I think we should hire more people.",
    ],
    "not only...but also": [
        "Not only is it fast, but also reliable.",
        "Not only did she agree, but also offered help.",
        "Not only is it cheaper, but also better quality.",
    ],
    "as far as i know": [
        "As far as I know, the deal is still on.",
        "As far as I know, they haven't decided yet.",
        "As far as I know, it's scheduled for Friday.",
    ],
    "in order to": [
        "In order to succeed, we need to plan ahead.",
        "In order to save time, let's skip the intro.",
        "In order to improve, you need consistent practice.",
    ],
}


def generate_phoneme_drills(hard_phonemes, words_per_phoneme=5):
    """Generate word lists for weak phonemes from curated bank.

    Args:
        hard_phonemes: list of phoneme strings (e.g., ["θ", "ɹ"])
        words_per_phoneme: max words to include per phoneme

    Returns:
        list of dicts: [{"phoneme": "θ", "words": ["think", "thank", ...]}]
    """
    drills = []
    for phoneme in hard_phonemes:
        ph_key = phoneme.lower().strip()
        words = PHONEME_WORD_BANK.get(ph_key, [])
        if words:
            drills.append({
                "phoneme": ph_key,
                "words": words[:words_per_phoneme],
            })
    return drills


def generate_word_drills(user_id, limit=10):
    """Select weak words for drilling based on low mastery/score.

    Returns:
        list of dicts: [{"word": "schedule", "avg_score": 42, "attempt_count": 5}]
    """
    weak = get_weak_words(user_id, limit=limit)
    return [{"word": w["word"], "avg_score": w["avg_score"], "attempt_count": w["attempt_count"]} for w in weak]


def generate_pattern_drills(hard_patterns, sentences_per_pattern=3):
    """Generate practice sentences for weak patterns from curated templates.

    Args:
        hard_patterns: list of pattern strings (e.g., ["i'd like to", "could you"])
        sentences_per_pattern: max sentences per pattern

    Returns:
        list of dicts: [{"pattern": "i'd like to", "sentences": [...]}]
    """
    drills = []
    for pattern in hard_patterns:
        pat_key = pattern.lower().strip()
        sentences = PATTERN_SENTENCE_BANK.get(pat_key, [])
        if sentences:
            drills.append({
                "pattern": pat_key,
                "sentences": sentences[:sentences_per_pattern],
            })
    return drills


def generate_daily_practice(user_id, phoneme_limit=3, word_limit=5, pattern_limit=3):
    """Produce a complete daily practice set from learner weaknesses.

    Combines phoneme drills, word drills, and pattern drills into one set.
    No manual selection required — pulls directly from Learning Memory.

    Returns:
        dict with phoneme_drills, word_drills, pattern_drills keys.
    """
    weak_phonemes_raw = get_weak_phonemes(user_id, limit=phoneme_limit)
    hard_phoneme_keys = [p["phoneme"] for p in weak_phonemes_raw]

    weak_patterns_raw = get_weak_patterns(user_id, limit=pattern_limit, min_attempts=1)
    hard_pattern_keys = [p["pattern"] for p in weak_patterns_raw]

    return {
        "phoneme_drills": generate_phoneme_drills(hard_phoneme_keys),
        "word_drills": generate_word_drills(user_id, limit=word_limit),
        "pattern_drills": generate_pattern_drills(hard_pattern_keys),
    }
