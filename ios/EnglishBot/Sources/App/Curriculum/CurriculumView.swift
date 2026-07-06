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
                    VStack(spacing: Spacing.md) {
                        SkeletonCard(lines: 2)
                        SkeletonCard(lines: 3)
                        SkeletonCard(lines: 2)
                    }
                    .padding(.horizontal, Spacing.md)
                    .padding(.top, Spacing.md)
                } else if viewModel.isGeneratingCurriculum {
                    VStack(spacing: Spacing.lg) {
                        ProgressView()
                            .scaleEffect(1.4)
                        Text("🔄 Đang tạo lộ trình học...\n(có thể mất 60–90s)")
                            .font(Font.BotTheme.bodyPrimary)
                            .foregroundColor(Color.BotTheme.textSecondary)
                            .multilineTextAlignment(.center)
                    }
                    .padding(Spacing.xl)
                    .frame(maxWidth: .infinity)
                } else if let error = viewModel.errorMessage {
                    VStack(spacing: Spacing.md) {
                        HStack(spacing: Spacing.sm) {
                            Image(systemName: "exclamationmark.triangle.fill")
                                .foregroundColor(Color.BotTheme.scorePoor)
                            Text(error)
                                .font(Font.BotTheme.bodyPrimary)
                                .foregroundColor(Color.BotTheme.textPrimary)
                        }
                        .padding(Spacing.md)
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .background(
                            RoundedRectangle(cornerRadius: Radius.md, style: .continuous)
                                .fill(Color.BotTheme.scorePoor.opacity(0.15))
                        )

                        Button {
                            Task { await viewModel.load() }
                        } label: {
                            Label("Thử lại", systemImage: "arrow.clockwise")
                                .font(Font.BotTheme.bodyPrimary.weight(.semibold))
                        }
                        .buttonStyle(.bordered)
                    }
                    .padding(.horizontal, Spacing.md)
                } else if let curriculum = viewModel.curriculum, let phase = viewModel.activePhase {
                    // Header
                    VStack(alignment: .leading, spacing: Spacing.sm) {
                        ProgressChip(text: "Phase \(phase.phaseNumber)", systemIcon: "map.fill", tinted: true)
                        
                        Text(curriculum.goalTitle)
                            .font(Font.BotTheme.heading1)
                            .foregroundColor(Color.BotTheme.textPrimary)
                            .padding(.top, Spacing.xs)
                        
                        Text(phase.theme)
                            .font(Font.BotTheme.bodySecondary)
                            .foregroundColor(Color.BotTheme.textSecondary)
                    }
                    .padding(Spacing.lg)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .background(
                        RoundedRectangle(cornerRadius: Radius.lg, style: .continuous)
                            .fill(Color.BotTheme.accentSoft)
                    )
                    .padding(.horizontal, Spacing.md)
                    
                    // Milestones
                    if let milestones = phase.milestones, !milestones.isEmpty {
                        VStack(alignment: .leading, spacing: Spacing.md) {
                            Text("🎯 Sau khi hoàn thành phase này, bạn sẽ:")
                                .font(Font.BotTheme.heading3)
                                .foregroundColor(Color.BotTheme.textPrimary)
                            
                            ForEach(milestones) { milestone in
                                MilestoneCard(milestone: milestone)
                            }
                        }
                        .padding(.horizontal, Spacing.md)
                    }
                    
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
                        VStack(spacing: Spacing.md) {
                            SkeletonCard(lines: 2)
                            SkeletonCard(lines: 2)
                        }
                        .padding(.horizontal, Spacing.md)
                    }
                }
            }
            .padding(.vertical, Spacing.md)
        }
        .background(Color.BotTheme.backgroundMain)
        .navigationTitle("Curriculum")
        .task {
            await viewModel.load()
        }
        .refreshable {
            await viewModel.load()
        }
        .onReceive(NotificationCenter.default.publisher(for: .phaseAdvanced)) { _ in
            Task {
                await viewModel.load()
            }
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
            
            Spacer(minLength: 0)
        }
        .padding(Spacing.md)
        .cardStyle(radius: Radius.lg)
        .padding(.horizontal, Spacing.md)
    }
}

struct MilestoneCard: View {
    let milestone: Milestone
    
    var body: some View {
        HStack(alignment: .top, spacing: Spacing.md) {
            Image(systemName: "checkmark.seal.fill")
                .foregroundColor(Color.BotTheme.primary)
                .font(.title3)
            
            VStack(alignment: .leading, spacing: Spacing.xs) {
                Text(milestone.description)
                    .font(Font.BotTheme.bodyPrimary.weight(.semibold))
                    .foregroundColor(Color.BotTheme.textPrimary)
                    .fixedSize(horizontal: false, vertical: true)
                
                Text(milestone.criteria)
                    .font(Font.BotTheme.bodySecondary)
                    .foregroundColor(Color.BotTheme.textSecondary)
                    .fixedSize(horizontal: false, vertical: true)
            }
            
            Spacer(minLength: 0)
        }
        .padding(Spacing.md)
        .cardStyle(radius: Radius.lg)
    }
}
