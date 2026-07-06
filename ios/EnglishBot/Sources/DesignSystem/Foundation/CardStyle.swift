import SwiftUI

/// A consistent elevated-surface treatment for cards and panels.
///
/// Uses a warm-tinted shadow (not pure black), a soft hairline border for edge
/// definition, and a configurable corner radius so containers can be softer
/// than their inner elements. Shadows are kept small and low-opacity to stay
/// scroll-performant.
public struct CardStyle: ViewModifier {
    private let radius: CGFloat
    private let elevated: Bool
    private let fill: Color

    public init(radius: CGFloat = Radius.lg, elevated: Bool = true, fill: Color = Color.BotTheme.backgroundSecondary) {
        self.radius = radius
        self.elevated = elevated
        self.fill = fill
    }

    public func body(content: Content) -> some View {
        content
            .background(
                RoundedRectangle(cornerRadius: radius, style: .continuous)
                    .fill(fill)
            )
            .overlay(
                RoundedRectangle(cornerRadius: radius, style: .continuous)
                    .strokeBorder(Color.BotTheme.border.opacity(0.6), lineWidth: 0.5)
            )
            .shadow(
                color: elevated ? Color.BotTheme.shadowColor : .clear,
                radius: elevated ? 14 : 0,
                x: 0,
                y: elevated ? 6 : 0
            )
    }
}

public extension View {
    /// Applies the standard elevated card treatment.
    func cardStyle(radius: CGFloat = Radius.lg, elevated: Bool = true, fill: Color = Color.BotTheme.backgroundSecondary) -> some View {
        modifier(CardStyle(radius: radius, elevated: elevated, fill: fill))
    }
}
