import Foundation
#if canImport(UIKit)
import UIKit
#endif

/// Lightweight haptic feedback wrapper. Cheap, dependency-free, and a no-op
/// on platforms without a Taptic Engine (macOS), so call sites stay clean.
///
/// Generators are created on demand and `prepare()`d immediately before firing
/// to minimise latency — Apple's recommended pattern for responsive feedback.
public enum Haptics {

    /// A light tap — for selection, word taps, minor toggles.
    public static func selection() {
        #if canImport(UIKit)
        let generator = UISelectionFeedbackGenerator()
        generator.prepare()
        generator.selectionChanged()
        #endif
    }

    /// Impact feedback with a configurable strength — for button presses,
    /// record start/stop.
    public enum Impact {
        case light, medium, heavy, soft, rigid
    }

    public static func impact(_ style: Impact = .medium) {
        #if canImport(UIKit)
        let mapped: UIImpactFeedbackGenerator.FeedbackStyle
        switch style {
        case .light:  mapped = .light
        case .medium: mapped = .medium
        case .heavy:  mapped = .heavy
        case .soft:   mapped = .soft
        case .rigid:  mapped = .rigid
        }
        let generator = UIImpactFeedbackGenerator(style: mapped)
        generator.prepare()
        generator.impactOccurred()
        #endif
    }

    /// Semantic notification feedback — for scoring outcomes.
    public enum Notification {
        case success, warning, error
    }

    public static func notify(_ type: Notification) {
        #if canImport(UIKit)
        let mapped: UINotificationFeedbackGenerator.FeedbackType
        switch type {
        case .success: mapped = .success
        case .warning: mapped = .warning
        case .error:   mapped = .error
        }
        let generator = UINotificationFeedbackGenerator()
        generator.prepare()
        generator.notificationOccurred(mapped)
        #endif
    }

    /// Convenience: map a 0–100 pronunciation score to the right notification.
    public static func forScore(_ score: Int) {
        if score >= 80 { notify(.success) }
        else if score >= 60 { notify(.warning) }
        else { notify(.error) }
    }
}
