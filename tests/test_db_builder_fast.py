from __future__ import annotations

import json
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from brain_graph.db.db_builder import BrainGraphDB


def test_db_builder_fast_import_creates_core_tables(tmp_path: Path) -> None:
    data_dir = tmp_path / ".brain_graph" / "data"
    docs_dir = data_dir / "documents" / "2025-12"
    emb_dir = data_dir / "embeddings" / "2025-12"
    docs_dir.mkdir(parents=True)
    emb_dir.mkdir(parents=True)

    file_base = "testnote-ABC123"
    doc_id = "01KCEQFS97VZFWN6Y0JH84BSM7"
    section_ulid = "01KCEQFS8X3CFC7N4YVA3G0FYV"
    chunk_ulid = "01KCEQFS8XBY4TQ5X86CEY9QGH"
    ent_ulid = "01KCA976R5ZT47BXRCKD32PBRA"

    doc_path = docs_dir / f"{file_base}.document.json"
    doc = {
        "id": doc_id,
        "slug": "testnote",
        "path": "vault/2025-12/testnote-ABC123.md",
        "original_source": None,
        "title": "Test Note",
        "language": "en",
        "doc_type": "note",
        "content_hash": "sha256:deadbeef",
        "file_hash": "sha256:deadbeef",
        "source_commit": None,
        "source_commit_date": None,
        "source_dirty": False,
        "created": "2025-01-01T00:00:00+00:00",
        "updated": "2025-01-01T00:00:00+00:00",
        "uses": 0,
        "importance": None,
        "decay": None,
        "full_text": "# Test Note\n+id:01KCEQFS97VZFWN6Y0JH84BSM7\n\nBody.\n",
        "facets": {},
        "nodes": {
            "sections": [
                {"id": "sec_1", "ulid": section_ulid, "title": "Test Note", "level": 1}
            ],
            "chunks": [
                {
                    "id": "chunk_abc",
                    "ulid": chunk_ulid,
                    "doc_id": doc_id,
                    "chunk_id": f"{doc_id}:aaaaaaaaaaaa",
                    "chunk_hash": "aaaaaaaaaaaa",
                    "chunk_index": 0,
                    "text": "Body.",
                    "tokens": 1,
                    "language": "en",
                    "char_start": 0,
                    "char_end": 5,
                    "summary": None,
                    "categories": [],
                }
            ],
            "entities": [
                {
                    "id": "ent_x",
                    "ulid": ent_ulid,
                    "entity_type": "LOC",
                    "title": "Somewhere",
                    "occurrences": 1,
                    "mentioned_in": ["chunk_abc"],
                }
            ],
        },
        "edges": [
            {
                "from_id": "sec_1",
                "to_id": "chunk_abc",
                "type": "in_section",
                "weight": None,
                "similarity": None,
                "overlap_chars": None,
            },
            {
                "from_id": "chunk_abc",
                "to_id": "ent_x",
                "type": "mentions",
                "weight": 1.0,
                "similarity": None,
                "overlap_chars": None,
            },
        ],
        "links": [],
        "backlinks": [],
        "processing": {"steps": [{"step": "chunking", "completed": True, "timestamp": "2025-01-01T00:00:00+00:00"}]},
    }
    doc_path.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")

    parquet_path = emb_dir / f"{file_base}.parquet"
    embedding = [0.0] * 1024
    pq.write_table(
        pa.table({"chunk_idx": ["chunk_abc"], "embedding": [embedding]}),
        parquet_path,
    )

    db = BrainGraphDB(":memory:")
    db.import_directory_fast(data_dir)

    # Filter to this document only (taxonomy import may add additional nodes/edges).
    assert db.con.execute(
        "SELECT COUNT(*) FROM nodes WHERE source_file = ?",
        [doc["path"]],
    ).fetchone()[0] == 3
    assert db.con.execute(
        "SELECT COUNT(*) FROM edges WHERE source_file = ?",
        [doc["path"]],
    ).fetchone()[0] == 2
    assert db.con.execute("SELECT COUNT(*) FROM meta").fetchone()[0] == 1
    assert db.con.execute("SELECT COUNT(*) FROM embedding_sources").fetchone()[0] == 1
    assert db.con.execute("SELECT COUNT(*) FROM chunk_embeddings_256d").fetchone()[0] == 1
    assert db.con.execute("SELECT COUNT(*) FROM doc_links").fetchone()[0] == 0
    assert db.con.execute("SELECT COUNT(*) FROM doc_backlinks").fetchone()[0] == 0

    row = db.con.execute(
        "SELECT chunk_id, chunk_local_id, source_file FROM chunk_embeddings_256d LIMIT 1"
    ).fetchone()
    assert row == (chunk_ulid, "chunk_abc", "vault/2025-12/testnote-ABC123.md")

    # Index building should not hard-fail in offline environments.
    db.build_indexes()


def test_db_builder_fast_import_builds_doc_links_and_backlinks(tmp_path: Path) -> None:
    data_dir = tmp_path / ".brain_graph" / "data"
    docs_dir = data_dir / "documents" / "2025-12"
    docs_dir.mkdir(parents=True)

    doc_a = "01KCEQFS97VZFWN6Y0JH84BSM7"
    doc_b = "01KCEQFS97VZFWN6Y0JH84BSM8"

    base_a = "a-AAAAAA"
    base_b = "b-BBBBBB"

    common = {
        "original_source": None,
        "language": "en",
        "doc_type": "note",
        "content_hash": "sha256:deadbeef",
        "file_hash": "sha256:deadbeef",
        "source_commit": None,
        "source_commit_date": None,
        "source_dirty": False,
        "created": "2025-01-01T00:00:00+00:00",
        "updated": "2025-01-01T00:00:00+00:00",
        "uses": 0,
        "importance": None,
        "decay": None,
        "facets": {},
        "nodes": {"sections": [], "chunks": [], "entities": []},
        "edges": [],
        "backlinks": [],
        "processing": {"steps": [{"step": "chunking", "completed": True, "timestamp": "2025-01-01T00:00:00+00:00"}]},
    }

    (docs_dir / f"{base_a}.document.json").write_text(
        json.dumps(
            {
                **common,
                "id": doc_a,
                "slug": "a",
                "path": f"vault/2025-12/{base_a}.md",
                "title": "A",
                "full_text": f"# A\n+id:{doc_a}\n\nSee +link:{doc_b}\n",
                "links": [
                    {"type": "link", "target_id": doc_b, "source_node": None, "context": "See +link", "char_offset": 0}
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (docs_dir / f"{base_b}.document.json").write_text(
        json.dumps(
            {
                **common,
                "id": doc_b,
                "slug": "b",
                "path": f"vault/2025-12/{base_b}.md",
                "title": "B",
                "full_text": f"# B\n+id:{doc_b}\n\nSee +link:{doc_a}\n",
                "links": [
                    {"type": "link", "target_id": doc_a, "source_node": None, "context": "See +link", "char_offset": 0}
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    db = BrainGraphDB(":memory:")
    db.import_directory_fast(data_dir)

    assert db.con.execute("SELECT COUNT(*) FROM doc_links").fetchone()[0] == 2
    assert db.con.execute("SELECT COUNT(*) FROM doc_backlinks").fetchone()[0] == 2

    links = set(db.con.execute("SELECT source_doc_id, target_doc_id FROM doc_links").fetchall())
    assert links == {(doc_a, doc_b), (doc_b, doc_a)}

    backlinks = set(db.con.execute("SELECT doc_id, source_doc_id FROM doc_backlinks").fetchall())
    assert backlinks == {(doc_a, doc_b), (doc_b, doc_a)}
