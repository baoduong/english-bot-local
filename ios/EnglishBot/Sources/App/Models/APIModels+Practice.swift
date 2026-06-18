import Foundation

// Practice Models
public struct WordScore: Codable, Identifiable {
    public let word: String
    public let accuracy: Int
    public let color: String
    public let phonemeSimilarity: Double
    public let tip: String?
    
    public var id: String { word }
    
    public init(word: String, accuracy: Int, color: String, phonemeSimilarity: Double, tip: String?) {
        self.word = word
        self.accuracy = accuracy
        self.color = color
        self.phonemeSimilarity = phonemeSimilarity
        self.tip = tip
    }
    
    enum CodingKeys: String, CodingKey {
        case word
        case accuracy
        case color
        case phonemeSimilarity = "phoneme_similarity"
        case tip
    }
}

public struct PhaseProgress: Codable {
    public let total: Int
    public let attempted: Int
    public let mastered: Int
    public let avgScore: Double
    public let strugglingWords: [String]
    
    public init(total: Int, attempted: Int, mastered: Int, avgScore: Double, strugglingWords: [String]) {
        self.total = total
        self.attempted = attempted
        self.mastered = mastered
        self.avgScore = avgScore
        self.strugglingWords = strugglingWords
    }
    
    enum CodingKeys: String, CodingKey {
        case total
        case attempted
        case mastered
        case avgScore = "avg_score"
        case strugglingWords = "struggling_words"
    }
}

public struct SampleAudio: Codable {
    public let audioId: String
    public let contentType: String
    public let durationMs: Int
    public let url: String
    // expiresAt is omitted for simplicity in App
    
    enum CodingKeys: String, CodingKey {
        case audioId = "audio_id"
        case contentType = "content_type"
        case durationMs = "duration_ms"
        case url
    }
}

public struct DrillInfo: Codable {
    public let activeWord: String
    public let drillIndex: Int
    public let totalWords: Int
    
    enum CodingKeys: String, CodingKey {
        case activeWord = "active_word"
        case drillIndex = "drill_index"
        case totalWords = "total_words"
    }
}

public struct PracticeSessionState: Codable {
    public let userId: String
    public let mode: String
    public let round: Int?
    public let failCount: Int
    public let drillIndex: Int?
    public let drillWords: [String]?
    
    enum CodingKeys: String, CodingKey {
        case userId = "user_id"
        case mode
        case round
        case failCount = "fail_count"
        case drillIndex = "drill_index"
        case drillWords = "drill_words"
    }
}

public struct PracticeSessionCurriculumContext: Codable {
    public let curriculumId: Int
    public let currentPhaseNumber: Int
    public let phaseTheme: String
    
    enum CodingKeys: String, CodingKey {
        case curriculumId = "curriculum_id"
        case currentPhaseNumber = "current_phase_number"
        case phaseTheme = "phase_theme"
    }
}

public struct PracticeSessionStateResponse: Codable {
    public let session: PracticeSessionState
    public let curriculum: PracticeSessionCurriculumContext
    public let currentItem: PracticeContentItem?
    public let progress: PhaseProgress?
    public let sampleAudio: SampleAudio?
    public let drill: DrillInfo?
    
    enum CodingKeys: String, CodingKey {
        case session
        case curriculum
        case currentItem = "current_item"
        case progress
        case sampleAudio = "sample_audio"
        case drill
    }
}

public struct ScoringResult: Codable {
    public let overallScore: Int
    public let passed: Bool
    public let transcript: String
    public let expectedText: String
    public let engine: String
    public let weakWords: [String]
    public let errorTypes: [String]
    public let feedbackMessage: String
    public let wordScores: [WordScore]
    public let sampleAudio: SampleAudio?
    
    public init(overallScore: Int, passed: Bool, transcript: String, expectedText: String, engine: String, weakWords: [String], errorTypes: [String], feedbackMessage: String, wordScores: [WordScore], sampleAudio: SampleAudio?) {
        self.overallScore = overallScore
        self.passed = passed
        self.transcript = transcript
        self.expectedText = expectedText
        self.engine = engine
        self.weakWords = weakWords
        self.errorTypes = errorTypes
        self.feedbackMessage = feedbackMessage
        self.wordScores = wordScores
        self.sampleAudio = sampleAudio
    }
    
