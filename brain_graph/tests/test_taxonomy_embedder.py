from __future__ import annotations

from pathlib import Path

import pyarrow.parquet as pq

from brain_graph.pipeline.taxonomy_embedder import category_to_text, save_parquet


def test_category_to_text_includes_title_description_and_keywords() -> None:
    cat = {
        "id": "test",
        "title": "Foo",
        "description": "Bar",
        "keywords": ["a", "b"],
    }
    text = category_to_text(cat)
    assert text.startswith("Query: ")
    assert "Foo" in text
    assert "Bar" in text
    assert "a, b" in text


def test_save_parquet_writes_expected_columns(tmp_path: Path) -> None:
    out = tmp_path / "taxonomy.parquet"
    save_parquet(
        ["cat1", "cat2"],
        [[0.1, 0.2], [0.3, 0.4]],
        out,
        {"embedding_model": "dummy"},
        actual_dim=2,
    )

    table = pq.read_table(out)
    assert "category_id" in table.column_names
    assert "embedding" in table.column_names
