import Foundation

@MainActor
public class ProgressViewModel: ObservableObject {
    @Published public var progress: ProgressResponse?
    @Published public var isLoading: Bool = false
    @Published public var error: String?
    
    public init() {}
    
    public func fetchProgress() {
        isLoading = true
        error = nil
        
        // Mock data
        DispatchQueue.main.asyncAfter(deadline: .now() + 1) {
            self.mockProgressResponse()
            self.isLoading = false
        }
    }
    
    private func mockProgressResponse() {
        let scores = [
            WordScore(word: "This", accuracy: 95, color: "green", phonemeSimilarity: 0.9, tip: nil),
            WordScore(word: "placeholder", accuracy: 40, color: "red", phonemeSimilarity: 0.4, tip: "Check 'p' sound")
        ]
        
        progress = ProgressResponse(
            user: UserProfile.mock(userId: "1", username: "user", displayName: "User", interfaceLanguage: "en", currentLevel: 1, totalSessions: 5, streakCount: 3),
            curriculum: CurriculumSummary.mock(curriculumId: 1, status: "active", goalTitle: "Improve pronunciation", goalDescription: "Focus on consonants", currentPhaseNumber: 1),
            phaseProgress: PhaseProgress(total: 10, attempted: 5, mastered: 3, avgScore: 75.0, strugglingWords: ["placeholder"]),
            recentWordScores: scores,
            lastSampleAudio: nil
        )
    }
}
