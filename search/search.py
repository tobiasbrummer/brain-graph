#!/usr/bin/env python3
"""
Search interface for brain-graph database.

Supports semantic search, BM25 full-text search, and hybrid search.
"""

import argparse
import json
import sys
from pathlib import Path

import duckdb
from openai import OpenAI

from file_utils import load_config


def embed_query(query: str, config: dict) -> list[float]:
    """Embed query text using the configured embedding model."""
    client = OpenAI(
        base_url=config["embedding_base_url"],
        api_key=config["embedding_api_key"],
    )

    # Add query prefix for Jina v3 asymmetric search
    query_text = f"Query: {query}"

    response = client.embeddings.create(
        input=[query_text],
        model=config["embedding_model"],
    )

    return response.data[0].embedding


def semantic_search(
    con: duckdb.DuckDBPyConnection, query_embedding: list[float], limit: int = 10
) -> list[dict]:
    """
    Semantic search using 256d embeddings.

    Args:
        con: DuckDB connection
        query_embedding: Query embedding (full 1024d, will be truncated)
        limit: Number of results to return

    Returns:
        List of results with chunk_id, text, summary, similarity
    """
    # Truncate to 256d
    query_emb_256d = query_embedding[:256]

    results = con.execute(
        """
        SELECT
            n.id,
            n.text,
            n.summary,
            n.source_file,
            array_cosine_similarity(e.embedding, ?::DOUBLE[256]) as similarity
        FROM chunk_embeddings_256d e
        JOIN nodes n ON e.chunk_id = n.id
        WHERE n.type = 'chunk'
        ORDER BY similarity DESC
        LIMIT ?
    """,
        [query_emb_256d, limit],
    ).fetchall()

    return [
        {
            "chunk_id": chunk_id,
            "text": text,
            "summary": summary,
            "source_file": source_file,
            "similarity": similarity,
        }
        for chunk_id, text, summary, source_file, similarity in results
    ]


def bm25_search(
    con: duckdb.DuckDBPyConnection, query: str, limit: int = 10
) -> list[dict]:
    """
    BM25 full-text search.

    Args:
        con: DuckDB connection
        query: Query text
        limit: Number of results to return

    Returns:
        List of results with chunk_id, text, summary, score
    """
    results = con.execute(
        """
        SELECT
            id,
            text,
            summary,
            source_file,
            fts_main_nodes.match_bm25(id, ?) as score
        FROM nodes
        WHERE fts_main_nodes.match_bm25(id, ?) IS NOT NULL
        ORDER BY score DESC
        LIMIT ?
    """,
        [query, query, limit],
    ).fetchall()

    return [
        {
            "chunk_id": chunk_id,
            "text": text,
            "summary": summary,
            "source_file": source_file,
            "bm25_score": score,
        }
        for chunk_id, text, summary, source_file, score in results
    ]


def hybrid_search(
    con: duckdb.DuckDBPyConnection,
    query: str,
    query_embedding: list[float],
    limit: int = 10,
    semantic_weight: float = 0.7,
    bm25_weight: float = 0.3,
) -> list[dict]:
    """
    Hybrid search combining semantic and BM25.

    Args:
        con: DuckDB connection
        query: Query text
        query_embedding: Query embedding (full 1024d, will be truncated)
        limit: Number of results
        semantic_weight: Weight for semantic similarity
        bm25_weight: Weight for BM25 score

    Returns:
        List of results with chunk_id, text, summary, hybrid_score
    """
    # Truncate to 256d
    query_emb_256d = query_embedding[:256]

    results = con.execute(
        """
        WITH semantic_results AS (
            SELECT
                n.id,
                n.text,
                n.summary,
                n.source_file,
                array_cosine_similarity(e.embedding, ?::DOUBLE[256]) as sem_score
            FROM chunk_embeddings_256d e
            JOIN nodes n ON e.chunk_id = n.id
            WHERE n.type = 'chunk'
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
    """,
        [query_emb_256d, query, query],
    ).fetchall()

    if not results:
        return []

    # Normalize and combine scores
    max_sem = max(r[4] for r in results) or 1.0
    max_bm25 = max(r[5] for r in results) or 1.0

    combined = []
    for chunk_id, text, summary, source_file, sem, bm25 in results:
        sem_norm = sem / max_sem
        bm25_norm = bm25 / max_bm25
        hybrid = sem_norm * semantic_weight + bm25_norm * bm25_weight

        combined.append(
            {
                "chunk_id": chunk_id,
                "text": text,
                "summary": summary,
                "source_file": source_file,
                "hybrid_score": hybrid,
                "semantic_score": sem_norm,
                "bm25_score": bm25_norm,
            }
        )

    # Sort by hybrid score
    combined.sort(key=lambda x: x["hybrid_score"], reverse=True)
    return combined[:limit]


