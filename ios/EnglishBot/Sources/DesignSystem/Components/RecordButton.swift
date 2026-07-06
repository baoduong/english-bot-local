import SwiftUI

public struct RecordButton: View {
    public let isRecording: Bool
    public let action: () -> Void

    @State private var isPressed = false

    public init(isRecording: Bool, action: @escaping () -> Void) {
        self.isRecording = isRecording
        self.action = action
    }

    public var body: some View {
        Button {
            Haptics.impact(isRecording ? .rigid : .medium)
            action()
        } label: {
            ZStack {
                // Breathing halo — only while recording.
                Circle()
                    .fill(Color.BotTheme.scorePoor.opacity(0.18))
                    .frame(width: 96, height: 96)
                    .scaleEffect(isRecording ? 1.15 : 0.85)
                    .opacity(isRecording ? 1 : 0)
                    .animation(
                        isRecording
                            ? .easeInOut(duration: 1.1).repeatForever(autoreverses: true)
                            : .easeOut(duration: 0.25),
                        value: isRecording
                    )

                // Main pad — gradient when idle, solid coral when recording.
                Circle()
                    .fill(
                        isRecording
                            ? AnyShapeStyle(Color.BotTheme.scorePoor)
                            : AnyShapeStyle(Color.BotTheme.accentGradient)
                    )
                    .frame(width: 68, height: 68)
                    .shadow(
                        color: (isRecording ? Color.BotTheme.scorePoor : Color.BotTheme.primary).opacity(0.35),
                        radius: 12, x: 0, y: 5
                    )

                // Icon: mic when idle, stop-square when recording.
                Group {
                    if isRecording {
                        RoundedRectangle(cornerRadius: 6, style: .continuous)
                            .fill(.white)
                            .frame(width: 26, height: 26)
                    } else {
                        Image(systemName: "mic.fill")
                            .font(.system(size: 26, weight: .semibold))
                            .foregroundStyle(.white)
                    }
                }
                .transition(.scale.combined(with: .opacity))
            }
            .scaleEffect(isPressed ? 0.94 : 1.0)
            .animation(.spring(response: 0.3, dampingFraction: 0.6), value: isPressed)
        }
        .buttonStyle(.plain)
        .simultaneousGesture(
            DragGesture(minimumDistance: 0)
                .onChanged { _ in isPressed = true }
                .onEnded { _ in isPressed = false }
        )
        .accessibilityLabel(isRecording ? "Stop recording" : "Start recording")
    }
}

#Preview {
    HStack(spacing: Spacing.xl) {
        RecordButton(isRecording: false, action: {})
        RecordButton(isRecording: true, action: {})
    }
    .padding()
}
