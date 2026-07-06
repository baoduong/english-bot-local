import pytest
from analysis.curriculum_types import validate_phase_content, validate_smart_sentence_regen


def test_sentence_with_ellipsis_rejected():
    bad_response = {
        "sentences": [
            {
                "sentence": "I want ... introduce myself",
                "target_phonemes": ["/w/"],
                "target_words": ["want"],
                "difficulty_score": 2
            },
            {
                "sentence": "Good morning everyone",
                "target_phonemes": ["/g/"],
                "target_words": ["good"],
                "difficulty_score": 1
            },
            {
                "sentence": "How are you today",
                "target_phonemes": ["/h/"],
                "target_words": ["how"],
                "difficulty_score": 1
            },
            {
                "sentence": "Thank you so much",
                "target_phonemes": ["/θ/"],
                "target_words": ["thank"],
                "difficulty_score": 2
            },
            {
                "sentence": "Have a nice day",
                "target_phonemes": ["/h/"],
                "target_words": ["have"],
                "difficulty_score": 1
            }
        ]
    }
    with pytest.raises(ValueError, match="ellipsis"):
        validate_phase_content(bad_response)


def test_sentence_with_blank_marker_rejected():
    bad_response = {
        "sentences": [
            {
                "sentence": "I want ___ introduce myself",
                "target_phonemes": ["/w/"],
                "target_words": ["want"],
                "difficulty_score": 2
            },
            {
                "sentence": "Good morning everyone",
                "target_phonemes": ["/g/"],
                "target_words": ["good"],
                "difficulty_score": 1
            },
            {
                "sentence": "How are you today",
                "target_phonemes": ["/h/"],
                "target_words": ["how"],
                "difficulty_score": 1
            },
            {
                "sentence": "Thank you so much",
                "target_phonemes": ["/θ/"],
                "target_words": ["thank"],
                "difficulty_score": 2
            },
            {
                "sentence": "Have a nice day",
                "target_phonemes": ["/h/"],
                "target_words": ["have"],
                "difficulty_score": 1
            }
        ]
    }
    with pytest.raises(ValueError, match="blank marker"):
        validate_phase_content(bad_response)


def test_valid_sentence_accepted():
    good_response = {
        "sentences": [
            {
                "sentence": "I want to introduce myself.",
                "target_phonemes": ["/w/", "/t/"],
                "target_words": ["want", "introduce"],
                "difficulty_score": 2
            },
            {
                "sentence": "Good morning everyone.",
                "target_phonemes": ["/g/"],
                "target_words": ["good"],
                "difficulty_score": 1
            },
            {
                "sentence": "How are you today?",
                "target_phonemes": ["/h/"],
                "target_words": ["how"],
                "difficulty_score": 1
            },
            {
                "sentence": "Thank you so much.",
                "target_phonemes": ["/θ/"],
                "target_words": ["thank"],
                "difficulty_score": 2
            },
            {
                "sentence": "Have a nice day.",
                "target_phonemes": ["/h/"],
                "target_words": ["have"],
                "difficulty_score": 1
            }
        ]
    }
    validate_phase_content(good_response)


def test_smart_sentence_regen_with_ellipsis_rejected():
    bad_regen = {
        "sentence": "The meeting ... at 3 PM",
        "target_phonemes": ["/m/"],
        "target_words": ["meeting"],
        "difficulty_score": 2
    }
    with pytest.raises(ValueError, match="ellipsis"):
        validate_smart_sentence_regen(bad_regen)


def test_smart_sentence_regen_with_blank_rejected():
    bad_regen = {
        "sentence": "The meeting [BLANK] at 3 PM",
        "target_phonemes": ["/m/"],
        "target_words": ["meeting"],
        "difficulty_score": 2
    }
    with pytest.raises(ValueError, match="blank marker"):
        validate_smart_sentence_regen(bad_regen)


def test_smart_sentence_regen_valid_accepted():
    good_regen = {
        "sentence": "The meeting starts at 3 PM.",
        "target_phonemes": ["/m/", "/s/"],
        "target_words": ["meeting", "starts"],
        "difficulty_score": 2
    }
    validate_smart_sentence_regen(good_regen)

