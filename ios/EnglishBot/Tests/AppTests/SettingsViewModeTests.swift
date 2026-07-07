import XCTest
import SwiftUI
import ViewInspector
@testable import App

final class SettingsViewModeTests: XCTestCase {

    private let suiteName = "test.settingsview"
    private var testStore: UserDefaults!

    override func setUp() {
        super.setUp()
        testStore = UserDefaults(suiteName: suiteName)!
        testStore.removePersistentDomain(forName: suiteName)
    }

    override func tearDown() {
        testStore.removePersistentDomain(forName: suiteName)
        super.tearDown()
    }

    func testNormalModeHasNoSetupBanner() throws {
        let view = SettingsView(mode: .normal, store: testStore)
        XCTAssertThrowsError(try view.inspect().find(text: "Backend not configured"))
    }

    func testSetupRequiredModeShowsBanner() throws {
        let view = SettingsView(mode: .setupRequired, store: testStore)
        let banner = try view.inspect().find(text: "Backend not configured")
        XCTAssertNotNil(banner)
    }

    func testSetupRequiredModeShowsSaveAndContinueButton() throws {
        let view = SettingsView(mode: .setupRequired, store: testStore)
        let button = try view.inspect().find(text: "Save & Continue")
        XCTAssertNotNil(button)
    }

    func testUrlSchemeRejectedFtp() async {
        var callbackInvoked = false
        let result = await Self.simulateSave(
            urlString: "ftp://foo.example.com",
            probe: { _, _ in .healthy },
            callback: { callbackInvoked = true }
        )
        XCTAssertFalse(callbackInvoked)
        XCTAssertTrue(result.contains("❌"))
    }

    func testUrlSchemeRejectedFile() async {
        var callbackInvoked = false
        let result = await Self.simulateSave(
            urlString: "file:///some/path",
            probe: { _, _ in .healthy },
            callback: { callbackInvoked = true }
        )
        XCTAssertFalse(callbackInvoked)
        XCTAssertTrue(result.contains("❌"))
    }

    func testSaveAndContinueInvokesCallbackOnHealthy() async {
        var callbackInvoked = false
        _ = await Self.simulateSave(
            urlString: "http://localhost:8080",
            probe: { _, _ in .healthy },
            callback: { callbackInvoked = true }
        )
        XCTAssertTrue(callbackInvoked)
    }

    func testSaveAndContinueStaysOnDegraded() async {
        var callbackInvoked = false
        let result = await Self.simulateSave(
            urlString: "http://localhost:8080",
            probe: { _, _ in .degraded("Ollama down") },
            callback: { callbackInvoked = true }
        )
        XCTAssertFalse(callbackInvoked)
        XCTAssertTrue(result.contains("❌"))
    }

    func testSaveAndContinueStaysOnUnreachable() async {
        var callbackInvoked = false
        let result = await Self.simulateSave(
            urlString: "http://localhost:8080",
            probe: { _, _ in .unreachable("Connection refused") },
            callback: { callbackInvoked = true }
        )
        XCTAssertFalse(callbackInvoked)
        XCTAssertTrue(result.contains("❌"))
    }

    private static func simulateSave(
        urlString: String,
        probe: @escaping (URL, TimeInterval) async -> ReachabilityStatus,
        callback: @escaping () async -> Void
    ) async -> String {
        let trimmed = urlString.trimmingCharacters(in: .whitespacesAndNewlines)
        guard let url = URL(string: trimmed),
              let scheme = url.scheme,
              (scheme == "http" || scheme == "https") else {
            return "❌ URL must start with http:// or https://"
        }
        let status = await probe(url, 20.0)
        switch status {
        case .healthy:
            await callback()
            return "✅ Success"
        case .degraded(let reason):
            return "❌ Backend degraded: \(reason)"
        case .unreachable(let reason):
            return "❌ \(reason)"
        }
    }
}
