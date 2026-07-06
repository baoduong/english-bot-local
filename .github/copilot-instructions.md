# Copilot Instructions

## Project Overview

A FastAPI backend + iOS app for English pronunciation coaching. Users record voice on iPhone; the backend grades pronunciation, provides per-word color-coded feedback, and manages an AI-generated curriculum with phase progression tracking — all in Vietnamese UI.

## Architecture

| File/Folder | Role |
|---|---|
| `api/main.py` | FastAPI application entry point, lifespan, exception handlers |
| `api/routers/` | Domain routers: users, onboarding, curriculum, practice, progress, health |
| `db/` | SQLite schema, connection, CRUD operations, user/session management |
| `engines/` | Hardened Ollama wrapper, AI curriculum generator, onboarding chat, TTS, audio processing |
| `analysis/` | Phase progression engine, curriculum types, pronunciation analysis, error tracking |
| `ios/EnglishBot/` | Native SwiftUI iOS app (Swift Package Manager) |

**Data flow:** iPhone audio upload → `POST /practice/audio` → `engines/whisper.py` or `engines/azure.py` (scoring) → `analysis/phase_engine.py` decides next step → `db/` updates progress → JSON response with per-word scores. Temp files (`temp_{user_id}_{filename}`, `teacher_sample.mp3`) are deleted immediately after use.

**Session state:** `sessions` table in SQLite persists active learners. Active sessions survive server restarts.

## Running the Backend

```bash
# Install dependencies
pip install -r requirements.txt

# Optional: .env file with
# USE_AZURE_SPEECH=false
# AZURE_SPEECH_KEY=your_key_here
# AZURE_SPEECH_REGION=southeastasia

# Run
uvicorn api.main:app --host 0.0.0.0 --port 8000
```

Whisper model (`small`) is eager-loaded at startup — takes a few seconds. Ollama must be running locally with `gemma4:31b-cloud` available. Edge-TTS requires internet access.

## Key Conventions

**Smart engine routing (`_should_use_azure` + `assess_difficulty` in `engines/`):**
- Khi `USE_AZURE_SPEECH=true`: Ollama phân tích độ khó câu/từ → "simple" dùng Whisper, "complex" dùng Azure
- Heuristic nhanh: từ đơn ≤ 6 ký tự → auto "simple" (không gọi Ollama)
- Cache kết quả (`_difficulty_cache`) — cùng câu/từ chỉ gọi Ollama 1 lần
- Whisper luôn được load sẵn bất kể Azure bật/tắt
- Khi `USE_AZURE_SPEECH=false`: tất cả đều dùng Whisper

**Scoring thresholds (engines/whisper.py, engines/azure.py):**
- Whisper `small` model với `word_timestamps=True`
- Nếu Whisper nghe đúng từ (tag `equal`): confidence ≥ 0.75 → green, ≥ 0.50 → yellow, < 0.50 → kiểm tra phoneme similarity (≥ 0.75 → yellow, else red)
- Nếu Whisper nghe sai từ (tag `replace`): dùng `phoneme_similarity()` với IPA → ≥ 0.70 → yellow, < 0.70 → red
- Nếu từ bị nuốt hoàn toàn (tag `delete`): gray
- Score ≥ 80/100 → round passed; < 80 → retry; lần fail thứ 2 kích hoạt Word Drill Mode

**Error type classification (`classify_error` in `analysis/errors.py`):**
- `omission` — bỏ sót/nuốt hoàn toàn
- `final_consonant` — nuốt phụ âm cuối (s, t, d, z, k, p)
- `th_sound` — lỗi âm /θ/ (think → tink)
- `r_l_confusion` — lẫn r/l
- `vowel_stress` — sai nguyên âm/trọng âm
- `sh_sound` — lỗi âm sh/ch
- `general` — không phân loại được

**Phoneme scoring (`phoneme_similarity` in `analysis/phonemes.py`):**
- Dùng `eng-to-ipa` chuyển từ sang IPA, rồi so sánh chuỗi IPA bằng `difflib.SequenceMatcher`
- Fallback sang so sánh ký tự nếu từ không có trong từ điển IPA (kết quả có dấu `*`)
- Tránh trường hợp Whisper chấm đỏ oan do accent Việt

**Database:** SQLite via `db/` package. Connection logic in `db/connection.py`. Major tables include: `users`, `curriculums`, `phases`, `phase_content`, `onboarding_conversations`, `sentences`, `score_history`, and error tracking tables.

**Code comments are in Vietnamese** — this is intentional and consistent throughout the codebase.

## System Flows

**Onboarding Flow:**
On first launch, the iOS app calls `POST /onboarding/start`. The `OnboardingChat` (Ollama) initiates a natural conversation to discover the user's learning goals, English level, and context. Once enough context is gathered, it generates a confirmation JSON. If the user confirms, the system proceeds to generate the curriculum.

**Curriculum Generation:**
`engines/curriculum_generator.py` uses the confirmed onboarding context to generate a structured curriculum (goals, phases, vocabulary, and sentences). It creates week-by-week phases tailored to the user's specific scenario.

**Phase Progression:**
`analysis/phase_engine.py` evaluates performance after a phase is completed. Based on pronunciation scores and error rates, it decides whether to:
- `advance`: Move to the next week's phase
- `repeat`: Repeat the current phase for more practice
- `regenerate`: Generate new content for the current theme because the current sentences might be too hard or ineffective
