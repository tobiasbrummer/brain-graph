"""
Two-stage retrieval with Matryoshka embeddings.

Stage 1: Fast retrieval with 256d vectors from DuckDB (HNSW index)
Stage 2: Precise re-ranking with 1024d vectors from Parquet files
"""

from pathlib import Path
from typing import Any

import duckdb
import numpy as np
import pyarrow.parquet as pq


def rerank_with_full_vectors(
    candidate_ids: list[str],
    query_embedding_full: list[float],
    parquet_path: str | Path,
    top_k: int = 10
) -> list[dict[str, Any]]:
    """
    Re-rank candidates using full 1024-dim vectors from Parquet.

    This is called after initial retrieval with 256-dim vectors.

    Args:
        candidate_ids: List of chunk IDs to re-rank
        query_embedding_full: Full 1024-dim query embedding
        parquet_path: Path to Parquet file with full embeddings
        top_k: Number of results to return

    Returns:
        List of dicts with chunk_id and similarity, sorted by similarity desc
    """
    if not candidate_ids:
        return []

    # Load full vectors for candidates
    table = pq.read_table(parquet_path)
    df = table.to_pandas()

    # Convert chunk IDs to indices if needed
    # Chunks are stored as chunk_idx (int) in Parquet, but may be string IDs in DB
    candidate_indices = []
    for cid in candidate_ids:
        if cid.startswith("chunk_"):
            # Extract hex index
            idx = int(cid.replace("chunk_", ""), 16)
            candidate_indices.append(idx)
        else:
            # Assume it's already an int
            candidate_indices.append(int(cid))

    # Filter to candidates only
    candidate_df = df[df['chunk_idx'].isin(candidate_indices)]

    if len(candidate_df) == 0:
        return []

    # Compute cosine similarity with full vectors
    query_vec = np.array(query_embedding_full)
    query_norm = np.linalg.norm(query_vec)

    scores = []
    for _, row in candidate_df.iterrows():
        full_vec = np.array(row['embedding'])
        full_norm = np.linalg.norm(full_vec)

        # Cosine similarity
        similarity = float(np.dot(query_vec, full_vec) / (query_norm * full_norm))

        chunk_id = f"chunk_{row['chunk_idx']:08x}"
        scores.append({
            'chunk_id': chunk_id,
            'similarity': similarity
        })

    # Sort by similarity and return top-k
    scores.sort(key=lambda x: x['similarity'], reverse=True)
    return scores[:top_k]


def semantic_search_with_reranking(
    con: duckdb.DuckDBPyConnection,
    query_embedding_full: list[float],
    initial_k: int = 50,
    final_k: int = 10
) -> list[dict[str, Any]]:
    """
    Two-stage semantic search with re-ranking.

    Stage 1: Fast retrieval with 256d vectors (HNSW index)
    Stage 2: Re-ranking with 1024d vectors from Parquet

    Args:
        con: DuckDB connection with loaded database
        query_embedding_full: Full 1024-dim query embedding
        initial_k: Number of candidates to retrieve in stage 1
        final_k: Number of final results after re-ranking

    Returns:
        List of dicts with chunk_id, similarity, text, summary
    """
    # Truncate query to 256d for stage 1
    query_emb_256d = query_embedding_full[:256]

    # Stage 1: Fast retrieval with 256d
    candidates = con.execute("""
        SELECT
            n.id,
            n.text,
            n.summary,
            e.source_file,
            array_cosine_similarity(e.embedding, ?::DOUBLE[256]) as similarity
        FROM chunk_embeddings_256d e
        JOIN nodes n ON e.chunk_id = n.id
        WHERE n.type = 'chunk'
        ORDER BY similarity DESC
        LIMIT ?
    """, [query_emb_256d, initial_k]).fetchall()

    if not candidates:
        return []

    # Group by source file for efficient Parquet loading
    by_source = {}
    for cand_id, text, summary, source, sim in candidates:
        by_source.setdefault(source, []).append({
            'id': cand_id,
            'text': text,
            'summary': summary,
            'sim_256d': sim
        })

    # Stage 2: Re-rank with full vectors
    reranked = []
    for source, chunks in by_source.items():
        # Get parquet path for this source
        result = con.execute(
            "SELECT parquet_path FROM embedding_sources WHERE source_file = ?",
            [source]
        ).fetchone()

        if not result:
            # No parquet file, use 256d similarity
            for chunk in chunks:
                reranked.append({
                    'chunk_id': chunk['id'],
                    'text': chunk['text'],
                    'summary': chunk['summary'],
                    'similarity': chunk['sim_256d'],
                    'reranked': False
                })
            continue

        parquet_path = result[0]

        # Re-rank these candidates
        chunk_ids = [c['id'] for c in chunks]
        scores = rerank_with_full_vectors(chunk_ids, query_embedding_full, parquet_path, final_k)

        # Merge with text/summary
        scores_by_id = {s['chunk_id']: s['similarity'] for s in scores}
        for chunk in chunks:
            if chunk['id'] in scores_by_id:
                reranked.append({
                    'chunk_id': chunk['id'],
                    'text': chunk['text'],
                    'summary': chunk['summary'],
                    'similarity': scores_by_id[chunk['id']],
                    'reranked': True
                })

    # Final sort by similarity
    reranked.sort(key=lambda x: x['similarity'], reverse=True)
    return reranked[:final_k]


