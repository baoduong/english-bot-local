import edge_tts


async def generate_sample_audio(text, output_path, rate="-20%"):
    """Tạo file audio đọc mẫu bằng Edge-TTS. Trả về True nếu thành công."""
    try:
        communicate = edge_tts.Communicate(text, "en-US-ChristopherNeural", rate=rate)
        await communicate.save(output_path)
        return True
    except Exception as e:
        print(f"Lỗi sinh âm thanh mẫu Edge-TTS: {e}")
        return False
