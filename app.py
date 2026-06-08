import discord
import os
import requests
import asyncio
import functools

from dotenv import load_dotenv
# Import chuẩn xác các hàm xử lý từ 2 file vệ tinh đã viết
from database import (get_or_create_user, get_next_sentence, update_user_progress,
                      save_failed_word, update_sentence_progress, clear_failed_word,
                      log_score, log_error_pattern, get_user_stats, adjust_user_level,
                      increment_total_sessions,
                      record_word_attempts_batch, get_weak_words,
                      record_phoneme_errors_batch, get_weak_phonemes,
                      record_pattern_attempts_batch, get_weak_patterns,
                      pick_shadowing_item, record_shadowing_attempt)
from ai_brain import (analyze_audio_with_whisper, analyze_single_word, send_new_word_tutorial,
                      generate_sample_audio, ERROR_TYPE_LABELS)
from analysis.patterns import extract_patterns
from analysis.learning_memory import (get_learner_profile, get_learning_insights,
                                      get_practice_recommendations)
from analysis.drills import generate_daily_practice

load_dotenv()

DISCORD_BOT_TOKEN=os.getenv("DISCORD_BOT_TOKEN")

# 1. Cấu hình quyền hạn (Intents) bắt buộc cho Bot Discord
intents = discord.Intents.default()
intents.message_content = True  # Bật tính năng đọc nội dung tin nhắn text
client = discord.Client(intents=intents)

