"""
Pydantic models mirroring the iPhone Gateway OpenAPI contract.
Source of truth: docs/api/iphone-gateway.openapi.yaml
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, UUID4


# ─── Shared / primitive ───────────────────────────────────────────────────────

class ErrorEnvelope(BaseModel):
    error_code: str
    message: str
    request_id: Optional[str] = None
    detail: Optional[Any] = None


class VocabularyItem(BaseModel):
    word: str
    ipa: str
    vietnamese_gloss: str
    example_sentence: str


class Milestone(BaseModel):
    description: str
    criteria: str


class WordScore(BaseModel):
    word: str
    accuracy: int = Field(ge=0, le=100)
    color: Literal["green", "yellow", "red", "gray"]
    phoneme_similarity: float = Field(ge=0.0, le=1.0)
    tip: Optional[str] = None
    error_type: Optional[str] = None
    error_label: Optional[str] = None
    target_ipa: Optional[str] = None
    practice_examples: list[str] = Field(default_factory=list)
    detected_ipa: Optional[str] = None
    phoneme_match_ratio: Optional[float] = None
    missing_phonemes: list[str] = Field(default_factory=list)


class SampleAudio(BaseModel):
    audio_id: str
    content_type: str
    duration_ms: int
    url: str
    expires_at: datetime


class PhaseProgress(BaseModel):
    total: int
    attempted: int
    mastered: int
    avg_score: float
    struggling_words: list[str] = Field(default_factory=list)


class LoadingHint(BaseModel):
    blocking: bool = True
    message: str
    estimated_seconds: int


# ─── User / profile ───────────────────────────────────────────────────────────

class UserProfile(BaseModel):
    user_id: str
    username: str
    display_name: Optional[str] = None
    interface_language: Literal["vi", "en"]
    created_at: datetime
    onboarding_completed_at: Optional[datetime] = None
    active_curriculum_id: Optional[int] = None
    current_level: int = Field(ge=1, le=3)
    total_sessions: int = Field(ge=0)
    streak_count: int = Field(ge=0)


class UserRegistrationRequest(BaseModel):
    username: str
    display_name: Optional[str] = None
    interface_language: Literal["vi", "en"] = "vi"
    device_name: Optional[str] = None


class UserRegistrationResponse(BaseModel):
    user: UserProfile
    next_action: str


# ─── Onboarding ───────────────────────────────────────────────────────────────

class OnboardingMessage(BaseModel):
    turn_number: int
    role: Literal["user", "assistant"]
    content: str


class GoalSynthesis(BaseModel):
    goal_title: str
    goal_description: str
    suggested_phase_count: int
    key_themes: list[str]


class OnboardingSessionState(BaseModel):
    user_id: str
    mode: str
    onboarding_turn: Optional[int] = None
    expires_at: Optional[datetime] = None


class OnboardingStartRequest(BaseModel):
    user_id: str
    resume_if_exists: bool = True


class OnboardingTurnResponse(BaseModel):
    session: OnboardingSessionState
    assistant_message: OnboardingMessage
    history_preview: list[OnboardingMessage]
    pending_goal_synthesis: Optional[GoalSynthesis] = None


class OnboardingRespondRequest(BaseModel):
    user_id: str
    message: str


class OnboardingRespondResponse(BaseModel):
    session: OnboardingSessionState
    result_type: Literal["question", "synthesis"]
    assistant_message: OnboardingMessage
    pending_goal_synthesis: Optional[GoalSynthesis] = None


class OnboardingConfirmRequest(BaseModel):
    user_id: str
    confirmed: bool


class OnboardingHistoryResponse(BaseModel):
    user_id: str
    mode: str
    turns: list[OnboardingMessage]
    pending_goal_synthesis: Optional[GoalSynthesis] = None


# ─── Curriculum ───────────────────────────────────────────────────────────────

class CurriculumSummary(BaseModel):
    curriculum_id: int
    user_id: Optional[str] = None
    status: str
    goal_title: str
    goal_description: str
    interface_language: str
    current_phase_number: int
    created_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class CurriculumPhase(BaseModel):
    phase_id: int
    phase_number: int
    theme: str
    status: str
    regeneration_count: int
    vocabulary: list[VocabularyItem] = Field(default_factory=list)
    milestones: list[Milestone] = Field(default_factory=list)
    sentence_count_target: Optional[int] = None
    curriculum_id: Optional[int] = None
    progress: Optional[PhaseProgress] = None


class PracticeContentItem(BaseModel):
    content_id: int
    sentence: str
    target_phonemes: list[str] = Field(default_factory=list)
    target_words: list[str] = Field(default_factory=list)
    difficulty_score: int
    attempt_count: Optional[int] = None
    last_score: Optional[int] = None
    mastered_at: Optional[datetime] = None


class CurrentCurriculumResponse(BaseModel):
    curriculum: CurriculumSummary
    active_phase: CurriculumPhase
    next_item: Optional[PracticeContentItem] = None


class CurriculumGenerateRequest(BaseModel):
    user_id: str
    source: str
    curriculum_id: int
    phase_number: int
    reason: Optional[str] = None


class CurriculumGenerateResponse(BaseModel):
    loading: LoadingHint
    curriculum: CurriculumSummary
    phase: CurriculumPhase
    content_items: list[PracticeContentItem] = Field(default_factory=list)


class AdvancePhaseRequest(BaseModel):
    user_id: str


class AdvancePhaseResponse(BaseModel):
    action: Literal["advance", "repeat", "regenerate", "phase_regenerated"]
    message: str
    curriculum: CurriculumSummary
    active_phase: CurriculumPhase
    first_practice_item: Optional[PracticeContentItem] = None


class PhaseDetailResponse(BaseModel):
    phase: CurriculumPhase
    content_items: list[PracticeContentItem] = Field(default_factory=list)


class CurriculumArchiveRequest(BaseModel):
    user_id: str
    confirm: bool
    reason: Optional[str] = None


class CurriculumArchiveResponse(BaseModel):
    archived_curriculum_id: int
    status: str
    onboarding_required: bool
    message: str


class OnboardingConfirmResponse(BaseModel):
    status: Literal["confirmed", "rejected"]
    loading: Optional[LoadingHint] = None
    curriculum: Optional[CurriculumSummary] = None
    phase: Optional[CurriculumPhase] = None
    first_practice_item: Optional[PracticeContentItem] = None
    message: Optional[str] = None
    onboarding_history_cleared: bool = True


# ─── Practice session ─────────────────────────────────────────────────────────

class PracticeSessionState(BaseModel):
    user_id: str
    mode: str
    round: Optional[int] = None
    fail_count: int = 0
    drill_index: Optional[int] = None
    drill_words: Optional[list[str]] = None
    started_at: Optional[datetime] = None
    consecutive_passes: int = 0


class PracticeSessionCurriculumContext(BaseModel):
    curriculum_id: int
    current_phase_number: int
    phase_theme: str


class DrillInfo(BaseModel):
    active_word: str
    drill_index: int
    total_words: int


class PracticeSessionStateResponse(BaseModel):
    session: PracticeSessionState
    curriculum: PracticeSessionCurriculumContext
    current_item: Optional[PracticeContentItem] = None
    progress: Optional[PhaseProgress] = None
    sample_audio: Optional[SampleAudio] = None
    drill: Optional[DrillInfo] = None
    phase_complete: bool = False
    consecutive_passes: int = 0


class PracticeSessionStartRequest(BaseModel):
    user_id: str
    resume_if_exists: bool = True


class PracticeSessionActionRequest(BaseModel):
    user_id: str


class PracticeSkipResponse(BaseModel):
    action: Literal["skipped"]
    skipped_count: int
    next_state: PracticeSessionStateResponse


class SessionEndSummary(BaseModel):
    total_attempts: int
    passed_first_try: int
    needed_drill: int
    skipped: int
    final_mode: str


class PracticeStopResponse(BaseModel):
    action: Literal["stopped"]
    session_cleared: bool
    summary: SessionEndSummary
    message: str


# ─── Scoring ──────────────────────────────────────────────────────────────────

class ScoringResult(BaseModel):
    overall_score: int = Field(ge=0, le=100)
    passed: bool
    transcript: str
    expected_text: str
    engine: Literal["whisper", "azure"]
    weak_words: list[str] = Field(default_factory=list)
    error_types: list[str] = Field(default_factory=list)
    feedback_message: str
    word_scores: list[WordScore] = Field(default_factory=list)
    sample_audio: Optional[SampleAudio] = None
    fluency_score: Optional[int] = None
    linking_score: Optional[int] = None
    prosody_score: Optional[int] = None
    pace_wpm: Optional[float] = None


class ScratchScoringResult(BaseModel):
    overall_score: int = Field(ge=0, le=100)
    transcript: str
    expected_text: str
    word_scores: list[WordScore] = Field(default_factory=list)
    passed: bool


class NextActionHint(BaseModel):
    action: str
    message: str
    focus_words: Optional[list[str]] = None


class CoachingHint(BaseModel):
    action: Literal["continue", "scaffold", "break_down", "skip_with_note"]
    message_vi: str
    scaffold_word: str | None = None
    scaffold_reason_vi: str | None = None
    syllables: list[str] = Field(default_factory=list)
    articulatory_tip_vi: str | None = None
    skip_reason_vi: str | None = None
    difficulty: int = Field(ge=1, le=10)
    attempt_count: int = Field(ge=0)
    max_attempts: int = Field(ge=1)


class PracticeAudioResponse(BaseModel):
    scoring: ScoringResult
    next_action: NextActionHint
    session: PracticeSessionState
    current_item: PracticeContentItem
    consecutive_passes: int = 0
    coaching: CoachingHint | None = None


# ─── Progress ─────────────────────────────────────────────────────────────────

class ProgressResponse(BaseModel):
    user: UserProfile
    curriculum: Optional[CurriculumSummary] = None
    phase_progress: Optional[PhaseProgress] = None
    recent_word_scores: list[WordScore] = Field(default_factory=list)
    last_sample_audio: Optional[SampleAudio] = None


class ProgressSummary(BaseModel):
    """Alias for richer summary usage by other modules."""
    user: UserProfile
    curriculum: Optional[CurriculumSummary] = None
    phase_progress: Optional[PhaseProgress] = None


# ─── Health ───────────────────────────────────────────────────────────────────

class HealthDependencies(BaseModel):
    database: Literal["up", "down"]
    ollama: Literal["up", "down"]
    whisper: Literal["loaded", "not_loaded"]
    ffmpeg: Literal["available", "unavailable"]


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded", "down"]
    app_version: str
    timestamp: datetime
    dependencies: HealthDependencies


# ─── WebSocket ────────────────────────────────────────────────────────────────

class WebSocketEnvelope(BaseModel):
    event: str
    timestamp: datetime
    data: dict[str, Any]
