import SwiftUI
#if canImport(UIKit)
import UIKit
public typealias PlatformColor = UIColor
#elseif canImport(AppKit)
import AppKit
public typealias PlatformColor = NSColor
#endif

public extension Color {
    /// Warm & friendly design system for a learning app.
    ///
    /// Palette philosophy:
    /// - Single considered accent (soft indigo) + one supporting hue (teal), both < 80% saturation.
    /// - Warm-tinted neutral surfaces layered for depth (base → raised → sunken).
    /// - Desaturated, calmer scoring colors so feedback encourages rather than alarms.
    /// - Colors adapt to light/dark via dynamic UIColor providers.
    enum BotTheme {

        // MARK: - Brand Accent

        /// Primary brand accent — soft indigo. Encouraging, not harsh.
        public static let primary = dynamic(
            light: PlatformColor(red: 0.36, green: 0.42, blue: 0.86, alpha: 1),   // #5C6BDB
            dark:  PlatformColor(red: 0.51, green: 0.56, blue: 0.94, alpha: 1)    // #838FF0
        )

        /// Softer tint of the accent for gradients / secondary emphasis.
        public static let secondary = dynamic(
            light: PlatformColor(red: 0.30, green: 0.68, blue: 0.71, alpha: 1),   // teal #4CADB5
            dark:  PlatformColor(red: 0.42, green: 0.78, blue: 0.80, alpha: 1)
        )

        /// A very soft wash of the accent for card backgrounds / highlights.
        public static let accentSoft = dynamic(
            light: PlatformColor(red: 0.36, green: 0.42, blue: 0.86, alpha: 0.10),
            dark:  PlatformColor(red: 0.51, green: 0.56, blue: 0.94, alpha: 0.16)
        )

        /// Accent gradient for hero elements (record button, primary CTAs).
        public static let accentGradient = LinearGradient(
            colors: [primary, secondary],
            startPoint: .topLeading,
            endPoint: .bottomTrailing
        )

        // MARK: - Status / Scoring Colors (desaturated, calmer)

        /// >= 80 — confident green, softened.
        public static let scoreExcellent = dynamic(
            light: PlatformColor(red: 0.24, green: 0.66, blue: 0.47, alpha: 1),   // #3DA878
            dark:  PlatformColor(red: 0.36, green: 0.78, blue: 0.58, alpha: 1)
        )
        /// >= 60 — warm amber instead of harsh yellow.
        public static let scoreAverage = dynamic(
            light: PlatformColor(red: 0.90, green: 0.62, blue: 0.24, alpha: 1),   // #E69E3D
            dark:  PlatformColor(red: 0.96, green: 0.72, blue: 0.36, alpha: 1)
        )
        /// < 60 — muted coral, not alarm-red.
        public static let scorePoor = dynamic(
            light: PlatformColor(red: 0.87, green: 0.40, blue: 0.40, alpha: 1),   // #DE6666
            dark:  PlatformColor(red: 0.94, green: 0.51, blue: 0.51, alpha: 1)
        )

        // MARK: - Backgrounds (warm-tinted neutral layers)

        /// App base background — very slightly warm off-white / near-black.
        public static let backgroundMain = dynamic(
            light: PlatformColor(red: 0.98, green: 0.98, blue: 0.97, alpha: 1),   // warm #FAFAF7
            dark:  PlatformColor(red: 0.07, green: 0.07, blue: 0.08, alpha: 1)    // tinted #121214
        )
        /// Raised surface — cards, panels.
        public static let backgroundSecondary = dynamic(
            light: PlatformColor(red: 1.00, green: 1.00, blue: 0.99, alpha: 1),   // #FFFFFC
            dark:  PlatformColor(red: 0.12, green: 0.12, blue: 0.14, alpha: 1)    // #1E1E23
        )
        /// Sunken / tertiary surface — inset fields, nested chips.
        public static let backgroundTertiary = dynamic(
            light: PlatformColor(red: 0.95, green: 0.95, blue: 0.93, alpha: 1),   // #F2F2ED
            dark:  PlatformColor(red: 0.16, green: 0.16, blue: 0.19, alpha: 1)    // #292930
        )

        // MARK: - Text

        public static let textPrimary = dynamic(
            light: PlatformColor(red: 0.11, green: 0.11, blue: 0.13, alpha: 1),
            dark:  PlatformColor(red: 0.96, green: 0.96, blue: 0.97, alpha: 1)
        )
        public static let textSecondary = dynamic(
            light: PlatformColor(red: 0.40, green: 0.40, blue: 0.43, alpha: 1),
            dark:  PlatformColor(red: 0.68, green: 0.68, blue: 0.72, alpha: 1)
        )
        public static let textTertiary = dynamic(
            light: PlatformColor(red: 0.60, green: 0.60, blue: 0.63, alpha: 1),
            dark:  PlatformColor(red: 0.48, green: 0.48, blue: 0.52, alpha: 1)
        )

        // MARK: - Borders & Dividers (subtle, warm-tinted)

        public static let border = dynamic(
            light: PlatformColor(red: 0.89, green: 0.89, blue: 0.86, alpha: 1),
            dark:  PlatformColor(red: 0.24, green: 0.24, blue: 0.27, alpha: 1)
        )

        // MARK: - Chat Bubbles

        /// User bubble uses the brand accent.
        public static let chatUser = primary
        /// AI bubble uses a soft raised neutral.
        public static let chatAI = backgroundTertiary

        // MARK: - Elevation (tinted shadows, not pure black)

        /// Soft ambient shadow tinted toward the accent hue for warmth.
        public static let shadowColor = dynamic(
            light: PlatformColor(red: 0.20, green: 0.22, blue: 0.40, alpha: 0.10),
            dark:  PlatformColor(red: 0.00, green: 0.00, blue: 0.00, alpha: 0.45)
        )

        // Fallback for previews.
        public static let fallbackPrimary = Color(red: 0.36, green: 0.42, blue: 0.86)

        // MARK: - Dynamic color helper

        /// Builds a Color that adapts to light/dark appearance.
        private static func dynamic(light: PlatformColor, dark: PlatformColor) -> Color {
            #if canImport(UIKit)
            return Color(uiColor: UIColor { traits in
                traits.userInterfaceStyle == .dark ? dark : light
            })
            #elseif canImport(AppKit)
            return Color(nsColor: NSColor(name: nil) { appearance in
                let isDark = appearance.bestMatch(from: [.darkAqua, .aqua]) == .darkAqua
                return isDark ? dark : light
            })
            #else
            return Color(light)
            #endif
        }
    }
}
