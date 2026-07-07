import XCTest
@testable import App

@MainActor
final class AppBootstrapViewModelTests: XCTestCase {

    // MARK: - Helpers

    private func makeVM(
        reachability: @escaping (URL, TimeInterval) async -> ReachabilityStatus = { _, _ in .healthy },
        bonjourDiscover: @escaping () async -> URL? = { nil },
        readStoredURL: @escaping () -> String? = { nil },
        writeStoredURL: @escaping (String) -> Void = { _ in },
        readOnboardingDone: @escaping () -> Bool = { false },
        setOnboardingDone: @escaping (Bool) -> Void = { _ in },
        curriculumProbe: @escaping (String) async -> Bool = { _ in false },
        readUserId: @escaping () -> String = { "test-user" }
    ) -> AppBootstrapViewModel {
        AppBootstrapViewModel(
            reachability: reachability,
            bonjourDiscover: bonjourDiscover,
            readStoredURL: readStoredURL,
            writeStoredURL: writeStoredURL,
            readOnboardingDone: readOnboardingDone,
            setOnboardingDone: setOnboardingDone,
            curriculumProbe: curriculumProbe,
            readUserId: readUserId
        )
    }

    // MARK: - Test 1: empty stored URL + Bonjour nil → .settingsRequired

    func testEmptyUrlAndBonjourNilRoutesToSettings() async {
        let vm = makeVM(
            bonjourDiscover: { nil },
            readStoredURL: { nil }
        )
        await vm.bootstrap()
        XCTAssertEqual(vm.route, .settingsRequired(reason: "Backend URL not configured"))
    }

    // MARK: - Test 2: empty stored URL + Bonjour finds URL + healthy → .onboarding

    func testEmptyUrlBonjourSucceedsHealthyRoutesToOnboarding() async {
        let discoveredURL = URL(string: "http://192.168.1.100:8080")!
        var savedURL: String?
        let vm = makeVM(
            reachability: { _, _ in .healthy },
            bonjourDiscover: { discoveredURL },
            readStoredURL: { savedURL },
            writeStoredURL: { savedURL = $0 },
            readOnboardingDone: { false },
            curriculumProbe: { _ in false }
        )
        await vm.bootstrap()
        XCTAssertEqual(vm.route, .onboarding)
        XCTAssertEqual(savedURL, "http://192.168.1.100:8080")
    }

    // MARK: - Test 3: stored URL + healthy + onboardingDone=true → .main

    func testStoredUrlHealthyOnboardingDoneRoutesToMain() async {
        let vm = makeVM(
            reachability: { _, _ in .healthy },
            readStoredURL: { "http://localhost:8080" },
            readOnboardingDone: { true }
        )
        await vm.bootstrap()
        XCTAssertEqual(vm.route, .main)
    }

    // MARK: - Test 4: stored URL + healthy + onboardingDone=false + curriculum exists → auto-set + .main

    func testStoredUrlHealthyNoCurriculumExistsAutoSetsOnboardingDone() async {
        var onboardingDoneValue = false
        let vm = makeVM(
            reachability: { _, _ in .healthy },
            readStoredURL: { "http://localhost:8080" },
            readOnboardingDone: { onboardingDoneValue },
            setOnboardingDone: { onboardingDoneValue = $0 },
            curriculumProbe: { _ in true }  // curriculum exists
        )
        await vm.bootstrap()
        XCTAssertEqual(vm.route, .main)
        XCTAssertTrue(onboardingDoneValue, "onboardingDone should be auto-set to true")
    }

    // MARK: - Test 5: stored URL + healthy + onboardingDone=false + no curriculum → .onboarding

    func testStoredUrlHealthyNoCurriculumRoutesToOnboarding() async {
        let vm = makeVM(
            reachability: { _, _ in .healthy },
            readStoredURL: { "http://localhost:8080" },
            readOnboardingDone: { false },
            curriculumProbe: { _ in false }
        )
        await vm.bootstrap()
        XCTAssertEqual(vm.route, .onboarding)
    }

