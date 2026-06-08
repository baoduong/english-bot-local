import re

_ABBREVIATIONS = frozenset([
    "mr", "mrs", "ms", "dr", "prof", "sr", "jr", "st", "ave", "blvd",
    "vs", "etc", "inc", "ltd", "corp", "dept", "univ", "approx",
    "jan", "feb", "mar", "apr", "jun", "jul", "aug", "sep", "oct", "nov", "dec",
    "fig", "eq", "vol", "no", "pp", "ed", "trans", "rev",
    "u.s", "u.k", "e.g", "i.e", "a.m", "p.m",
])

_SENTENCE_BOUNDARY = re.compile(
    r'(?<=[.!?])'
    r'(?<![A-Z][.])'       # not single uppercase letter + period (initials)
    r'\s+'
)

_ELLIPSIS_PLACEHOLDER = "\x00ELLIPSIS\x00"
_DECIMAL_PLACEHOLDER = "\x00DECIMAL\x00"


def segment_text(text):
    """Split text into sentence segments using rule-based boundaries.

    Handles abbreviations, ellipses, decimal numbers, and newline paragraphs.
    Returns list of non-empty sentence strings.
    """
    if not text or not text.strip():
        return []

    lines = text.strip().split("\n")
    sentences = []

    for line in lines:
        line = line.strip()
        if not line:
            continue
        sentences.extend(_split_line(line))

    return [s for s in sentences if len(s) >= 3]


def _split_line(line):
    line = line.replace("...", _ELLIPSIS_PLACEHOLDER)
    line = re.sub(r'(\d)\.(\d)', r'\1' + _DECIMAL_PLACEHOLDER + r'\2', line)

    for abbr in _ABBREVIATIONS:
        pattern = re.compile(r'\b' + re.escape(abbr) + r'\.', re.IGNORECASE)
        line = pattern.sub(abbr + _ELLIPSIS_PLACEHOLDER, line)

    parts = _SENTENCE_BOUNDARY.split(line)

    results = []
    for part in parts:
        part = part.replace(_ELLIPSIS_PLACEHOLDER, "...").replace(_DECIMAL_PLACEHOLDER, ".")
        part = part.strip()
        if part:
            results.append(part)

    return results
