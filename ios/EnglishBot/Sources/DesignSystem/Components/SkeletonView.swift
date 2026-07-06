import SwiftUI

/// A shimmering placeholder that matches the shape of loading content — far
/// more premium than a spinner because it hints at the layout to come.
///
/// The shimmer is a moving gradient driven by `opacity`/`offset` on the GPU,
/// so it stays smooth even with several skeletons on screen.
public struct SkeletonView: View {
    private let cornerRadius: CGFloat
    @State private var phase: CGFloat = -1

    public init(cornerRadius: CGFloat = Radius.md) {
        self.cornerRadius = cornerRadius
    }

    public var body: some View {
        RoundedRectangle(cornerRadius: cornerRadius, style: .continuous)
            .fill(Color.BotTheme.backgroundTertiary)
            .overlay(shimmer)
            .clipShape(RoundedRectangle(cornerRadius: cornerRadius, style: .continuous))
            .onAppear {
                withAnimation(.linear(duration: 1.3).repeatForever(autoreverses: false)) {
                    phase = 2
                }
            }
    }

    private var shimmer: some View {
        GeometryReader { geo in
            LinearGradient(
                colors: [
                    .clear,
                    Color.BotTheme.textTertiary.opacity(0.18),
                    .clear
                ],
                startPoint: .leading,
                endPoint: .trailing
            )
            .frame(width: geo.size.width * 0.6)
            .offset(x: geo.size.width * phase)
        }
    }
}

/// A prebuilt card-shaped skeleton for list loading states.
public struct SkeletonCard: View {
    private let lines: Int
    public init(lines: Int = 2) { self.lines = lines }

    public var body: some View {
        VStack(alignment: .leading, spacing: Spacing.sm) {
            SkeletonView(cornerRadius: Radius.sm)
                .frame(width: 140, height: 18)
            ForEach(0..<lines, id: \.self) { index in
                SkeletonView(cornerRadius: Radius.sm)
                    .frame(maxWidth: index == lines - 1 ? 220 : .infinity)
                    .frame(height: 14)
            }
        }
        .padding(Spacing.md)
        .frame(maxWidth: .infinity, alignment: .leading)
        .cardStyle(elevated: false)
    }
}

#Preview {
    VStack(spacing: Spacing.md) {
        SkeletonCard()
        SkeletonCard(lines: 3)
    }
    .padding()
}
