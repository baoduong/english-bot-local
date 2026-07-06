import SwiftUI
import DesignSystem
#if canImport(UIKit)
import UIKit
#endif

public struct SettingsView: View {
    @AppStorage("eb_apiBaseURL") private var baseURL: String = ""
    @State private var testResult: String?
    @State private var isTesting = false

    public init() {}

    public var body: some View {
        Form {
            Section {
                TextField("http://192.168.1.x:8000", text: $baseURL)
                    #if canImport(UIKit)
                    .keyboardType(UIKeyboardType.URL)
                    .textInputAutocapitalization(.never)
                    .autocorrectionDisabled(true)
                    #endif

                Button(action: testConnection) {
                    if isTesting {
                        ProgressView()
                    } else {
                        Label("Test Connection", systemImage: "network")
                    }
                }
                .disabled(isTesting)

                if let result = testResult {
                    HStack(spacing: Spacing.sm) {
                        Image(systemName: result.contains("✅") ? "checkmark.circle.fill" : "xmark.circle.fill")
                        Text(result.replacingOccurrences(of: "✅ ", with: "").replacingOccurrences(of: "❌ ", with: ""))
                    }
                    .foregroundColor(result.contains("✅") ? Color.BotTheme.scoreExcellent : Color.BotTheme.scorePoor)
                }
            } header: {
                Label("Backend URL", systemImage: "server.rack")
            }

            Section {
                Button(action: {
                    Task {
                        if let url = await BonjourDiscovery().discover(timeout: 5.0) {
                            baseURL = url.absoluteString
                            testResult = "✅ Found: \(url.absoluteString)"
                        } else {
                            testResult = "❌ No backend found on network"
                        }
                    }
                }) {
                    Label("Re-discover via Bonjour", systemImage: "magnifyingglass")
                }
            } header: {
                Label("Discovery", systemImage: "antenna.radiowaves.left.and.right")
            }
        }
        .navigationTitle("Settings")
    }

    private func testConnection() {
        isTesting = true

        Task {
            defer { isTesting = false }

            do {
                let trimmedBaseURL = baseURL.trimmingCharacters(in: .whitespacesAndNewlines)
                let candidate = trimmedBaseURL.isEmpty ? "http://localhost:8000" : trimmedBaseURL
                let url = try validatedURL(from: candidate)
                let (_, response) = try await URLSession.shared.data(from: url.appendingPathComponent("health"))

                if let http = response as? HTTPURLResponse, http.statusCode == 200 {
                    testResult = "✅ Connected!"
                } else {
                    testResult = "❌ Server returned error"
                }
            } catch {
                testResult = "❌ \(error.localizedDescription)"
            }
        }
    }

    private func validatedURL(from rawValue: String) throws -> URL {
        guard let url = URL(string: rawValue) else {
            throw URLError(.badURL)
        }

        return url
    }
}