# 2. Bộ nhớ đệm lưu trạng thái học trong ngày của các User
# Cấu trúc: { user_id: { "round": 1, "sentence": "...", "new_word": "...", "fail_count": 0 } }
user_sessions = {}

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
    # LỆNH VÀO HỌC: !daily
    # ========================================================
    if message.content.strip() == "!daily":
        if user_id in user_sessions:
            if user_sessions[user_id]["mode"] == "completed":
                await message.reply("✅ Đã hoàn thành phiên hôm nay! Gõ `!more` để thêm hiệp, hoặc chờ tới mai.")
            else:
                await message.reply("🔄 Bạn đang ở trong hiệp đấu rồi! Hãy nộp bài ghi âm cho câu hiện tại nhé.")
            return

        await message.channel.send("🔄 Đang truy cập học bạ điện tử của bạn trên SQLite...")
        
        # Kiểm tra/Tạo user mới và check xem có bị đứt chuỗi Streak không
        user_data = get_or_create_user(user_id, user_name)
        streak = user_data["streak"]
        user_level = user_data.get("current_level", 1)
        
        # Bốc câu hỏi thông minh theo thuật toán Spaced Repetition (Ưu tiên từ sai -> Từ cũ -> Từ mới)
        next_task = get_next_sentence(user_id)
        
        # Khởi tạo phiên học ngày hôm nay cho user
        user_sessions[user_id] = {
            "round": 1,
            "max_rounds": 3,
            "sentence": next_task["sentence"],
            "new_word": next_task["new_word"],
            "fail_count": 0,
            "mode": "sentence",
            "drill_words": [],
            "drill_index": 0,
            "drill_fails": 0,
            "drill_passed": 0,
            "drill_done": False,  # True sau khi đã drill xong 1 lần — không drill lại cùng câu
            "used_sentences": [next_task["sentence"]],  # Track câu đã bốc trong phiên
            "session_stats": {"passed_first_try": 0, "needed_drill": 0, "skipped": 0}  # Thống kê cuối phiên
        }
        
        await message.channel.send(f"🔥 **Chuỗi ngày học liên tục:** `{streak} ngày`. Giữ vững ngọn lửa nhé!")
        
        # Nếu câu có chứa từ mới hoặc từ sai nặng -> Drill từ khóa trước khi đọc cả câu
        if next_task["new_word"]:
            await start_keyword_drill(message.channel, user_sessions[user_id], next_task["sentence"], next_task["new_word"])
        else:
            await message.reply(
                f"🎯 **HIỆP 1/3 - Nhấn giữ micro và đọc to câu sau:**\n"
                f"👉 **`{next_task['sentence']}`**"
            )
        return

    # ========================================================
    # LỆNH TRỢ GIÚP: !help
    # ========================================================
    if message.content.strip() == "!help":
        await message.reply(
            "📖 **HƯỚNG DẪN SỬ DỤNG BOT LUYỆN PHÁT ÂM**\n\n"
            "🎯 `!daily` — Bắt đầu phiên học hôm nay (3 hiệp)\n"
            "➕ `!more` — Thêm hiệp bonus sau khi hoàn thành (tối đa 6)\n"
            "⏭️ `!skip` — Bỏ qua câu hiện tại, sang câu mới\n"
            "🛑 `!stop` — Thoát phiên học giữa chừng\n"
            "📊 `!stats` — Xem thống kê tiến trình và điểm yếu\n"
            "📋 `!profile` — Hồ sơ học tập + điểm yếu + gợi ý\n"
            "🎧 `!shadow` — Luyện shadowing (nghe + đọc theo)\n"
            "📝 `!drills` — Bài tập hôm nay (tự sinh từ điểm yếu)\n"
            "📖 `!help` — Hiển thị hướng dẫn này\n\n"
            "**Cách học:** Gõ `!daily` → Nhấn giữ micro → Đọc to câu hiện ra → Bot chấm điểm.\n"
            "Điểm ≥ 80 để qua hiệp. Nếu kẹt, bot sẽ tách từng từ khó ra luyện riêng. 💪\n"
            "Điểm tốt liên tục → bot tự tăng độ khó. Kẹt nhiều → bot giảm về bài dễ hơn. 🎚️"
        )
        return

    # ========================================================
    # LỆNH BỎ QUA: !skip
    # ========================================================
    if message.content.strip() == "!skip":
        if user_id not in user_sessions:
            await message.reply("⚠️ Bạn chưa bắt đầu phiên học. Gõ `!daily` để vào học nhé!")
            return
        
        session = user_sessions[user_id]
        
        # Đánh dấu câu hiện tại là fail và cất vào sổ đen nếu có từ khóa
        update_sentence_progress(user_id, session["sentence"], success=False)
        if session["new_word"]:
            save_failed_word(user_id, session["new_word"])
        session["session_stats"]["skipped"] += 1
        
        session["round"] += 1
        session["fail_count"] = 0
        session["mode"] = "sentence"
        
        if session["round"] > session["max_rounds"]:
            new_streak = update_user_progress(user_id, status="completed")
            increment_total_sessions(user_id)
            stats = session["session_stats"]
            await message.channel.send(
                f"🏆 **HOÀN THÀNH PHIÊN HỌC!** 🔥 Chuỗi: `{new_streak} ngày`\n"
                f"📊 Pass ngay: {stats['passed_first_try']} | Cần drill: {stats['needed_drill']} | Bỏ qua: {stats['skipped']}\n"
                f"💡 Gõ `!more` để thêm hiệp bonus, hoặc nghỉ ngơi tới mai!"
            )
            session["mode"] = "completed"
        else:
            next_task = get_next_sentence(user_id, exclude_sentences=session["used_sentences"])
            session["sentence"] = next_task["sentence"]
            session["new_word"] = next_task["new_word"]
            session["used_sentences"].append(next_task["sentence"])
            session["drill_done"] = False
            if next_task["new_word"]:
                await start_keyword_drill(message.channel, session, next_task["sentence"], next_task["new_word"])
            else:
                await message.channel.send(f"👉 **`{session['sentence']}`**")
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
            streak_msg = f"🔥 Chuỗi: `{new_streak} ngày` (vẫn được tính vì đã hoàn thành {completed_rounds} hiệp)"
        else:
            streak_msg = "⚠️ Chưa hoàn thành hiệp nào nên không tính streak."
        
        del user_sessions[user_id]
        await message.reply(f"🛑 **Đã thoát phiên học.**\n{streak_msg}\nGõ `!daily` khi muốn quay lại nhé!")
        return

    # ========================================================
    # LỆNH THÊM HIỆP: !more
    # ========================================================
    if message.content.strip() == "!more":
        if user_id not in user_sessions or user_sessions[user_id]["mode"] != "completed":
            await message.reply("⚠️ Bạn cần hoàn thành phiên học trước (gõ `!daily` để bắt đầu).")
            return
        session = user_sessions[user_id]
        if session["max_rounds"] >= 6:
            await message.reply("🛑 Đã đạt tối đa **6 hiệp** cho 1 phiên. Nghỉ ngơi rồi quay lại vào ngày mai nhé! 💤")
            del user_sessions[user_id]
            return
        session["max_rounds"] += 1
        next_task = get_next_sentence(user_id, exclude_sentences=session["used_sentences"])
        session["sentence"] = next_task["sentence"]
        session["new_word"] = next_task["new_word"]
        session["used_sentences"].append(next_task["sentence"])
        session["fail_count"] = 0
        session["mode"] = "sentence"
        session["drill_done"] = False
        await message.channel.send(
            f"💪 **HIỆP BONUS {session['round']}/{session['max_rounds']}!** Tinh thần chiến đấu cao!\n"
        )
        if next_task["new_word"]:
            await start_keyword_drill(message.channel, session, next_task["sentence"], next_task["new_word"])
        else:
            await message.channel.send(f"👉 **`{session['sentence']}`**")
        return

    # ========================================================
    # LỆNH XEM THỐNG KÊ: !stats
    # ========================================================
    if message.content.strip() == "!stats":
        stats = get_user_stats(user_id)
        if not stats:
            await message.reply("📊 Chưa có dữ liệu. Gõ `!daily` để bắt đầu luyện nhé!")
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
        item = pick_shadowing_item(user_id)
        if not item:
            await message.reply("📭 Chưa có câu shadowing nào trong hệ thống. Liên hệ admin để thêm nhé!")
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
        }

        await message.channel.send(
            f"🎧 **SHADOWING MODE**\n\n"
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
            await message.reply("📋 Chưa có đủ dữ liệu để tạo bài tập. Luyện thêm vài phiên `!daily` rồi quay lại!")
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

        msg += "💡 Gõ `!shadow` để luyện shadowing, hoặc `!daily` để vào phiên chấm điểm!"
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

                result_msg = (
                    f"🎧 **KẾT QUẢ SHADOWING** — **{score}/100** điểm\n"
                    f"```ansi\n{ansi_feedback}\n```"
                )
                if error_details and score < 100:
                    result_msg += f"\n{error_details}"

                if score >= 80:
                    result_msg += "\n\n✅ Tốt lắm! Gõ `!shadow` để thử câu khác, hoặc `!daily` để vào phiên chính."
                else:
                    result_msg += "\n\n🔄 Chưa đạt 80 — nghe lại mẫu rồi thử lần nữa! Hoặc gõ `!shadow` để đổi câu."

                await message.reply(result_msg)

                if score >= 80:
                    del user_sessions[user_id]
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
                        # Quá nhiều từ bị kẹt → không ép đọc lại câu, đổi sang câu khác
                        update_sentence_progress(user_id, session["sentence"], success=False)
                        if session["new_word"]:
                            save_failed_word(user_id, session["new_word"])

                        session["round"] += 1
                        session["fail_count"] = 0

                        await message.channel.send(
                            f"🤝 Bạn chỉ luyện được **{passed_count}/{total_drilled} từ** — câu này còn hơi sớm với cơ miệng hiện tại. "
                            f"Thầy đã cất vào *Danh sách phục thù*, ngày mai quay lại chinh phục nhé!\n"
                        )

                        if session["round"] > session["max_rounds"]:
                            new_streak = update_user_progress(user_id, status="completed")
                            increment_total_sessions(user_id)
                            stats = session["session_stats"]
                            await message.channel.send(
                                f"🏆 **Hoàn thành!** 🔥 Chuỗi: `{new_streak} ngày`\n"
                                f"📊 Pass: {stats['passed_first_try']} | Drill: {stats['needed_drill']} | Skip: {stats['skipped']}\n"
                                f"💡 Gõ `!more` để thêm hiệp bonus!"
                            )
                            session["mode"] = "completed"
                        else:
                            next_task = get_next_sentence(user_id, exclude_sentences=session["used_sentences"])
                            session["sentence"] = next_task["sentence"]
                            session["new_word"] = next_task["new_word"]
                            session["used_sentences"].append(next_task["sentence"])
                            await message.channel.send(f"⏭️ Sang **HIỆP {session['round']}/{session['max_rounds']}** với câu mới:")
                            if next_task["new_word"]:
                                await start_keyword_drill(message.channel, session, next_task["sentence"], next_task["new_word"])
                            else:
                                await message.channel.send(f"👉 **`{session['sentence']}`**")
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
                
                if session["round"] > session["max_rounds"]:
                    # HOÀN THÀNH ĐỦ HIỆP CỦA NGÀY — hiển thị tổng kết phiên
                    new_streak = update_user_progress(user_id, status="completed")
                    increment_total_sessions(user_id)
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
                    # BƯỚC SANG HIỆP TIẾP THEO
                    next_task = get_next_sentence(user_id, exclude_sentences=session["used_sentences"])
                    session["sentence"] = next_task["sentence"]
                    session["new_word"] = next_task["new_word"]
                    session["used_sentences"].append(next_task["sentence"])
                    
                    if next_task["new_word"]:
                        await start_keyword_drill(message.channel, session, next_task["sentence"], next_task["new_word"])
                    else:
                        await message.channel.send(
                            f"💪 Làm tốt lắm! Tiếp tục sang **HIỆP {session['round']}/{session['max_rounds']}**:\n"
                            f"👉 **`{session['sentence']}`**"
                        )
            else:
                # PHÁT ÂM CHƯA ĐẠT CHUẨN (<80 điểm)
                session["fail_count"] += 1
                
                # Nếu đã drill xong mà vẫn fail cả câu → auto-advance, không lặp vô tận
                if session["drill_done"]:
                    update_sentence_progress(user_id, session["sentence"], success=False)
                    if session["new_word"]:
                        save_failed_word(user_id, session["new_word"])
                    
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
                        stats = session["session_stats"]
                        await message.channel.send(
                            f"🏆 **Hoàn thành!** 🔥 Chuỗi: `{new_streak} ngày`\n"
                            f"📊 Pass: {stats['passed_first_try']} | Drill: {stats['needed_drill']} | Skip: {stats['skipped']}\n"
                            f"💡 Gõ `!more` để thêm hiệp bonus!"
                        )
                        session["mode"] = "completed"
                    else:
                        next_task = get_next_sentence(user_id, exclude_sentences=session["used_sentences"])
                        session["sentence"] = next_task["sentence"]
                        session["new_word"] = next_task["new_word"]
                        session["used_sentences"].append(next_task["sentence"])
                        await message.channel.send(f"⏭️ Sang **HIỆP {session['round']}/{session['max_rounds']}** với câu mới:")
                        if next_task["new_word"]:
                            await start_keyword_drill(message.channel, session, next_task["sentence"], next_task["new_word"])
                        else:
                            await message.channel.send(f"👉 **`{session['sentence']}`**")

                elif session["fail_count"] >= 3:
                    # 🟥 THẤT BẠI QUÁ 3 LẦN (chưa từng drill) -> ĐỔI CÂU
                    update_sentence_progress(user_id, session["sentence"], success=False)
                    if session["new_word"]:
                        save_failed_word(user_id, session["new_word"])
                    
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
                        stats = session["session_stats"]
                        await message.channel.send(
                            f"🏆 **Hoàn thành!** 🔥 Chuỗi: `{new_streak} ngày`\n"
                            f"📊 Pass: {stats['passed_first_try']} | Drill: {stats['needed_drill']} | Skip: {stats['skipped']}\n"
                            f"💡 Gõ `!more` để thêm hiệp bonus!"
                        )
                        session["mode"] = "completed"
                    else:
                        next_task = get_next_sentence(user_id, exclude_sentences=session["used_sentences"])
                        session["sentence"] = next_task["sentence"]
                        session["new_word"] = next_task["new_word"]
                        session["used_sentences"].append(next_task["sentence"])
                        await message.channel.send(f"⏭️ Hãy bước sang **HIỆP {session['round']}/{session['max_rounds']}** với một thử thách mới tươi mới hơn:")
                        if next_task["new_word"]:
                            await start_keyword_drill(message.channel, session, next_task["sentence"], next_task["new_word"])
                        else:
                            await message.channel.send(f"👉 **`{session['sentence']}`**")

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
