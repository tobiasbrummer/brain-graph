#!/usr/bin/env python3
"""
Test script for brain-graph DuckDB database.

Tests database structure, indexes, and query examples.

Usage:
    python test_db.py  # uses in-memory DB from test_data/output
    python test_db.py brain.duckdb  # tests existing persistent DB
"""

import sys
from pathlib import Path

import duckdb
from build_db import BrainGraphDB


def test_database_structure(con: duckdb.DuckDBPyConnection):
    """Test that all tables and indexes exist."""
    print("\n=== Testing Database Structure ===\n")

    # Check tables
    tables = con.execute("SHOW TABLES").fetchall()
    table_names = [t[0] for t in tables]

    required_tables = [
        'nodes', 'edges',
        'chunk_embeddings_256d', 'taxonomy_embeddings_256d',
        'embedding_sources', 'meta'
    ]

    print("Tables:")
    for table in required_tables:
        status = "✓" if table in table_names else "✗"
        print(f"  {status} {table}")

    # Check indexes
    indexes = con.execute("SELECT * FROM duckdb_indexes()").fetchall()
    print(f"\nIndexes: {len(indexes)} total")

    # Check extensions
    extensions = con.execute("SELECT * FROM duckdb_extensions() WHERE loaded").fetchall()
    print(f"\nExtensions loaded:")
    for ext in extensions:
        print(f"  - {ext[0]}")


def test_node_counts(con: duckdb.DuckDBPyConnection):
    """Test node and edge counts."""
    print("\n=== Testing Node and Edge Counts ===\n")

    # Nodes by type
    result = con.execute("SELECT type, COUNT(*) FROM nodes GROUP BY type ORDER BY COUNT(*) DESC").fetchall()
    print("Nodes by type:")
    for node_type, count in result:
        print(f"  {node_type}: {count}")

    # Edges by type
    result = con.execute("SELECT type, COUNT(*) FROM edges GROUP BY type ORDER BY COUNT(*) DESC").fetchall()
    print("\nEdges by type:")
    for edge_type, count in result:
        print(f"  {edge_type}: {count}")

    # Embeddings
    chunk_emb_count = con.execute("SELECT COUNT(*) FROM chunk_embeddings_256d").fetchone()[0]
    tax_emb_count = con.execute("SELECT COUNT(*) FROM taxonomy_embeddings_256d").fetchone()[0]
    print(f"\nEmbeddings:")
    print(f"  Chunk embeddings (256d): {chunk_emb_count}")
    print(f"  Taxonomy embeddings (256d): {tax_emb_count}")


def test_semantic_search(con: duckdb.DuckDBPyConnection):
    """Test semantic search with dummy query."""
    print("\n=== Testing Semantic Search (256d) ===\n")

    # Get a random embedding to use as query
    result = con.execute("SELECT embedding FROM chunk_embeddings_256d LIMIT 1").fetchone()
    if not result:
        print("No embeddings found, skipping semantic search test")
        return

    query_emb = result[0]

    # Search
    results = con.execute("""
        SELECT
            n.id,
            n.text,
            array_cosine_similarity(e.embedding, ?::DOUBLE[256]) as similarity
        FROM chunk_embeddings_256d e
        JOIN nodes n ON e.chunk_id = n.id
        WHERE n.type = 'chunk'
        ORDER BY similarity DESC
        LIMIT 5
    """, [query_emb]).fetchall()

    print(f"Found {len(results)} results")
    for i, (chunk_id, text, sim) in enumerate(results, 1):
        text_preview = text[:100] + "..." if len(text) > 100 else text
        print(f"\n{i}. {chunk_id} (sim: {sim:.3f})")
        print(f"   {text_preview}")


def test_fulltext_search(con: duckdb.DuckDBPyConnection):
    """Test full-text search."""
    print("\n=== Testing Full-Text Search (BM25) ===\n")

    # Get a word from existing text
    result = con.execute("""
        SELECT text FROM nodes WHERE text IS NOT NULL AND length(text) > 20 LIMIT 1
    """).fetchone()

    if not result:
        print("No text found, skipping FTS test")
        return

    # Extract first word
    query_word = result[0].split()[0]
    print(f"Searching for: '{query_word}'")

    results = con.execute("""
        SELECT
            id,
            text,
            fts_main_nodes.match_bm25(id, ?) as score
        FROM nodes
        WHERE fts_main_nodes.match_bm25(id, ?) IS NOT NULL
        ORDER BY score DESC
        LIMIT 5
    """, [query_word, query_word]).fetchall()

    print(f"Found {len(results)} results")
    for i, (node_id, text, score) in enumerate(results, 1):
        text_preview = text[:100] + "..." if len(text) > 100 else text
        print(f"\n{i}. {node_id} (score: {score:.3f})")
        print(f"   {text_preview}")


