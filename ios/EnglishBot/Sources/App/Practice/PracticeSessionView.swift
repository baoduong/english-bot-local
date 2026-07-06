import SwiftUI
import DesignSystem

public struct PracticeSessionView: View {
    private let userId: String
    @StateObject private var viewModel: PracticeViewModel
    @StateObject private var audioRecorder = AudioRecorder()
    @StateObject private var audioPlayer = AudioPlayer()
    @State private var showMicDeniedAlert = false
    
    public init(userId: String) {
        self.userId = userId
        _viewModel = StateObject(wrappedValue: PracticeViewModel(userId: userId))
    }
    
    public var body: some View {
        VStack(spacing: Spacing.xl) {
            if viewModel.isWordDrill {
                WordDrillView(viewModel: viewModel, audioRecorder: audioRecorder, audioPlayer: audioPlayer)
            } else {
                SentencePracticeView(viewModel: viewModel, audioRecorder: audioRecorder, audioPlayer: audioPlayer)
            }
        }
        .padding(.horizontal, Spacing.lg)
        .padding(.top, Spacing.lg)
        .padding(.bottom, 100)
        .background(Color.BotTheme.backgroundMain.ignoresSafeArea())
        .onChange(of: viewModel.currentSentence) { _ in
            audioPlayer.clearCache()
        }
        .onAppear {
            Task {
                await viewModel.startSession()
            }
            Task {
                _ = await audioRecorder.requestPermission()
            }
        }
        .onDisappear {
            viewModel.onViewDisappear()
        }
        .alert("Cần quyền micro", isPresented: $showMicDeniedAlert) {
            Button("Mở Cài đặt") {
                #if canImport(UIKit)
                if let url = URL(string: UIApplication.openSettingsURLString) {
                    UIApplication.shared.open(url)
                }
                #endif
            }
            Button("Đóng", role: .cancel) {}
        } message: {
            Text("Mở Cài đặt → English Bot → Microphone để cho phép ghi âm")
        }
    }
}

private struct SentencePracticeView: View {
    @ObservedObject var viewModel: PracticeViewModel
    @ObservedObject var audioRecorder: AudioRecorder
    @ObservedObject var audioPlayer: AudioPlayer
    @State private var showMicDeniedAlert = false
    
    var body: some View {
        Group {
            if viewModel.phaseComplete {
                phaseCompleteView
            } else {
                practiceContentView
            }
        }
    }

    private var phaseCompleteView: some View {
        VStack(spacing: Spacing.xl) {
            Text("🎉 Phase Complete!")
                .font(Font.BotTheme.display)
                .foregroundStyle(Color.BotTheme.accentGradient)

            Text("Bạn đã hoàn thành phase này!")
                .font(Font.BotTheme.bodyPrimary)
                .foregroundColor(Color.BotTheme.textSecondary)
                .multilineTextAlignment(.center)

            if let progress = viewModel.phaseProgress {
                VStack(spacing: Spacing.sm) {
                    Text("Điểm trung bình")
                        .font(Font.BotTheme.bodySecondary)
                        .foregroundColor(Color.BotTheme.textSecondary)
                    Text(String(format: "%.1f", progress.avgScore))
                        .font(Font.BotTheme.scoreLarge)
                        .foregroundColor(scoreColor(Int(progress.avgScore)))
                }
                .padding()
                .frame(maxWidth: .infinity)
                .cardStyle(radius: Radius.lg)
            }

            if viewModel.isAdvancingPhase {
                LoadingIndicator()
                Text("Đang tạo phase tiếp theo... (có thể mất 30-60 giây)")
                    .font(Font.BotTheme.bodySecondary)
                    .foregroundColor(Color.BotTheme.textSecondary)
                    .multilineTextAlignment(.center)
            } else {
                Button(action: { Task { await viewModel.advancePhase() } }) {
                    Text("Generate phase tiếp theo →")
                        .font(Font.BotTheme.heading3)
                        .foregroundColor(.white)
                        .padding()
                        .frame(maxWidth: .infinity)
                        .background(Color.BotTheme.accentGradient)
                        .cornerRadius(Radius.md)
                }
                .buttonStyle(.pressable)
                .disabled(viewModel.isAdvancingPhase)
            }

            if let errorMessage = viewModel.errorMessage {
                Text(errorMessage)
                    .font(Font.BotTheme.bodySecondary)
                    .foregroundColor(Color.BotTheme.scorePoor)
                    .multilineTextAlignment(.center)
            }
        }
        .padding()
    }