def hybrid_search_with_reranking(
    con: duckdb.DuckDBPyConnection,
    query_text: str,
    query_embedding_full: list[float],
    initial_k: int = 50,
    final_k: int = 10,
    semantic_weight: float = 0.7,
    bm25_weight: float = 0.3
) -> list[dict[str, Any]]:
    """
    Hybrid search (semantic + BM25) with re-ranking.

    Args:
        con: DuckDB connection
        query_text: Text query for BM25
        query_embedding_full: Full 1024-dim embedding for semantic search
        initial_k: Candidates per method in stage 1
        final_k: Final results after fusion and re-ranking
        semantic_weight: Weight for semantic similarity (default: 0.7)
        bm25_weight: Weight for BM25 score (default: 0.3)

    Returns:
        List of results with chunk_id, text, summary, hybrid_score
    """
    # Truncate query to 256d
    query_emb_256d = query_embedding_full[:256]

    # Stage 1: Retrieve candidates
    results = con.execute("""
        WITH semantic_results AS (
            SELECT
                n.id,
                n.text,
                n.summary,
                e.source_file,
                array_cosine_similarity(e.embedding, ?::DOUBLE[256]) as sem_score
            FROM chunk_embeddings_256d e
            JOIN nodes n ON e.chunk_id = n.id
            WHERE n.type = 'chunk'
            ORDER BY sem_score DESC
            LIMIT ?
        ),
        bm25_results AS (
            SELECT
                id,
                text,
                summary,
                source_file,
                fts_main_nodes.match_bm25(id, ?) as bm25_score
            FROM nodes
            WHERE fts_main_nodes.match_bm25(id, ?) IS NOT NULL
            ORDER BY bm25_score DESC
            LIMIT ?
        )
        SELECT
            COALESCE(s.id, b.id) as id,
            COALESCE(s.text, b.text) as text,
            COALESCE(s.summary, b.summary) as summary,
            COALESCE(s.source_file, b.source_file) as source_file,
            COALESCE(s.sem_score, 0) as sem_score,
            COALESCE(b.bm25_score, 0) as bm25_score
        FROM semantic_results s
        FULL OUTER JOIN bm25_results b ON s.id = b.id
    """, [query_emb_256d, initial_k, query_text, query_text, initial_k]).fetchall()

    if not results:
        return []

    # Normalize scores
    max_sem = max(r[4] for r in results) or 1.0
    max_bm25 = max(r[5] for r in results) or 1.0

    # Group by source for re-ranking
    by_source = {}
    for cid, text, summary, source, sem, bm25 in results:
        sem_norm = sem / max_sem
        bm25_norm = bm25 / max_bm25
        hybrid = sem_norm * semantic_weight + bm25_norm * bm25_weight

        by_source.setdefault(source, []).append({
            'id': cid,
            'text': text,
            'summary': summary,
            'hybrid_score_256d': hybrid,
            'sem_score_256d': sem_norm,
            'bm25_score': bm25_norm
        })

    # Stage 2: Re-rank semantic component with full vectors
    reranked = []
    for source, chunks in by_source.items():
        # Get parquet path
        result = con.execute(
            "SELECT parquet_path FROM embedding_sources WHERE source_file = ?",
            [source]
        ).fetchone()

        if not result:
            # No re-ranking, use 256d scores
            for chunk in chunks:
                reranked.append({
                    'chunk_id': chunk['id'],
                    'text': chunk['text'],
                    'summary': chunk['summary'],
                    'hybrid_score': chunk['hybrid_score_256d'],
                    'semantic_score': chunk['sem_score_256d'],
                    'bm25_score': chunk['bm25_score'],
                    'reranked': False
                })
            continue

        parquet_path = result[0]

        # Re-rank with full vectors
        chunk_ids = [c['id'] for c in chunks]
        scores = rerank_with_full_vectors(chunk_ids, query_embedding_full, parquet_path, len(chunk_ids))

        # Re-compute hybrid scores with full-vector semantic scores
        scores_by_id = {s['chunk_id']: s['similarity'] for s in scores}

        # Normalize new semantic scores
        max_sem_full = max(scores_by_id.values()) or 1.0

        for chunk in chunks:
            sem_full = scores_by_id.get(chunk['id'], chunk['sem_score_256d'])
            sem_full_norm = sem_full / max_sem_full
            hybrid_full = sem_full_norm * semantic_weight + chunk['bm25_score'] * bm25_weight

            reranked.append({
                'chunk_id': chunk['id'],
                'text': chunk['text'],
                'summary': chunk['summary'],
                'hybrid_score': hybrid_full,
                'semantic_score': sem_full_norm,
                'bm25_score': chunk['bm25_score'],
                'reranked': True
            })

    # Final sort
    reranked.sort(key=lambda x: x['hybrid_score'], reverse=True)
    return reranked[:final_k]
