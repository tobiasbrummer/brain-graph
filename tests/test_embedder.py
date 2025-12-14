from __future__ import annotations

from pathlib import Path

from brain_graph.pipeline.embedder import extract_text_ranges, filter_oversized_texts, normalize_markdown


def test_normalize_markdown_removes_links_formatting_and_ulid() -> None:
    text = (
        "# Title\n"
        "+id:01KCEQFS97VZFWN6Y0JH84BSM7\n\n"
        "See [Foo](https://example.com) and **bold** `code`.\n"
    )
    out = normalize_markdown(text)
    assert "+id:" not in out
    assert "https://example.com" not in out
    assert "Foo" in out
    assert "bold" in out
    assert "code" in out


def test_extract_text_ranges_adds_section_context(tmp_path: Path) -> None:
    md = tmp_path / "note.md"
    content = "## Section\n\nHello *world*.\n"
    md.write_text(content, encoding="utf-8")

    # Extract just the paragraph range.
    start = content.index("Hello")
    end = content.index(".\n") + 1

    nodes = [
        {"id": "sec_1", "type": "section", "title": "Section", "level": 2},
        {"id": "chunk_1", "type": "chunk", "char_start": start, "char_end": end},
    ]
    edges = [{"type": "contains", "from": "sec_1", "to": "chunk_1"}]

    texts, chunk_ids = extract_text_ranges(md, nodes, edges)
    assert chunk_ids == ["chunk_1"]
    assert len(texts) == 1
    assert texts[0].startswith("Passage: ")
    assert "Section:" in texts[0]
    assert "Hello world." in texts[0]


def test_filter_oversized_texts_skips_large_items() -> None:
    texts = ["short", "x" * (8000 * 4 + 1)]
    ids = ["a", "b"]

    filtered_texts, filtered_ids, skipped = filter_oversized_texts(texts, ids, max_tokens=8000)
    assert filtered_texts == ["short"]
    assert filtered_ids == ["a"]
    assert skipped == [1]
