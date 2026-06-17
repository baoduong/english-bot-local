"""
Dependency injection for the iPhone Gateway API.

Singletons are instantiated once at module load (mirrors app.py lines 66-69).
FastAPI Depends() functions expose them to router handlers.
"""
from __future__ import annotations

from engines.ollama_client import OllamaClient
from engines.curriculum_generator import CurriculumGenerator
from engines.onboarding_chat import OnboardingChat
from analysis.phase_engine import PhaseEngine

# ─── Module-level singletons ─────────────────────────────────────────────────
# Same construction order as app.py: ollama → generator → onboarding → phase

_ollama_client: OllamaClient = OllamaClient()
_curriculum_generator: CurriculumGenerator = CurriculumGenerator(_ollama_client)
_onboarding_chat: OnboardingChat = OnboardingChat(_ollama_client)
_phase_engine: PhaseEngine = PhaseEngine(_ollama_client, _curriculum_generator)


# ─── DI provider functions ───────────────────────────────────────────────────

def get_ollama_client() -> OllamaClient:
    """Return the shared OllamaClient singleton."""
    return _ollama_client


def get_curriculum_generator() -> CurriculumGenerator:
    """Return the shared CurriculumGenerator singleton."""
    return _curriculum_generator


def get_onboarding_chat() -> OnboardingChat:
    """Return the shared OnboardingChat singleton."""
    return _onboarding_chat


def get_phase_engine() -> PhaseEngine:
    """Return the shared PhaseEngine singleton."""
    return _phase_engine
