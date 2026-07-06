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
                .overlay(Color.BotTheme.border)
            
            // Input Area
            HStack(spacing: Spacing.md) {
                TextField("Type a message...", text: $inputText)
                    .font(Font.BotTheme.bodyPrimary)
                    .padding(.horizontal, Spacing.md)
                    .padding(.vertical, 10)
                    .background(Color.BotTheme.backgroundTertiary)
                    .cornerRadius(Radius.md)
                    .overlay(
                        RoundedRectangle(cornerRadius: Radius.md)
                            .strokeBorder(Color.BotTheme.border, lineWidth: 0.5)
                    )
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
                        .font(.system(size: 18, weight: .semibold))
                        .foregroundColor(inputText.isEmpty ? Color.BotTheme.textTertiary : .white)
                        .frame(width: 40, height: 40)
                        .background(
                            Group {
                                if inputText.isEmpty {
                                    Color.BotTheme.backgroundTertiary
                                } else {
                                    Color.BotTheme.accentGradient
                                }
                            }
                        )
                        .clipShape(Circle())
                }
                .disabled(inputText.isEmpty || viewModel.isTyping || viewModel.pendingGoal != nil)
                .buttonStyle(.pressable)
            }
            .padding(Spacing.md)
            .background(Color.BotTheme.backgroundMain)
        }
        .overlay(alignment: .top) {
            if let error = viewModel.errorMessage {
                HStack(spacing: Spacing.sm) {
                    Image(systemName: "exclamationmark.triangle.fill")
                        .foregroundColor(Color.BotTheme.scorePoor)
                    Text(error)
                        .font(Font.BotTheme.bodySecondary)
                        .foregroundColor(Color.BotTheme.textPrimary)
                }
                .padding(.horizontal, Spacing.md)
                .padding(.vertical, Spacing.sm)
                .background(Color.BotTheme.backgroundSecondary)
                .cornerRadius(Radius.md)
                .overlay(
                    RoundedRectangle(cornerRadius: Radius.md)
                        .strokeBorder(Color.BotTheme.border.opacity(0.6), lineWidth: 0.5)
                )
                .shadow(color: Color.BotTheme.shadowColor, radius: 8, x: 0, y: 4)
                .padding(.horizontal, Spacing.md)
                .padding(.top, Spacing.md)
                .transition(.opacity.combined(with: .scale(scale: 0.96)))
            }
        }
        .animation(.easeOut(duration: 0.2), value: viewModel.errorMessage != nil)
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
                .foregroundColor(Color.BotTheme.textPrimary)
            
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
                        .font(Font.BotTheme.heading3)
                        .foregroundColor(Color.BotTheme.textSecondary)
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, Spacing.sm)
                        .background(Color.BotTheme.backgroundTertiary)
                        .cornerRadius(Radius.md)
                }
                .buttonStyle(.pressable)
                
                Button(action: {
                    Task { await viewModel.confirmGoal(accepted: true) }
                }) {
                    Text("Confirm")
                        .font(Font.BotTheme.heading3)
                        .foregroundColor(.white)
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, Spacing.sm)
                        .background(Color.BotTheme.accentGradient)
                        .cornerRadius(Radius.md)
                }
                .buttonStyle(.pressable)
            }
            .padding(.top, Spacing.xs)
        }
        .padding(Spacing.lg)
        .cardStyle()
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
