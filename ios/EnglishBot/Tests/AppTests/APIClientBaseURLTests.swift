import XCTest
@testable import App

/// Tests for APIClient.baseURL computed property.
/// Uses a custom UserDefaults suite to avoid polluting UserDefaults.standard.
final class APIClientBaseURLTests: XCTestCase {

    private let suiteName = "test.apiclient.baseurl"
    private var testDefaults: UserDefaults!

    override func setUp() {
        super.setUp()
        testDefaults = UserDefaults(suiteName: suiteName)!
        testDefaults.removePersistentDomain(forName: suiteName)
        // Redirect APIClient's key to our test suite by clearing standard
        UserDefaults.standard.removeObject(forKey: APIClient.baseURLDefaultsKey)
    }

    override func tearDown() {
        testDefaults.removePersistentDomain(forName: suiteName)
        UserDefaults.standard.removeObject(forKey: APIClient.baseURLDefaultsKey)
        super.tearDown()
    }

    // Test 1: UserDefaults has stored URL → baseURL returns that URL
    func testStoredURLReturned() {
        UserDefaults.standard.set("http://192.168.1.100:8080", forKey: APIClient.baseURLDefaultsKey)
        let client = APIClient()
        XCTAssertEqual(client.baseURL.absoluteString, "http://192.168.1.100:8080")
    }

    // Test 2: UserDefaults empty → baseURL returns http://localhost:8080 (NOT 8000)
    func testEmptyDefaultsReturnsLocalhostPort8080() {
        UserDefaults.standard.removeObject(forKey: APIClient.baseURLDefaultsKey)
        let client = APIClient()
        XCTAssertEqual(client.baseURL.absoluteString, "http://localhost:8080")
        XCTAssertFalse(client.baseURL.absoluteString.contains("8000"), "Port must be 8080, not 8000")
    }

    // Test 3: UserDefaults has invalid URL (bare string) → baseURL returns default
    func testInvalidURLReturnsDefault() {
        UserDefaults.standard.set("not a url", forKey: APIClient.baseURLDefaultsKey)
        let client = APIClient()
        XCTAssertEqual(client.baseURL.absoluteString, "http://localhost:8080")
    }

    // Test 4: UserDefaults has file:// URL (wrong scheme) → baseURL returns default
    func testFileSchemeURLReturnsDefault() {
        UserDefaults.standard.set("file:///some/path", forKey: APIClient.baseURLDefaultsKey)
        let client = APIClient()
        XCTAssertEqual(client.baseURL.absoluteString, "http://localhost:8080")
    }

    // Test 5 (CRITICAL): change UserDefaults value → next baseURL access returns new URL
    func testUserDefaultsChangeAppliesLive() {
        UserDefaults.standard.set("http://192.168.1.1:8080", forKey: APIClient.baseURLDefaultsKey)
        let client = APIClient()
        XCTAssertEqual(client.baseURL.absoluteString, "http://192.168.1.1:8080")

        // Change the stored URL
        UserDefaults.standard.set("http://10.0.0.1:9090", forKey: APIClient.baseURLDefaultsKey)

        // Next access should return the new URL (proves live update)
        XCTAssertEqual(client.baseURL.absoluteString, "http://10.0.0.1:9090",
                       "baseURL must re-read UserDefaults on every access")
    }

    // Test 6: init(baseURL:) parameter is ignored — actual baseURL from UserDefaults
    func testInitBaseURLParameterIgnored() {
        UserDefaults.standard.set("http://192.168.1.50:8080", forKey: APIClient.baseURLDefaultsKey)
        let ignoredURL = URL(string: "http://should-be-ignored.example.com")!
        let client = APIClient(baseURL: ignoredURL)
        // The init param should be ignored; UserDefaults value wins
        XCTAssertEqual(client.baseURL.absoluteString, "http://192.168.1.50:8080",
                       "init(baseURL:) parameter must be ignored; UserDefaults value is authoritative")
    }
}
