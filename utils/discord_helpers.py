async def send_chunked(channel, text: str, max_len: int = 1900) -> list:
    """Sends text to Discord channel, splitting on newlines if >max_len chars.
    Returns list of Message objects sent.
    max_len defaults to 1900 (under Discord's 2000 limit) for safety margin.
    """
    if len(text) <= max_len:
        return [await channel.send(text)]

    chunks = []
    current = ""
    for line in text.split("\n"):
        if len(current) + len(line) + 1 > max_len:
            if current:
                chunks.append(current)
            if len(line) > max_len:
                for i in range(0, len(line), max_len):
                    chunks.append(line[i:i + max_len])
                current = ""
            else:
                current = line
        else:
            current = f"{current}\n{line}" if current else line
    if current:
        chunks.append(current)

    messages = []
    for chunk in chunks:
        messages.append(await channel.send(chunk))
    return messages