def test_graph_queries(con: duckdb.DuckDBPyConnection):
    """Test property graph queries."""
    print("\n=== Testing Property Graph Queries (DuckPGQ) ===\n")

    # Find a section node
    result = con.execute("SELECT id FROM nodes WHERE type = 'section' LIMIT 1").fetchone()
    if not result:
        print("No sections found, skipping graph test")
        return

    section_id = result[0]
    print(f"Testing with section: {section_id}")

    # Find all nodes connected to this section
    results = con.execute("""
        SELECT
            n.id,
            n.type,
            e.type as relationship,
            target.id as target_id,
            target.type as target_type
        FROM graph_table (brain_graph
            MATCH (n:Node)-[e:Relationship]->(target:Node)
            WHERE n.id = ?
            COLUMNS (n.id, n.type, e.type, target.id, target.type)
        )
        LIMIT 10
    """, [section_id]).fetchall()

    print(f"Found {len(results)} connections")
    for i, (nid, ntype, rel, tid, ttype) in enumerate(results, 1):
        print(f"  {i}. {nid} ({ntype}) --[{rel}]--> {tid} ({ttype})")


def test_metadata_filtering(con: duckdb.DuckDBPyConnection):
    """Test filtering by metadata (language, categories)."""
    print("\n=== Testing Metadata Filtering ===\n")

    # Language filter
    result = con.execute("""
        SELECT language, COUNT(*) FROM nodes WHERE language IS NOT NULL GROUP BY language
    """).fetchall()

    if result:
        print("Nodes by language:")
        for lang, count in result:
            print(f"  {lang}: {count}")

        # Category filter
        result = con.execute("""
            SELECT c.to_id as category, COUNT(*) as count
            FROM edges c
            WHERE c.type = 'categorized_as'
            GROUP BY c.to_id
            ORDER BY count DESC
            LIMIT 5
        """).fetchall()

        if result:
            print("\nTop 5 categories:")
            for cat, count in result:
                print(f"  {cat}: {count} chunks")


def test_meta_table(con: duckdb.DuckDBPyConnection):
    """Test meta table for deduplication."""
    print("\n=== Testing Meta Table ===\n")

    # Count meta entries
    count = con.execute("SELECT COUNT(*) FROM meta").fetchone()[0]
    print(f"Meta entries: {count}")

    if count > 0:
        # Show sample meta data
        result = con.execute("""
            SELECT
                ulid,
                source_file,
                source_hash,
                source_commit,
                source_dirty,
                created_at
            FROM meta
            LIMIT 3
        """).fetchall()

        print("\nSample meta entries:")
        for i, (ulid, file, hash, commit, dirty, created) in enumerate(result, 1):
            print(f"\n  {i}. ULID: {ulid}")
            print(f"     File: {file}")
            print(f"     Hash: {hash}")
            if commit:
                print(f"     Commit: {commit}")
            print(f"     Dirty: {dirty}")
            print(f"     Created: {created}")

        # Test hash lookup (for deduplication)
        sample_hash = result[0][2] if result else None
        if sample_hash:
            dup_check = con.execute("""
                SELECT ulid, source_file
                FROM meta
                WHERE source_hash = ?
            """, [sample_hash]).fetchone()

            print(f"\nHash lookup test (for dedup):")
            print(f"  Query hash: {sample_hash}")
            print(f"  Found: {dup_check[1] if dup_check else 'None'}")


def main():
    if len(sys.argv) > 1:
        # Test existing database
        db_path = sys.argv[1]
        print(f"Testing existing database: {db_path}")
        con = duckdb.connect(db_path)
    else:
        # Build in-memory database
        data_dir = Path(".brain_graph/data")
        print(f"Building in-memory database from {data_dir}...")
        db = BrainGraphDB(":memory:")
        db.import_directory(data_dir)
        db.build_indexes()
        con = db.con

    # Run tests
    try:
        test_database_structure(con)
        test_node_counts(con)
        test_meta_table(con)
        test_semantic_search(con)
        test_fulltext_search(con)
        test_graph_queries(con)
        test_metadata_filtering(con)

        print("\n=== All tests completed ===\n")

    except Exception as e:
        print(f"\nError during testing: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
