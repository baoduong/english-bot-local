import XCTest
import SwiftUI
import ViewInspector
#if canImport(UIKit)
import UIKit
#endif
@testable import App

final class FlowLayoutTests: XCTestCase {
    func test_flowLayoutWrapsFiveChipsAndReportsTightWidth() throws {
        let layout = FlowLayout(spacing: 8)
        let result = FlowLayout.FlowResult(in: 200, subviews: [
            CGSize(width: 52, height: 28),
            CGSize(width: 52, height: 28),
            CGSize(width: 68, height: 28),
            CGSize(width: 60, height: 28),
            CGSize(width: 56, height: 28),
        ], spacing: layout.spacing)

        XCTAssertEqual(result.frames.count, 5)
        XCTAssertGreaterThanOrEqual(result.frames[2].minY, result.frames[0].minY)
        XCTAssertGreaterThan(result.frames[4].minY, result.frames[2].minY)
        XCTAssertLessThanOrEqual(result.bounds.width, 200)
        XCTAssertGreaterThan(result.bounds.height, 28)
    }

    func test_flowLayoutReturnsTighterWidthForTwoChips() throws {
        let result = FlowLayout.FlowResult(in: 200, subviews: [
            CGSize(width: 52, height: 28),
            CGSize(width: 52, height: 28),
        ], spacing: 8)

        XCTAssertEqual(result.frames.count, 2)
        XCTAssertLessThan(result.bounds.width, 200)
        XCTAssertGreaterThan(result.bounds.width, 0)
        XCTAssertEqual(result.bounds.height, 28)
    }
}
