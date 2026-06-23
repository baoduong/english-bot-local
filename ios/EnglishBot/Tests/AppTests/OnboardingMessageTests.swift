import XCTest
@testable import App

final class OnboardingMessageTests: XCTestCase {
    func test_decodeMessagesWithSameTurnNumberGeneratesDistinctIds() throws {
        let json = """
        [
          {"turn_number":1,"role":"user","content":"Hi"},
          {"turn_number":1,"role":"assistant","content":"Hello"}
        ]
        """.data(using: .utf8)!

        let messages = try JSONDecoder().decode([OnboardingMessage].self, from: json)

        XCTAssertEqual(messages.count, 2)
        XCTAssertEqual(messages[0].turnNumber, 1)
        XCTAssertEqual(messages[1].turnNumber, 1)
        XCTAssertNotEqual(messages[0].id, messages[1].id)
    }
}