    enum CodingKeys: String, CodingKey {
        case overallScore = "overall_score"
        case passed
        case transcript
        case expectedText = "expected_text"
        case engine
        case weakWords = "weak_words"
        case errorTypes = "error_types"
        case feedbackMessage = "feedback_message"
        case wordScores = "word_scores"
        case sampleAudio = "sample_audio"
    }
}

public struct NextActionHint: Codable {
    public let action: String
    public let message: String
    public let focusWords: [String]?
    
    public init(action: String, message: String, focusWords: [String]?) {
        self.action = action
        self.message = message
        self.focusWords = focusWords
    }
    
    enum CodingKeys: String, CodingKey {
        case action
        case message
        case focusWords = "focus_words"
    }
}

public struct PracticeAudioResponse: Codable {
    public let scoring: ScoringResult
    public let nextAction: NextActionHint
    public let session: PracticeSessionState
    public let currentItem: PracticeContentItem
    
    enum CodingKeys: String, CodingKey {
        case scoring
        case nextAction = "next_action"
        case session
        case currentItem = "current_item"
    }
}

public struct ProgressResponse: Codable {
    public let user: UserProfile
    public let curriculum: CurriculumSummary?
    public let phaseProgress: PhaseProgress?
    public let recentWordScores: [WordScore]
    public let lastSampleAudio: SampleAudio?
    
    public init(user: UserProfile, curriculum: CurriculumSummary?, phaseProgress: PhaseProgress?, recentWordScores: [WordScore], lastSampleAudio: SampleAudio?) {
        self.user = user
        self.curriculum = curriculum
        self.phaseProgress = phaseProgress
        self.recentWordScores = recentWordScores
        self.lastSampleAudio = lastSampleAudio
    }
    
    enum CodingKeys: String, CodingKey {
        case user
        case curriculum
        case phaseProgress = "phase_progress"
        case recentWordScores = "recent_word_scores"
        case lastSampleAudio = "last_sample_audio"
    }
}

// Extend existing models with init for mocking ONLY if they don't have it
public extension UserProfile {
    static func mock(userId: String, username: String, displayName: String?, interfaceLanguage: String, currentLevel: Int, totalSessions: Int, streakCount: Int) -> UserProfile {
        return UserProfile(userId: userId, username: username, displayName: displayName, interfaceLanguage: interfaceLanguage, currentLevel: currentLevel, totalSessions: totalSessions, streakCount: streakCount)
    }
}

public extension CurriculumSummary {
    static func mock(curriculumId: Int, status: String, goalTitle: String, goalDescription: String, currentPhaseNumber: Int) -> CurriculumSummary {
        return CurriculumSummary(curriculumId: curriculumId, status: status, goalTitle: goalTitle, goalDescription: goalDescription, currentPhaseNumber: currentPhaseNumber)
    }
}

// MARK: - Practice Session Requests/Responses (added for backend wiring)

public struct PracticeSessionStartRequest: Codable {
    public let userId: String
    public let resumeIfExists: Bool
    public init(userId: String, resumeIfExists: Bool = true) {
        self.userId = userId
        self.resumeIfExists = resumeIfExists
    }
    enum CodingKeys: String, CodingKey {
        case userId = "user_id"
        case resumeIfExists = "resume_if_exists"
    }
}

public struct PracticeSessionActionRequest: Codable {
    public let userId: String
    public init(userId: String) { self.userId = userId }
    enum CodingKeys: String, CodingKey {
        case userId = "user_id"
    }
}

public struct SessionEndSummary: Codable {
    public let totalAttempts: Int
    public let passedFirstTry: Int
    public let neededDrill: Int
    public let skipped: Int
    public let finalMode: String
    enum CodingKeys: String, CodingKey {
        case totalAttempts = "total_attempts"
        case passedFirstTry = "passed_first_try"
        case neededDrill = "needed_drill"
        case skipped
        case finalMode = "final_mode"
    }
}

public struct PracticeSkipResponse: Codable {
    public let action: String
    public let skippedCount: Int
    public let nextState: PracticeSessionStateResponse
    enum CodingKeys: String, CodingKey {
        case action
        case skippedCount = "skipped_count"
        case nextState = "next_state"
    }
}

public struct PracticeStopResponse: Codable {
    public let action: String
    public let sessionCleared: Bool
    public let summary: SessionEndSummary
    public let message: String
    enum CodingKeys: String, CodingKey {
        case action
        case sessionCleared = "session_cleared"
        case summary
        case message
    }
}
