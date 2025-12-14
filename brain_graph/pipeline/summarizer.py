#!/usr/bin/env python3
"""
Summarizer: Erstellt 1-Satz-Zusammenfassungen für Chunks.

Liest nodes.json, extrahiert Chunk-Texte, generiert Summaries via LLM,
schreibt updated nodes.json.

Usage:
    python summarizer.py -i vault/YYYY-MM/file.md
"""

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

from openai import OpenAI

from file_utils import extract_ulid_from_md, get_output_paths, strip_ulid_lines, update_meta, load_config
from cli_utils import emit_json, error_result, ms_since, ok_result


def load_config(config_path: Path | None = None) -> dict[str, Any]:
    """Lädt Config aus config.json."""
    defaults = {
        "summary_base_url": "http://localhost:8100/v1",
        "summary_model": "mistral-7b-instruct",
        "summary_api_key": "unused",
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


def extract_chunk_text(node: dict[str, Any], source_text: str) -> str:
    """Extrahiert Chunk-Text aus Source."""
    if node.get("type") != "chunk":
        return ""
    start = node.get("char_start", 0)
    end = node.get("char_end", 0)
    return strip_ulid_lines(source_text[start:end]).strip()


def generate_summary(text: str, client: OpenAI, model: str) -> str:
    """Generiert 1-Satz-Zusammenfassung via LLM."""
    prompt = f"""Summarize the following text in ONE concise German sentence (max 20 words):

{text}

Summary:"""

    print(f"Generating summary... {prompt}", file=sys.stderr)

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=100,
            temperature=0.3,
        )
        print(f"LLM response: {response}", file=sys.stderr)
        summary = response.choices[0].message.content.strip()
        return summary
    except Exception as e:
        print(f"Error generating summary: {e}", file=sys.stderr)
        return ""


def summarize_chunks(
    nodes: list[dict[str, Any]],
    source_text: str,
    config: dict[str, Any],
) -> list[dict[str, Any]]:
    """
    Erstellt Summaries für alle Chunks.

    Returns: updated_nodes
    """
    client = OpenAI(
        base_url=config["summary_base_url"],
        api_key=config["summary_api_key"],
    )

    updated_nodes = []
    chunk_count = 0

    for i, node in enumerate(nodes):
        if node.get("type") != "chunk":
            updated_nodes.append(node)
            continue

        # Extrahiere Text
        text = extract_chunk_text(node, source_text)
        if not text:
            updated_nodes.append(node)
            continue

        # Generiere Summary
        print(f"Summarizing chunk {i+1}...", file=sys.stderr)
        summary = generate_summary(text, client, config["summary_model"])

        if summary:
            node = {**node, "summary": summary}
            chunk_count += 1

        updated_nodes.append(node)

    print(f"Generated {chunk_count} summaries", file=sys.stderr)
    return updated_nodes


def main():
    start = time.perf_counter()
    parser = argparse.ArgumentParser(description="Generate summaries for chunks")
    parser.add_argument(
        "-i", "--input", type=Path, required=True, help="Source Markdown file"
    )
    parser.add_argument(
        "--base-dir",
        type=Path,
        default=Path(".brain_graph/data"),
        help="Base data directory",
    )
    parser.add_argument(
        "-c",
        "--config",
        type=Path,
        help="config.json path",
        default=Path(".brain_graph/config/config.json"),
    )
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

        # ULID extrahieren
        doc_ulid = extract_ulid_from_md(args.input)
        if not doc_ulid:
            raise ValueError(f"No ULID found in {args.input}")

        # Pfade ermitteln
        output_paths = get_output_paths(args.input, doc_ulid, args.base_dir)

        if not output_paths["nodes"].exists():
            raise FileNotFoundError(f"Nodes file not found: {output_paths['nodes']} (run chunker.py first)")

        # Config laden
        config = load_config(args.config)

        # Lade Daten
        nodes = json.loads(output_paths["nodes"].read_text(encoding="utf-8"))
        source_text = args.input.read_text(encoding="utf-8")

        chunk_count = sum(1 for n in nodes if n.get("type") == "chunk")
        print(f"Loaded {len(nodes)} nodes ({chunk_count} chunks)", file=sys.stderr)

        # Summarize
        updated_nodes = summarize_chunks(nodes, source_text, config)

        # Schreibe nodes.json zurück (in-place update)
        output_paths["nodes"].write_text(
            json.dumps(updated_nodes, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"Updated {output_paths['nodes']}", file=sys.stderr)

        # Update meta.json
        summary_count = sum(
            1 for n in updated_nodes if n.get("type") == "chunk" and n.get("summary")
        )
        update_meta(
            output_paths["meta"],
            {
                "step": "summarization",
                "summary_count": summary_count,
                "model": config["summary_model"],
            },
        )
        print(f"Updated {output_paths['meta']}", file=sys.stderr)

        result = ok_result(
            "summarizer",
            input=str(args.input),
            doc_ulid=doc_ulid,
            output={"nodes": str(output_paths["nodes"]), "meta": str(output_paths["meta"])},
            counts={"summaries": summary_count, "chunks": chunk_count},
            model=config.get("summary_model"),
            duration_ms=ms_since(start),
        )
        if args.format == "json":
            emit_json(result, pretty=args.pretty)
        return 0
    except Exception as e:
        if args.format == "json":
            emit_json(error_result("summarizer", e, include_traceback=args.debug, duration_ms=ms_since(start)), pretty=args.pretty)
            return 1
        raise


if __name__ == "__main__":
    raise SystemExit(main())
