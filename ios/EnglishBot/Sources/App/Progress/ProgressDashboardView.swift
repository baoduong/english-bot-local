import SwiftUI
import DesignSystem

public struct ProgressDashboardView: View {
    private let userId: String
    @StateObject private var viewModel: ProgressViewModel
    
    public init(userId: String) {
        self.userId = userId
        _viewModel = StateObject(wrappedValue: ProgressViewModel(userId: userId))
    }
    
    public var body: some View {
        ScrollView {
            VStack(spacing: Spacing.xl) {
                if viewModel.isLoading {
                    LoadingIndicator()
                        .padding(.top, 100)
                } else if let progress = viewModel.progress {
                    // Profile Header
                    HStack {
                        VStack(alignment: .leading) {
                            Text("Welcome back,")
                                .font(Font.BotTheme.bodySecondary)
                                .foregroundColor(Color.BotTheme.textSecondary)
                            Text(progress.user.displayName ?? progress.user.username)
                                .font(Font.BotTheme.heading1)
                                .foregroundColor(Color.BotTheme.textPrimary)
                        }
                        Spacer()
                        VStack(alignment: .trailing) {
                            Text("🔥 \(progress.user.streakCount) day streak")
                                .font(Font.BotTheme.caption)
                                .foregroundColor(Color.BotTheme.primary)
                            Text("Level \(progress.user.currentLevel)")
                                .font(Font.BotTheme.caption)
                                .foregroundColor(Color.BotTheme.textSecondary)
                        }
                    }
                    
                    // Current Curriculum Card
                    if let curriculum = progress.curriculum, let phase = progress.phaseProgress {
                        VStack(alignment: .leading, spacing: Spacing.md) {
                            Text("Phase \(curriculum.currentPhaseNumber): \(curriculum.goalTitle)")
                                .font(Font.BotTheme.heading2)
                                .foregroundColor(Color.BotTheme.textPrimary)
                            
                            ProgressChip(text: "\(phase.mastered)/\(phase.total) Mastered", icon: "🏆")
                            
                            HStack {
                                Text("Avg Score: \(Int(phase.avgScore))")
                                    .font(Font.BotTheme.caption)
                                    .foregroundColor(Color.BotTheme.textSecondary)
                                Spacer()
                            }
                        }
                        .padding()
                        .background(Color.BotTheme.backgroundSecondary)
                        .cornerRadius(Spacing.md)
                    }
                    
                    // Recent Scores
                    if !progress.recentWordScores.isEmpty {
                        VStack(alignment: .leading, spacing: Spacing.md) {
                            Text("Recent Words")
                                .font(Font.BotTheme.heading2)
                                .foregroundColor(Color.BotTheme.textPrimary)
                            
                            FlowLayout(spacing: Spacing.sm) {
                                ForEach(progress.recentWordScores) { score in
                                    WordScorePill(word: score.word, score: score.accuracy)
                                }
                            }
                        }
                    }
                    
                    // Error Breakdown (mocked from struggling words)
                    if let phase = progress.phaseProgress, !phase.strugglingWords.isEmpty {
                        VStack(alignment: .leading, spacing: Spacing.md) {
                            Text("Needs Practice")
                                .font(Font.BotTheme.heading2)
                                .foregroundColor(Color.BotTheme.textPrimary)
                            
                            ForEach(phase.strugglingWords, id: \.self) { word in
                                HStack {
                                    Text(word)
                                        .font(Font.BotTheme.bodyPrimary)
                                        .foregroundColor(Color.BotTheme.textPrimary)
                                    Spacer()
                                    Text("Consonants")
                                        .font(Font.BotTheme.caption)
                                        .foregroundColor(Color.BotTheme.textSecondary)
                                }
                                .padding()
                                .background(Color.BotTheme.backgroundSecondary)
                                .cornerRadius(Spacing.sm)
                            }
                        }
                    }
                }
            }
            .padding(Spacing.lg)
        }
        .background(Color.BotTheme.backgroundMain.ignoresSafeArea())
        .onAppear {
            Task { await viewModel.fetchProgress() }
        }
    }
}
