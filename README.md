# 🎤 English Pronunciation Bot

Discord bot luyện phát âm tiếng Anh cá nhân hóa — ghi âm, chấm điểm từng từ, và tự động lên lịch ôn tập thông minh.

---

## Tính năng

- **Chấm điểm phát âm từng từ** với bản đồ màu ANSI trực quan (🟢 đúng / 🟡 chưa chuẩn / 🔴 sai)
- **Word Drill Mode** — khi phát âm câu chưa đạt, bot tách các từ khó ra luyện riêng lẻ trước
- **Spaced Repetition (Leitner System)** — tự động lên lịch ôn tập: Box 1 (hàng ngày), Box 2 (3 ngày), Box 3 (7 ngày)
- **Danh sách phục thù** — từ sai nặng được lưu lại và ưu tiên xuất hiện buổi học hôm sau
- **Pre-teaching** — trước khi luyện câu có từ mới, bot giải thích cách phát âm (Ollama) và phát audio mẫu (Edge-TTS)
- **Streak tracking** — theo dõi chuỗi ngày học liên tục, tự động reset nếu bỏ ngày
- **Smart engine routing** — Ollama phân tích độ khó → câu dễ dùng Whisper (free), câu khó mới gọi Azure (tiết kiệm API)
- **Auto-leveling** — tự động tăng/giảm độ khó dựa trên xu hướng điểm gần nhất
- **Error pattern detection** — phát hiện lỗi phát âm lặp lại (nuốt phụ âm cuối, lẫn r/l, th sound...)
- **Flexible rounds** — mặc định 3 hiệp, dùng `!more` để thêm bonus (tối đa 6)
- **Progress tracking** — `!stats` xem thống kê 30 ngày, xu hướng điểm, và top điểm yếu

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
| Gõ `!daily` | Bắt đầu phiên học 3 hiệp |
| Gõ `!more` | Thêm hiệp bonus (sau khi hoàn thành, tối đa 6) |
| Gõ `!skip` | Bỏ qua câu hiện tại |
| Gõ `!stop` | Thoát phiên học giữa chừng |
| Gõ `!stats` | Xem thống kê tiến trình + điểm yếu |
| Gõ `!help` | Hiển thị hướng dẫn |
| Gửi file ghi âm (`.ogg`, `.wav`, `.mp3`, `.m4a`) | Bot chấm điểm và phản hồi |

### Flow một phiên học

```
!daily
  └─ Bot bốc câu theo thuật toán Spaced Repetition
  └─ (Nếu có từ mới) Bot giải thích phát âm + phát audio mẫu

Hiệp 1 → Ghi âm → Điểm ≥ 80? → Hiệp 2 → Hiệp 3 → 🏆 Hoàn thành
              ↓
         Lần fail 1: Thử lại cả câu
              ↓
         Lần fail 2: Word Drill Mode
              ├─ Luyện từng từ khó (pass ≥ 50% số từ)
              │     └─ → Thử lại cả câu
              └─ (pass < 50%) → Đổi câu, lưu vào Danh sách phục thù
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

## Thêm câu luyện tập

Thêm trực tiếp vào bảng `sentences` trong SQLite:

```sql
INSERT INTO sentences (sentence_text, keyword, difficulty) VALUES
  ('Please send me the quarterly report.', 'quarterly', 2),
  ('We need to finalize the budget.', 'finalize', 2);
```

`keyword` là từ tiêu điểm — dùng để pre-teaching và lưu vào Danh sách phục thù khi sai nặng.

`difficulty`: 1 = Dễ, 2 = Trung bình, 3 = Khó. Bot tự chọn câu phù hợp với level hiện tại của user.

---

## Cấu trúc dự án

```
app.py          — Discord event loop, session state, flow logic
ai_brain.py     — Whisper/Azure scoring, phoneme analysis, error classification, Ollama tips, Edge-TTS audio
database.py     — SQLite, Leitner spaced repetition, streak tracking, score history, error pattern detection
```

Database: `english_learner.db` (SQLite, tự tạo khi chạy lần đầu)

### Bảng dữ liệu chính

| Bảng | Chức năng |
|---|---|
| `users` | Thông tin user, streak, level |
| `sentences` | Kho câu luyện tập (có difficulty) |
| `user_progress` | Tiến trình Leitner mỗi câu |
| `failed_words` | Danh sách phục thù |
| `score_history` | Log điểm mỗi lần chấm |
| `error_patterns` | Lỗi lặp lại theo loại |