    private var practiceContentView: some View {
        VStack(spacing: 0) {
            // Header
            HStack {
                Button("Stop") {
                    Task { await viewModel.stop() }
                }
                .foregroundColor(Color.BotTheme.textSecondary)
                
                Spacer()
                
                Button("Skip") {
                    Task { await viewModel.skip() }
                }
                .foregroundColor(Color.BotTheme.textSecondary)
            }
            .padding(.bottom, Spacing.md)

            ScrollView {
                VStack(spacing: Spacing.xl) {
                    // Content - tappable words
                    let words = viewModel.currentSentence.split(separator: " ").map(String.init)
                    FlowLayout(spacing: Spacing.sm) {
                        ForEach(Array(words.enumerated()), id: \.offset) { _, word in
                            TappableWordView(word: word, viewModel: viewModel, audioPlayer: audioPlayer)
                        }
                    }
                    .frame(maxWidth: .infinity)

                    HStack(spacing: Spacing.md) {
                        Button(action: {
                            if let u = viewModel.sampleAudioURL { audioPlayer.play(url: u) }
                        }) {
                            HStack {
                                Image(systemName: "speaker.wave.2.fill")
                                Text("Nghe")
                            }
                            .padding()
                            .background(Color.BotTheme.backgroundTertiary)
                            .cornerRadius(Radius.md)
                        }
                        .foregroundColor(Color.BotTheme.primary)
                        .buttonStyle(.pressable)

                        if let slowURL = viewModel.slowSampleAudioURL {
                            Button(action: {
                                audioPlayer.play(url: slowURL)
                            }) {
                                HStack {
                                    Image(systemName: "tortoise.fill")
                                    Text("Nghe chậm")
                                }
                                .padding()
                                .background(Color.BotTheme.backgroundTertiary)
                                .cornerRadius(Radius.md)
                            }
                            .foregroundColor(Color.BotTheme.primary)
                            .buttonStyle(.pressable)
                        }
                    }

                    // Feedback Area
                    if viewModel.state == .uploading {
                        LoadingIndicator()
                    } else if viewModel.state == .scored, let result = viewModel.scoreResult {
                        feedbackView(result: result)
                    }
                }
                .padding(.vertical, Spacing.md)
            }

            actionButton
                .padding(.top, Spacing.md)
        }
    }

    private var actionButton: some View {
        Group {
            if viewModel.state == .scored {
                Button(action: {
                    Task { await viewModel.next() }
                }) {
                    Text(viewModel.nextAction?.action == "word_drill" ? "Start Word Drill" : "Next")
                        .font(Font.BotTheme.heading3)
                        .foregroundColor(.white)
                        .padding()
                        .frame(maxWidth: .infinity)
                        .background(Color.BotTheme.accentGradient)
                        .cornerRadius(Radius.md)
                }
                .buttonStyle(.pressable)
            } else if viewModel.state == .uploading {
                LoadingIndicator()
            } else {
                RecordButton(isRecording: audioRecorder.isRecording) {
                    if audioRecorder.isRecording {
                        let url = audioRecorder.stopRecording()
                        Task { await viewModel.onRecordingStopped(url: url) }
                    } else {
                        do {
                            _ = try audioRecorder.startRecording()
                            viewModel.onRecordingStarted()
                        } catch AudioRecorder.AudioRecorderError.permissionDenied {
                            showMicDeniedAlert = true
                        } catch {
                            print("Recording failed: \(error)")
                        }
                    }
                }
            }
        }
    }
    
