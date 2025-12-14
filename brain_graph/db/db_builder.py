#!/usr/bin/env python3
"""
Build DuckDB database from brain_graph "Document JSON" outputs.

Creates an in-memory database with:
- Vector similarity search (VSS) with Matryoshka embeddings (256d)
- Full-text search (FTS/BM25)
- Property graph queries (DuckPGQ)
- Reference to full 1024d vectors in Parquet for re-ranking

Usage:
    brain db build --output .brain_graph/brain.duckdb
    python -m brain_graph.db.db_builder --output .brain_graph/brain.duckdb

Inputs (default):
    - `.brain_graph/data/documents/**/*.document.json`
    - `.brain_graph/data/embeddings/**/*.parquet` (optional)
"""

import argparse
import sys
import time
from pathlib import Path
from typing import Any

import duckdb

from brain_graph.utils.cli_utils import emit_json, error_result, ms_since, ok_result


REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def _find_duckpgq_extension() -> Path:
    """Return the expected DuckPGQ extension path (prefer package-local lib)."""
    # Preferred location: <repo>/brain_graph/lib/duckpgq/duckpgq.duckdb_extension
    pkg_root = Path(__file__).resolve().parent.parent
    preferred = pkg_root / "lib" / "duckpgq" / "duckpgq.duckdb_extension"
    if preferred.exists():
        return preferred

    # Backward-compatible fallback: <repo>/lib/duckpgq/duckpgq.duckdb_extension
    return REPO_ROOT / "lib" / "duckpgq" / "duckpgq.duckdb_extension"


def _sql_quote(value: str) -> str:
    """Escape a string for use as a single-quoted SQL literal."""
    return value.replace("'", "''")


