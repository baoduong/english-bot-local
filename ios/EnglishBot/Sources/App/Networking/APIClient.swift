import Foundation

public enum APIError: Error {
    case invalidURL
    case networkError(Error)
    case decodingError(Error)
    case httpError(Int)
    case invalidResponse
}

public class APIClient: ObservableObject {
    public let baseURL: URL
    private let session: URLSession
    
    public init(baseURL: URL = URL(string: "http://localhost:8000")!, session: URLSession = .shared) {
        self.baseURL = baseURL
        self.session = session
    }
    
    private func decode<T: Decodable>(_ data: Data, type: T.Type) throws -> T {
        let decoder = JSONDecoder()
        // If dates are used, uncomment and configure date format
        // decoder.dateDecodingStrategy = .iso8601
        return try decoder.decode(T.self, from: data)
    }
    
    private func encode<T: Encodable>(_ payload: T) throws -> Data {
        let encoder = JSONEncoder()
        return try encoder.encode(payload)
    }
    
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
}
