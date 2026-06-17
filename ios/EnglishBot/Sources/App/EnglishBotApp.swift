import SwiftUI
import DesignSystem

/// Root navigation entry point for the English Learning iOS app.
/// Routes between onboarding, curriculum, practice, and progress screens
/// based on persisted user state.
public struct EnglishBotApp: View {
    @AppStorage("userId") private var userId: String = UUID().uuidString
    @AppStorage("onboardingCompleted") private var onboardingCompleted: Bool = false
    @State private var showingPractice: Bool = false
    @State private var showingProgress: Bool = false
    
    public init() {}
    
    public var body: some View {
        NavigationView {
            if !onboardingCompleted {
                OnboardingChatView(userId: userId)
                    .onReceive(NotificationCenter.default.publisher(for: .onboardingConfirmed)) { _ in
                        onboardingCompleted = true
                    }
            } else {
                CurriculumView(userId: userId)
                    .toolbar {
                        ToolbarItem(placement: .automatic) {
                            Button(action: { showingProgress = true }) {
                                Image(systemName: "chart.bar.fill")
                            }
                        }
                        ToolbarItem(placement: .automatic) {
                            Button(action: { showingPractice = true }) {
                                Image(systemName: "mic.fill")
                            }
                        }
                    }
                    .sheet(isPresented: $showingPractice) {
                        NavigationView {
                            PracticeSessionView()
                                .toolbar {
                                    ToolbarItem(placement: .cancellationAction) {
                                        Button("Done") { showingPractice = false }
                                    }
                                }
                        }
                    }
                    .sheet(isPresented: $showingProgress) {
                        NavigationView {
                            ProgressDashboardView()
                                .toolbar {
                                    ToolbarItem(placement: .cancellationAction) {
                                        Button("Done") { showingProgress = false }
                                    }
                                }
                        }
                    }
            }
        }
    }
}

extension Notification.Name {
    static let onboardingConfirmed = Notification.Name("onboardingConfirmed")
}
