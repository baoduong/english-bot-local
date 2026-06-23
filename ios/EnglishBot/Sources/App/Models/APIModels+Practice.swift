import Foundation

// Practice Models
public struct WordScore: Codable, Identifiable {
    public let word: String
    public let accuracy: Int
    public let color: String
    public let phonemeSimilarity: Double
    public let tip: String?
    public let errorType: String?
    public let errorLabel: String?
    public let targetIpa: String?
    public let practiceExamples: [String]
    public let detectedIpa: String?
    public let phonemeMatchRatio: Double?
    public let missingPhonemes: [String]
    
    public let id: UUID
    
    public init(word: String, accuracy: Int, color: String, phonemeSimilarity: Double, tip: String?, errorType: String? = nil, errorLabel: String? = nil, targetIpa: String? = nil, practiceExamples: [String] = [], detectedIpa: String? = nil, phonemeMatchRatio: Double? = nil, missingPhonemes: [String] = []) {
        self.word = word
        self.accuracy = accuracy
        self.color = color
        self.phonemeSimilarity = phonemeSimilarity
        self.tip = tip
        self.errorType = errorType
        self.errorLabel = errorLabel
        self.targetIpa = targetIpa
        self.practiceExamples = practiceExamples
        self.detectedIpa = detectedIpa
        self.phonemeMatchRatio = phonemeMatchRatio
        self.missingPhonemes = missingPhonemes
        self.id = UUID()
    }
    
    public init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        word = try container.decode(String.self, forKey: .word)
        accuracy = try container.decode(Int.self, forKey: .accuracy)
        color = try container.decode(String.self, forKey: .color)
        phonemeSimilarity = try container.decode(Double.self, forKey: .phonemeSimilarity)
        tip = try container.decodeIfPresent(String.self, forKey: .tip)
        errorType = try container.decodeIfPresent(String.self, forKey: .errorType)
        errorLabel = try container.decodeIfPresent(String.self, forKey: .errorLabel)
        targetIpa = try container.decodeIfPresent(String.self, forKey: .targetIpa)
        practiceExamples = try container.decodeIfPresent([String].self, forKey: .practiceExamples) ?? []
        detectedIpa = try container.decodeIfPresent(String.self, forKey: .detectedIpa)
        phonemeMatchRatio = try container.decodeIfPresent(Double.self, forKey: .phonemeMatchRatio)
        missingPhonemes = try container.decodeIfPresent([String].self, forKey: .missingPhonemes) ?? []
        id = UUID()
    }
    
    enum CodingKeys: String, CodingKey {
        case word
        case accuracy
        case color
        case phonemeSimilarity = "phoneme_similarity"
        case tip
        case errorType = "error_type"
        case errorLabel = "error_label"
        case targetIpa = "target_ipa"
        case practiceExamples = "practice_examples"
        case detectedIpa = "detected_ipa"
        case phonemeMatchRatio = "phoneme_match_ratio"
        case missingPhonemes = "missing_phonemes"
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
    public let consecutivePasses: Int
    
    public init(userId: String, mode: String, round: Int?, failCount: Int, drillIndex: Int?, drillWords: [String]?, consecutivePasses: Int = 0) {
        self.userId = userId
        self.mode = mode
        self.round = round
        self.failCount = failCount
        self.drillIndex = drillIndex
        self.drillWords = drillWords
        self.consecutivePasses = consecutivePasses
    }
    
    public init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        userId = try container.decode(String.self, forKey: .userId)
        mode = try container.decode(String.self, forKey: .mode)
        round = try container.decodeIfPresent(Int.self, forKey: .round)
        failCount = try container.decode(Int.self, forKey: .failCount)
        drillIndex = try container.decodeIfPresent(Int.self, forKey: .drillIndex)
        drillWords = try container.decodeIfPresent([String].self, forKey: .drillWords)
        consecutivePasses = try container.decodeIfPresent(Int.self, forKey: .consecutivePasses) ?? 0
    }
    
    enum CodingKeys: String, CodingKey {
        case userId = "user_id"
        case mode
        case round
        case failCount = "fail_count"
        case drillIndex = "drill_index"
        case drillWords = "drill_words"
        case consecutivePasses = "consecutive_passes"
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
    public let phaseComplete: Bool
    public let consecutivePasses: Int
    
    enum CodingKeys: String, CodingKey {
        case session
        case curriculum
        case currentItem = "current_item"
        case progress
        case sampleAudio = "sample_audio"
        case drill
        case phaseComplete = "phase_complete"
        case consecutivePasses = "consecutive_passes"
    }

    public init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        session = try c.decode(PracticeSessionState.self, forKey: .session)
        curriculum = try c.decode(PracticeSessionCurriculumContext.self, forKey: .curriculum)
        currentItem = try c.decodeIfPresent(PracticeContentItem.self, forKey: .currentItem)
        progress = try c.decodeIfPresent(PhaseProgress.self, forKey: .progress)
        sampleAudio = try c.decodeIfPresent(SampleAudio.self, forKey: .sampleAudio)
        drill = try c.decodeIfPresent(DrillInfo.self, forKey: .drill)
        phaseComplete = try c.decodeIfPresent(Bool.self, forKey: .phaseComplete) ?? false
        consecutivePasses = try c.decodeIfPresent(Int.self, forKey: .consecutivePasses) ?? 0
    }
}

public struct AdvancePhaseResponse: Codable {
    public let action: String
    public let message: String
    public let curriculum: CurriculumSummary
    public let activePhase: CurriculumPhase
    public let firstPracticeItem: PracticeContentItem?

