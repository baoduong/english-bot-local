from __future__ import annotations

from typing import Any

from analysis.errors import get_target_ipa
from analysis.phonemes import clean_word


def _phonemes_to_list(ipa_string: str) -> list[str]:
    return [p for p in ipa_string.strip().split() if p]


def _strip_ipa_brackets(value: str | None) -> str:
    if not value:
        return ""
    return value.strip("/ ").replace(" ", "")


def _split_ipa_into_phonemes(joined: str) -> list[str]:
    multichar = ["tʃ", "dʒ", "eɪ", "aɪ", "ɔɪ", "oʊ", "aʊ", "uː", "iː", "ɔː", "ɑː", "ɜː"]
    result: list[str] = []
    index = 0
    while index < len(joined):
        matched = False
        for token in multichar:
            if joined[index:index + len(token)] == token:
                result.append(token)
                index += len(token)
                matched = True
                break
        if not matched:
            result.append(joined[index])
            index += 1
    return result


def _lcs_length(left: list[str], right: list[str]) -> int:
    if not left or not right:
        return 0
    dp = [[0] * (len(right) + 1) for _ in range(len(left) + 1)]
    for i in range(1, len(left) + 1):
        for j in range(1, len(right) + 1):
            if left[i - 1] == right[j - 1]:
                dp[i][j] = dp[i - 1][j - 1] + 1
            else:
                dp[i][j] = max(dp[i - 1][j], dp[i][j - 1])
    return dp[-1][-1]


def analyze_phonemes_per_word(audio_path: str, expected_text: str) -> dict[str, dict[str, Any]]:
    from engines.phoneme_recognizer import get_phoneme_recognizer

    detected_ipa = get_phoneme_recognizer().recognize(audio_path)
    return align_phonemes_per_word(expected_text, detected_ipa)


def align_phonemes_per_word(expected_text: str, detected_ipa: str) -> dict[str, dict[str, Any]]:
    words = expected_text.split()
    if not words:
        return {}

    expected_per_word: list[list[str]] = []
    for word in words:
        ipa_raw = get_target_ipa(clean_word(word)) or ""
        expected_per_word.append(_split_ipa_into_phonemes(_strip_ipa_brackets(ipa_raw)))

    detected = _phonemes_to_list(detected_ipa)
    total_expected_len = sum(len(phonemes) for phonemes in expected_per_word) or 1
    result: dict[str, dict[str, Any]] = {}
    cursor = 0

    for index, (word, expected_phonemes) in enumerate(zip(words, expected_per_word)):
        key = clean_word(word)
        if not expected_phonemes:
            result[key] = {
                "detected_ipa": "",
                "expected_ipa": "",
                "phoneme_match_ratio": 0.0,
                "missing_phonemes": [],
                "extra_phonemes": [],
            }
            continue

        remaining_words = len(words) - index
        remaining_detected = max(0, len(detected) - cursor)
        if remaining_words == 1:
            slice_phonemes = detected[cursor:]
            cursor = len(detected)
        else:
            share = max(1, round(len(detected) * len(expected_phonemes) / total_expected_len))
            share = min(share, remaining_detected)
            slice_phonemes = detected[cursor:cursor + share]
            cursor += share

        lcs = _lcs_length(expected_phonemes, slice_phonemes)
        missing = [phoneme for phoneme in expected_phonemes if phoneme not in slice_phonemes]
        extra = [phoneme for phoneme in slice_phonemes if phoneme not in expected_phonemes]

        result[key] = {
            "detected_ipa": f"/{''.join(slice_phonemes)}/" if slice_phonemes else "",
            "expected_ipa": f"/{''.join(expected_phonemes)}/",
            "phoneme_match_ratio": round(lcs / max(len(expected_phonemes), 1), 2),
            "missing_phonemes": missing,
            "extra_phonemes": extra,
        }

    return result
