import Foundation
import CoreGraphics

public struct Spacing {
    /// 4pt grid system
    public static let xs: CGFloat = 4
    public static let sm: CGFloat = 8
    public static let md: CGFloat = 16
    public static let lg: CGFloat = 24
    public static let xl: CGFloat = 32
    public static let xxl: CGFloat = 48
}

/// Corner-radius scale. Vary radius by element role: tight on inner/small
/// elements, softer on large containers — never one uniform value everywhere.
public struct Radius {
    /// Small chips, pills' inner elements.
    public static let sm: CGFloat = 8
    /// Buttons, inset fields.
    public static let md: CGFloat = 12
    /// Cards, panels.
    public static let lg: CGFloat = 18
    /// Large hero containers / sheets.
    public static let xl: CGFloat = 26
}
