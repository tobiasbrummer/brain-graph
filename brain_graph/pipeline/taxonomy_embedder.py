#!/usr/bin/env python3
"""
Taxonomy Embedder: Taxonomie-Kategorien → Embeddings.

Liest `.brain_graph/config/taxonomy.md.nodes.json`, erzeugt Embeddings und schreibt
`.brain_graph/config/taxonomy.md.parquet`.

Usage:
    brain pipeline taxonomy-embed
    python -m brain_graph.pipeline.taxonomy_embedder
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq
from openai import OpenAI

from brain_graph.utils.cli_utils import emit_json, error_result, ms_since, ok_result
from brain_graph.utils.file_utils import load_config


def category_to_text(category: dict[str, Any]) -> str:
    """Konvertiert eine Kategorie zu Text für Embedding (Query-Prompt)."""
    title = (category.get("title") or "").strip()
    description = (category.get("description") or "").strip()
    keywords = category.get("keywords") or []

    keywords_text = ""
    if isinstance(keywords, list):
        keywords_text = ", ".join([str(k).strip() for k in keywords if str(k).strip()])

    parts: list[str] = []
    if title:
        parts.append(title)
    if description:
        parts.append(description)
    if keywords_text:
        parts.append(f"Schlüsselbegriffe: {keywords_text}")

    content = "\n\n".join(parts).strip()
    if not content:
        return ""

    # WICHTIG: Präfix für Jina v3 / asymmetrische Suche hinzufügen
    return f"Query: {content}"


def embed_texts(texts: list[str], config: dict[str, Any]) -> list[list[float]]:
    """Embedded Texte via OpenAI-kompatible API."""
    client = OpenAI(
        base_url=config["embedding_base_url"],
        api_key=config.get("embedding_api_key", "unused"),
    )

    embeddings: list[list[float]] = []
    batch_size = int(config.get("embedding_batch_size", 1))
    model = config["embedding_model"]

    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        print(
            f"Embedding taxonomy batch {i//batch_size + 1}/{(len(texts)-1)//batch_size + 1}...",
            file=sys.stderr,
        )
        response = client.embeddings.create(input=batch, model=model)
        batch_embeddings = sorted(response.data, key=lambda x: x.index)
        embeddings.extend([e.embedding for e in batch_embeddings])

    return embeddings


def save_parquet(
    category_ids: list[str],
    embeddings: list[list[float]],
    output_path: Path,
    config: dict[str, Any],
    *,
    actual_dim: int,
) -> None:
    """Speichert Taxonomie-Embeddings als Parquet."""
    table = pa.table({"category_id": category_ids, "embedding": embeddings})

    metadata = {
        b"model": str(config.get("embedding_model", "unknown")).encode(),
        b"dim": str(actual_dim).encode(),
        b"created_at": datetime.now(timezone.utc).isoformat().encode(),
        b"type": b"taxonomy",
    }
    existing = table.schema.metadata or {}
    table = table.replace_schema_metadata({**existing, **metadata})

    pq.write_table(table, output_path, compression="zstd")


def main() -> int:
    start = time.perf_counter()
    parser = argparse.ArgumentParser(description="Embed taxonomy categories")
    parser.add_argument(
        "-i",
        "--input",
        type=Path,
        default=Path(".brain_graph/config/taxonomy.md.nodes.json"),
        help="Input taxonomy nodes.json (default: .brain_graph/config/taxonomy.md.nodes.json)",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path(".brain_graph/config/taxonomy.md.parquet"),
        help="Output Parquet file (default: .brain_graph/config/taxonomy.md.parquet)",
    )
    parser.add_argument("-c", "--config", type=Path, default=None, help="config.json path")
    parser.add_argument(
        "--format",
        choices=["json", "text"],
        default="json",
        help="Output format (default: json)",
    )
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output")
    parser.add_argument("--debug", action="store_true", help="Include traceback in JSON error output")
    args = parser.parse_args()

    try:
        if not args.input.exists():
            raise FileNotFoundError(f"Input file not found: {args.input}")

        config = load_config(args.config)

        categories = json.loads(args.input.read_text(encoding="utf-8"))
        if not isinstance(categories, list):
            raise ValueError(f"Expected JSON array in {args.input}")

        texts: list[str] = []
        category_ids: list[str] = []
        for cat in categories:
            if not isinstance(cat, dict):
                continue
            text = category_to_text(cat)
            if text:
                texts.append(text)
                category_ids.append(str(cat.get("id")))

        if not texts:
            raise ValueError("No category texts prepared for embedding")

        embeddings = embed_texts(texts, config)

        actual_dim = len(embeddings[0]) if embeddings else 0
        expected_dim = int(config.get("embedding_dim", actual_dim or 0) or 0)
        if expected_dim and actual_dim and actual_dim != expected_dim:
            print(
                f"Warning: expected dim {expected_dim}, got {actual_dim}",
                file=sys.stderr,
            )

        args.output.parent.mkdir(parents=True, exist_ok=True)
        save_parquet(
            category_ids,
            embeddings,
            args.output,
            config,
            actual_dim=actual_dim,
        )

        result = ok_result(
            "taxonomy_embedder",
            input=str(args.input),
            output={"parquet": str(args.output)},
            counts={"categories": len(categories), "texts_embedded": len(embeddings)},
            embedding={"model": config.get("embedding_model"), "dim": actual_dim},
            duration_ms=ms_since(start),
        )
        if args.format == "json":
            emit_json(result, pretty=args.pretty)
        else:
            print(f"Written {args.output} ({len(embeddings)} embeddings)")
        return 0
    except Exception as e:
        if args.format == "json":
            emit_json(
                error_result("taxonomy_embedder", e, include_traceback=args.debug, duration_ms=ms_since(start)),
                pretty=args.pretty,
            )
            return 1
        raise


if __name__ == "__main__":
    raise SystemExit(main())

