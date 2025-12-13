"""
Ranking and re-ranking functions for search results.

Functions:
- reciprocal_rank_fusion: Combine multiple rankings without score normalization
- rerank_with_full_vectors: Re-rank with full 1024d Matryoshka embeddings
- rerank_with_model: Re-rank with dedicated reranker model (jina, bge, etc.)
- semantic_search_with_reranking: Two-stage semantic search (256d → 1024d)
- hybrid_search_with_reranking: Hybrid search with re-ranking
"""

from pathlib import Path
from typing import Any

import duckdb
import numpy as np
import pyarrow.parquet as pq
from openai import OpenAI


def reciprocal_rank_fusion(
    rankings: list[list[dict[str, Any]]],
    k: int = 60,
    limit: int | None = None
) -> list[dict[str, Any]]:
    """
    Reciprocal Rank Fusion (RRF) for combining multiple rankings.

    RRF formula: RRF(d) = Σ 1/(k + rank_i(d))
    where rank_i(d) is the rank of document d in ranking i.

    This method is parameter-free and works well for heterogeneous retrieval methods
    (semantic, BM25, fuzzy, exact) without needing score normalization.

    Args:
        rankings: List of ranking lists, each containing result dicts with 'chunk_id'
        k: Constant for RRF formula (default: 60, commonly used value)
        limit: Maximum number of results to return (default: None = all)

    Returns:
        Combined ranking with RRF scores, sorted by score descending

    Example:
        >>> semantic_results = semantic_search(con, query_emb, limit=50)
        >>> bm25_results = bm25_search(con, query, limit=50)
        >>> fuzzy_results = fuzzy_search(con, query, limit=50)
        >>> combined = reciprocal_rank_fusion([semantic_results, bm25_results, fuzzy_results])
    """
    # Collect all unique chunks and their data
    chunks = {}  # chunk_id -> result dict
    rrf_scores = {}  # chunk_id -> RRF score

    # Process each ranking
    for ranking in rankings:
        for rank, result in enumerate(ranking):
            chunk_id = result['chunk_id']

            # Store chunk data (from first occurrence)
            if chunk_id not in chunks:
                chunks[chunk_id] = result

            # Add to RRF score
            # rank starts at 0, so rank+1 is the actual position (1-indexed)
            rrf_contribution = 1.0 / (k + rank + 1)
            rrf_scores[chunk_id] = rrf_scores.get(chunk_id, 0.0) + rrf_contribution

    # Build final ranking
    results = []
    for chunk_id, score in rrf_scores.items():
        result = chunks[chunk_id].copy()
        result['rrf_score'] = score
        results.append(result)

    # Sort by RRF score
    results.sort(key=lambda x: x['rrf_score'], reverse=True)

    if limit is not None:
        results = results[:limit]

    return results


