from __future__ import annotations

from crossborder_daily.splitter import split_message


def test_long_message_split() -> None:
    text = "\n\n".join(f"段落{i} " + "内容" * 80 for i in range(20))

    chunks = split_message(text, max_chars=700)

    assert len(chunks) > 1
    assert all(len(chunk) <= 720 for chunk in chunks)
    assert chunks[0].startswith("（1/")