class BrainGraphDB:
    """Builds and manages the brain-graph DuckDB database."""

    def __init__(self, db_path: str = ":memory:"):
        """Initialize database connection."""
        self.con = duckdb.connect(
            db_path,
            config={
                "allow_unsigned_extensions": "true",
                "hnsw_enable_experimental_persistence": "true",
            },
        )
        self._setup_extensions()
        self._create_schema()

    def _setup_extensions(self):
        """Install and load required extensions."""
        print("Setting up DuckDB extensions...", file=sys.stderr)
        # Avoid failing hard in offline environments: try LOAD first, then INSTALL+LOAD.
        for ext in ["vss", "fts"]:
            try:
                self.con.execute(f"LOAD {ext};")
            except duckdb.Error:
                try:
                    self.con.execute(f"INSTALL {ext};")
                    self.con.execute(f"LOAD {ext};")
                except duckdb.Error as e:
                    print(
                        f"Warning: Could not load DuckDB extension '{ext}' ({e})",
                        file=sys.stderr,
                    )
        duckpgq_path = _find_duckpgq_extension()
        try:
            self.con.execute("LOAD duckpgq;")
        except duckdb.Error:
            try:
                if duckpgq_path.exists():
                    self.con.execute(f"LOAD '{_sql_quote(duckpgq_path.as_posix())}';")
                else:
                    self.con.execute("INSTALL duckpgq;")
                    self.con.execute("LOAD duckpgq;")
            except duckdb.Error as e:
                print(
                    f"Warning: DuckPGQ extension not available ({e})", file=sys.stderr
                )

    def _create_schema(self):
        """Create all tables and indexes."""
        print("Creating database schema...", file=sys.stderr)

        # Nodes table
        self.con.execute(
            """
            CREATE TABLE IF NOT EXISTS nodes (
                id VARCHAR PRIMARY KEY,
                ulid VARCHAR NOT NULL,
                type VARCHAR NOT NULL,
                source_file VARCHAR,
                title VARCHAR,
                text VARCHAR,
                description VARCHAR,
                keywords VARCHAR[],
                language VARCHAR,
                char_start INTEGER,
                char_end INTEGER,
                summary VARCHAR,
                entity_type VARCHAR,
                occurrences INTEGER,
                mentioned_in VARCHAR[],
                level INTEGER,
                code_language VARCHAR,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """
        )

        # Edges table
        self.con.execute(
            """
            CREATE TABLE IF NOT EXISTS edges (
                id INTEGER PRIMARY KEY,
                from_id VARCHAR NOT NULL,
                to_id VARCHAR NOT NULL,
                type VARCHAR NOT NULL,
                weight DOUBLE,
                similarity DOUBLE,
                overlap_chars INTEGER,
                source_file VARCHAR,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """
        )

        # Chunk embeddings (256d)
        self.con.execute(
            """
            CREATE TABLE IF NOT EXISTS chunk_embeddings_256d (
                chunk_id VARCHAR PRIMARY KEY,
                chunk_local_id VARCHAR,
                embedding FLOAT[256],
                source_file VARCHAR
            );
        """
        )

        # Taxonomy embeddings (256d)
        self.con.execute(
            """
            CREATE TABLE IF NOT EXISTS taxonomy_embeddings_256d (
                category_id VARCHAR PRIMARY KEY,
                embedding FLOAT[256]
            );
        """
        )

        # Embedding sources (for re-ranking)
        self.con.execute(
            """
            CREATE TABLE IF NOT EXISTS embedding_sources (
                source_file VARCHAR,
                parquet_path VARCHAR,
                embedding_dim INTEGER DEFAULT 1024,
                model VARCHAR,
                created_at TIMESTAMP
            );
        """
        )

        # Meta table (for deduplication and tracking)
        self.con.execute(
            """
            CREATE TABLE IF NOT EXISTS meta (
                ulid VARCHAR PRIMARY KEY,
                source_file VARCHAR NOT NULL,
                source_hash VARCHAR NOT NULL,
                source_commit VARCHAR,
                source_commit_date TIMESTAMP,
                source_dirty BOOLEAN,
                created_at TIMESTAMP,
                modified_at TIMESTAMP,
                uses INTEGER,
                importance DOUBLE,
                decay DOUBLE
            );
        """
        )

    def import_directory_fast(
        self,
        data_dir: Path,
        documents_dir: Path | None = None,
        target_dim: int = 256,
    ) -> None:
        """
        Ultra-fast import using DuckDB-native read_json/read_parquet.

        Requires Document JSONs under:
        - <data_dir>/documents/YYYY-MM/*.document.json

        This builds:
        - nodes (id = ulid)
        - edges (from_id/to_id = ulid)
        - meta (document-level)
        - embedding_sources + chunk_embeddings_256d (chunk_id = chunk ulid)
        - taxonomy nodes/embeddings/edges (if available)
        """
        docs_dir = documents_dir or (data_dir / "documents")
        doc_glob = f"{docs_dir.as_posix()}/**/*.document.json"
        emb_dir = data_dir / "embeddings"
        emb_glob = f"{emb_dir.as_posix()}/**/*.parquet"

        taxonomy_nodes_path = Path(".brain_graph/config/taxonomy.md.nodes.json")
        taxonomy_edges_path = Path(".brain_graph/config/taxonomy.md.edges.json")
        taxonomy_parquet_path = Path(".brain_graph/config/taxonomy.md.parquet")

        if not docs_dir.exists():
            raise FileNotFoundError(
                f"Documents directory not found: {docs_dir}\n"
                "Make sure your pipeline has written *.document.json files (or pass --documents-dir)."
            )
        if not any(docs_dir.rglob("*.document.json")):
            raise FileNotFoundError(
                f"No '*.document.json' files found under {docs_dir}\n"
                "Make sure your pipeline has written *.document.json files."
            )

        has_embeddings = emb_dir.exists() and any(emb_dir.rglob("*.parquet"))

        # Stage documents once (avoid re-scanning JSON multiple times).
        self.con.execute(
            f"""
            CREATE OR REPLACE TEMP TABLE documents AS
            SELECT
                id::VARCHAR AS doc_id,
                path::VARCHAR AS source_file,
                language::VARCHAR AS language,
                file_hash::VARCHAR AS source_hash,
                source_commit::VARCHAR AS source_commit,
                source_commit_date::VARCHAR AS source_commit_date,
                source_dirty::BOOLEAN AS source_dirty,
                created::VARCHAR AS created,
                updated::VARCHAR AS updated,
                uses::INTEGER AS uses,
                importance::DOUBLE AS importance,
                decay::DOUBLE AS decay,
                nodes AS nodes,
                edges AS edges,
                links AS links,
                regexp_extract(filename, '([^/]+)[.]document[.]json$', 1) AS file_base
            FROM read_json_auto('{_sql_quote(doc_glob)}', filename=true);
            """
        )

        # Nodes (one CTAS; id = ulid)
        self.con.execute(
            """
            CREATE OR REPLACE TABLE nodes AS
            WITH
            sections AS (
                SELECT
                    sec.ulid::VARCHAR AS id,
                    sec.ulid::VARCHAR AS ulid,
                    'section'::VARCHAR AS type,
                    d.source_file AS source_file,
                    sec.title::VARCHAR AS title,
                    NULL::VARCHAR AS text,
                    NULL::VARCHAR AS description,
                    []::VARCHAR[] AS keywords,
                    d.language AS language,
                    NULL::INTEGER AS char_start,
                    NULL::INTEGER AS char_end,
                    NULL::VARCHAR AS summary,
                    NULL::VARCHAR AS entity_type,
                    NULL::INTEGER AS occurrences,
                    []::VARCHAR[] AS mentioned_in,
                    sec.level::INTEGER AS level,
                    NULL::VARCHAR AS code_language,
                    CURRENT_TIMESTAMP AS created_at
                FROM documents d, UNNEST(d.nodes.sections) AS s(sec)
            ),
            chunks AS (
                SELECT
                    ch.ulid::VARCHAR AS id,
                    ch.ulid::VARCHAR AS ulid,
                    'chunk'::VARCHAR AS type,
                    d.source_file AS source_file,
                    NULL::VARCHAR AS title,
                    ch.text::VARCHAR AS text,
                    NULL::VARCHAR AS description,
                    []::VARCHAR[] AS keywords,
                    ch.language::VARCHAR AS language,
                    ch.char_start::INTEGER AS char_start,
                    ch.char_end::INTEGER AS char_end,
                    ch.summary::VARCHAR AS summary,
                    NULL::VARCHAR AS entity_type,
                    NULL::INTEGER AS occurrences,
                    []::VARCHAR[] AS mentioned_in,
                    NULL::INTEGER AS level,
                    NULL::VARCHAR AS code_language,
                    CURRENT_TIMESTAMP AS created_at
                FROM documents d, UNNEST(d.nodes.chunks) AS c(ch)
            ),
            entities AS (
                SELECT
                    ent.ulid::VARCHAR AS id,
                    ent.ulid::VARCHAR AS ulid,
                    'entity'::VARCHAR AS type,
                    d.source_file AS source_file,
                    NULL::VARCHAR AS title,
                    ent.title::VARCHAR AS text,
                    NULL::VARCHAR AS description,
                    []::VARCHAR[] AS keywords,
                    d.language AS language,
                    NULL::INTEGER AS char_start,
                    NULL::INTEGER AS char_end,
                    NULL::VARCHAR AS summary,
                    ent.entity_type::VARCHAR AS entity_type,
                    ent.occurrences::INTEGER AS occurrences,
                    ent.mentioned_in::VARCHAR[] AS mentioned_in,
                    NULL::INTEGER AS level,
                    NULL::VARCHAR AS code_language,
                    CURRENT_TIMESTAMP AS created_at
                FROM documents d, UNNEST(d.nodes.entities) AS e(ent)
            )
            SELECT * FROM sections
            UNION ALL SELECT * FROM chunks
            UNION ALL SELECT * FROM entities;
            """
        )

        # Edges: map document-local IDs -> node ULIDs
        self.con.execute(
            """
            CREATE OR REPLACE TABLE edges AS
            WITH
            node_map AS (
                SELECT d.doc_id, sec.id::VARCHAR AS local_id, sec.ulid::VARCHAR AS ulid
                FROM documents d, UNNEST(d.nodes.sections) AS s(sec)
                UNION ALL
                SELECT d.doc_id, ch.id::VARCHAR AS local_id, ch.ulid::VARCHAR AS ulid
                FROM documents d, UNNEST(d.nodes.chunks) AS c(ch)
                UNION ALL
                SELECT d.doc_id, ent.id::VARCHAR AS local_id, ent.ulid::VARCHAR AS ulid
                FROM documents d, UNNEST(d.nodes.entities) AS e(ent)
            ),
            doc_edges AS (
                SELECT
                    d.doc_id,
                    d.source_file,
                    edge.from_id::VARCHAR AS from_local_id,
                    edge.to_id::VARCHAR AS to_local_id,
                    edge.type::VARCHAR AS type,
                    edge.weight::DOUBLE AS weight,
                    edge.similarity::DOUBLE AS similarity,
                    edge.overlap_chars::INTEGER AS overlap_chars
                FROM documents d, UNNEST(d.edges) AS e(edge)
            )
            SELECT
                row_number() OVER ()::INTEGER AS id,
                fm.ulid AS from_id,
                tm.ulid AS to_id,
                de.type AS type,
                de.weight AS weight,
                de.similarity AS similarity,
                de.overlap_chars AS overlap_chars,
                de.source_file AS source_file,
                CURRENT_TIMESTAMP AS created_at
            FROM doc_edges de
            JOIN node_map fm ON fm.doc_id = de.doc_id AND fm.local_id = de.from_local_id
            JOIN node_map tm ON tm.doc_id = de.doc_id AND tm.local_id = de.to_local_id;
            """
        )

        # Meta (doc-level)
        self.con.execute(
            """
            CREATE OR REPLACE TABLE meta AS
            SELECT
                doc_id::VARCHAR AS ulid,
                source_file::VARCHAR AS source_file,
                COALESCE(source_hash, '')::VARCHAR AS source_hash,
                source_commit::VARCHAR AS source_commit,
                try_cast(source_commit_date AS TIMESTAMP) AS source_commit_date,
                source_dirty::BOOLEAN AS source_dirty,
                try_cast(created AS TIMESTAMP) AS created_at,
                try_cast(updated AS TIMESTAMP) AS modified_at,
                uses::INTEGER AS uses,
                importance::DOUBLE AS importance,
                decay::DOUBLE AS decay
            FROM documents;
            """
        )

        # Embedding sources: map vault path -> parquet path (via filename base)
        if has_embeddings:
            self.con.execute(
                f"""
                CREATE OR REPLACE TABLE embedding_sources AS
                WITH
                emb_files AS (
                    SELECT DISTINCT
                        regexp_extract(filename, '([^/]+)[.]parquet$', 1) AS file_base,
                        filename AS parquet_path
                    FROM read_parquet('{_sql_quote(emb_glob)}', filename=true)
                )
                SELECT
                    d.source_file::VARCHAR AS source_file,
                    e.parquet_path::VARCHAR AS parquet_path,
                    1024::INTEGER AS embedding_dim,
                    'unknown'::VARCHAR AS model,
                    CURRENT_TIMESTAMP AS created_at
                FROM documents d
                JOIN emb_files e USING (file_base);
                """
            )
        else:
            self.con.execute(
                """
                CREATE OR REPLACE TABLE embedding_sources AS
                SELECT
                    NULL::VARCHAR AS source_file,
                    NULL::VARCHAR AS parquet_path,
                    NULL::INTEGER AS embedding_dim,
                    NULL::VARCHAR AS model,
                    NULL::TIMESTAMP AS created_at
                WHERE FALSE;
                """
            )

        # Chunk embeddings (256d): map chunk_idx (local chunk ID) -> chunk ulid, include source_file for grouping
        if has_embeddings:
            self.con.execute(
                f"""
                CREATE OR REPLACE TABLE chunk_embeddings_256d AS
                WITH
                chunk_map AS (
                    SELECT
                        d.file_base,
                        d.source_file,
                        ch.id::VARCHAR AS chunk_local_id,
                        ch.ulid::VARCHAR AS chunk_ulid
                    FROM documents d, UNNEST(d.nodes.chunks) AS c(ch)
                ),
                emb_raw AS (
                    SELECT
                        regexp_extract(filename, '([^/]+)[.]parquet$', 1) AS file_base,
                        chunk_idx::VARCHAR AS chunk_local_id,
                        embedding AS embedding,
                        filename AS parquet_path
                    FROM read_parquet('{_sql_quote(emb_glob)}', filename=true)
                )
                SELECT
                    cm.chunk_ulid AS chunk_id,
                    cm.chunk_local_id AS chunk_local_id,
                    CAST(emb_raw.embedding[1:{target_dim}] AS FLOAT[{target_dim}]) AS embedding,
                    cm.source_file AS source_file
                FROM emb_raw
                JOIN chunk_map cm
                  ON cm.file_base = emb_raw.file_base
                 AND cm.chunk_local_id = emb_raw.chunk_local_id;
                """
            )
        else:
            self.con.execute(
                f"""
                CREATE OR REPLACE TABLE chunk_embeddings_256d AS
                SELECT
                    NULL::VARCHAR AS chunk_id,
                    NULL::VARCHAR AS chunk_local_id,
                    NULL::FLOAT[{target_dim}] AS embedding,
                    NULL::VARCHAR AS source_file
                WHERE FALSE;
                """
            )

        # Document links/backlinks (derived from forward links).
        #
        # Note: This does not write back into *.document.json files; it only creates DB tables
        # that can be queried by the search/graph layer.
        try:
            self.con.execute(
                """
                CREATE OR REPLACE TABLE doc_links AS
                SELECT
                    d.doc_id::VARCHAR AS source_doc_id,
                    l.link.target_id::VARCHAR AS target_doc_id,
                    l.link.type::VARCHAR AS type,
                    l.link.source_node::VARCHAR AS source_node,
                    l.link.context::VARCHAR AS context,
                    l.link.char_offset::INTEGER AS char_offset
                FROM documents d, UNNEST(d.links) AS l(link)
                WHERE l.link.target_id IS NOT NULL
                  AND length(l.link.target_id::VARCHAR) = 26;
                """
            )
            self.con.execute(
                """
                CREATE OR REPLACE TABLE doc_backlinks AS
                SELECT
                    target_doc_id::VARCHAR AS doc_id,
                    source_doc_id::VARCHAR AS source_doc_id,
                    type::VARCHAR AS type,
                    source_node::VARCHAR AS source_node,
                    context::VARCHAR AS context,
                    char_offset::INTEGER AS char_offset
                FROM doc_links;
                """
            )
        except duckdb.Error as e:
            print(
                f"Warning: Could not build doc_links/doc_backlinks, skipping ({e})",
                file=sys.stderr,
            )
            self.con.execute(
                """
                CREATE OR REPLACE TABLE doc_links AS
                SELECT
                    NULL::VARCHAR AS source_doc_id,
                    NULL::VARCHAR AS target_doc_id,
                    NULL::VARCHAR AS type,
                    NULL::VARCHAR AS source_node,
                    NULL::VARCHAR AS context,
                    NULL::INTEGER AS char_offset
                WHERE FALSE;
                """
            )
            self.con.execute(
                """
                CREATE OR REPLACE TABLE doc_backlinks AS
                SELECT
                    NULL::VARCHAR AS doc_id,
                    NULL::VARCHAR AS source_doc_id,
                    NULL::VARCHAR AS type,
                    NULL::VARCHAR AS source_node,
                    NULL::VARCHAR AS context,
                    NULL::INTEGER AS char_offset
                WHERE FALSE;
                """
            )

        # Optional taxonomy import (nodes + embeddings + edges).
        if taxonomy_nodes_path.exists():
            tax_nodes = taxonomy_nodes_path.as_posix()
            self.con.execute(
                f"""
                CREATE OR REPLACE TEMP TABLE taxonomy AS
                SELECT * FROM read_json_auto('{_sql_quote(tax_nodes)}', format='array');
                """
            )

            self.con.execute(
                """
                INSERT INTO nodes
                SELECT
                    t.ulid::VARCHAR AS id,
                    t.ulid::VARCHAR AS ulid,
                    'category'::VARCHAR AS type,
                    NULL::VARCHAR AS source_file,
                    t.title::VARCHAR AS title,
                    NULL::VARCHAR AS text,
                    t.description::VARCHAR AS description,
                    t.keywords::VARCHAR[] AS keywords,
                    NULL::VARCHAR AS language,
                    NULL::INTEGER AS char_start,
                    NULL::INTEGER AS char_end,
                    NULL::VARCHAR AS summary,
                    NULL::VARCHAR AS entity_type,
                    NULL::INTEGER AS occurrences,
                    []::VARCHAR[] AS mentioned_in,
                    NULL::INTEGER AS level,
                    NULL::VARCHAR AS code_language,
                    CURRENT_TIMESTAMP AS created_at
                FROM taxonomy t;
                """
            )

            if taxonomy_parquet_path.exists():
                tax_parquet = taxonomy_parquet_path.as_posix()
                self.con.execute(
                    f"""
                    CREATE OR REPLACE TABLE taxonomy_embeddings_256d AS
                    WITH emb AS (
                        SELECT category_id::VARCHAR AS category_slug, embedding AS embedding
                        FROM read_parquet('{_sql_quote(tax_parquet)}')
                    )
                    SELECT
                        t.ulid::VARCHAR AS category_id,
                        CAST(emb.embedding[1:{target_dim}] AS FLOAT[{target_dim}]) AS embedding
                    FROM emb
                    JOIN taxonomy t ON t.id::VARCHAR = emb.category_slug;
                    """
                )
            else:
                self.con.execute(
                    f"""
                    CREATE OR REPLACE TABLE taxonomy_embeddings_256d AS
                    SELECT NULL::VARCHAR AS category_id, NULL::FLOAT[{target_dim}] AS embedding
                    WHERE FALSE;
                    """
                )

            if taxonomy_edges_path.exists():
                tax_edges = taxonomy_edges_path.as_posix()
                self.con.execute(
                    f"""
                    INSERT INTO edges
                    WITH
                    raw AS (
                        SELECT * FROM read_json_auto('{_sql_quote(tax_edges)}', format='array')
                    ),
                    mapped AS (
                        SELECT
                            f.ulid::VARCHAR AS from_id,
                            t.ulid::VARCHAR AS to_id,
                            raw.type::VARCHAR AS type,
                            raw.weight::DOUBLE AS weight
                        FROM raw
                        JOIN taxonomy f ON f.id::VARCHAR = raw."from"
                        JOIN taxonomy t ON t.id::VARCHAR = raw."to"
                    )
                    SELECT
                        (SELECT COALESCE(MAX(id), 0) FROM edges) + row_number() OVER ()::INTEGER AS id,
                        from_id,
                        to_id,
                        type,
                        weight,
                        NULL::DOUBLE AS similarity,
                        NULL::INTEGER AS overlap_chars,
                        NULL::VARCHAR AS source_file,
                        CURRENT_TIMESTAMP AS created_at
                    FROM mapped;
                    """
                )

            # Chunk -> category edges from Document chunk.categories (weight/similarity not available at schema-level yet).
            self.con.execute(
                """
                INSERT INTO edges
                WITH
                chunk_categories AS (
                    SELECT
                        d.source_file,
                        ch.ulid::VARCHAR AS chunk_ulid,
                        COALESCE(try_cast(ch.categories AS VARCHAR[]), []::VARCHAR[]) AS categories
                    FROM documents d, UNNEST(d.nodes.chunks) AS c(ch)
                ),
                mapped AS (
                    SELECT
                        cc.source_file,
                        cc.chunk_ulid AS from_id,
                        t.ulid::VARCHAR AS to_id,
                        'categorized_as'::VARCHAR AS type
                    FROM chunk_categories cc,
                         UNNEST(cc.categories) cat_slug
                    JOIN taxonomy t ON t.id::VARCHAR = cat_slug::VARCHAR
                )
                SELECT
                    (SELECT COALESCE(MAX(id), 0) FROM edges) + row_number() OVER ()::INTEGER AS id,
                    from_id,
                    to_id,
                    type,
                    NULL::DOUBLE AS weight,
                    NULL::DOUBLE AS similarity,
                    NULL::INTEGER AS overlap_chars,
                    source_file,
                    CURRENT_TIMESTAMP AS created_at
                FROM mapped;
                """
            )
        else:
            # Ensure taxonomy_embeddings_256d exists even if taxonomy is missing.
            self.con.execute(
                f"""
                CREATE OR REPLACE TABLE taxonomy_embeddings_256d AS
                SELECT NULL::VARCHAR AS category_id, NULL::FLOAT[{target_dim}] AS embedding
                WHERE FALSE;
                """
            )

        # Drop staging table to reduce memory footprint (nodes/edges/meta/embeddings already materialized).
        self.con.execute("DROP TABLE IF EXISTS documents")

    def build_indexes(self):
        """Build all indexes after data import."""
        print("\nBuilding indexes...", file=sys.stderr)

        import time

        # Get chunk count for progress estimation
        chunk_count = self.con.execute(
            "SELECT COUNT(*) FROM chunk_embeddings_256d"
        ).fetchone()[0]
        print(f"  VSS indexes (HNSW) for {chunk_count} chunks...", file=sys.stderr)

        # HNSW parameters:
        # - Default metric is l2sq (faster than cosine, similar results for normalized embeddings)
        # - M: connections per layer (16 default)
        # - ef_construction: search depth during build (128 default)
        start = time.time()
        try:
            self.con.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_chunk_embeddings_hnsw
                ON chunk_embeddings_256d
                USING HNSW (embedding)
                """
            )
            elapsed = time.time() - start
            print(f"    Chunk HNSW index built in {elapsed:.1f}s", file=sys.stderr)
        except duckdb.Error as e:
            print(
                f"    Warning: Could not build chunk HNSW index, skipping ({e})",
                file=sys.stderr,
            )

        try:
            self.con.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_taxonomy_embeddings_hnsw
                ON taxonomy_embeddings_256d
                USING HNSW (embedding)
                """
            )
        except duckdb.Error as e:
            print(
                f"    Warning: Could not build taxonomy HNSW index, skipping ({e})",
                file=sys.stderr,
            )

        print("  B-tree indexes...", file=sys.stderr)
        self.con.execute("CREATE INDEX IF NOT EXISTS idx_nodes_type ON nodes(type)")
        self.con.execute(
            "CREATE INDEX IF NOT EXISTS idx_nodes_source ON nodes(source_file)"
        )
        self.con.execute(
            "CREATE INDEX IF NOT EXISTS idx_nodes_language ON nodes(language)"
        )
        self.con.execute("CREATE INDEX IF NOT EXISTS idx_edges_type ON edges(type)")
        self.con.execute("CREATE INDEX IF NOT EXISTS idx_edges_from ON edges(from_id)")
        self.con.execute("CREATE INDEX IF NOT EXISTS idx_edges_to ON edges(to_id)")
        self.con.execute(
            "CREATE INDEX IF NOT EXISTS idx_meta_hash ON meta(source_hash)"
        )

        # Load German stopwords
        print("  German stopwords...", file=sys.stderr)
        stopwords_path = Path(".brain_graph/config/stopwords_de.md")
        if stopwords_path.exists():
            # Create stopwords table
            self.con.execute("DROP TABLE IF EXISTS german_stopwords")
            self.con.execute("CREATE TABLE german_stopwords (word VARCHAR)")

            # Load stopwords from file
            stopwords = stopwords_path.read_text(encoding="utf-8").strip().split("\n")
            stopwords = [w.strip() for w in stopwords if w.strip()]

            # Insert in batches for efficiency
            self.con.executemany(
                "INSERT INTO german_stopwords VALUES (?)", [(w,) for w in stopwords]
            )
            print(f"    Loaded {len(stopwords)} German stopwords", file=sys.stderr)
            stopwords_table = "german_stopwords"
        else:
            print(
                f"    Warning: {stopwords_path} not found, using no stopwords",
                file=sys.stderr,
            )
            stopwords_table = "none"

        # Get text node count
        text_count = self.con.execute(
            "SELECT COUNT(*) FROM nodes WHERE text IS NOT NULL OR summary IS NOT NULL"
        ).fetchone()[0]
        print(f"  FTS index (BM25) for {text_count} text nodes...", file=sys.stderr)

        # Create FTS index with German stemmer and stopwords
        start = time.time()
        try:
            self.con.execute(
                f"""
                PRAGMA create_fts_index(
                    'nodes', 'id', 'text', 'summary', 'title', 'description',
                    stemmer='german',
                    stopwords='{stopwords_table}',
                    ignore='(\\.|[^a-zäöüß])+',
                    strip_accents=1,
                    lower=1,
                    overwrite=1
                )
                """
            )
            elapsed = time.time() - start
            print(f"    FTS index built in {elapsed:.1f}s", file=sys.stderr)
        except duckdb.Error as e:
            print(
                f"    Warning: Could not build FTS index, skipping ({e})",
                file=sys.stderr,
            )

        print("  Property graph...", file=sys.stderr)
        try:
            self.con.execute("DROP PROPERTY GRAPH IF EXISTS brain_graph;")
            # This DuckPGQ build supports a reduced CREATE PROPERTY GRAPH grammar
            # (no LABEL/PROPERTIES clauses, and requires REFERENCES on keys).
            self.con.execute(
                """
                CREATE PROPERTY GRAPH brain_graph
                VERTEX TABLES (nodes)
                EDGE TABLES (
                    edges
                        SOURCE KEY (from_id) REFERENCES nodes(id)
                        DESTINATION KEY (to_id) REFERENCES nodes(id)
                );
            """
            )
        except duckdb.Error as e:
            print(
                f"  Warning: Property graph creation failed, skipping ({e})",
                file=sys.stderr,
            )

    def stats(self):
        """Print database statistics."""
        print("\n=== Database Statistics ===", file=sys.stderr)

        result = self.con.execute(
            "SELECT type, COUNT(*) as count FROM nodes GROUP BY type"
        ).fetchall()
        print("\nNodes by type:", file=sys.stderr)
        for row in result:
            print(f"  {row[0]}: {row[1]}", file=sys.stderr)

        result = self.con.execute(
            "SELECT type, COUNT(*) as count FROM edges GROUP BY type"
        ).fetchall()
        print("\nEdges by type:", file=sys.stderr)
        for row in result:
            print(f"  {row[0]}: {row[1]}", file=sys.stderr)

        result = self.con.execute(
            "SELECT COUNT(*) FROM chunk_embeddings_256d"
        ).fetchone()
        print(f"\nChunk embeddings (256d): {result[0]}", file=sys.stderr)

        result = self.con.execute(
            "SELECT COUNT(*) FROM taxonomy_embeddings_256d"
        ).fetchone()
        print(f"Taxonomy embeddings (256d): {result[0]}", file=sys.stderr)

        result = self.con.execute("SELECT COUNT(*) FROM embedding_sources").fetchone()
        print(f"Embedding sources (Parquet): {result[0]}", file=sys.stderr)


