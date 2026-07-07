import Foundation
import SwiftUI

public enum APIError: Error {
    case invalidURL
    case networkError(Error)
    case decodingError(Error)
    case httpError(Int)
    case invalidResponse
}

public class APIClient: ObservableObject {
    // MARK: - UserDefaults key (internal for testability)
    static let baseURLDefaultsKey = "eb_apiBaseURL"

    public static let shared = APIClient()
    public static let configuredSession: URLSession = {
        let config = URLSessionConfiguration.default
        config.timeoutIntervalForRequest = 30
        config.timeoutIntervalForResource = 180
        config.waitsForConnectivity = true
        return URLSession(configuration: config)
    }()

    // MARK: - Computed baseURL (re-reads UserDefaults on every access — live update)
    /// P0-4 / P1-5: Computed property reads current UserDefaults value per call.
    /// Fallback is http://localhost:8080 (matches Windows scripts default, NOT 8000).
    public var baseURL: URL { Self.readCurrentBaseURL() }

    private let session: URLSession

    /// Keep init signature for backward compat. The `baseURL` parameter is IGNORED —
    /// actual URL always comes from UserDefaults via computed property.
    public init(baseURL: URL = URL(string: "http://localhost:8080")!, session: URLSession = APIClient.configuredSession) {
        #if DEBUG
        if baseURL.absoluteString != "http://localhost:8080" {
            print("⚠️ [APIClient] init(baseURL:) parameter ignored — URL always read from UserDefaults")
        }
        #endif
        self.session = session
    }

    // MARK: - Private URL resolution

    private static func readCurrentBaseURL() -> URL {
        if let storedValue = UserDefaults.standard.string(forKey: baseURLDefaultsKey) {
            let trimmed = storedValue.trimmingCharacters(in: .whitespacesAndNewlines)
            if !trimmed.isEmpty,
               let url = URL(string: trimmed),
               let scheme = url.scheme,
               (scheme == "http" || scheme == "https") {
                return url
            }
        }
        return URL(string: "http://localhost:8080")!
    }

    // MARK: - Decode / Encode helpers

    private func decode<T: Decodable>(_ data: Data, type: T.Type) throws -> T {
        let decoder = JSONDecoder()
        do {
            return try decoder.decode(T.self, from: data)
        } catch let DecodingError.keyNotFound(key, context) {
            print("❌ [APIClient] Missing key '\(key.stringValue)' at \(context.codingPath.map { $0.stringValue }.joined(separator: "."))")
            throw APIError.decodingError(DecodingError.keyNotFound(key, context))
        } catch let DecodingError.typeMismatch(expectedType, context) {
            print("❌ [APIClient] Type mismatch: expected \(expectedType) at \(context.codingPath.map { $0.stringValue }.joined(separator: "."))")
            throw APIError.decodingError(DecodingError.typeMismatch(expectedType, context))
        } catch let DecodingError.valueNotFound(expectedType, context) {
            print("❌ [APIClient] Value not found: \(expectedType) at \(context.codingPath.map { $0.stringValue }.joined(separator: "."))")
            throw APIError.decodingError(DecodingError.valueNotFound(expectedType, context))
        } catch {
            throw APIError.decodingError(error)
        }
    }

    private func encode<T: Encodable>(_ payload: T) throws -> Data {
        let encoder = JSONEncoder()
        return try encoder.encode(payload)
    }

    // MARK: - Onboarding

    public func startOnboarding(userId: String) async throws -> OnboardingTurnResponse {
        guard let url = URL(string: "/onboarding/start", relativeTo: baseURL) else { throw APIError.invalidURL }
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try encode(OnboardingStartRequest(userId: userId, resumeIfExists: true))

        let (data, response) = try await session.data(for: request)
        guard let httpResponse = response as? HTTPURLResponse else { throw APIError.invalidResponse }
        if !(200...299).contains(httpResponse.statusCode) { throw APIError.httpError(httpResponse.statusCode) }

        return try decode(data, type: OnboardingTurnResponse.self)
    }

