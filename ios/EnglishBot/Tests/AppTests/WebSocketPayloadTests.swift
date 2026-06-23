import XCTest
@testable import App

final class WebSocketPayloadTests: XCTestCase {
    func test_decodeConnectedEvent() throws {
        let json = """
        {"event":"connected","timestamp":"2024-01-01T00:00:00","data":{"user_id":"abc","resumed":false}}
        """.data(using: .utf8)!
        let envelope = try JSONDecoder().decode(WebSocketEnvelope.self, from: json)
        if case .connected(let payload) = envelope.data {
            XCTAssertEqual(payload.userId, "abc")
            XCTAssertEqual(payload.resumed, false)
        } else { XCTFail("Expected .connected") }
    }

    func test_decodeErrorEvent() throws {
        let json = """
        {"event":"error","timestamp":"2024-01-01","data":{"error_code":"SESSION_NOT_FOUND","message":"No session","detail":null}}
        """.data(using: .utf8)!
        let envelope = try JSONDecoder().decode(WebSocketEnvelope.self, from: json)
        if case .error(let payload) = envelope.data {
            XCTAssertEqual(payload.errorCode, "SESSION_NOT_FOUND")
        } else { XCTFail("Expected .error") }
    }

    func test_decodeHeartbeat() throws {
        let json = """
        {"event":"heartbeat","timestamp":"2024-01-01","data":{}}
        """.data(using: .utf8)!
        let envelope = try JSONDecoder().decode(WebSocketEnvelope.self, from: json)
        if case .heartbeat = envelope.data { } else { XCTFail("Expected .heartbeat") }
    }

    func test_decodeUnknownEvent() throws {
        let json = """
        {"event":"future_event","timestamp":"2024-01-01","data":{"foo":"bar"}}
        """.data(using: .utf8)!
        let envelope = try JSONDecoder().decode(WebSocketEnvelope.self, from: json)
        if case .unknown = envelope.data { } else { XCTFail("Expected .unknown") }
    }
}