def rerank_with_model(
    query: str,
    candidates: list[dict[str, Any]],
    config: dict[str, Any],
    top_k: int | None = None,
    model: str | None = None,
    task: str = "reranking"
) -> list[dict[str, Any]]:
    """
    Re-rank candidates using a dedicated reranker model.

    Supports:
    - Dedicated rerankers (jina-reranker-v2, bge-reranker-v2-m3, etc.)
    - Jina-v3 with task="separation"
    - Any OpenAI-compatible reranking API

    Args:
        query: Search query
        candidates: List of candidate dicts with 'chunk_id', 'text', 'summary'
        config: Config dict with reranker settings
        top_k: Number of results to return (default: all)
        model: Reranker model to use (default: from config)
        task: Task type for multi-task models (default: "reranking")

    Returns:
        Reranked list with added 'rerank_score' field

    Config format:
        {
            "reranker_base_url": "http://localhost:8080/v1",
            "reranker_api_key": "dummy",
            "reranker_model": "jinaai/jina-reranker-v2-base-multilingual"
        }
    """
    if not candidates:
        return []

    # Use provided model or from config
    model = model or config.get("reranker_model")
    if not model:
        raise ValueError("No reranker model specified in config or parameters")

    # Initialize OpenAI client for reranker
    client = OpenAI(
        base_url=config.get("reranker_base_url"),
        api_key=config.get("reranker_api_key", "dummy"),
    )

    # Prepare documents for reranking
    # Use summary if available, else text (truncated)
    documents = []
    for cand in candidates:
        text = cand.get('summary') or cand.get('text', '')
        # Truncate very long texts (rerankers typically have token limits)
        max_chars = 2000
        if len(text) > max_chars:
            text = text[:max_chars] + "..."
        documents.append(text)

    # Call reranker
    # Note: OpenAI-compatible reranker APIs vary in their interface
    # Some use chat completions, some use a custom rerank endpoint
    # This assumes a rerank-style API similar to jina-reranker

    try:
        # Try jina-reranker style API (common for many rerankers)
        response = client.post(
            f"/rerank",
            json={
                "model": model,
                "query": query,
                "documents": documents,
                "top_n": top_k or len(documents),
            }
        )
        results = response.json()

        # Parse response and merge scores
        reranked = []
        for item in results.get("results", []):
            idx = item["index"]
            score = item["relevance_score"]
            candidate = candidates[idx].copy()
            candidate['rerank_score'] = score
            reranked.append(candidate)

    except (AttributeError, KeyError):
        # Fallback: try using embeddings API with task parameter (for jina-v3 separation)
        # This is experimental and may not work with all models
        try:
            # For jina-v3 multi-task model with separation task
            # Note: This requires special API support, not standard OpenAI
            response = client.embeddings.create(
                input=query,
                model=model,
                extra_body={
                    "task": task,
                    "documents": documents
                }
            )

            # Parse separation scores (format TBD based on actual API)
            reranked = []
            for idx, score in enumerate(response.data[0].embedding[:len(documents)]):
                candidate = candidates[idx].copy()
                candidate['rerank_score'] = float(score)
                reranked.append(candidate)

            # Sort by score
            reranked.sort(key=lambda x: x['rerank_score'], reverse=True)

        except Exception as e:
            # If both methods fail, fall back to original order with warning
            print(f"Warning: Reranker API call failed: {e}", file=__import__('sys').stderr)
            print("Returning original candidate order", file=__import__('sys').stderr)
            return candidates[:top_k] if top_k else candidates

    return reranked[:top_k] if top_k else reranked


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

    # chunk_idx is now stored as string IDs (e.g. "chunk_360dc915") in Parquet
    # Filter to candidates only
    candidate_df = df[df['chunk_idx'].isin(candidate_ids)]

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

        scores.append({
            'chunk_id': row['chunk_idx'],
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


def multiway_search_with_rrf(
    con: duckdb.DuckDBPyConnection,
    query_text: str,
    query_embedding_full: list[float],
    initial_k: int = 50,
    final_k: int = 10,
    enable_semantic: bool = True,
    enable_bm25: bool = True,
    enable_fuzzy: bool = True,
    enable_exact: bool = False,
    fuzzy_max_distance: int = 2,
    exact_case_sensitive: bool = False,
    rrf_k: int = 60,
    rerank_with_full: bool = True
) -> list[dict[str, Any]]:
    """
    Multi-way search combining semantic, BM25, fuzzy, and exact string search using RRF.

    Pipeline:
    1. Run enabled search methods in parallel (semantic, BM25, fuzzy, exact)
    2. Combine rankings with RRF (no score normalization needed)
    3. Optionally re-rank top candidates with full 1024d vectors

    Args:
        con: DuckDB connection
        query_text: Text query
        query_embedding_full: Full 1024d query embedding
        initial_k: Number of candidates per method in stage 1
        final_k: Number of final results to return
        enable_semantic: Enable semantic search (default: True)
        enable_bm25: Enable BM25 search (default: True)
        enable_fuzzy: Enable fuzzy search (default: True)
        enable_exact: Enable exact string search (default: False, often noisy)
        fuzzy_max_distance: Max edit distance for fuzzy search (default: 2)
        exact_case_sensitive: Case-sensitive exact search (default: False)
        rrf_k: RRF constant (default: 60)
        rerank_with_full: Re-rank with full 1024d vectors (default: True)

    Returns:
        List of results with chunk_id, text, summary, rrf_score (and similarity if reranked)
    """
    rankings = []

    # Stage 1: Run enabled search methods
    if enable_semantic:
        # Semantic search with 256d
        query_emb_256d = query_embedding_full[:256]
        semantic_results = con.execute("""
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

        semantic_ranking = [
            {
                'chunk_id': cid,
                'text': text,
                'summary': summary,
                'source_file': source,
                'semantic_score': sim
            }
            for cid, text, summary, source, sim in semantic_results
        ]
        rankings.append(semantic_ranking)

    if enable_bm25:
        # BM25 search
        bm25_results = con.execute("""
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
        """, [query_text, query_text, initial_k]).fetchall()

        bm25_ranking = [
            {
                'chunk_id': cid,
                'text': text,
                'summary': summary,
                'source_file': source,
                'bm25_score': score
            }
            for cid, text, summary, source, score in bm25_results
        ]
        rankings.append(bm25_ranking)

    if enable_fuzzy:
        # Fuzzy search
        query_terms = query_text.lower().split()
        if query_terms:
            fuzzy_results = con.execute("""
                WITH query_terms AS (
                    SELECT UNNEST(?::VARCHAR[]) as term
                ),
                word_matches AS (
                    SELECT
                        n.id,
                        n.text,
                        n.summary,
                        n.source_file,
                        qt.term as query_term,
                        word.word as matched_word,
                        editdist(qt.term, word.word) as distance
                    FROM nodes n,
                         LATERAL (
                             SELECT UNNEST(string_split(lower(n.text), ' ')) as word
                         ) word,
                         query_terms qt
                    WHERE n.type = 'chunk'
                      AND editdist(qt.term, word.word) <= ?
                      AND length(word.word) >= 3
                ),
                scored_chunks AS (
                    SELECT
                        id,
                        text,
                        summary,
                        source_file,
                        COUNT(DISTINCT query_term) as matched_terms,
                        AVG(distance) as avg_distance
                    FROM word_matches
                    GROUP BY id, text, summary, source_file
                )
                SELECT
                    id,
                    text,
                    summary,
                    source_file,
                    (matched_terms * 10.0 / (1.0 + avg_distance)) as fuzzy_score
                FROM scored_chunks
                ORDER BY fuzzy_score DESC
                LIMIT ?
            """, [query_terms, fuzzy_max_distance, initial_k]).fetchall()

            fuzzy_ranking = [
                {
                    'chunk_id': cid,
                    'text': text,
                    'summary': summary,
                    'source_file': source,
                    'fuzzy_score': score
                }
                for cid, text, summary, source, score in fuzzy_results
            ]
            rankings.append(fuzzy_ranking)

    if enable_exact:
        # Exact string search
        if exact_case_sensitive:
            exact_results = con.execute("""
                SELECT
                    id,
                    text,
                    summary,
                    source_file,
                    (length(text) - length(replace(text, ?, ''))) / length(?) as match_count
                FROM nodes
                WHERE type = 'chunk'
                  AND text LIKE '%' || ? || '%'
                ORDER BY match_count DESC
                LIMIT ?
            """, [query_text, query_text, query_text, initial_k]).fetchall()
        else:
            query_lower = query_text.lower()
            exact_results = con.execute("""
                SELECT
                    id,
                    text,
                    summary,
                    source_file,
                    (length(lower(text)) - length(replace(lower(text), ?, ''))) / length(?) as match_count
                FROM nodes
                WHERE type = 'chunk'
                  AND lower(text) LIKE '%' || ? || '%'
                ORDER BY match_count DESC
                LIMIT ?
            """, [query_lower, query_lower, query_lower, initial_k]).fetchall()

        exact_ranking = [
            {
                'chunk_id': cid,
                'text': text,
                'summary': summary,
                'source_file': source,
                'exact_score': float(count)
            }
            for cid, text, summary, source, count in exact_results
        ]
        rankings.append(exact_ranking)

    if not rankings:
        return []

    # Stage 2: Combine with RRF
    rrf_results = reciprocal_rank_fusion(rankings, k=rrf_k, limit=final_k * 3)

    if not rrf_results:
        return []

    # Stage 3: Optional re-ranking with full 1024d vectors
    if rerank_with_full:
        # Group by source file
        by_source = {}
        for result in rrf_results:
            source = result.get('source_file')
            if source:
                by_source.setdefault(source, []).append(result)

        reranked = []
        for source, chunks in by_source.items():
            # Get parquet path
            parquet_result = con.execute(
                "SELECT parquet_path FROM embedding_sources WHERE source_file = ?",
                [source]
            ).fetchone()

            if not parquet_result:
                # No parquet, keep RRF scores
                reranked.extend(chunks)
                continue

            parquet_path = parquet_result[0]

            # Re-rank with full vectors
            chunk_ids = [c['chunk_id'] for c in chunks]
            scores = rerank_with_full_vectors(
                chunk_ids, query_embedding_full, parquet_path, len(chunk_ids)
            )

            # Merge scores
            scores_by_id = {s['chunk_id']: s['similarity'] for s in scores}
            for chunk in chunks:
                if chunk['chunk_id'] in scores_by_id:
                    chunk['similarity'] = scores_by_id[chunk['chunk_id']]
                    chunk['reranked'] = True
                    reranked.append(chunk)

        # Sort by similarity (full vector) if available, else RRF score
        reranked.sort(
            key=lambda x: x.get('similarity', x.get('rrf_score', 0)),
            reverse=True
        )
        return reranked[:final_k]
    else:
        # Just return RRF results
        return rrf_results[:final_k]


def multiway_search_with_all_reranking(
    con: duckdb.DuckDBPyConnection,
    query_text: str,
    query_embedding_full: list[float],
    config: dict[str, Any],
    initial_k: int = 50,
    final_k: int = 10,
    enable_semantic: bool = True,
    enable_bm25: bool = True,
    enable_fuzzy: bool = True,
    enable_exact: bool = False,
    fuzzy_max_distance: int = 2,
    exact_case_sensitive: bool = False,
    rrf_k: int = 60,
    rerank_with_full: bool = True,
    rerank_with_model_enable: bool = False,
    reranker_model: str | None = None
) -> list[dict[str, Any]]:
    """
    Complete multi-stage search pipeline with all reranking options.

    Pipeline:
    1. Multi-way retrieval (semantic + BM25 + fuzzy + exact)
    2. RRF fusion
    3. Optional: Re-rank with full 1024d vectors
    4. Optional: Re-rank with dedicated reranker model

    Args:
        con: DuckDB connection
        query_text: Text query
        query_embedding_full: Full 1024d query embedding
        config: Config dict (for reranker settings)
        initial_k: Candidates per method in stage 1
        final_k: Final number of results
        enable_semantic: Enable semantic search
        enable_bm25: Enable BM25 search
        enable_fuzzy: Enable fuzzy search
        enable_exact: Enable exact string search
        fuzzy_max_distance: Max edit distance for fuzzy
        exact_case_sensitive: Case-sensitive exact search
        rrf_k: RRF constant
        rerank_with_full: Re-rank with full 1024d vectors
        rerank_with_model_enable: Re-rank with dedicated reranker model
        reranker_model: Reranker model to use (default: from config)

    Returns:
        Final ranked results

    Example:
        >>> config = load_config()
        >>> query_emb = embed_query("Wie funktioniert ML?", config)
        >>> results = multiway_search_with_all_reranking(
        ...     con, "Wie funktioniert ML?", query_emb, config,
        ...     rerank_with_full=True,
        ...     rerank_with_model_enable=True
        ... )
    """
    # Stage 1-3: Multi-way search + RRF + optional full vector reranking
    results = multiway_search_with_rrf(
        con, query_text, query_embedding_full,
        initial_k=initial_k,
        final_k=final_k * 2 if rerank_with_model_enable else final_k,  # Get more if reranker follows
        enable_semantic=enable_semantic,
        enable_bm25=enable_bm25,
        enable_fuzzy=enable_fuzzy,
        enable_exact=enable_exact,
        fuzzy_max_distance=fuzzy_max_distance,
        exact_case_sensitive=exact_case_sensitive,
        rrf_k=rrf_k,
        rerank_with_full=rerank_with_full
    )

    # Stage 4: Optional reranking with dedicated model
    if rerank_with_model_enable and results:
        results = rerank_with_model(
            query=query_text,
            candidates=results,
            config=config,
            top_k=final_k,
            model=reranker_model
        )

    return results[:final_k]
