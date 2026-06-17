import SwiftUI

public extension Color {
    enum BotTheme {
        // Semantic Colors
        public static let primary = Color("BrandPrimary")
        public static let secondary = Color("BrandSecondary")
        
        // Status Colors (Matching Discord Bot's ANSI feedback)
        public static let scoreExcellent = Color.green // >= 80
        public static let scoreAverage = Color.yellow  // >= 60
        public static let scorePoor = Color.red        // < 60
        
        // Backgrounds (using system names for SwiftUI to avoid UIKit dependency)
        public static let backgroundMain = Color("systemBackground")
        public static let backgroundSecondary = Color("secondarySystemBackground")
        public static let backgroundTertiary = Color("tertiarySystemBackground")
        
        // Text
        public static let textPrimary = Color("label")
        public static let textSecondary = Color("secondaryLabel")
        public static let textTertiary = Color("tertiaryLabel")
        
        // Borders & Dividers
        public static let border = Color("separator")
        
        // Chat Bubbles
        public static let chatUser = Color.blue
        public static let chatAI = Color("secondarySystemBackground")
        
        // Fallbacks for missing assets to ensure preview works immediately
        public static let fallbackPrimary = Color(red: 0.2, green: 0.5, blue: 0.9)
    }
}