    public func respondOnboarding(userId: String, message: String) async throws -> OnboardingRespondResponse {
        guard let url = URL(string: "/onboarding/respond", relativeTo: baseURL) else { throw APIError.invalidURL }
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try encode(OnboardingRespondRequest(userId: userId, message: message))

        let (data, response) = try await session.data(for: request)
        guard let httpResponse = response as? HTTPURLResponse else { throw APIError.invalidResponse }
        if !(200...299).contains(httpResponse.statusCode) { throw APIError.httpError(httpResponse.statusCode) }

        return try decode(data, type: OnboardingRespondResponse.self)
    }

    public func confirmOnboarding(userId: String, confirmed: Bool) async throws -> OnboardingConfirmResponse {
        guard let url = URL(string: "/onboarding/confirm", relativeTo: baseURL) else { throw APIError.invalidURL }
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try encode(OnboardingConfirmRequest(userId: userId, confirmed: confirmed))

        let (data, response) = try await session.data(for: request)
        guard let httpResponse = response as? HTTPURLResponse else { throw APIError.invalidResponse }
        if !(200...299).contains(httpResponse.statusCode) { throw APIError.httpError(httpResponse.statusCode) }

        return try decode(data, type: OnboardingConfirmResponse.self)
    }

    public func getCurrentCurriculum(userId: String) async throws -> CurrentCurriculumResponse {
        guard let url = URL(string: "/curriculum/current?user_id=\(userId)", relativeTo: baseURL) else { throw APIError.invalidURL }
        var request = URLRequest(url: url)
        request.httpMethod = "GET"

        let (data, response) = try await session.data(for: request)
        guard let httpResponse = response as? HTTPURLResponse else { throw APIError.invalidResponse }
        if !(200...299).contains(httpResponse.statusCode) { throw APIError.httpError(httpResponse.statusCode) }

        return try decode(data, type: CurrentCurriculumResponse.self)
    }

    public func getPhaseDetail(phaseId: Int) async throws -> PhaseDetailResponse {
        guard let url = URL(string: "/curriculum/phase/\(phaseId)", relativeTo: baseURL) else { throw APIError.invalidURL }
        var request = URLRequest(url: url)
        request.httpMethod = "GET"

        let (data, response) = try await session.data(for: request)
        guard let httpResponse = response as? HTTPURLResponse else { throw APIError.invalidResponse }
        if !(200...299).contains(httpResponse.statusCode) { throw APIError.httpError(httpResponse.statusCode) }

        return try decode(data, type: PhaseDetailResponse.self)
    }

    public func advancePhase(userId: String) async throws -> AdvancePhaseResponse {
        guard let url = URL(string: "/curriculum/advance-phase", relativeTo: baseURL) else { throw APIError.invalidURL }
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try encode(["user_id": userId])
        let (data, response) = try await session.data(for: request)
        guard let httpResponse = response as? HTTPURLResponse else { throw APIError.invalidResponse }
        if !(200...299).contains(httpResponse.statusCode) { throw APIError.httpError(httpResponse.statusCode) }
        return try decode(data, type: AdvancePhaseResponse.self)
    }

    // MARK: - Practice

    public func startPracticeSession(userId: String, resumeIfExists: Bool = true) async throws -> PracticeSessionStateResponse {
        guard let url = URL(string: "/practice/session/start", relativeTo: baseURL) else { throw APIError.invalidURL }
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try encode(PracticeSessionStartRequest(userId: userId, resumeIfExists: resumeIfExists))
        let (data, response) = try await session.data(for: request)
        guard let httpResponse = response as? HTTPURLResponse else { throw APIError.invalidResponse }
        if !(200...299).contains(httpResponse.statusCode) { throw APIError.httpError(httpResponse.statusCode) }
        return try decode(data, type: PracticeSessionStateResponse.self)
    }

