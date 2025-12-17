#!/usr/bin/env python3
"""
Search interface for brain-graph database.

Supports semantic search, BM25 full-text search, and hybrid search.
"""

import argparse
import json
import sys
import time
from pathlib import Path

import duckdb

from brain_graph.utils.cli_utils import emit_json, error_result, ms_since, ok_result
from brain_graph.utils.embedding_client import embed_single_cached
from brain_graph.utils.file_utils import load_config


def embed_query(query: str, config: dict) -> list[float]:
    """Embed query text using the configured embedding model (cached)."""
    # Add query prefix for Jina v3 asymmetric search
    query_text = f"Query: {query}"
    return embed_single_cached(query_text, config)


def semantic_search(
    con: duckdb.DuckDBPyConnection, query_embedding: list[float], limit: int = 10
) -> list[dict]:
    """
    Semantic search using 256d embeddings with HNSW index.

    Args:
        con: DuckDB connection
        query_embedding: Query embedding (full 1024d, will be truncated)
        limit: Number of results to return

    Returns:
        List of results with chunk_id, text, summary, similarity
    """
    # Truncate to 256d
    query_emb_256d = query_embedding[:256]

    # Use array_cosine_distance for HNSW index utilization (metric='cosine')
    # ORDER BY distance ASC + LIMIT triggers HNSW index scan
    # Hybrid ranking: similarity * 0.6 + (relevance / 10.0) * 0.4
    results = con.execute(
        """
        SELECT
            e.chunk_id,
            n.text,
            n.summary,
            n.source_file,
            1.0 - array_cosine_distance(e.embedding, ?::FLOAT[256]) as similarity,
            COALESCE(r.relevance_score, 0.0) as relevance
        FROM chunk_embeddings_256d e
        JOIN nodes n ON e.chunk_id = n.id
        LEFT JOIN relevance_scores r ON n.ulid = r.ulid
        ORDER BY (
            (1.0 - array_cosine_distance(e.embedding, ?::FLOAT[256])) * 0.6 +
            (COALESCE(r.relevance_score, 0.0) / 10.0) * 0.4
        ) DESC
        LIMIT ?
    """,
        [query_emb_256d, query_emb_256d, limit],
    ).fetchall()

    return [
        {
            "chunk_id": chunk_id,
            "text": text,
            "summary": summary,
            "source_file": source_file,
            "similarity": similarity,
            "relevance": relevance,
            "score": similarity * 0.6 + (relevance / 10.0) * 0.4,
        }
        for chunk_id, text, summary, source_file, similarity, relevance in results
    ]


