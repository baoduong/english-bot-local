import SwiftUI
import DesignSystem

public struct CoachingHintView: View {
    public let hint: CoachingHint
    @ObservedObject public var audioPlayer: AudioPlayer
    public let wordAudioURL: (String) -> URL?
    public let apiClient: APIClient
    public let userId: String
    public let onSkipRequested: () -> Void
    public let onContinueRequested: () -> Void

    @StateObject private var scratchRecorder = AudioRecorder()
    @State private var scratchResult: ScratchScoringResult?
    @State private var isScoring = false
    @State private var scratchErrorMessage: String?
    @State private var breakDownIndex = 0
    @State private var currentScratchTargetOverride: String?

    public init(
        hint: CoachingHint,
        audioPlayer: AudioPlayer,
        wordAudioURL: @escaping (String) -> URL?,
        apiClient: APIClient,
        userId: String,
        onSkipRequested: @escaping () -> Void,
        onContinueRequested: @escaping () -> Void
    ) {
        self.hint = hint
        self.audioPlayer = audioPlayer
        self.wordAudioURL = wordAudioURL
        self.apiClient = apiClient
        self.userId = userId
        self.onSkipRequested = onSkipRequested
        self.onContinueRequested = onContinueRequested
    }

    public var body: some View {
        VStack(alignment: .leading, spacing: Spacing.md) {
            HStack {
                Text("🤖 Coach AI")
                    .font(Font.BotTheme.heading3)
                    .foregroundColor(Color.BotTheme.primary)
                Spacer()
                Text("Lần thử: \(hint.attemptCount)/\(hint.maxAttempts)")
                    .font(Font.BotTheme.caption)
                    .foregroundColor(Color.BotTheme.textSecondary)
            }

            Divider()
                .background(Color.BotTheme.primary.opacity(0.3))

            Text(hint.messageVi)
                .font(Font.BotTheme.bodyPrimary)
                .foregroundColor(Color.BotTheme.textPrimary)
                .multilineTextAlignment(.leading)
                .fixedSize(horizontal: false, vertical: true)
                .frame(maxWidth: .infinity, alignment: .leading)

            if hint.action == "scaffold" {
                scaffoldLayout
            } else if hint.action == "break_down" {
                breakDownLayout
            } else if hint.action == "skip_with_note" {
                skipWithNoteLayout
            }

            if let tip = hint.articulatoryTipVi, !tip.isEmpty {
                HStack(alignment: .top, spacing: Spacing.xs) {
                    Text("💡")
                    Text(tip)
                        .font(Font.BotTheme.bodySecondary)
                        .foregroundColor(Color.BotTheme.textSecondary)
                        .fixedSize(horizontal: false, vertical: true)
                        .frame(maxWidth: .infinity, alignment: .leading)
                }
                .padding(.top, Spacing.xs)
            }

            Button(action: {
                if hint.action == "skip_with_note" {
                    onSkipRequested()
                } else {
                    onContinueRequested()
                }
            }) {
                Text(actionButtonText)
                    .font(Font.BotTheme.heading3)
                    .foregroundColor(.white)
                    .padding()
                    .frame(maxWidth: .infinity)
                    .background(Color.BotTheme.accentGradient)
                    .cornerRadius(Radius.md)
            }
            .buttonStyle(.pressable)
            .padding(.top, Spacing.sm)
        }
        .padding()
        .cardStyle(radius: Radius.lg)
        .onChange(of: hint.action) { _ in resetScratchFlow() }
        .onChange(of: hint.scaffoldWord) { _ in resetScratchFlow() }
        .onChange(of: hint.syllables) { _ in resetScratchFlow() }
    }

    private var actionButtonText: String {
        switch hint.action {
        case "scaffold": return "Tôi đã đọc được, thử lại từ gốc"
        case "skip_with_note": return "Bỏ qua, quay lại sau"
        default: return "Đã hiểu, thử lại"
        }
    }

