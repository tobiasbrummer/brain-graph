#!/usr/bin/env python3
"""
LLM Verifier: Verifiziert Embedding-basierte Kategorisierung via LLM.

Nimmt Embedding-Ergebnisse und lässt ein LLM die Kategorien überprüfen.
Entfernt False Positives und kann fehlende Kategorien ergänzen.

Usage:
    python llm_verifier.py -i vault/YYYY-MM/file.md
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from openai import OpenAI

from file_utils import (
    extract_ulid_from_md,
    get_output_paths,
    update_meta
)


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


def normalize_markdown(text: str) -> str:
    """Entfernt Markdown-Syntax."""
    import re
    text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
    text = re.sub(r'\*\*([^\*]+)\*\*', r'\1', text)
    text = re.sub(r'\*([^\*]+)\*', r'\1', text)
    text = re.sub(r'__([^_]+)__', r'\1', text)
    text = re.sub(r'_([^_]+)_', r'\1', text)
    text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'`([^`]+)`', r'\1', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def extract_chunk_text(
    chunk_id: str,
    source_path: Path,
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]]
) -> str:
    """Extrahiert Chunk-Text mit Section-Kontext."""
    source_text = source_path.read_text(encoding="utf-8")

    # Finde Chunk-Node
    node_map = {n["id"]: n for n in nodes if isinstance(n, dict)}
    chunk_node = node_map.get(chunk_id)

    if not chunk_node or chunk_node.get("type") != "chunk":
        return ""

    # Extrahiere Text
    start = chunk_node.get("char_start", 0)
    end = chunk_node.get("char_end", 0)
    text = source_text[start:end].strip()
    text = normalize_markdown(text)

    # Section-Titel hinzufügen
    chunk_to_section = {}
    for edge in edges:
        if edge.get("type") == "contains":
            chunk_to_section[edge["to"]] = edge["from"]

    section_id = chunk_to_section.get(chunk_id)
    if section_id and section_id in node_map:
        section_node = node_map[section_id]
        section_title = section_node.get("title", "")
        if section_title:
            section_title = normalize_markdown(section_title)
            text = f"{section_title}: {text}"

    return text


def verify_categories(
    text: str,
    current_categories: list[str],
    all_categories: list[dict[str, Any]],
    client: OpenAI,
    model: str,
) -> list[str]:
    """Verifiziert Kategorien via LLM.

    Returns: Liste von verifizierten category_ids
    """
    if not current_categories:
        return []

    # Erstelle Category-Infos für Prompt
    cat_map = {cat["id"]: cat for cat in all_categories}
    current_cat_info = []
    for cat_id in current_categories:
        if cat_id in cat_map:
            cat = cat_map[cat_id]
            desc = cat.get("description", "")[:50]
            current_cat_info.append(f"- {cat_id}: {desc}")

    cat_info_str = "\n".join(current_cat_info)

    prompt = f"""Überprüfe ob die Kategorien zum Text passen.

Text (erste 400 Zeichen):
{text[:400]}

Zugeordnete Kategorien:
{cat_info_str}

Welche Kategorien passen WIRKLICH? Antworte NUR mit den passenden IDs (komma-getrennt) oder "none".
"""

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=100,
            temperature=0.1,
        )

        message = response.choices[0].message
        result = (message.content or "").strip().lower()

        if not result or result == "none":
            return []

        # Parse category IDs
        verified_ids = [c.strip() for c in result.split(",")]

        # Validiere gegen current_categories
        verified_ids = [c for c in verified_ids if c in current_categories]

        return verified_ids

    except Exception as e:
        print(f"Error verifying categories: {e}", file=sys.stderr)
        # Bei Fehler: behalte Original-Kategorien
        return current_categories


def apply_verified_categories(
    nodes: list[dict[str, Any]],
    verified_categories: dict[str, list[str]]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Wendet verifizierte Kategorien auf Nodes an.

    Returns: (updated_nodes, category_edges)
    """
    updated_nodes = []
    category_edges = []

    for node in nodes:
        if node.get("type") == "chunk" and node["id"] in verified_categories:
            categories = verified_categories[node["id"]]

            # Wenn Kategorien vorhanden, setze sie; sonst entferne das Feld
            if categories:
                node = {**node, "categories": categories}

                # Erstelle Edges
                for cat_id in categories:
                    category_edges.append({
                        "from": node["id"],
                        "to": cat_id,
                        "type": "categorized_as",
                        "weight": 6,  # Höherer Wert für LLM-verifizierte Kategorien
                    })
            else:
                # Alle Kategorien entfernt - entferne categories-Feld
                node = {k: v for k, v in node.items() if k != "categories"}

        updated_nodes.append(node)

    return updated_nodes, category_edges