def code_search(
    con: duckdb.DuckDBPyConnection,
    query_embedding: list[float],
    limit: int = 10,
    languages: list[str] | None = None,
) -> list[dict]:
    """
    Semantic code search using code embeddings.

    Searches functions, classes, and methods using their embeddings.
    Optionally filters by programming language.

    Args:
        con: DuckDB connection
        query_embedding: Query embedding (full dimension, will be truncated to 256d)
        limit: Number of results to return
        languages: Optional list of languages to filter (e.g., ["python", "javascript"])

    Returns:
        List of results with code_id, name, signature, docstring, similarity, language
    """
    # Truncate to 256d
    query_emb_256d = query_embedding[:256]

    # Language filter
    lang_filter = ""
    if languages:
        lang_list = "', '".join(languages)
        lang_filter = f"AND e.language IN ('{lang_list}')"

    # Use array_cosine_distance for HNSW index utilization (metric='cosine')
    results = con.execute(
        f"""
        SELECT
            e.code_id,
            n.title as name,
            n.signature,
            n.docstring,
            n.content as text,
            n.source_file,
            e.language,
            1.0 - array_cosine_distance(e.embedding, ?::FLOAT[256]) as similarity
        FROM code_embeddings_256d e
        JOIN nodes n ON e.code_id = n.id
        WHERE n.type IN ('function', 'class', 'method')
          {lang_filter}
        ORDER BY array_cosine_distance(e.embedding, ?::FLOAT[256]) ASC
        LIMIT ?
    """,
        [query_emb_256d, query_emb_256d, limit],
    ).fetchall()

    return [
        {
            "code_id": code_id,
            "name": name,
            "signature": signature or "",
            "docstring": docstring or "",
            "text": text,
            "source_file": source_file,
            "language": language,
            "similarity": similarity,
        }
        for code_id, name, signature, docstring, text, source_file, language, similarity in results
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

    Uses Top-K merge strategy: fetch top candidates from both search methods,
    then merge and re-rank. Much faster than FULL OUTER JOIN over all chunks.

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

    # Fetch more candidates than final limit for better coverage
    candidate_limit = min(limit * 5, 100)

    # Top-K semantic results using HNSW index
    results = con.execute(
        """
        WITH semantic_topk AS (
            SELECT
                e.chunk_id as id,
                n.text,
                n.summary,
                n.source_file,
                1.0 - array_cosine_distance(e.embedding, ?::FLOAT[256]) as sem_score
            FROM chunk_embeddings_256d e
            JOIN nodes n ON e.chunk_id = n.id
            ORDER BY array_cosine_distance(e.embedding, ?::FLOAT[256]) ASC
            LIMIT ?
        ),
        bm25_topk AS (
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
        ),
        merged AS (
            SELECT id, text, summary, source_file, sem_score, 0.0 as bm25_score
            FROM semantic_topk
            UNION ALL
            SELECT id, text, summary, source_file, 0.0 as sem_score, bm25_score
            FROM bm25_topk
        )
        SELECT
            id,
            MAX(text) as text,
            MAX(summary) as summary,
            MAX(source_file) as source_file,
            MAX(sem_score) as sem_score,
            MAX(bm25_score) as bm25_score
        FROM merged
        GROUP BY id
    """,
        [
            query_emb_256d,
            query_emb_256d,
            candidate_limit,
            query,
            query,
            candidate_limit,
        ],
    ).fetchall()
    if not results:
        return []

    # Normalize and combine scores
    max_sem = max((r[4] for r in results), default=1.0) or 1.0
    max_bm25 = max((r[5] for r in results), default=1.0) or 1.0

    combined = []
    for chunk_id, text, summary, source_file, sem, bm25 in results:
        sem_norm = sem / max_sem if sem else 0.0
        bm25_norm = bm25 / max_bm25 if bm25 else 0.0
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

    Uses a two-phase approach for performance:
    1. Pre-filter candidates using LIKE patterns (fast)
    2. Apply editdist3 only on promising candidates

    Args:
        con: DuckDB connection
        query: Search query
        limit: Number of results to return
        max_distance: Maximum edit distance (default: 2)

    Returns:
        List of dicts with chunk_id, text, summary, fuzzy_score
    """
    # Split query into terms
    query_terms = [t for t in query.lower().split() if len(t) >= 3]

    if not query_terms:
        return []

    # Build LIKE patterns for pre-filtering (much faster than editdist on all rows)
    # For each term, create pattern that matches prefix/suffix variations
    like_conditions = []
    for term in query_terms:
        # Match words starting or containing the term (handles typos at end)
        like_conditions.append(f"lower(n.text) LIKE '%{term[:3]}%'")

    like_filter = " OR ".join(like_conditions)

    # Limit pre-filter candidates
    candidate_limit = min(limit * 10, 500)

    # Two-phase fuzzy search: pre-filter then editdist
    results = con.execute(
        f"""
        WITH candidates AS (
            SELECT id, text, summary, source_file
            FROM nodes n
            WHERE n.type = 'chunk'
              AND ({like_filter})
            LIMIT {candidate_limit}
        ),
        query_terms AS (
            SELECT UNNEST(?::VARCHAR[]) as term
        ),
        word_matches AS (
            SELECT
                c.id,
                c.text,
                c.summary,
                c.source_file,
                qt.term as query_term,
                word.word as matched_word,
                editdist3(qt.term, word.word) as distance
            FROM candidates c,
                 LATERAL (
                     SELECT UNNEST(
                         regexp_split_to_array(lower(c.text), '[^a-zäöüß]+')
                     ) as word
                 ) word,
                 query_terms qt
            WHERE length(word.word) >= 3
              AND editdist3(qt.term, word.word) <= ?
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
    """
    Print search results in a human-readable format.

    Displays chunk ID, source file, relevance scores (varies by mode),
    summary, and text preview for each result.

    Args:
        results: Search results from semantic_search, bm25_search, etc.
        mode: Search mode (semantic, bm25, fuzzy, hybrid) for score display
    """
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
        elif mode == "fuzzy":
            print(
                f"   Fuzzy Score: {result['fuzzy_score']:.3f} (matched {result['matched_terms']} terms)"
            )
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
    start = time.perf_counter()
    parser = argparse.ArgumentParser(description="Search brain-graph database")
    parser.add_argument("query", help="Search query")
    parser.add_argument(
        "--db",
        default=".brain_graph/brain.duckdb",
        help="DuckDB database path (default: .brain_graph/brain.duckdb)",
    )
    parser.add_argument(
        "--mode",
        choices=["semantic", "bm25", "hybrid", "fuzzy", "code"],
        default="hybrid",
        help="Search mode (default: hybrid)",
    )
    parser.add_argument(
        "--fuzzy-only",
        action="store_true",
        help="Use fuzzy search only (shortcut for --mode fuzzy)",
    )
    parser.add_argument(
        "--semantic-only",
        action="store_true",
        help="Use semantic search only (shortcut for --mode semantic)",
    )
    parser.add_argument(
        "--limit", type=int, default=10, help="Number of results (default: 10)"
    )
    parser.add_argument(
        "--languages",
        help="Comma-separated list of languages for code search (e.g., python,javascript)",
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
    parser.add_argument(
        "--format",
        choices=["json", "text"],
        default="json",
        help="Output format (default: json)",
    )
    parser.add_argument(
        "--pretty", action="store_true", help="Pretty-print JSON output"
    )
    parser.add_argument(
        "--debug", action="store_true", help="Include traceback in JSON error output"
    )
    args = parser.parse_args()

    con: duckdb.DuckDBPyConnection | None = None

    def _load_extension_safe(ext: str) -> None:
        assert con is not None
        try:
            con.execute(f"LOAD {ext};")
        except duckdb.Error:
            try:
                con.execute(f"INSTALL {ext};")
                con.execute(f"LOAD {ext};")
            except duckdb.Error as e:
                print(
                    f"Warning: Could not load DuckDB extension '{ext}' ({e})",
                    file=sys.stderr,
                )

    try:
        # Check if DB exists, otherwise build from documents directory
        db_path = Path(args.db)
        data_dir = Path(".brain_graph/data")
        documents_dir = data_dir / "documents"

        if not db_path.exists():
            if documents_dir.exists() and any(documents_dir.rglob("*.document.json")):
                print(
                    f"Database not found, building in-memory DB from {documents_dir}...",
                    file=sys.stderr,
                )
                from brain_graph.db.db_builder import BrainGraphDB

                db = BrainGraphDB(":memory:")
                db.import_directory_fast(data_dir)
                db.build_indexes()
                con = db.con
                print("Database ready", file=sys.stderr)
                db_path = None
            else:
                raise FileNotFoundError(f"Database not found: {db_path}")

        # Load config
        config = load_config(args.config)

        # Load database if not already loaded
        if db_path is not None:
            print("Loading database into memory...", file=sys.stderr)
            con = duckdb.connect(":memory:")

            con.execute(f"ATTACH '{db_path}' AS disk_db (READ_ONLY)")

            main_tables = [
                "nodes",
                "edges",
                "chunk_embeddings_256d",
                "code_embeddings_256d",
                "taxonomy_embeddings_256d",
                "embedding_sources",
                "meta",
                "german_stopwords",
            ]

            for table_name in main_tables:
                exists = con.execute(
                    f"SELECT COUNT(*) FROM duckdb_tables() WHERE database_name='disk_db' AND table_name='{table_name}'"
                ).fetchone()[0]
                if exists:
                    print(f"  Loading table: {table_name}", file=sys.stderr)
                    con.execute(
                        f"CREATE TABLE {table_name} AS SELECT * FROM disk_db.{table_name}"
                    )

            con.execute("DETACH disk_db")

            print("Building indexes...", file=sys.stderr)

            _load_extension_safe("vss")
            try:
                con.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_chunk_embeddings_hnsw
                    ON chunk_embeddings_256d
                    USING HNSW (embedding)
                    WITH (metric = 'cosine')
                    """
                )
            except duckdb.Error as e:
                print(
                    f"Warning: Could not build HNSW index, skipping ({e})",
                    file=sys.stderr,
                )

            _load_extension_safe("fts")

            has_stopwords = (
                con.execute(
                    "SELECT COUNT(*) FROM duckdb_tables() WHERE table_name='german_stopwords'"
                ).fetchone()[0]
                > 0
            )
            stopwords_param = "german_stopwords" if has_stopwords else "none"
            try:
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
            except duckdb.Error as e:
                print(
                    f"Warning: Could not build FTS index, skipping ({e})",
                    file=sys.stderr,
                )

            print("Database ready (indexes built)", file=sys.stderr)

        if con is None:
            raise RuntimeError("Database connection not available")

        # Handle shortcut flags
        mode = args.mode
        if args.fuzzy_only:
            mode = "fuzzy"
        elif args.semantic_only:
            mode = "semantic"

        query_embedding = None
        if mode in ["semantic", "hybrid", "code"]:
            print("Embedding query...", file=sys.stderr)
            query_embedding = embed_query(args.query, config)

        print(f"Searching with {mode} mode...", file=sys.stderr)

        if mode == "semantic":
            results = semantic_search(con, query_embedding, args.limit)
            score_key = "similarity"
        elif mode == "bm25":
            results = bm25_search(con, args.query, args.limit)
            score_key = "bm25_score"
        elif mode == "fuzzy":
            results = fuzzy_search(con, args.query, args.limit)
            score_key = "fuzzy_score"
        elif mode == "code":
            languages = args.languages.split(",") if args.languages else None
            results = code_search(con, query_embedding, args.limit, languages)
            score_key = "similarity"
        else:
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

        results = deduplicate_by_document(results, score_key)

        if args.format == "json":
            emit_json(
                ok_result(
                    "search",
                    query=args.query,
                    mode=mode,
                    limit=args.limit,
                    score_key=score_key,
                    results=results,
                    counts={"results": len(results)},
                    duration_ms=ms_since(start),
                ),
                pretty=args.pretty,
            )
        else:
            print_results(results, mode)
        return 0
    except Exception as e:
        if args.format == "json":
            emit_json(
                error_result(
                    "search",
                    e,
                    include_traceback=args.debug,
                    duration_ms=ms_since(start),
                ),
                pretty=args.pretty,
            )
            return 1
        raise
    finally:
        if con is not None:
            try:
                con.close()
            except Exception:
                pass


if __name__ == "__main__":
    raise SystemExit(main())
