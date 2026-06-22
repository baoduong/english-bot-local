import SwiftUI
import DesignSystem

public struct PracticeSessionView: View {
    private let userId: String
    @StateObject private var viewModel: PracticeViewModel
    @StateObject private var audioRecorder = AudioRecorder()
    @StateObject private var audioPlayer = AudioPlayer()
    
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
        .padding(Spacing.lg)
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
    }
}

private struct SentencePracticeView: View {
    @ObservedObject var viewModel: PracticeViewModel
    @ObservedObject var audioRecorder: AudioRecorder
    @ObservedObject var audioPlayer: AudioPlayer
    
    var body: some View {
        VStack(spacing: Spacing.xl) {
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
            
            Spacer()
            
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
                    .background(Color.BotTheme.backgroundSecondary)
                    .cornerRadius(Spacing.sm)
                }
                .foregroundColor(Color.BotTheme.primary)

                if let slowURL = viewModel.slowSampleAudioURL {
                    Button(action: {
                        audioPlayer.play(url: slowURL)
                    }) {
                        HStack {
                            Image(systemName: "tortoise.fill")
                            Text("Nghe chậm")
                        }
                        .padding()
                        .background(Color.BotTheme.backgroundSecondary)
                        .cornerRadius(Spacing.sm)
                    }
                    .foregroundColor(Color.BotTheme.primary)
                }
            }
            
            // Feedback Area
            if viewModel.state == .uploading {
                LoadingIndicator()
            } else if viewModel.state == .scored, let result = viewModel.scoreResult {
                feedbackView(result: result)
            } else {
                Spacer().frame(height: 100) // Placeholder
            }
            
            Spacer()
            
            // Record Button
            if viewModel.state == .scored {
                Button(action: {
                    Task { await viewModel.next() }
                }) {
                    Text(viewModel.nextAction?.action == "word_drill" ? "Start Word Drill" : "Next")
                        .font(Font.BotTheme.heading3)
                        .foregroundColor(.white)
                        .padding()
                        .frame(maxWidth: .infinity)
                        .background(Color.BotTheme.primary)
                        .cornerRadius(Spacing.md)
                }
            } else {
                RecordButton(isRecording: audioRecorder.isRecording) {
                    if audioRecorder.isRecording {
                        let url = audioRecorder.stopRecording()
                        Task { await viewModel.onRecordingStopped(url: url) }
                    } else {
                        do {
                            _ = try audioRecorder.startRecording()
                            viewModel.onRecordingStarted()
                        } catch {
                            print("Recording failed: \(error)")
                        }
                    }
                }
            }
        }
    }
    
    private func feedbackView(result: ScoringResult) -> some View {
        VStack(spacing: Spacing.md) {
            Text(result.passed ? "Great job!" : "Let's try again")
                .font(Font.BotTheme.heading3)
                .foregroundColor(result.passed ? Color.BotTheme.scoreExcellent : Color.BotTheme.scoreAverage)
            
            Text("Score: \(result.overallScore)")
                .font(Font.BotTheme.heading2)
                .foregroundColor(Color.BotTheme.textPrimary)
            
            FlowLayout(spacing: Spacing.sm) {
                ForEach(result.wordScores) { wordScore in
                    WordScorePill(word: wordScore.word, score: wordScore.accuracy)
                }
            }
            
            if !result.feedbackMessage.isEmpty {
                Text(result.feedbackMessage)
                    .font(Font.BotTheme.bodySecondary)
                    .foregroundColor(Color.BotTheme.textSecondary)
                    .multilineTextAlignment(.center)
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
        }
        .padding()
        .background(Color.BotTheme.backgroundSecondary)
        .cornerRadius(Spacing.md)
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
        HStack(alignment: .top, spacing: Spacing.sm) {
            Text(wordScore.word)
                .font(Font.BotTheme.bodyPrimary.weight(.semibold))
                .foregroundColor(.white)
                .padding(.horizontal, Spacing.sm)
                .padding(.vertical, Spacing.xs)
                .background(scoreColor)
                .cornerRadius(Spacing.sm)
            
            Text(wordScore.tip ?? "")
                .font(Font.BotTheme.bodySecondary)
                .foregroundColor(Color.BotTheme.textPrimary)
                .fixedSize(horizontal: false, vertical: true)
                .frame(maxWidth: .infinity, alignment: .leading)
        }
        .padding(Spacing.sm)
        .background(Color.BotTheme.backgroundMain)
        .cornerRadius(Spacing.sm)
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
