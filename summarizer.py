#!/usr/bin/env python3
"""
Summarizer: Erstellt 1-Satz-Zusammenfassungen für Chunks.

Liest nodes.json, extrahiert Chunk-Texte, generiert Summaries via LLM,
schreibt updated nodes.json.

Usage:
    python summarizer.py input.nodes.json -s source.md -o output.nodes.json
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from openai import OpenAI


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


def load_nodes(path: Path) -> list[dict[str, Any]]:
    """Lädt Nodes aus JSON."""
    return json.loads(path.read_text(encoding="utf-8"))


def extract_chunk_text(node: dict[str, Any], source_text: str) -> str:
    """Extrahiert Chunk-Text aus Source."""
    if node.get("type") != "chunk":
        return ""
    start = node.get("char_start", 0)
    end = node.get("char_end", 0)
    return source_text[start:end].strip()


def generate_summary(text: str, client: OpenAI, model: str) -> str:
    """Generiert 1-Satz-Zusammenfassung via LLM."""
    prompt = f"""Summarize the following text in ONE concise German sentence (max 20 words):

{text}

Summary:"""
    
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=100,
            temperature=0.3,
        )
        
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
    parser = argparse.ArgumentParser(description="Generate summaries for chunks")
    parser.add_argument("input", type=Path, help="Input nodes.json")
    parser.add_argument("-s", "--source", type=Path, required=True, help="Source markdown file")
    parser.add_argument("-o", "--output", type=Path, help="Output nodes.json (default: same as input)")
    parser.add_argument("-c", "--config", type=Path, help="config.json path")
    args = parser.parse_args()

    if not args.input.exists():
        print(f"Error: Input file not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    if not args.source.exists():
        print(f"Error: Source file not found: {args.source}", file=sys.stderr)
        sys.exit(1)

    # Config laden
    config = load_config(args.config)

    # Lade Daten
    nodes = load_nodes(args.input)
    source_text = args.source.read_text(encoding="utf-8")

    chunk_count = sum(1 for n in nodes if n.get("type") == "chunk")
    print(f"Loaded {len(nodes)} nodes ({chunk_count} chunks)", file=sys.stderr)

    # Summarize
    updated_nodes = summarize_chunks(nodes, source_text, config)

    # Output
    output_path = args.output or args.input
    output_path.write_text(
        json.dumps(updated_nodes, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    print(f"Written {output_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
