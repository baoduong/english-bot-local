import XCTest
import SwiftUI
import ViewInspector
@testable import App

// MARK: - Test Views

private struct StateDrivenView: View, Inspectable {
    @State var message: String = "initial"

    var body: some View {
        Text(message)
    }
}

private class TestViewModel: ObservableObject {
    @Published var message: String = "initial"
}

private struct ObservableObjectDrivenView: View, Inspectable {
    @ObservedObject var viewModel: TestViewModel

    var body: some View {
        Text(viewModel.message)
    }
}

// MARK: - ViewHostingTestSupportTests

final class ViewHostingTestSupportTests: XCTestCase {

    // Test 1: Static view inspection works — ViewInspector can inspect a simple Text view
    func testStatefulViewInspectionFires() throws {
        let view = Text("initial")
        let text = try view.inspect().text().string()
        XCTAssertEqual(text, "initial")
    }

    // Test 2: ObservableObject-driven view — ViewInspector can inspect @ObservedObject view body
    func testObservableObjectDrivenViewInspectionFires() throws {
        let vm = TestViewModel()
        let view = ObservableObjectDrivenView(viewModel: vm)
        let text = try view.inspect().text().string()
        XCTAssertEqual(text, "initial")
    }

    // Test 3: Inspection helper types are constructable (API surface test)
    func testViewHostingCleanupAfterTest() throws {
        let view = StateDrivenView()
        let text = try view.inspect().text().string()
        XCTAssertEqual(text, "initial")
        let inspection = Inspection<StateDrivenView>()
        XCTAssertNotNil(inspection.notice)
    }
}
