# EnglishBot iOS Design System

## Overview
This design system provides the foundation for the EnglishBot native iOS application. It is built entirely in SwiftUI and distributed as a Swift Package for modularity and reusability.

## Tokens
Tokens define the core visual language of the app. They are accessible via extensions on standard SwiftUI types.

### Colors
Available via `Color.BotTheme`:
- **Semantic Colors**: `primary`, `secondary` (requires asset catalog definitions in app)
- **Status Colors**: `scoreExcellent` (green, ≥80), `scoreAverage` (yellow, ≥60), `scorePoor` (red, <60)
- **Backgrounds**: `backgroundMain`, `backgroundSecondary`, `backgroundTertiary`
- **Text**: `textPrimary`, `textSecondary`, `textTertiary`
- **Borders**: `border`
- **Chat**: `chatUser` (blue), `chatAI` (gray)

### Typography
Available via `Font.BotTheme`:
- **Headings**: `heading1` (large page titles), `heading2` (section headers), `heading3` (component titles)
- **Body**: `bodyPrimary` (standard reading), `bodySecondary` (secondary reading)
- **Specialty**: `caption` (small hints), `phonetics` (monospaced for phonetic spellings like `/fəˈnɛtɪk/`)

### Spacing
Available via `Spacing`:
- 4pt grid system: `xs` (4), `sm` (8), `md` (16), `lg` (24), `xl` (32), `xxl` (48)

## Components

### WordScorePill
Displays a word with a background color based on the pronunciation score.
```swift
WordScorePill(word: "Excellent", score: 95) // Green
WordScorePill(word: "Average", score: 65)   // Yellow
WordScorePill(word: "Poor", score: 45)      // Red
```

### ChatBubble
Displays a conversational message, styled differently depending on the role.
```swift
ChatBubble(text: "Hello, I want to practice English.", role: .user) // Blue, right-aligned
ChatBubble(text: "Great! What are your goals?", role: .ai)          // Gray, left-aligned
```

### ProgressChip
A compact indicator for curriculum context or status.
```swift
ProgressChip(text: "Week 2 · Code Reviews · 3/12", icon: "📍")
```

### RecordButton
A large, prominent button for capturing voice input. Includes an animated pulsing state when recording.
```swift
RecordButton(isRecording: isRecording) {
    // toggle recording state
}
```

### LoadingIndicator
Animated dots used to indicate AI processing/thinking states.
```swift
LoadingIndicator()
```

## Integration
To use this design system in the main app:
1. Add the local package dependency to your Xcode project.
2. `import DesignSystem` in your SwiftUI views.
3. Ensure the app target's Asset Catalog defines the expected color names ("BrandPrimary", "BrandSecondary", "systemBackground", etc.) or use system defaults where applicable.
