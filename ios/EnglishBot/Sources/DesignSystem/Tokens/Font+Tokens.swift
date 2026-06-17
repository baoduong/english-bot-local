import SwiftUI

public extension Font {
    enum BotTheme {
        // App-wide custom font if needed, otherwise using semantic system fonts
        
        /// For large page titles and emphasis
        public static let heading1 = Font.system(.largeTitle, design: .rounded).weight(.bold)
        
        /// For section headers
        public static let heading2 = Font.system(.title2, design: .rounded).weight(.semibold)
        
        /// For component titles (like chips)
        public static let heading3 = Font.system(.headline, design: .rounded).weight(.medium)
        
        /// Standard reading text
        public static let bodyPrimary = Font.system(.body, design: .default)
        
        /// Secondary reading text
        public static let bodySecondary = Font.system(.subheadline, design: .default)
        
        /// For small labels and hints
        public static let caption = Font.system(.caption, design: .default).weight(.medium)
        
        /// Specifically for phonetic spellings (/fəˈnɛtɪk/)
        public static let phonetics = Font.system(.callout, design: .monospaced)
    }
}
