import XCTest
import SwiftUI
import ViewInspector
@testable import App

final class SmokeTests: XCTestCase {
    func test_appModuleImports() {
        XCTAssertTrue(true)
    }

    func test_viewInspectorWorking() throws {
        let view = Text("Hello Test")
        let text = try view.inspect().text().string()
        XCTAssertEqual(text, "Hello Test")
    }
}
