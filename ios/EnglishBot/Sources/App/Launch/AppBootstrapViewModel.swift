import Foundation
import SwiftUI

// MARK: - BootstrapRoute

/// State machine route for the app's launch flow.
public enum BootstrapRoute: Equatable {
    case checking
    case settingsRequired(reason: String)
    case onboarding
    case main

    public static func == (lhs: BootstrapRoute, rhs: BootstrapRoute) -> Bool {
        switch (lhs, rhs) {
        case (.checking, .checking): return true
        case (.settingsRequired(let a), .settingsRequired(let b)): return a == b
        case (.onboarding, .onboarding): return true
        case (.main, .main): return true
        default: return false
        }
    }
}

// MARK: - AppBootstrapViewModel

/// Drives the app's launch state machine.
/// All dependencies are injected via closures for pure testability.
/// Uses `isBootstrapping` reentry guard to prevent double-bootstrap.
@MainActor
public class AppBootstrapViewModel: ObservableObject {
    @Published public var route: BootstrapRoute = .checking
    @Published public var progressMessage: String = "Connecting..."

    // MARK: - Reentry guard (P1-2 fix)
    private var isBootstrapping: Bool = false
    private var activeBootstrapTask: Task<Void, Never>?

    // MARK: - Injectable closures (all have prod defaults)
    let reachability: (URL, TimeInterval) async -> ReachabilityStatus
    let bonjourDiscover: () async -> URL?
    let readStoredURL: () -> String?
    let writeStoredURL: (String) -> Void
    let readOnboardingDone: () -> Bool
    let setOnboardingDone: (Bool) -> Void
    let curriculumProbe: (_ userId: String) async -> Bool
    let readUserId: () -> String

    public init(
        reachability: @escaping (URL, TimeInterval) async -> ReachabilityStatus = { url, timeout in
            await Reachability.probe(baseURL: url, timeout: timeout)
        },
        bonjourDiscover: @escaping () async -> URL? = { nil },
        readStoredURL: @escaping () -> String? = {
            UserDefaults.standard.string(forKey: "eb_apiBaseURL")
        },
        writeStoredURL: @escaping (String) -> Void = { value in
            UserDefaults.standard.set(value, forKey: "eb_apiBaseURL")
        },
        readOnboardingDone: @escaping () -> Bool = {
            UserDefaults.standard.bool(forKey: "eb_onboardingDone")
        },
        setOnboardingDone: @escaping (Bool) -> Void = { value in
            UserDefaults.standard.set(value, forKey: "eb_onboardingDone")
        },
        curriculumProbe: @escaping (_ userId: String) async -> Bool = { userId in
            do {
                _ = try await APIClient.shared.getCurrentCurriculum(userId: userId)
                return true
            } catch {
                return false
            }
        },
        readUserId: @escaping () -> String = {
            UserDefaults.standard.string(forKey: "eb_userId") ?? ""
        }
    ) {
        self.reachability = reachability
        self.bonjourDiscover = bonjourDiscover
        self.readStoredURL = readStoredURL
        self.writeStoredURL = writeStoredURL
        self.readOnboardingDone = readOnboardingDone
        self.setOnboardingDone = setOnboardingDone
        self.curriculumProbe = curriculumProbe
        self.readUserId = readUserId
    }

    // MARK: - bootstrap()

    /// Main launch sequence. Reentry-guarded: concurrent calls return early.
    public func bootstrap() async {
        // P1-2: Reentry guard — prevents double-bootstrap
        guard !isBootstrapping else { return }
        isBootstrapping = true
        route = .checking
        progressMessage = "Connecting..."
        defer { isBootstrapping = false }

        // Step 1: Read stored URL
        var storedURLString = readStoredURL()?.trimmingCharacters(in: .whitespacesAndNewlines) ?? ""

        // Step 2: If empty, try Bonjour (5s)
        if storedURLString.isEmpty {
            if let discovered = await bonjourDiscover() {
                let discoveredStr = discovered.absoluteString
                writeStoredURL(discoveredStr)
                storedURLString = discoveredStr
            }
        }

        // Step 3: If still empty → settings required
        guard !storedURLString.isEmpty else {
            route = .settingsRequired(reason: "Backend URL not configured")
            return
        }

        // Step 4: Validate URL
        guard let url = URL(string: storedURLString),
              let scheme = url.scheme,
              (scheme == "http" || scheme == "https") else {
            route = .settingsRequired(reason: "Invalid URL format")
            return
        }

        // Step 5: Progress message updates (fire-and-forget)
        let progressTask = Task { @MainActor [weak self] in
            try? await Task.sleep(nanoseconds: 5_000_000_000)
            guard let strongSelf = self, strongSelf.isBootstrapping else { return }
            strongSelf.progressMessage = "Still checking your backend..."
            try? await Task.sleep(nanoseconds: 10_000_000_000)
            guard let strongSelf2 = self, strongSelf2.isBootstrapping else { return }
            strongSelf2.progressMessage = "Almost there..."
        }
        defer { progressTask.cancel() }

        // Step 6: Probe reachability
        let status = await reachability(url, 20.0)

        // Step 7: Route based on status
        switch status {
        case .healthy:
            let onboardingDone = readOnboardingDone()
            if !onboardingDone {
                let userId = readUserId()
                let hasCurriculum = await curriculumProbe(userId)
                if hasCurriculum {
                    setOnboardingDone(true)
                    route = .main
                } else {
                    route = .onboarding
                }
            } else {
                route = .main
            }

        case .degraded(let reason):
            route = .settingsRequired(reason: reason)

        case .unreachable(let reason):
            route = .settingsRequired(reason: reason)
        }
    }

    // MARK: - retryAfterSettingsSave()

    /// Called by SettingsView after user saves a valid URL and backend is healthy.
    /// Cancels any active bootstrap task and starts fresh.
    public func retryAfterSettingsSave() async {
        activeBootstrapTask?.cancel()
        activeBootstrapTask = nil
        // isBootstrapping may be true if a previous bootstrap is still running.
        // Force reset so fresh bootstrap can proceed.
        isBootstrapping = false
        await bootstrap()
    }

    // MARK: - handleGoalReset()

    /// Called when user resets their learning goal.
    /// Cancels active bootstrap and re-runs from scratch.
    public func handleGoalReset() async {
        activeBootstrapTask?.cancel()
        activeBootstrapTask = nil
        isBootstrapping = false
        await bootstrap()
    }
}
