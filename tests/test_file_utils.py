from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from brain_graph.utils.file_utils import (
    extract_ulid_from_md,
    generate_ulid,
    get_or_generate_ulid,
    inject_ulid_into_md,
    slugify,
    strip_ulid_lines,
)


def test_slugify_basic() -> None:
    assert slugify("Jazz Einführung") == "jazz-einfuhrung"
    assert slugify("C++ Programming") == "c-programming"


def test_generate_ulid_is_deterministic_with_fixed_timestamp() -> None:
    ts = datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    a1 = generate_ulid("hello", timestamp=ts)
    a2 = generate_ulid("hello", timestamp=ts)
    b = generate_ulid("world", timestamp=ts)

    assert a1 == a2
    assert a1 != b
    assert len(a1) == 26


def test_strip_ulid_lines_removes_injected_id_lines() -> None:
    text = "Title\n+id:01KCEQFS97VZFWN6Y0JH84BSM7\n\nBody"
    assert "+id:" not in strip_ulid_lines(text)


def test_inject_and_extract_ulid_roundtrip(tmp_path: Path) -> None:
    md = tmp_path / "note.md"
    md.write_text("# Title\n\nBody\n", encoding="utf-8")

    ulid = "01KCEQFS97VZFWN6Y0JH84BSM7"
    injected = inject_ulid_into_md(md, ulid)
    assert injected is True
    assert extract_ulid_from_md(md) == ulid

    # Second injection should be a no-op
    injected_again = inject_ulid_into_md(md, ulid)
    assert injected_again is False


def test_get_or_generate_ulid_prefers_existing(tmp_path: Path) -> None:
    md = tmp_path / "note.md"
    ulid = "01KCEQFS97VZFWN6Y0JH84BSM7"
    md.write_text(f"# Title\n+id:{ulid}\n\nBody\n", encoding="utf-8")

    got = get_or_generate_ulid(md, md.read_text(encoding="utf-8"))
    assert got == ulid
