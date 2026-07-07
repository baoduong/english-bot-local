# iOS First Launch Flow

## Overview

When the English Bot iOS app launches, it runs a bootstrap sequence before showing any content. The app checks whether a backend URL is configured and whether the backend is reachable. This prevents the chicken-and-egg problem where the gear icon (Settings) was only accessible after completing onboarding — which required a working backend.

The bootstrap sequence is driven by `AppBootstrapViewModel`, which owns a state machine with four routes: `.checking`, `.settingsRequired`, `.onboarding`, and `.main`. The root view (`EnglishBotApp`) renders `SplashView` while checking, then transitions to the appropriate screen based on the result.

## State Diagram

```
App Launch
    │
    ▼
[SplashView] (.checking)
    │
    ├─ userId empty? ──► generate UUID, stay on SplashView
    │
    ├─ stored URL empty?
    │       │
    │       ├─ Bonjour discovers URL ──► save URL, continue
    │       └─ Bonjour fails ──────────► .settingsRequired("Backend URL not configured")
    │
    ├─ URL invalid format? ──────────────► .settingsRequired("Invalid URL format")
    │
    ├─ Reachability probe (20s timeout)
    │       │
    │       ├─ .healthy
    │       │       │
    │       │       ├─ onboardingDone=true ──────────────────────► .main
    │       │       ├─ onboardingDone=false + curriculum exists ──► setOnboardingDone(true) → .main
    │       │       └─ onboardingDone=false + no curriculum ──────► .onboarding
    │       │
    │       ├─ .degraded(reason) ──────────────────────────────────► .settingsRequired(reason)
    │       └─ .unreachable(reason) ────────────────────────────────► .settingsRequired(reason)
    │
    └─ .settingsRequired ──► fullScreenCover(SettingsView, mode: .setupRequired)
                                    │
                                    └─ Save & Continue ──► retryAfterSettingsSave() ──► re-run bootstrap
```

## Configuration

All state is persisted via `UserDefaults` using these keys:

| Key | Type | Purpose |
|-----|------|---------|
| `eb_apiBaseURL` | String | Backend base URL (e.g. `http://192.168.1.100:8080`) |
| `eb_onboardingDone` | Bool | Whether onboarding has been completed |
| `eb_userId` | String | Unique user identifier (UUID, auto-generated) |
| `eb_activeTab` | Int | Last active tab index |

Both `APIClient.baseURL` and `WebSocketClient.baseURL` are computed properties that re-read `eb_apiBaseURL` from `UserDefaults` on every access. URL changes in Settings apply immediately to all subsequent API calls and WebSocket connections — no app restart required.

## User Troubleshooting

**App stuck on splash screen:**
- The probe has a 20-second timeout. If the backend is slow to start, wait up to 20 seconds.
- If it times out, the app will automatically show the Settings screen.
- Check that the backend is running: `uvicorn api.main:app --host 0.0.0.0 --port 8080`

**Can't dismiss the Settings screen:**
- This is intentional. The `.setupRequired` mode uses `fullScreenCover` which cannot be swiped away.
- There is no Cancel button in setup mode — you must enter a valid URL and tap "Save & Continue".
- If the backend is not running, the probe will fail and show an error. Start the backend first.

**URL keeps failing:**
- Ensure the URL starts with `http://` or `https://` (not `ftp://`, `ws://`, or bare hostname).
- Ensure the port matches your backend: default is `8080` (Windows scripts) or `8000` (legacy).
- Try the "Test Connection" button in normal Settings mode (gear icon in Curriculum toolbar).

**Degraded backend message:**
- This means the backend responded but Ollama or the database is down.
- The `/health` endpoint returned `{"status": "degraded"}`.
- Start Ollama: `ollama serve` and ensure the model is available.
- The app routes to Settings with the degraded reason so you can diagnose.

## Developer Notes

### Reentry Guard

`AppBootstrapViewModel` uses `isBootstrapping: Bool` to prevent double-bootstrap. If `bootstrap()` is called while already running (e.g., from a `.task` modifier re-firing), the second call returns immediately. This is the P1-2 fix.

### Closure-based Dependency Injection

All external dependencies (reachability probe, Bonjour discovery, UserDefaults reads/writes, curriculum probe) are injected as closures in `AppBootstrapViewModel.init()`. This enables pure unit testing without mocking URLSession or UserDefaults.standard directly.

### Curriculum Probe Location

The curriculum probe (`curriculumProbe` closure) is called **inside** `AppBootstrapViewModel.bootstrap()` after a successful reachability check. It is NOT an inline `.task` on `onboardingFlow`. This was a P0 fix — the inline `.task` approach caused the probe to fire before the backend was confirmed reachable.

### macOS-only NetService

`BonjourDiscovery` uses `NetServiceBrowser` which is macOS/iOS only. The package does not support Linux CI. This is documented and intentional — the app is iOS-first.

### WebSocket URL Conversion

`WebSocketClient.httpToWs(_:)` converts `http://` → `ws://` and `https://` → `wss://`. The same `eb_apiBaseURL` key is used for both REST and WebSocket connections. Changing the URL in Settings updates both immediately.

## Rollback Strategy

If a regression is introduced by this feature, use these targeted rollback steps:

**If APIClient computed baseURL breaks in production:**
- Revert commits T3 (`refactor(ios): APIClient.baseURL computed + port 8080 fallback + test isolation`) and T10 to restore cached-URL behavior.
- The `init(baseURL:)` parameter was preserved for backward compat — callers are unaffected.

**If WebSocket refactor breaks streaming:**
- Revert commit T10 (`refactor(ios): WebSocketClient.baseURL computed with http↔ws conversion`) only.
- APIClient refactor (T3) is independent and can remain.

**If SplashView state machine loops:**
- Hard-reset by manually clearing `eb_apiBaseURL` in Xcode's UserDefaults debugger (Devices & Simulators → App Data).
- Or delete and reinstall the app to clear all UserDefaults.

**If fullScreenCover blocks unexpectedly:**
- The `.settingsRequired` route uses `.fullScreenCover(isPresented: .constant(true))` — it cannot be dismissed programmatically except by changing `bootstrap.route` away from `.settingsRequired`.
- Ensure `retryAfterSettingsSave()` is called after a successful save — this re-runs bootstrap and changes the route.

## Known Limitations

1. **Existing user with backend transiently down**: If a returning user's backend is down at cold launch, they are forced into the blocking Settings screen even though their URL is already configured. This is a documented tradeoff for safety — the app cannot proceed without a healthy backend. The user must wait for the backend to come back up, then tap "Save & Continue".

2. **App backgrounded mid-probe**: If the app is backgrounded while the 20-second probe is running, the probe may be cancelled by iOS. The user must foreground the app and cold-restart if stuck on the splash screen.

3. **No custom splash image**: The splash uses SF Symbol `mic.fill` + text "English Coach". A custom image can be added later by replacing the `Image(systemName:)` with an `Image("AppLogo")` asset.

4. **No background reachability re-probe**: The probe only runs at cold launch. If the backend goes down while the app is in use, the user will see API errors in the normal flow — not a re-routing to Settings. This is intentional (per plan scope).
