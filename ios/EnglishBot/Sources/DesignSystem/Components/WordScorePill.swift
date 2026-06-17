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
        Text(word)
            .font(Font.BotTheme.bodyPrimary.weight(.semibold))
            .foregroundColor(.white)
            .padding(.horizontal, Spacing.sm)
            .padding(.vertical, Spacing.xs)
            .background(scoreColor)
            .cornerRadius(Spacing.sm)
    }
}

#Preview {
    HStack {
        WordScorePill(word: "Excellent", score: 95)
        WordScorePill(word: "Average", score: 65)
        WordScorePill(word: "Poor", score: 45)
    }
    .padding()
}
