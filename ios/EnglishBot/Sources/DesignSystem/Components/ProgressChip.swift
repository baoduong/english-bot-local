import SwiftUI

public struct ProgressChip: View {
    public let text: String
    public let icon: String?
    
    public init(text: String, icon: String? = nil) {
        self.text = text
        self.icon = icon
    }
    
    public var body: some View {
        HStack(spacing: Spacing.xs) {
            if let icon = icon {
                Text(icon)
            }
            Text(text)
                .font(Font.BotTheme.caption)
                .foregroundColor(Color.BotTheme.textSecondary)
        }
        .padding(.horizontal, Spacing.sm)
        .padding(.vertical, Spacing.xs)
        .background(Color.BotTheme.backgroundSecondary)
        .clipShape(Capsule())
        .overlay(
            Capsule()
                .stroke(Color.BotTheme.border, lineWidth: 1)
        )
    }
}

#Preview {
    HStack {
        ProgressChip(text: "Week 2 · Code Reviews · 3/12", icon: "📍")
        ProgressChip(text: "Phase 1 Complete")
    }
    .padding()
}
