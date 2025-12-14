from __future__ import annotations

import duckdb
import pyarrow as pa
import pyarrow.parquet as pq

from brain_graph.search.reranking import _get_parquet_id_map, reciprocal_rank_fusion, rerank_with_full_vectors


def test_reciprocal_rank_fusion_combines_rankings() -> None:
    rankings = [
        [{"chunk_id": "a"}, {"chunk_id": "b"}, {"chunk_id": "c"}],
        [{"chunk_id": "a"}, {"chunk_id": "c"}, {"chunk_id": "b"}],
        [{"chunk_id": "a"}],
    ]

    combined = reciprocal_rank_fusion(rankings, k=60)
    assert combined
    assert combined[0]["chunk_id"] == "a"
    assert "rrf_score" in combined[0]


def test_rerank_with_full_vectors_orders_by_similarity(tmp_path) -> None:
    parquet_path = tmp_path / "embeddings.parquet"

    table = pa.table(
        {
            "chunk_idx": ["a", "b"],
            "embedding": [[1.0, 0.0], [0.0, 1.0]],
        }
    )
    pq.write_table(table, parquet_path)

    scores = rerank_with_full_vectors(
        candidate_ids=["a", "b"],
        query_embedding_full=[1.0, 0.0],
        parquet_path=parquet_path,
        top_k=2,
    )

    assert [s["chunk_id"] for s in scores] == ["a", "b"]
    assert scores[0]["similarity"] > scores[1]["similarity"]


def test_get_parquet_id_map_supports_new_schema() -> None:
    con = duckdb.connect(":memory:")
    con.execute(
        """
        CREATE TABLE chunk_embeddings_256d (
            chunk_id VARCHAR,
            chunk_local_id VARCHAR,
            source_file VARCHAR
        )
        """
    )
    con.execute(
        "INSERT INTO chunk_embeddings_256d VALUES ('ULID_CHUNK', 'chunk_local', 'doc.md')"
    )

    parquet_ids, id_map = _get_parquet_id_map(con, "doc.md", ["ULID_CHUNK"])
    assert parquet_ids == ["chunk_local"]
    assert id_map == {"chunk_local": "ULID_CHUNK"}


def test_get_parquet_id_map_falls_back_without_column() -> None:
    con = duckdb.connect(":memory:")
    con.execute(
        """
        CREATE TABLE chunk_embeddings_256d (
            chunk_id VARCHAR,
            source_file VARCHAR
        )
        """
    )
    con.execute("INSERT INTO chunk_embeddings_256d VALUES ('chunk_a', 'doc.md')")

    parquet_ids, id_map = _get_parquet_id_map(con, "doc.md", ["chunk_a"])
    assert parquet_ids == ["chunk_a"]
    assert id_map is None
