from __future__ import annotations

import pytest
from hypothesis import given, settings, strategies as st


def _whisper_overall_score(word_points: list[float]) -> int:
    if not word_points:
        return 0
    return max(0, min(100, int((sum(word_points) / len(word_points)) * 100)))


WHISPER_POINTS = st.sampled_from([0.0, 0.1, 0.5, 0.6, 1.0])


@pytest.mark.slow
@settings(max_examples=100)
@given(word_points=st.lists(WHISPER_POINTS, min_size=1, max_size=20))
def test_whisper_overall_score_stays_within_bounds(word_points: list[float]) -> None:
    overall = _whisper_overall_score(word_points)
    assert 0 <= overall <= 100


@pytest.mark.slow
@settings(max_examples=100)
@given(word_points=st.lists(WHISPER_POINTS, min_size=1, max_size=20))
def test_whisper_overall_score_is_monotonic_under_per_word_improvement(word_points: list[float]) -> None:
    improved = [min(1.0, point + 0.1) for point in word_points]
    assert _whisper_overall_score(improved) >= _whisper_overall_score(word_points)


@pytest.mark.slow
@settings(max_examples=100)
@given(word_points=st.lists(WHISPER_POINTS, min_size=1, max_size=20))
def test_whisper_overall_score_matches_integer_average_of_word_points(word_points: list[float]) -> None:
    expected = int(sum(word_points) / len(word_points) * 100)
    assert _whisper_overall_score(word_points) == expected