    enum CodingKeys: String, CodingKey {
        case action
        case message
        case curriculum
        case activePhase = "active_phase"
        case firstPracticeItem = "first_practice_item"
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
    
    public let fluencyScore: Int?
    public let linkingScore: Int?
    public let prosodyScore: Int?
    public let paceWpm: Double?
    
    public init(overallScore: Int, passed: Bool, transcript: String, expectedText: String, engine: String, weakWords: [String], errorTypes: [String], feedbackMessage: String, wordScores: [WordScore], sampleAudio: SampleAudio?, fluencyScore: Int? = nil, linkingScore: Int? = nil, prosodyScore: Int? = nil, paceWpm: Double? = nil) {
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
        self.fluencyScore = fluencyScore
        self.linkingScore = linkingScore
        self.prosodyScore = prosodyScore
        self.paceWpm = paceWpm
    }
    
    public init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        overallScore = try container.decode(Int.self, forKey: .overallScore)
        passed = try container.decode(Bool.self, forKey: .passed)
        transcript = try container.decode(String.self, forKey: .transcript)
        expectedText = try container.decode(String.self, forKey: .expectedText)
        engine = try container.decode(String.self, forKey: .engine)
        weakWords = try container.decode([String].self, forKey: .weakWords)
        errorTypes = try container.decode([String].self, forKey: .errorTypes)
        feedbackMessage = try container.decode(String.self, forKey: .feedbackMessage)
        wordScores = try container.decode([WordScore].self, forKey: .wordScores)
        sampleAudio = try container.decodeIfPresent(SampleAudio.self, forKey: .sampleAudio)
        fluencyScore = try container.decodeIfPresent(Int.self, forKey: .fluencyScore)
        linkingScore = try container.decodeIfPresent(Int.self, forKey: .linkingScore)
        prosodyScore = try container.decodeIfPresent(Int.self, forKey: .prosodyScore)
        paceWpm = try container.decodeIfPresent(Double.self, forKey: .paceWpm)
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
        case fluencyScore = "fluency_score"
        case linkingScore = "linking_score"
        case prosodyScore = "prosody_score"
        case paceWpm = "pace_wpm"
    }
}

public struct ScratchScoringResult: Codable {
    public let overallScore: Int
    public let transcript: String
    public let expectedText: String
    public let wordScores: [WordScore]
    public let passed: Bool

    enum CodingKeys: String, CodingKey {
        case overallScore = "overall_score"
        case transcript
        case expectedText = "expected_text"
        case wordScores = "word_scores"
        case passed
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

public struct CoachingHint: Codable {
    public let action: String  // "continue" | "scaffold" | "break_down" | "skip_with_note"
    public let messageVi: String
    public let scaffoldWord: String?
    public let scaffoldReasonVi: String?
    public let syllables: [String]
    public let articulatoryTipVi: String?
    public let skipReasonVi: String?
    public let difficulty: Int
    public let attemptCount: Int
    public let maxAttempts: Int
    
    enum CodingKeys: String, CodingKey {
        case action
        case messageVi = "message_vi"
        case scaffoldWord = "scaffold_word"
        case scaffoldReasonVi = "scaffold_reason_vi"
        case syllables
        case articulatoryTipVi = "articulatory_tip_vi"
        case skipReasonVi = "skip_reason_vi"
        case difficulty
        case attemptCount = "attempt_count"
        case maxAttempts = "max_attempts"
    }
    
    public init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        action = try c.decode(String.self, forKey: .action)
        messageVi = try c.decode(String.self, forKey: .messageVi)
        scaffoldWord = try c.decodeIfPresent(String.self, forKey: .scaffoldWord)
        scaffoldReasonVi = try c.decodeIfPresent(String.self, forKey: .scaffoldReasonVi)
        syllables = try c.decodeIfPresent([String].self, forKey: .syllables) ?? []
        articulatoryTipVi = try c.decodeIfPresent(String.self, forKey: .articulatoryTipVi)
        skipReasonVi = try c.decodeIfPresent(String.self, forKey: .skipReasonVi)
        difficulty = try c.decodeIfPresent(Int.self, forKey: .difficulty) ?? 5
        attemptCount = try c.decodeIfPresent(Int.self, forKey: .attemptCount) ?? 0
        maxAttempts = try c.decodeIfPresent(Int.self, forKey: .maxAttempts) ?? 3
    }
}

public struct PracticeAudioResponse: Codable {
    public let scoring: ScoringResult
    public let nextAction: NextActionHint
    public let coaching: CoachingHint?
    public let session: PracticeSessionState
    public let currentItem: PracticeContentItem
    public let consecutivePasses: Int
    
    public init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        scoring = try container.decode(ScoringResult.self, forKey: .scoring)
        nextAction = try container.decode(NextActionHint.self, forKey: .nextAction)
        coaching = try container.decodeIfPresent(CoachingHint.self, forKey: .coaching)
        session = try container.decode(PracticeSessionState.self, forKey: .session)
        currentItem = try container.decode(PracticeContentItem.self, forKey: .currentItem)
        consecutivePasses = try container.decodeIfPresent(Int.self, forKey: .consecutivePasses) ?? 0
    }
    
    enum CodingKeys: String, CodingKey {
        case scoring
        case nextAction = "next_action"
        case coaching
        case session
        case currentItem = "current_item"
        case consecutivePasses = "consecutive_passes"
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
