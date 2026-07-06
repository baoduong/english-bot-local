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
    public let id: UUID
    public let turnNumber: Int
    public let role: String
    public let content: String
    
    enum CodingKeys: String, CodingKey {
        case turnNumber = "turn_number"
        case role
        case content
    }

    public init(id: UUID = UUID(), turnNumber: Int, role: String, content: String) {
        self.id = id
        self.turnNumber = turnNumber
        self.role = role
        self.content = content
    }

    public init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        id = UUID()
        turnNumber = try container.decode(Int.self, forKey: .turnNumber)
        role = try container.decode(String.self, forKey: .role)
        content = try container.decode(String.self, forKey: .content)
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
    public let userId: String?
    public let interfaceLanguage: String?
    public let createdAt: String?
    public let completedAt: String?
    
    public var id: Int { curriculumId }
    
    enum CodingKeys: String, CodingKey {
        case curriculumId = "curriculum_id"
        case status
        case goalTitle = "goal_title"
        case goalDescription = "goal_description"
        case currentPhaseNumber = "current_phase_number"
        case userId = "user_id"
        case interfaceLanguage = "interface_language"
        case createdAt = "created_at"
        case completedAt = "completed_at"
    }
}

public struct Milestone: Codable, Identifiable {
    public let description: String
    public let criteria: String
    public var id: String { description }
}

/// Vocabulary item as returned by the backend phase plan.
/// Backend sends objects: {"word": "...", "ipa": "...", "vietnamese_gloss": "...", "example_sentence": "..."}
public struct VocabularyItem: Codable, Identifiable {
    public let word: String
    public let ipa: String
    public let vietnameseGloss: String
    public let exampleSentence: String

    public var id: String { word }

    enum CodingKeys: String, CodingKey {
        case word
        case ipa
        case vietnameseGloss = "vietnamese_gloss"
        case exampleSentence = "example_sentence"
    }
}

public struct CurriculumPhase: Codable, Identifiable {
    public let phaseId: Int
    public let phaseNumber: Int
    public let theme: String
    public let status: String
    public let milestones: [Milestone]?
    /// Backend sends VocabularyItem objects (word/ipa/vietnamese_gloss/example_sentence).
    /// Previously typed as [String]? which caused a Codable type-mismatch decode error.
    public let vocabulary: [VocabularyItem]?
    public let progress: PhaseProgress?
    public let regenerationCount: Int?
    
    public var id: Int { phaseId }
    
    enum CodingKeys: String, CodingKey {
        case phaseId = "phase_id"
        case phaseNumber = "phase_number"
        case theme
        case status
        case milestones
        case vocabulary
        case progress
        case regenerationCount = "regeneration_count"
    }
    
    public init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        phaseId = try c.decode(Int.self, forKey: .phaseId)
        phaseNumber = try c.decode(Int.self, forKey: .phaseNumber)
        theme = try c.decode(String.self, forKey: .theme)
        status = try c.decode(String.self, forKey: .status)
        milestones = try c.decodeIfPresent([Milestone].self, forKey: .milestones)
        vocabulary = try c.decodeIfPresent([VocabularyItem].self, forKey: .vocabulary)
        progress = try c.decodeIfPresent(PhaseProgress.self, forKey: .progress)
        regenerationCount = try c.decodeIfPresent(Int.self, forKey: .regenerationCount)
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
    public let onboardingHistoryCleared: Bool?
    
    enum CodingKeys: String, CodingKey {
        case status
        case loading
        case curriculum
        case phase
        case firstPracticeItem = "first_practice_item"
        case message
        case onboardingHistoryCleared = "onboarding_history_cleared"
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

public struct ArchiveCurriculumRequest: Codable {
    public let userId: String
    public let confirm: Bool

    public init(userId: String, confirm: Bool = true) {
        self.userId = userId
        self.confirm = confirm
    }

    enum CodingKeys: String, CodingKey {
        case userId = "user_id"
        case confirm
    }
}

public struct ArchiveCurriculumResponse: Codable {
    public let archivedCurriculumId: Int
    public let status: String
    public let onboardingRequired: Bool
    public let message: String

    enum CodingKeys: String, CodingKey {
        case archivedCurriculumId = "archived_curriculum_id"
        case status
        case onboardingRequired = "onboarding_required"
        case message
    }
}

public enum WebSocketPayload {
    case connected(ConnectedPayload)
    case practiceState(PracticeStatePayload)
    case scoringResult(ScoringResultPayload)
    case error(ErrorPayload)
    case heartbeat
    case unknown
}

public struct ConnectedPayload: Codable {
    public let userId: String?
    public let resumed: Bool?

    enum CodingKeys: String, CodingKey {
        case userId = "user_id"
        case resumed
    }
}

public struct PracticeStatePayload: Codable {
    public let status: String?
    public let message: String?
}

public struct ScoringResultPayload: Codable {
    public let status: String?
    public let message: String?
}

public struct ErrorPayload: Codable {
    public let errorCode: String?
    public let message: String?
    public let detail: String?

    enum CodingKeys: String, CodingKey {
        case errorCode = "error_code"
        case message
        case detail
    }
}

public struct WebSocketEnvelope: Decodable {
    public let event: String
    public let timestamp: String
    public let data: WebSocketPayload

    enum CodingKeys: String, CodingKey {
        case event
        case timestamp
        case data
    }

    public init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        event = try container.decode(String.self, forKey: .event)
        timestamp = try container.decode(String.self, forKey: .timestamp)

        switch event {
        case "connected":
            let payload = try container.decodeIfPresent(ConnectedPayload.self, forKey: .data)
            data = payload.map { .connected($0) } ?? .unknown
        case "practice_state":
            let payload = try container.decodeIfPresent(PracticeStatePayload.self, forKey: .data)
            data = payload.map { .practiceState($0) } ?? .unknown
        case "scoring_result":
            let payload = try container.decodeIfPresent(ScoringResultPayload.self, forKey: .data)
            data = payload.map { .scoringResult($0) } ?? .unknown
        case "error":
            let payload = try container.decodeIfPresent(ErrorPayload.self, forKey: .data)
            data = payload.map { .error($0) } ?? .unknown
        case "heartbeat":
            data = .heartbeat
        default:
            data = .unknown
        }
    }
}
