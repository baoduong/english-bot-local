import discord
import os
import re
import requests
import asyncio
import functools
from datetime import datetime

from dotenv import load_dotenv
# Import chuẩn xác các hàm xử lý từ 2 file vệ tinh đã viết
from database import (get_next_sentence, update_user_progress,
                      save_failed_word, update_sentence_progress, clear_failed_word,
                      log_score, log_error_pattern, get_user_stats, adjust_user_level,
                      increment_total_sessions,
                      record_word_attempts_batch,
                      record_phoneme_errors_batch, get_weak_phonemes,
                      record_pattern_attempts_batch, get_weak_patterns)
from ai_brain import (analyze_audio_with_whisper, analyze_single_word, send_new_word_tutorial,
                      generate_sample_audio, ERROR_TYPE_LABELS)
from analysis.patterns import extract_patterns
from analysis.learning_memory import (get_learner_profile, get_learning_insights,
                                      get_practice_recommendations)
from analysis.metrics import get_learning_progress
from engines.ollama_client import OllamaClient, OllamaUnavailableError, OllamaSchemaError
from engines.curriculum_generator import CurriculumGenerator
from engines.onboarding_chat import OnboardingChat
from engines.prompts import (
    teacher_coaching_prompt,
    teacher_borderline_pass_prompt,
    pre_sentence_coaching_prompt,
    post_session_summary_prompt,
    word_pronunciation_prompt,
    weekly_progress_report_prompt,
)
from analysis.phase_engine import PhaseEngine
from analysis.curriculum_types import (
    validate_teacher_coaching,
    validate_teacher_borderline_pass,
    validate_pre_sentence_coaching,
    validate_post_session_summary,
    validate_word_pronunciation,
    validate_weekly_report,
)
from db.curriculum import (
    get_active_curriculum, get_active_phase, get_next_practice_sentence,
    get_phases_for_curriculum, get_phase_progress, record_phase_content_attempt,
    archive_curriculum
)
from db.connection import get_db_connection
from db.sessions import save_session, load_all_sessions, delete_session
from db.users import get_or_create_user, needs_onboarding, clear_active_curriculum

load_dotenv()

DISCORD_BOT_TOKEN=os.getenv("DISCORD_BOT_TOKEN")

# 1. Cấu hình quyền hạn (Intents) bắt buộc cho Bot Discord
intents = discord.Intents.default()
intents.message_content = True  # Bật tính năng đọc nội dung tin nhắn text
client = discord.Client(intents=intents)

# 2. Bộ nhớ đệm lưu trạng thái học trong ngày của các User
# Cấu trúc: { user_id: { "round": 1, "sentence": "...", "new_word": "...", "fail_count": 0 } }
user_sessions = {}

_ollama_client = OllamaClient()
_curriculum_generator = CurriculumGenerator(_ollama_client)
_onboarding_chat = OnboardingChat(_ollama_client)
_phase_engine = PhaseEngine(_ollama_client, _curriculum_generator)

OLLAMA_DOWN_MESSAGE = (
    "⚠️ AI assistant đang không khả dụng.\n"
    "Hãy đảm bảo Ollama đang chạy: `ollama serve`\n"
    "Sau đó thử lại."
)


def _persist_session(user_id):
    if user_id in user_sessions:
        save_session(user_id, user_sessions[user_id])


def _init_session(user_id, mode, **kwargs):
    """Khởi tạo session với đầy đủ các key cũ và mới."""
    session = {
        "round": 1,
        "max_rounds": 5,
        "sentence": "",
        "new_word": None,
        "fail_count": 0,
        "mode": mode,
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
        "difficulty_pref": 1,
        # Các key mới cho onboarding/curriculum
        "curriculum_id": None,
        "current_phase_id": None,
        "current_phase_number": None,
        "phase_theme": None,
        "phase_total_content": None,
        "phase_mastered_count": None,
        "onboarding_turn": 0,
        "pending_goal_synthesis": None,
    }
    session.update(kwargs)
    user_sessions[user_id] = session
    return session


def _session_in_onboarding(user_id):
    session = user_sessions.get(user_id)
    if not session:
        return False
    return session.get("mode") in ("onboarding", "awaiting_goal_confirmation")


def _session_in_curriculum_practice(user_id):
    session = user_sessions.get(user_id)
    if not session:
        return False
    return session.get("mode") == "curriculum_practice"


def _end_session(user_id):
    session = user_sessions.get(user_id, {})
    session.pop("pending_goal_synthesis", None)
    user_sessions.pop(user_id, None)
    delete_session(user_id)


def _write_session_analytics(user_id, session):
    started_at = session.get("started_at")
    if not started_at:
        return
    scores = session.get("scores", [])
    avg_score = round(sum(scores) / len(scores), 1) if scores else 0
    rounds_completed = session["round"] - 1

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """INSERT INTO session_analytics
           (user_id, started_at, completed_at, rounds_completed, rounds_total, avg_score, content_segments_used)
           VALUES (?, ?, datetime('now'), ?, ?, ?, ?)""",
        (user_id, started_at, rounds_completed, session["max_rounds"], avg_score, 0)
    )
    conn.commit()
    conn.close()


async def _send_session_summary(channel, user_id, session):
    if session.get("mode") != "curriculum_practice":
        return
    scores = session.get("scores", [])
    if not scores:
        return
    stats = (
        f"Sentences attempted: {len(scores)}\n"
        f"Average score: {round(sum(scores)/len(scores), 1)}\n"
        f"Highest: {max(scores)}\n"
        f"Lowest: {min(scores)}\n"
        f"Phase: {session.get('phase_theme', 'unknown')}\n"
        f"Mastered: {session.get('phase_mastered_count', 0)}/{session.get('phase_total_content', 0)}"
    )
    try:
        summary = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: _ollama_client.generate_json_sync(
                post_session_summary_prompt(stats, _build_learner_context(user_id)),
                validate_post_session_summary,
            ),
        )
        if summary.get("summary"):
            await channel.send(f"📝 **Tổng kết phiên học:**\n{summary['summary']}")
            if summary.get("practice_tip"):
                await channel.send(f"💡 **Bài tập về nhà:** {summary['practice_tip']}")
    except (OllamaUnavailableError, OllamaSchemaError):
        pass


