import SwiftUI
import DesignSystem

public struct OnboardingChatView: View {
    @StateObject private var viewModel: OnboardingViewModel
    @State private var inputText: String = ""
    
    public init(userId: String) {
        _viewModel = StateObject(wrappedValue: OnboardingViewModel(userId: userId))
    }
    
    public var body: some View {
        VStack(spacing: 0) {
            ScrollViewReader { proxy in
                ScrollView {
                    VStack(spacing: Spacing.md) {
                        ForEach(viewModel.messages) { message in
                            ChatBubble(text: message.content, role: message.role == "user" ? .user : .ai)
                                .id(message.turnNumber)
                        }
                        
                        if viewModel.isTyping {
                            HStack {
                                LoadingIndicator()
                                Spacer()
                            }
                            .padding(.horizontal, Spacing.md)
                            .id("typing")
                        }
                        
                        if let goal = viewModel.pendingGoal {
                            goalSynthesisCard(goal: goal)
                                .id("goal")
                        }
                    }
                    .padding(.vertical, Spacing.md)
                }
                .onChange(of: viewModel.messages.count) { _ in
                    scrollToBottom(proxy: proxy)
                }
                .onChange(of: viewModel.isTyping) { _ in
                    scrollToBottom(proxy: proxy)
                }
                .onChange(of: viewModel.pendingGoal != nil) { _ in
                    scrollToBottom(proxy: proxy)
                }
            }
            
            Divider()
            
            // Input Area
            HStack {
                TextField("Type a message...", text: $inputText)
                    .padding(Spacing.sm)
                    .background(Color.BotTheme.backgroundSecondary)
                    .cornerRadius(Spacing.sm)
                    .disabled(viewModel.isTyping || viewModel.pendingGoal != nil)
                
                Button(action: {
                    guard !inputText.isEmpty else { return }
                    let textToSend = inputText
                    inputText = ""
                    Task {
                        await viewModel.sendMessage(textToSend)
                    }
                }) {
                    Image(systemName: "paperplane.fill")
                        .font(.system(size: 20))
                        .foregroundColor(inputText.isEmpty ? Color.BotTheme.textTertiary : Color.BotTheme.primary)
                }
                .disabled(inputText.isEmpty || viewModel.isTyping || viewModel.pendingGoal != nil)
            }
            .padding(Spacing.md)
            .background(Color.BotTheme.backgroundMain)
        }
        .background(Color.BotTheme.backgroundMain)
        .navigationTitle("Onboarding")
        #if os(iOS)
        .navigationBarTitleDisplayMode(.inline)
        #endif
        .task {
            if viewModel.messages.isEmpty {
                await viewModel.start()
            }
        }
    }
    
    @ViewBuilder
    private func goalSynthesisCard(goal: GoalSynthesis) -> some View {
        VStack(alignment: .leading, spacing: Spacing.md) {
            Text("Suggested Goal")
                .font(Font.BotTheme.heading3)
                .foregroundColor(Color.BotTheme.textPrimary)
            
            Text(goal.goalTitle)
                .font(Font.BotTheme.bodyPrimary)
                .bold()
            
            Text(goal.goalDescription)
                .font(Font.BotTheme.bodySecondary)
                .foregroundColor(Color.BotTheme.textSecondary)
            
            HStack {
                ForEach(goal.keyThemes, id: \.self) { theme in
                    ProgressChip(text: theme)
                }
            }
            
            HStack(spacing: Spacing.md) {
                Button(action: {
                    Task { await viewModel.confirmGoal(accepted: false) }
                }) {
                    Text("Reject")
                        // .font(Font.BotTheme.button) // Doesn't exist, using caption instead
                        .font(Font.BotTheme.caption)
                        .foregroundColor(.red)
                        .frame(maxWidth: .infinity)
                        .padding(Spacing.sm)
                        .background(Color.red.opacity(0.1))
                        .cornerRadius(Spacing.sm)
                }
                
                Button(action: {
                    Task { await viewModel.confirmGoal(accepted: true) }
                }) {
                    Text("Confirm")
                        .font(Font.BotTheme.caption)
                        .foregroundColor(.white)
                        .frame(maxWidth: .infinity)
                        .padding(Spacing.sm)
                        .background(Color.BotTheme.primary)
                        .cornerRadius(Spacing.sm)
                }
            }
        }
        .padding(Spacing.md)
        .background(Color.BotTheme.backgroundSecondary)
        .cornerRadius(Spacing.md)
        .padding(.horizontal, Spacing.md)
    }
    
    private func scrollToBottom(proxy: ScrollViewProxy) {
        withAnimation {
            if viewModel.pendingGoal != nil {
                proxy.scrollTo("goal", anchor: .bottom)
            } else if viewModel.isTyping {
                proxy.scrollTo("typing", anchor: .bottom)
            } else if let last = viewModel.messages.last {
                proxy.scrollTo(last.turnNumber, anchor: .bottom)
            }
        }
    }
}