    private struct HeaderInfo {
        let text: String
        let subtitle: String
        let color: Color
        let showTargetWords: Bool
    }
    
    private func headerForOutcome(result: ScoringResult, nextAction: NextActionHint?, consecutive: Int) -> HeaderInfo {
        let action = nextAction?.action ?? ""
        
        // Rule 1: Just mastered
        if action == "pass" && consecutive >= 2 {
            return HeaderInfo(text: "✅ Mastered!", subtitle: "Bạn đã hoàn thành câu này 2 lần liên tiếp!", color: Color.BotTheme.scoreExcellent, showTargetWords: false)
        }
        
        // Rule 2: First quality pass, need one more
        if action == "retry" && consecutive == 1 {
            return HeaderInfo(text: "🔥 Tốt! Còn 1 lần nữa", subtitle: "Đọc lại 1 lần nữa để hoàn thành (1/2)", color: Color.BotTheme.scoreAverage, showTargetWords: false)
        }
        
        // Rule 3: High overall but target words failed quality bar
        if action == "retry" && consecutive == 0 && result.overallScore >= 80 {
            return HeaderInfo(text: "⚠️ Cần đọc chuẩn target words", subtitle: "Điểm tổng tốt (\(result.overallScore)/100), nhưng câu này có từ trọng tâm chưa đạt. Tập trung vào những từ này:", color: Color.BotTheme.scoreAverage, showTargetWords: true)
        }
        
        // Rule 4: Going into word drill
        if action == "word_drill" {
            return HeaderInfo(text: "📚 Hãy luyện các từ yếu trước", subtitle: "Sau 2 lần chưa đạt — chuyển sang luyện từng từ. Bấm Start Word Drill bên dưới.", color: Color.BotTheme.scoreAverage, showTargetWords: false)
        }
        
        // Rule 5: Auto-advance after too many failures
        if action == "pass" && result.overallScore < 80 {
            return HeaderInfo(text: "👉 Bỏ qua câu này", subtitle: "Đã thử nhiều lần — quay lại câu này sau khi luyện thêm.", color: Color.BotTheme.textSecondary, showTargetWords: false)
        }
        
        // Rule 6: Regular retry (low score)
        if action == "retry" && result.overallScore < 80 {
            return HeaderInfo(text: "Thử lại nhé", subtitle: "Đọc chậm và rõ hơn câu này.", color: Color.BotTheme.scorePoor, showTargetWords: false)
        }
        
        // Fallback
        return HeaderInfo(
            text: result.passed ? "Tốt!" : "Thử lại nhé",
            subtitle: result.passed ? "Tiếp tục luyện tập câu này." : "Đọc chậm và rõ hơn câu này.",
            color: result.passed ? Color.BotTheme.scoreAverage : Color.BotTheme.scorePoor,
            showTargetWords: false
        )
    }
    
    private func scoreColor(_ score: Int) -> Color {
        if score >= 80 { return Color.BotTheme.scoreExcellent }
        if score >= 60 { return Color.BotTheme.scoreAverage }
        return Color.BotTheme.scorePoor
    }
    
