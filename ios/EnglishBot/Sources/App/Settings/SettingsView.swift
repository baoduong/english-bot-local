import SwiftUI
import DesignSystem
#if canImport(UIKit)
import UIKit
#endif

// MARK: - SettingsMode

public enum SettingsMode {
    case normal
    case setupRequired
}

// MARK: - SettingsView

public struct SettingsView: View {
    @State private var baseURL: String
    @State private var testResult: String?
    @State private var isTesting = false
    @State private var isSavingAndContinuing = false

    private let mode: SettingsMode
    private let store: UserDefaults
    private let onSaveAndContinue: (() async -> Void)?
    private let reachabilityProbe: ((URL, TimeInterval) async -> ReachabilityStatus)?

    public init(
        mode: SettingsMode = .normal,
        store: UserDefaults = .standard,
        onSaveAndContinue: (() async -> Void)? = nil,
        reachabilityProbe: ((URL, TimeInterval) async -> ReachabilityStatus)? = nil
    ) {
        self.mode = mode
        self.store = store
        self.onSaveAndContinue = onSaveAndContinue
        self.reachabilityProbe = reachabilityProbe
        self._baseURL = State(initialValue: store.string(forKey: "eb_apiBaseURL") ?? "")
    }

    public var body: some View {
        Form {
            if mode == .setupRequired {
                Section {
                    Label("Backend not configured", systemImage: "wifi.exclamationmark")
                        .foregroundColor(Color.BotTheme.scorePoor)
                    Text("Enter your backend URL below to continue.")
                        .font(Font.BotTheme.bodySecondary)
                }
            }

            Section {
                TextField("http://192.168.1.x:8080", text: $baseURL)
                    #if canImport(UIKit)
                    .keyboardType(UIKeyboardType.URL)
                    .textInputAutocapitalization(.never)
                    .autocorrectionDisabled(true)
                    #endif

                if mode == .normal {
                    Button(action: testConnection) {
                        if isTesting {
                            ProgressView()
                        } else {
                            Label("Test Connection", systemImage: "network")
                        }
                    }
                    .disabled(isTesting)
                }

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

            if mode == .normal {
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

            if mode == .setupRequired {
                Section {
                    Button(action: {
                        Task { await saveAndContinue() }
                    }) {
                        if isSavingAndContinuing {
                            ProgressView()
                        } else {
                            Label("Save & Continue", systemImage: "arrow.right.circle.fill")
                        }
                    }
                    .disabled(baseURL.isEmpty || isSavingAndContinuing)
                }
            }
        }
        .navigationTitle("Settings")
        .onChange(of: baseURL) { newValue in
            store.set(newValue, forKey: "eb_apiBaseURL")
        }
    }

    // MARK: - Actions

    private func testConnection() {
        isTesting = true
        Task {
            defer { isTesting = false }
            do {
                let trimmedBaseURL = baseURL.trimmingCharacters(in: .whitespacesAndNewlines)
                let candidate = trimmedBaseURL.isEmpty ? "http://localhost:8080" : trimmedBaseURL
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

    private func saveAndContinue() async {
        isSavingAndContinuing = true
        defer { isSavingAndContinuing = false }

        let trimmed = baseURL.trimmingCharacters(in: .whitespacesAndNewlines)

        guard let url = URL(string: trimmed),
              let scheme = url.scheme,
              (scheme == "http" || scheme == "https") else {
            testResult = "❌ URL must start with http:// or https://"
            return
        }

        let probe = reachabilityProbe ?? { url, timeout in
            await Reachability.probe(baseURL: url, timeout: timeout)
        }

        let status = await probe(url, 20.0)

        switch status {
        case .healthy:
            await onSaveAndContinue?()
        case .degraded(let reason):
            testResult = "❌ Backend degraded: \(reason)"
        case .unreachable(let reason):
            testResult = "❌ \(reason)"
        }
    }

    private func validatedURL(from rawValue: String) throws -> URL {
        guard let url = URL(string: rawValue) else {
            throw URLError(.badURL)
        }
        return url
    }
}
