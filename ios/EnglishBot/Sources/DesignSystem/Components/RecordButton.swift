import SwiftUI

public struct RecordButton: View {
    public let isRecording: Bool
    public let action: () -> Void
    
    public init(isRecording: Bool, action: @escaping () -> Void) {
        self.isRecording = isRecording
        self.action = action
    }
    
    public var body: some View {
        Button(action: action) {
            ZStack {
                Circle()
                    .fill(isRecording ? Color.red.opacity(0.2) : Color.BotTheme.chatUser.opacity(0.1))
                    .frame(width: 80, height: 80)
                    .scaleEffect(isRecording ? 1.2 : 1.0)
                    .animation(isRecording ? .easeInOut(duration: 1).repeatForever(autoreverses: true) : .default, value: isRecording)
                
                Circle()
                    .fill(isRecording ? Color.red : Color.BotTheme.chatUser)
                    .frame(width: 60, height: 60)
                
                if isRecording {
                    RoundedRectangle(cornerRadius: 4)
                        .fill(Color.white)
                        .frame(width: 24, height: 24)
                } else {
                    Image(systemName: "mic.fill")
                        .font(.title)
                        .foregroundColor(.white)
                }
            }
        }
        .buttonStyle(.plain)
    }
}

#Preview {
    HStack(spacing: Spacing.xl) {
        RecordButton(isRecording: false, action: {})
        RecordButton(isRecording: true, action: {})
    }
    .padding()
}
