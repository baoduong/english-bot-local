import discord
import os
import re
import requests
import asyncio
import functools
from datetime import datetime

from dotenv import load_dotenv
# Import chuẩn xác các hàm xử lý từ 2 file vệ tinh đã viết
from database import (get_or_create_user, get_next_sentence, update_user_progress,
                      save_failed_word, update_sentence_progress, clear_failed_word,
                      log_score, log_error_pattern, get_user_stats, adjust_user_level,
                      increment_total_sessions,
                      record_word_attempts_batch, get_weak_words,
                      record_phoneme_errors_batch, get_weak_phonemes,
                      record_pattern_attempts_batch, get_weak_patterns,
                      pick_shadowing_item, record_shadowing_attempt,
                      create_content_item, list_content_items, search_content,
                      get_segments, bulk_import)
from ai_brain import (analyze_audio_with_whisper, analyze_single_word, send_new_word_tutorial,
                      generate_sample_audio, ERROR_TYPE_LABELS)
from analysis.patterns import extract_patterns
from analysis.learning_memory import (get_learner_profile, get_learning_insights,
                                      get_practice_recommendations)
from analysis.drills import generate_daily_practice
from analysis.recommendations import build_today_session, get_recommended_content
from analysis.metrics import get_learning_progress, get_recommendation_metrics, get_content_health
from db.content_usage import record_usage
from db.recommendations import record_recommendation, mark_completed, mark_skipped
from db.shadowing import pick_content_shadowing
from db.connection import get_db_connection

load_dotenv()

DISCORD_BOT_TOKEN=os.getenv("DISCORD_BOT_TOKEN")

# 1. Cấu hình quyền hạn (Intents) bắt buộc cho Bot Discord
intents = discord.Intents.default()
intents.message_content = True  # Bật tính năng đọc nội dung tin nhắn text
client = discord.Client(intents=intents)

# 2. Bộ nhớ đệm lưu trạng thái học trong ngày của các User
# Cấu trúc: { user_id: { "round": 1, "sentence": "...", "new_word": "...", "fail_count": 0 } }
user_sessions = {}


def _write_session_analytics(user_id, session):
    started_at = session.get("started_at")
    if not started_at:
        return
    scores = session.get("scores", [])
    avg_score = round(sum(scores) / len(scores), 1) if scores else 0
    rounds_completed = session["round"] - 1
    content_used = session.get("content_segments_used", 0)

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """INSERT INTO session_analytics
           (user_id, started_at, completed_at, rounds_completed, rounds_total, avg_score, content_segments_used)
           VALUES (?, ?, datetime('now'), ?, ?, ?, ?)""",
        (user_id, started_at, rounds_completed, session["max_rounds"], avg_score, content_used)
    )
    conn.commit()
    conn.close()


def _strip_markdown(text):
    """Remove markdown formatting: # headers, * bullets, - bullets, ** bold **, ` code `."""
    lines = text.split("\n")
    cleaned = []
    for line in lines:
        line = re.sub(r"^#{1,6}\s+", "", line)
        line = re.sub(r"^\s*[\*\-]\s+", "", line)
        line = re.sub(r"\*\*(.+?)\*\*", r"\1", line)
        line = re.sub(r"\*(.+?)\*", r"\1", line)
        line = re.sub(r"`(.+?)`", r"\1", line)
        cleaned.append(line)
    return "\n".join(cleaned)


def _parse_import_text(raw_text):
    """Parse import text into list of {title, text} items.
    Supports --- separators for multiple items and markdown stripping.
    """
    raw_text = _strip_markdown(raw_text)
    blocks = re.split(r"\n---+\n", raw_text)
    items = []
    for block in blocks:
        block = block.strip()
        if not block:
            continue
        lines = block.split("\n", 1)
        title = lines[0].strip()
        body = lines[1].strip() if len(lines) > 1 else ""
        if not body:
            continue
        items.append({"title": title, "text": body})
    return items


def _decide_round_type(session):
    """Adaptive: chọn loại round tiếp theo dựa trên lịch sử trong phiên."""
    history = session.get("round_history", [])
    if not history:
        return "sentence"

    recent_fails = 0
    for h in reversed(history[-3:]):
        if not h["passed"]:
            recent_fails += 1
        else:
            break

    last_scores = [h["score"] for h in history[-3:] if h["score"] is not None]
    avg_recent = sum(last_scores) / len(last_scores) if last_scores else 70

    if recent_fails >= 2:
        return "shadowing"

    if avg_recent >= 90 and len(history) >= 2:
        return "sentence"

    last_type = history[-1]["type"] if history else "sentence"
    rotation = ["sentence", "shadowing", "sentence", "recommend", "sentence"]
    round_idx = len(history) % len(rotation)
    next_type = rotation[round_idx]

    if recent_fails >= 1 and next_type == "sentence":
        return "shadowing"

    return next_type


def _should_shorten_session(session):
    """Rút ngắn phiên nếu user đang struggle quá nhiều."""
    history = session.get("round_history", [])
    if len(history) < 3:
        return False
    last_3_scores = [h["score"] for h in history[-3:] if h["score"] is not None]
    if last_3_scores and sum(last_3_scores) / len(last_3_scores) < 50:
        return True
    return False


def _get_adaptive_difficulty(session):
    """Trả về difficulty preference (1-5) dựa trên performance gần nhất."""
    history = session.get("round_history", [])
    base_diff = session.get("difficulty_pref", 2)

    if len(history) < 2:
        return base_diff

    last_2 = history[-2:]
    if all(h["passed"] and h.get("score", 0) >= 90 for h in last_2):
        return min(5, base_diff + 1)
    if all(not h["passed"] for h in last_2):
        return max(1, base_diff - 1)

    return base_diff


async def _advance_to_next_round(channel, user_id, session):
    """Adaptive: chuyển sang round tiếp theo với loại bài phù hợp."""
    round_type = _decide_round_type(session)
    difficulty = _get_adaptive_difficulty(session)
    session["difficulty_pref"] = difficulty

    if _should_shorten_session(session):
        old_max = session["max_rounds"]
        session["max_rounds"] = min(session["round"] + 1, old_max)
        if session["max_rounds"] < old_max:
            await channel.send("💡 Thầy thấy hôm nay hơi nặng — rút gọn phiên học để giữ năng lượng nhé!")

    round_num = session["round"]
    max_rounds = session["max_rounds"]

    if round_type == "shadowing":
        content_item = pick_content_shadowing(user_id)
        if content_item:
            session["mode"] = "shadowing"
            item = {"id": content_item["id"], "text": content_item["text"], "source": "content"}
            session["shadowing_item"] = item
            session["sentence"] = item["text"]
            session["new_word"] = None
            session["fail_count"] = 0
            session["drill_done"] = False
            session["content_segments_used"] = session.get("content_segments_used", 0) + 1
            await channel.send(
                f"🎧 **Hiệp {round_num}/{max_rounds} — Shadowing**\n"
                f"Nghe mẫu rồi đọc theo:\n"
                f"👉 **`{item['text']}`**"
            )
            sample_path = f"shadow_sample_{user_id}.mp3"
            if await generate_sample_audio(item["text"], sample_path):
                await channel.send(file=discord.File(sample_path))
                os.remove(sample_path)
            return
        round_type = "sentence"

    if round_type == "recommend":
        recs = get_recommended_content(user_id, limit=1)
        if recs:
            rec = recs[0]
            rec_id = record_recommendation(user_id, rec["segment_id"], reasons=rec["reasons"], score=rec["score"])
            session["mode"] = "recommend_practice"
            item = {"id": rec["segment_id"], "text": rec["text"], "source": "content"}
            session["shadowing_item"] = item
            session["current_rec_id"] = rec_id
            session["sentence"] = rec["text"]
            session["new_word"] = None
            session["fail_count"] = 0
            session["drill_done"] = False
            session["content_segments_used"] = session.get("content_segments_used", 0) + 1
            reasons_str = f" ({', '.join(rec['reasons'][:2])})" if rec["reasons"] else ""
            await channel.send(
                f"💡 **Hiệp {round_num}/{max_rounds} — Luyện gợi ý**{reasons_str}\n"
                f"👉 **`{rec['text']}`**"
            )
            sample_path = f"rec_sample_{user_id}.mp3"
            if await generate_sample_audio(rec["text"], sample_path):
                await channel.send(file=discord.File(sample_path))
                os.remove(sample_path)
            return
        round_type = "sentence"

    next_task = get_next_sentence(user_id, exclude_sentences=session.get("used_sentences", []))
    session["mode"] = "sentence"
    session["sentence"] = next_task["sentence"]
    session["new_word"] = next_task["new_word"]
    session["fail_count"] = 0
    session["drill_done"] = False
    session.setdefault("used_sentences", []).append(next_task["sentence"])

    if next_task["new_word"]:
        await start_keyword_drill(channel, session, next_task["sentence"], next_task["new_word"])
    else:
        await channel.send(
            f"🎯 **Hiệp {round_num}/{max_rounds} — Đọc câu:**\n"
            f"👉 **`{next_task['sentence']}`**"
        )