    // MARK: - Test 6: stored URL + unreachable → .settingsRequired with reason

    func testStoredUrlUnreachableRoutesToSettings() async {
        let vm = makeVM(
            reachability: { _, _ in .unreachable("Connection refused") },
            readStoredURL: { "http://localhost:8080" }
        )
        await vm.bootstrap()
        XCTAssertEqual(vm.route, .settingsRequired(reason: "Connection refused"))
    }

    // MARK: - Test 7: stored URL + degraded → .settingsRequired with degraded reason

    func testStoredUrlDegradedRoutesToSettings() async {
        let vm = makeVM(
            reachability: { _, _ in .degraded("Ollama down") },
            readStoredURL: { "http://localhost:8080" }
        )
        await vm.bootstrap()
        XCTAssertEqual(vm.route, .settingsRequired(reason: "Ollama down"))
    }

    // MARK: - Test 8 (RACE): concurrent bootstrap() calls — only ONE reachability probe fires

    func testConcurrentBootstrapCallsFireProbeOnce() async {
        var probeCallCount = 0
        // Use a slow reachability to ensure the first bootstrap is still running when second starts
        let vm = makeVM(
            reachability: { _, _ in
                probeCallCount += 1
                // Small delay to ensure first bootstrap is "in progress" when second fires
                try? await Task.sleep(nanoseconds: 10_000_000) // 10ms
                return .healthy
            },
            readStoredURL: { "http://localhost:8080" },
            readOnboardingDone: { true }
        )

        // Start first bootstrap in a Task so it runs concurrently
        let firstTask = Task { @MainActor in
            await vm.bootstrap()
        }

        // Yield to let first task start and set isBootstrapping = true
        await Task.yield()

        // Now fire second bootstrap — should be a no-op due to reentry guard
        await vm.bootstrap()

        // Wait for first task to complete
        await firstTask.value

        XCTAssertEqual(probeCallCount, 1, "Reachability probe should fire exactly ONCE despite concurrent bootstrap() calls")
    }

    // MARK: - Test 9 (RACE): retryAfterSettingsSave() starts fresh

    func testRetryAfterSettingsSaveStartsFresh() async {
        var probeCallCount = 0
        let vm = makeVM(
            reachability: { _, _ in
                probeCallCount += 1
                return .healthy
            },
            readStoredURL: { "http://localhost:8080" },
            readOnboardingDone: { true }
        )

        // First bootstrap
        await vm.bootstrap()
        XCTAssertEqual(probeCallCount, 1)

        // Retry should run a fresh bootstrap
        await vm.retryAfterSettingsSave()
        XCTAssertEqual(probeCallCount, 2, "retryAfterSettingsSave should trigger a fresh bootstrap probe")
        XCTAssertEqual(vm.route, .main)
    }

    // MARK: - Test 10 (RACE): handleGoalReset() starts fresh

    func testHandleGoalResetStartsFresh() async {
        var probeCallCount = 0
        let vm = makeVM(
            reachability: { _, _ in
                probeCallCount += 1
                return .healthy
            },
            readStoredURL: { "http://localhost:8080" },
            readOnboardingDone: { true }
        )

        await vm.bootstrap()
        XCTAssertEqual(probeCallCount, 1)

        await vm.handleGoalReset()
        XCTAssertEqual(probeCallCount, 2, "handleGoalReset should trigger a fresh bootstrap probe")
    }

    // MARK: - Test 11: invalid stored URL → .settingsRequired(reason: "Invalid URL format")

    func testInvalidStoredUrlRoutesToSettings() async {
        let vm = makeVM(
            readStoredURL: { "not a url" }
        )
        await vm.bootstrap()
        XCTAssertEqual(vm.route, .settingsRequired(reason: "Invalid URL format"))
    }
}
