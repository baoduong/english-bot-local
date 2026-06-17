import Foundation

public class WebSocketClient: ObservableObject {
    private var webSocketTask: URLSessionWebSocketTask?
    private let baseURL: URL
    private let session = URLSession(configuration: .default)
    
    // Use AsyncStream setup
    private var eventContinuation: AsyncStream<WebSocketEnvelope>.Continuation?
    public var events: AsyncStream<WebSocketEnvelope>?
    
    public init(baseURL: URL = URL(string: "ws://localhost:8000")!) {
        self.baseURL = baseURL
    }
    
    public func connect(userId: String) {
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
