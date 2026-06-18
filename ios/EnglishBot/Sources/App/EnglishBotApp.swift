import SwiftUI
import DesignSystem

// MARK: - App-wide Notification Names

public extension Notification.Name {
    static let onboardingConfirmed = Notification.Name("eb.onboardingConfirmed")
}

// MARK: - Navigation Route Token

enum NavigationRoute: Hashable {
    case practice
    case progress
}

// MARK: - EnglishBotApp (Root View)

public struct EnglishBotApp: View {
    @AppStorage("eb_userId") private var userId: String = ""
    @AppStorage("eb_onboardingDone") private var onboardingDone: Bool = false
    @AppStorage("eb_activeTab") private var activeTab: Int = 0
    @State private var onboardingNavigated: Bool = false

    public init() {}

    public var body: some View {
        Group {
            if userId.isEmpty {
                Color.BotTheme.backgroundMain
                    .ignoresSafeArea()
                    .onAppear { userId = UUID().uuidString }
            } else if !onboardingDone {
                onboardingFlow
            } else {
                mainTabView
            }
        }
    }

    // MARK: - Onboarding Flow

    private var onboardingFlow: some View {
        NavigationStack {
            OnboardingChatView(userId: userId)
                .onReceive(
                    NotificationCenter.default.publisher(for: .onboardingConfirmed)
                ) { _ in
                    onboardingDone = true
                    onboardingNavigated = true
                }
                .navigationDestination(isPresented: $onboardingNavigated) {
                    curriculumView
                }
        }
    }

    // MARK: - Main Tab View

    private var mainTabView: some View {
        TabView(selection: $activeTab) {
            NavigationStack {
                curriculumView
            }
            .tabItem {
                Label("Curriculum", systemImage: "list.bullet.rectangle")
            }
            .tag(0)

            NavigationStack {
                PracticeSessionView(userId: userId)
                    .navigationTitle("Practice")
                    #if os(iOS)
                    .navigationBarTitleDisplayMode(.inline)
                    #endif
            }
            .tabItem {
                Label("Practice", systemImage: "mic.fill")
            }
            .tag(1)

            NavigationStack {
                ProgressDashboardView(userId: userId)
                    .navigationTitle("Progress")
                    #if os(iOS)
                    .navigationBarTitleDisplayMode(.inline)
                    #endif
            }
            .tabItem {
                Label("Progress", systemImage: "chart.bar.fill")
            }
            .tag(2)
        }
        .tint(Color.BotTheme.primary)
    }

    // MARK: - CurriculumView

    @ViewBuilder
    private var curriculumView: some View {
        CurriculumView(userId: userId)
            .navigationDestination(for: NavigationRoute.self) { route in
                switch route {
                case .practice:
                    PracticeSessionView(userId: userId)
                        .navigationTitle("Practice")
                        #if os(iOS)
                        .navigationBarTitleDisplayMode(.inline)
                        #endif
                case .progress:
                    ProgressDashboardView(userId: userId)
                        .navigationTitle("Progress")
                        #if os(iOS)
                        .navigationBarTitleDisplayMode(.inline)
                        #endif
                }
            }
            .toolbar {
                ToolbarItem(placement: .automatic) {
                    NavigationLink(value: NavigationRoute.practice) {
                        Label("Practice", systemImage: "mic.circle.fill")
                            .foregroundColor(Color.BotTheme.primary)
                    }
                }
            }
    }
}
