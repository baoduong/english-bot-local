import SwiftUI
import DesignSystem

public struct ProgressDashboardView: View {
    private let userId: String
    @StateObject private var viewModel: ProgressViewModel
    @State private var showResetConfirm: Bool = false
    
    public init(userId: String) {
        self.userId = userId
        _viewModel = StateObject(wrappedValue: ProgressViewModel(userId: userId))
    }
    
    public var body: some View {
        ScrollView {
            VStack(spacing: Spacing.xl) {
                if viewModel.isLoading {
                    VStack(alignment: .leading, spacing: Spacing.xl) {
                        HStack {
                            VStack(alignment: .leading, spacing: Spacing.xs) {
                                SkeletonView(cornerRadius: Radius.sm)
                                    .frame(width: 100, height: 16)
                                SkeletonView(cornerRadius: Radius.sm)
                                    .frame(width: 180, height: 32)
                            }
                            Spacer()
                            SkeletonView(cornerRadius: Radius.sm)
                                .frame(width: 60, height: 40)
                        }
                        SkeletonCard(lines: 2)
                        SkeletonCard(lines: 4)
                    }
                    .padding(.top, Spacing.lg)
                } else if let progress = viewModel.progress {
                    let hasData = progress.curriculum != nil || !progress.recentWordScores.isEmpty || (progress.phaseProgress != nil && !progress.phaseProgress!.strugglingWords.isEmpty)
                    
                    // Profile Header
                    HStack(alignment: .center) {
                        VStack(alignment: .leading, spacing: Spacing.xs) {
                            Text("Welcome back,")
                                .font(Font.BotTheme.bodySecondary)
                                .foregroundColor(Color.BotTheme.textSecondary)
                            Text(progress.user.displayName ?? shortUserName(progress.user.username))
                                .font(Font.BotTheme.heading1)
                                .foregroundColor(Color.BotTheme.textPrimary)
                                .lineLimit(1)
                                .truncationMode(.middle)
                        }
                        Spacer()
                        VStack(alignment: .trailing, spacing: Spacing.xs) {
                            HStack(spacing: 4) {
                                Image(systemName: "flame.fill")
                                    .foregroundColor(Color.BotTheme.primary)
                                Text("\(progress.user.streakCount)")
                                    .font(Font.BotTheme.numeric)
                                    .foregroundColor(Color.BotTheme.textPrimary)
                                Text("ngày")
                                    .font(Font.BotTheme.caption)
                                    .foregroundColor(Color.BotTheme.textSecondary)
                            }
                            ProgressChip(text: "Level \(progress.user.currentLevel)", systemIcon: "star.fill", tinted: true)
                        }
                        
                        // Reset Goal menu
                        if viewModel.isResettingGoal {
                            ProgressView()
                                .padding(.leading, Spacing.sm)
                        } else {
                            Menu {
                                Button(role: .destructive, action: {
                                    showResetConfirm = true
                                }) {
                                    Label("Đổi mục tiêu", systemImage: "arrow.triangle.2.circlepath")
                                }
                            } label: {
                                Image(systemName: "ellipsis.circle.fill")
                                    .font(.title)
                                    .foregroundColor(Color.BotTheme.primary)
                            }
                            .padding(.leading, Spacing.sm)
                        }
                    }
                    
                    if hasData {
                        // Current Curriculum Card
                        if let curriculum = progress.curriculum, let phase = progress.phaseProgress {
                            VStack(alignment: .leading, spacing: Spacing.md) {
                                Text("Phase \(curriculum.currentPhaseNumber): \(curriculum.goalTitle)")
                                    .font(Font.BotTheme.heading2)
                                    .foregroundColor(Color.BotTheme.textPrimary)
                                
                                ProgressChip(text: "\(phase.mastered)/\(phase.total) Mastered", systemIcon: "trophy.fill", tinted: true)
                                
                                HStack {
                                    Text("Avg Score:")
                                        .font(Font.BotTheme.caption)
                                        .foregroundColor(Color.BotTheme.textSecondary)
                                    Text("\(Int(phase.avgScore))")
                                        .font(Font.BotTheme.numeric)
                                        .foregroundColor(Color.BotTheme.textPrimary)
                                    Spacer()
                                }
                            }
                            .padding(Spacing.lg)
                            .frame(maxWidth: .infinity, alignment: .leading)
                            .cardStyle(radius: Radius.lg)
                        }
                        
                        // Recent Scores
                        if !progress.recentWordScores.isEmpty {
                            VStack(alignment: .leading, spacing: Spacing.md) {
                                Text("Recent Words")
                                    .font(Font.BotTheme.heading2)
                                    .foregroundColor(Color.BotTheme.textPrimary)
                                    .padding(.horizontal, Spacing.lg)
                                    .padding(.top, Spacing.lg)
                                
                                FlowLayout(spacing: Spacing.sm) {
                                    ForEach(progress.recentWordScores) { score in
                                        WordScorePill(word: score.word, score: score.accuracy)
                                    }
                                }
                                .padding(.horizontal, Spacing.lg)
                                .padding(.bottom, Spacing.lg)
                            }
                            .frame(maxWidth: .infinity, alignment: .leading)
                            .cardStyle(radius: Radius.lg)
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
                                            .font(Font.BotTheme.bodyEmphasis)
                                            .foregroundColor(Color.BotTheme.textPrimary)
                                        Spacer()
                                        Text("Consonants")
                                            .font(Font.BotTheme.caption)
                                            .foregroundColor(Color.BotTheme.textSecondary)
                                    }
                                    .padding(Spacing.md)
                                    .cardStyle(radius: Radius.md, fill: Color.BotTheme.backgroundTertiary)
                                }
                            }
                            .padding(Spacing.lg)
                            .frame(maxWidth: .infinity, alignment: .leading)
                            .cardStyle(radius: Radius.lg)
                        }
                    } else {
                        VStack(spacing: Spacing.md) {
                            Image(systemName: "chart.line.uptrend.xyaxis")
                                .font(.system(size: 48))
                                .foregroundColor(Color.BotTheme.primary)
                                .padding(.bottom, Spacing.sm)
                            
                            Text("Hành trình của bạn bắt đầu từ đây")
                                .font(Font.BotTheme.heading2)
                                .foregroundColor(Color.BotTheme.textPrimary)
                            
                            Text("Hãy hoàn thành bài học đầu tiên để theo dõi tiến độ và từ vựng của bạn.")
                                .font(Font.BotTheme.bodyPrimary)
                                .foregroundColor(Color.BotTheme.textSecondary)
                                .multilineTextAlignment(.center)
                        }
                        .padding(Spacing.xl)
                        .frame(maxWidth: .infinity)
                        .padding(.top, Spacing.xl)
                    }
                } else {
                    VStack(spacing: Spacing.md) {
                        Image(systemName: "chart.line.uptrend.xyaxis")
                                .font(.system(size: 48))
                                .foregroundColor(Color.BotTheme.primary)
                                .padding(.bottom, Spacing.sm)
                            
                        Text("Chưa có dữ liệu tiến độ")
                            .font(Font.BotTheme.heading2)
                            .foregroundColor(Color.BotTheme.textPrimary)
                        
                        Text("Hãy bắt đầu học để xem phân tích và gợi ý cải thiện.")
                            .font(Font.BotTheme.bodyPrimary)
                            .foregroundColor(Color.BotTheme.textSecondary)
                            .multilineTextAlignment(.center)
                    }
                    .padding(Spacing.xl)
                    .frame(maxWidth: .infinity)
                    .padding(.top, 100)
                }
            }
            .padding(Spacing.lg)
        }
        .background(Color.BotTheme.backgroundMain.ignoresSafeArea())
        .onAppear {
            Task { await viewModel.fetchProgress() }
        }
        .alert("Đổi mục tiêu học tập?", isPresented: $showResetConfirm) {
            Button("Huỷ", role: .cancel) {}
            Button("Đồng ý đổi", role: .destructive) {
                Task {
                    let ok = await viewModel.resetGoal()
                    if ok {
                        NotificationCenter.default.post(name: .goalReset, object: nil)
                    }
                }
            }
        } message: {
            Text("Lộ trình hiện tại sẽ được lưu trữ. Bạn sẽ bắt đầu onboarding để đặt mục tiêu mới. Lịch sử điểm số vẫn được giữ trong tài khoản của bạn.")
        }
        .alert("Lỗi", isPresented: Binding(
            get: { viewModel.error != nil },
            set: { if !$0 { viewModel.error = nil } }
        )) {
            Button("OK", role: .cancel) {}
        } message: {
            if let error = viewModel.error {
                Text(error)
            }
        }
    }
    
    private func shortUserName(_ raw: String) -> String {
        if raw.count > 20, raw.contains("-") {
            return "User \(raw.prefix(6))"
        }
        return raw
    }
}