def fuzzy_search(
    con: duckdb.DuckDBPyConnection, query: str, limit: int = 50, max_distance: int = 2
) -> list[dict]:
    """
    Fuzzy search using Levenshtein distance (edit distance).

    Finds chunks where text contains words similar to query terms.
    Good for handling typos and spelling variations.

    Args:
        con: DuckDB connection
        query: Search query
        limit: Number of results to return
        max_distance: Maximum edit distance (default: 2)

    Returns:
        List of dicts with chunk_id, text, summary, fuzzy_score
    """
    # Split query into terms
    query_terms = query.lower().split()

    if not query_terms:
        return []

    # Build fuzzy search query
    # For each query term, find chunks with similar words
    results = con.execute(
        """
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
                editdist3(qt.term, word.word) as distance
            FROM nodes n,
                 LATERAL (
                     SELECT UNNEST(string_split(lower(n.text), ' ')) as word
                 ) word,
                 query_terms qt
            WHERE n.type = 'chunk'
              AND editdist3(qt.term, word.word) <= ?
              AND length(word.word) >= 3
        ),
        scored_chunks AS (
            SELECT
                id,
                text,
                summary,
                source_file,
                COUNT(DISTINCT query_term) as matched_terms,
                AVG(distance) as avg_distance,
                COUNT(*) as total_matches
            FROM word_matches
            GROUP BY id, text, summary, source_file
        )
        SELECT
            id,
            text,
            summary,
            source_file,
            matched_terms,
            avg_distance,
            total_matches,
            -- Score: matched terms (higher = better) / avg distance (lower = better)
            (matched_terms * 10.0 / (1.0 + avg_distance)) as fuzzy_score
        FROM scored_chunks
        ORDER BY fuzzy_score DESC, matched_terms DESC
        LIMIT ?
    """,
        [query_terms, max_distance, limit],
    ).fetchall()

    return [
        {
            "chunk_id": cid,
            "text": text,
            "summary": summary,
            "source_file": source_file,
            "matched_terms": matched_terms,
            "avg_distance": avg_distance,
            "total_matches": total_matches,
            "fuzzy_score": fuzzy_score,
        }
        for cid, text, summary, source_file, matched_terms, avg_distance, total_matches, fuzzy_score in results
    ]


def exact_string_search(
    con: duckdb.DuckDBPyConnection,
    query: str,
    limit: int = 50,
    case_sensitive: bool = False,
) -> list[dict]:
    """
    Exact string search without tokenization.

    Finds chunks containing the exact query string.
    Useful for searching specific terms, IDs, or phrases.

    Args:
        con: DuckDB connection
        query: Exact string to search for
        limit: Number of results to return
        case_sensitive: Whether to match case (default: False)

    Returns:
        List of dicts with chunk_id, text, summary, exact_match_count
    """
    if case_sensitive:
        # Case-sensitive search
        results = con.execute(
            """
            SELECT
                id,
                text,
                summary,
                source_file,
                (length(text) - length(replace(text, ?, ''))) / length(?) as match_count,
                1.0 / (1.0 + strpos(text, ?)) as position_score
            FROM nodes
            WHERE type = 'chunk'
              AND text LIKE '%' || ? || '%'
            ORDER BY match_count DESC, position_score DESC
            LIMIT ?
        """,
            [query, query, query, query, limit],
        ).fetchall()
    else:
        # Case-insensitive search
        query_lower = query.lower()
        results = con.execute(
            """
            SELECT
                id,
                text,
                summary,
                source_file,
                (length(lower(text)) - length(replace(lower(text), ?, ''))) / length(?) as match_count,
                1.0 / (1.0 + strpos(lower(text), ?)) as position_score
            FROM nodes
            WHERE type = 'chunk'
              AND lower(text) LIKE '%' || ? || '%'
            ORDER BY match_count DESC, position_score DESC
            LIMIT ?
        """,
            [query_lower, query_lower, query_lower, query_lower, limit],
        ).fetchall()

    return [
        {
            "chunk_id": cid,
            "text": text,
            "summary": summary,
            "source_file": source_file,
            "match_count": int(match_count),
            "position_score": position_score,
        }
        for cid, text, summary, source_file, match_count, position_score in results
    ]


