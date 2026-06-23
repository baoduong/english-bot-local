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
    private var pollingTask: Task<Void, Never>?

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
        cancelCoachingPolling()
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

    private func cancelCoachingPolling() {
        pollingTask?.cancel()
        pollingTask = nil
    }

    public func onViewDisappear() {
        cancelCoachingPolling()
    }

    private func startCoachingPolling() {
        cancelCoachingPolling()
        let attemptContentId = currentContentId
        pollingTask = Task { [weak self] in
            guard let self = self else { return }

            for _ in 0..<10 {
                do {
                    try await Task.sleep(nanoseconds: 3_000_000_000)
                } catch {
                    break
                }

                if Task.isCancelled { break }

                do {
                    let response = try await self.apiClient.getPendingCoaching(userId: self.userId)
                    if let hint = response.coaching, let token = response.ackToken {
                        if let responseContentId = response.contentId,
                           let attemptContentId,
                           responseContentId != attemptContentId {
                            continue
                        }

                        await MainActor.run {
                            self.coachingHint = hint
                        }
                        _ = try? await self.apiClient.ackCoaching(userId: self.userId, ackToken: token)
                        break
                    }
                } catch {
                    continue
                }
            }

            await MainActor.run {
                self.pollingTask = nil
            }
        }
    }

    public func startSession() async {
        guard !hasStarted else { return }
        cancelCoachingPolling()
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
            coachingHint = nil
            consecutivePasses = response.consecutivePasses
            state = .scored
            startCoachingPolling()
        } catch {
            errorMessage = error.localizedDescription
            state = .idle
        }
    }

    public func skip() async {
        cancelCoachingPolling()
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
        cancelCoachingPolling()
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
        cancelCoachingPolling()
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
