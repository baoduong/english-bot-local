import Foundation

public struct UserProfile: Codable, Identifiable {
    public let userId: String
    public let username: String
    public let displayName: String?
    public let interfaceLanguage: String
    public let currentLevel: Int
    public let totalSessions: Int
    public let streakCount: Int
    
    public var id: String { userId }
    
    enum CodingKeys: String, CodingKey {
        case userId = "user_id"
        case username
        case displayName = "display_name"
        case interfaceLanguage = "interface_language"
        case currentLevel = "current_level"
        case totalSessions = "total_sessions"
        case streakCount = "streak_count"
    }
}

public struct OnboardingMessage: Codable, Identifiable {
    public let turnNumber: Int
    public let role: String
    public let content: String
    
    public var id: Int { turnNumber }
    
    enum CodingKeys: String, CodingKey {
        case turnNumber = "turn_number"
        case role
        case content
    }
}

public struct GoalSynthesis: Codable {
    public let goalTitle: String
    public let goalDescription: String
    public let suggestedPhaseCount: Int
    public let keyThemes: [String]
    
    enum CodingKeys: String, CodingKey {
        case goalTitle = "goal_title"
        case goalDescription = "goal_description"
        case suggestedPhaseCount = "suggested_phase_count"
        case keyThemes = "key_themes"
    }
}

public struct OnboardingSessionState: Codable {
    public let userId: String
    public let mode: String
    public let onboardingTurn: Int?
    
    enum CodingKeys: String, CodingKey {
        case userId = "user_id"
        case mode
        case onboardingTurn = "onboarding_turn"
    }
}

// Requests
public struct OnboardingStartRequest: Codable {
    public let userId: String
    public let resumeIfExists: Bool
    
    enum CodingKeys: String, CodingKey {
        case userId = "user_id"
        case resumeIfExists = "resume_if_exists"
    }
}

public struct OnboardingRespondRequest: Codable {
    public let userId: String
    public let message: String
    
    enum CodingKeys: String, CodingKey {
        case userId = "user_id"
        case message
    }
}

public struct OnboardingConfirmRequest: Codable {
    public let userId: String
    public let confirmed: Bool
    
    enum CodingKeys: String, CodingKey {
        case userId = "user_id"
        case confirmed
    }
}

// Responses
public struct OnboardingTurnResponse: Codable {
    public let session: OnboardingSessionState
    public let assistantMessage: OnboardingMessage
    public let historyPreview: [OnboardingMessage]
    public let pendingGoalSynthesis: GoalSynthesis?
    
    enum CodingKeys: String, CodingKey {
        case session
        case assistantMessage = "assistant_message"
        case historyPreview = "history_preview"
        case pendingGoalSynthesis = "pending_goal_synthesis"
    }
}

public struct OnboardingRespondResponse: Codable {
    public let session: OnboardingSessionState
    public let resultType: String
    public let assistantMessage: OnboardingMessage
    public let pendingGoalSynthesis: GoalSynthesis?
    
    enum CodingKeys: String, CodingKey {
        case session
        case resultType = "result_type"
        case assistantMessage = "assistant_message"
        case pendingGoalSynthesis = "pending_goal_synthesis"
    }
}

public struct LoadingHint: Codable {
    public let blocking: Bool
    public let message: String
    public let estimatedSeconds: Int
    
    enum CodingKeys: String, CodingKey {
        case blocking
        case message
        case estimatedSeconds = "estimated_seconds"
    }
}

public struct CurriculumSummary: Codable, Identifiable {
    public let curriculumId: Int
    public let status: String
    public let goalTitle: String
    public let goalDescription: String
    public let currentPhaseNumber: Int
    
    public var id: Int { curriculumId }
    
    enum CodingKeys: String, CodingKey {
        case curriculumId = "curriculum_id"
        case status
        case goalTitle = "goal_title"
        case goalDescription = "goal_description"
        case currentPhaseNumber = "current_phase_number"
    }
}

public struct CurriculumPhase: Codable, Identifiable {
    public let phaseId: Int
    public let phaseNumber: Int
    public let theme: String
    public let status: String
    
    public var id: Int { phaseId }
    
    enum CodingKeys: String, CodingKey {
        case phaseId = "phase_id"
        case phaseNumber = "phase_number"
        case theme
        case status
    }
}

public struct PracticeContentItem: Codable, Identifiable {
    public let contentId: Int
    public let sentence: String
    public let targetPhonemes: [String]?
    public let targetWords: [String]?
    public let difficultyScore: Int
    public let attemptCount: Int?
    public let lastScore: Int?
    public let masteredAt: String?

    public var id: Int { contentId }

    enum CodingKeys: String, CodingKey {
        case contentId = "content_id"
        case sentence
        case targetPhonemes = "target_phonemes"
        case targetWords = "target_words"
        case difficultyScore = "difficulty_score"
        case attemptCount = "attempt_count"
        case lastScore = "last_score"
        case masteredAt = "mastered_at"
    }
}

public struct OnboardingConfirmResponse: Codable {
    public let status: String
    public let loading: LoadingHint?
    public let curriculum: CurriculumSummary?
    public let phase: CurriculumPhase?
    public let firstPracticeItem: PracticeContentItem?
    public let message: String?
    
    enum CodingKeys: String, CodingKey {
        case status
        case loading
        case curriculum
        case phase
        case firstPracticeItem = "first_practice_item"
        case message
    }
}

public struct CurrentCurriculumResponse: Codable {
    public let curriculum: CurriculumSummary
    public let activePhase: CurriculumPhase
    public let nextItem: PracticeContentItem?
    
    enum CodingKeys: String, CodingKey {
        case curriculum
        case activePhase = "active_phase"
        case nextItem = "next_item"
    }
}

public struct PhaseDetailResponse: Codable {
    public let phase: CurriculumPhase
    public let contentItems: [PracticeContentItem]
    
    enum CodingKeys: String, CodingKey {
        case phase
        case contentItems = "content_items"
    }
}

public struct WebSocketEnvelope: Codable {
    public let event: String
    public let timestamp: String
    // Since data can be any dict, we'll keep it simple by decoding to Data or using a dynamic container.
    // For now, let's keep it as raw JSON Data for specific event parsing later.
}
