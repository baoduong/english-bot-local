import SwiftUI
import DesignSystem

public struct CurriculumView: View {
    @StateObject private var viewModel: CurriculumViewModel
    
    public init(userId: String) {
        _viewModel = StateObject(wrappedValue: CurriculumViewModel(userId: userId))
    }
    
    public var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: Spacing.xl) {
                if viewModel.isLoading && viewModel.curriculum == nil {
                    ProgressView()
                        .frame(maxWidth: .infinity, alignment: .center)
                        .padding(.top, Spacing.xxl)
                } else if let error = viewModel.errorMessage {
                    Text("Error: \(error)")
                        .foregroundColor(.red)
                        .padding()
                } else if let curriculum = viewModel.curriculum, let phase = viewModel.activePhase {
                    // Header
                    VStack(alignment: .leading, spacing: Spacing.sm) {
                        Text(curriculum.goalTitle)
                            .font(Font.BotTheme.heading2)
                            .foregroundColor(Color.BotTheme.textPrimary)
                        
                        Text("Phase \(phase.phaseNumber)")
                            .font(Font.BotTheme.heading3)
                            .foregroundColor(Color.BotTheme.primary)
                        
                        Text(phase.theme)
                            .font(Font.BotTheme.bodyPrimary)
                            .foregroundColor(Color.BotTheme.textSecondary)
                        
                        ProgressChip(text: "Phase \(phase.phaseNumber)", icon: "📍")
                    }
                    .padding(.horizontal, Spacing.md)
                    
                    // Content Items
                    if let detail = viewModel.phaseDetail {
                        VStack(alignment: .leading, spacing: Spacing.md) {
                            Text("Sentences")
                                .font(Font.BotTheme.heading3)
                                .foregroundColor(Color.BotTheme.textPrimary)
                                .padding(.horizontal, Spacing.md)
                            
                            ForEach(detail.contentItems) { item in
                                SentenceRow(item: item)
                            }
                        }
                    } else if viewModel.isLoading {
                        ProgressView()
                            .frame(maxWidth: .infinity, alignment: .center)
                    }
                }
            }
            .padding(.vertical, Spacing.md)
        }
        .background(Color.BotTheme.backgroundMain)
        .navigationTitle("Curriculum")
        .task {
            await viewModel.fetchCurrentCurriculum()
        }
    }
}

struct SentenceRow: View {
    let item: PracticeContentItem
    
    var body: some View {
        HStack(spacing: Spacing.md) {
            // Status Icon
            Group {
                if item.masteredAt != nil {
                    Image(systemName: "checkmark.circle.fill")
                        .foregroundColor(Color.BotTheme.scoreExcellent)
                } else if let score = item.lastScore {
                    if score >= 80 {
                        Image(systemName: "checkmark.circle.fill")
                            .foregroundColor(Color.BotTheme.scoreExcellent)
                    } else if score >= 60 {
                        Image(systemName: "exclamationmark.circle.fill")
                            .foregroundColor(Color.BotTheme.scoreAverage)
                    } else {
                        Image(systemName: "xmark.circle.fill")
                            .foregroundColor(Color.BotTheme.scorePoor)
                    }
                } else {
                    Image(systemName: "circle")
                        .foregroundColor(Color.BotTheme.textTertiary)
                }
            }
            .font(.title2)
            
            VStack(alignment: .leading, spacing: Spacing.xs) {
                Text(item.sentence)
                    .font(Font.BotTheme.bodyPrimary)
                    .foregroundColor(Color.BotTheme.textPrimary)
                
                if let score = item.lastScore {
                    Text("Last score: \(score)")
                        .font(Font.BotTheme.caption)
                        .foregroundColor(Color.BotTheme.textSecondary)
                }
            }
            
            Spacer()
        }
        .padding(Spacing.md)
        .background(Color.BotTheme.backgroundSecondary)
        .cornerRadius(Spacing.md)
        .padding(.horizontal, Spacing.md)
    }
}
