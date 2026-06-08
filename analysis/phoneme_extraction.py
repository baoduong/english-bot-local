import re

_WORD_PATTERN = re.compile(r"[a-zA-Z']+")

PHONEME_WORD_MAP = {
    "θ": {"think", "thank", "thin", "three", "thirty", "thought", "through", "thumb", "therapy", "thunder",
           "thirst", "theory", "theme", "thick", "thousand", "third", "threat", "throw", "thrust", "thaw"},
    "ð": {"the", "this", "that", "there", "these", "those", "them", "then", "other", "weather",
           "father", "mother", "brother", "whether", "together", "another", "rather", "either", "neither", "smooth"},
    "ɹ": {"run", "right", "read", "river", "really", "around", "correct", "program", "road", "rain",
           "room", "reach", "require", "result", "return", "report", "reason", "remain", "role", "rule"},
    "l": {"live", "light", "learn", "little", "level", "listen", "total", "follow", "table", "pull",
           "large", "local", "long", "lead", "leave", "likely", "late", "letter", "list", "land"},
    "ʃ": {"she", "ship", "show", "should", "share", "shake", "shelter", "sure", "nation", "special",
           "social", "official", "machine", "ocean", "pressure", "fashion", "cashier", "condition", "station", "mention"},
    "ʒ": {"measure", "pleasure", "vision", "decision", "usual", "casual", "garage", "massage", "beige", "rouge",
           "treasure", "leisure", "exposure", "closure", "revision", "television", "occasion", "illusion", "confusion", "fusion"},
    "tʃ": {"church", "chance", "change", "charge", "chapter", "challenge", "achieve", "match", "catch", "watch",
            "choose", "check", "cheap", "chain", "chart", "chief", "child", "choice", "pitch", "teach"},
    "dʒ": {"just", "job", "join", "judge", "journey", "gentle", "huge", "bridge", "edge", "age",
            "project", "major", "manage", "message", "budget", "college", "package", "knowledge", "damage", "village"},
    "ŋ": {"sing", "thing", "ring", "bring", "long", "wrong", "young", "strong", "among", "along",
           "king", "morning", "evening", "nothing", "something", "anything", "running", "building", "working", "during"},
    "v": {"very", "voice", "value", "visit", "view", "never", "over", "have", "give", "save",
           "every", "even", "move", "leave", "live", "love", "above", "available", "however", "environment"},
    "w": {"well", "work", "want", "week", "would", "away", "always", "between", "power", "twelve",
           "world", "water", "way", "wait", "walk", "watch", "while", "where", "wide", "wonder"},
    "z": {"zero", "zone", "zip", "zoo", "zeal", "buzz", "jazz", "fizz", "was", "because",
           "his", "these", "those", "easy", "reason", "music", "always", "business", "please", "result"},
    "f": {"find", "first", "four", "feel", "fast", "phone", "enough", "offer", "staff", "proof",
           "fact", "family", "follow", "food", "force", "form", "free", "friend", "front", "full"},
    "s": {"see", "say", "side", "some", "start", "center", "science", "since", "space", "source",
           "city", "place", "face", "policy", "service", "process", "society", "sentence", "surface", "system"},
    "C#": {"hand", "stand", "just", "fast", "next", "project", "product", "impact", "accept", "suggest",
            "kept", "fact", "act", "expect", "aspect", "effect", "object", "subject", "conflict", "connect"},
    "V": {"about", "important", "develop", "consider", "determine", "photograph", "economy", "category",
           "particular", "opportunity", "community", "ability", "technology", "university", "authority", "activity"},
}


def extract_target_phonemes(text):
    words = set(w.lower() for w in _WORD_PATTERN.findall(text))
    found_phonemes = []

    for phoneme, word_set in PHONEME_WORD_MAP.items():
        if words & word_set:
            found_phonemes.append(phoneme)

    return sorted(found_phonemes)