def deduplicate_by_document(results: list[dict], score_key: str) -> list[dict]:
    """
    Keep only the best chunk per document.

    Args:
        results: Search results
        score_key: Key to use for scoring ('similarity', 'bm25_score', 'hybrid_score')

    Returns:
        Deduplicated results with one chunk per document
    """
    if not results:
        return results

    # Group by source_file, keep best chunk per document
    best_per_doc = {}
    for result in results:
        source = result.get("source_file", "unknown")
        score = result.get(score_key, 0)

        if source not in best_per_doc or score > best_per_doc[source].get(score_key, 0):
            best_per_doc[source] = result

    # Return in original score order
    deduplicated = list(best_per_doc.values())
    deduplicated.sort(key=lambda x: x.get(score_key, 0), reverse=True)

    return deduplicated


def print_results(results: list[dict], mode: str):
    """Print search results in a readable format."""
    if not results:
        print("No results found.")
        return

    print(f"\nFound {len(results)} results:\n")
    print("=" * 80)

    for i, result in enumerate(results, 1):
        print(f"\n{i}. {result['chunk_id']}")
        print(f"   Source: {result.get('source_file', 'unknown')}")

        # Print scores
        if mode == "semantic":
            print(f"   Similarity: {result['similarity']:.3f}")
        elif mode == "bm25":
            print(f"   BM25 Score: {result['bm25_score']:.3f}")
        elif mode == "hybrid":
            print(
                f"   Hybrid: {result['hybrid_score']:.3f} "
                f"(sem: {result['semantic_score']:.3f}, bm25: {result['bm25_score']:.3f})"
            )

        # Print summary if available
        if result.get("summary"):
            summary = result["summary"]
            if len(summary) > 200:
                summary = summary[:200] + "..."
            print(f"\n   Summary: {summary}")

        # Print text preview
        text = result.get("text", "")
        if text:
            text_preview = text[:300] + "..." if len(text) > 300 else text
            print(f"\n   {text_preview}")

        print()


