#!/usr/bin/env python3
"""
Embedder: Texte → Parquet mit Vektoren.

Liest Config aus pyproject.toml, nimmt Texte via stdin oder JSON-File,
gibt Parquet mit Embeddings aus.

Unterstützt zwei Input-Modi:
1. Direkte Texte: JSON-Array mit Strings
2. Nodes mit Ranges: JSON-Array mit Objekten (char_start/char_end)

Usage:
    # Direkte Texte
    echo '["text1", "text2"]' | python embedder.py -o output.parquet
    python embedder.py -i texts.json -o output.parquet

    # Nodes mit Ranges (source wird automatisch abgeleitet)
    python embedder.py -i Jazz.md.nodes.json -o output.parquet

    # Nodes mit Ranges (expliziter source)
    python embedder.py -i nodes.json -s source.md -o output.parquet
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

from file_utils import (
    extract_ulid_from_md,
    get_output_paths,
    ensure_output_dirs,
    update_meta
)


def load_config(config_path: Path | None = None) -> dict[str, Any]:
    """Lädt Config aus config.json, mit Defaults."""
    defaults = {
        "embedding_base_url": "http://localhost:8200/v1",
        "embedding_model": "jina-embeddings-v2-base-de",
        "embedding_dim": 768,
        "embedding_api_key": "unused",
        "embedding_batch_size": 1,
    }

    # Suche config.json
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


def normalize_markdown(text: str) -> str:
    """Entfernt Markdown-Syntax und URLs für sauberere Embeddings.

    - [Text](URL) → Text
    - **bold**, *italic* → Text
    - ## Headings → Headings
    - Mehrfache Whitespace → einzelnes Space
    """
    import re

    # Markdown-Links: [Text](URL) → Text
    text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)

    # Bold und Italic
    text = re.sub(r'\*\*([^\*]+)\*\*', r'\1', text)  # **bold**
    text = re.sub(r'\*([^\*]+)\*', r'\1', text)      # *italic*
    text = re.sub(r'__([^_]+)__', r'\1', text)       # __bold__
    text = re.sub(r'_([^_]+)_', r'\1', text)         # _italic_

    # Heading-Marker entfernen (## → "")
    text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)

    # Code-Backticks entfernen
    text = re.sub(r'`([^`]+)`', r'\1', text)

    # Mehrfache Whitespace normalisieren
    text = re.sub(r'\s+', ' ', text)

    return text.strip()


def extract_text_ranges(source_path: Path, nodes: list[dict[str, Any]], edges: list[dict[str, Any]] | None = None) -> list[str]:
    """Extrahiert Texte aus einem Source-File basierend auf char_start/char_end.

    Filtert nur Nodes vom Typ 'chunk' (nicht 'code' oder 'section').
    Fügt Section-Titel als Kontext hinzu.
    Normalisiert den Text (entfernt Markdown-Syntax).
    Code braucht einen separaten Embedder.
    """
    source_text = source_path.read_text(encoding="utf-8")
    texts = []

    # Erstelle Mapping: node_id -> node für schnellen Zugriff
    node_map = {n["id"]: n for n in nodes if isinstance(n, dict)}

    # Erstelle Mapping: chunk_id -> section_id aus 'contains' edges
    chunk_to_section = {}
    if edges:
        for edge in edges:
            if edge.get("type") == "contains":
                chunk_to_section[edge["to"]] = edge["from"]

    for node in nodes:
        # Nur chunk Nodes embedden - nicht code, nicht sections
        if not isinstance(node, dict):
            texts.append(str(node))
            continue

        node_type = node.get("type", "")
        if node_type != "chunk":
            continue

        if "char_start" not in node or "char_end" not in node:
            continue

        start = node["char_start"]
        end = node["char_end"]
        text = source_text[start:end].strip()

        # Markdown normalisieren
        text = normalize_markdown(text)

        # Section-Titel als Kontext hinzufügen
        section_id = chunk_to_section.get(node["id"])
        if section_id and section_id in node_map:
            section_node = node_map[section_id]
            section_title = section_node.get("title", "")
            if section_title:
                # Normalisiere auch den Titel
                section_title = normalize_markdown(section_title)
                text = f"{section_title}: {text}"

        if text:  # Nur nicht-leere Texte
            # WICHTIG: Präfix für Jina v3 / asymmetrische Suche hinzufügen
            text = f"Passage: {text}"
            texts.append(text)

    return texts


def filter_oversized_texts(texts: list[str], max_tokens: int = 7000) -> tuple[list[str], list[int]]:
    """Filtert zu große Texte aus und gibt Indices der gefilterten zurück.

    Args:
        texts: Liste von Texten
        max_tokens: Maximale Token-Anzahl (grobe Schätzung: chars / 4)
                    Default 7000 tokens für jina-embeddings-v2-base-de (~8k context)

    Returns:
        (gefilterte_texte, indices_der_geskippten)
    """
    filtered = []
    skipped = []

    max_chars = max_tokens * 4  # Grobe Schätzung: 1 token ≈ 4 chars

    for i, text in enumerate(texts):
        if len(text) > max_chars:
            print(f"Warning: Skipping text {i} (too large: {len(text)} chars, ~{len(text)//4} tokens)",
                  file=sys.stderr)
            skipped.append(i)
        else:
            filtered.append(text)

    return filtered, skipped


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
        print(f"Embedding batch {batch}, {i//batch_size + 1}/{(len(texts)-1)//batch_size + 1}...\n\n", file=sys.stderr)
        response = client.embeddings.create(
            input=batch,
            model=config["embedding_model"],
        )
        # Sortiere nach Index, falls API sie unsortiert zurückgibt
        batch_embeddings = sorted(response.data, key=lambda x: x.index)
        embeddings.extend([e.embedding for e in batch_embeddings])

    return embeddings


def save_parquet(
    embeddings: list[list[float]],
    output_path: Path,
    config: dict[str, Any],
    source: str | None = None,
) -> None:
    """Speichert Embeddings als Parquet mit Metadata."""
    table = pa.table({
        "chunk_idx": list(range(len(embeddings))),
        "embedding": embeddings,
    })
    
    # Metadata
    metadata = {
        b"model": config["embedding_model"].encode(),
        b"dim": str(config["embedding_dim"]).encode(),
        b"created_at": datetime.now(timezone.utc).isoformat().encode(),
    }
    if source:
        metadata[b"source"] = source.encode()
    
    # Merge mit existierenden Schema-Metadata
    existing = table.schema.metadata or {}
    table = table.replace_schema_metadata({**existing, **metadata})
    
    pq.write_table(table, output_path, compression="zstd")


def main():
    parser = argparse.ArgumentParser(description="Embed texts to Parquet")
    parser.add_argument("-i", "--input", type=Path, required=True, help="Source Markdown file")
    parser.add_argument("-c", "--config", type=Path, help="config.json path")
    parser.add_argument("--base-dir", type=Path, default=Path(".brain_graph/data"),
                        help="Base data directory (default: .brain_graph/data)")
    args = parser.parse_args()

    if not args.input.exists():
        print(f"Error: Source file not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    # Config laden
    config = load_config(args.config)

    # ULID aus Markdown extrahieren
    doc_ulid = extract_ulid_from_md(args.input)
    if not doc_ulid:
        print(f"Error: No ULID found in {args.input}. Run chunker.py first.", file=sys.stderr)
        sys.exit(1)

    print(f"Document ULID: {doc_ulid}", file=sys.stderr)

    # Output-Pfade finden
    output_paths = get_output_paths(args.input, doc_ulid, args.base_dir)

    # Nodes und Edges laden
    if not output_paths['nodes'].exists():
        print(f"Error: Nodes file not found: {output_paths['nodes']}", file=sys.stderr)
        print("Run chunker.py first.", file=sys.stderr)
        sys.exit(1)

    nodes = json.loads(output_paths['nodes'].read_text(encoding="utf-8"))

    edges = None
    if output_paths['edges'].exists():
        edges = json.loads(output_paths['edges'].read_text(encoding="utf-8"))
        print(f"Loaded {len(edges)} edges", file=sys.stderr)

    # Texte extrahieren
    print(f"Extracting text ranges from {args.input}", file=sys.stderr)
    texts = extract_text_ranges(args.input, nodes, edges)
    print(f"Extracted {len(texts)} texts", file=sys.stderr)

    if not texts:
        print("No texts extracted", file=sys.stderr)
        sys.exit(1)

    # Debug: Text-Größen
    sizes = [len(t) for t in texts]
    print(f"Text sizes: min={min(sizes)}, max={max(sizes)}, avg={sum(sizes)//len(sizes)}", file=sys.stderr)

    # Filter zu große Texte
    texts, skipped_indices = filter_oversized_texts(texts)
    if skipped_indices:
        print(f"Skipped {len(skipped_indices)} oversized texts", file=sys.stderr)

    if not texts:
        print("No texts remaining after filtering", file=sys.stderr)
        sys.exit(1)

    # Embeddings erzeugen
    embeddings = embed_texts(texts, config)

    # Dimension validieren
    actual_dim = len(embeddings[0])
    if actual_dim != config["embedding_dim"]:
        print(f"Warning: expected dim {config['embedding_dim']}, got {actual_dim}",
              file=sys.stderr)

    # Parquet schreiben
    save_parquet(embeddings, output_paths['embeddings'], config, args.input.name)
    print(f"Written {output_paths['embeddings']} ({len(embeddings)} embeddings)", file=sys.stderr)

    # meta.json updaten
    if output_paths['meta'].exists():
        meta = json.loads(output_paths['meta'].read_text(encoding="utf-8"))
    else:
        meta = {
            "source_file": args.input.name,
            "ulid": doc_ulid,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "uses": 1,
            "importance": None,
            "decay": None,
            "categories": [],
            "processing_steps": []
        }

    # Update meta
    update_meta(output_paths['meta'], {
        "step": "embedding",
        "embedding_count": len(embeddings),
        "model": config["embedding_model"],
        "dim": actual_dim
    })
    print(f"Updated {output_paths['meta']}", file=sys.stderr)


if __name__ == "__main__":
    main()