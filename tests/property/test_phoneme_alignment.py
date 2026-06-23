from __future__ import annotations

from typing import Any

import pytest
from hypothesis import given, settings, strategies as st

from engines import phoneme_alignment
from analysis.errors import get_target_ipa
from analysis.phonemes import clean_word


PHONEME = st.sampled_from([
    "a",
    "e",
    "i",
    "o",
    "u",
    "θ",
    "ʃ",
    "ŋ",
    "k",
    "s",
    "t",
    "f",
    "ɪ",
    "tʃ",
    "dʒ",
])
WORD = st.text(min_size=1, max_size=8, alphabet=st.characters(min_codepoint=97, max_codepoint=122))


def _expected_phonemes_for_words(words: list[str]) -> dict[str, list[str]]:
    mapping: dict[str, list[str]] = {}
    for word in words:
        cleaned = clean_word(word)
        ipa_raw = get_target_ipa(cleaned) or ""
        mapping[cleaned] = phoneme_alignment._split_ipa_into_phonemes(
            phoneme_alignment._strip_ipa_brackets(ipa_raw)
        )
    return mapping


@pytest.mark.slow
@settings(max_examples=80)
@given(detected=st.lists(PHONEME, min_size=0, max_size=30), words=st.lists(WORD, min_size=1, max_size=8))
def test_alignment_returns_one_entry_per_cleaned_word(detected: list[str], words: list[str]) -> None:
    expected_text = " ".join(words)
    result = phoneme_alignment.align_phonemes_per_word(expected_text, " ".join(detected))
    assert set(result.keys()) == {clean_word(word) for word in words}


@pytest.mark.slow
@settings(max_examples=80)
@given(detected=st.lists(PHONEME, min_size=0, max_size=30), words=st.lists(WORD, min_size=1, max_size=8))
def test_alignment_never_assigns_more_detected_phonemes_than_provided(detected: list[str], words: list[str]) -> None:
    expected_text = " ".join(words)
    result = phoneme_alignment.align_phonemes_per_word(expected_text, " ".join(detected))
    assigned = 0
    for data in result.values():
        typed_data = dict[str, Any](data)
        detected_ipa = str(typed_data["detected_ipa"])
        assigned += len(phoneme_alignment._split_ipa_into_phonemes(phoneme_alignment._strip_ipa_brackets(detected_ipa)))
    assert assigned <= len(detected)


@pytest.mark.slow
@settings(max_examples=80)
@given(detected=st.lists(PHONEME, min_size=0, max_size=30), words=st.lists(WORD, min_size=1, max_size=8))
def test_alignment_output_is_structurally_consistent_with_expected_ipa(detected: list[str], words: list[str]) -> None:
    expected_text = " ".join(words)
    result = phoneme_alignment.align_phonemes_per_word(expected_text, " ".join(detected))
    expected_mapping = _expected_phonemes_for_words(words)

    for word in words:
        key = clean_word(word)
        data = result[key]
        expected_phonemes = expected_mapping[key]
        expected_ipa = f"/{''.join(expected_phonemes)}/" if expected_phonemes else ""
        typed_data = dict[str, Any](data)
        assert typed_data["expected_ipa"] == expected_ipa
        assert 0.0 <= float(typed_data["phoneme_match_ratio"]) <= 1.0
        assert isinstance(typed_data["missing_phonemes"], list)
        assert isinstance(typed_data["extra_phonemes"], list)
        for missing in typed_data["missing_phonemes"]:
            assert missing in expected_phonemes
