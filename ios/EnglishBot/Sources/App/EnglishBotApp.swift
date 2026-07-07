import SwiftUI
import DesignSystem

// MARK: - App-wide Notification Names

public extension Notification.Name {
    static let onboardingConfirmed = Notification.Name("eb.onboardingConfirmed")
    static let goalReset = Notification.Name("eb.goalReset")
    static let phaseAdvanced = Notification.Name("eb.phaseAdvanced")
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
    @State private var isShowingSettings = false

    @StateObject private var bootstrap: AppBootstrapViewModel

    public init() {
        _bootstrap = StateObject(wrappedValue: AppBootstrapViewModel(
            reachability: { url, timeout in await Reachability.probe(baseURL: url, timeout: timeout) },
            bonjourDiscover: { await BonjourDiscovery().discover(timeout: 5.0) },
            readStoredURL: { UserDefaults.standard.string(forKey: "eb_apiBaseURL") },
            writeStoredURL: { UserDefaults.standard.set($0, forKey: "eb_apiBaseURL") },
            readOnboardingDone: { UserDefaults.standard.bool(forKey: "eb_onboardingDone") },
            setOnboardingDone: { UserDefaults.standard.set($0, forKey: "eb_onboardingDone") },
            curriculumProbe: { userId in
                do {
                    _ = try await APIClient.shared.getCurrentCurriculum(userId: userId)
                    return true
                } catch { return false }
            },
            readUserId: { UserDefaults.standard.string(forKey: "eb_userId") ?? "" }
        ))
    }

    public var body: some View {
        Group {
            if userId.isEmpty {
                SplashView(viewModel: bootstrap)
                    .onAppear { userId = UUID().uuidString }
            } else {
                switch bootstrap.route {
                case .checking:
                    SplashView(viewModel: bootstrap)
                        .task { await bootstrap.bootstrap() }
                case .settingsRequired:
                    SplashView(viewModel: bootstrap)
                        #if os(iOS)
                        .fullScreenCover(isPresented: .constant(true)) {
                            NavigationStack {
                                SettingsView(
                                    mode: .setupRequired,
                                    onSaveAndContinue: { await bootstrap.retryAfterSettingsSave() }
                                )
                            }
                        }
                        #else
                        .sheet(isPresented: .constant(true)) {
                            NavigationStack {
                                SettingsView(
                                    mode: .setupRequired,
                                    onSaveAndContinue: { await bootstrap.retryAfterSettingsSave() }
                                )
                            }
                        }
                        #endif
                case .onboarding:
                    onboardingFlow
                case .main:
                    mainTabView
                }
            }
        }
        .onReceive(NotificationCenter.default.publisher(for: .goalReset)) { _ in
            onboardingDone = false
            activeTab = 0
            Task { await bootstrap.handleGoalReset() }
        }
        .sheet(isPresented: $isShowingSettings) {
            NavigationStack {
                SettingsView(mode: .normal)
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
                    .toolbar(.hidden, for: .navigationBar)
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
                        .toolbar(.hidden, for: .navigationBar)
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

                ToolbarItem(placement: .automatic) {
                    Button {
                        isShowingSettings = true
                    } label: {
                        Label("Settings", systemImage: "gearshape")
                    }
                }
            }
    }
}
