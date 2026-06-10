# pyright: reportUnknownVariableType=false, reportUnknownParameterType=false, reportMissingTypeArgument=false, reportUnannotatedClassAttribute=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportExplicitAny=false, reportAny=false
# ─────────────────────────────────────────────
# Phase Progression Engine
#
# REGENERATION CAP: Maximum 2 regenerations per phase slot.
# After 2 regenerations, force-advance to next phase.
# Enforced in BOTH evaluate_phase (prevents AI from requesting regen)
# and apply_decision (defense-in-depth if evaluate_phase is bypassed).
# Decision #11 from user interview: "No phase regeneration > 2 times"
# ─────────────────────────────────────────────
import asyncio
from typing import Any

from engines.ollama_client import OllamaClient
from engines.curriculum_generator import CurriculumGenerator
from engines.prompts import progression_decision_prompt
from analysis.curriculum_types import validate_progression_decision
from db.curriculum import (
    get_phase,
    get_phase_progress,
    get_phase_regeneration_count,
    complete_phase,
    mark_phase_regenerated,
    activate_phase,
    increment_phase_number,
    get_phases_for_curriculum,
    get_curriculum,
)


def _log_decision_override(original_action: str, forced_action: str, reason: str, context: dict) -> None:
    """Log when AI decision is overridden by code-level guard."""
    print(f"[phase_engine] Override: {original_action} → {forced_action}. Reason: {reason}. Context: {context}")


class PhaseEngine:
    def __init__(self, ollama_client: OllamaClient, curriculum_generator: CurriculumGenerator):
        self.ollama_client: OllamaClient = ollama_client
        self.curriculum_generator: CurriculumGenerator = curriculum_generator

    def evaluate_phase(self, phase_id: int) -> dict[str, Any]:
        phase = get_phase(phase_id)
        if not phase:
            raise ValueError(f"Phase not found: {phase_id}")

        progress = get_phase_progress(phase_id)
        regen_count = get_phase_regeneration_count(
            phase["curriculum_id"],
            phase["phase_number"],
        )

        performance_data = {
            "completion_pct": round(progress["mastered"] / progress["total"] * 100, 1)
            if progress["total"] > 0
            else 0,
            "avg_score": progress["avg_score"],
            "mastered_count": progress["mastered"],
            "struggling_words": progress["struggling_words"],
            "regeneration_count": regen_count,
        }

        if regen_count >= 2:
            _log_decision_override(
                "ai_decision", "advance",
                "regeneration cap reached (2 regenerations)",
                {"phase_id": phase_id, "regen_count": regen_count},
            )
            return {
                "action": "advance",
                "reasoning": "Force-advance: regeneration cap reached (2 regenerations)",
                "confidence": 1.0,
            }

        prompt = progression_decision_prompt(phase, performance_data)
        decision = self.ollama_client.generate_json_sync(prompt, validate_progression_decision)
        return decision

    async def evaluate_phase_async(self, phase_id: int) -> dict[str, Any]:
        return await asyncio.to_thread(self.evaluate_phase, phase_id)

    def apply_decision(self, phase_id: int, decision: dict[str, Any]) -> dict[str, Any]:
        action = decision["action"]

        if action == "advance":
            complete_phase(phase_id)
            phase = get_phase(phase_id)
            if not phase:
                raise ValueError(f"Phase not found after completion: {phase_id}")

            new_phase_num = increment_phase_number(phase["curriculum_id"])
            return {
                "next_action": "generate_next_phase",
                "curriculum_id": phase["curriculum_id"],
                "next_phase_number": new_phase_num,
            }

        if action == "repeat":
            return {
                "next_action": "continue",
                "phase_id": phase_id,
            }

        if action == "regenerate":
            phase = get_phase(phase_id)
            if not phase:
                raise ValueError(f"Phase not found: {phase_id}")

            # Defense-in-depth: check regen cap even if evaluate_phase missed it
            regen_count = get_phase_regeneration_count(phase["curriculum_id"], phase["phase_number"])
            if regen_count >= 2:
                _log_decision_override(
                    "regenerate", "advance",
                    "apply_decision regen cap defense-in-depth",
                    {"phase_id": phase_id, "regen_count": regen_count},
                )
                complete_phase(phase_id)
                new_phase_num = increment_phase_number(phase["curriculum_id"])
                return {
                    "next_action": "generate_next_phase",
                    "curriculum_id": phase["curriculum_id"],
                    "next_phase_number": new_phase_num,
                }

            mark_phase_regenerated(phase_id)

            curriculum = get_curriculum(phase["curriculum_id"])
            if not curriculum:
                raise ValueError(f"Curriculum not found: {phase['curriculum_id']}")

            previous_phases = get_phases_for_curriculum(phase["curriculum_id"])
            new_phase_id, _ = self.curriculum_generator.generate_full_phase(
                phase["curriculum_id"],
                curriculum["goal_title"],
                curriculum["goal_description"],
                phase["phase_number"],
                previous_phases,
                "Phase regenerated due to low performance",
            )
            activate_phase(new_phase_id)

            return {
                "next_action": "phase_regenerated",
                "new_phase_id": new_phase_id,
            }

        raise ValueError(f"Invalid progression action: {action}")

    async def apply_decision_async(self, phase_id: int, decision: dict[str, Any]) -> dict[str, Any]:
        return await asyncio.to_thread(self.apply_decision, phase_id, decision)

    def should_check_progression(self, phase_id: int) -> bool:
        progress = get_phase_progress(phase_id)
        if progress["total"] == 0:
            return False

        return (progress["attempted"] / progress["total"]) >= 0.5
