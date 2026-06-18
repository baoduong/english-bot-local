import SwiftUI
import DesignSystem

public struct WordDrillView: View {
    @ObservedObject var viewModel: PracticeViewModel
    @ObservedObject var audioRecorder: AudioRecorder
    @ObservedObject var audioPlayer: AudioPlayer
    
    public var body: some View {
        VStack(spacing: Spacing.xl) {
            // Header
            HStack {
                Button("Stop Drill") {
                    Task { await viewModel.stop() }
                }
                .foregroundColor(Color.BotTheme.textSecondary)
                
                Spacer()
                
                Text(viewModel.drillProgress)
                    .font(Font.BotTheme.caption)
                    .foregroundColor(Color.BotTheme.textSecondary)
            }
            
            Spacer()
            
            // Content
            Text(viewModel.drillWord)
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
                VStack(spacing: Spacing.sm) {
                    if let wordScore = result.wordScores.first(where: { $0.word == viewModel.drillWord }) {
                        WordScorePill(word: wordScore.word, score: wordScore.accuracy)
                    }
                    if !result.feedbackMessage.isEmpty {
                        Text(result.feedbackMessage)
                            .font(Font.BotTheme.bodySecondary)
                            .foregroundColor(Color.BotTheme.textSecondary)
                            .multilineTextAlignment(.center)
                    }
                }
                .padding()
                .background(Color.BotTheme.backgroundSecondary)
                .cornerRadius(Spacing.md)
            } else {
                Spacer().frame(height: 100) // Placeholder
            }
            
            Spacer()
            
            // Record Button
            if viewModel.state == .scored {
                Button(action: {
                    Task { await viewModel.next() }
                }) {
                    Text("Next")
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
}
