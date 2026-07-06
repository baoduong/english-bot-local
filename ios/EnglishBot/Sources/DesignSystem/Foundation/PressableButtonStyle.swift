import SwiftUI

/// Gives any button a physical, native-feeling press: a subtle scale-down and
/// dim on press, with an optional haptic tap. GPU-accelerated (transform +
/// opacity only), spring-eased for weight.
public struct PressableButtonStyle: ButtonStyle {
    private let scale: CGFloat
    private let haptic: Haptics.Impact?

    public init(scale: CGFloat = 0.97, haptic: Haptics.Impact? = .light) {
        self.scale = scale
        self.haptic = haptic
    }

    public func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .scaleEffect(configuration.isPressed ? scale : 1.0)
            .opacity(configuration.isPressed ? 0.88 : 1.0)
            .animation(.spring(response: 0.28, dampingFraction: 0.62), value: configuration.isPressed)
            .onChange(of: configuration.isPressed) { pressed in
                if pressed, let haptic { Haptics.impact(haptic) }
            }
    }
}

public extension ButtonStyle where Self == PressableButtonStyle {
    /// Default pressable style with a light haptic.
    static var pressable: PressableButtonStyle { PressableButtonStyle() }

    /// Pressable style with a custom scale / haptic.
    static func pressable(scale: CGFloat = 0.97, haptic: Haptics.Impact? = .light) -> PressableButtonStyle {
        PressableButtonStyle(scale: scale, haptic: haptic)
    }
}
