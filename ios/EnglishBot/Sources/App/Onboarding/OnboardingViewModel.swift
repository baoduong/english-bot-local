import Foundation
import Combine

@MainActor
public class OnboardingViewModel: ObservableObject {
    @Published public var messages: [OnboardingMessage] = []
    @Published public var isTyping = false
    @Published public var pendingGoal: GoalSynthesis?
    @Published public var synthesisConfirmed = false
    @Published public var errorMessage: String?
    
    private let apiClient: APIClient
    private let wsClient: WebSocketClient
    private let userId: String
    
    public init(userId: String, apiClient: APIClient = APIClient(), wsClient: WebSocketClient = WebSocketClient()) {
        self.userId = userId
        self.apiClient = apiClient
        self.wsClient = wsClient
    }
    
    public func start() async {
        isTyping = true
        do {
            let response = try await apiClient.startOnboarding(userId: userId)
            self.messages = response.historyPreview
            if let synthesis = response.pendingGoalSynthesis {
                self.pendingGoal = synthesis
            }
        } catch {
            self.errorMessage = error.localizedDescription
        }
        isTyping = false
    }
    
    public func sendMessage(_ text: String) async {
        let userMsg = OnboardingMessage(turnNumber: messages.count + 1, role: "user", content: text)
        messages.append(userMsg)
        
        isTyping = true
        do {
            let response = try await apiClient.respondOnboarding(userId: userId, message: text)
            messages.append(response.assistantMessage)
            
            if response.resultType == "synthesis", let synthesis = response.pendingGoalSynthesis {
                self.pendingGoal = synthesis
            }
        } catch {
            self.errorMessage = error.localizedDescription
        }
        isTyping = false
    }
    
    public func confirmGoal(accepted: Bool) async {
        isTyping = true
        do {
            let response = try await apiClient.confirmOnboarding(userId: userId, confirmed: accepted)
            if response.status == "confirmed" {
                self.synthesisConfirmed = true
            } else {
                self.pendingGoal = nil // Rejected, clear and continue
                // Depending on the backend, it might start over or ask another question. 
                // We'd ideally need to fetch the next state if rejected.
            }
        } catch {
            self.errorMessage = error.localizedDescription
        }
        isTyping = false
    }
}