def main():
    start = time.perf_counter()
    parser = argparse.ArgumentParser(description="Build brain-graph DuckDB database")
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path(".brain_graph/data"),
        help="Base data directory (default: .brain_graph/data)",
    )
    parser.add_argument(
        "--documents-dir",
        type=Path,
        default=None,
        help="Directory containing *.document.json files (default: <data-dir>/documents)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output database file (default: :memory: for in-memory)",
    )
    parser.add_argument(
        "--embedding-dim",
        type=int,
        default=256,
        help="Target dimension for Matryoshka truncation (default: 256)",
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

    try:
        # Build database
        db_path = str(args.output) if args.output else ":memory:"
        print(f"Building database: {db_path}", file=sys.stderr)
        print(f"Data directory: {args.data_dir}", file=sys.stderr)
        print(f"Embedding dimension: {args.embedding_dim}", file=sys.stderr)

        db = BrainGraphDB(db_path)
        db.import_directory_fast(
            args.data_dir,
            documents_dir=args.documents_dir,
            target_dim=args.embedding_dim,
        )
        db.build_indexes()
        db.stats()

        # Collect stats for JSON output
        nodes_by_type = dict(
            db.con.execute("SELECT type, COUNT(*) FROM nodes GROUP BY type").fetchall()
        )
        edges_by_type = dict(
            db.con.execute("SELECT type, COUNT(*) FROM edges GROUP BY type").fetchall()
        )
        result = ok_result(
            "build_db",
            output={"db": str(args.output) if args.output else None},
            data_dir=str(args.data_dir),
            documents_dir=str(args.documents_dir or (args.data_dir / "documents")),
            embedding_dim=args.embedding_dim,
            mode="fast",
            counts={
                "nodes_by_type": nodes_by_type,
                "edges_by_type": edges_by_type,
                "chunk_embeddings_256d": db.con.execute(
                    "SELECT COUNT(*) FROM chunk_embeddings_256d"
                ).fetchone()[0],
                "taxonomy_embeddings_256d": db.con.execute(
                    "SELECT COUNT(*) FROM taxonomy_embeddings_256d"
                ).fetchone()[0],
                "embedding_sources": db.con.execute(
                    "SELECT COUNT(*) FROM embedding_sources"
                ).fetchone()[0],
                "doc_links": db.con.execute(
                    "SELECT COUNT(*) FROM doc_links"
                ).fetchone()[0],
                "doc_backlinks": db.con.execute(
                    "SELECT COUNT(*) FROM doc_backlinks"
                ).fetchone()[0],
                "meta": db.con.execute("SELECT COUNT(*) FROM meta").fetchone()[0],
            },
            duration_ms=ms_since(start),
        )
        if args.format == "json":
            emit_json(result, pretty=args.pretty)

        if args.output:
            print(f"\nDatabase created: {args.output}", file=sys.stderr)
            print("Use DuckDB CLI or Python to query:", file=sys.stderr)
            print(f"  duckdb {args.output}", file=sys.stderr)
        else:
            print(
                "\nIn-memory database created. Connection available in `db.con`",
                file=sys.stderr,
            )
            print("To use:", file=sys.stderr)
            print(
                "  from brain_graph.db.db_builder import BrainGraphDB", file=sys.stderr
            )
            print("  db = BrainGraphDB(':memory:')", file=sys.stderr)
            print(
                "  db.import_directory_fast(Path('.brain_graph/data'))", file=sys.stderr
            )
            print("  db.build_indexes()", file=sys.stderr)
        return 0
    except Exception as e:
        if args.format == "json":
            emit_json(
                error_result(
                    "build_db",
                    e,
                    include_traceback=args.debug,
                    duration_ms=ms_since(start),
                ),
                pretty=args.pretty,
            )
            return 1
        raise


if __name__ == "__main__":
    raise SystemExit(main())
