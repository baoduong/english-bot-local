import SwiftUI
import DesignSystem

public struct CoachingHintView: View {
    public let hint: CoachingHint
    @ObservedObject public var audioPlayer: AudioPlayer
    public let wordAudioURL: (String) -> URL?
    public let onSkipRequested: () -> Void
    public let onContinueRequested: () -> Void
    
    public init(
        hint: CoachingHint,
        audioPlayer: AudioPlayer,
        wordAudioURL: @escaping (String) -> URL?,
        onSkipRequested: @escaping () -> Void,
        onContinueRequested: @escaping () -> Void
    ) {
        self.hint = hint
        self.audioPlayer = audioPlayer
        self.wordAudioURL = wordAudioURL
        self.onSkipRequested = onSkipRequested
        self.onContinueRequested = onContinueRequested
    }
    
    public var body: some View {
        VStack(alignment: .leading, spacing: Spacing.md) {
            // Header
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
            
            // Message
            Text(hint.messageVi)
                .font(Font.BotTheme.bodyPrimary)
                .foregroundColor(Color.BotTheme.textPrimary)
                .multilineTextAlignment(.leading)
                .fixedSize(horizontal: false, vertical: true)
                .frame(maxWidth: .infinity, alignment: .leading)
            
            // Layout-specific content
            if hint.action == "scaffold" {
                scaffoldLayout
            } else if hint.action == "break_down" {
                breakDownLayout
            } else if hint.action == "skip_with_note" {
                skipWithNoteLayout
            }
            
            // Articulatory Tip (Common to most actions)
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
            
            // Action Button
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
                    .background(Color.BotTheme.primary)
                    .cornerRadius(Spacing.md)
            }
            .padding(.top, Spacing.sm)
        }
        .padding()
        .background(Color.BotTheme.primary.opacity(0.08))
        .cornerRadius(Spacing.md)
        .overlay(
            RoundedRectangle(cornerRadius: Spacing.md)
                .stroke(Color.BotTheme.primary, lineWidth: 1)
        )
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
                    .background(Color.BotTheme.backgroundMain)
                    .cornerRadius(Spacing.sm)
                    .overlay(
                        RoundedRectangle(cornerRadius: Spacing.sm)
                            .stroke(Color.BotTheme.primary.opacity(0.3), lineWidth: 1)
                    )
                }
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
                    ForEach(Array(hint.syllables.enumerated()), id: \.offset) { index, syllable in
                        HStack(spacing: Spacing.xs) {
                            Button(action: {
                                if let url = wordAudioURL(syllable) {
                                    audioPlayer.play(url: url)
                                }
                            }) {
                                VStack(spacing: 4) {
                                    Text(syllable)
                                        .font(Font.BotTheme.heading3)
                                        .foregroundColor(Color.BotTheme.primary)
                                    Image(systemName: "speaker.wave.2.fill")
                                        .font(.caption2)
                                        .foregroundColor(Color.BotTheme.primary)
                                }
                                .padding(.horizontal, Spacing.md)
                                .padding(.vertical, Spacing.sm)
                                .background(Color.BotTheme.backgroundMain)
                                .cornerRadius(Spacing.sm)
                                .overlay(
                                    RoundedRectangle(cornerRadius: Spacing.sm)
                                        .stroke(Color.BotTheme.primary.opacity(0.3), lineWidth: 1)
                                )
                            }
                            
                            if index < hint.syllables.count - 1 {
                                Image(systemName: "arrow.right")
                                    .foregroundColor(Color.BotTheme.textSecondary)
                                    .padding(.horizontal, 4)
                            }
                        }
                    }
                }
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
}