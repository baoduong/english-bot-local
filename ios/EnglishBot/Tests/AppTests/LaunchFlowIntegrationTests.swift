import XCTest
@testable import App

@MainActor
final class LaunchFlowIntegrationTests: XCTestCase {

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

    // S1: Fresh install (empty userId, empty baseURL, Bonjour fails) → settingsRequired
    func testS1FreshInstallNoUrlBonjourFails() async {
        let vm = makeVM(
            bonjourDiscover: { nil },
            readStoredURL: { nil }
        )
        await vm.bootstrap()
        if case .settingsRequired = vm.route {
            // pass
        } else {
            XCTFail("S1: Expected .settingsRequired, got \(vm.route)")
        }
    }

    // S2: Fresh install + Bonjour succeeds + healthy → onboarding shown
    func testS2FreshInstallBonjourSucceedsHealthy() async {
        var savedURL: String?
        let vm = makeVM(
            reachability: { _, _ in .healthy },
            bonjourDiscover: { URL(string: "http://192.168.1.100:8080") },
            readStoredURL: { savedURL },
            writeStoredURL: { savedURL = $0 },
            readOnboardingDone: { false },
            curriculumProbe: { _ in false }
        )
        await vm.bootstrap()
        XCTAssertEqual(vm.route, .onboarding, "S2: Bonjour success + healthy should route to onboarding")
    }

    // S3: Returning user + URL + healthy + !onboardingDone + no curriculum → onboarding
    func testS3ReturningUserHealthyNoCurriculum() async {
        let vm = makeVM(
            reachability: { _, _ in .healthy },
            readStoredURL: { "http://localhost:8080" },
            readOnboardingDone: { false },
            curriculumProbe: { _ in false }
        )
        await vm.bootstrap()
        XCTAssertEqual(vm.route, .onboarding, "S3: Returning user, no curriculum → onboarding")
    }

    // S4: Returning user + URL + healthy + onboardingDone=true → main tabs
    func testS4ReturningUserOnboardingDone() async {
        let vm = makeVM(
            reachability: { _, _ in .healthy },
            readStoredURL: { "http://localhost:8080" },
            readOnboardingDone: { true }
        )
        await vm.bootstrap()
        XCTAssertEqual(vm.route, .main, "S4: Returning user, onboardingDone=true → main")
    }

    // S5: Returning user + URL + healthy + !onboardingDone + curriculum exists → auto-set + main
    func testS5ReturningUserCurriculumExistsAutoSetsOnboardingDone() async {
        var onboardingDoneValue = false
        let vm = makeVM(
            reachability: { _, _ in .healthy },
            readStoredURL: { "http://localhost:8080" },
            readOnboardingDone: { onboardingDoneValue },
            setOnboardingDone: { onboardingDoneValue = $0 },
            curriculumProbe: { _ in true }
        )
        await vm.bootstrap()
        XCTAssertEqual(vm.route, .main, "S5: Curriculum exists → auto-set onboardingDone + main")
        XCTAssertTrue(onboardingDoneValue, "S5: onboardingDone should be auto-set to true")
    }

    // S6: Returning user + URL + unreachable → settingsRequired with reason
    func testS6ReturningUserUnreachable() async {
        let vm = makeVM(
            reachability: { _, _ in .unreachable("Connection refused") },
            readStoredURL: { "http://localhost:8080" }
        )
        await vm.bootstrap()
        if case .settingsRequired(let reason) = vm.route {
            XCTAssertEqual(reason, "Connection refused", "S6: Unreachable reason should be passed through")
        } else {
            XCTFail("S6: Expected .settingsRequired, got \(vm.route)")
        }
    }

    // S7: Returning user + URL + degraded → settingsRequired with degraded reason
    func testS7ReturningUserDegraded() async {
        let vm = makeVM(
            reachability: { _, _ in .degraded("Ollama down") },
            readStoredURL: { "http://localhost:8080" }
        )
        await vm.bootstrap()
        if case .settingsRequired(let reason) = vm.route {
            XCTAssertEqual(reason, "Ollama down", "S7: Degraded reason should be passed through")
        } else {
            XCTFail("S7: Expected .settingsRequired, got \(vm.route)")
        }
    }

    // S8 (multi-turn): invalid URL → error → correct URL → healthy → onboarding
    func testS8InvalidThenValidUrlRecovery() async {
        var storedURL: String? = "not a url"

        let vm = makeVM(
            reachability: { _, _ in .healthy },
            readStoredURL: { storedURL },
            writeStoredURL: { storedURL = $0 },
            readOnboardingDone: { false },
            curriculumProbe: { _ in false }
        )

        await vm.bootstrap()
        if case .settingsRequired(let reason) = vm.route {
            XCTAssertEqual(reason, "Invalid URL format", "S8: Invalid URL should route to settingsRequired")
        } else {
            XCTFail("S8 step 1: Expected .settingsRequired for invalid URL, got \(vm.route)")
        }

        storedURL = "http://192.168.1.100:8080"
        await vm.retryAfterSettingsSave()
        XCTAssertEqual(vm.route, .onboarding, "S8: After valid URL + healthy → onboarding")
    }
}