_ERR_PHONEME = {"th_sound": "θ", "r_l_confusion": "ɹ", "sh_sound": "ʃ", "final_consonant": "C#", "vowel_stress": "V"}


def _build_learner_context(user_id):
    profile = get_learner_profile(user_id)
    progress = get_learning_progress(user_id)

    parts = []
    if profile["hard_words"]:
        weak = ", ".join(f"{w['word']}({w['success_rate']}%)" for w in profile["hard_words"][:5])
        parts.append(f"- Từ yếu: {weak}")
    if profile["hard_phonemes"]:
        ph = ", ".join(f"/{p['phoneme']}/" for p in profile["hard_phonemes"][:3])
        parts.append(f"- Âm yếu: {ph}")
    if profile["mastered_words"]:
        parts.append(f"- Đã thành thạo: {len(profile['mastered_words'])} từ")
    if progress.get("pronunciation_trend"):
        parts.append(f"- Xu hướng phát âm: {progress['pronunciation_trend']}")
    if progress.get("avg_score"):
        parts.append(f"- Điểm trung bình: {progress['avg_score']}")
    if profile["hard_patterns"]:
        pat = ", ".join(f"\"{p['pattern']}\"" for p in profile["hard_patterns"][:3])
        parts.append(f"- Cấu trúc cần luyện: {pat}")

    return "\n".join(parts) if parts else ""


def _record_practice_stats(user_id, text, word_scores, error_types, score):
    """Record word/phoneme/pattern stats for ANY practice mode.
    
    This ensures learner profile updates regardless of which mode was used.
    """
    if word_scores:
        record_word_attempts_batch(user_id, word_scores)

    phoneme_errs = []
    for word, err_type in error_types:
        ph = _ERR_PHONEME.get(err_type)
        if ph:
            phoneme_errs.append((ph, word))
    if phoneme_errs:
        record_phoneme_errors_batch(user_id, phoneme_errs)

    matched_patterns = extract_patterns(text)
    if matched_patterns:
        record_pattern_attempts_batch(user_id, matched_patterns, score)


_SESSION_TTL_SECONDS = 7200
_ONBOARDING_TTL_SECONDS = 86400  # 24 hours for onboarding sessions


def _cleanup_stale_sessions():
    now = datetime.now()
    stale = []
    for uid, sess in user_sessions.items():
        started = sess.get("started_at")
        if not started:
            stale.append(uid)
            continue
        mode = sess.get("mode", "")
        if mode == "curriculum_practice":
            continue
        ttl = _ONBOARDING_TTL_SECONDS if mode in (
            "onboarding", "awaiting_goal_confirmation", "awaiting_goal_change_confirmation"
        ) else _SESSION_TTL_SECONDS
        try:
            elapsed = (now - datetime.fromisoformat(started)).total_seconds()
            if elapsed > ttl:
                stale.append(uid)
        except (ValueError, TypeError):
            stale.append(uid)
    for uid in stale:
        mode = user_sessions.get(uid, {}).get("mode", "")
        if mode in ("onboarding", "awaiting_goal_confirmation"):
            try:
                from db.curriculum import clear_onboarding_conversation
                clear_onboarding_conversation(uid)
            except Exception:
                pass
        user_sessions.pop(uid, None)
        delete_session(uid)


async def _advance_to_next_round(channel, user_id, session):
    """Adaptive: chuyển sang round tiếp theo."""
    round_num = session["round"]
    max_rounds = session["max_rounds"]

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
    _persist_session(user_id)


def _migrate_legacy_sessions():
    """Drops sessions that don't have a recognized mode (old schema)."""
    valid_modes = (
        'sentence', 'keyword_drill', 'word_drill',
        'curriculum_practice', 'onboarding',
        'awaiting_goal_confirmation', 'awaiting_goal_change_confirmation',
        'completed'
    )
    to_remove = []
    for uid, session in user_sessions.items():
        mode = session.get('mode')
        if mode not in valid_modes:
            to_remove.append(uid)
    for uid in to_remove:
        print(f"[migrate] Dropping legacy session for {uid} (unknown mode: {user_sessions[uid].get('mode')})")
        _end_session(uid)


@client.event

