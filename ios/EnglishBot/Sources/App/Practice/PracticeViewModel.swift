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
    @Published public var currentSentence: String = "This is a placeholder sentence."
    @Published public var scoreResult: ScoringResult?
    @Published public var nextAction: NextActionHint?
    
    // For Word Drill
    @Published public var isWordDrill: Bool = false
    @Published public var drillWord: String = ""
    @Published public var drillProgress: String = ""
    
    public init() {}
    
    public func startSession() {
        // Fetch session from backend
        // Update currentSentence, etc.
        state = .idle
    }
    
    public func onRecordingStarted() {
        state = .recording
    }
    
    public func onRecordingStopped(url: URL?) {
        guard let url = url else { return }
        state = .uploading
        
        // Mock upload and scoring
        DispatchQueue.main.asyncAfter(deadline: .now() + 1.5) {
            self.mockScoringResponse()
            self.state = .scored
        }
    }
    
    public func skip() {
        // Call backend skip, then reset
        state = .idle
        scoreResult = nil
        nextAction = nil
    }
    
    public func stop() {
        // Stop session
    }
    
    public func next() {
        if nextAction?.action == "word_drill" {
            isWordDrill = true
            if let firstWord = nextAction?.focusWords?.first {
                drillWord = firstWord
                drillProgress = "Word 1/\(nextAction?.focusWords?.count ?? 1)"
            }
        } else {
            isWordDrill = false
            currentSentence = "Here is the next sentence to practice."
        }
        
        state = .idle
        scoreResult = nil
        nextAction = nil
    }
    
    private func mockScoringResponse() {
        let scores = [
            WordScore(word: "This", accuracy: 95, color: "green", phonemeSimilarity: 0.9, tip: nil),
            WordScore(word: "is", accuracy: 85, color: "green", phonemeSimilarity: 0.8, tip: nil),
            WordScore(word: "a", accuracy: 65, color: "yellow", phonemeSimilarity: 0.6, tip: nil),
            WordScore(word: "placeholder", accuracy: 40, color: "red", phonemeSimilarity: 0.4, tip: "Check 'p' sound"),
            WordScore(word: "sentence.", accuracy: 90, color: "green", phonemeSimilarity: 0.9, tip: nil)
        ]
        
        scoreResult = ScoringResult(
            overallScore: 75,
            passed: false,
            transcript: "This is a plasholder sentence",
            expectedText: "This is a placeholder sentence",
            engine: "mock",
            weakWords: ["placeholder", "a"],
            errorTypes: ["consonant"],
            feedbackMessage: "Watch your pronunciation of 'placeholder'.",
            wordScores: scores,
            sampleAudio: nil
        )
        
        nextAction = NextActionHint(
            action: "word_drill",
            message: "Let's drill some words",
            focusWords: ["placeholder", "a"]
        )
    }
}
