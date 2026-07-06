"""
Regression test: /onboarding/confirm response shape must be decodable by iOS Codable.

Root cause of original bug: CurriculumPhase.vocabulary was typed as [String]? in iOS
but the backend sends [VocabularyItem] objects with {word, ipa, vietnamese_gloss,
example_sentence}. This caused a Swift Codable typeMismatch decode error.
"""
from __future__ import annotations


import pytest
from httpx import AsyncClient

from db.curriculum import add_onboarding_turn
from db.users import get_or_create_user


def _seed_onboarding_user(user_id: str) -> None:
    get_or_create_user(user_id, user_id)
    add_onboarding_turn(user_id, 1, "user", "Xin chào! Mình muốn học phát âm tiếng Anh.")
    add_onboarding_turn(user_id, 2, "assistant", "Bạn muốn học phát âm trong ngữ cảnh nào?")
    add_onboarding_turn(user_id, 3, "user", "Mình hay họp với đồng nghiệp nước ngoài.")
    add_onboarding_turn(user_id, 4, "assistant", "Bạn thường gặp khó khăn với từ nào nhất?")
    add_onboarding_turn(user_id, 5, "user", "Các từ kỹ thuật và trình bày tiến độ.")


@pytest.mark.anyio
async def test_confirm_response_json_shape(
    client: AsyncClient,
    clean_db: str,
    mock_ollama,
) -> None:
    user_id = "test-confirm-shape-01"
    _seed_onboarding_user(user_id)

    mock_ollama.set_next_response("onboarding_synthesize")
    mock_ollama.set_next_response("phase_plan_basic")
    mock_ollama.set_next_response("phase_plan_basic")

    resp = await client.post(
        "/onboarding/confirm",
        json={"user_id": user_id, "confirmed": True},
    )
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"

    body = resp.json()

    assert body["status"] == "confirmed"
    assert body.get("curriculum") is not None, "curriculum must be present on confirmed response"
    assert body.get("phase") is not None, "phase must be present on confirmed response"

    phase = body["phase"]
    assert "phase_id" in phase
    assert "phase_number" in phase
    assert "theme" in phase
    assert "status" in phase

    vocabulary = phase.get("vocabulary")
    if vocabulary:
        for item in vocabulary:
            assert isinstance(item, dict), (
                f"vocabulary items must be objects (VocabularyItem), got {type(item)}: {item!r}. "
                "iOS Codable expects [VocabularyItem] not [String]."
            )
            assert "word" in item, f"VocabularyItem missing 'word': {item}"
            assert "ipa" in item, f"VocabularyItem missing 'ipa': {item}"
            assert "vietnamese_gloss" in item, f"VocabularyItem missing 'vietnamese_gloss': {item}"
            assert "example_sentence" in item, f"VocabularyItem missing 'example_sentence': {item}"

    milestones = phase.get("milestones")
    if milestones:
        for m in milestones:
            assert isinstance(m, dict), f"milestone must be object, got {type(m)}: {m!r}"
            assert "description" in m
            assert "criteria" in m

    from api.models import OnboardingConfirmResponse
    OnboardingConfirmResponse(**body)


@pytest.mark.anyio
async def test_confirm_rejected_response_shape(
    client: AsyncClient,
    clean_db: str,
    mock_ollama,
) -> None:
    user_id = "test-confirm-reject-01"
    _seed_onboarding_user(user_id)

    mock_ollama.set_next_response("onboarding_synthesize")

    resp = await client.post(
        "/onboarding/confirm",
        json={"user_id": user_id, "confirmed": False},
    )
    assert resp.status_code == 200

    body = resp.json()
    assert body["status"] == "rejected"
    assert body.get("curriculum") is None
    assert body.get("phase") is None

    from api.models import OnboardingConfirmResponse
    OnboardingConfirmResponse(**body)
