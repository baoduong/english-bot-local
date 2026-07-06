import SwiftUI

public extension Font {
    /// Typographic scale for a friendly learning app.
    ///
    /// Rounded, warm display faces for titles; clean default for reading text;
    /// monospaced tabular figures for anything numeric (scores, percentages)
    /// so digits never jitter as values change.
    enum BotTheme {

        // MARK: - Display / Headings (rounded, weighted for presence)

        /// Hero display text — big moments (phase complete, the practiced word).
        public static let display = Font.system(size: 40, weight: .bold, design: .rounded)

        /// For large page titles and emphasis.
        public static let heading1 = Font.system(.largeTitle, design: .rounded).weight(.bold)

        /// For section headers.
        public static let heading2 = Font.system(.title2, design: .rounded).weight(.semibold)

        /// For component titles (chips, card headers).
        public static let heading3 = Font.system(.headline, design: .rounded).weight(.semibold)

        // MARK: - Body (clean, readable)

        /// Standard reading text.
        public static let bodyPrimary = Font.system(.body, design: .default)

        /// Emphasised body text (medium weight for subtle hierarchy).
        public static let bodyEmphasis = Font.system(.body, design: .default).weight(.medium)

        /// Secondary reading text.
        public static let bodySecondary = Font.system(.subheadline, design: .default)

        /// For small labels and hints.
        public static let caption = Font.system(.caption, design: .default).weight(.medium)

        /// Uppercase micro-label (use with tracking + secondary color).
        public static let label = Font.system(.caption2, design: .default).weight(.semibold)

        // MARK: - Specialised

        /// Numeric display — scores and stats. Tabular so digits are fixed-width.
        public static let scoreLarge = Font.system(size: 34, weight: .bold, design: .rounded)
            .monospacedDigit()

        /// Inline numeric values (e.g. "Avg 82").
        public static let numeric = Font.system(.headline, design: .rounded)
            .weight(.semibold)
            .monospacedDigit()

        /// Specifically for phonetic spellings (/fəˈnɛtɪk/).
        public static let phonetics = Font.system(.callout, design: .monospaced)
    }
}
