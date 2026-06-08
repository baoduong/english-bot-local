KNOWN_PATTERNS = [
    "i'd like to",
    "i would like to",
    "could you",
    "would you mind",
    "would you",
    "can you",
    "may i",
    "could i",
    "i'm going to",
    "i'm planning to",
    "i want to",
    "i need to",
    "i have to",
    "i think",
    "i believe",
    "in my opinion",
    "it seems like",
    "i feel like",
    "have you ever",
    "do you think",
    "how do you",
    "what do you think",
    "can you tell me",
    "you should",
    "we should",
    "we need to",
    "let's",
    "why don't we",
    "how about",
    "i've been",
    "i haven't",
    "i used to",
    "i've never",
    "please let me know",
    "i appreciate",
    "thank you for",
    "i'm looking forward to",
    "i was wondering",
    "would it be possible",
    "i'm looking for",
    "there is",
    "there are",
    "it's important to",
    "the problem is",
    "the reason is",
    "let me",
    "allow me to",
    "i'm sorry",
    "excuse me",
]

_SORTED_PATTERNS = sorted(KNOWN_PATTERNS, key=len, reverse=True)


def extract_patterns(sentence):
    """Match sentence against known speaking patterns. Returns list of matched pattern strings."""
    lower = sentence.lower().strip()
    matched = []
    for pattern in _SORTED_PATTERNS:
        if lower.startswith(pattern) or f" {pattern}" in f" {lower}":
            matched.append(pattern)
    return matched
