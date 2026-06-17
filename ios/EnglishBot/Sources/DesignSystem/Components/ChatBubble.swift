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
    
    public var body: some View {
        HStack {
            if role == .user { Spacer() }
            
            Text(text)
                .font(Font.BotTheme.bodyPrimary)
                .foregroundColor(role == .user ? .white : Color.BotTheme.textPrimary)
                .padding(Spacing.md)
                .background(role == .user ? Color.BotTheme.chatUser : Color.BotTheme.chatAI)
                .clipShape(RoundedRectangle(cornerRadius: Spacing.md, style: .continuous))
                // Add tail
                .overlay(alignment: role == .user ? .bottomTrailing : .bottomLeading) {
                    Image(systemName: "triangle.fill")
                        .font(.system(size: 14))
                        .foregroundColor(role == .user ? Color.BotTheme.chatUser : Color.BotTheme.chatAI)
                        .rotationEffect(.degrees(role == .user ? -45 : 45))
                        .offset(x: role == .user ? 5 : -5, y: 5)
                }
            
            if role == .ai { Spacer() }
        }
        .padding(.horizontal, Spacing.md)
    }
}

#Preview {
    VStack(spacing: Spacing.md) {
        ChatBubble(text: "Hello, I want to practice English.", role: .user)
        ChatBubble(text: "Great! What is your current level and what are your goals?", role: .ai)
    }
}
