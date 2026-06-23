import SwiftUI

// Simple FlowLayout for Tags/Pills
public struct FlowLayout: Layout {
    public var spacing: CGFloat
    
    public init(spacing: CGFloat) {
        self.spacing = spacing
    }
    
    public func sizeThatFits(proposal: ProposedViewSize, subviews: Subviews, cache: inout ()) -> CGSize {
        let maxWidth = proposal.width ?? .infinity
        let result = FlowResult(in: maxWidth, subviews: subviews.map { $0.sizeThatFits(.unspecified) }, spacing: spacing)
        return result.bounds
    }
    
    public func placeSubviews(in bounds: CGRect, proposal: ProposedViewSize, subviews: Subviews, cache: inout ()) {
        let result = FlowResult(in: bounds.width, subviews: subviews.map { $0.sizeThatFits(.unspecified) }, spacing: spacing)
        for (index, subview) in subviews.enumerated() {
            subview.place(at: CGPoint(x: bounds.minX + result.frames[index].minX, y: bounds.minY + result.frames[index].minY), proposal: ProposedViewSize(result.frames[index].size))
        }
    }
    
    public struct FlowResult {
        var bounds: CGSize = .zero
        var frames: [CGRect] = []
        
        init(in maxWidth: CGFloat, subviews: [CGSize], spacing: CGFloat) {
            var currentX: CGFloat = 0
            var currentY: CGFloat = 0
            var lineHeight: CGFloat = 0
            var usedWidth: CGFloat = 0
            
            for size in subviews {
                
                if currentX + size.width > maxWidth && currentX > 0 {
                    currentX = 0
                    currentY += lineHeight + spacing
                    lineHeight = 0
                }
                
                frames.append(CGRect(x: currentX, y: currentY, width: size.width, height: size.height))
                usedWidth = max(usedWidth, currentX + size.width)
                
                currentX += size.width + spacing
                lineHeight = max(lineHeight, size.height)
            }
            
            bounds = CGSize(width: usedWidth, height: currentY + lineHeight)
        }
    }
}

protocol SizedFlowSubview {
    var flowSize: CGSize { get }
}
