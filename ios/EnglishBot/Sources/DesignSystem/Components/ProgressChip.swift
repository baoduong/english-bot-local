import SwiftUI

public struct ProgressChip: View {
    public let text: String
    public let systemIcon: String?
    public let tinted: Bool

    public init(text: String, systemIcon: String? = nil, tinted: Bool = false) {
        self.text = text
        self.systemIcon = systemIcon
        self.tinted = tinted
    }

    /// Back-compat initializer for existing call sites passing an emoji `icon`.
    public init(text: String, icon: String?) {
        self.text = icon.map { "\($0) \(text)" } ?? text
        self.systemIcon = nil
        self.tinted = true
    }

    public var body: some View {
        HStack(spacing: Spacing.xs) {
            if let systemIcon {
                Image(systemName: systemIcon)
                    .font(.caption2.weight(.semibold))
            }
            Text(text)
                .font(Font.BotTheme.caption)
        }
        .foregroundColor(tinted ? Color.BotTheme.primary : Color.BotTheme.textSecondary)
        .padding(.horizontal, Spacing.sm + 2)
        .padding(.vertical, Spacing.xs + 1)
        .background(
            Capsule(style: .continuous)
                .fill(tinted ? Color.BotTheme.accentSoft : Color.BotTheme.backgroundTertiary)
        )
        .overlay(
            Capsule(style: .continuous)
                .strokeBorder(
                    tinted ? Color.BotTheme.primary.opacity(0.25) : Color.BotTheme.border.opacity(0.6),
                    lineWidth: 0.5
                )
        )
    }
}

#Preview {
    HStack {
        ProgressChip(text: "Week 2 · Code Reviews · 3/12", icon: "📍")
        ProgressChip(text: "Phase 1 Complete", systemIcon: "checkmark.seal.fill", tinted: true)
    }
    .padding()
    .background(Color.BotTheme.backgroundMain)
}