    private var scaffoldLayout: some View {
        VStack(alignment: .leading, spacing: Spacing.sm) {
            Text("🪜 Hãy luyện từ này trước:")
                .font(Font.BotTheme.bodySecondary.weight(.semibold))
                .foregroundColor(Color.BotTheme.textPrimary)

            if let scaffoldWord = hint.scaffoldWord {
                Button(action: {
                    if let url = wordAudioURL(scaffoldWord) {
                        audioPlayer.play(url: url)
                    }
                }) {
                    VStack(spacing: Spacing.xs) {
                        Text(scaffoldWord)
                            .font(Font.BotTheme.heading1)
                            .foregroundColor(Color.BotTheme.primary)

                        HStack(spacing: 4) {
                            Image(systemName: "speaker.wave.2.fill")
                            Text("Nghe phát âm")
                        }
                        .font(Font.BotTheme.caption)
                        .foregroundColor(Color.BotTheme.primary)
                    }
                    .padding()
                    .frame(maxWidth: .infinity)
                    .background(Color.BotTheme.backgroundTertiary)
                    .cornerRadius(Radius.md)
                }
                .buttonStyle(.pressable)

                scratchPracticeSection(target: scaffoldWord, prompt: "Thử ghi âm '\(scaffoldWord)'")
            }

            if let reason = hint.scaffoldReasonVi, !reason.isEmpty {
                HStack(alignment: .top, spacing: Spacing.xs) {
                    Text("💭")
                    Text(reason)
                        .font(Font.BotTheme.bodySecondary)
                        .foregroundColor(Color.BotTheme.textSecondary)
                        .fixedSize(horizontal: false, vertical: true)
                        .frame(maxWidth: .infinity, alignment: .leading)
                }
            }
        }
    }

    private var breakDownLayout: some View {
        VStack(alignment: .leading, spacing: Spacing.sm) {
            Text("🧩 Luyện từng phần:")
                .font(Font.BotTheme.bodySecondary.weight(.semibold))
                .foregroundColor(Color.BotTheme.textPrimary)

            if !hint.syllables.isEmpty {
                FlowLayout(spacing: Spacing.sm) {
                    ForEach(Array(breakDownTargets.enumerated()), id: \.offset) { index, syllable in
                        HStack(spacing: Spacing.xs) {
                            Button(action: {
                                if let url = wordAudioURL(syllable) {
                                    audioPlayer.play(url: url)
                                }
                            }) {
                                VStack(spacing: 4) {
                                    Text(syllable)
                                        .font(Font.BotTheme.heading3)
                                        .foregroundColor(index == breakDownIndex ? Color.BotTheme.primary : Color.BotTheme.textSecondary)
                                    Image(systemName: "speaker.wave.2.fill")
                                        .font(.caption2)
                                        .foregroundColor(index == breakDownIndex ? Color.BotTheme.primary : Color.BotTheme.textSecondary)
                                }
                                .padding(.horizontal, Spacing.md)
                                .padding(.vertical, Spacing.sm)
                                .background(index == breakDownIndex ? Color.BotTheme.primary.opacity(0.1) : Color.BotTheme.backgroundTertiary)
                                .cornerRadius(Radius.sm)
                            }
                            .buttonStyle(.pressable)

                            if index < breakDownTargets.count - 1 {
                                Image(systemName: "arrow.right")
                                    .foregroundColor(Color.BotTheme.textSecondary)
                                    .padding(.horizontal, 4)
                            }
                        }
                    }
                }

                scratchPracticeSection(
                    target: currentScratchTarget,
                    prompt: "Thử ghi âm: \(currentScratchTarget)",
                    helperText: breakDownProgressText
                )
            }
        }
    }

    private var skipWithNoteLayout: some View {
        VStack(alignment: .leading, spacing: Spacing.sm) {
            if let reason = hint.skipReasonVi, !reason.isEmpty {
                HStack(alignment: .top, spacing: Spacing.xs) {
                    Text("💭")
                    Text(reason)
                        .font(Font.BotTheme.bodySecondary)
                        .foregroundColor(Color.BotTheme.textSecondary)
                        .fixedSize(horizontal: false, vertical: true)
                        .frame(maxWidth: .infinity, alignment: .leading)
                }
            }
        }
    }

    private var breakDownTargets: [String] {
        guard let scaffoldWord = hint.scaffoldWord, !scaffoldWord.isEmpty else {
            return hint.syllables
        }
        return hint.syllables + [scaffoldWord]
    }

    private var currentScratchTarget: String {
        if let override = currentScratchTargetOverride, !override.isEmpty {
            return override
        }
        if hint.action == "break_down" {
            return breakDownTargets.indices.contains(breakDownIndex) ? breakDownTargets[breakDownIndex] : breakDownTargets.last ?? ""
        }
        return hint.scaffoldWord ?? ""
    }

    private var breakDownProgressText: String? {
        guard hint.action == "break_down", !breakDownTargets.isEmpty else { return nil }
        let label = breakDownIndex == breakDownTargets.count - 1 ? "từ hoàn chỉnh" : "âm tiết \(breakDownIndex + 1)/\(breakDownTargets.count - 1)"
        return "Đang luyện: \(label)"
    }

