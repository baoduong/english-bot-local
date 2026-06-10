import edge_tts


async def generate_sample_audio(text: str, output_path: str, rate: str = "-20%") -> bool:
    try:
        communicate = edge_tts.Communicate(text, "en-US-ChristopherNeural", rate=rate)
        await communicate.save(output_path)
        return True
    except Exception as e:
        print(f"Lỗi sinh âm thanh mẫu Edge-TTS: {e}")
        return False


async def generate_chunked_audio(sentence: str, output_path: str, chunk_size: int = 3) -> bool:
    words = sentence.split()
    if len(words) <= chunk_size:
        return await generate_sample_audio(sentence, output_path, rate="-30%")

    chunks = []
    for i in range(0, len(words), chunk_size):
        chunk = " ".join(words[i:i + chunk_size])
        chunks.append(chunk)

    slow_text = " . . . ".join(chunks)
    return await generate_sample_audio(slow_text, output_path, rate="-30%")
