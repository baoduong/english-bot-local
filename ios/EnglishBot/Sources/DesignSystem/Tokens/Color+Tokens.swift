import SwiftUI
#if canImport(UIKit)
import UIKit
#endif

public extension Color {
    enum BotTheme {
        // Semantic Colors
        public static let primary = Color(red: 0.2, green: 0.5, blue: 0.9)
        public static let secondary = Color(red: 0.4, green: 0.7, blue: 1.0)

        // Status Colors (Matching Discord Bot's ANSI feedback)
        public static let scoreExcellent = Color.green // >= 80
        public static let scoreAverage = Color.yellow  // >= 60
        public static let scorePoor = Color.red        // < 60

        // Backgrounds
        #if canImport(UIKit)
        public static let backgroundMain = Color(uiColor: .systemBackground)
        public static let backgroundSecondary = Color(uiColor: .secondarySystemBackground)
        public static let backgroundTertiary = Color(uiColor: .tertiarySystemBackground)
        #else
        public static let backgroundMain = Color(nsColor: .windowBackgroundColor)
        public static let backgroundSecondary = Color(nsColor: .controlBackgroundColor)
        public static let backgroundTertiary = Color(nsColor: .textBackgroundColor)
        #endif

        // Text
        #if canImport(UIKit)
        public static let textPrimary = Color(uiColor: .label)
        public static let textSecondary = Color(uiColor: .secondaryLabel)
        public static let textTertiary = Color(uiColor: .tertiaryLabel)
        #else
        public static let textPrimary = Color(nsColor: .labelColor)
        public static let textSecondary = Color(nsColor: .secondaryLabelColor)
        public static let textTertiary = Color(nsColor: .tertiaryLabelColor)
        #endif

        // Borders & Dividers
        #if canImport(UIKit)
        public static let border = Color(uiColor: .separator)
        #else
        public static let border = Color(nsColor: .separatorColor)
        #endif

        // Chat Bubbles
        public static let chatUser = Color.blue
        #if canImport(UIKit)
        public static let chatAI = Color(uiColor: .secondarySystemBackground)
        #else
        public static let chatAI = Color(nsColor: .controlBackgroundColor)
        #endif

        // Fallbacks for missing assets to ensure preview works immediately
        public static let fallbackPrimary = Color(red: 0.2, green: 0.5, blue: 0.9)
    }
}
