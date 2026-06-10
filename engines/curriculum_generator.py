import asyncio
from typing import Any

from analysis.curriculum_types import (
    validate_phase_content,
    validate_phase_plan,
    validate_smart_sentence_regen,
)
from db.curriculum import activate_phase, add_phase_content, create_phase
from engines.ollama_client import OllamaClient
from engines.prompts import (
    phase_content_prompt,
    phase_plan_prompt,
    smart_sentence_regen_prompt,
)


class CurriculumGenerator:
    def __init__(self, ollama_client: OllamaClient):
        self.ollama_client = ollama_client

    def generate_phase_plan(
        self,
        goal_title,
        goal_description,
        phase_number,
        previous_phases,
        performance_summary,
    ) -> dict[str, Any]:
        prompt = phase_plan_prompt(
            goal_title,
            goal_description,
            phase_number,
            previous_phases,
            performance_summary,
        )
        return self.ollama_client.generate_json_sync(prompt, validate_phase_plan)

    def generate_phase_content(self, phase_plan, sentence_count: int = 12) -> list[dict[str, Any]]:
        prompt = phase_content_prompt(phase_plan, sentence_count)
        response = self.ollama_client.generate_json_sync(prompt, validate_phase_content)
        return response["sentences"]

    def generate_full_phase(
        self,
        curriculum_id,
        goal_title,
        goal_description,
        phase_number,
        previous_phases,
        performance_summary: str = "",
    ) -> tuple[int, list[int]]:
        plan = self.generate_phase_plan(
            goal_title,
            goal_description,
            phase_number,
            previous_phases,
            performance_summary,
        )

        phase_id = create_phase(
            curriculum_id,
            phase_number,
            plan["theme"],
            plan["vocabulary"],
            plan["milestones"],
        )

        content_items = self.generate_phase_content(plan, plan.get("sentence_count_target", 12))
        add_phase_content(phase_id, content_items)
        activate_phase(phase_id)

        return phase_id, []

    def generate_replacement_sentence(self, target_phonemes, difficulty, theme, failed_sentences) -> dict[str, Any]:
        prompt = smart_sentence_regen_prompt(target_phonemes, difficulty, theme, failed_sentences)
        return self.ollama_client.generate_json_sync(prompt, validate_smart_sentence_regen)

    async def generate_phase_plan_async(
        self,
        goal_title,
        goal_description,
        phase_number,
        previous_phases,
        performance_summary,
    ) -> dict[str, Any]:
        return await asyncio.to_thread(
            self.generate_phase_plan,
            goal_title,
            goal_description,
            phase_number,
            previous_phases,
            performance_summary,
        )

    async def generate_phase_content_async(
        self,
        phase_plan,
        sentence_count: int = 12,
    ) -> list[dict[str, Any]]:
        return await asyncio.to_thread(self.generate_phase_content, phase_plan, sentence_count)

    async def generate_full_phase_async(
        self,
        curriculum_id,
        goal_title,
        goal_description,
        phase_number,
        previous_phases,
        performance_summary: str = "",
    ) -> tuple[int, list[int]]:
        return await asyncio.to_thread(
            self.generate_full_phase,
            curriculum_id,
            goal_title,
            goal_description,
            phase_number,
            previous_phases,
            performance_summary,
        )

    async def generate_replacement_sentence_async(
        self,
        target_phonemes,
        difficulty,
        theme,
        failed_sentences,
    ):
        return await asyncio.to_thread(
            self.generate_replacement_sentence,
            target_phonemes,
            difficulty,
            theme,
            failed_sentences,
        )
