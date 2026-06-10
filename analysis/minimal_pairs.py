MINIMAL_PAIRS = {
    "θ": [
        ("think", "sink"), ("three", "tree"), ("math", "mass"),
        ("thick", "sick"), ("thing", "sing"), ("path", "pass"),
        ("thank", "sank"), ("thought", "sort"), ("thin", "sin"),
        ("both", "boss"),
    ],
    "ɹ": [
        ("right", "light"), ("read", "lead"), ("rice", "lice"),
        ("wrong", "long"), ("rain", "lane"), ("row", "low"),
        ("rock", "lock"), ("red", "led"), ("rip", "lip"),
        ("rate", "late"),
    ],
    "ʃ": [
        ("ship", "sip"), ("she", "see"), ("shop", "sop"),
        ("shin", "sin"), ("shack", "sack"), ("shoe", "sue"),
        ("share", "sare"), ("sheep", "seep"), ("shy", "sigh"),
        ("show", "so"),
    ],
    "C#": [
        ("cats", "cat"), ("dogs", "dog"), ("maps", "map"),
        ("sits", "sit"), ("beds", "bed"), ("cups", "cup"),
        ("hands", "hand"), ("asks", "ask"), ("helps", "help"),
        ("works", "work"),
    ],
    "V": [
        ("ship", "sheep"), ("bit", "beat"), ("full", "fool"),
        ("pull", "pool"), ("sit", "seat"), ("hit", "heat"),
        ("live", "leave"), ("fill", "feel"), ("rich", "reach"),
        ("still", "steal"),
    ],
}


def get_minimal_pairs_for_phoneme(phoneme: str, count: int = 5):
    pairs = MINIMAL_PAIRS.get(phoneme, [])
    return pairs[:count]


def get_phoneme_display_name(phoneme: str):
    names = {
        "θ": "th (/θ/)",
        "ɹ": "r vs l",
        "ʃ": "sh (/ʃ/)",
        "C#": "final consonants",
        "V": "vowel length",
    }
    return names.get(phoneme, phoneme)
