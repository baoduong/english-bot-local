import SwiftUI

public struct WordScorePill: View {
    public let word: String
    public let score: Int

    public init(word: String, score: Int) {
        self.word = word
        self.score = score
    }

    private var scoreColor: Color {
        if score >= 80 { return Color.BotTheme.scoreExcellent }
        if score >= 60 { return Color.BotTheme.scoreAverage }
        return Color.BotTheme.scorePoor
    }

    public var body: some View {
        HStack(spacing: Spacing.xs) {
            Text(word)
                .font(Font.BotTheme.bodyEmphasis)
            Text("\(score)")
                .font(Font.system(.subheadline, design: .rounded).weight(.bold).monospacedDigit())
                .opacity(0.85)
        }
        .foregroundStyle(.white)
        .padding(.horizontal, Spacing.sm + 2)
        .padding(.vertical, Spacing.xs + 1)
        .background(
            Capsule(style: .continuous).fill(scoreColor)
        )
        .shadow(color: scoreColor.opacity(0.3), radius: 3, x: 0, y: 2)
    }
}

#Preview {
    HStack {
        WordScorePill(word: "Excellent", score: 95)
        WordScorePill(word: "Average", score: 65)
        WordScorePill(word: "Poor", score: 45)
    }
    .padding()
    .background(Color.BotTheme.backgroundMain)
}
