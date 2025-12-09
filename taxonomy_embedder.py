#!/usr/bin/env python3
"""
Taxonomy Embedder: Taxonomie-Kategorien → Embeddings.

Liest taxonomy.nodes.json, erstellt Text aus title + keywords,
embedded via OpenAI-kompatible API, schreibt Parquet.

Usage:
    python taxonomy_embedder.py -i taxonomy.nodes.json -o taxonomy.parquet
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq
from openai import OpenAI


def load_config(config_path: Path | None = None) -> dict[str, Any]:
    """Lädt Config aus config.json."""
    defaults = {
        "embedding_base_url": "http://localhost:8200/v1",
        "embedding_model": "jina-embeddings-v2-base-de",
        "embedding_dim": 768,
        "embedding_api_key": "unused",
        "embedding_batch_size": 1,
    }

    if config_path is None:
        for parent in [Path.cwd(), *Path.cwd().parents]:
            candidate = parent / "config.json"
            if candidate.exists():
                config_path = candidate
                break

    if config_path and config_path.exists():
        user_config = json.loads(config_path.read_text(encoding="utf-8"))
        defaults.update(user_config)

    return defaults


def category_to_text(category: dict[str, Any]) -> str:
    """Konvertiert Kategorie-Beschreibung zu Text für Embedding.

    Kombiniert description und keywords für bessere Embeddings.
    """
    description = category.get("description", "")
    keywords = category.get("keywords", [])

    # Keywords als komma-separierte Liste
    keywords_text = ", ".join(keywords) if keywords else ""

    # Kombiniere: Description + Keywords
    if keywords_text:
        content = f"{description}\n\nSchlüsselbegriffe: {keywords_text}"
    else:
        content = description

    # WICHTIG: Präfix für Jina v3 / asymmetrische Suche hinzufügen
    return f"Query: {content}"


def embed_texts(texts: list[str], config: dict[str, Any]) -> list[list[float]]:
    """Embedded Texte via OpenAI-kompatible API."""
    client = OpenAI(
        base_url=config["embedding_base_url"],
        api_key=config["embedding_api_key"],
    )

    embeddings = []
    batch_size = config["embedding_batch_size"]

    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        print(f"Embedding batch {i//batch_size + 1}/{(len(texts)-1)//batch_size + 1}...", file=sys.stderr)
        response = client.embeddings.create(
            input=batch,
            model=config["embedding_model"],
        )
        # Sortiere nach Index
        batch_embeddings = sorted(response.data, key=lambda x: x.index)
        embeddings.extend([e.embedding for e in batch_embeddings])

    return embeddings


def save_parquet(
    category_ids: list[str],
    embeddings: list[list[float]],
    output_path: Path,
    config: dict[str, Any],
) -> None:
    """Speichert Taxonomie-Embeddings als Parquet."""
    table = pa.table({
        "category_id": category_ids,
        "embedding": embeddings,
    })

    # Metadata
    metadata = {
        b"model": config["embedding_model"].encode(),
        b"dim": str(config["embedding_dim"]).encode(),
        b"created_at": datetime.now(timezone.utc).isoformat().encode(),
        b"type": b"taxonomy",
    }

    # Merge mit existierenden Schema-Metadata
    existing = table.schema.metadata or {}
    table = table.replace_schema_metadata({**existing, **metadata})

    pq.write_table(table, output_path, compression="zstd")


def main():
    parser = argparse.ArgumentParser(description="Embed taxonomy categories")
    parser.add_argument("-i", "--input", type=Path, default=Path("taxonomy.nodes.json"),
                        help="Input taxonomy nodes.json")
    parser.add_argument("-o", "--output", type=Path, default=Path("taxonomy.parquet"),
                        help="Output Parquet file")
    parser.add_argument("-c", "--config", type=Path, help="config.json path")
    args = parser.parse_args()

    if not args.input.exists():
        print(f"Error: Input file not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    # Config laden
    config = load_config(args.config)

    # Lade Kategorien
    categories = json.loads(args.input.read_text(encoding="utf-8"))
    print(f"Loaded {len(categories)} categories", file=sys.stderr)

    # Konvertiere zu Texten
    texts = []
    category_ids = []
    for cat in categories:
        text = category_to_text(cat)
        if text:
            texts.append(text)
            category_ids.append(cat["id"])

    print(texts)
    print(f"Prepared {len(texts)} texts for embedding", file=sys.stderr)

    # Embeddings erzeugen
    embeddings = embed_texts(texts, config)

    # Dimension validieren
    actual_dim = len(embeddings[0])
    if actual_dim != config["embedding_dim"]:
        print(f"Warning: expected dim {config['embedding_dim']}, got {actual_dim}",
              file=sys.stderr)

    # Speichern
    save_parquet(category_ids, embeddings, args.output, config)
    print(f"Written {args.output} ({len(embeddings)} embeddings)", file=sys.stderr)


if __name__ == "__main__":
    main()
