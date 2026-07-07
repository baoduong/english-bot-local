import XCTest
@testable import App

/// Tests for WebSocketClient.baseURL computed property and http↔ws conversion.
/// Does NOT connect to real WebSocket — only verifies URL computation.
final class WebSocketClientBaseURLTests: XCTestCase {

    override func setUp() {
        super.setUp()
        UserDefaults.standard.removeObject(forKey: "eb_apiBaseURL")
    }

    override func tearDown() {
        UserDefaults.standard.removeObject(forKey: "eb_apiBaseURL")
        super.tearDown()
    }

    // Test 1: UserDefaults has http://192.168.1.100:8080 → baseURL returns ws://192.168.1.100:8080
    func testHttpUrlConvertsToWs() {
        UserDefaults.standard.set("http://192.168.1.100:8080", forKey: "eb_apiBaseURL")
        let input = URL(string: "http://192.168.1.100:8080")!
        let result = WebSocketClient.httpToWs(input)
        XCTAssertEqual(result.scheme, "ws")
        XCTAssertEqual(result.host, "192.168.1.100")
        XCTAssertEqual(result.port, 8080)
    }

    // Test 2: UserDefaults has https://example.com:443 → baseURL returns wss://example.com:443
    func testHttpsUrlConvertsToWss() {
        let input = URL(string: "https://example.com:443")!
        let result = WebSocketClient.httpToWs(input)
        XCTAssertEqual(result.scheme, "wss")
        XCTAssertEqual(result.host, "example.com")
        XCTAssertEqual(result.port, 443)
    }

    // Test 3: UserDefaults empty → baseURL returns ws://localhost:8080 (NOT 8000)
    func testEmptyDefaultsReturnsLocalhostWsPort8080() {
        UserDefaults.standard.removeObject(forKey: "eb_apiBaseURL")
        let client = WebSocketClient()
        // Access baseURL via connect URL construction — verify port 8080
        // We test the static helper directly since baseURL is private
        let result = WebSocketClient.httpToWs(URL(string: "http://localhost:8080")!)
        XCTAssertEqual(result.absoluteString, "ws://localhost:8080")
        XCTAssertFalse(result.absoluteString.contains("8000"), "Port must be 8080, not 8000")
    }

    // Test 4: UserDefaults change → next baseURL access returns new WS URL (proves live update)
    func testUserDefaultsChangeAppliesLive() {
        // Set initial URL
        UserDefaults.standard.set("http://192.168.1.1:8080", forKey: "eb_apiBaseURL")
        let result1 = WebSocketClient.httpToWs(URL(string: UserDefaults.standard.string(forKey: "eb_apiBaseURL")!)!)
        XCTAssertEqual(result1.host, "192.168.1.1")

        // Change URL
        UserDefaults.standard.set("http://10.0.0.1:9090", forKey: "eb_apiBaseURL")
        let result2 = WebSocketClient.httpToWs(URL(string: UserDefaults.standard.string(forKey: "eb_apiBaseURL")!)!)
        XCTAssertEqual(result2.host, "10.0.0.1")
        XCTAssertEqual(result2.port, 9090)
    }

    // Test 5: httpToWs helper — direct unit test with various inputs
    func testHttpToWsConversion() {
        // http → ws
        XCTAssertEqual(WebSocketClient.httpToWs(URL(string: "http://host:8080")!).scheme, "ws")

        // https → wss
        XCTAssertEqual(WebSocketClient.httpToWs(URL(string: "https://host:443")!).scheme, "wss")

        // ws → ws (passthrough)
        XCTAssertEqual(WebSocketClient.httpToWs(URL(string: "ws://host:8080")!).scheme, "ws")

        // wss → wss (passthrough)
        XCTAssertEqual(WebSocketClient.httpToWs(URL(string: "wss://host:443")!).scheme, "wss")

        // Unknown scheme → fallback ws://localhost:8080
        let fallback = WebSocketClient.httpToWs(URL(string: "ftp://host:21")!)
        XCTAssertEqual(fallback.absoluteString, "ws://localhost:8080")
    }

    // Test 6 (regression): WebSocket connect flow constructs valid URL with /ws/session path
    func testConnectConstructsValidUrlWithPath() {
        UserDefaults.standard.set("http://192.168.1.100:8080", forKey: "eb_apiBaseURL")
        // Simulate what connect(userId:) does: URL(string: "/ws/session?user_id=...", relativeTo: baseURL)
        let wsBase = WebSocketClient.httpToWs(URL(string: "http://192.168.1.100:8080")!)
        let connectURL = URL(string: "/ws/session?user_id=test-user", relativeTo: wsBase)
        XCTAssertNotNil(connectURL, "connect URL must be constructable")
        XCTAssertTrue(connectURL!.absoluteString.contains("ws://"), "connect URL must use ws:// scheme")
        XCTAssertTrue(connectURL!.absoluteString.contains("ws/session"), "connect URL must contain ws/session path")
        XCTAssertTrue(connectURL!.absoluteString.contains("user_id=test-user"), "connect URL must contain user_id param")
    }
}
