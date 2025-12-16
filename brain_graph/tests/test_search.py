from __future__ import annotations

import duckdb

from brain_graph.search.searcher import exact_string_search, fuzzy_search, semantic_search


def _make_con() -> duckdb.DuckDBPyConnection:
    con = duckdb.connect(":memory:")
    con.execute(
        """
        CREATE TABLE nodes (
            id VARCHAR,
            type VARCHAR,
            text VARCHAR,
            summary VARCHAR,
            source_file VARCHAR
        )
        """
    )
    con.execute(
        """
        CREATE TABLE chunk_embeddings_256d (
            chunk_id VARCHAR,
            embedding FLOAT[256]
        )
        """
    )
    return con


def test_fuzzy_search_finds_typos() -> None:
    con = _make_con()
    con.execute(
        "INSERT INTO nodes VALUES (?, 'chunk', ?, NULL, ?)",
        ["c1", "Maschinelles Lernen ist ein Teilgebiet der KI.", "doc1.md"],
    )

    results = fuzzy_search(con, "Mashinelles Lehrnen", limit=5, max_distance=2)
    assert results
    assert results[0]["chunk_id"] == "c1"
    assert results[0]["matched_terms"] >= 1


def test_exact_string_search_is_case_insensitive_by_default() -> None:
    con = _make_con()
    con.execute(
        "INSERT INTO nodes VALUES (?, 'chunk', ?, NULL, ?)",
        ["c1", "Deep Learning is fun.", "doc1.md"],
    )

    results = exact_string_search(con, "deep learning", limit=5)
    assert results
    assert results[0]["chunk_id"] == "c1"
    assert results[0]["match_count"] >= 1


def test_semantic_search_orders_by_cosine_similarity() -> None:
    con = _make_con()
    con.execute(
        "INSERT INTO nodes VALUES (?, 'chunk', ?, NULL, ?)",
        ["c1", "A", "doc1.md"],
    )
    con.execute(
        "INSERT INTO nodes VALUES (?, 'chunk', ?, NULL, ?)",
        ["c2", "B", "doc2.md"],
    )

    emb1 = [1.0] + [0.0] * 255
    emb2 = [0.0, 1.0] + [0.0] * 254
    con.execute("INSERT INTO chunk_embeddings_256d VALUES (?, ?::FLOAT[256])", ["c1", emb1])
    con.execute("INSERT INTO chunk_embeddings_256d VALUES (?, ?::FLOAT[256])", ["c2", emb2])

    results = semantic_search(con, emb1, limit=2)
    assert [r["chunk_id"] for r in results] == ["c1", "c2"]

