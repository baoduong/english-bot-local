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
    @Published public var errorMessage: String?

    // For Word Drill
    @Published public var isWordDrill: Bool = false
    @Published public var drillWord: String = ""
    @Published public var drillProgress: String = ""

    private let userId: String
    private let apiClient: APIClient
    private var currentContentId: Int?

    public init(userId: String, apiClient: APIClient = APIClient()) {
        self.userId = userId
        self.apiClient = apiClient
    }

    public var sampleAudioURL: URL? {
        if isWordDrill && !drillWord.isEmpty {
            return apiClient.sampleAudioURL(userId: userId, word: drillWord)
        }
        return apiClient.sampleAudioURL(userId: userId, expectedText: currentSentence)
    }

    private func applyState(_ response: PracticeSessionStateResponse) {
        currentContentId = response.currentItem?.contentId
        if let drill = response.drill {
            isWordDrill = true
            drillWord = drill.activeWord
            drillProgress = "Word \(drill.drillIndex + 1)/\(drill.totalWords)"
            currentSentence = drill.activeWord
        } else {
            isWordDrill = false
            currentSentence = response.currentItem?.sentence ?? ""
        }
    }

    public func startSession() async {
        state = .idle
        errorMessage = nil
        do {
            let response = try await apiClient.startPracticeSession(userId: userId, resumeIfExists: true)
            applyState(response)
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    public func onRecordingStarted() {
        state = .recording
    }

    public func onRecordingStopped(url: URL?) async {
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
            currentContentId = response.currentItem.contentId
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
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    public func stop() async {
        errorMessage = nil
        do {
            _ = try await apiClient.stopPracticeSession(userId: userId)
        } catch {
            errorMessage = error.localizedDescription
        }
        state = .idle
        scoreResult = nil
        nextAction = nil
    }

    public func next() async {
        errorMessage = nil
        scoreResult = nil
        nextAction = nil
        state = .idle
        do {
            let response = try await apiClient.getPracticeState(userId: userId)
            applyState(response)
        } catch {
            errorMessage = error.localizedDescription
        }
    }
}