    private func feedbackView(result: ScoringResult) -> some View {
        let header = headerForOutcome(result: result, nextAction: viewModel.nextAction, consecutive: viewModel.consecutivePasses)
        let failingTargetWords = result.wordScores.filter { $0.accuracy < 75 }
        
        return VStack(spacing: Spacing.md) {
            VStack(spacing: Spacing.xs) {
                Text(header.text)
                    .font(Font.BotTheme.heading3)
                    .foregroundColor(header.color)
                Text(header.subtitle)
                    .font(Font.BotTheme.bodySecondary)
                    .foregroundColor(Color.BotTheme.textSecondary)
                    .multilineTextAlignment(.center)
            }
            
            Text("Score: \(result.overallScore)")
                .font(Font.BotTheme.scoreLarge)
                .foregroundColor(scoreColor(result.overallScore))
            
            if header.showTargetWords && !failingTargetWords.isEmpty {
                VStack(alignment: .leading, spacing: Spacing.xs) {
                    Text("⚠️ Từ trọng tâm cần luyện:")
                        .font(Font.BotTheme.bodySecondary)
                        .foregroundColor(Color.BotTheme.textSecondary)
                    FlowLayout(spacing: Spacing.sm) {
                        ForEach(Array(failingTargetWords.enumerated()), id: \.offset) { _, ws in
                            Text(ws.word)
                                .font(Font.BotTheme.bodySecondary.weight(.semibold))
                                .foregroundColor(Color.BotTheme.scorePoor)
                                .padding(.horizontal, Spacing.sm)
                                .padding(.vertical, Spacing.xs)
                                .overlay(
                                    RoundedRectangle(cornerRadius: Radius.sm)
                                        .stroke(Color.BotTheme.scorePoor, lineWidth: 1.5)
                                )
                        }
                    }
                }
                .frame(maxWidth: .infinity, alignment: .leading)
            }
            
            if result.fluencyScore != nil || result.linkingScore != nil || result.prosodyScore != nil {
                VStack(spacing: Spacing.xs) {
                    FlowLayout(spacing: Spacing.sm) {
                        if let accuracy = Optional(result.overallScore) {
                            scoreChip(title: "🎯 Chính xác", score: accuracy)
                        }
                        if let f = result.fluencyScore {
                            scoreChip(title: "🌊 Trôi chảy", score: f)
                        }
                        if let l = result.linkingScore {
                            scoreChip(title: "🔗 Nối âm", score: l)
                        }
                        if let p = result.prosodyScore {
                            scoreChip(title: "🎵 Ngữ điệu", score: p)
                        }
                    }
                    if let pace = result.paceWpm {
                        Text(String(format: "📈 Tốc độ: %.0f wpm", pace))
                            .font(Font.BotTheme.caption)
                            .foregroundColor(Color.BotTheme.textSecondary)
                    }
                }
            }
            
            if viewModel.consecutivePasses < 2 || result.passed {
                if viewModel.consecutivePasses == 1 {
                    VStack(spacing: Spacing.xs) {
                        Text("🔥 Lần đạt liên tiếp: 1/2")
                            .font(Font.BotTheme.heading3)
                            .foregroundColor(Color.BotTheme.scoreAverage)
                        Text("Đọc lại 1 lần nữa để hoàn thành câu này")
                            .font(Font.BotTheme.bodySecondary)
                            .foregroundColor(Color.BotTheme.textPrimary)
                            .multilineTextAlignment(.center)
                        HStack(spacing: Spacing.sm) {
                            Circle().fill(Color.BotTheme.scoreAverage).frame(width: 12, height: 12)
                            Circle().stroke(Color.BotTheme.scoreAverage, lineWidth: 2).frame(width: 12, height: 12)
                        }
                    }
                    .padding()
                    .frame(maxWidth: .infinity)
                    .background(Color.BotTheme.scoreAverage.opacity(0.15))
                    .cornerRadius(Radius.md)
                } else if viewModel.consecutivePasses >= 2 {
                    Text("✅ 2/2 — Mastered!")
                        .font(Font.BotTheme.heading3)
                        .foregroundColor(Color.BotTheme.scoreExcellent)
                        .padding()
                        .frame(maxWidth: .infinity)
                        .background(Color.BotTheme.scoreExcellent.opacity(0.15))
                        .cornerRadius(Radius.md)
                }
            }
            
            FlowLayout(spacing: Spacing.sm) {
                ForEach(result.wordScores) { wordScore in
                    WordScorePill(word: wordScore.word, score: wordScore.accuracy)
                }
            }
            
            let weakScores = result.wordScores.filter { $0.accuracy < 80 }
            if !weakScores.isEmpty {
                VStack(alignment: .leading, spacing: Spacing.xs) {
                    ForEach(Array(weakScores.enumerated()), id: \.offset) { _, ws in
                        HStack(spacing: Spacing.sm) {
                            Image(systemName: "exclamationmark.triangle.fill")
                                .foregroundColor(Color.BotTheme.scoreAverage)
                            Text(ws.word)
                                .font(Font.BotTheme.bodyPrimary.weight(.semibold))
                                .foregroundColor(Color.BotTheme.textPrimary)
                            Text(":")
                                .foregroundColor(Color.BotTheme.textSecondary)
                            Text(result.engine.capitalized)
                                .font(Font.BotTheme.bodySecondary)
                                .foregroundColor(Color.BotTheme.textSecondary)
                            Text("\(ws.accuracy)/100")
                                .font(Font.BotTheme.bodyPrimary.weight(.semibold))
                                .foregroundColor(Color.BotTheme.textPrimary)
                            Spacer()
                        }
                        .padding(.horizontal, Spacing.sm)
                        .padding(.vertical, Spacing.xs)
                    }
                }
                .padding(.top, Spacing.xs)
            }
            
            // Tips for weak words
            let tipsAvailable = result.wordScores.filter { $0.accuracy < 80 && $0.tip != nil && !($0.tip ?? "").isEmpty }
            if !tipsAvailable.isEmpty {
                VStack(alignment: .leading, spacing: Spacing.sm) {
                    Text("💡 Mẹo phát âm")
                        .font(Font.BotTheme.heading3)
                        .foregroundColor(Color.BotTheme.textPrimary)
                        .padding(.top, Spacing.sm)
                    
                    ForEach(Array(tipsAvailable.enumerated()), id: \.offset) { _, score in
                        TipCard(wordScore: score)
                    }
                }
                .frame(maxWidth: .infinity, alignment: .leading)
            }
            
            if let coaching = viewModel.coachingHint {
                CoachingHintView(
                    hint: coaching,
                    audioPlayer: audioPlayer,
                    wordAudioURL: viewModel.wordAudioURL,
                    apiClient: viewModel.apiClient,
                    userId: viewModel.userId,
                    onSkipRequested: { Task { await viewModel.skip() } },
                    onContinueRequested: { viewModel.retryCurrentSentence() }
                )
                .padding(.top, Spacing.sm)
            }
        }
        .padding()
        .cardStyle(radius: Radius.lg)
        .onAppear {
            Haptics.forScore(result.overallScore)
        }
    }