@client.event
async def on_ready():
    print("--------------------------------------------------")
    print(f"🤖 Bot Giáo Viên AI đã kích hoạt thành công!")
    print(f"🎯 Tên Bot: {client.user.name} (ID: {client.user.id})")
    print("🚀 Sẵn sàng tóm file ghi âm từ iPhone của bạn!")
    print("--------------------------------------------------")

async def start_keyword_drill(channel, session, sentence, new_word):
    """
    Khi câu có từ mới: giảng bài + chuyển sang keyword_drill mode.
    User phải đọc đúng từ khóa trước khi đọc cả câu.
    """
    await send_new_word_tutorial(channel, sentence, new_word)
    session["mode"] = "keyword_drill"
    session["keyword_target"] = new_word
    session["keyword_fails"] = 0

@client.event
async def on_message(message):
    # Bỏ qua tin nhắn do chính Bot tự gửi để tránh vòng lặp vô hạn
    if message.author == client.user:
        return

    user_id = str(message.author.id)
    user_name = message.author.name

    # ========================================================
    # LỆNH VÀO HỌC: !go (adaptive session) — !daily là alias
    # ========================================================
    if message.content.strip() in ("!go", "!daily"):
        if user_id in user_sessions:
            if user_sessions[user_id]["mode"] == "completed":
                await message.reply("✅ Đã hoàn thành phiên hôm nay! Gõ `!more` để thêm hiệp, hoặc chờ tới mai.")
            else:
                await message.reply("🔄 Bạn đang ở trong hiệp đấu rồi! Hãy nộp bài ghi âm cho câu hiện tại nhé.")
            return

        await message.channel.send("🔄 Đang chuẩn bị phiên học thích ứng cho bạn...")

        user_data = get_or_create_user(user_id, user_name)
        streak = user_data["streak"]
        user_level = user_data.get("current_level", 1)

        user_sessions[user_id] = {
            "round": 1,
            "max_rounds": 5,
            "sentence": "",
            "new_word": None,
            "fail_count": 0,
            "mode": "sentence",
            "drill_words": [],
            "drill_index": 0,
            "drill_fails": 0,
            "drill_passed": 0,
            "drill_done": False,
            "used_sentences": [],
            "session_stats": {"passed_first_try": 0, "needed_drill": 0, "skipped": 0},
            "started_at": datetime.now().isoformat(),
            "scores": [],
            "content_segments_used": 0,
            "round_history": [],
            "difficulty_pref": user_level,
        }

        await message.channel.send(f"🔥 **Chuỗi ngày học:** `{streak} ngày` | Phiên adaptive 5 hiệp — bot sẽ tự chọn bài phù hợp!")

        await _advance_to_next_round(message.channel, user_id, user_sessions[user_id])
        return

    # ========================================================
    # LỆNH TRỢ GIÚP: !help
    # ========================================================
    if message.content.strip() == "!help":
        await message.reply(
            "📖 **HƯỚNG DẪN SỬ DỤNG**\n\n"
            "🎯 `!go` — Bắt đầu phiên học (bot tự chọn bài phù hợp)\n"
            "⏭️ `!skip` — Bỏ qua bài hiện tại\n"
            "🛑 `!stop` — Thoát phiên học\n"
            "📊 `!me` — Xem hồ sơ + tiến bộ + gợi ý\n\n"
            "**Cách học:** Gõ `!go` → Bot đưa bài → Ghi âm đọc → Bot chấm điểm.\n"
            "Bot tự điều chỉnh: đọc tốt → tăng khó, kẹt nhiều → chuyển bài dễ hơn. 🎚️"
        )
        return

    # ========================================================
    # LỆNH HỒ SƠ TỔNG HỢP: !me
    # ========================================================
    if message.content.strip() == "!me":
        stats = get_user_stats(user_id)
        profile = get_learner_profile(user_id)
        progress = get_learning_progress(user_id)

        if not stats and not profile["hard_words"]:
            await message.reply("📊 Chưa có dữ liệu. Gõ `!go` để bắt đầu luyện nhé!")
            return

        msg = "📊 **HỒ SƠ CỦA BẠN**\n\n"

        if stats:
            level_names = {1: "🟢 Dễ", 2: "🟡 TB", 3: "🔴 Khó"}
            level_text = level_names.get(stats.get("level", 1), "🟢 Dễ")
            msg += f"🔥 Streak: **{stats.get('streak', 0)} ngày** | 📚 Phiên: **{stats.get('total_sessions', 0)}** | 🎚️ {level_text}\n"
            if stats.get("avg_score"):
                trend_icon = "📈" if stats.get("trend", 0) >= 0 else "📉"
                msg += f"{trend_icon} Điểm TB: **{stats['avg_score']}/100**\n"

        if progress["score_count"] > 0:
            trend_icons = {"improving": "📈", "declining": "📉", "stable": "➡️"}
            msg += f"\n**Xu hướng:** {trend_icons[progress['pronunciation_trend']]} Phát âm {progress['pronunciation_trend']}"
            msg += f" | {trend_icons[progress['mastery_trend']]} Mastery {progress['mastery_trend']}\n"

        if profile["hard_words"]:
            words_str = ", ".join(f"*{w['word']}*" for w in profile["hard_words"][:5])
            msg += f"\n🔴 **Từ yếu:** {words_str}\n"

        if profile["hard_phonemes"]:
            ph_str = ", ".join(f"/{p['phoneme']}/" for p in profile["hard_phonemes"][:4])
            msg += f"🔤 **Âm yếu:** {ph_str}\n"

        if profile["hard_patterns"]:
            pat_str = ", ".join(f"\"{p['pattern']}\"" for p in profile["hard_patterns"][:3])
            msg += f"🗣️ **Cấu trúc cần luyện:** {pat_str}\n"

        if progress.get("phoneme_improvement"):
            msg += f"\n✅ **Tiến bộ gần đây:** {', '.join(f'/{p}/' for p in progress['phoneme_improvement'][:3])}\n"

        if profile["mastered_words"]:
            msg += f"🏆 **Đã thành thạo:** {len(profile['mastered_words'])} từ\n"

        recs = get_practice_recommendations(user_id, limit=3)
        if recs.get("recommended_words") or recs.get("recommended_phonemes"):
            msg += "\n💡 **Nên tập trung:**"
            if recs.get("recommended_words"):
                msg += f" Từ: {', '.join(f'*{w}*' for w in recs['recommended_words'][:3])}"
            if recs.get("recommended_phonemes"):
                msg += f" | Âm: {', '.join(f'/{p}/' for p in recs['recommended_phonemes'][:2])}"
            msg += "\n"

        health = get_content_health()
        if health["total_segments"] > 0:
            msg += f"\n📦 **Kho bài:** {health['total_segments']} segments | ~{health['coverage_days']} ngày còn lại\n"

        msg += "\n💡 Gõ `!go` để luyện tập!"
        await message.reply(msg)
        return

    # ========================================================
    # LỆNH BỎ QUA: !skip
    # ========================================================
    if message.content.strip() == "!skip":
        if user_id not in user_sessions:
            await message.reply("⚠️ Bạn chưa bắt đầu phiên học. Gõ `!go` để vào học nhé!")
            return
        
        session = user_sessions[user_id]
        
        if session["mode"] == "sentence":
            update_sentence_progress(user_id, session["sentence"], success=False)
            if session["new_word"]:
                save_failed_word(user_id, session["new_word"])
        session["session_stats"]["skipped"] += 1

        session.setdefault("round_history", []).append({
            "type": session.get("mode", "sentence"),
            "passed": False,
            "score": None,
        })
        
        session["round"] += 1
        session["fail_count"] = 0
        
        if session["round"] > session["max_rounds"]:
            new_streak = update_user_progress(user_id, status="completed")
            increment_total_sessions(user_id)
            _write_session_analytics(user_id, session)
            stats = session["session_stats"]
            await message.channel.send(
                f"🏆 **HOÀN THÀNH PHIÊN HỌC!** 🔥 Chuỗi: `{new_streak} ngày`\n"
                f"📊 Pass ngay: {stats['passed_first_try']} | Cần drill: {stats['needed_drill']} | Bỏ qua: {stats['skipped']}\n"
                f"💡 Gõ `!more` để thêm hiệp bonus, hoặc nghỉ ngơi tới mai!"
            )
            session["mode"] = "completed"
        else:
            await _advance_to_next_round(message.channel, user_id, session)
        return

    # ========================================================
    # LỆNH THOÁT: !stop
    # ========================================================
    if message.content.strip() == "!stop":
        if user_id not in user_sessions:
            await message.reply("⚠️ Bạn chưa có phiên học nào đang chạy.")
            return
        
        session = user_sessions[user_id]
        completed_rounds = session["round"] - 1
        
        if completed_rounds > 0:
            new_streak = update_user_progress(user_id, status="completed")
            _write_session_analytics(user_id, session)
            streak_msg = f"🔥 Chuỗi: `{new_streak} ngày` (vẫn được tính vì đã hoàn thành {completed_rounds} hiệp)"
        else:
            streak_msg = "⚠️ Chưa hoàn thành hiệp nào nên không tính streak."
        
        del user_sessions[user_id]
        await message.reply(f"🛑 **Đã thoát phiên học.**\n{streak_msg}\nGõ `!go` khi muốn quay lại nhé!")
        return

    # ========================================================
    # LỆNH THÊM HIỆP: !more
    # ========================================================
    if message.content.strip() == "!more":
        if user_id not in user_sessions or user_sessions[user_id]["mode"] != "completed":
            await message.reply("⚠️ Bạn cần hoàn thành phiên học trước (gõ `!go` để bắt đầu).")
            return
        session = user_sessions[user_id]
        if session["max_rounds"] >= 8:
            await message.reply("🛑 Đã đạt tối đa **8 hiệp** cho 1 phiên. Nghỉ ngơi rồi quay lại vào ngày mai nhé! 💤")
            del user_sessions[user_id]
            return
        session["max_rounds"] += 1
        session["round"] = session["max_rounds"]
        session["fail_count"] = 0
        await message.channel.send(
            f"💪 **HIỆP BONUS {session['round']}/{session['max_rounds']}!** Tinh thần chiến đấu cao!"
        )
        await _advance_to_next_round(message.channel, user_id, session)
        return

    # ========================================================
    # LỆNH XEM THỐNG KÊ: !stats
    # ========================================================
    if message.content.strip() == "!stats":
        stats = get_user_stats(user_id)
        if not stats:
            await message.reply("📊 Chưa có dữ liệu. Gõ `!go` để bắt đầu luyện nhé!")
            return
        
        level_names = {1: "🟢 Dễ", 2: "🟡 Trung bình", 3: "🔴 Khó"}
        level_text = level_names.get(stats.get("level", 1), "🟢 Dễ")
        
        msg = (
            f"📊 **THỐNG KÊ CỦA BẠN**\n\n"
            f"🔥 Streak: **{stats.get('streak', 0)} ngày**\n"
            f"📚 Tổng phiên: **{stats.get('total_sessions', 0)}**\n"
            f"🎚️ Cấp độ: **{level_text}**\n"
        )
        
        if stats.get("avg_score"):
            trend_icon = "📈" if stats.get("trend", 0) >= 0 else "📉"
            msg += f"{trend_icon} Điểm TB (30 ngày): **{stats['avg_score']}/100**"
            if stats.get("trend", 0) != 0:
                msg += f" ({'+' if stats['trend'] > 0 else ''}{stats['trend']} so với tháng trước)"
            msg += "\n"
        if stats.get("total_attempts"):
            msg += f"🎯 Tổng lần chấm: **{stats['total_attempts']}**\n"
        
        # Top error patterns
        if stats.get("top_errors"):
            msg += "\n🔍 **Điểm yếu lặp lại:**\n"
            for err in stats["top_errors"][:5]:
                label = ERROR_TYPE_LABELS.get(err["type"], err["type"])
                msg += f"  {label}: *{err['word']}* — {err['count']} lần\n"
        
        if stats.get("mastered"):
            msg += f"\n✅ Từ đã thuộc (Box 3): **{stats['mastered']}/{stats.get('total_learned', '?')}**\n"
        
        weak_words = get_weak_words(user_id, limit=5)
        if weak_words:
            msg += "\n📝 **Từ hay sai nhất:**\n"
            for ww in weak_words:
                msg += f"  • *{ww['word']}* — TB {ww['avg_score']}/100, pass {ww['success_rate']}% ({ww['attempt_count']} lần)\n"

        weak_phonemes = get_weak_phonemes(user_id, limit=5)
        if weak_phonemes:
            msg += "\n🔤 **Âm hay lỗi nhất:**\n"
            for wp in weak_phonemes:
                examples = ", ".join(wp["example_words"][:3]) if wp["example_words"] else ""
                msg += f"  • /{wp['phoneme']}/ — {wp['error_count']} lần"
                if examples:
                    msg += f" (vd: {examples})"
                msg += "\n"

        await message.reply(msg)
        return

    # ========================================================
    # LỆNH XEM HỒ SƠ HỌC: !profile
    # ========================================================
    if message.content.strip() == "!profile":
        profile = get_learner_profile(user_id)
        insights = get_learning_insights(user_id)
        recs = get_practice_recommendations(user_id, limit=5)

        if not profile["hard_words"] and not profile["hard_phonemes"] and not profile["hard_patterns"]:
            await message.reply("📋 Chưa có đủ dữ liệu để phân tích. Luyện thêm vài phiên rồi quay lại nhé!")
            return

        msg = "📋 **HỒ SƠ HỌC TẬP CỦA BẠN**\n\n"

        if profile["hard_words"]:
            msg += "🔴 **Từ đang yếu:**\n"
            for w in profile["hard_words"][:5]:
                msg += f"  • *{w['word']}* — {w['mastery']} ({w['attempt_count']} lần, pass {w['success_rate']}%)\n"
            msg += "\n"

        if profile["hard_phonemes"]:
            msg += "🔤 **Âm đang yếu:**\n"
            for p in profile["hard_phonemes"][:5]:
                examples = ", ".join(p["example_words"][:3]) if p["example_words"] else ""
                msg += f"  • /{p['phoneme']}/ — {p['mastery']} ({p['error_count']} lỗi)"
                if examples:
                    msg += f" vd: {examples}"
                msg += "\n"
            msg += "\n"

        if profile["hard_patterns"]:
            msg += "🗣️ **Cấu trúc cần luyện:**\n"
            for pt in profile["hard_patterns"][:5]:
                msg += f"  • \"{pt['pattern']}\" — {pt['mastery']} (TB {pt['avg_score']}/100)\n"
            msg += "\n"

        if profile["mastered_words"]:
            mastered_sample = ", ".join(profile["mastered_words"][:8])
            msg += f"✅ **Từ đã thành thạo ({len(profile['mastered_words'])}):** {mastered_sample}\n\n"

        if insights.get("top_weakness_phoneme"):
            msg += f"⚡ **Điểm yếu #1:** /{insights['top_weakness_phoneme']}/\n"
        if insights.get("most_improved_word"):
            msg += f"📈 **Tiến bộ nhất:** *{insights['most_improved_word']}*\n"
        if insights.get("hardest_pattern"):
            msg += f"🎯 **Cấu trúc khó nhất:** \"{insights['hardest_pattern']}\"\n"
        if insights.get("sessions_this_week") is not None:
            msg += f"📅 **Phiên tuần này:** {insights['sessions_this_week']}\n"

        if recs.get("recommended_words") or recs.get("recommended_phonemes") or recs.get("recommended_patterns"):
            msg += "\n💡 **NÊN LUYỆN TIẾP:**\n"
            if recs.get("recommended_words"):
                words_list = ", ".join(f"*{w}*" for w in recs["recommended_words"][:5])
                msg += f"  Từ: {words_list}\n"
            if recs.get("recommended_phonemes"):
                ph_list = ", ".join(f"/{p}/" for p in recs["recommended_phonemes"][:3])
                msg += f"  Âm: {ph_list}\n"
            if recs.get("recommended_patterns"):
                pat_list = ", ".join(f"\"{p}\"" for p in recs["recommended_patterns"][:3])
                msg += f"  Cấu trúc: {pat_list}\n"

        await message.reply(msg)
        return

    # ========================================================
    # LỆNH SHADOWING: !shadow
    # ========================================================
    if message.content.strip() == "!shadow":
        content_item = pick_content_shadowing(user_id)
        if content_item:
            item = {"id": content_item["id"], "text": content_item["text"], "source": "content"}
        else:
            item = pick_shadowing_item(user_id)
            if item:
                item = dict(item)
                item["source"] = "builtin"

        if not item:
            await message.reply("📭 Chưa có câu shadowing nào. Gõ `!import` để nhập nội dung, hoặc liên hệ admin!")
            return

        user_sessions[user_id] = {
            "mode": "shadowing",
            "shadowing_item": item,
            "round": 0,
            "max_rounds": 0,
            "sentence": item["text"],
            "new_word": None,
            "fail_count": 0,
            "drill_words": [],
            "drill_index": 0,
            "drill_fails": 0,
            "drill_passed": 0,
            "drill_done": False,
            "used_sentences": [],
            "session_stats": {"passed_first_try": 0, "needed_drill": 0, "skipped": 0},
            "started_at": datetime.now().isoformat(),
            "scores": [],
            "content_segments_used": 0,
        }

        source_label = " (từ thư viện)" if item.get("source") == "content" else ""
        await message.channel.send(
            f"🎧 **SHADOWING MODE**{source_label}\n\n"
            f"👉 **`{item['text']}`**\n\n"
            f"Nghe mẫu bên dưới, rồi ghi âm đọc theo nhé! 🎤"
        )
        sample_path = f"shadow_sample_{user_id}.mp3"
        if await generate_sample_audio(item["text"], sample_path):
            await message.channel.send(file=discord.File(sample_path))
            os.remove(sample_path)
        return

    # ========================================================
    # LỆNH XEM BÀI TẬP HÔM NAY: !drills
    # ========================================================
    if message.content.strip() == "!drills":
        practice = generate_daily_practice(user_id)

        if not practice["phoneme_drills"] and not practice["word_drills"] and not practice["pattern_drills"]:
            await message.reply("📋 Chưa có đủ dữ liệu để tạo bài tập. Luyện thêm vài phiên `!go` rồi quay lại!")
            return

        msg = "📝 **BÀI TẬP HÔM NAY**\n\n"

        if practice["phoneme_drills"]:
            msg += "🔤 **Luyện âm:**\n"
            for drill in practice["phoneme_drills"]:
                words = ", ".join(drill["words"])
                msg += f"  /{drill['phoneme']}/ → {words}\n"
            msg += "\n"

        if practice["word_drills"]:
            msg += "📝 **Từ cần ôn:**\n"
            for drill in practice["word_drills"]:
                msg += f"  • *{drill['word']}* (TB: {drill['avg_score']}/100)\n"
            msg += "\n"

        if practice["pattern_drills"]:
            msg += "🗣️ **Cấu trúc cần luyện:**\n"
            for drill in practice["pattern_drills"]:
                msg += f"  **\"{drill['pattern']}\"**\n"
                for s in drill["sentences"]:
                    msg += f"    → {s}\n"
            msg += "\n"

        msg += "💡 Gõ `!shadow` để luyện shadowing, hoặc `!go` để vào phiên chấm điểm!"
        await message.reply(msg)
        return

    # ========================================================
    # LỆNH NHẬP NỘI DUNG: !import
    # ========================================================
    if message.content.strip().startswith("!import"):
        raw = message.content[len("!import"):].strip()

        if message.attachments:
            txt_files = [a for a in message.attachments if a.filename.endswith(".txt")]
            if txt_files:
                total_items = 0
                total_segs = 0
                for att in txt_files:
                    file_bytes = await att.read()
                    file_text = file_bytes.decode("utf-8", errors="ignore")
                    items = _parse_import_text(file_text)
                    if items:
                        results = bulk_import(items)
                        total_items += len(results)
                        total_segs += sum(r["segment_count"] for r in results)
                await message.reply(
                    f"✅ **Đã nhập từ file!**\n"
                    f"📄 {total_items} bài | 🔢 {total_segs} segments"
                )
                return

        if not raw:
            await message.reply(
                "📥 **Cách dùng `!import`:**\n"
                "```\n!import Tiêu đề bài\nNội dung câu 1. Câu 2.\nĐoạn tiếp theo.\n```\n"
                "**Nhập nhiều bài cùng lúc** — dùng `---` ngăn cách:\n"
                "```\n!import Bài 1\nNội dung bài 1.\n---\nBài 2\nNội dung bài 2.\n```\n"
                "**Đính kèm file `.txt`** — bot tự đọc và nhập.\n"
                "Markdown (`#`, `*`, `-` đầu dòng) sẽ tự động bị loại bỏ."
            )
            return

        items = _parse_import_text(raw)
        if not items:
            await message.reply("⚠️ Không tìm được nội dung hợp lệ. Mỗi bài cần tiêu đề dòng 1 và nội dung từ dòng 2.")
            return

        results = bulk_import(items)
        total_segs = sum(r["segment_count"] for r in results)

        if len(results) == 1:
            r = results[0]
            await message.reply(
                f"✅ **Đã nhập thành công!**\n"
                f"📄 *{items[0]['title']}*\n"
                f"🔢 Tách được **{r['segment_count']}** câu (segments)\n"
                f"🆔 ID: `{r['item_id']}`"
            )
        else:
            await message.reply(
                f"✅ **Đã nhập {len(results)} bài!**\n"
                f"🔢 Tổng cộng **{total_segs}** segments"
            )
        return

    # ========================================================
    # LỆNH THƯ VIỆN: !library
    # ========================================================
    if message.content.strip().startswith("!library"):
        args = message.content[len("!library"):].strip()

        if not args:
            items = list_content_items(limit=10)
            if not items:
                await message.reply("📚 Thư viện trống. Gõ `!import` để thêm nội dung!")
                return
            msg = "📚 **THƯ VIỆN NỘI DUNG** (gần nhất)\n\n"
            for item in items:
                tags_str = ", ".join(item["tags"]) if item["tags"] else ""
                tag_display = f" [{tags_str}]" if tags_str else ""
                msg += f"• `{item['id']}` **{item['title']}** (diff={item['difficulty']}){tag_display}\n"
            msg += f"\n💡 `!library <từ khóa>` để tìm kiếm"
            await message.reply(msg)
            return

        results = search_content(args, limit=10)
        if not results:
            await message.reply(f"🔍 Không tìm thấy nội dung nào cho \"{args}\".")
            return

        msg = f"🔍 **Kết quả cho \"{args}\":**\n\n"
        for item in results:
            msg += f"• `{item['id']}` **{item['title']}** (diff={item['difficulty']})\n"
        await message.reply(msg)
        return

    # ========================================================
    # LỆNH KẾ HOẠCH HÔM NAY: !plan
    # ========================================================
    if message.content.strip() == "!plan":
        session_plan = build_today_session(user_id)

        msg = "🗓️ **KẾ HOẠCH HỌC HÔM NAY**\n\n"

        if session_plan["shadowing"]:
            msg += "🎧 **Shadowing (nghe + đọc theo):**\n"
            for i, s in enumerate(session_plan["shadowing"], 1):
                reasons_str = ", ".join(s["reasons"][:2]) if s["reasons"] else ""
                msg += f"  {i}. \"{s['text'][:60]}{'...' if len(s['text']) > 60 else ''}\" (diff={s['difficulty_score']})"
                if reasons_str:
                    msg += f" — *{reasons_str}*"
                msg += "\n"
            msg += "\n"

        if session_plan["review_words"]:
            words_list = ", ".join(f"*{w}*" for w in session_plan["review_words"])
            msg += f"📝 **Từ cần ôn:** {words_list}\n\n"

        if session_plan["review_phonemes"]:
            ph_list = ", ".join(f"/{p}/" for p in session_plan["review_phonemes"])
            msg += f"🔤 **Âm cần luyện:** {ph_list}\n\n"

        if session_plan["recommended_content"]:
            msg += "💡 **Nội dung gợi ý:**\n"
            for i, rec in enumerate(session_plan["recommended_content"][:5], 1):
                msg += f"  {i}. \"{rec['text'][:50]}{'...' if len(rec['text']) > 50 else ''}\" (score={rec['score']})\n"
            msg += "\n"

        if not session_plan["shadowing"] and not session_plan["review_words"] and not session_plan["recommended_content"]:
            msg += "📭 Chưa có đủ dữ liệu. Gõ `!go` để bắt đầu luyện, `!import` để thêm nội dung!\n"

        msg += "💡 Gõ `!shadow` để luyện shadowing, `!drills` cho bài tập, `!recommend` để xem gợi ý chi tiết."
        await message.reply(msg)
        return

    # ========================================================
    # LỆNH GỢI Ý NỘI DUNG: !recommend
    # ========================================================
    if message.content.strip().startswith("!recommend"):
        args = message.content[len("!recommend"):].strip()

        if args == "skip" and user_id in user_sessions and user_sessions[user_id].get("mode") == "recommend_practice":
            session = user_sessions[user_id]
            rec_id = session.get("current_rec_id")
            if rec_id:
                mark_skipped(rec_id)
            del user_sessions[user_id]
            await message.reply("⏭️ Đã bỏ qua. Gõ `!recommend` để xem gợi ý tiếp theo.")
            return

        recommendations = get_recommended_content(user_id, limit=3)
        if not recommendations:
            await message.reply("📭 Chưa có nội dung để gợi ý. Gõ `!import` để nhập nội dung trước!")
            return

        rec = recommendations[0]
        rec_id = record_recommendation(user_id, rec["segment_id"], reasons=rec["reasons"], score=rec["score"])

        msg = "💡 **GỢI Ý LUYỆN TẬP**\n\n"
        msg += f"👉 **\"{rec['text']}\"**\n"
        msg += f"📊 Độ khó: {rec['difficulty_score']}/5 | Score: {rec['score']}\n"
        if rec["reasons"]:
            msg += f"💬 Lý do: {', '.join(rec['reasons'][:3])}\n"
        msg += f"\n🎤 Ghi âm đọc câu trên để luyện tập! Hoặc `!recommend skip` để bỏ qua."

        user_sessions[user_id] = {
            "mode": "recommend_practice",
            "shadowing_item": {"id": rec["segment_id"], "text": rec["text"], "source": "content"},
            "current_rec_id": rec_id,
            "round": 0,
            "max_rounds": 0,
            "sentence": rec["text"],
            "new_word": None,
            "fail_count": 0,
            "drill_words": [],
            "drill_index": 0,
            "drill_fails": 0,
            "drill_passed": 0,
            "drill_done": False,
            "used_sentences": [],
            "session_stats": {"passed_first_try": 0, "needed_drill": 0, "skipped": 0},
            "started_at": datetime.now().isoformat(),
            "scores": [],
            "content_segments_used": 0,
        }

        await message.reply(msg)

        sample_path = f"recommend_sample_{user_id}.mp3"
        if await generate_sample_audio(rec["text"], sample_path):
            await message.channel.send(file=discord.File(sample_path))
            os.remove(sample_path)
        return

    # ========================================================
    # LỆNH XEM TIẾN BỘ: !progress
    # ========================================================
    if message.content.strip() == "!progress":
        progress = get_learning_progress(user_id)
        rec_metrics = get_recommendation_metrics(user_id)

        if progress["score_count"] == 0 and rec_metrics["total"] == 0:
            await message.reply("📈 Chưa có dữ liệu tiến bộ. Luyện thêm vài phiên `!go` rồi quay lại!")
            return

        trend_icons = {"improving": "📈", "declining": "📉", "stable": "➡️"}

        msg = "📈 **TIẾN BỘ CỦA BẠN**\n\n"

        if progress["score_count"] > 0:
            msg += f"{trend_icons[progress['pronunciation_trend']]} Phát âm: **{progress['pronunciation_trend']}** (TB: {progress['avg_score']}/100, {progress['score_count']} lần chấm)\n"
            msg += f"{trend_icons[progress['mastery_trend']]} Mastery: **{progress['mastery_trend']}**\n\n"

        if progress["phoneme_improvement"]:
            msg += f"✅ Âm tiến bộ: {', '.join(f'/{p}/' for p in progress['phoneme_improvement'][:5])}\n"
        if progress["phoneme_struggling"]:
            msg += f"🔴 Âm còn yếu: {', '.join(f'/{p}/' for p in progress['phoneme_struggling'][:5])}\n"
        if progress["word_improvement"]:
            msg += f"✅ Từ tiến bộ: {', '.join(f'*{w}*' for w in progress['word_improvement'][:5])}\n"
        if progress["word_declining"]:
            msg += f"🔴 Từ cần ôn: {', '.join(f'*{w}*' for w in progress['word_declining'][:5])}\n"

        if rec_metrics["total"] > 0:
            msg += f"\n📊 **Hiệu quả gợi ý:** {rec_metrics['total']} gợi ý"
            msg += f" | Hoàn thành: {rec_metrics['completion_rate']}%"
            msg += f" | Bỏ qua: {rec_metrics['skip_rate']}%\n"

        msg += "\n💡 Gõ `!profile` để xem chi tiết hồ sơ, `!plan` để xem kế hoạch hôm nay."
        await message.reply(msg)
        return

    # ========================================================
    # XỬ LÝ KHI USER GỬI FILE VOICE (TIN NHẮN THOẠI TỪ IPHONE)
    # ========================================================
    if user_id in user_sessions and message.attachments:
        session = user_sessions[user_id]
        
        if session["mode"] == "completed":
            await message.reply("✅ Phiên hôm nay đã xong! Gõ `!more` để thêm hiệp, hoặc chờ tới mai.")
            return
        
        attachment = message.attachments[0]
        
        # Nhận diện các định dạng âm thanh phổ biến của Discord di động (.ogg, .wav, .m4a, .mp3)
        if any(attachment.filename.lower().endswith(ext) for ext in ['.ogg', '.wav', '.mp3', '.m4a']):
            await message.channel.send("👂 Thầy AI đang nghe bài và phân tích khẩu hình...")
            
            # Tải file âm thanh từ máy chủ Discord về máy tính local
            temp_audio_path = f"temp_{user_id}_{attachment.filename}"
            try:
                audio_data = requests.get(attachment.url).content
                with open(temp_audio_path, "wb") as f:
                    f.write(audio_data)
            except Exception as e:
                await message.reply(f"❌ Lỗi tải file ghi âm từ Discord: {e}")
                return

            # ====================================================
            # NHÁNH 0: KEYWORD DRILL - Đọc từ khóa trước khi đọc câu
            # ====================================================
            if session["mode"] == "keyword_drill":
                keyword = session["keyword_target"]
                passed, confidence, heard = await asyncio.get_event_loop().run_in_executor(
                    None, functools.partial(analyze_single_word, temp_audio_path, keyword)
                )
                
                if os.path.exists(temp_audio_path):
                    os.remove(temp_audio_path)

                if passed:
                    session["mode"] = "sentence"
                    session["keyword_fails"] = 0
                    await message.reply(
                        f"✅ **{keyword.upper()}** — Phát âm chuẩn! (`{int(confidence*100)}%`)\n"
                        f"Giờ hãy đọc **cả câu** nhé:\n"
                        f"👉 **`{session['sentence']}`**"
                    )
                else:
                    session["keyword_fails"] += 1
                    if session["keyword_fails"] >= 3:
                        # Fail 3 lần từ khóa → cho qua luôn, đọc cả câu
                        session["mode"] = "sentence"
                        session["keyword_fails"] = 0
                        heard_text = f" (AI nghe thành: *{heard}*)" if heard and heard != keyword.lower() else ""
                        await message.reply(
                            f"🤝 Từ **{keyword.upper()}** khá khó{heard_text}. Thử đọc cả câu luôn nhé — "
                            f"đặt trong ngữ cảnh có khi lại dễ hơn!\n"
                            f"👉 **`{session['sentence']}`**"
                        )
                    else:
                        heard_text = f" (AI nghe thành: *{heard}*)" if heard and heard != keyword.lower() else ""
                        await message.reply(
                            f"❌ Chưa đạt{heard_text}. Nghe lại mẫu rồi thử lần nữa! "
                            f"(Lần {session['keyword_fails']}/3)"
                        )
                        sample_path = f"keyword_sample_{user_id}.mp3"
                        if await generate_sample_audio(keyword, sample_path):
                            await message.channel.send(file=discord.File(sample_path))
                            os.remove(sample_path)
                return

            # ====================================================
            # NHÁNH 0.5: SHADOWING MODE - Đọc theo mẫu
            # ====================================================
            if session["mode"] == "shadowing":
                item = session["shadowing_item"]
                score, ansi_feedback, error_details, problem_words, error_types, word_scores = await asyncio.get_event_loop().run_in_executor(
                    None, functools.partial(analyze_audio_with_whisper, temp_audio_path, item["text"])
                )

                if os.path.exists(temp_audio_path):
                    os.remove(temp_audio_path)

                record_shadowing_attempt(user_id, item["id"], score)

                if item.get("source") == "content":
                    record_usage(item["id"], "shadowing")

                session["scores"].append(score)
                result_msg = (
                    f"🎧 **KẾT QUẢ SHADOWING** — **{score}/100** điểm\n"
                    f"```ansi\n{ansi_feedback}\n```"
                )
                if error_details and score < 100:
                    result_msg += f"\n{error_details}"

                is_adaptive = "round_history" in session and session["max_rounds"] > 0

                if score >= 80:
                    if is_adaptive:
                        result_msg += "\n\n✅ Tốt lắm!"
                        await message.reply(result_msg)
                        session.setdefault("round_history", []).append({
                            "type": "shadowing", "passed": True, "score": score,
                        })
                        session["round"] += 1
                        if session["round"] > session["max_rounds"]:
                            new_streak = update_user_progress(user_id, status="completed")
                            increment_total_sessions(user_id)
                            _write_session_analytics(user_id, session)
                            stats = session["session_stats"]
                            await message.channel.send(
                                f"🏆 **HOÀN THÀNH!** 🔥 Chuỗi: `{new_streak} ngày`\n"
                                f"📊 Pass: {stats['passed_first_try']} | Drill: {stats['needed_drill']} | Skip: {stats['skipped']}\n"
                                f"💡 Gõ `!more` để thêm hiệp bonus!"
                            )
                            session["mode"] = "completed"
                        else:
                            await _advance_to_next_round(message.channel, user_id, session)
                    else:
                        result_msg += "\n\n✅ Tốt lắm! Gõ `!shadow` để thử câu khác, hoặc `!go` để vào phiên chính."
                        await message.reply(result_msg)
                        del user_sessions[user_id]
                else:
                    result_msg += "\n\n🔄 Chưa đạt 80 — nghe lại mẫu rồi thử lần nữa! Hoặc gõ `!skip` để bỏ qua."
                    await message.reply(result_msg)
                return

            # ====================================================
            # NHÁNH 0.6: RECOMMEND PRACTICE - Luyện nội dung gợi ý
            # ====================================================
            if session["mode"] == "recommend_practice":
                item = session["shadowing_item"]
                score, ansi_feedback, error_details, problem_words, error_types, word_scores = await asyncio.get_event_loop().run_in_executor(
                    None, functools.partial(analyze_audio_with_whisper, temp_audio_path, item["text"])
                )

                if os.path.exists(temp_audio_path):
                    os.remove(temp_audio_path)

                record_usage(item["id"], "recommend_practice")
                session["scores"].append(score)

                result_msg = (
                    f"💡 **KẾT QUẢ LUYỆN GỢI Ý** — **{score}/100** điểm\n"
                    f"```ansi\n{ansi_feedback}\n```"
                )
                if error_details and score < 100:
                    result_msg += f"\n{error_details}"

                is_adaptive = "round_history" in session and session["max_rounds"] > 0

                if score >= 80:
                    rec_id = session.get("current_rec_id")
                    if rec_id:
                        mark_completed(rec_id, score)
                    if is_adaptive:
                        result_msg += "\n\n✅ Xuất sắc!"
                        await message.reply(result_msg)
                        session.setdefault("round_history", []).append({
                            "type": "recommend", "passed": True, "score": score,
                        })
                        session["round"] += 1
                        if session["round"] > session["max_rounds"]:
                            new_streak = update_user_progress(user_id, status="completed")
                            increment_total_sessions(user_id)
                            _write_session_analytics(user_id, session)
                            stats = session["session_stats"]
                            await message.channel.send(
                                f"🏆 **HOÀN THÀNH!** 🔥 Chuỗi: `{new_streak} ngày`\n"
                                f"📊 Pass: {stats['passed_first_try']} | Drill: {stats['needed_drill']} | Skip: {stats['skipped']}\n"
                                f"💡 Gõ `!more` để thêm hiệp bonus!"
                            )
                            session["mode"] = "completed"
                        else:
                            await _advance_to_next_round(message.channel, user_id, session)
                    else:
                        result_msg += "\n\n✅ Xuất sắc! Gõ `!recommend` để nhận gợi ý tiếp, hoặc `!go` để vào phiên chính."
                        await message.reply(result_msg)
                        del user_sessions[user_id]
                else:
                    result_msg += "\n\n🔄 Chưa đạt 80. Thử lại hoặc gõ `!skip` để bỏ qua."
                    await message.reply(result_msg)
                return

            # ====================================================
            # NHÁNH 1: WORD DRILL MODE - Chấm từng từ riêng lẻ
            # ====================================================
            if session["mode"] == "word_drill":
                current_word = session["drill_words"][session["drill_index"]]
                passed, confidence, heard = await asyncio.get_event_loop().run_in_executor(
                    None, functools.partial(analyze_single_word, temp_audio_path, current_word)
                )
                
                if os.path.exists(temp_audio_path):
                    os.remove(temp_audio_path)

                if passed:
                    session["drill_fails"] = 0
                    session["drill_passed"] += 1
                    await message.reply(
                        f"✅ **{current_word.upper()}** — Chuẩn rồi! (độ tự tin: `{int(confidence*100)}%`)"
                    )
                    session["drill_index"] += 1
                else:
                    session["drill_fails"] += 1
                    if session["drill_fails"] >= 2:
                        # Fail 2 lần trên 1 từ drill → bỏ qua để không nản, đã có Sổ đen lo
                        await message.reply(
                            f"🤝 Từ **{current_word.upper()}** khá hóc búa! Thầy bỏ vào *Danh sách phục thù* để luyện kỹ hơn sau nhé."
                        )
                        save_failed_word(user_id, current_word)
                        session["drill_index"] += 1
                        session["drill_fails"] = 0
                    else:
                        heard_text = f" (AI nghe thành: *{heard}*)" if heard and heard != current_word.lower() else ""
                        await message.reply(
                            f"❌ Chưa đạt{heard_text}. Nghe lại audio mẫu và thử một lần nữa nhé! "
                            f"(Lần {session['drill_fails']}/2)"
                        )
                        sample_path = f"drill_sample_{user_id}.mp3"
                        if await generate_sample_audio(current_word, sample_path):
                            await message.channel.send(file=discord.File(sample_path))
                            os.remove(sample_path)
                        return  # Chờ user ghi âm lại

                # Kiểm tra còn từ nào cần drill không
                if session["drill_index"] < len(session["drill_words"]):
                    next_word = session["drill_words"][session["drill_index"]]
                    await message.channel.send(f"➡️ Tiếp theo, hãy đọc từ: **{next_word.upper()}** 👇")
                    sample_path = f"drill_sample_{user_id}.mp3"
                    if await generate_sample_audio(next_word, sample_path):
                        await message.channel.send(file=discord.File(sample_path))
                        os.remove(sample_path)
                else:
                    # Drill xong hết → kiểm tra tỉ lệ thực sự pass được
                    total_drilled = len(session["drill_words"])
                    passed_count = session["drill_passed"]
                    pass_rate = passed_count / total_drilled if total_drilled > 0 else 0

                    # Reset drill state
                    session["mode"] = "sentence"
                    session["drill_words"] = []
                    session["drill_index"] = 0
                    session["drill_passed"] = 0

                    if pass_rate >= 0.5:
                        # Đủ từ pass → cho thử lại câu 1 lần cuối cùng
                        session["fail_count"] = 0
                        session["drill_done"] = True  # Đánh dấu đã drill — nếu vẫn fail sẽ auto-skip
                        await message.channel.send(
                            f"💪 **Đã luyện {passed_count}/{total_drilled} từ!** Thử đọc lại cả câu **1 lần cuối** nào:\n"
                            f"👉 **`{session['sentence']}`**"
                        )
                    else:
                        update_sentence_progress(user_id, session["sentence"], success=False)
                        if session["new_word"]:
                            save_failed_word(user_id, session["new_word"])

                        session.setdefault("round_history", []).append({
                            "type": "sentence", "passed": False, "score": None,
                        })
                        session["round"] += 1
                        session["fail_count"] = 0

                        await message.channel.send(
                            f"🤝 Bạn chỉ luyện được **{passed_count}/{total_drilled} từ** — câu này còn hơi sớm với cơ miệng hiện tại. "
                            f"Thầy đã cất vào *Danh sách phục thù*, ngày mai quay lại chinh phục nhé!\n"
                        )

                        if session["round"] > session["max_rounds"]:
                            new_streak = update_user_progress(user_id, status="completed")
                            increment_total_sessions(user_id)
                            _write_session_analytics(user_id, session)
                            stats = session["session_stats"]
                            await message.channel.send(
                                f"🏆 **Hoàn thành!** 🔥 Chuỗi: `{new_streak} ngày`\n"
                                f"📊 Pass: {stats['passed_first_try']} | Drill: {stats['needed_drill']} | Skip: {stats['skipped']}\n"
                                f"💡 Gõ `!more` để thêm hiệp bonus!"
                            )
                            session["mode"] = "completed"
                        else:
                            await _advance_to_next_round(message.channel, user_id, session)
                return

            # ====================================================
            # NHÁNH 2: SENTENCE MODE - Chấm cả câu (logic gốc)
            # ====================================================
            score, ansi_feedback, error_details, problem_words, error_types, word_scores = await asyncio.get_event_loop().run_in_executor(
                None, functools.partial(analyze_audio_with_whisper, temp_audio_path, session["sentence"])
            )
            
            # Xóa file tạm ngay lập tức sau khi xử lý xong để nhẹ máy local
            if os.path.exists(temp_audio_path):
                os.remove(temp_audio_path)
            
            # Log điểm + lỗi vào database để track pattern dài hạn
            log_score(user_id, session["sentence"], score)
            session["scores"].append(score)
            for word, err_type in error_types:
                log_error_pattern(user_id, err_type, word)

            if word_scores:
                record_word_attempts_batch(user_id, word_scores)

            _ERR_PHONEME = {"th_sound": "θ", "r_l_confusion": "ɹ", "sh_sound": "ʃ", "final_consonant": "C#", "vowel_stress": "V"}
            phoneme_errs = []
            for word, err_type in error_types:
                ph = _ERR_PHONEME.get(err_type)
                if ph:
                    phoneme_errs.append((ph, word))
            if phoneme_errs:
                record_phoneme_errors_batch(user_id, phoneme_errs)

            matched_patterns = extract_patterns(session["sentence"])
            if matched_patterns:
                record_pattern_attempts_batch(user_id, matched_patterns, score)

            # Gộp kết quả chấm điểm thành 1-2 message thay vì 3-4
            progress_bar = "🟩" * session["round"] + "⬜" * (session["max_rounds"] - session["round"])
            score_block = (
                f"📊 [{progress_bar}] Hiệp {session['round']}/{session['max_rounds']} — "
                f"**{score}/100** điểm\n"
                f"```ansi\n{ansi_feedback}\n```"
            )
            if error_details and score < 100:
                score_block += f"\n{error_details}"
            await message.reply(score_block)

            # CHUYỂN LOGIC ĐIỀU HƯỚNG HIỆP ĐẤU
            if score >= 80:
                # PHÁT ÂM ĐẠT CHUẨN -> ĐƯỢC QUA MÀN
                update_sentence_progress(user_id, session["sentence"], success=True)
                if session["new_word"]:
                    clear_failed_word(user_id, session["new_word"])
                if session["fail_count"] == 0:
                    session["session_stats"]["passed_first_try"] += 1
                
                # Auto-adjust level dựa trên xu hướng điểm gần nhất
                level_change = adjust_user_level(user_id)
                if level_change == "up":
                    await message.channel.send("🎉 **LEVEL UP!** Bạn đang tiến bộ rõ rệt — thử thách sẽ được nâng cấp! 📈")
                elif level_change == "down":
                    await message.channel.send("💪 Thầy sẽ đưa bài dễ hơn một chút để luyện lại nền tảng nhé! 📉")
                
                session["round"] += 1
                session["fail_count"] = 0
                
                session.setdefault("round_history", []).append({
                    "type": "sentence", "passed": True, "score": score,
                })

                if session["round"] > session["max_rounds"]:
                    new_streak = update_user_progress(user_id, status="completed")
                    increment_total_sessions(user_id)
                    _write_session_analytics(user_id, session)
                    stats = session["session_stats"]
                    await message.channel.send(
                        f"🏆 **HOÀN THÀNH CHỈ TIÊU NGÀY!** 🏆\n"
                        f"🔥 Chuỗi: **{new_streak} ngày**\n\n"
                        f"📊 **Tổng kết phiên học:**\n"
                        f"✅ Pass ngay: **{stats['passed_first_try']}** hiệp\n"
                        f"🔄 Cần drill: **{stats['needed_drill']}** hiệp\n"
                        f"⏭️ Bỏ qua: **{stats['skipped']}** hiệp\n\n"
                        f"💡 Gõ `!more` để thêm hiệp bonus, hoặc nghỉ ngơi tới mai! 💤"
                    )
                    session["mode"] = "completed"
                else:
                    await _advance_to_next_round(message.channel, user_id, session)
            else:
                # PHÁT ÂM CHƯA ĐẠT CHUẨN (<80 điểm)
                session["fail_count"] += 1
                
                # Nếu đã drill xong mà vẫn fail cả câu → auto-advance, không lặp vô tận
                if session["drill_done"]:
                    update_sentence_progress(user_id, session["sentence"], success=False)
                    if session["new_word"]:
                        save_failed_word(user_id, session["new_word"])
                    
                    session.setdefault("round_history", []).append({
                        "type": "sentence", "passed": False, "score": score,
                    })
                    session["round"] += 1
                    session["fail_count"] = 0
                    session["drill_done"] = False
                    
                    await message.channel.send(
                        f"🤝 Bạn đã drill từng từ rồi nhưng ghép câu vẫn khó — "
                        f"**không sao cả**, đây là chuyện bình thường! Fluency (nói trôi chảy) cần thời gian.\n"
                        f"Thầy cất câu này vào *Danh sách phục thù* để ôn lại sau nhé! 💪"
                    )
                    
                    if session["round"] > session["max_rounds"]:
                        new_streak = update_user_progress(user_id, status="completed")
                        increment_total_sessions(user_id)
                        _write_session_analytics(user_id, session)
                        stats = session["session_stats"]
                        await message.channel.send(
                            f"🏆 **Hoàn thành!** 🔥 Chuỗi: `{new_streak} ngày`\n"
                            f"📊 Pass: {stats['passed_first_try']} | Drill: {stats['needed_drill']} | Skip: {stats['skipped']}\n"
                            f"💡 Gõ `!more` để thêm hiệp bonus!"
                        )
                        session["mode"] = "completed"
                    else:
                        await _advance_to_next_round(message.channel, user_id, session)

                elif session["fail_count"] >= 3:
                    update_sentence_progress(user_id, session["sentence"], success=False)
                    if session["new_word"]:
                        save_failed_word(user_id, session["new_word"])
                    
                    session.setdefault("round_history", []).append({
                        "type": "sentence", "passed": False, "score": score,
                    })
                    session["round"] += 1
                    session["fail_count"] = 0
                    session["drill_done"] = False
                    
                    await message.channel.send(
                        f"🤝 **Giáo viên AI can thiệp:** Câu này có vẻ đang làm khó cơ miệng của bạn. "
                        f"Thầy đã âm thầm cất từ này vào *'Danh sách phục thù'* để ngày mai chúng ta xử lý lại khi đầu óc thoải mái hơn. "
                        f"Bây giờ hãy bỏ qua nó để bảo toàn năng lượng nhé!\n"
                    )
                    
                    if session["round"] > session["max_rounds"]:
                        new_streak = update_user_progress(user_id, status="completed")
                        increment_total_sessions(user_id)
                        _write_session_analytics(user_id, session)
                        stats = session["session_stats"]
                        await message.channel.send(
                            f"🏆 **Hoàn thành!** 🔥 Chuỗi: `{new_streak} ngày`\n"
                            f"📊 Pass: {stats['passed_first_try']} | Drill: {stats['needed_drill']} | Skip: {stats['skipped']}\n"
                            f"💡 Gõ `!more` để thêm hiệp bonus!"
                        )
                        session["mode"] = "completed"
                    else:
                        await _advance_to_next_round(message.channel, user_id, session)

                elif session["fail_count"] == 2 and problem_words and not session["drill_done"]:
                    # 🟡 SAI LẦN 2 VÀ CÓ TỪ KHÓ -> KÍCH HOẠT WORD DRILL MODE
                    session["mode"] = "word_drill"
                    session["drill_words"] = problem_words
                    session["drill_index"] = 0
                    session["drill_fails"] = 0
                    session["drill_passed"] = 0
                    session["session_stats"]["needed_drill"] += 1
                    
                    first_word = problem_words[0]
                    await message.channel.send(
                        f"💡 **Thầy có mẹo chống nản cho bạn!**\n"
                        f"Thay vì đọc lại cả câu, hãy luyện từng từ khó một rồi ghép lại. "
                        f"Chỉ có **{len(problem_words)} từ** cần chinh phục thôi!\n\n"
                        f"🎯 Bắt đầu với từ: **{first_word.upper()}** — Nghe mẫu rồi đọc lại nhé 👇"
                    )
                    sample_path = f"drill_sample_{user_id}.mp3"
                    if await generate_sample_audio(first_word, sample_path):
                        await message.channel.send(file=discord.File(sample_path))
                        os.remove(sample_path)

                else:
                    # SAI LẦN ĐẦU -> Phát audio mẫu để user nghe so sánh, rồi thử lại
                    await message.reply(
                        f"❌ Chưa đạt (cần ≥80). Nghe mẫu bên dưới rồi thử lại nhé! "
                        f"(Lần {session['fail_count']}/3, gõ `!skip` nếu muốn bỏ qua)"
                    )
                    sample_path = f"sentence_sample_{user_id}.mp3"
                    if await generate_sample_audio(session["sentence"], sample_path):
                        await message.channel.send(file=discord.File(sample_path))
                        os.remove(sample_path)

client.run(DISCORD_BOT_TOKEN)
