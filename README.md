# 🎤 English Pronunciation Bot

Discord bot luyện phát âm tiếng Anh cá nhân hóa — ghi âm, chấm điểm từng từ, và tự động lên lịch ôn tập thông minh.

---

## Tính năng

- **AI Conversational Onboarding** — Ollama-powered chat discovers your learning goal naturally
- **Personalized Curriculum** — AI generates weekly phases with vocabulary, milestones, and practice sentences
- **Phase Progression** — AI evaluates your performance and decides: advance to next week, repeat, or regenerate content
- **Mini-context Header** — Shows current week, theme, and progress (📍 Tuần 2 · Code Reviews · 3/12)
- **Pronunciation Scoring** — Whisper/Azure smart routing với bản đồ màu ANSI trực quan (🟢 đúng / 🟡 chưa chuẩn / 🔴 sai)
- **Goal Change** — `!goal change` để thiết lập lại mục tiêu học tập và tạo lộ trình mới
- **Session Persistence** — Trạng thái phiên học được lưu trữ an toàn qua SQLite, không mất khi restart bot

---

## Cài đặt

### Yêu cầu

- Python 3.9+
- [Ollama](https://ollama.ai) đang chạy local với model `gemma4:31b-cloud`
- ffmpeg (để convert audio khi dùng Azure): `brew install ffmpeg`

### Cài thư viện

```bash
pip install -r requirements.txt
```

### Cấu hình `.env`

```env
# Bắt buộc
DISCORD_BOT_TOKEN=your_discord_token_here

# --- Azure Speech (tuỳ chọn, chính xác hơn Whisper với accent Việt) ---
USE_AZURE_SPEECH=false
AZURE_SPEECH_KEY=your_key_here
AZURE_SPEECH_REGION=southeastasia
```

Token Discord lấy tại: https://discord.com/developers/applications

### Chạy bot

```bash
python app.py
```

Lần đầu khởi động sẽ mất vài giây để nạp Whisper vào RAM.

---

## Cách sử dụng

| Hành động | Kết quả |
|---|---|
| Gõ `!go` | Bắt đầu học — kích hoạt onboarding cho user mới, hoặc tiếp tục lộ trình học |
| Gõ `!skip` | Bỏ qua câu hiện tại |
| Gõ `!stop` | (Gõ trong phiên) Thoát phiên học giữa chừng |
| Gõ `!me` | Xem hồ sơ và tiến độ lộ trình học |
| Gõ `!goal change` | Lưu trữ lộ trình hiện tại và bắt đầu lại quá trình onboarding |
| Gõ `!help` | Hiển thị hướng dẫn |

### Flow lộ trình học

```
First !go → AI Onboarding Chat → Goal Confirmation → Week 1 Generated → Practice
  └─ Voice Recording → Score (Whisper/Azure) → ≥80? → Next sentence
                                                 └─ <80 → Retry / Word Drill
  └─ Phase Complete → AI Evaluates → Advance / Repeat / Regenerate → Next Week
```

---

## Engine chấm điểm

### Smart Routing (khi bật Azure)

Khi `USE_AZURE_SPEECH=true`, bot **không gọi Azure cho tất cả** — Ollama phân tích độ khó trước:

| Độ khó | Engine | Ví dụ |
|---|---|---|
| Simple | Whisper (free) | "Hello", "Good morning", "Thank you" |
| Complex | Azure (chính xác) | "Throughout", "Entrepreneurship", câu dài/phụ âm khó |

Từ đơn ≤ 6 ký tự → auto simple (không gọi Ollama). Kết quả được cache.

### Whisper (mặc định — local, miễn phí)

Dùng Whisper `small` + so sánh âm vị IPA để tránh đỏ oan do accent:

| Ngưỡng | Màu |
|---|---|
| Confidence ≥ 0.75 hoặc phoneme similarity đủ cao | 🟢 Xanh |
| Confidence ≥ 0.50 | 🟡 Vàng |
| Thấp hơn | 🔴 Đỏ |

### Azure Speech (tuỳ chọn — chính xác hơn với accent Việt)

Dùng Azure Pronunciation Assessment API — trả về `AccuracyScore` thực sự đo chất lượng phát âm từng từ:

| AccuracyScore | Màu |
|---|---|
| ≥ 80 | 🟢 Xanh |
| ≥ 60 | 🟡 Vàng |
| < 60 | 🔴 Đỏ |

Bật Azure: đặt `USE_AZURE_SPEECH=true` trong `.env`. Cần cài thêm:
```bash
pip install azure-cognitiveservices-speech pydub
```

Chi phí Azure: ~$1.32/giờ audio. **Free tier 5 giờ/tháng** — đủ dùng cho bot cá nhân.

---

## Cấu trúc dự án

```
app.py                         — Discord event loop, session state, command handlers
ai_brain.py                    — Whisper/Azure scoring, pre-teaching via Ollama + Edge-TTS
database.py                    — Backward-compat wrapper (re-exports from db/ package)

db/
  schema.py                    — SQLite table definitions (18 tables)
  connection.py                — DB connection factory
  curriculum.py                — CRUD: curriculums, phases, phase_content, onboarding
  users.py                     — User management + onboarding status
  sessions.py                  — Active session persistence + cleanup
  sentences.py                 — Sentence bank for practice
  word_stats.py / phoneme_errors.py / pattern_stats.py — Learner statistics

engines/
  ollama_client.py             — Hardened Ollama wrapper (JSON, retries, timeouts)
  curriculum_generator.py      — AI-driven phase generation
  onboarding_chat.py           — Conversational goal discovery
  prompts.py                   — Prompt templates for all AI interactions
  tts.py / whisper.py / azure.py — Audio processing engines

analysis/
  phase_engine.py              — Phase progression decisions (advance/repeat/regenerate)
  curriculum_types.py          — TypedDicts and validators for curriculum data
  pronunciation.py / phonemes.py / errors.py / patterns.py — Pronunciation analysis
```

Database: `english_learner.db` (SQLite, tự tạo khi chạy lần đầu)

### Bảng dữ liệu chính

| Bảng | Chức năng |
|---|---|
| `users` | Thông tin user và trạng thái onboarding |
| `curriculums` | Mục tiêu học tập và trạng thái |
| `phases` | Các giai đoạn học theo tuần, chủ đề và milestone |
| `phase_content` | Các câu thực hành theo từng giai đoạn và thống kê |
| `onboarding_conversations` | Lịch sử trò chuyện khi xác định mục tiêu |
| `sentences` | Kho câu luyện tập tổng hợp |
| `score_history` | Lịch sử chấm điểm |
| `error_patterns` | Các lỗi phát âm thường gặp |