    private func scoreChip(title: String, score: Int) -> some View {
        let color: Color
        if score >= 80 { color = Color.BotTheme.scoreExcellent }
        else if score >= 60 { color = Color.BotTheme.scoreAverage }
        else { color = Color.BotTheme.scorePoor }
        
        return Text("\(title): \(score)")
            .font(Font.BotTheme.caption)
            .foregroundColor(.white)
            .padding(.horizontal, Spacing.sm)
            .padding(.vertical, 4)
            .background(color)
            .cornerRadius(Radius.sm)
    }
}

private struct TipCard: View {
    let wordScore: WordScore
    
    private var scoreColor: Color {
        if wordScore.accuracy >= 80 { return Color.BotTheme.scoreExcellent }
        if wordScore.accuracy >= 60 { return Color.BotTheme.scoreAverage }
        return Color.BotTheme.scorePoor
    }
    
    var body: some View {
        VStack(alignment: .leading, spacing: Spacing.sm) {
            HStack(alignment: .center, spacing: Spacing.sm) {
                Text(wordScore.word)
                    .font(Font.BotTheme.bodyPrimary.weight(.semibold))
                    .foregroundColor(.white)
                    .padding(.horizontal, Spacing.sm)
                    .padding(.vertical, Spacing.xs)
                    .background(scoreColor)
                    .cornerRadius(Radius.sm)
                
                if let label = wordScore.errorLabel {
                    Text(label)
                        .font(Font.BotTheme.bodySecondary.weight(.semibold))
                        .foregroundColor(Color.BotTheme.textPrimary)
                        .fixedSize(horizontal: false, vertical: true)
                }
                Spacer(minLength: 0)
            }
            
            if let ipa = wordScore.targetIpa {
                VStack(alignment: .leading, spacing: Spacing.xs) {
                    HStack(spacing: Spacing.xs) {
                        Text("🎯 Đúng:")
                            .font(Font.BotTheme.bodySecondary)
                            .foregroundColor(Color.BotTheme.textSecondary)
                        Text(ipa)
                            .font(.system(.body, design: .monospaced))
                            .foregroundColor(Color.BotTheme.textPrimary)
                    }
                    
                    if let detected = wordScore.detectedIpa {
                        HStack(spacing: Spacing.xs) {
                            Text("🗣️ Bạn đọc:")
                                .font(Font.BotTheme.bodySecondary)
                                .foregroundColor(Color.BotTheme.textSecondary)
                            Text(detected)
                                .font(.system(.body, design: .monospaced))
                                .foregroundColor(!wordScore.missingPhonemes.isEmpty ? Color.BotTheme.scorePoor : Color.BotTheme.textPrimary)
                        }
                    }
                    
                    if !wordScore.missingPhonemes.isEmpty {
                        HStack(spacing: Spacing.xs) {
                            Text("⚠️ Thiếu âm:")
                                .font(Font.BotTheme.bodySecondary)
                                .foregroundColor(Color.BotTheme.scoreAverage)
                            Text(wordScore.missingPhonemes.joined(separator: ", "))
                                .font(Font.BotTheme.bodySecondary.weight(.semibold))
                                .foregroundColor(Color.BotTheme.scoreAverage)
                        }
                    }
                }
            }
            
            if let tip = wordScore.tip, !tip.isEmpty {
                Text(tip)
                    .font(Font.BotTheme.bodySecondary)
                    .foregroundColor(Color.BotTheme.textPrimary)
                    .fixedSize(horizontal: false, vertical: true)
            }
            
            if !wordScore.practiceExamples.isEmpty {
                HStack(alignment: .top, spacing: Spacing.xs) {
                    Text("📚 Luyện thêm:")
                        .font(Font.BotTheme.bodySecondary)
                        .foregroundColor(Color.BotTheme.textSecondary)
                    Text(wordScore.practiceExamples.joined(separator: ", "))
                        .font(Font.BotTheme.bodySecondary.weight(.semibold))
                        .foregroundColor(Color.BotTheme.primary)
                        .fixedSize(horizontal: false, vertical: true)
                }
            }
        }
        .padding(Spacing.md)
        .frame(maxWidth: .infinity, alignment: .leading)
        .cardStyle(radius: Radius.lg)
    }
}

public struct TappableWordView: View {
    let word: String
    @ObservedObject var viewModel: PracticeViewModel
    @ObservedObject var audioPlayer: AudioPlayer
    
    @State private var isTapped = false
    
    public var body: some View {
        Text(word)
            .font(Font.BotTheme.heading1)
            .foregroundColor(isTapped ? Color.BotTheme.primary : Color.BotTheme.textPrimary)
            .scaleEffect(isTapped ? 1.1 : 1.0)
            .onTapGesture {
                withAnimation(.easeInOut(duration: 0.15)) {
                    isTapped = true
                }
                if let url = viewModel.wordAudioURL(for: word) {
                    audioPlayer.play(url: url)
                }
                
                DispatchQueue.main.asyncAfter(deadline: .now() + 0.3) {
                    withAnimation(.easeInOut(duration: 0.15)) {
                        isTapped = false
                    }
                }
            }
    }
}
