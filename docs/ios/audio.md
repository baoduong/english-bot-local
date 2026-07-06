# iOS Audio Recording and Playback

This document defines the recommended iOS audio settings for the English pronunciation practice app so recordings stay compatible with the backend scoring pipeline and sample audio playback stays predictable.

## Recording Config

Use an `AVAudioSession` configuration that supports **simultaneous recording and playback**.

Recommended session setup:

- Category: `.playAndRecord`
- Mode: speech-friendly mode appropriate for voice input
- Options: include the standard speaker/routing options needed for in-app playback while recording

Recording target format:

- Container / extension: `.m4a`
- Codec: AAC
- Sample rate: `44100 Hz`
- Channels: `mono` (`1` channel)
- Bitrate: keep it in the typical voice-recording AAC range; use a moderate bitrate that preserves clarity without producing oversized files

Why this matters:

- iPhone natively records to `.m4a`, which is already accepted by the backend ingestion path.
- Mono, 44.1 kHz AAC recordings are easy to transcode into the backend scoring format.
- Keeping the upload file small reduces network friction and makes preprocessing faster.

Implementation note:

- Follow Apple documentation conventions for `AVAudioSession` activation/deactivation around recording and playback transitions.
- The session should be configured before recording starts and should be prepared for route changes such as speaker, headset, or Bluetooth use.

## Playback Strategy

The app should use different playback mechanisms depending on the audio source.

### Decision Table

| Use case | Recommended API | Reason |
|---|---|---|
| Stream sample pronunciation audio from backend or remote URL | `AVPlayer` | Best fit for URL-based media playback, simple buffering, and straightforward integration |
| Synchronized or low-latency in-app audio processing | `AVAudioEngine` | Better when audio needs mixing, effects, analysis, or tighter control over the signal chain |
| Minimal pair practice audio delivery | `AVPlayer` for normal playback, `AVAudioEngine` only if you need processing or custom routing | Minimal pairs are usually best delivered as simple sample playback, unless the app must alter or inspect the audio stream |

### Guidance

- Use `AVPlayer` for sample audio streaming because it is the simplest and most maintainable path for playing sentence or word examples.
- Use `AVAudioEngine` only when the app needs signal-level control, such as live processing, filtering, metering, or future pronunciation analysis features.
- For minimal pair exercises, keep delivery lightweight: fetch the audio and play it directly unless there is a specific need for audio graph control.

## Backend Compatibility Checklist

Before shipping iOS recording, verify the recorded file matches the backend transcode-and-score pipeline.

- [ ] File extension is `.m4a`
- [ ] Recording uses AAC in an MPEG-4 container
- [ ] Sample rate is `44100 Hz`
- [ ] Channel count is `1` (mono)
- [ ] File size stays small enough for mobile upload and backend preprocessing
- [ ] Backend transcodes uploaded `.m4a` to `WAV 16 kHz mono` before Whisper scoring
- [ ] Backend conversion uses the existing `ffmpeg` / `pydub` path
- [ ] Sample audio references remain compatible with backend-generated pronunciation examples

Compatibility notes:

- The backend already accepts common audio upload formats, but the preferred iOS recording output is still `.m4a` because it is the native mobile recording format.
- The backend scoring path should normalize user recordings to `WAV 16 kHz mono` before passing them into Whisper.
- Sample audio generation currently produces `.mp3`, so the iOS player must support streaming and local playback of compressed audio assets.
