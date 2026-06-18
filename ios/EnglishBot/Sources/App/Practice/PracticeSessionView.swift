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
            
            // Content
            Text(viewModel.currentSentence)
                .font(Font.BotTheme.heading1)
                .foregroundColor(Color.BotTheme.textPrimary)
                .multilineTextAlignment(.center)
            
            Button(action: {
                if let u = viewModel.sampleAudioURL { audioPlayer.play(url: u) }
            }) {
                HStack {
                    Image(systemName: "speaker.wave.2.fill")
                    Text("Listen")
                }
                .padding()
                .background(Color.BotTheme.backgroundSecondary)
                .cornerRadius(Spacing.sm)
            }
            .foregroundColor(Color.BotTheme.primary)
            
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
        }
        .padding()
        .background(Color.BotTheme.backgroundSecondary)
        .cornerRadius(Spacing.md)
    }
}
