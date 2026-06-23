import Foundation

@MainActor
public class ProgressViewModel: ObservableObject {
    @Published public var progress: ProgressResponse?
    @Published public var isLoading: Bool = false
    @Published public var isResettingGoal: Bool = false
    @Published public var error: String?

    private let userId: String
    private let apiClient: APIClient

    public init(userId: String, apiClient: APIClient = APIClient.shared) {
        self.userId = userId
        self.apiClient = apiClient
    }

    public func fetchProgress() async {
        isLoading = true
        error = nil
        do {
            progress = try await apiClient.getProgress(userId: userId)
        } catch {
            self.error = error.localizedDescription
        }
        isLoading = false
    }

    public func resetGoal() async -> Bool {
        isResettingGoal = true
        error = nil
        defer { isResettingGoal = false }
        do {
            _ = try await apiClient.archiveCurriculum(userId: userId)
            return true
        } catch {
            self.error = error.localizedDescription
            return false
        }
    }
}
