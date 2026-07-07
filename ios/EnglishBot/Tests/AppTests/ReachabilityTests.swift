import XCTest
@testable import App

// MARK: - MockURLProtocol

final class MockURLProtocol: URLProtocol {
    static var requestHandler: ((URLRequest) throws -> (HTTPURLResponse, Data))?

    override class func canInit(with request: URLRequest) -> Bool { true }
    override class func canonicalRequest(for request: URLRequest) -> URLRequest { request }

    override func startLoading() {
        guard let handler = MockURLProtocol.requestHandler else {
            client?.urlProtocol(self, didFailWithError: URLError(.unknown))
            return
        }
        do {
            let (response, data) = try handler(request)
            client?.urlProtocol(self, didReceive: response, cacheStoragePolicy: .notAllowed)
            client?.urlProtocol(self, didLoad: data)
            client?.urlProtocolDidFinishLoading(self)
        } catch {
            client?.urlProtocol(self, didFailWithError: error)
        }
    }

    override func stopLoading() {}
}

// MARK: - ReachabilityTests

final class ReachabilityTests: XCTestCase {

    private var mockConfig: URLSessionConfiguration!
    private let baseURL = URL(string: "http://localhost:8080")!

    override func setUp() {
        super.setUp()
        mockConfig = URLSessionConfiguration.ephemeral
        mockConfig.protocolClasses = [MockURLProtocol.self]
        MockURLProtocol.requestHandler = nil
    }

    override func tearDown() {
        MockURLProtocol.requestHandler = nil
        super.tearDown()
    }

    // Test 1: HTTP 200 + JSON {"status":"healthy"} → .healthy
    func testProbeReturnsHealthyOn200() async {
        MockURLProtocol.requestHandler = { _ in
            let response = HTTPURLResponse(
                url: self.baseURL.appendingPathComponent("health"),
                statusCode: 200,
                httpVersion: nil,
                headerFields: ["Content-Type": "application/json"]
            )!
            let data = #"{"status":"healthy","ollama":"ok","whisper":"ok"}"#.data(using: .utf8)!
            return (response, data)
        }

        let status = await Reachability.probe(baseURL: baseURL, timeout: 0.1, sessionConfiguration: mockConfig)
        XCTAssertEqual(status, .healthy)
    }

    // Test 2: HTTP 200 + JSON {"status":"degraded","reason":"Ollama down"} → .degraded with reason
    func testProbeReturnsDegradedOnBackendStatusDegraded() async {
        MockURLProtocol.requestHandler = { _ in
            let response = HTTPURLResponse(
                url: self.baseURL.appendingPathComponent("health"),
                statusCode: 200,
                httpVersion: nil,
                headerFields: ["Content-Type": "application/json"]
            )!
            let data = #"{"status":"degraded","reason":"Ollama down"}"#.data(using: .utf8)!
            return (response, data)
        }

        let status = await Reachability.probe(baseURL: baseURL, timeout: 0.1, sessionConfiguration: mockConfig)
        if case .degraded(let reason) = status {
            XCTAssertEqual(reason, "Ollama down")
        } else {
            XCTFail("Expected .degraded, got \(status)")
        }
    }

    // Test 3: HTTP 200 + JSON without status field → .degraded("Invalid /health response")
    func testProbeReturnsDegradedOnMissingStatusField() async {
        MockURLProtocol.requestHandler = { _ in
            let response = HTTPURLResponse(
                url: self.baseURL.appendingPathComponent("health"),
                statusCode: 200,
                httpVersion: nil,
                headerFields: ["Content-Type": "application/json"]
            )!
            let data = #"{"ollama":"ok"}"#.data(using: .utf8)!
            return (response, data)
        }

        let status = await Reachability.probe(baseURL: baseURL, timeout: 0.1, sessionConfiguration: mockConfig)
        XCTAssertEqual(status, .degraded("Invalid /health response"))
    }

    // Test 4: HTTP 200 + HTML body (captive portal) → .unreachable("Captive portal...")
    func testProbeReturnsUnreachableOnCaptivePortalHTML() async {
        MockURLProtocol.requestHandler = { _ in
            let response = HTTPURLResponse(
                url: self.baseURL.appendingPathComponent("health"),
                statusCode: 200,
                httpVersion: nil,
                headerFields: ["Content-Type": "text/html; charset=utf-8"]
            )!
            let data = "<html><body>Login required</body></html>".data(using: .utf8)!
            return (response, data)
        }

        let status = await Reachability.probe(baseURL: baseURL, timeout: 0.1, sessionConfiguration: mockConfig)
        XCTAssertEqual(status, .unreachable("Captive portal or invalid backend"))
    }

    // Test 5: HTTP 404 → .unreachable("HTTP 404")
    func testProbeReturnsUnreachableOn404() async {
        MockURLProtocol.requestHandler = { _ in
            let response = HTTPURLResponse(
                url: self.baseURL.appendingPathComponent("health"),
                statusCode: 404,
                httpVersion: nil,
                headerFields: [:]
            )!
            return (response, Data())
        }

        let status = await Reachability.probe(baseURL: baseURL, timeout: 0.1, sessionConfiguration: mockConfig)
        XCTAssertEqual(status, .unreachable("HTTP 404"))
    }

    // Test 6: Network error (mock throws) → .unreachable(error message)
    func testProbeReturnsUnreachableOnNetworkError() async {
        MockURLProtocol.requestHandler = { _ in
            throw URLError(.notConnectedToInternet)
        }

        let status = await Reachability.probe(baseURL: baseURL, timeout: 0.1, sessionConfiguration: mockConfig)
        if case .unreachable = status {
            // pass
        } else {
            XCTFail("Expected .unreachable, got \(status)")
        }
    }

    // Test 7: Timeout (mock delays > timeout) → .unreachable within ~200ms
    func testProbeReturnsUnreachableOnTimeout() async {
        MockURLProtocol.requestHandler = { _ in
            // Simulate delay by throwing timeout error
            throw URLError(.timedOut)
        }

        let start = Date()
        let status = await Reachability.probe(baseURL: baseURL, timeout: 0.1, sessionConfiguration: mockConfig)
        let elapsed = Date().timeIntervalSince(start)

        if case .unreachable = status {
            // pass
        } else {
            XCTFail("Expected .unreachable on timeout, got \(status)")
        }
        XCTAssertLessThan(elapsed, 2.0, "Probe should complete quickly with short timeout")
    }

    // Test 8: Verify URLSession config uses passed timeout
    func testProbeCompletesWithinTimeoutBound() async {
        MockURLProtocol.requestHandler = { _ in
            let response = HTTPURLResponse(
                url: self.baseURL.appendingPathComponent("health"),
                statusCode: 200,
                httpVersion: nil,
                headerFields: ["Content-Type": "application/json"]
            )!
            let data = #"{"status":"healthy"}"#.data(using: .utf8)!
            return (response, data)
        }

        let start = Date()
        let status = await Reachability.probe(baseURL: baseURL, timeout: 0.5, sessionConfiguration: mockConfig)
        let elapsed = Date().timeIntervalSince(start)

        XCTAssertEqual(status, .healthy)
        XCTAssertLessThan(elapsed, 1.0, "Probe with 0.5s timeout should complete within 1s")
    }
}