def main():
    parser = argparse.ArgumentParser(description="Verify embedding-based categories via LLM")
    parser.add_argument("-i", "--input", type=Path, required=True, help="Source Markdown file")
    parser.add_argument("-t", "--taxonomy", type=Path, default=Path(".brain_graph/config/taxonomy.md.nodes.json"),
                        help="Taxonomy nodes.json")
    parser.add_argument("--base-dir", type=Path, default=Path(".brain_graph/data"),
                        help="Base data directory")
    parser.add_argument("-c", "--config", type=Path, help="config.json path", default=Path(".brain_graph/config/config.json"))
    args = parser.parse_args()

    if not args.input.exists():
        print(f"Error: Source file not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    # ULID extrahieren
    doc_ulid = extract_ulid_from_md(args.input)
    if not doc_ulid:
        print(f"Error: No ULID found in {args.input}", file=sys.stderr)
        sys.exit(1)

    # Pfade ermitteln
    output_paths = get_output_paths(args.input, doc_ulid, args.base_dir)

    if not output_paths['nodes'].exists():
        print(f"Error: Nodes file not found: {output_paths['nodes']}", file=sys.stderr)
        print("Run chunker.py and taxonomy_matcher.py first.", file=sys.stderr)
        sys.exit(1)

    if not args.taxonomy.exists():
        print(f"Error: Taxonomy file not found: {args.taxonomy}", file=sys.stderr)
        sys.exit(1)

    # Config laden
    config = load_config(args.config)

    # LLM Client
    client = OpenAI(
        base_url=config["summary_base_url"],
        api_key=config["summary_api_key"],
    )

    # Lade Daten
    print("Loading data...", file=sys.stderr)
    nodes = json.loads(output_paths['nodes'].read_text(encoding="utf-8"))
    categories = json.loads(args.taxonomy.read_text(encoding="utf-8"))

    # Lade Edges
    edges = []
    if output_paths['edges'].exists():
        edges = json.loads(output_paths['edges'].read_text(encoding="utf-8"))

    print(f"Loaded {len(nodes)} nodes, {len(categories)} categories", file=sys.stderr)

    # Sammle Chunks mit Kategorien
    chunks_with_categories = []
    for node in nodes:
        if node.get("type") == "chunk" and node.get("categories"):
            chunks_with_categories.append((node["id"], node["categories"]))

    if not chunks_with_categories:
        print("Warning: No chunks with categories found. Run taxonomy_matcher.py first.", file=sys.stderr)
        sys.exit(0)

    print(f"Found {len(chunks_with_categories)} chunks with categories", file=sys.stderr)

    # Verifiziere Kategorien
    print("Verifying categories via LLM...", file=sys.stderr)
    verified_categories = {}

    for i, (chunk_id, current_cats) in enumerate(chunks_with_categories, 1):
        print(f"  {i}/{len(chunks_with_categories)}: {chunk_id} ({len(current_cats)} cats)", file=sys.stderr)

        # Extrahiere Text
        text = extract_chunk_text(chunk_id, args.input, nodes, edges)
        if not text:
            print(f"    Warning: No text for {chunk_id}", file=sys.stderr)
            verified_categories[chunk_id] = current_cats
            continue

        # Verifiziere
        verified = verify_categories(text, current_cats, categories, client, config["summary_model"])

        if len(verified) < len(current_cats):
            removed = set(current_cats) - set(verified)
            print(f"    Removed: {removed}", file=sys.stderr)

        verified_categories[chunk_id] = verified

    print(f"Verified {len(verified_categories)} chunks", file=sys.stderr)

    # Stats
    original_count = sum(len(cats) for _, cats in chunks_with_categories)
    verified_count = sum(len(cats) for cats in verified_categories.values())
    removed_count = original_count - verified_count

    print(f"Original: {original_count} assignments", file=sys.stderr)
    print(f"Verified: {verified_count} assignments", file=sys.stderr)
    print(f"Removed: {removed_count} false positives", file=sys.stderr)

    # Apply verified categories (in-place update)
    updated_nodes, category_edges = apply_verified_categories(nodes, verified_categories)

    # Schreibe nodes.json zurück
    output_paths['nodes'].write_text(
        json.dumps(updated_nodes, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    print(f"Updated {output_paths['nodes']}", file=sys.stderr)

    # Merge category-edges in edges.json (remove old, add new)
    if output_paths['edges'].exists():
        existing_edges = json.loads(output_paths['edges'].read_text(encoding="utf-8"))
        existing_edges = [e for e in existing_edges if e.get('type') != 'categorized_as']
        existing_edges.extend(category_edges)
    else:
        existing_edges = category_edges

    output_paths['edges'].write_text(
        json.dumps(existing_edges, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    print(f"Updated {output_paths['edges']}", file=sys.stderr)

    # Update meta.json
    update_meta(output_paths['meta'], {
        "step": "llm_verification",
        "original_assignments": original_count,
        "verified_assignments": verified_count,
        "removed_false_positives": removed_count,
        "model": config["summary_model"]
    })
    print(f"Updated {output_paths['meta']}", file=sys.stderr)


if __name__ == "__main__":
    main()
