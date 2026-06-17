import SwiftUI

public struct LoadingIndicator: View {
    @State private var isAnimating = false
    
    public init() {}
    
    public var body: some View {
        HStack(spacing: Spacing.xs) {
            ForEach(0..<3) { index in
                Circle()
                    .fill(Color.BotTheme.textSecondary)
                    .frame(width: 8, height: 8)
                    .scaleEffect(isAnimating ? 1.0 : 0.5)
                    .opacity(isAnimating ? 1.0 : 0.3)
                    .animation(
                        .easeInOut(duration: 0.6)
                        .repeatForever()
                        .delay(Double(index) * 0.2),
                        value: isAnimating
                    )
            }
        }
        .padding(Spacing.md)
        .background(Color.BotTheme.chatAI)
        .clipShape(RoundedRectangle(cornerRadius: Spacing.md, style: .continuous))
        .onAppear {
            isAnimating = true
        }
    }
}

#Preview {
    LoadingIndicator()
        .padding()
}
