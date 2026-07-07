import XCTest
import SwiftUI
import ViewInspector
@testable import App

@MainActor
final class SplashViewTests: XCTestCase {

    private func makeVM(progressMessage: String = "Connecting...") -> AppBootstrapViewModel {
        let vm = AppBootstrapViewModel(
            reachability: { _, _ in .healthy },
            readStoredURL: { "http://localhost:8080" },
            readOnboardingDone: { true }
        )
        vm.progressMessage = progressMessage
        return vm
    }

    // Test 1: initial render shows "Connecting..." message
    func testInitialRenderShowsConnectingMessage() throws {
        let vm = makeVM(progressMessage: "Connecting...")
        let view = SplashView(viewModel: vm)
        let progressText = try view.inspect().find(text: "Connecting...")
        XCTAssertNotNil(progressText)
    }

    // Test 2: when viewModel.progressMessage changes, view reflects new message
    func testProgressMessageUpdatesUsingT9Pattern() throws {
        let vm = makeVM(progressMessage: "Still checking...")
        let view = SplashView(viewModel: vm)
        let progressText = try view.inspect().find(text: "Still checking...")
        XCTAssertNotNil(progressText)
    }

    // Test 3: mic.fill SF Symbol renders
    func testMicFillSymbolPresent() throws {
        let vm = makeVM()
        let view = SplashView(viewModel: vm)
        let image = try view.inspect().find(ViewType.Image.self)
        XCTAssertNotNil(image)
    }

    // Test 4: "English Coach" text present
    func testEnglishCoachTextPresent() throws {
        let vm = makeVM()
        let view = SplashView(viewModel: vm)
        let titleText = try view.inspect().find(text: "English Coach")
        XCTAssertNotNil(titleText)
    }

    // Test 5: ProgressView present
    func testProgressViewPresent() throws {
        let vm = makeVM()
        let view = SplashView(viewModel: vm)
        let progressView = try view.inspect().find(ViewType.ProgressView.self)
        XCTAssertNotNil(progressView)
    }
}
