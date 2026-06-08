import ollama
import asyncio
import functools
import os
from dotenv import load_dotenv

load_dotenv()

OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma4:31b-cloud")

# Cache kết quả phân tích độ khó — tránh gọi Ollama lại cho cùng câu
_difficulty_cache = {}


def _ollama_generate(prompt, temperature=0.7):
    """Gọi Ollama sync — dùng trong thread pool để không block event loop"""
    return ollama.generate(model=OLLAMA_MODEL, prompt=prompt, options={"temperature": temperature})


async def _ollama_async(prompt, temperature=0.7):
    """Gọi Ollama non-blocking — chạy trong thread executor"""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, functools.partial(_ollama_generate, prompt, temperature))


def assess_difficulty(text):
    """
    Dùng Ollama phân tích độ khó phát âm của câu/từ cho người Việt.
    Trả về: "simple" hoặc "complex"
    Kết quả được cache để không gọi lại Ollama cho cùng text.
    Hàm sync — gọi trước khi vào async flow (trong analyze functions chạy trên thread).
    """
    cache_key = text.strip().lower()
    if cache_key in _difficulty_cache:
        return _difficulty_cache[cache_key]

    # Heuristic nhanh cho từ đơn ngắn — không cần gọi LLM
    words = text.strip().split()
    if len(words) == 1 and len(words[0]) <= 6:
        _difficulty_cache[cache_key] = "simple"
        return "simple"

    prompt = f"""Analyze pronunciation difficulty of this English text for a Vietnamese speaker.
Text: "{text}"

Consider: silent letters, consonant clusters (th, str, ght), unusual vowel sounds, word length, stress patterns.

Reply with ONLY one word: "simple" or "complex". No explanation."""

    try:
        response = ollama.generate(model=OLLAMA_MODEL, prompt=prompt, options={"temperature": 0})
        answer = response["response"].strip().lower()
        result = "complex" if "complex" in answer else "simple"
    except Exception as e:
        print(f"Ollama assess_difficulty error: {e}. Default: simple")
        result = "simple"

    _difficulty_cache[cache_key] = result
    return result
