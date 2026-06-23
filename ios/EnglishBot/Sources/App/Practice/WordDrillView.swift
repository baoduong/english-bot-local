import SwiftUI
import DesignSystem

public struct WordDrillView: View {
    @ObservedObject var viewModel: PracticeViewModel
    @ObservedObject var audioRecorder: AudioRecorder
    @ObservedObject var audioPlayer: AudioPlayer
    @State private var showMicDeniedAlert = false
    
    public var body: some View {
        VStack(spacing: Spacing.xl) {
            // Header
            VStack(spacing: Spacing.xs) {
                HStack {
                    Button("Stop Drill") {
                        Task { await viewModel.stop() }
                    }
                    .foregroundColor(Color.BotTheme.textSecondary)
                    
                    Spacer()
                    
                    Button(action: {
                        Task { await viewModel.skip() }
                    }) {
                        HStack(spacing: Spacing.xs) {
                            Image(systemName: "forward.fill")
                            Text("Bỏ qua từ này")
                        }
                    }
                    .foregroundColor(Color.BotTheme.scoreAverage)
                }
                
                if !viewModel.drillProgress.isEmpty {
                    Text(viewModel.drillProgress)
                        .font(Font.BotTheme.caption)
                        .foregroundColor(Color.BotTheme.textSecondary)
                        .frame(maxWidth: .infinity, alignment: .trailing)
                }
            }
            
            Spacer()
            
            // Content
            TappableWordView(word: viewModel.drillWord, viewModel: viewModel, audioPlayer: audioPlayer)
            
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
                
                if let coaching = viewModel.coachingHint {
                    CoachingHintView(
                        hint: coaching,
                        audioPlayer: audioPlayer,
                        wordAudioURL: viewModel.wordAudioURL,
                        apiClient: viewModel.apiClient,
                        userId: viewModel.userId,
                        onSkipRequested: { Task { await viewModel.skip() } },
                        onContinueRequested: { viewModel.coachingHint = nil }
                    )
                }
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