def main():
    parser = argparse.ArgumentParser(description="Search brain-graph database")
    parser.add_argument("query", help="Search query")
    parser.add_argument(
        "--db",
        default=".brain_graph/brain.duckdb",
        help="DuckDB database path (default: .brain_graph/brain.duckdb)",
    )
    parser.add_argument(
        "--mode",
        choices=["semantic", "bm25", "hybrid"],
        default="hybrid",
        help="Search mode (default: hybrid)",
    )
    parser.add_argument(
        "--limit", type=int, default=10, help="Number of results (default: 10)"
    )
    parser.add_argument(
        "--semantic-weight",
        type=float,
        default=0.7,
        help="Weight for semantic in hybrid mode (default: 0.7)",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="Config file path (default: auto-detect)",
    )
    args = parser.parse_args()

    # Check if DB exists, otherwise build from data directory
    db_path = Path(args.db)
    data_dir = Path(".brain_graph/data")

    if not db_path.exists():
        if data_dir.exists() and any(data_dir.rglob("*.nodes.json")):
            print(f"Database not found, building from {data_dir}...", file=sys.stderr)
            from build_db import BrainGraphDB

            # Build in-memory database
            db = BrainGraphDB(":memory:")
            db.import_directory(data_dir)
            db.build_indexes()

            # Use the connection from BrainGraphDB
            con = db.con

            print(f"✓ Database ready", file=sys.stderr)
            # Skip the normal loading process below
            db_path = None
        else:
            print(f"Error: Database not found: {db_path}", file=sys.stderr)
            print(f"And no data found in {data_dir}", file=sys.stderr)
            print("Run 'python build_db.py' first to create data.", file=sys.stderr)
            sys.exit(1)

    # Load config
    config = load_config(args.config)

    # Load database if not already loaded
    if db_path is not None:
        # Load database into memory for faster search
        print(f"Loading database into memory...", file=sys.stderr)
        con = duckdb.connect(":memory:")

        # Attach disk database and copy to memory
        con.execute(f"ATTACH '{db_path}' AS disk_db (READ_ONLY)")

        # Copy main tables (exclude internal FTS tables)
        main_tables = [
            "nodes",
            "edges",
            "chunk_embeddings_256d",
            "taxonomy_embeddings_256d",
            "embedding_sources",
            "meta",
            "german_stopwords",
        ]

        for table_name in main_tables:
            # Check if table exists before copying
            exists = con.execute(
                f"SELECT COUNT(*) FROM duckdb_tables() WHERE database_name='disk_db' AND table_name='{table_name}'"
            ).fetchone()[0]
            if exists:
                print(f"  Loading table: {table_name}", file=sys.stderr)
                con.execute(
                    f"CREATE TABLE {table_name} AS SELECT * FROM disk_db.{table_name}"
                )

        # Detach disk database (now everything is in memory)
        con.execute("DETACH disk_db")

        # Rebuild indexes for fast search
        print(f"Building indexes...", file=sys.stderr)

        # VSS extension
        con.execute("INSTALL vss; LOAD vss;")

        # HNSW index for vector search
        con.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_chunk_embeddings_hnsw
            ON chunk_embeddings_256d
            USING HNSW (embedding)
            WITH (metric = 'cosine')
        """
        )

        # FTS extension
        con.execute("INSTALL fts; LOAD fts;")

        # Full-text search index with German stemmer and stopwords
        # Check if german_stopwords table exists (copied from disk DB)
        has_stopwords = (
            con.execute(
                "SELECT COUNT(*) FROM duckdb_tables() WHERE table_name='german_stopwords'"
            ).fetchone()[0]
            > 0
        )

        stopwords_param = "german_stopwords" if has_stopwords else "none"

        con.execute(
            f"""
            PRAGMA create_fts_index(
                'nodes', 'id', 'text', 'summary', 'title', 'description',
                stemmer='german',
                stopwords='{stopwords_param}',
                ignore='(\\.|[^a-zäöüß])+',
                strip_accents=1,
                lower=1,
                overwrite=1
            )
        """
        )

        print(f"✓ Database ready (indexes built)", file=sys.stderr)
    # else: con is already set from the BrainGraphDB build above

    # Perform search
    query_embedding = None
    if args.mode in ["semantic", "hybrid"]:
        print(f"Embedding query...", file=sys.stderr)
        query_embedding = embed_query(args.query, config)

    print(f"Searching with {args.mode} mode...", file=sys.stderr)

    if args.mode == "semantic":
        results = semantic_search(con, query_embedding, args.limit)
        score_key = "similarity"
    elif args.mode == "bm25":
        results = bm25_search(con, args.query, args.limit)
        score_key = "bm25_score"
    elif args.mode == "hybrid":
        bm25_weight = 1.0 - args.semantic_weight
        results = hybrid_search(
            con,
            args.query,
            query_embedding,
            args.limit,
            args.semantic_weight,
            bm25_weight,
        )
        score_key = "hybrid_score"

    # Deduplicate: only best chunk per document
    results = deduplicate_by_document(results, score_key)

    # Print results
    print_results(results, args.mode)

    con.close()


if __name__ == "__main__":
    main()
