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
import time
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
    load_config,
    strip_ulid_lines,
    update_meta
)
from cli_utils import emit_json, error_result, ms_since, ok_result


def normalize_markdown(text: str) -> str:
    """Entfernt Markdown-Syntax und URLs für sauberere Embeddings.

    - [Text](URL) → Text
    - **bold**, *italic* → Text
    - ## Headings → Headings
    - Mehrfache Whitespace → einzelnes Space
    """
    import re

    text = strip_ulid_lines(text)

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


def extract_text_ranges(source_path: Path, nodes: list[dict[str, Any]], edges: list[dict[str, Any]] | None = None) -> tuple[list[str], list[str]]:
    """Extrahiert Texte aus einem Source-File basierend auf char_start/char_end.

    Filtert nur Nodes vom Typ 'chunk' (nicht 'code' oder 'section').
    Fügt Section-Titel als Kontext hinzu.
    Normalisiert den Text (entfernt Markdown-Syntax).
    Code braucht einen separaten Embedder.

    Returns:
        (texts, chunk_ids): Listen von Texten und zugehörigen chunk IDs
    """
    source_text = source_path.read_text(encoding="utf-8")
    texts = []
    chunk_ids = []

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
            chunk_ids.append(f"unknown_{len(chunk_ids)}")
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
            chunk_ids.append(node["id"])

    return texts, chunk_ids


def filter_oversized_texts(texts: list[str], chunk_ids: list[str], max_tokens: int = 7000) -> tuple[list[str], list[str], list[int]]:
    """Filtert zu große Texte aus und gibt Indices der gefilterten zurück.

    Args:
        texts: Liste von Texten
        chunk_ids: Liste von chunk IDs (parallel zu texts)
        max_tokens: Maximale Token-Anzahl (grobe Schätzung: chars / 4)
                    Default 7000 tokens für jina-embeddings-v2-base-de (~8k context)

    Returns:
        (gefilterte_texte, gefilterte_chunk_ids, indices_der_geskippten)
    """
    filtered_texts = []
    filtered_ids = []
    skipped = []

    max_chars = max_tokens * 4  # Grobe Schätzung: 1 token ≈ 4 chars

    for i, (text, chunk_id) in enumerate(zip(texts, chunk_ids)):
        if len(text) > max_chars:
            print(f"Warning: Skipping text {i} ({chunk_id}) (too large: {len(text)} chars, ~{len(text)//4} tokens)",
                  file=sys.stderr)
            skipped.append(i)
        else:
            filtered_texts.append(text)
            filtered_ids.append(chunk_id)

    return filtered_texts, filtered_ids, skipped


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
    chunk_ids: list[str],
    output_path: Path,
    config: dict[str, Any],
    source: str | None = None,
) -> None:
    """Speichert Embeddings als Parquet mit Metadata."""
    table = pa.table({
        "chunk_idx": chunk_ids,
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
    start = time.perf_counter()
    parser = argparse.ArgumentParser(description="Embed texts to Parquet")
    parser.add_argument("-i", "--input", type=Path, required=True, help="Source Markdown file")
    parser.add_argument("-c", "--config", type=Path, help="config.json path")
    parser.add_argument("--base-dir", type=Path, default=Path(".brain_graph/data"),
                        help="Base data directory (default: .brain_graph/data)")
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
            raise FileNotFoundError(f"Source file not found: {args.input}")

        # Config laden
        config = load_config(args.config)

        # ULID aus Markdown extrahieren
        doc_ulid = extract_ulid_from_md(args.input)
        if not doc_ulid:
            raise ValueError(f"No ULID found in {args.input}. Run chunker.py first.")

        print(f"Document ULID: {doc_ulid}", file=sys.stderr)

        # Output-Pfade finden
        output_paths = get_output_paths(args.input, doc_ulid, args.base_dir)

        # Nodes und Edges laden
        if not output_paths['nodes'].exists():
            raise FileNotFoundError(f"Nodes file not found: {output_paths['nodes']}")

        nodes = json.loads(output_paths['nodes'].read_text(encoding="utf-8"))

        edges = None
        if output_paths['edges'].exists():
            edges = json.loads(output_paths['edges'].read_text(encoding="utf-8"))
            print(f"Loaded {len(edges)} edges", file=sys.stderr)

        # Texte extrahieren
        print(f"Extracting text ranges from {args.input}", file=sys.stderr)
        texts, chunk_ids = extract_text_ranges(args.input, nodes, edges)
        print(f"Extracted {len(texts)} texts", file=sys.stderr)

        if not texts:
            raise ValueError("No texts extracted")

        # Debug: Text-Größen
        sizes = [len(t) for t in texts]
        print(
            f"Text sizes: min={min(sizes)}, max={max(sizes)}, avg={sum(sizes)//len(sizes)}",
            file=sys.stderr,
        )

        # Filter zu große Texte
        texts, chunk_ids, skipped_indices = filter_oversized_texts(texts, chunk_ids)
        if skipped_indices:
            print(f"Skipped {len(skipped_indices)} oversized texts", file=sys.stderr)

        if not texts:
            raise ValueError("No texts remaining after filtering")

        # Embeddings erzeugen
        embeddings = embed_texts(texts, config)

        # Dimension validieren
        actual_dim = len(embeddings[0])
        if actual_dim != config["embedding_dim"]:
            print(f"Warning: expected dim {config['embedding_dim']}, got {actual_dim}", file=sys.stderr)

        # Parquet schreiben
        save_parquet(embeddings, chunk_ids, output_paths['embeddings'], config, args.input.name)
        print(f"Written {output_paths['embeddings']} ({len(embeddings)} embeddings)", file=sys.stderr)

        # Update meta
        update_meta(
            output_paths['meta'],
            {
                "step": "embedding",
                "embedding_count": len(embeddings),
                "model": config["embedding_model"],
                "dim": actual_dim,
            },
        )
        print(f"Updated {output_paths['meta']}", file=sys.stderr)

        result = ok_result(
            "embedder",
            input=str(args.input),
            doc_ulid=doc_ulid,
            output={
                "embeddings": str(output_paths["embeddings"]),
                "meta": str(output_paths["meta"]),
            },
            counts={
                "texts_extracted": len(texts) + len(skipped_indices),
                "texts_embedded": len(embeddings),
                "chunks_embedded": len(chunk_ids),
                "skipped_texts": len(skipped_indices),
            },
            embedding={"model": config.get("embedding_model"), "dim": actual_dim},
            duration_ms=ms_since(start),
        )
        if args.format == "json":
            emit_json(result, pretty=args.pretty)
        return 0
    except Exception as e:
        if args.format == "json":
            emit_json(error_result("embedder", e, include_traceback=args.debug, duration_ms=ms_since(start)), pretty=args.pretty)
            return 1
        raise


if __name__ == "__main__":
    raise SystemExit(main())
