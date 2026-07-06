import Foundation
import Combine

@MainActor
public class CurriculumViewModel: ObservableObject {
    @Published public var curriculum: CurriculumSummary?
    @Published public var activePhase: CurriculumPhase?
    @Published public var phaseDetail: PhaseDetailResponse?
    @Published public var isLoading = false
    @Published public var isGeneratingCurriculum = false
    @Published public var errorMessage: String?

    private let apiClient: APIClient
    private let userId: String
    private var generationRetryTask: Task<Void, Never>?

    public init(userId: String, apiClient: APIClient = APIClient.shared) {
        self.userId = userId
        self.apiClient = apiClient
    }

    public func load() async {
        generationRetryTask?.cancel()
        generationRetryTask = nil
        isLoading = true
        isGeneratingCurriculum = false
        errorMessage = nil
        defer { isLoading = false }

        do {
            let response = try await apiClient.getCurrentCurriculum(userId: userId)
            isGeneratingCurriculum = false
            self.curriculum = response.curriculum
            self.activePhase = response.activePhase
            await fetchPhaseDetail(phaseId: response.activePhase.phaseId)
        } catch APIError.httpError(404) {
            isGeneratingCurriculum = true
            scheduleGenerationRetry()
        } catch {
            self.errorMessage = error.localizedDescription
        }
    }

    public func fetchCurrentCurriculum() async {
        await load()
    }

    public func fetchPhaseDetail(phaseId: Int) async {
        do {
            let detail = try await apiClient.getPhaseDetail(phaseId: phaseId)
            self.phaseDetail = detail
        } catch {
            self.errorMessage = error.localizedDescription
        }
    }

    private func scheduleGenerationRetry() {
        generationRetryTask = Task {
            for _ in 0..<20 {
                try? await Task.sleep(nanoseconds: 5_000_000_000)
                guard !Task.isCancelled else { return }
                do {
                    let response = try await apiClient.getCurrentCurriculum(userId: userId)
                    isGeneratingCurriculum = false
                    self.curriculum = response.curriculum
                    self.activePhase = response.activePhase
                    await fetchPhaseDetail(phaseId: response.activePhase.phaseId)
                    return
                } catch {
                    continue
                }
            }
            isGeneratingCurriculum = false
            errorMessage = "Không thể tải lộ trình. Kéo xuống để thử lại."
        }
    }
}
