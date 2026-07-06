import SwiftUI

public enum ChatRole {
    case user
    case ai
}

public struct ChatBubble: View {
    public let text: String
    public let role: ChatRole

    public init(text: String, role: ChatRole) {
        self.text = text
        self.role = role
    }

    private var isUser: Bool { role == .user }

    public var body: some View {
        HStack {
            if isUser { Spacer(minLength: Spacing.xl) }

            Text(text)
                .font(Font.BotTheme.bodyPrimary)
                .foregroundColor(isUser ? .white : Color.BotTheme.textPrimary)
                .padding(.horizontal, Spacing.md)
                .padding(.vertical, Spacing.sm + 2)
                .background(
                    Group {
                        if isUser {
                            Color.BotTheme.accentGradient
                        } else {
                            Color.BotTheme.chatAI
                        }
                    }
                )
                // Asymmetric radius: the corner nearest the sender is tighter,
                // giving a natural "tail" without a hacky rotated triangle.
                .clipShape(BubbleShape(isUser: isUser))
                .overlay(
                    BubbleShape(isUser: isUser)
                        .strokeBorder(
                            isUser ? Color.clear : Color.BotTheme.border.opacity(0.5),
                            lineWidth: 0.5
                        )
                )
                .shadow(color: Color.BotTheme.shadowColor.opacity(0.6), radius: 4, x: 0, y: 2)
                .frame(maxWidth: .infinity, alignment: isUser ? .trailing : .leading)

            if !isUser { Spacer(minLength: Spacing.xl) }
        }
        .padding(.horizontal, Spacing.md)
    }
}

/// A rounded-rectangle bubble whose bottom corner on the sender's side is
/// tightened to imply a speech tail.
private struct BubbleShape: InsettableShape {
    let isUser: Bool
    var inset: CGFloat = 0

    func path(in rect: CGRect) -> Path {
        let r = rect.insetBy(dx: inset, dy: inset)
        let big: CGFloat = 18
        let small: CGFloat = 6

        // Per-corner radii, built manually so it works on iOS 16.0.
        let tl = big
        let tr = big
        let bl: CGFloat = isUser ? big : small
        let br: CGFloat = isUser ? small : big

        var path = Path()
        path.move(to: CGPoint(x: r.minX + tl, y: r.minY))
        path.addLine(to: CGPoint(x: r.maxX - tr, y: r.minY))
        path.addArc(center: CGPoint(x: r.maxX - tr, y: r.minY + tr),
                    radius: tr, startAngle: .degrees(-90), endAngle: .degrees(0), clockwise: false)
        path.addLine(to: CGPoint(x: r.maxX, y: r.maxY - br))
        path.addArc(center: CGPoint(x: r.maxX - br, y: r.maxY - br),
                    radius: br, startAngle: .degrees(0), endAngle: .degrees(90), clockwise: false)
        path.addLine(to: CGPoint(x: r.minX + bl, y: r.maxY))
        path.addArc(center: CGPoint(x: r.minX + bl, y: r.maxY - bl),
                    radius: bl, startAngle: .degrees(90), endAngle: .degrees(180), clockwise: false)
        path.addLine(to: CGPoint(x: r.minX, y: r.minY + tl))
        path.addArc(center: CGPoint(x: r.minX + tl, y: r.minY + tl),
                    radius: tl, startAngle: .degrees(180), endAngle: .degrees(270), clockwise: false)
        path.closeSubpath()
        return path
    }

    func inset(by amount: CGFloat) -> some InsettableShape {
        var copy = self
        copy.inset += amount
        return copy
    }
}

#Preview {
    VStack(spacing: Spacing.md) {
        ChatBubble(text: "Hello, I want to practice English.", role: .user)
        ChatBubble(text: "Great! What is your current level and what are your goals?", role: .ai)
    }
    .padding(.vertical)
    .background(Color.BotTheme.backgroundMain)
}
