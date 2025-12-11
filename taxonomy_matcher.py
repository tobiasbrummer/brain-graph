#!/usr/bin/env python3
"""
Taxonomy Matcher: Ordnet Chunks via Embedding-Similarity Kategorien zu.

Lädt Chunk-Embeddings + Taxonomy-Embeddings, berechnet Cosine-Similarity,
erstellt Category-Zuordnungen.

Usage:
    python taxonomy_matcher.py -i source.md
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pyarrow.parquet as pq

from file_utils import (
    extract_ulid_from_md,
    get_output_paths
)


def load_embeddings(parquet_path: Path) -> tuple[list[str], np.ndarray]:
    """
    Lädt Embeddings aus Parquet.

    Returns: (ids, embeddings_matrix)
        - ids: Liste von IDs (chunk_idx oder category_id)
        - embeddings_matrix: numpy array (n_items, embedding_dim)
    """
    table = pq.read_table(parquet_path)

    # Chunk embeddings haben chunk_idx, taxonomy hat category_id
    if "chunk_idx" in table.column_names:
        ids = table["chunk_idx"].to_pylist()
    elif "category_id" in table.column_names:
        ids = table["category_id"].to_pylist()
    else:
        raise ValueError(f"No id column found in {parquet_path}")

    # Embeddings sind Listen von Floats
    embeddings_list = table["embedding"].to_pylist()
    embeddings_matrix = np.array(embeddings_list, dtype=np.float32)

    return ids, embeddings_matrix


def cosine_similarity_matrix(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """
    Berechnet Cosine-Similarity zwischen allen Paaren.

    Args:
        a: (n, dim) matrix
        b: (m, dim) matrix

    Returns:
        (n, m) similarity matrix
    """
    # Normalisiere Vektoren
    a_norm = a / np.linalg.norm(a, axis=1, keepdims=True)
    b_norm = b / np.linalg.norm(b, axis=1, keepdims=True)

    # Cosine similarity = dot product of normalized vectors
    similarity = np.dot(a_norm, b_norm.T)

    return similarity


def match_categories(
    chunk_ids: list[int],
    chunk_embeddings: np.ndarray,
    category_ids: list[str],
    category_embeddings: np.ndarray,
    top_n: int = 3,
    min_similarity: float = 0.3,
    max_gap: float | None = None,
    verbose: bool = False,
) -> dict[int, list[tuple[str, float]]]:
    """
    Matched Chunks zu Kategorien via Cosine-Similarity.

    Args:
        max_gap: Wenn gesetzt, werden weitere Kategorien ignoriert, wenn der
                 Abstand zur vorherigen Kategorie größer als max_gap ist.
        verbose: Wenn True, werden Debug-Informationen ausgegeben.

    Returns: Dict[chunk_idx -> [(category_id, similarity), ...]]
    """
    # Berechne Similarity-Matrix (n_chunks, n_categories)
    similarity = cosine_similarity_matrix(chunk_embeddings, category_embeddings)

    matches = {}
    filtered_count = {"by_min_sim": 0, "by_gap": 0}

    for i, chunk_idx in enumerate(chunk_ids):
        # Top-N ähnlichste Kategorien für diesen Chunk
        chunk_similarities = similarity[i]

        # Sortiere nach Similarity
        sorted_indices = np.argsort(chunk_similarities)[::-1][:top_n]

        if verbose and i < 10:  # Zeige erste 10 chunks im Detail
            print(f"\n  Chunk {chunk_idx}:", file=sys.stderr)

        # Filtere nach min_similarity und max_gap
        chunk_matches = []
        prev_sim = None
        for rank, idx in enumerate(sorted_indices):
            sim = float(chunk_similarities[idx])
            cat_id = category_ids[idx]

            # Berechne Gap zur vorherigen Kategorie
            gap = prev_sim - sim if prev_sim is not None else 0.0

            # Prüfe min_similarity
            if sim < min_similarity:
                if verbose and i < 10:
                    print(f"    #{rank+1} {cat_id}: {sim:.3f} [FILTERED: below min_similarity {min_similarity}]", file=sys.stderr)
                filtered_count["by_min_sim"] += 1
                break

            # Prüfe max_gap (Abstand zur vorherigen Kategorie)
            if max_gap is not None and prev_sim is not None:
                if gap > max_gap:
                    if verbose and i < 10:
                        print(f"    #{rank+1} {cat_id}: {sim:.3f} (gap: {gap:.3f}) [FILTERED: gap > {max_gap}]", file=sys.stderr)
                    filtered_count["by_gap"] += 1
                    break

            if verbose and i < 10:
                gap_str = f" (gap: {gap:.3f})" if prev_sim is not None else ""
                print(f"    #{rank+1} {cat_id}: {sim:.3f}{gap_str} ✓", file=sys.stderr)

            chunk_matches.append((cat_id, sim))
            prev_sim = sim

        if chunk_matches:
            matches[chunk_idx] = chunk_matches

    if verbose:
        print(f"\nFiltering stats:", file=sys.stderr)
        print(f"  Filtered by min_similarity: {filtered_count['by_min_sim']}", file=sys.stderr)
        print(f"  Filtered by max_gap: {filtered_count['by_gap']}", file=sys.stderr)

    return matches


def apply_categories(
    nodes: list[dict[str, Any]],
    matches: dict[int, list[tuple[str, float]]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """
    Wendet Category-Matches auf Nodes an.

    Returns: (updated_nodes, category_edges)
    """
    updated_nodes = []
    category_edges = []

    # Erstelle chunk_idx -> node mapping
    chunk_nodes = {}
    for node in nodes:
        if node.get("type") == "chunk":
            # chunk_idx ist die Position in der parquet-datei
            # Wir müssen die gleiche Reihenfolge annehmen
            pass

    # Einfacherer Ansatz: Iteriere durch chunks in Reihenfolge
    chunk_counter = 0
    for node in nodes:
        if node.get("type") != "chunk":
            updated_nodes.append(node)
            continue

        # Dieser Chunk hat chunk_idx = chunk_counter
        if chunk_counter in matches:
            categories = [cat_id for cat_id, sim in matches[chunk_counter]]
            node = {**node, "categories": categories}

            # Erstelle Edges
            for cat_id, similarity in matches[chunk_counter]:
                category_edges.append({
                    "from": node["id"],
                    "to": cat_id,
                    "type": "categorized_as",
                    "weight": int(similarity * 10),  # 0.0-1.0 -> 0-10
                    "similarity": round(similarity, 3),
                })

        updated_nodes.append(node)
        chunk_counter += 1

    return updated_nodes, category_edges


def main():
    parser = argparse.ArgumentParser(description="Match chunks to taxonomy via embeddings")
    parser.add_argument("-i", "--input", type=Path, required=True, help="Source Markdown file")
    parser.add_argument("-t", "--taxonomy", type=Path, default=Path("data/taxonomy.parquet"),
                        help="Taxonomy embeddings parquet")
    parser.add_argument("--base-dir", type=Path, default=Path(".brain_graph/data"),
                        help="Base data directory")
    parser.add_argument("--top-n", type=int, default=2,
                        help="Max categories per chunk")
    parser.add_argument("--min-similarity", type=float, default=0.499,
                        help="Minimum similarity threshold")
    parser.add_argument("--max-gap", type=float, default=0.1,
                        help="Maximum gap between top category and next category")
    parser.add_argument("--verbose", action="store_true",
                        help="Print similarity scores")
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

    # Prüfe ob Embeddings existieren
    if not output_paths['embeddings'].exists():
        print(f"Error: Embeddings not found: {output_paths['embeddings']}", file=sys.stderr)
        print("Run embedder.py first.", file=sys.stderr)
        sys.exit(1)

    if not args.taxonomy.exists():
        print(f"Error: Taxonomy parquet not found: {args.taxonomy}", file=sys.stderr)
        sys.exit(1)

    # Lade Embeddings
    print("Loading embeddings...", file=sys.stderr)
    chunk_ids, chunk_embeddings = load_embeddings(output_paths['embeddings'])
    category_ids, category_embeddings = load_embeddings(args.taxonomy)

    print(f"Loaded {len(chunk_ids)} chunks, {len(category_ids)} categories", file=sys.stderr)

    # Match Categories
    print("Matching categories...", file=sys.stderr)
    if args.verbose:
        print(f"  Parameters: top_n={args.top_n}, min_similarity={args.min_similarity}, max_gap={args.max_gap}", file=sys.stderr)

    matches = match_categories(
        chunk_ids, chunk_embeddings,
        category_ids, category_embeddings,
        top_n=args.top_n,
        min_similarity=args.min_similarity,
        max_gap=args.max_gap,
        verbose=args.verbose,
    )

    print(f"Found matches for {len(matches)} chunks", file=sys.stderr)

    # Lade Nodes
    nodes = json.loads(output_paths['nodes'].read_text(encoding="utf-8"))

    # Apply Categories (inkrementell)
    updated_nodes, category_edges = apply_categories(nodes, matches)

    # Count
    classified = sum(1 for n in updated_nodes if "categories" in n and n["categories"])
    total_assignments = sum(len(n.get("categories", [])) for n in updated_nodes)

    print(f"Classified {classified} chunks with {total_assignments} category assignments", file=sys.stderr)

    # Schreibe nodes.json zurück (in-place update)
    output_paths['nodes'].write_text(
        json.dumps(updated_nodes, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    print(f"Updated {output_paths['nodes']}", file=sys.stderr)

    # Merge category-edges in edges.json
    if output_paths['edges'].exists():
        existing_edges = json.loads(output_paths['edges'].read_text(encoding="utf-8"))
        # Remove old category edges
        existing_edges = [e for e in existing_edges if e.get('type') != 'categorized_as']
        # Add new category edges
        existing_edges.extend(category_edges)
    else:
        existing_edges = category_edges

    output_paths['edges'].write_text(
        json.dumps(existing_edges, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    print(f"Updated {output_paths['edges']} ({len(category_edges)} category edges)", file=sys.stderr)

    # Update meta.json
    if output_paths['meta'].exists():
        meta = json.loads(output_paths['meta'].read_text(encoding="utf-8"))
    else:
        meta = {"processing_steps": []}

    now = datetime.now(timezone.utc)
    meta["modified_at"] = now.isoformat()
    meta["processing_steps"].append({
        "step": "taxonomy_matching",
        "completed": True,
        "timestamp": now.isoformat(),
        "classified_chunks": classified,
        "total_assignments": total_assignments,
        "parameters": {
            "top_n": args.top_n,
            "min_similarity": args.min_similarity,
            "max_gap": args.max_gap
        }
    })

    output_paths['meta'].write_text(
        json.dumps(meta, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    print(f"Updated {output_paths['meta']}", file=sys.stderr)


if __name__ == "__main__":
    main()
