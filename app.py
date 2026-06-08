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
                      increment_total_sessions)
from ai_brain import (analyze_audio_with_whisper, analyze_single_word, send_new_word_tutorial,
                      generate_sample_audio, ERROR_TYPE_LABELS)

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
        
        # Nếu câu có chứa từ mới hoặc từ sai nặng -> Kích hoạt chế độ giảng bài trước khi bắt đọc
        if next_task["new_word"]:
            await send_new_word_tutorial(message.channel, next_task["sentence"], next_task["new_word"])
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
                await send_new_word_tutorial(message.channel, next_task["sentence"], next_task["new_word"])
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
            await send_new_word_tutorial(message.channel, next_task["sentence"], next_task["new_word"])
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
        
        await message.reply(msg)
        return

    # ========================================================
    # XỬ LÝ KHI USER GỬI FILE VOICE (TIN NHẮN THOẠI TỪ IPHONE)
    # ========================================================
    # Điều kiện: Người dùng đang trong phiên học và tin nhắn có đính kèm file (Attachment)
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
                                await send_new_word_tutorial(message.channel, next_task["sentence"], next_task["new_word"])
                            else:
                                await message.channel.send(f"👉 **`{session['sentence']}`**")
                return

            # ====================================================
            # NHÁNH 2: SENTENCE MODE - Chấm cả câu (logic gốc)
            # ====================================================
            score, ansi_feedback, error_details, problem_words, error_types = await asyncio.get_event_loop().run_in_executor(
                None, functools.partial(analyze_audio_with_whisper, temp_audio_path, session["sentence"])
            )
            
            # Xóa file tạm ngay lập tức sau khi xử lý xong để nhẹ máy local
            if os.path.exists(temp_audio_path):
                os.remove(temp_audio_path)
            
            # Log điểm + lỗi vào database để track pattern dài hạn
            log_score(user_id, session["sentence"], score)
            for word, err_type in error_types:
                log_error_pattern(user_id, err_type, word)
                
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
                        await send_new_word_tutorial(message.channel, next_task["sentence"], next_task["new_word"])
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
                            await send_new_word_tutorial(message.channel, next_task["sentence"], next_task["new_word"])
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
                            await send_new_word_tutorial(message.channel, next_task["sentence"], next_task["new_word"])
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
