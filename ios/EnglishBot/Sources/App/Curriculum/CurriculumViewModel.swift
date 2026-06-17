import Foundation
import Combine

@MainActor
public class CurriculumViewModel: ObservableObject {
    @Published public var curriculum: CurriculumSummary?
    @Published public var activePhase: CurriculumPhase?
    @Published public var phaseDetail: PhaseDetailResponse?
    @Published public var isLoading = false
    @Published public var errorMessage: String?
    
    private let apiClient: APIClient
    private let userId: String
    
    public init(userId: String, apiClient: APIClient = APIClient()) {
        self.userId = userId
        self.apiClient = apiClient
    }
    
    public func fetchCurrentCurriculum() async {
        isLoading = true
        do {
            let response = try await apiClient.getCurrentCurriculum(userId: userId)
            self.curriculum = response.curriculum
            self.activePhase = response.activePhase
            
            // Immediately fetch phase details to get the sentences
            await fetchPhaseDetail(phaseId: response.activePhase.phaseId)
        } catch {
            self.errorMessage = error.localizedDescription
        }
        isLoading = false
    }
    
    public func fetchPhaseDetail(phaseId: Int) async {
        do {
            let detail = try await apiClient.getPhaseDetail(phaseId: phaseId)
            self.phaseDetail = detail
        } catch {
            self.errorMessage = error.localizedDescription
        }
    }
}
