from typing import TypedDict, Optional, List
from enum import Enum

# --- Enums ---

class CurriculumStatus(Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    ARCHIVED = "archived"

class PhaseStatus(Enum):
    PENDING = "pending"
    ACTIVE = "active"
    COMPLETED = "completed"
    REGENERATED = "regenerated"

# --- TypedDicts ---

class OnboardingTurn(TypedDict):
    turn_number: int
    role: str
    content: str

class GoalSynthesis(TypedDict):
    goal_title: str
    goal_description: str
    suggested_phase_count: Optional[int]
    key_themes: List[str]

class PhaseVocabulary(TypedDict):
    word: str
    ipa: str
    vietnamese_gloss: str
    example_sentence: str

class PhaseMilestone(TypedDict):
    description: str
    criteria: str

class PhasePlan(TypedDict):
    phase_number: int
    theme: str
    vocabulary: List[PhaseVocabulary]
    milestones: List[PhaseMilestone]
    sentence_count_target: int

class PhaseContentItem(TypedDict):
    sentence: str
    target_phonemes: List[str]
    target_words: List[str]
    difficulty_score: int

class ProgressionDecision(TypedDict):
    action: str
    reasoning: str
    confidence: float

# --- Validators ---

def validate_goal_synthesis(data: dict) -> None:
    if not isinstance(data, dict):
        raise ValueError("Data must be a dictionary")
    
    title = data.get("goal_title")
    if not isinstance(title, str) or not title.strip():
        raise ValueError("goal_title must be a non-empty string")
    
    if "goal_description" not in data or not isinstance(data["goal_description"], str):
        raise ValueError("goal_description must be a string")
    
    themes = data.get("key_themes")
    if not isinstance(themes, list):
        raise ValueError("key_themes must be a list")

def validate_phase_plan(data: dict) -> None:
    if not isinstance(data, dict):
        raise ValueError("Data must be a dictionary")
    
    theme = data.get("theme")
    if not isinstance(theme, str) or not theme.strip():
        raise ValueError("theme must be a non-empty string")
    
    vocab = data.get("vocabulary")
    if not isinstance(vocab, list) or not (5 <= len(vocab) <= 15):
        raise ValueError("vocabulary must be a list with 5-15 items")
    
    milestones = data.get("milestones")
    if not isinstance(milestones, list) or not (1 <= len(milestones) <= 5):
        raise ValueError("milestones must be a list with 1-5 items")
    
    target = data.get("sentence_count_target")
    if not isinstance(target, int) or not (5 <= target <= 20):
        raise ValueError("sentence_count_target must be an integer between 5 and 20")

def validate_phase_content(data: dict) -> None:
    if not isinstance(data, dict):
        raise ValueError("Data must be a dictionary")
    
    sentences = data.get("sentences")
    if not isinstance(sentences, list) or not (5 <= len(sentences) <= 20):
        raise ValueError("sentences must be a list with 5-20 items")
    
    for i, item in enumerate(sentences):
        if not isinstance(item, dict) or not isinstance(item.get("sentence"), str) or not item["sentence"].strip():
            raise ValueError(f"Sentence item at index {i} must have a non-empty 'sentence' string")

def validate_progression_decision(data: dict) -> None:
    if not isinstance(data, dict):
        raise ValueError("Data must be a dictionary")
    
    action = data.get("action")
    valid_actions = {"advance", "repeat", "regenerate"}
    if action not in valid_actions:
        raise ValueError(f"action must be one of {valid_actions}")
    
    if "reasoning" not in data or not isinstance(data["reasoning"], str):
        raise ValueError("reasoning must be a string")
    
    confidence = data.get("confidence")
    if not isinstance(confidence, (int, float)) or not (0 <= confidence <= 1):
        raise ValueError("confidence must be a number between 0 and 1")


def validate_teacher_coaching(data: dict) -> None:
    if not isinstance(data, dict):
        raise ValueError("Data must be a dictionary")

    action = data.get("action")
    valid_actions = {"retry_sentence", "drill_words", "move_on"}
    if action not in valid_actions:
        raise ValueError(f"action must be one of {valid_actions}")

    if "message" not in data or not isinstance(data["message"], str) or not data["message"].strip():
        raise ValueError("message must be a non-empty string")

    focus_words = data.get("focus_words")
    if not isinstance(focus_words, list):
        raise ValueError("focus_words must be a list")


def validate_teacher_borderline_pass(data: dict) -> None:
    if not isinstance(data, dict):
        raise ValueError("Data must be a dictionary")

    action = data.get("action")
    valid_actions = {"pass_with_note", "drill_weak_words", "retry_sentence"}
    if action not in valid_actions:
        raise ValueError(f"action must be one of {valid_actions}")

    if "message" not in data or not isinstance(data["message"], str) or not data["message"].strip():
        raise ValueError("message must be a non-empty string")

    if not isinstance(data.get("weak_words"), list):
        raise ValueError("weak_words must be a list")


def validate_pre_sentence_coaching(data: dict) -> None:
    if not isinstance(data, dict):
        raise ValueError("Data must be a dictionary")
    if "tip" not in data or not isinstance(data["tip"], str) or not data["tip"].strip():
        raise ValueError("tip must be a non-empty string")
    if not isinstance(data.get("focus_words"), list):
        raise ValueError("focus_words must be a list")


def validate_post_session_summary(data: dict) -> None:
    if not isinstance(data, dict):
        raise ValueError("Data must be a dictionary")
    if "summary" not in data or not isinstance(data["summary"], str) or not data["summary"].strip():
        raise ValueError("summary must be a non-empty string")


def validate_smart_sentence_regen(data: dict) -> None:
    if not isinstance(data, dict):
        raise ValueError("Data must be a dictionary")
    if "sentence" not in data or not isinstance(data["sentence"], str) or not data["sentence"].strip():
        raise ValueError("sentence must be a non-empty string")


def validate_word_pronunciation(data: dict) -> None:
    if not isinstance(data, dict):
        raise ValueError("Data must be a dictionary")
    if "explanation" not in data or not isinstance(data["explanation"], str) or not data["explanation"].strip():
        raise ValueError("explanation must be a non-empty string")


def validate_weekly_report(data: dict) -> None:
    if not isinstance(data, dict):
        raise ValueError("Data must be a dictionary")
    if "report" not in data or not isinstance(data["report"], str) or not data["report"].strip():
        raise ValueError("report must be a non-empty string")
