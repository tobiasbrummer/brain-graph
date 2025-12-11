#!/usr/bin/env python3
"""
Build in-memory DuckDB database from brain-graph-2 pipeline outputs.

Creates an in-memory database with:
- Vector similarity search (VSS) with Matryoshka embeddings (256d)
- Full-text search (FTS/BM25)
- Property graph queries (DuckPGQ)
- Reference to full 1024d vectors in Parquet for re-ranking

Usage:
    python build_db.py --data-dir test_data/output
    python build_db.py --data-dir test_data/output --output brain.duckdb  # persistent mode
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import duckdb
import pyarrow.parquet as pq


def truncate_embedding(full_vector: list[float], target_dim: int = 256) -> list[float]:
    """
    Truncate Matryoshka embedding to smaller dimension.

    Jina v3 embeddings are trained with Matryoshka Representation Learning,
    meaning the first N dimensions retain semantic information.
    """
    return full_vector[:target_dim]


class BrainGraphDB:
    """Builds and manages the brain-graph DuckDB database."""

    def __init__(self, db_path: str = ":memory:"):
        """Initialize database connection."""
        self.con = duckdb.connect(db_path)
        self._setup_extensions()
        self._create_schema()

    def _setup_extensions(self):
        """Install and load required extensions."""
        print("Setting up DuckDB extensions...", file=sys.stderr)
        self.con.execute("INSTALL vss;")
        self.con.execute("LOAD vss;")
        self.con.execute("INSTALL fts;")
        self.con.execute("LOAD fts;")

    def _create_schema(self):
        """Create all tables and indexes."""
        print("Creating database schema...", file=sys.stderr)

        # Nodes table
        self.con.execute("""
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
        """)

        # Edges table
        self.con.execute("""
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
        """)

        # Chunk embeddings (256d)
        self.con.execute("""
            CREATE TABLE IF NOT EXISTS chunk_embeddings_256d (
                chunk_id VARCHAR PRIMARY KEY,
                embedding DOUBLE[256],
                source_file VARCHAR
            );
        """)

        # Taxonomy embeddings (256d)
        self.con.execute("""
            CREATE TABLE IF NOT EXISTS taxonomy_embeddings_256d (
                category_id VARCHAR PRIMARY KEY,
                embedding DOUBLE[256]
            );
        """)

        # Embedding sources (for re-ranking)
        self.con.execute("""
            CREATE TABLE IF NOT EXISTS embedding_sources (
                source_file VARCHAR,
                parquet_path VARCHAR,
                embedding_dim INTEGER DEFAULT 1024,
                model VARCHAR,
                created_at TIMESTAMP
            );
        """)

        # Meta table (for deduplication and tracking)
        self.con.execute("""
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
        """)

    def import_nodes(self, nodes_path: Path, source_file: str):
        """Import nodes from JSON."""
        with open(nodes_path, encoding="utf-8") as f:
            nodes = json.load(f)

        for node in nodes:
            self.con.execute("""
                INSERT OR REPLACE INTO nodes (
                    id, ulid, type, source_file,
                    title, text, description, keywords,
                    language, char_start, char_end, summary,
                    entity_type, occurrences, mentioned_in,
                    level, code_language
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, [
                node.get('id'),
                node.get('ulid'),
                node.get('type'),
                source_file,
                node.get('title'),
                node.get('text'),
                node.get('description'),
                node.get('keywords', []),
                node.get('language'),
                node.get('char_start'),
                node.get('char_end'),
                node.get('summary'),
                node.get('entity_type'),
                node.get('occurrences'),
                node.get('mentioned_in', []),
                node.get('level'),
                node.get('code_language', node.get('language') if node.get('type') == 'code' else None)
            ])

    def import_edges(self, edges_path: Path, source_file: str, edge_id_offset: int = 0):
        """Import edges from JSON."""
        with open(edges_path, encoding="utf-8") as f:
            edges = json.load(f)

        for i, edge in enumerate(edges):
            self.con.execute("""
                INSERT OR REPLACE INTO edges (
                    id, from_id, to_id, type,
                    weight, similarity, overlap_chars, source_file
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, [
                edge_id_offset + i,
                edge['from'],
                edge['to'],
                edge['type'],
                edge.get('weight'),
                edge.get('similarity'),
                edge.get('overlap_chars'),
                source_file
            ])

        return edge_id_offset + len(edges)

    def import_embeddings(self, parquet_path: Path, source_file: str, target_dim: int = 256):
        """
        Import embeddings from Parquet, truncating to target dimension.
        """
        table = pq.read_table(parquet_path)
        df = table.to_pandas()

        # Get metadata
        metadata = table.schema.metadata or {}
        model = metadata.get(b'model', b'unknown').decode('utf-8')
        dim = int(metadata.get(b'dim', b'1024').decode('utf-8'))

        # Register Parquet source
        self.con.execute("""
            INSERT INTO embedding_sources (source_file, parquet_path, embedding_dim, model, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, [source_file, str(parquet_path), dim, model, datetime.now(timezone.utc)])

        # Import truncated embeddings
        for _, row in df.iterrows():
            chunk_id = row['chunk_idx'] if isinstance(row['chunk_idx'], str) else f"chunk_{row['chunk_idx']:08x}"
            embedding_truncated = truncate_embedding(row['embedding'], target_dim)

            self.con.execute("""
                INSERT OR REPLACE INTO chunk_embeddings_256d (chunk_id, embedding, source_file)
                VALUES (?, ?, ?)
            """, [chunk_id, embedding_truncated, source_file])

    def import_meta(self, meta: dict):
        """Import meta data from meta.json."""
        self.con.execute("""
            INSERT OR REPLACE INTO meta (
                ulid, source_file, source_hash,
                source_commit, source_commit_date, source_dirty,
                created_at, modified_at, uses, importance, decay
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            meta.get('ulid'),
            meta.get('source_file'),
            meta.get('source_hash'),
            meta.get('source_commit'),
            meta.get('source_commit_date'),
            meta.get('source_dirty'),
            meta.get('created_at'),
            meta.get('modified_at'),
            meta.get('uses'),
            meta.get('importance'),
            meta.get('decay')
        ])

    def import_taxonomy(
        self,
        nodes_path: Path = Path("data/taxonomy.nodes.json"),
        parquet_path: Path = Path("data/taxonomy.parquet"),
        target_dim: int = 256
    ):
        """Import taxonomy nodes and embeddings."""
        if not nodes_path.exists() or not parquet_path.exists():
            print(f"Warning: Taxonomy files not found, skipping", file=sys.stderr)
            return

        # Import taxonomy nodes
        with open(nodes_path, encoding="utf-8") as f:
            categories = json.load(f)

        for cat in categories:
            self.con.execute("""
                INSERT OR REPLACE INTO nodes (id, ulid, type, title, description, keywords)
                VALUES (?, ?, 'category', ?, ?, ?)
            """, [
                cat['id'],
                cat['ulid'],
                cat['title'],
                cat['description'],
                cat['keywords']
            ])

        # Import taxonomy embeddings
        table = pq.read_table(parquet_path)
        df = table.to_pandas()

        for _, row in df.iterrows():
            embedding_truncated = truncate_embedding(row['embedding'], target_dim)

            self.con.execute("""
                INSERT OR REPLACE INTO taxonomy_embeddings_256d (category_id, embedding)
                VALUES (?, ?)
            """, [row['category_id'], embedding_truncated])

    def import_directory(self, data_dir: Path):
        """
        Import all pipeline outputs from new .brain_graph/data structure.

        Expected structure:
        .brain_graph/data/
        ├── nodes/YYYY-MM/{slug}-{ulid}.nodes.json
        ├── edges/YYYY-MM/{slug}-{ulid}.edges.json
        ├── embeddings/YYYY-MM/{slug}-{ulid}.parquet
        ├── meta/YYYY-MM/{slug}-{ulid}.meta.json
        └── ner/
            ├── nodes/YYYY-MM/{slug}-{ulid}.ner.nodes.json
            └── edges/YYYY-MM/{slug}-{ulid}.ner.edges.json
        """
        # Find all nodes files (these are the canonical source)
        nodes_dir = data_dir / "nodes"
        if not nodes_dir.exists():
            print(f"Warning: Nodes directory not found: {nodes_dir}", file=sys.stderr)
            return

        nodes_files = list(nodes_dir.rglob("*.nodes.json"))
        if not nodes_files:
            print(f"Warning: No nodes files found in {nodes_dir}", file=sys.stderr)
            return

        edge_id_offset = 0

        for nodes_file in sorted(nodes_files):
            # Extract filename base (e.g., "jazz-einfuhrung-a1b2c3")
            filename_base = nodes_file.stem.replace('.nodes', '')
            month_folder = nodes_file.parent.name  # YYYY-MM

            print(f"\nImporting {filename_base} ({month_folder})...", file=sys.stderr)

            # Construct paths to other files
            edges_file = data_dir / "edges" / month_folder / f"{filename_base}.edges.json"
            embeddings_file = data_dir / "embeddings" / month_folder / f"{filename_base}.parquet"
            meta_file = data_dir / "meta" / month_folder / f"{filename_base}.meta.json"
            ner_nodes_file = data_dir / "ner" / "nodes" / month_folder / f"{filename_base}.ner.nodes.json"
            ner_edges_file = data_dir / "ner" / "edges" / month_folder / f"{filename_base}.ner.edges.json"

            # Load and import meta
            source_file = filename_base
            if meta_file.exists():
                meta = json.loads(meta_file.read_text(encoding="utf-8"))
                source_file = meta.get("source_file", filename_base)
                print(f"  Meta: {meta_file.name}", file=sys.stderr)
                self.import_meta(meta)

            # Import nodes
            print(f"  Nodes: {nodes_file.name}", file=sys.stderr)
            self.import_nodes(nodes_file, source_file)

            # Import edges
            if edges_file.exists():
                print(f"  Edges: {edges_file.name}", file=sys.stderr)
                edge_id_offset = self.import_edges(edges_file, source_file, edge_id_offset)

            # Import NER nodes and edges
            if ner_nodes_file.exists():
                print(f"  NER Nodes: {ner_nodes_file.name}", file=sys.stderr)
                self.import_nodes(ner_nodes_file, source_file)

            if ner_edges_file.exists():
                print(f"  NER Edges: {ner_edges_file.name}", file=sys.stderr)
                edge_id_offset = self.import_edges(ner_edges_file, source_file, edge_id_offset)

            # Import embeddings
            if embeddings_file.exists():
                print(f"  Embeddings: {embeddings_file.name}", file=sys.stderr)
                self.import_embeddings(embeddings_file, source_file)

        # Import taxonomy
        print("\nImporting taxonomy...", file=sys.stderr)
        self.import_taxonomy()

    def build_indexes(self):
        """Build all indexes after data import."""
        print("\nBuilding indexes...", file=sys.stderr)

        print("  VSS indexes (HNSW)...", file=sys.stderr)
        self.con.execute("""
            CREATE INDEX IF NOT EXISTS idx_chunk_embeddings_hnsw
            ON chunk_embeddings_256d
            USING HNSW (embedding)
        """)

        self.con.execute("""
            CREATE INDEX IF NOT EXISTS idx_taxonomy_embeddings_hnsw
            ON taxonomy_embeddings_256d
            USING HNSW (embedding)
        """)

        print("  B-tree indexes...", file=sys.stderr)
        self.con.execute("CREATE INDEX IF NOT EXISTS idx_nodes_type ON nodes(type)")
        self.con.execute("CREATE INDEX IF NOT EXISTS idx_nodes_source ON nodes(source_file)")
        self.con.execute("CREATE INDEX IF NOT EXISTS idx_nodes_language ON nodes(language)")
        self.con.execute("CREATE INDEX IF NOT EXISTS idx_edges_type ON edges(type)")
        self.con.execute("CREATE INDEX IF NOT EXISTS idx_edges_from ON edges(from_id)")
        self.con.execute("CREATE INDEX IF NOT EXISTS idx_edges_to ON edges(to_id)")
        self.con.execute("CREATE INDEX IF NOT EXISTS idx_meta_hash ON meta(source_hash)")

        print("  FTS index (BM25)...", file=sys.stderr)
        self.con.execute("""
            PRAGMA create_fts_index(
                'nodes',
                'id',
                'text', 'summary', 'title', 'description',
                overwrite=1
            )
        """)

        print("  Property graph...", file=sys.stderr)
        self.con.execute("""
            CREATE PROPERTY GRAPH brain_graph
            VERTEX TABLES (
                nodes LABEL Node PROPERTIES (id, type, title, text, language, summary)
            )
            EDGE TABLES (
                edges
                    SOURCE KEY (from_id) REFERENCES nodes (id)
                    DESTINATION KEY (to_id) REFERENCES nodes (id)
                    LABEL Relationship
                    PROPERTIES (type, weight, similarity)
            )
        """)

    def stats(self):
        """Print database statistics."""
        print("\n=== Database Statistics ===", file=sys.stderr)

        result = self.con.execute("SELECT type, COUNT(*) as count FROM nodes GROUP BY type").fetchall()
        print("\nNodes by type:", file=sys.stderr)
        for row in result:
            print(f"  {row[0]}: {row[1]}", file=sys.stderr)

        result = self.con.execute("SELECT type, COUNT(*) as count FROM edges GROUP BY type").fetchall()
        print("\nEdges by type:", file=sys.stderr)
        for row in result:
            print(f"  {row[0]}: {row[1]}", file=sys.stderr)

        result = self.con.execute("SELECT COUNT(*) FROM chunk_embeddings_256d").fetchone()
        print(f"\nChunk embeddings (256d): {result[0]}", file=sys.stderr)

        result = self.con.execute("SELECT COUNT(*) FROM taxonomy_embeddings_256d").fetchone()
        print(f"Taxonomy embeddings (256d): {result[0]}", file=sys.stderr)

        result = self.con.execute("SELECT COUNT(*) FROM embedding_sources").fetchone()
        print(f"Embedding sources (Parquet): {result[0]}", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(description="Build brain-graph DuckDB database")
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path(".brain_graph/data"),
        help="Base data directory (default: .brain_graph/data)"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output database file (default: :memory: for in-memory)"
    )
    parser.add_argument(
        "--embedding-dim",
        type=int,
        default=256,
        help="Target dimension for Matryoshka truncation (default: 256)"
    )

    args = parser.parse_args()

    # Build database
    db_path = str(args.output) if args.output else ":memory:"
    print(f"Building database: {db_path}", file=sys.stderr)
    print(f"Data directory: {args.data_dir}", file=sys.stderr)
    print(f"Embedding dimension: {args.embedding_dim}", file=sys.stderr)

    db = BrainGraphDB(db_path)
    db.import_directory(args.data_dir)
    db.build_indexes()
    db.stats()

    if args.output:
        print(f"\nDatabase created: {args.output}", file=sys.stderr)
        print("Use DuckDB CLI or Python to query:", file=sys.stderr)
        print(f"  duckdb {args.output}", file=sys.stderr)
    else:
        print("\nIn-memory database created. Connection available in `db.con`", file=sys.stderr)
        print("To use:", file=sys.stderr)
        print("  import build_db", file=sys.stderr)
        print("  db = build_db.BrainGraphDB(':memory:')", file=sys.stderr)
        print("  db.import_directory(Path('.brain_graph/data'))", file=sys.stderr)
        print("  db.build_indexes()", file=sys.stderr)


if __name__ == "__main__":
    main()