async def on_ready():
    global user_sessions
    restored = load_all_sessions()
    if restored:
        user_sessions.update(restored)
        print(f"[restore] Loaded {len(restored)} active session(s) from DB")
    _migrate_legacy_sessions()

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as cnt FROM users")
    total_users = cursor.fetchone()["cnt"]
    cursor.execute("SELECT COUNT(*) as cnt FROM users WHERE onboarding_completed_at IS NULL")
    need_onboarding = cursor.fetchone()["cnt"]
    conn.close()
    print(f"[startup] Found {total_users} users, {need_onboarding} need onboarding")

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
    # XỬ LÝ TEXT REPLIES: onboarding / confirmation flows
    # ========================================================
    _cleanup_stale_sessions()
    if user_id in user_sessions and not message.content.strip().startswith("!"):
        session = user_sessions[user_id]

        if session["mode"] == "onboarding":
            session["onboarding_turn"] += 1
            try:
                result = await _onboarding_chat.submit_user_reply_async(user_id, message.content)
            except (OllamaUnavailableError, OllamaSchemaError):
                await message.channel.send(OLLAMA_DOWN_MESSAGE)
                return
            except Exception as exc:
                await message.channel.send(f"❌ Lỗi: {exc}")
                _end_session(user_id)
                return

            if result["type"] == "question":
                await message.channel.send(result["text"])
                _persist_session(user_id)
                return
            elif result["type"] == "synthesis":
                session["pending_goal_synthesis"] = result["goal"]
                session["mode"] = "awaiting_goal_confirmation"
                goal = result["goal"]
                await message.channel.send(
                    f"🎯 Mình hiểu goal của bạn là:\n"
                    f"**{goal['goal_title']}**\n\n"
                    f"{goal.get('goal_description', '')}\n\n"
                    f"Đúng vậy không? Trả lời \"yes\" để bắt đầu, hoặc \"no\" để onboarding lại."
                )
                _persist_session(user_id)
                return

        elif session["mode"] == "awaiting_goal_confirmation":
            text_lower = message.content.strip().lower()
            if text_lower in ("yes", "y", "ok", "có", "đúng"):
                goal = session["pending_goal_synthesis"]
                try:
                    curriculum_id = await _onboarding_chat.confirm_and_create_curriculum_async(
                        user_id, goal, interface_language='vi'
                    )
                except Exception as exc:
                    await message.channel.send(f"❌ Lỗi tạo curriculum: {exc}")
                    _end_session(user_id)
                    return

                await message.channel.send("✅ Đã lưu goal. Đang tạo Tuần 1, đợi xíu nha...")
                try:
                    await _curriculum_generator.generate_full_phase_async(
                        curriculum_id, goal["goal_title"], goal.get("goal_description", ""), 1, []
                    )
                except (OllamaUnavailableError, OllamaSchemaError):
                    await message.channel.send(OLLAMA_DOWN_MESSAGE)
                    _end_session(user_id)
                    return

                await message.channel.send("🎉 Tuần 1 sẵn sàng! Gõ `!go` để bắt đầu luyện tập.")
                _end_session(user_id)
                return
            elif text_lower in ("no", "n", "không"):
                from db.curriculum import clear_onboarding_conversation
                clear_onboarding_conversation(user_id)
                _end_session(user_id)
                await message.channel.send("Ok, gõ `!go` để onboarding lại từ đầu.")
                return
            else:
                await message.channel.send("Trả lời `yes` để bắt đầu hoặc `no` để làm lại.")
                return

        elif session["mode"] == "awaiting_goal_change_confirmation":
            text_lower = message.content.strip().lower()
            if text_lower in ("yes", "y", "ok", "có", "đúng"):
                cur = get_active_curriculum(user_id)
                if cur:
                    archive_curriculum(cur["id"])
                clear_active_curriculum(user_id)
                _end_session(user_id)
                await message.channel.send("✅ Đã archive curriculum cũ. Gõ `!go` để bắt đầu onboarding mới.")
                return
            else:
                _end_session(user_id)
                await message.channel.send("Hủy thay đổi goal.")
                return

    # ========================================================
    # LỆNH VÀO HỌC: !go (adaptive session) — !daily là alias
    # ========================================================
    if message.content.strip() in ("!go", "!daily"):
        _cleanup_stale_sessions()
        if user_id in user_sessions:
            session = user_sessions[user_id]
            mode = session.get("mode")

            if mode == "curriculum_practice" and session.get("sentence"):
                progress = get_phase_progress(session["current_phase_id"])
                session["phase_mastered_count"] = progress["mastered"]
                session["phase_total_content"] = progress["total"]
                header = f"📍 Tuần {session['current_phase_number']} · {session['phase_theme']} · {progress['mastered']}/{progress['total']}"
                await message.channel.send(
                    f"📚 Bạn đang luyện tập dở — tiếp tục nào!\n\n"
                    f"{header}\n\n"
                    f"🎯 **Đọc câu sau:**\n"
                    f"👉 **`{session['sentence']}`**\n\n"
                    f"🔊 *Nghe mẫu bên dưới, rồi ghi âm đọc lại.*\n"
                    f"⏭️ *Gõ `!skip` để bỏ qua, `!stop` để thoát.*"
                )
                sample_path = f"curriculum_sample_{user_id}.mp3"
                if await generate_sample_audio(session["sentence"], sample_path):
                    await message.channel.send(file=discord.File(sample_path))
                    try:
                        os.remove(sample_path)
                    except Exception:
                        pass
                return

            if mode == "onboarding":
                await message.reply("💬 Bạn đang trong quá trình onboarding. Hãy trả lời câu hỏi của AI để tiếp tục.")
                return

            if mode == "awaiting_goal_confirmation":
                await message.reply("⏳ Bạn đang chờ xác nhận goal. Trả lời `yes` hoặc `no`.")
                return

            await message.reply("🔄 Bạn đang trong phiên học. Gõ `!stop` để thoát trước khi bắt đầu mới.")
            return

        user_data = get_or_create_user(user_id, user_name)

        if needs_onboarding(user_id):
            _init_session(user_id, "onboarding", onboarding_turn=0)
            try:
                greeting = await _onboarding_chat.start_conversation_async(user_id)
            except (OllamaUnavailableError, OllamaSchemaError):
                _end_session(user_id)
                await message.channel.send(OLLAMA_DOWN_MESSAGE)
                return

            await message.channel.send(greeting)
            _persist_session(user_id)
            return

        curriculum = get_active_curriculum(user_id)
        if not curriculum:
            clear_active_curriculum(user_id)
            await message.channel.send("📚 Curriculum không tìm thấy. Gõ `!go` lần nữa để bắt đầu onboarding.")
            return

        phase = get_active_phase(curriculum["id"])
        if not phase:
            try:
                await message.channel.send(f"📚 Đang tạo Tuần {curriculum['current_phase_number']}...")
                previous_phases = get_phases_for_curriculum(curriculum["id"])
                await _curriculum_generator.generate_full_phase_async(
                    curriculum["id"],
                    curriculum["goal_title"],
                    curriculum["goal_description"],
                    curriculum["current_phase_number"],
                    previous_phases,
                )
            except (OllamaUnavailableError, OllamaSchemaError):
                await message.channel.send(OLLAMA_DOWN_MESSAGE)
                return

            phase = get_active_phase(curriculum["id"])

        if not phase:
            await message.channel.send("⚠️ Không thể khởi tạo phase luyện tập. Gõ `!go` để thử lại.")
            return

        content = get_next_practice_sentence(phase["id"])
        if not content:
            if _phase_engine.should_check_progression(phase["id"]):
                try:
                    decision = await _phase_engine.evaluate_phase_async(phase["id"])
                    result = await _phase_engine.apply_decision_async(phase["id"], decision)
                except (OllamaUnavailableError, OllamaSchemaError):
                    await message.channel.send(OLLAMA_DOWN_MESSAGE)
                    return

                if result["next_action"] == "generate_next_phase":
                    await message.channel.send(
                        f"🎉 Hoàn thành Tuần {phase['phase_number']}! Đang chuẩn bị Tuần tiếp theo..."
                    )
                    next_phase_number = result.get("next_phase_number", curriculum["current_phase_number"])
                    try:
                        previous_phases = get_phases_for_curriculum(curriculum["id"])
                        await _curriculum_generator.generate_full_phase_async(
                            curriculum["id"],
                            curriculum["goal_title"],
                            curriculum["goal_description"],
                            next_phase_number,
                            previous_phases,
                        )
                    except (OllamaUnavailableError, OllamaSchemaError):
                        await message.channel.send(OLLAMA_DOWN_MESSAGE)
                        return
                    phase = get_active_phase(curriculum["id"])
                elif result["next_action"] == "phase_regenerated":
                    await message.channel.send("🔄 Phase được tạo lại.")
                    phase = get_active_phase(curriculum["id"])
                elif result["next_action"] == "continue":
                    await message.channel.send("Tiếp tục luyện tập...")

            if phase:
                content = get_next_practice_sentence(phase["id"])

        if not content:
            await message.channel.send("📚 Chưa có nội dung luyện tập khả dụng. Gõ `!go` lại sau nhé.")
            return

        progress = get_phase_progress(phase["id"])
        _init_session(
            user_id,
            "curriculum_practice",
            curriculum_id=curriculum["id"],
            current_phase_id=phase["id"],
            current_phase_number=phase["phase_number"],
            phase_theme=phase["theme"],
            phase_total_content=progress["total"],
            phase_mastered_count=progress["mastered"],
            sentence=content["sentence"],
            content_id=content["id"],
        )

        header = f"📍 Tuần {phase['phase_number']} · {phase['theme']} · {progress['mastered']}/{progress['total']}"
        await message.channel.send(
            f"{header}\n\n"
            f"🎯 **Đọc câu sau:**\n"
            f"👉 **`{content['sentence']}`**\n\n"
            f"🔊 *Nghe mẫu bên dưới, rồi ghi âm đọc lại và gửi file audio vào đây.*\n"
            f"⏭️ *Gõ `!skip` để bỏ qua, `!stop` để thoát.*"
        )
        sample_path = f"curriculum_sample_{user_id}.mp3"
        if await generate_sample_audio(content["sentence"], sample_path):
            await message.channel.send(file=discord.File(sample_path))
            try:
                os.remove(sample_path)
            except Exception:
                pass
        try:
            coaching_data = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: _ollama_client.generate_json_sync(
                    pre_sentence_coaching_prompt(content["sentence"], _build_learner_context(user_id)),
                    validate_pre_sentence_coaching,
                ),
            )
            if coaching_data.get("tip"):
                await message.channel.send(f"🎓 **Gợi ý trước khi đọc:** {coaching_data['tip']}")
        except (OllamaUnavailableError, OllamaSchemaError):
            pass
        _persist_session(user_id)

        weak_phonemes = get_weak_phonemes(user_id, limit=1)
        if weak_phonemes:
            from analysis.minimal_pairs import get_minimal_pairs_for_phoneme, get_phoneme_display_name

            top_phoneme = weak_phonemes[0]["phoneme"]
            pairs = get_minimal_pairs_for_phoneme(top_phoneme, count=3)
            if pairs:
                phoneme_name = get_phoneme_display_name(top_phoneme)
                pairs_text = "\n".join(f"  🔸 **{a}** vs **{b}**" for a, b in pairs)
                await message.channel.send(
                    f"💡 **Khởi động nhanh — Luyện âm {phoneme_name}:**\n"
                    f"{pairs_text}\n\n"
                    f"🔊 *Nghe sự khác biệt giữa 2 từ bên dưới:*"
                )
                pair_a, pair_b = pairs[0]
                pair_audio_text = f"{pair_a}. . . {pair_b}. . . {pair_a}. . . {pair_b}"
                sample_path = f"minimal_pair_{user_id}.mp3"
                if await generate_sample_audio(pair_audio_text, sample_path):
                    await message.channel.send(file=discord.File(sample_path))
                    try:
                        os.remove(sample_path)
                    except Exception:
                        pass
        return

    # ========================================================
    # LỆNH TRỢ GIÚP: !help
    # ========================================================
    if message.content.strip() == "!help":
        await message.reply(
            "📖 **HƯỚNG DẪN SỬ DỤNG**\n\n"
            "🎯 `!go` — Bắt đầu phiên học (bot tự chọn bài phù hợp)\n"
            "⏭️ `!skip` — Bỏ qua bài hiện tại\n"
            "📊 `!me` — Xem hồ sơ + tiến bộ\n\n"
            "**Cách học:** Gõ `!go` → Bot đưa bài → Ghi âm đọc → Bot chấm điểm.\n"
            "Bot tự điều chỉnh: đọc tốt → tăng khó, kẹt nhiều → chuyển bài dễ hơn. 🎚️"
        )
        return

    # ========================================================
    # LỆNH THAY ĐỔI MỤC TIÊU: !goal / !goal change
    # ========================================================
    if message.content.strip().startswith("!goal"):
        parts = message.content.strip().split()
        if len(parts) < 2 or parts[1] != "change":
            await message.reply("Use `!goal change` to start a new learning curriculum.")
            return
        if needs_onboarding(user_id):
            await message.reply("Bạn chưa onboarding. Chạy `!go` để bắt đầu.")
            return
        cur = get_active_curriculum(user_id)
        if not cur:
            await message.reply("Chưa có curriculum. Gõ `!go` để bắt đầu.")
            return
        confirm_msg = (
            f"🎯 Goal hiện tại: \"{cur['goal_title']}\"\n"
            f"📝 Mô tả: {cur['goal_description']}\n"
            f"📚 Bạn đang ở Tuần {cur['current_phase_number']}\n\n"
            f"⚠️ `!goal change` sẽ:\n"
            f"- Archive curriculum hiện tại (giữ lịch sử)\n"
            f"- Bắt đầu onboarding lại từ đầu\n"
            f"- Tạo curriculum mới với goal khác\n\n"
            f"Xác nhận thay đổi? Trả lời \"yes\" trong 60 giây để tiếp tục, hoặc bỏ qua."
        )
        _init_session(user_id, "awaiting_goal_change_confirmation")
        await message.channel.send(confirm_msg)
        _persist_session(user_id)
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

        cur = get_active_curriculum(user_id)
        if cur:
            msg += f"\n📚 **Goal:** {cur['goal_title']}\n"
            msg += f"📝 {cur['goal_description']}\n\n"
            phases = get_phases_for_curriculum(cur['id'])
            if phases:
                msg += "**Phases:**\n"
                for p in phases:
                    if p['status'] == 'completed':
                        msg += f"  ✅ Tuần {p['phase_number']}: {p['theme']} (hoàn thành)\n"
                    elif p['status'] == 'active':
                        prog = get_phase_progress(p['id'])
                        msg += f"  🔄 Tuần {p['phase_number']}: {p['theme']} ({prog['mastered']}/{prog['total']} mastered"
                        if prog['avg_score'] is not None:
                            msg += f", avg {prog['avg_score']}%"
                        msg += ") ← ACTIVE\n"
                    elif p['status'] == 'regenerated':
                        msg += f"  🔄 Tuần {p['phase_number']}: {p['theme']} (regenerated)\n"
                    else:
                        msg += f"  ⏳ Tuần {p['phase_number']}: {p['theme']}\n"
            total_mastered = sum(get_phase_progress(p['id'])['mastered'] for p in phases if p['status'] in ('completed', 'active'))
            msg += f"\nTổng: {total_mastered} câu đã master qua {len(phases)} tuần\n"
        elif needs_onboarding(user_id):
            msg += "\n📚 Chưa có goal. Gõ `!go` để bắt đầu onboarding.\n"
        else:
            msg += "\n📚 Chưa có curriculum đang active. Gõ `!go` để tạo mới.\n"

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

        if session.get("mode") == "curriculum_practice" and session.get("current_phase_id"):
            next_content = get_next_practice_sentence(session["current_phase_id"])
            if next_content and next_content["id"] != session.get("content_id"):
                progress = get_phase_progress(session["current_phase_id"])
                session["sentence"] = next_content["sentence"]
                session["content_id"] = next_content["id"]
                session["fail_count"] = 0
                session["phase_mastered_count"] = progress["mastered"]
                session["phase_total_content"] = progress["total"]
                header = f"📍 Tuần {session['current_phase_number']} · {session['phase_theme']} · {progress['mastered']}/{progress['total']}"
                await message.channel.send(
                    f"⏭️ Bỏ qua!\n\n{header}\n\n"
                    f"🎯 **Đọc câu sau:**\n"
                    f"👉 **`{next_content['sentence']}`**\n\n"
                    f"🔊 *Nghe mẫu bên dưới, rồi ghi âm đọc lại.*"
                )
                sample_path = f"curriculum_sample_{user_id}.mp3"
                if await generate_sample_audio(next_content["sentence"], sample_path):
                    await message.channel.send(file=discord.File(sample_path))
                    try:
                        os.remove(sample_path)
                    except Exception:
                        pass
                _persist_session(user_id)
            else:
                await message.channel.send("📚 Không còn câu nào trong phase này. Gõ `!go` để kiểm tra tiến trình.")
                _end_session(user_id)
            return

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
            _end_session(user_id)
            await message.channel.send(
                f"🏆 **HOÀN THÀNH PHIÊN HỌC!** 🔥 Chuỗi: `{new_streak} ngày`"
            )
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
        if session.get("mode") == "curriculum_practice":
            await _send_session_summary(message.channel, user_id, session)
        _end_session(user_id)
        await message.reply("✅ Đã thoát phiên học. Gõ `!go` khi muốn quay lại luyện tập!")
        return

    # ========================================================
    # XỬ LÝ KHI USER GỬI FILE VOICE (TIN NHẮN THOẠI TỪ IPHONE)
    # ========================================================
    if user_id in user_sessions and message.attachments:
        session = user_sessions[user_id]
        
        attachment = message.attachments[0]
        
        # Nhận diện các định dạng âm thanh phổ biến của Discord di động (.ogg, .wav, .m4a, .mp3)
        if any(attachment.filename.lower().endswith(ext) for ext in ['.ogg', '.wav', '.mp3', '.m4a']):
            await message.channel.send("👂 Thầy AI đang nghe bài và phân tích khẩu hình...")
            
            # Tải file âm thanh từ máy chủ Discord về máy tính local
            temp_audio_path = f"temp_{user_id}_{attachment.filename}"
            try:
                loop = asyncio.get_event_loop()
                audio_data = await loop.run_in_executor(
                    None, lambda: requests.get(attachment.url).content
                )
                with open(temp_audio_path, "wb") as f:
                    f.write(audio_data)
            except Exception as e:
                await message.reply(f"❌ Lỗi tải file ghi âm từ Discord: {e}")
                return

            try:
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
                        total_drilled = len(session["drill_words"])
                        passed_count = session["drill_passed"]
                        pass_rate = passed_count / total_drilled if total_drilled > 0 else 0

                        restore_mode = session.get("curriculum_id") and "curriculum_practice" or "sentence"
                        session["mode"] = restore_mode
                        session["drill_words"] = []
                        session["drill_index"] = 0
                        session["drill_passed"] = 0

                        if pass_rate >= 0.5:
                            session["fail_count"] = 0
                            session["drill_done"] = True
                            await message.channel.send(
                                f"💪 **Đã luyện {passed_count}/{total_drilled} từ!** Thử đọc lại cả câu nào:\n"
                                f"👉 **`{session['sentence']}`**"
                            )
                            sample_path = f"drill_sample_{user_id}.mp3"
                            if await generate_sample_audio(session["sentence"], sample_path):
                                await message.channel.send(file=discord.File(sample_path))
                                try:
                                    os.remove(sample_path)
                                except Exception:
                                    pass
                        else:
                            if restore_mode == "curriculum_practice":
                                next_content = get_next_practice_sentence(session["current_phase_id"])
                                if next_content and next_content["id"] != session.get("content_id"):
                                    session["sentence"] = next_content["sentence"]
                                    session["content_id"] = next_content["id"]
                                    session["fail_count"] = 0
                                    session["drill_done"] = False
                                    progress = get_phase_progress(session["current_phase_id"])
                                    header = f"📍 Tuần {session['current_phase_number']} · {session['phase_theme']} · {progress['mastered']}/{progress['total']}"
                                    await message.channel.send(
                                        f"🤝 Câu này hơi khó — chuyển sang câu khác nhé!\n\n{header}\n\n"
                                        f"🎯 **Đọc câu sau:**\n"
                                        f"👉 **`{next_content['sentence']}`**\n\n"
                                        f"🔊 *Nghe mẫu bên dưới, rồi ghi âm đọc lại.*"
                                    )
                                    sample_path = f"curriculum_sample_{user_id}.mp3"
                                    if await generate_sample_audio(next_content["sentence"], sample_path):
                                        await message.channel.send(file=discord.File(sample_path))
                                        try:
                                            os.remove(sample_path)
                                        except Exception:
                                            pass
                                else:
                                    await message.channel.send("📚 Đã hết câu mới. Gõ `!go` để kiểm tra tiến trình.")
                                    _end_session(user_id)
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
                                    f"🤝 Bạn chỉ luyện được **{passed_count}/{total_drilled} từ** — câu này còn hơi sớm. "
                                    f"Quay lại chinh phục sau nhé!\n"
                                )

                                if session["round"] > session["max_rounds"]:
                                    new_streak = update_user_progress(user_id, status="completed")
                                    increment_total_sessions(user_id)
                                    _write_session_analytics(user_id, session)
                                    _end_session(user_id)
                                    await message.channel.send(
                                        f"🏆 **HOÀN THÀNH PHIÊN HỌC!** 🔥 Chuỗi: `{new_streak} ngày`"
                                    )
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

                _record_practice_stats(user_id, session["sentence"], word_scores, error_types, score)

                if session.get("mode") == "curriculum_practice" and session.get("content_id"):
                    record_phase_content_attempt(session["content_id"], score)
                    progress = get_phase_progress(session["current_phase_id"])
                    session["phase_mastered_count"] = progress["mastered"]
                    session["phase_total_content"] = progress["total"]
                    header = (
                        f"📍 Tuần {session['current_phase_number']} · {session['phase_theme']} · "
                        f"{progress['mastered']}/{progress['total']}"
                    )

                    score_block = (
                        f"{header}\n\n"
                        f"📊 **{score}/100** điểm\n"
                        f"```ansi\n{ansi_feedback}\n```"
                    )

                    if score >= 80:
                        if error_details:
                            score_block += f"\n{error_details}"

                        if problem_words and score < 95:
                            await message.reply(score_block)

                            bp_prompt = teacher_borderline_pass_prompt(
                                session["sentence"], score, problem_words, error_details or "",
                                _build_learner_context(user_id)
                            )
                            try:
                                bp_decision = await asyncio.get_event_loop().run_in_executor(
                                    None, lambda: _ollama_client.generate_json_sync(bp_prompt, validate_teacher_borderline_pass)
                                )
                            except (OllamaUnavailableError, OllamaSchemaError):
                                bp_decision = {"action": "pass_with_note", "message": "Đạt rồi! Tiếp tục nhé.", "weak_words": problem_words}

                            bp_action = bp_decision["action"]
                            bp_message = bp_decision["message"]
                            weak_words = bp_decision.get("weak_words", [])

                            for w in weak_words:
                                save_failed_word(user_id, w)

                            if bp_action == "drill_weak_words" and weak_words and not session.get("drill_done"):
                                session["mode"] = "word_drill"
                                session["drill_words"] = weak_words
                                session["drill_index"] = 0
                                session["drill_fails"] = 0
                                session["drill_passed"] = 0

                                first_word = weak_words[0]
                                await message.channel.send(
                                    f"🎓 {bp_message}\n\n"
                                    f"🎯 Đọc từ: **{first_word.upper()}** 👇"
                                )
                                try:
                                    word_explain = await asyncio.get_event_loop().run_in_executor(
                                        None,
                                        lambda: _ollama_client.generate_json_sync(
                                            word_pronunciation_prompt(first_word, "general", _build_learner_context(user_id)),
                                            validate_word_pronunciation,
                                        ),
                                    )
                                    if word_explain.get("explanation"):
                                        await message.channel.send(f"📖 {word_explain['explanation']}")
                                except (OllamaUnavailableError, OllamaSchemaError):
                                    pass
                                sample_path = f"drill_sample_{user_id}.mp3"
                                if await generate_sample_audio(first_word, sample_path):
                                    await message.channel.send(file=discord.File(sample_path))
                                    try:
                                        os.remove(sample_path)
                                    except Exception:
                                        pass
                                _persist_session(user_id)
                                return

                            if bp_action == "retry_sentence":
                                await message.channel.send(f"🎓 {bp_message}")
                                sample_path = f"sentence_sample_{user_id}.mp3"
                                if await generate_sample_audio(session["sentence"], sample_path):
                                    await message.channel.send(file=discord.File(sample_path))
                                    try:
                                        os.remove(sample_path)
                                    except Exception:
                                        pass
                                _persist_session(user_id)
                                return

                            await message.channel.send(f"🎓 {bp_message}")
                        else:
                            await message.reply(score_block)

                        next_content = get_next_practice_sentence(session["current_phase_id"])
                        if next_content:
                            session["sentence"] = next_content["sentence"]
                            session["content_id"] = next_content["id"]
                            session["fail_count"] = 0
                            await message.channel.send(
                                f"➡️ Câu tiếp theo:\n\n"
                                f"🎯 **Đọc câu sau:**\n"
                                f"👉 **`{next_content['sentence']}`**\n\n"
                                f"🔊 *Nghe mẫu bên dưới, rồi ghi âm đọc lại.*"
                            )
                            sample_path = f"curriculum_sample_{user_id}.mp3"
                            if await generate_sample_audio(next_content["sentence"], sample_path):
                                await message.channel.send(file=discord.File(sample_path))
                                try:
                                    os.remove(sample_path)
                                except Exception:
                                    pass
                            _persist_session(user_id)
                            return

                        await message.channel.send(
                            f"🎉 Hoàn thành Tuần {session.get('current_phase_number')}! Gõ `!go` để sang bước tiếp theo."
                        )
                        try:
                            phase_data = (
                                f"Phase: {session.get('phase_theme', 'unknown')}\n"
                                f"Mastered: {session.get('phase_mastered_count', 0)}/{session.get('phase_total_content', 0)}\n"
                                f"Total scores in session: {len(session.get('scores', []))}\n"
                                f"Average score: {round(sum(session.get('scores', []))/max(len(session.get('scores', [])), 1), 1)}"
                            )
                            report = await asyncio.get_event_loop().run_in_executor(
                                None,
                                lambda: _ollama_client.generate_json_sync(
                                    weekly_progress_report_prompt(phase_data, _build_learner_context(user_id)),
                                    validate_weekly_report,
                                ),
                            )
                            if report.get("report"):
                                await message.channel.send(f"📊 **Báo cáo tuần:**\n{report['report']}")
                        except (OllamaUnavailableError, OllamaSchemaError):
                            pass
                        await _send_session_summary(message.channel, user_id, session)
                        _end_session(user_id)
                        return

                    if error_details:
                        score_block += f"\n{error_details}"
                    await message.reply(score_block)

                    session["fail_count"] = session.get("fail_count", 0) + 1
                    current_content = get_next_practice_sentence(session["current_phase_id"])
                    if current_content and current_content.get("id") != session.get("content_id"):
                        current_content = None
                    if not current_content:
                        current_content = {
                            "sentence": session["sentence"],
                            "target_phonemes": [],
                            "difficulty_score": 3,
                        }

                    if session["fail_count"] >= 6:
                        coaching = {
                            "action": "move_on",
                            "message": "Câu này cần thêm thời gian — mình chuyển sang câu khác rồi quay lại sau nhé! Đừng lo, mỗi lần thử đều giúp não ghi nhớ.",
                            "focus_words": [],
                        }
                    else:
                        coaching_prompt = teacher_coaching_prompt(
                            session["sentence"], score, session["fail_count"],
                            problem_words or [], error_details or "",
                            _build_learner_context(user_id)
                        )
                        try:
                            coaching = await asyncio.get_event_loop().run_in_executor(
                                None, lambda: _ollama_client.generate_json_sync(coaching_prompt, validate_teacher_coaching)
                            )
                        except (OllamaUnavailableError, OllamaSchemaError):
                            coaching = {
                                "action": "retry_sentence",
                                "message": "Nghe lại mẫu rồi thử lại nhé!",
                                "focus_words": [],
                            }

                    ai_action = coaching["action"]
                    ai_message = coaching["message"]

                    if ai_action == "drill_words":
                        drill_words = coaching.get("focus_words", []) or problem_words or []
                        if drill_words and not session.get("drill_done"):
                            session["mode"] = "word_drill"
                            session["drill_words"] = drill_words
                            session["drill_index"] = 0
                            session["drill_fails"] = 0
                            session["drill_passed"] = 0

                            first_word = drill_words[0]
                            await message.channel.send(
                                f"🎓 {ai_message}\n\n"
                                f"🎯 Đọc từ: **{first_word.upper()}** 👇"
                            )
                            try:
                                word_explain = await asyncio.get_event_loop().run_in_executor(
                                    None,
                                    lambda: _ollama_client.generate_json_sync(
                                        word_pronunciation_prompt(first_word, "general", _build_learner_context(user_id)),
                                        validate_word_pronunciation,
                                    ),
                                )
                                if word_explain.get("explanation"):
                                    await message.channel.send(f"📖 {word_explain['explanation']}")
                            except (OllamaUnavailableError, OllamaSchemaError):
                                pass
                            sample_path = f"drill_sample_{user_id}.mp3"
                            if await generate_sample_audio(first_word, sample_path):
                                await message.channel.send(file=discord.File(sample_path))
                                try:
                                    os.remove(sample_path)
                                except Exception:
                                    pass
                            _persist_session(user_id)
                            return
                        ai_action = "retry_sentence"

                    if ai_action == "move_on":
                        next_content = get_next_practice_sentence(session["current_phase_id"])
                        if next_content and next_content["id"] != session.get("content_id"):
                            progress = get_phase_progress(session["current_phase_id"])
                            session["sentence"] = next_content["sentence"]
                            session["content_id"] = next_content["id"]
                            session["fail_count"] = 0
                            session["drill_done"] = False
                            session["phase_mastered_count"] = progress["mastered"]
                            session["phase_total_content"] = progress["total"]
                            header = f"📍 Tuần {session['current_phase_number']} · {session['phase_theme']} · {progress['mastered']}/{progress['total']}"
                            await message.channel.send(
                                f"🎓 {ai_message}\n\n{header}\n\n"
                                f"🎯 **Đọc câu sau:**\n"
                                f"👉 **`{next_content['sentence']}`**\n\n"
                                f"🔊 *Nghe mẫu bên dưới, rồi ghi âm đọc lại.*"
                            )
                            sample_path = f"curriculum_sample_{user_id}.mp3"
                            if await generate_sample_audio(next_content["sentence"], sample_path):
                                await message.channel.send(file=discord.File(sample_path))
                                try:
                                    os.remove(sample_path)
                                except Exception:
                                    pass
                            _persist_session(user_id)
                            return
                        try:
                            regen = await _curriculum_generator.generate_replacement_sentence_async(
                                current_content.get("target_phonemes", []),
                                current_content.get("difficulty_score", 3),
                                session.get("phase_theme", "general"),
                                [session["sentence"]],
                            )
                            if regen.get("sentence"):
                                from db.curriculum import add_phase_content

                                add_phase_content(session["current_phase_id"], [regen])
                                new_content = get_next_practice_sentence(session["current_phase_id"])
                                if new_content and new_content["id"] != session.get("content_id"):
                                    progress = get_phase_progress(session["current_phase_id"])
                                    session["sentence"] = new_content["sentence"]
                                    session["content_id"] = new_content["id"]
                                    session["fail_count"] = 0
                                    session["drill_done"] = False
                                    session["phase_mastered_count"] = progress["mastered"]
                                    session["phase_total_content"] = progress["total"]
                                    header = f"📍 Tuần {session['current_phase_number']} · {session['phase_theme']} · {progress['mastered']}/{progress['total']}"
                                    await message.channel.send(
                                        f"🎓 {ai_message}\n\n{header}\n\n"
                                        f"🎯 **Đọc câu sau:**\n"
                                        f"👉 **`{new_content['sentence']}`**\n\n"
                                        f"🔊 *Nghe mẫu bên dưới, rồi ghi âm đọc lại.*"
                                    )
                                    sample_path = f"curriculum_sample_{user_id}.mp3"
                                    if await generate_sample_audio(new_content["sentence"], sample_path):
                                        await message.channel.send(file=discord.File(sample_path))
                                        try:
                                            os.remove(sample_path)
                                        except Exception:
                                            pass
                                    _persist_session(user_id)
                                    return
                        except (OllamaUnavailableError, OllamaSchemaError):
                            pass
                        await message.channel.send("📚 Đã hết câu mới. Gõ `!go` để kiểm tra tiến trình.")
                        await _send_session_summary(message.channel, user_id, session)
                        _end_session(user_id)
                        return

                    await message.channel.send(f"🎓 {ai_message}")
                    words = session["sentence"].split()
                    if len(words) > 8 and session["fail_count"] >= 2:
                        from engines.tts import generate_chunked_audio

                        chunk_path = f"chunked_sample_{user_id}.mp3"
                        if await generate_chunked_audio(session["sentence"], chunk_path):
                            await message.channel.send(
                                "🔊 *Câu này hơi dài — nghe từng phần chậm rồi ghép lại:*"
                            )
                            await message.channel.send(file=discord.File(chunk_path))
                            try:
                                os.remove(chunk_path)
                            except Exception:
                                pass
                    else:
                        sample_path = f"sentence_sample_{user_id}.mp3"
                        if await generate_sample_audio(session["sentence"], sample_path):
                            await message.channel.send(file=discord.File(sample_path))
                            try:
                                os.remove(sample_path)
                            except Exception:
                                pass
                    _persist_session(user_id)
                    return

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
                        _end_session(user_id)
                        await message.channel.send(
                            f"🏆 **HOÀN THÀNH CHỈ TIÊU NGÀY!** 🏆\n"
                            f"🔥 Chuỗi: **{new_streak} ngày**\n\n"
                            f"💡 Nghỉ ngơi tới mai! 💤"
                        )
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
                            _end_session(user_id)
                            await message.channel.send(
                                f"🏆 **Hoàn thành!** 🔥 Chuỗi: `{new_streak} ngày`"
                            )
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
                            _end_session(user_id)
                            await message.channel.send(
                                f"🏆 **Hoàn thành!** 🔥 Chuỗi: `{new_streak} ngày`"
                            )
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


            except Exception as exc:
                if os.path.exists(temp_audio_path):
                    os.remove(temp_audio_path)
                await message.reply(f"❌ Lỗi xử lý bài ghi âm: {exc}")
                return

client.run(DISCORD_BOT_TOKEN)
