from __future__ import annotations


def split_message(text: str, *, max_chars: int = 3500) -> list[str]:
    if max_chars < 500:
        raise ValueError("max_chars must be at least 500")
    if len(text) <= max_chars:
        return [text]

    chunks: list[str] = []
    current: list[str] = []
    current_len = 0
    for paragraph in _paragraphs(text):
        paragraph_len = len(paragraph)
        if paragraph_len > max_chars:
            if current:
                chunks.append("\n\n".join(current).strip())
                current = []
                current_len = 0
            chunks.extend(_hard_split(paragraph, max_chars=max_chars))
            continue
        added_len = paragraph_len + (2 if current else 0)
        if current and current_len + added_len > max_chars:
            chunks.append("\n\n".join(current).strip())
            current = [paragraph]
            current_len = paragraph_len
        else:
            current.append(paragraph)
            current_len += added_len
    if current:
        chunks.append("\n\n".join(current).strip())
    total = len(chunks)
    if total <= 1:
        return chunks
    return [f"（{index}/{total}）\n{chunk}" for index, chunk in enumerate(chunks, start=1)]


def _paragraphs(text: str) -> list[str]:
    return [paragraph.strip() for paragraph in text.split("\n\n") if paragraph.strip()]


def _hard_split(text: str, *, max_chars: int) -> list[str]:
    return [text[index : index + max_chars] for index in range(0, len(text), max_chars)]
