#!/usr/bin/env python3
"""
Taxonomy Matcher: Ordnet Chunks via Embedding-Similarity Kategorien zu.

Lädt Chunk-Embeddings + Taxonomy-Embeddings, berechnet Cosine-Similarity,
erstellt Category-Zuordnungen.

Usage:
    python taxonomy_matcher.py chunks.parquet -t taxonomy.parquet -n nodes.json
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pyarrow.parquet as pq


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
) -> dict[int, list[tuple[str, float]]]:
    """
    Matched Chunks zu Kategorien via Cosine-Similarity.

    Returns: Dict[chunk_idx -> [(category_id, similarity), ...]]
    """
    # Berechne Similarity-Matrix (n_chunks, n_categories)
    similarity = cosine_similarity_matrix(chunk_embeddings, category_embeddings)

    matches = {}
    for i, chunk_idx in enumerate(chunk_ids):
        # Top-N ähnlichste Kategorien für diesen Chunk
        chunk_similarities = similarity[i]

        # Sortiere nach Similarity
        sorted_indices = np.argsort(chunk_similarities)[::-1][:top_n]

        # Filtere nach min_similarity
        chunk_matches = []
        for idx in sorted_indices:
            sim = float(chunk_similarities[idx])
            if sim >= min_similarity:
                chunk_matches.append((category_ids[idx], sim))

        if chunk_matches:
            matches[chunk_idx] = chunk_matches

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
    parser.add_argument("chunks_parquet", type=Path, help="Chunk embeddings parquet")
    parser.add_argument("-t", "--taxonomy", type=Path, default=Path("taxonomy.parquet"),
                        help="Taxonomy embeddings parquet")
    parser.add_argument("-n", "--nodes", type=Path, required=True,
                        help="Input nodes.json")
    parser.add_argument("-o", "--output-prefix", type=Path,
                        help="Output prefix (default: same as nodes)")
    parser.add_argument("--top-n", type=int, default=2,
                        help="Max categories per chunk")
    parser.add_argument("--min-similarity", type=float, default=0.499,
                        help="Minimum similarity threshold")
    parser.add_argument("--verbose", action="store_true",
                        help="Print similarity scores for each match")
    args = parser.parse_args()

    if not args.chunks_parquet.exists():
        print(f"Error: Chunks parquet not found: {args.chunks_parquet}", file=sys.stderr)
        sys.exit(1)

    if not args.taxonomy.exists():
        print(f"Error: Taxonomy parquet not found: {args.taxonomy}", file=sys.stderr)
        sys.exit(1)

    if not args.nodes.exists():
        print(f"Error: Nodes file not found: {args.nodes}", file=sys.stderr)
        sys.exit(1)

    # Lade Embeddings
    print("Loading embeddings...", file=sys.stderr)
    chunk_ids, chunk_embeddings = load_embeddings(args.chunks_parquet)
    category_ids, category_embeddings = load_embeddings(args.taxonomy)

    print(f"Loaded {len(chunk_ids)} chunks, {len(category_ids)} categories", file=sys.stderr)

    # Match Categories
    print("Matching categories...", file=sys.stderr)
    matches = match_categories(
        chunk_ids, chunk_embeddings,
        category_ids, category_embeddings,
        top_n=args.top_n,
        min_similarity=args.min_similarity,
    )

    print(f"Found matches for {len(matches)} chunks", file=sys.stderr)

    # Verbose output
    if args.verbose:
        print("\nTop matches per chunk:", file=sys.stderr)
        for chunk_idx, chunk_matches in sorted(matches.items())[:10]:  # Zeige erste 10
            print(f"  Chunk {chunk_idx}:", file=sys.stderr)
            for cat_id, sim in chunk_matches:
                print(f"    {cat_id}: {sim:.3f}", file=sys.stderr)

    # Lade Nodes
    nodes = json.loads(args.nodes.read_text(encoding="utf-8"))

    # Apply Categories
    updated_nodes, category_edges = apply_categories(nodes, matches)

    # Count
    classified = sum(1 for n in updated_nodes if "categories" in n)
    total_assignments = sum(len(n.get("categories", [])) for n in updated_nodes)

    print(f"Classified {classified} chunks with {total_assignments} category assignments", file=sys.stderr)

    # Output
    output_prefix = args.output_prefix or args.nodes.stem

    nodes_out = Path(f"{output_prefix}.nodes.json")
    edges_out = Path(f"{output_prefix}.category-edges.json")

    nodes_out.write_text(json.dumps(updated_nodes, ensure_ascii=False, indent=2), encoding="utf-8")
    edges_out.write_text(json.dumps(category_edges, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Written {nodes_out}", file=sys.stderr)
    print(f"Written {edges_out}", file=sys.stderr)


if __name__ == "__main__":
    main()
