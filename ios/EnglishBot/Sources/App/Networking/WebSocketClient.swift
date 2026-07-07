import Foundation

public class WebSocketClient: ObservableObject {
    private var webSocketTask: URLSessionWebSocketTask?
    private let session = URLSession(configuration: .default)

    // Use AsyncStream setup
    private var eventContinuation: AsyncStream<WebSocketEnvelope>.Continuation?
    public var events: AsyncStream<WebSocketEnvelope>?

    /// Computed baseURL — re-reads UserDefaults on every access for live URL updates.
    /// Converts http:// → ws:// and https:// → wss://.
    /// Fallback: ws://localhost:8080 (NOT 8000 — matches Windows scripts default).
    private var baseURL: URL { Self.computeWSBaseURL() }

    /// Keep init signature for backward compat. The `baseURL` parameter is IGNORED —
    /// actual URL always comes from UserDefaults via computed property.
    public init(baseURL: URL = URL(string: "ws://localhost:8080")!) {
        #if DEBUG
        if baseURL.absoluteString != "ws://localhost:8080" {
            print("⚠️ [WebSocketClient] init(baseURL:) parameter ignored — URL always read from UserDefaults")
        }
        #endif
    }

    // MARK: - URL Computation

    /// Reads the REST base URL from UserDefaults (same key as APIClient) and converts to WS scheme.
    private static func computeWSBaseURL() -> URL {
        let defaultsKey = "eb_apiBaseURL"
        if let storedValue = UserDefaults.standard.string(forKey: defaultsKey) {
            let trimmed = storedValue.trimmingCharacters(in: .whitespacesAndNewlines)
            if !trimmed.isEmpty, let url = URL(string: trimmed) {
                return httpToWs(url)
            }
        }
        return URL(string: "ws://localhost:8080")!
    }

    /// Converts http:// → ws://, https:// → wss://.
    /// Preserves host, port, and path.
    /// Unknown/missing scheme → fallback ws://localhost:8080.
    static func httpToWs(_ url: URL) -> URL {
        guard var components = URLComponents(url: url, resolvingAgainstBaseURL: false) else {
            return URL(string: "ws://localhost:8080")!
        }

        switch components.scheme {
        case "http":
            components.scheme = "ws"
        case "https":
            components.scheme = "wss"
        case "ws", "wss":
            // Already WS scheme — return as-is
            return url
        default:
            return URL(string: "ws://localhost:8080")!
        }

        return components.url ?? URL(string: "ws://localhost:8080")!
    }

    // MARK: - Connection

    public func connect(userId: String) {
        // Uses computed baseURL — always fresh URL for new connections
        guard let url = URL(string: "/ws/session?user_id=\(userId)", relativeTo: baseURL) else { return }

        let (stream, continuation) = AsyncStream.makeStream(of: WebSocketEnvelope.self)
        self.events = stream
        self.eventContinuation = continuation

        webSocketTask = session.webSocketTask(with: url)
        webSocketTask?.resume()
        receiveMessage()
    }

    public func disconnect() {
        webSocketTask?.cancel(with: .normalClosure, reason: nil)
        webSocketTask = nil
        eventContinuation?.finish()
    }

    // MARK: - Message Handling

    private func receiveMessage() {
        webSocketTask?.receive { [weak self] result in
            guard let self = self else { return }

            switch result {
            case .success(let message):
                switch message {
                case .string(let text):
                    if let data = text.data(using: .utf8) {
                        self.handleData(data)
                    }
                case .data(let data):
                    self.handleData(data)
                @unknown default:
                    break
                }
                self.receiveMessage() // Continue listening
            case .failure(let error):
                print("WebSocket error: \(error)")
                self.disconnect()
            }
        }
    }

    private func handleData(_ data: Data) {
        let decoder = JSONDecoder()
        do {
            let envelope = try decoder.decode(WebSocketEnvelope.self, from: data)
            eventContinuation?.yield(envelope)
        } catch {
            print("WebSocket decode error: \(error)")
        }
    }
}
