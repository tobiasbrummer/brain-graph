#!/usr/bin/env python3
"""
Code Embedder: Code Units (functions/classes/methods) → Parquet mit Vektoren.

Liest eine Markdown-Datei mit Code-Blöcken, lädt die dazugehörigen
`*.nodes.json` Dateien aus `.brain_graph/data/`, extrahiert Code-Units
(Funktionen, Klassen, Methoden) und schreibt ein Parquet mit Embeddings.

Config:
    `.brain_graph/config/config.json` (oder `config.json` fallback)

Usage:
    brain pipeline code-embed vault/YYYY-MM/file.md
    python -m brain_graph.pipeline.code_embedder -i vault/YYYY-MM/file.md
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

from brain_graph.utils.embedding_client import embed_batch
from brain_graph.utils.file_utils import (
    extract_ulid_from_md,
    get_output_paths,
    ensure_output_dirs,
    load_config,
    update_meta
)
from brain_graph.utils.cli_utils import emit_json, error_result, ms_since, ok_result


def extract_code_ranges(source_path: Path, nodes: list[dict[str, Any]]) -> tuple[list[str], list[str]]:
    """Extrahiert Code aus Funktionen/Klassen/Methoden basierend auf char_start/char_end.

    Filtert nur Nodes vom Typ 'function', 'class', oder 'method'.
    Fügt Signature und Docstring als Kontext hinzu.

    Returns:
        (code_texts, code_ids): Listen von Code-Texten und zugehörigen code IDs
    """
    source_text = source_path.read_text(encoding="utf-8")
    code_texts = []
    code_ids = []

    for node in nodes:
        if not isinstance(node, dict):
            continue

        node_type = node.get("type", "")
        if node_type not in ["function", "class", "method"]:
            continue

        if "char_start" not in node or "char_end" not in node:
            continue

        start = node["char_start"]
        end = node["char_end"]
        code = source_text[start:end].strip()

        # Kontext: Signature + Docstring
        signature = node.get("signature", "")
        docstring = node.get("docstring", "")
        name = node.get("name", "")
        language = node.get("language", "")

        # Build context
        context_parts = []
        if signature:
            context_parts.append(signature)
        if docstring:
            context_parts.append(docstring)
        context_parts.append(code)

        context = "\n".join(context_parts)

        if context:
            # WICHTIG: Präfix für asymmetrische Suche (Code-spezifisch)
            context = f"Code: {context}"
            code_texts.append(context)
            code_ids.append(node["id"])

    return code_texts, code_ids


def filter_oversized_texts(texts: list[str], code_ids: list[str], max_tokens: int = 7000) -> tuple[list[str], list[str], list[int]]:
    """Filtert zu große Code-Texte aus und gibt Indices der gefilterten zurück.

    Args:
        texts: Liste von Code-Texten
        code_ids: Liste von code IDs (parallel zu texts)
        max_tokens: Maximale Token-Anzahl (grobe Schätzung: chars / 4)

    Returns:
        (gefilterte_texte, gefilterte_code_ids, indices_der_geskippten)
    """
    filtered_texts = []
    filtered_ids = []
    skipped = []

    max_chars = max_tokens * 4  # Grobe Schätzung: 1 token ≈ 4 chars

    for i, (text, code_id) in enumerate(zip(texts, code_ids)):
        if len(text) > max_chars:
            print(f"Warning: Skipping code unit {i} ({code_id}) (too large: {len(text)} chars, ~{len(text)//4} tokens)",
                  file=sys.stderr)
            skipped.append(i)
        else:
            filtered_texts.append(text)
            filtered_ids.append(code_id)

    return filtered_texts, filtered_ids, skipped


def embed_code(texts: list[str], config: dict[str, Any]) -> list[list[float]]:
    """Embedded Code-Texte via OpenAI-kompatible API (mit Batch-Support)."""
    batch_size = config.get("code_embedding_batch_size", config.get("embedding_batch_size", 32))
    total_batches = (len(texts) - 1) // batch_size + 1

    print(f"Embedding {len(texts)} code units in {total_batches} batches...", file=sys.stderr)

    # Use code-specific config
    code_config = config.copy()
    code_config["embedding_model"] = config["code_embedding_model"]
    code_config["embedding_base_url"] = config.get("code_embedding_base_url", config.get("embedding_base_url"))
    code_config["embedding_api_key"] = config.get("code_embedding_api_key", config.get("embedding_api_key"))
    code_config["embedding_batch_size"] = batch_size

    return embed_batch(texts, code_config)


def save_parquet(
    embeddings: list[list[float]],
    code_ids: list[str],
    output_path: Path,
    config: dict[str, Any],
    source: str | None = None,
) -> None:
    """Speichert Code-Embeddings als Parquet mit Metadata."""
    table = pa.table({
        "code_idx": code_ids,
        "embedding": embeddings,
    })

    # Metadata
    actual_dim = len(embeddings[0]) if embeddings else 0
    metadata = {
        b"model": config["code_embedding_model"].encode(),
        b"dim": str(actual_dim).encode(),
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
    parser = argparse.ArgumentParser(description="Embed code units to Parquet")
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

        # Check for code_embedding_model
        if "code_embedding_model" not in config:
            raise ValueError("Missing 'code_embedding_model' in config. Add code embedding model configuration.")

        # ULID aus Markdown extrahieren
        doc_ulid = extract_ulid_from_md(args.input)
        if not doc_ulid:
            raise ValueError(f"No ULID found in {args.input}. Run chunker.py first.")

        print(f"Document ULID: {doc_ulid}", file=sys.stderr)

        # Output-Pfade finden
        output_paths = get_output_paths(args.input, doc_ulid, args.base_dir)

        # Nodes laden
        if not output_paths['nodes'].exists():
            raise FileNotFoundError(f"Nodes file not found: {output_paths['nodes']}")

        nodes = json.loads(output_paths['nodes'].read_text(encoding="utf-8"))
        print(f"Loaded {len(nodes)} nodes", file=sys.stderr)

        # Code-Texte extrahieren
        code_texts, code_ids = extract_code_ranges(args.input, nodes)
        print(f"Extracted {len(code_texts)} code units", file=sys.stderr)

        if not code_texts:
            print("No code units found - nothing to embed", file=sys.stderr)
            emit_json(ok_result(
                tool="code_embedder",
                output={"code_count": 0, "embedded_count": 0},
                duration_ms=ms_since(start)
            ), args.format, args.pretty)
            return 0

        # Oversized filtern
        code_texts, code_ids, skipped = filter_oversized_texts(code_texts, code_ids)
        if skipped:
            print(f"Skipped {len(skipped)} oversized code units", file=sys.stderr)

        if not code_texts:
            print("All code units oversized - nothing to embed", file=sys.stderr)
            emit_json(ok_result(
                tool="code_embedder",
                output={"code_count": len(code_ids) + len(skipped), "embedded_count": 0, "skipped_count": len(skipped)},
                duration_ms=ms_since(start)
            ), args.format, args.pretty)
            return 0

        # Embeddings erstellen
        embeddings = embed_code(code_texts, config)
        print(f"Created {len(embeddings)} embeddings", file=sys.stderr)

        # Output directories sicherstellen
        ensure_output_dirs(output_paths)

        # Parquet speichern (.code.parquet)
        code_parquet_path = output_paths['embeddings_parquet'].parent / f"{output_paths['embeddings_parquet'].stem}.code.parquet"
        save_parquet(embeddings, code_ids, code_parquet_path, config, source=str(args.input))
        print(f"Saved embeddings to {code_parquet_path}", file=sys.stderr)

        # Meta-Update
        update_meta(
            output_paths['meta'],
            {
                "step": "code_embedding",
                "code_embedding_count": len(embeddings),
                "code_model": config["code_embedding_model"],
                "code_dim": len(embeddings[0]) if embeddings else 0,
            }
        )

        emit_json(ok_result(
            tool="code_embedder",
            output={
                "code_count": len(code_texts) + len(skipped),
                "embedded_count": len(embeddings),
                "skipped_count": len(skipped),
                "output_file": str(code_parquet_path),
            },
            counts={"code_units": len(code_texts), "embeddings": len(embeddings)},
            duration_ms=ms_since(start)
        ), args.format, args.pretty)

        return 0

    except Exception as e:
        emit_json(error_result(
            tool="code_embedder",
            error=e,
            duration_ms=ms_since(start),
            include_traceback=args.debug
        ), args.format, args.pretty)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
