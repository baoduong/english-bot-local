import Foundation

// MARK: - ReachabilityStatus

/// Result of a /health probe. Only `.healthy` allows routing to the main app.
/// `.degraded` means backend is up but Ollama/DB is down — routes to Settings with reason.
/// `.unreachable` means no connection at all — routes to Settings with reason.
public enum ReachabilityStatus: Equatable {
    case healthy
    case degraded(String)
    case unreachable(String)

    public static func == (lhs: ReachabilityStatus, rhs: ReachabilityStatus) -> Bool {
        switch (lhs, rhs) {
        case (.healthy, .healthy): return true
        case (.degraded(let a), .degraded(let b)): return a == b
        case (.unreachable(let a), .unreachable(let b)): return a == b
        default: return false
        }
    }
}

// MARK: - Reachability

/// Probes the backend /health endpoint and returns a typed status.
/// Uses a dedicated URLSession per probe for testability (injectable via URLProtocol).
public struct Reachability {

    /// Probe the backend /health endpoint.
    /// - Parameters:
    ///   - baseURL: The base URL of the backend (e.g. http://192.168.1.100:8080)
    ///   - timeout: Request timeout in seconds. Default 20s. Inject 0.1 in tests for speed.
    ///   - sessionConfiguration: Optional custom URLSessionConfiguration for testing (URLProtocol injection).
    /// - Returns: ReachabilityStatus — never throws.
    public static func probe(
        baseURL: URL,
        timeout: TimeInterval = 20.0,
        sessionConfiguration: URLSessionConfiguration? = nil
    ) async -> ReachabilityStatus {
        let healthURL = baseURL.appendingPathComponent("health")

        let config: URLSessionConfiguration
        if let injected = sessionConfiguration {
            config = injected
        } else {
            config = URLSessionConfiguration.ephemeral
            config.timeoutIntervalForRequest = timeout
            config.timeoutIntervalForResource = timeout + 5
        }
        let session = URLSession(configuration: config)

        var request = URLRequest(url: healthURL)
        request.httpMethod = "GET"
        request.timeoutInterval = timeout

        do {
            let (data, response) = try await session.data(for: request)

            guard let httpResponse = response as? HTTPURLResponse else {
                return .unreachable("Invalid response")
            }

            guard httpResponse.statusCode == 200 else {
                return .unreachable("HTTP \(httpResponse.statusCode)")
            }

            // P1-6: Reject captive portal / HTML responses
            let contentType = httpResponse.value(forHTTPHeaderField: "Content-Type") ?? ""
            guard contentType.contains("application/json") else {
                return .unreachable("Captive portal or invalid backend")
            }

            // Parse JSON status field
            guard let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any] else {
                return .degraded("Invalid /health response")
            }

            guard let statusField = json["status"] as? String else {
                return .degraded("Invalid /health response")
            }

            switch statusField {
            case "healthy":
                return .healthy
            case "degraded":
                let reason = json["reason"] as? String ?? "Backend degraded: check Ollama/DB"
                return .degraded(reason)
            default:
                return .degraded("Invalid /health response")
            }

        } catch let urlError as URLError where urlError.code == .timedOut {
            return .unreachable("Request timed out")
        } catch {
            return .unreachable(error.localizedDescription)
        }
    }
}
