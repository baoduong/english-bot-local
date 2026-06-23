import Foundation
import SwiftUI

@MainActor
public class PracticeViewModel: ObservableObject {
    public enum State {
        case idle
        case recording
        case uploading
        case scored
    }

    @Published public var state: State = .idle
    @Published public var currentSentence: String = ""
    @Published public var scoreResult: ScoringResult?
    @Published public var nextAction: NextActionHint?
    @Published public var coachingHint: CoachingHint?
    @Published public var errorMessage: String?
    @Published public var phaseComplete: Bool = false
    @Published public var isAdvancingPhase: Bool = false
    @Published public var phaseProgress: PhaseProgress?
    @Published public var consecutivePasses: Int = 0
    @Published private(set) var hasStarted: Bool = false

    // For Word Drill
    @Published public var isWordDrill: Bool = false
    @Published public var drillWord: String = ""
    @Published public var drillProgress: String = ""

    public let userId: String
    public let apiClient: APIClient
    private var currentContentId: Int?

    public init(userId: String, apiClient: APIClient = APIClient.shared) {
        self.userId = userId
        self.apiClient = apiClient
    }

    public var sampleAudioURL: URL? {
        if isWordDrill && !drillWord.isEmpty {
            return apiClient.sampleAudioURL(userId: userId, word: drillWord)
        }
        return apiClient.sampleAudioURL(userId: userId, expectedText: currentSentence)
    }

    public var slowSampleAudioURL: URL? {
        guard !isWordDrill, !currentSentence.isEmpty else { return nil }
        return apiClient.sampleAudioURL(userId: userId, expectedText: currentSentence, slow: true)
    }

    public func wordAudioURL(for word: String) -> URL? {
        return apiClient.sampleAudioURL(userId: userId, word: word)
    }

    private func applyState(_ response: PracticeSessionStateResponse) {
        coachingHint = nil
        phaseComplete = response.phaseComplete
        phaseProgress = response.progress
        consecutivePasses = response.consecutivePasses
        currentContentId = response.currentItem?.contentId
        if let drill = response.drill {
            isWordDrill = true
            drillWord = drill.activeWord
            drillProgress = "Word \(drill.drillIndex + 1)/\(drill.totalWords)"
            currentSentence = drill.activeWord
        } else {
            isWordDrill = false
            currentSentence = response.currentItem?.sentence ?? ""
            drillWord = ""
            drillProgress = ""
        }
    }

    public func startSession() async {
        guard !hasStarted else { return }
        state = .idle
        errorMessage = nil
        do {
            let response = try await apiClient.startPracticeSession(userId: userId, resumeIfExists: true)
            applyState(response)
            scoreResult = nil
            nextAction = nil
            coachingHint = nil
            hasStarted = true
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    public func onRecordingStarted() {
        guard state != .uploading else { return }
        state = .recording
    }

    public func onRecordingStopped(url: URL?) async {
        guard state != .uploading else { return }
        guard let url = url else { return }
        state = .uploading
        errorMessage = nil
        do {
            let response = try await apiClient.scorePracticeAudio(
                userId: userId,
                audioURL: url,
                contentId: currentContentId,
                expectedText: currentSentence.isEmpty ? nil : currentSentence
            )
            scoreResult = response.scoring
            nextAction = response.nextAction
            coachingHint = response.coaching
            consecutivePasses = response.consecutivePasses
            currentContentId = response.currentItem?.contentId
            state = .scored
        } catch {
            errorMessage = error.localizedDescription
            state = .idle
        }
    }

    public func skip() async {
        errorMessage = nil
        do {
            let response = try await apiClient.skipPracticeItem(userId: userId)
            applyState(response.nextState)
            state = .idle
            scoreResult = nil
            nextAction = nil
            coachingHint = nil
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    public func stop() async {
        hasStarted = false
        errorMessage = nil
        do {
            _ = try await apiClient.stopPracticeSession(userId: userId)
        } catch {
            errorMessage = error.localizedDescription
        }
        state = .idle
        scoreResult = nil
        nextAction = nil
        coachingHint = nil
    }

    public func advancePhase() async {
        isAdvancingPhase = true
        errorMessage = nil
        do {
            _ = try await apiClient.advancePhase(userId: userId)
            await startSession()
        } catch {
            errorMessage = error.localizedDescription
        }
        isAdvancingPhase = false
    }

    public func next() async {
        errorMessage = nil
        scoreResult = nil
        nextAction = nil
        coachingHint = nil
        state = .idle
        do {
            let response = try await apiClient.getPracticeState(userId: userId)
            applyState(response)
        } catch {
            errorMessage = error.localizedDescription
        }
    }
}