    @ViewBuilder
    private func scratchPracticeSection(target: String, prompt: String, helperText: String? = nil) -> some View {
        if !target.isEmpty {
            VStack(alignment: .leading, spacing: Spacing.sm) {
                if let helperText, !helperText.isEmpty {
                    Text(helperText)
                        .font(Font.BotTheme.caption)
                        .foregroundColor(Color.BotTheme.textSecondary)
                }

                HStack(spacing: Spacing.md) {
                    RecordButton(isRecording: scratchRecorder.isRecording) {
                        handleScratchRecordTap(for: target)
                    }

                    VStack(alignment: .leading, spacing: Spacing.xs) {
                        Text(scratchRecorder.isRecording ? "Đang ghi âm: \(target)" : "🎙 \(prompt)")
                            .font(Font.BotTheme.bodyPrimary.weight(.semibold))
                            .foregroundColor(Color.BotTheme.textPrimary)
                        Text("Bấm để bắt đầu, bấm lần nữa để chấm điểm ngay")
                            .font(Font.BotTheme.caption)
                            .foregroundColor(Color.BotTheme.textSecondary)
                    }
                }

                if isScoring {
                    HStack(spacing: Spacing.sm) {
                        ProgressView()
                        Text("Đang chấm phát âm...")
                            .font(Font.BotTheme.bodySecondary)
                            .foregroundColor(Color.BotTheme.textSecondary)
                    }
                }

                if let result = scratchResult {
                    scratchResultView(result)
                }

                if let scratchErrorMessage, !scratchErrorMessage.isEmpty {
                    Text(scratchErrorMessage)
                        .font(Font.BotTheme.bodySecondary)
                        .foregroundColor(Color.BotTheme.scorePoor)
                }

                if scratchResult != nil {
                    Button("Thử lại") {
                        clearScratchResult()
                    }
                    .font(Font.BotTheme.bodySecondary.weight(.semibold))
                    .foregroundColor(Color.BotTheme.primary)
                }
            }
            .padding(.top, Spacing.xs)
        }
    }

    @ViewBuilder
    private func scratchResultView(_ result: ScratchScoringResult) -> some View {
        let tone = scratchTone(for: result.overallScore)

        VStack(alignment: .leading, spacing: Spacing.sm) {
            HStack(spacing: Spacing.sm) {
                Image(systemName: tone.icon)
                    .foregroundColor(tone.color)
                Text("\(result.overallScore)/100 — \(tone.message)")
                    .font(Font.BotTheme.bodyPrimary.weight(.semibold))
                    .foregroundColor(tone.color)
            }

            if !result.wordScores.isEmpty {
                FlowLayout(spacing: Spacing.sm) {
                    ForEach(result.wordScores) { score in
                        WordScorePill(word: score.word, score: score.accuracy)
                    }
                }
            }
        }
        .padding()
        .frame(maxWidth: .infinity, alignment: .leading)
        .cardStyle(radius: Radius.lg, elevated: false, fill: tone.color.opacity(0.12))
        .onAppear {
            Haptics.forScore(result.overallScore)
        }
    }

    private func handleScratchRecordTap(for target: String) {
        if scratchRecorder.isRecording {
            let url = scratchRecorder.stopRecording()
            guard let url else { return }
            currentScratchTargetOverride = target
            Task {
                await submitScratchRecording(url: url, target: target)
            }
            return
        }

        scratchErrorMessage = nil
        do {
            _ = try scratchRecorder.startRecording()
        } catch {
            scratchErrorMessage = error.localizedDescription
        }
    }

    private func submitScratchRecording(url: URL, target: String) async {
        isScoring = true
        scratchErrorMessage = nil
        defer {
            isScoring = false
            try? FileManager.default.removeItem(at: url)
        }

        do {
            let result = try await apiClient.scoreScratch(userId: userId, audioURL: url, targetText: target)
            scratchResult = result
            if hint.action == "break_down", result.passed, breakDownIndex < breakDownTargets.count - 1 {
                breakDownIndex += 1
                clearScratchResult(keepTarget: false)
            }
        } catch {
            scratchErrorMessage = error.localizedDescription
        }
    }

    private func scratchTone(for score: Int) -> (icon: String, message: String, color: Color) {
        if score >= 80 {
            return ("checkmark.circle.fill", "Tốt lắm!", Color.BotTheme.scoreExcellent)
        }
        if score >= 60 {
            return ("exclamationmark.circle.fill", "Khá rồi — đọc lại nhé", Color.BotTheme.scoreAverage)
        }
        return ("xmark.circle.fill", "Chưa đúng — nghe lại audio mẫu rồi thử lại", Color.BotTheme.scorePoor)
    }

    private func clearScratchResult(keepTarget: Bool = true) {
        scratchResult = nil
        scratchErrorMessage = nil
        if !keepTarget {
            currentScratchTargetOverride = nil
        }
    }

    private func resetScratchFlow() {
        scratchResult = nil
        scratchErrorMessage = nil
        isScoring = false
        breakDownIndex = 0
        currentScratchTargetOverride = nil
    }
}