    public func getPracticeState(userId: String) async throws -> PracticeSessionStateResponse {
        guard let url = URL(string: "/practice/session/state?user_id=\(userId)", relativeTo: baseURL) else { throw APIError.invalidURL }
        var request = URLRequest(url: url)
        request.httpMethod = "GET"
        let (data, response) = try await session.data(for: request)
        guard let httpResponse = response as? HTTPURLResponse else { throw APIError.invalidResponse }
        if !(200...299).contains(httpResponse.statusCode) { throw APIError.httpError(httpResponse.statusCode) }
        return try decode(data, type: PracticeSessionStateResponse.self)
    }

    public func skipPracticeItem(userId: String) async throws -> PracticeSkipResponse {
        guard let url = URL(string: "/practice/session/skip", relativeTo: baseURL) else { throw APIError.invalidURL }
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try encode(PracticeSessionActionRequest(userId: userId))
        let (data, response) = try await session.data(for: request)
        guard let httpResponse = response as? HTTPURLResponse else { throw APIError.invalidResponse }
        if !(200...299).contains(httpResponse.statusCode) { throw APIError.httpError(httpResponse.statusCode) }
        return try decode(data, type: PracticeSkipResponse.self)
    }

    public func stopPracticeSession(userId: String) async throws -> PracticeStopResponse {
        guard let url = URL(string: "/practice/session/stop", relativeTo: baseURL) else { throw APIError.invalidURL }
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try encode(PracticeSessionActionRequest(userId: userId))
        let (data, response) = try await session.data(for: request)
        guard let httpResponse = response as? HTTPURLResponse else { throw APIError.invalidResponse }
        if !(200...299).contains(httpResponse.statusCode) { throw APIError.httpError(httpResponse.statusCode) }
        return try decode(data, type: PracticeStopResponse.self)
    }

    public func scorePracticeAudio(userId: String, audioURL: URL, contentId: Int? = nil, expectedText: String? = nil) async throws -> PracticeAudioResponse {
        guard let url = URL(string: "/practice/audio", relativeTo: baseURL) else { throw APIError.invalidURL }
        let boundary = "Boundary-\(UUID().uuidString)"
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("multipart/form-data; boundary=\(boundary)", forHTTPHeaderField: "Content-Type")

        var body = Data()
        func appendField(_ name: String, _ value: String) {
            body.append("--\(boundary)\r\n".data(using: .utf8)!)
            body.append("Content-Disposition: form-data; name=\"\(name)\"\r\n\r\n".data(using: .utf8)!)
            body.append("\(value)\r\n".data(using: .utf8)!)
        }
        appendField("user_id", userId)
        if let contentId = contentId { appendField("content_id", String(contentId)) }
        if let expectedText = expectedText { appendField("expected_text", expectedText) }

        let fileData = try Data(contentsOf: audioURL)
        body.append("--\(boundary)\r\n".data(using: .utf8)!)
        body.append("Content-Disposition: form-data; name=\"audio_file\"; filename=\"practice.m4a\"\r\n".data(using: .utf8)!)
        body.append("Content-Type: audio/m4a\r\n\r\n".data(using: .utf8)!)
        body.append(fileData)
        body.append("\r\n".data(using: .utf8)!)
        body.append("--\(boundary)--\r\n".data(using: .utf8)!)
        request.httpBody = body

        let (data, response) = try await session.data(for: request)
        guard let httpResponse = response as? HTTPURLResponse else { throw APIError.invalidResponse }
        if !(200...299).contains(httpResponse.statusCode) { throw APIError.httpError(httpResponse.statusCode) }
        return try decode(data, type: PracticeAudioResponse.self)
    }

    public func getPendingCoaching(userId: String) async throws -> CoachingPendingResponse {
        let url = baseURL.appendingPathComponent("practice/coaching/pending")
        var components = URLComponents(url: url, resolvingAgainstBaseURL: false)!
        components.queryItems = [URLQueryItem(name: "user_id", value: userId)]
        var request = URLRequest(url: components.url!)
        request.httpMethod = "GET"

        let (data, response) = try await session.data(for: request)
        guard let httpResponse = response as? HTTPURLResponse else { throw APIError.invalidResponse }
        if !(200...299).contains(httpResponse.statusCode) { throw APIError.httpError(httpResponse.statusCode) }

        return try decode(data, type: CoachingPendingResponse.self)
    }

