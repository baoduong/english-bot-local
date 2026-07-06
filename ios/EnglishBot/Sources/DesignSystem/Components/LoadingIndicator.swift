import SwiftUI

public struct LoadingIndicator: View {
    @State private var isAnimating = false

    public init() {}

    public var body: some View {
        HStack(spacing: Spacing.xs + 1) {
            ForEach(0..<3) { index in
                Circle()
                    .fill(Color.BotTheme.primary)
                    .frame(width: 9, height: 9)
                    .scaleEffect(isAnimating ? 1.0 : 0.45)
                    .opacity(isAnimating ? 1.0 : 0.35)
                    .animation(
                        .easeInOut(duration: 0.6)
                        .repeatForever()
                        .delay(Double(index) * 0.18),
                        value: isAnimating
                    )
            }
        }
        .padding(.horizontal, Spacing.md)
        .padding(.vertical, Spacing.sm + 2)
        .background(Color.BotTheme.chatAI)
        .clipShape(Capsule(style: .continuous))
        .onAppear { isAnimating = true }
    }
}

#Preview {
    LoadingIndicator()
        .padding()
        .background(Color.BotTheme.backgroundMain)
}
