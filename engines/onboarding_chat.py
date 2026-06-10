import json
import re
import asyncio

from engines.ollama_client import OllamaClient
from engines.prompts import onboarding_system_prompt, onboarding_synthesis_prompt, MAX_ONBOARDING_TURNS
from analysis.curriculum_types import validate_goal_synthesis
from db.curriculum import (add_onboarding_turn, get_onboarding_conversation,
                           clear_onboarding_conversation, count_onboarding_turns,
                           create_curriculum)
from db.users import mark_onboarding_complete


class OnboardingChat:
    def __init__(self, ollama_client: OllamaClient):
        self.ollama_client = ollama_client

    def start_conversation(self, user_id, interface_language='vi') -> str:
        clear_onboarding_conversation(user_id)

        opening_user_text = "Xin chào! Mình muốn bắt đầu học phát âm tiếng Anh."
        messages = [
            {
                "role": "system",
                "content": onboarding_system_prompt(interface_language),
            },
            {
                "role": "user",
                "content": opening_user_text,
            },
        ]

        ai_greeting = self.ollama_client.chat_sync(messages)

        add_onboarding_turn(user_id, 1, "user", opening_user_text)
        add_onboarding_turn(user_id, 2, "assistant", ai_greeting)

        return ai_greeting

    def submit_user_reply(self, user_id, user_text) -> dict:
        turn_count = count_onboarding_turns(user_id)
        add_onboarding_turn(user_id, turn_count + 1, "user", user_text)

        history = get_onboarding_conversation(user_id)
        user_turn_count = sum(1 for turn in history if turn.get("role") == "user")
        if user_turn_count >= MAX_ONBOARDING_TURNS:
            goal = self.synthesize_goal(user_id)
            return {
                "type": "synthesis",
                "goal": goal,
                "turn_number": turn_count + 1,
            }

        messages = [{"role": "system", "content": onboarding_system_prompt("vi")}]
        messages.extend(
            {
                "role": turn["role"],
                "content": turn["content"],
            }
            for turn in history
        )

        ai_response = self.ollama_client.chat_sync(messages)
        add_onboarding_turn(user_id, turn_count + 2, "assistant", ai_response)

        matched = re.search(r'\{[^{}]*"goal_title"[^{}]*\}', ai_response)
        if matched:
            try:
                parsed_goal = json.loads(matched.group(0))
                validate_goal_synthesis(parsed_goal)
                return {
                    "type": "synthesis",
                    "goal": parsed_goal,
                    "turn_number": turn_count + 2,
                }
            except (json.JSONDecodeError, ValueError, TypeError):
                pass

        return {
            "type": "question",
            "text": ai_response,
            "turn_number": turn_count + 2,
        }

    def synthesize_goal(self, user_id) -> dict:
        history = get_onboarding_conversation(user_id)
        history_for_prompt = [
            {
                "turn_number": turn.get("turn_number"),
                "role": turn.get("role"),
                "content": turn.get("content"),
            }
            for turn in history
        ]

        prompt = onboarding_synthesis_prompt(history_for_prompt)
        goal = self.ollama_client.generate_json_sync(prompt, validate_goal_synthesis)
        return goal

    def confirm_and_create_curriculum(self, user_id, goal_synthesis, interface_language='vi') -> int:
        curriculum_id = create_curriculum(
            user_id,
            goal_synthesis['goal_title'],
            goal_synthesis.get('goal_description', ''),
            interface_language,
        )
        mark_onboarding_complete(user_id, curriculum_id)
        clear_onboarding_conversation(user_id)
        return curriculum_id

    async def start_conversation_async(self, user_id, interface_language='vi') -> str:
        return await asyncio.to_thread(self.start_conversation, user_id, interface_language)

    async def submit_user_reply_async(self, user_id, user_text) -> dict:
        return await asyncio.to_thread(self.submit_user_reply, user_id, user_text)

    async def synthesize_goal_async(self, user_id) -> dict:
        return await asyncio.to_thread(self.synthesize_goal, user_id)

    async def confirm_and_create_curriculum_async(self, user_id, goal_synthesis, interface_language='vi') -> int:
        return await asyncio.to_thread(
            self.confirm_and_create_curriculum,
            user_id,
            goal_synthesis,
            interface_language,
        )