    public func ackCoaching(userId: String, ackToken: String) async throws -> CoachingAckResponse {
        let url = baseURL.appendingPathComponent("practice/coaching/ack")
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try encode(CoachingAckRequest(userId: userId, ackToken: ackToken))

        let (data, response) = try await session.data(for: request)
        guard let httpResponse = response as? HTTPURLResponse else { throw APIError.invalidResponse }
        if !(200...299).contains(httpResponse.statusCode) { throw APIError.httpError(httpResponse.statusCode) }

        return try decode(data, type: CoachingAckResponse.self)
    }

    public func scoreScratch(userId: String, audioURL: URL, targetText: String) async throws -> ScratchScoringResult {
        guard let url = URL(string: "/practice/scratch-score", relativeTo: baseURL) else { throw APIError.invalidURL }
        let boundary = "Boundary-\(UUID().uuidString)"
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("multipart/form-data; boundary=\(boundary)", forHTTPHeaderField: "Content-Type")

        var body = Data()
        func appendField(_ name: String, _ value: String) {
            body.append("--\(boundary)\r\n".data(using: .utf8)!)
            body.append("Content-Disposition: form-data; name=\"\(name)\"\r\n\r\n".data(using: .utf8)!)
            body.append("\(value)\r\n".data(using: .utf8)!)
        }

        appendField("user_id", userId)
        appendField("target_text", targetText)

        let fileData = try Data(contentsOf: audioURL)
        body.append("--\(boundary)\r\n".data(using: .utf8)!)
        body.append("Content-Disposition: form-data; name=\"audio_file\"; filename=\"scratch.m4a\"\r\n".data(using: .utf8)!)
        body.append("Content-Type: audio/m4a\r\n\r\n".data(using: .utf8)!)
        body.append(fileData)
        body.append("\r\n".data(using: .utf8)!)
        body.append("--\(boundary)--\r\n".data(using: .utf8)!)
        request.httpBody = body

        let (data, response) = try await session.data(for: request)
        guard let httpResponse = response as? HTTPURLResponse else { throw APIError.invalidResponse }
        if !(200...299).contains(httpResponse.statusCode) { throw APIError.httpError(httpResponse.statusCode) }
        return try decode(data, type: ScratchScoringResult.self)
    }

    public func getProgress(userId: String) async throws -> ProgressResponse {
        guard let url = URL(string: "/progress?user_id=\(userId)", relativeTo: baseURL) else { throw APIError.invalidURL }
        var request = URLRequest(url: url)
        request.httpMethod = "GET"
        let (data, response) = try await session.data(for: request)
        guard let httpResponse = response as? HTTPURLResponse else { throw APIError.invalidResponse }
        if !(200...299).contains(httpResponse.statusCode) { throw APIError.httpError(httpResponse.statusCode) }
        return try decode(data, type: ProgressResponse.self)
    }

    public func archiveCurriculum(userId: String) async throws -> ArchiveCurriculumResponse {
        guard let url = URL(string: "/curriculum/archive", relativeTo: baseURL) else { throw APIError.invalidURL }
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try encode(ArchiveCurriculumRequest(userId: userId, confirm: true))
        let (data, response) = try await session.data(for: request)
        guard let httpResponse = response as? HTTPURLResponse else { throw APIError.invalidResponse }
        if !(200...299).contains(httpResponse.statusCode) { throw APIError.httpError(httpResponse.statusCode) }
        return try decode(data, type: ArchiveCurriculumResponse.self)
    }

    public func sampleAudioURL(userId: String, word: String? = nil, expectedText: String? = nil, slow: Bool = false) -> URL? {
        var components = "/practice/audio/sample?user_id=\(userId.addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed) ?? userId)"
        if let word = word, let enc = word.addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed) {
            components += "&word=\(enc)"
        } else if let expectedText = expectedText, let enc = expectedText.addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed) {
            components += "&expected_text=\(enc)"
        }
        if slow {
            components += "&slow=true"
        }
        return URL(string: components, relativeTo: baseURL)
    }
}
