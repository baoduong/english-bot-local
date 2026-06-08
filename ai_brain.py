"""Backward-compatible wrapper — new code should import from analysis/ and engines/ packages directly."""

from analysis.phonemes import clean_word, phoneme_similarity
from analysis.errors import classify_error, ERROR_TYPE_LABELS
from analysis.pronunciation import analyze_audio as analyze_audio_with_whisper, analyze_single_word
from engines.tts import generate_sample_audio
from engines.ollama import _ollama_async

import discord
import os


async def send_new_word_tutorial(channel, sentence, new_word):
    """
    Hàm Tiền giáo dục (Pre-teaching) cho từ mới hoặc từ bị kẹt:
    1. Gọi Llama 3.2 viết mẹo khẩu hình mỳ ăn liền.
    2. Gọi Edge-TTS tạo file âm thanh đọc mẫu chuẩn Microsoft Neural.
    3. Gửi cả 2 lên kênh Discord.
    """
    prompt = f"""
    Học viên chuẩn bị luyện câu có chứa từ: "{new_word}".
    Hãy viết hướng dẫn phát âm từ "{new_word}" bằng tiếng Việt:
    - Cách bẻ nhỏ âm tiết và vị trí đánh trọng âm.
    - Một mẹo đặt lưỡi hoặc răng để phát âm đúng nhất.
    Viết cực kỳ ngắn gọn, dưới 50 từ, trình bày bằng các gạch đầu dòng rõ ràng.
    """
    try:
        response = await _ollama_async(prompt)
        teacher_tip = response["response"]
    except Exception as e:
        print(f"Lỗi gọi Ollama: {e}")
        teacher_tip = f"• Hãy chú ý nhấn đúng trọng âm của từ: **{new_word}**."

    output_audio_path = "teacher_sample.mp3"
    has_audio = await generate_sample_audio(sentence, output_audio_path)

    await channel.send(
        f"🆕 **HỌC TỪ MỚI CÙNG GIÁO VIÊN AI:**\n"
        f"🎯 Từ tiêu điểm: **{new_word.upper()}**\n\n"
        f"{teacher_tip}\n"
        f"👇 *Nghe kỹ file phát âm mẫu dưới đây rồi giữ micro bắt chước đọc lại nhé:*"
    )

    await channel.send(f"👉 **`{sentence}`**")

    if has_audio and os.path.exists(output_audio_path):
        await channel.send(file=discord.File(output_audio_path))
        try:
            os.remove(output_audio_path)
        except Exception:
            pass
