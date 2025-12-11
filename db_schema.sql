-- =============================================================================
-- Brain Graph 2: DuckDB Schema
-- =============================================================================
-- Complete schema for in-memory knowledge graph with semantic search,
-- full-text search, and property graph queries.
--
-- Extensions: VSS (Vector Similarity), FTS (Full-Text), DuckPGQ (Graph)
-- =============================================================================

-- Extensions (must be installed/loaded before use)
INSTALL vss;
LOAD vss;
INSTALL fts;
LOAD fts;

-- =============================================================================
-- CORE TABLES
-- =============================================================================

-- Nodes table (all node types: section, chunk, code, entity, category)
CREATE TABLE nodes (
    -- Identity
    id VARCHAR PRIMARY KEY,
    ulid VARCHAR NOT NULL,
    type VARCHAR NOT NULL,  -- section, chunk, code, entity, category

    -- Source tracking
    source_file VARCHAR,    -- original .md file

    -- Content (varies by type)
    title VARCHAR,          -- sections, categories
    text VARCHAR,           -- chunks, entities
    description VARCHAR,    -- categories
    keywords VARCHAR[],     -- categories

    -- Chunk-specific
    language VARCHAR,       -- de, en, etc.
    char_start INTEGER,     -- position in source
    char_end INTEGER,
    summary VARCHAR,        -- LLM-generated summary

    -- Entity-specific
    entity_type VARCHAR,    -- PER, ORG, LOC, PRODUCT, etc.
    occurrences INTEGER,    -- how often entity appears
    mentioned_in VARCHAR[], -- chunk IDs where entity appears

    -- Section/Code-specific
    level INTEGER,          -- heading level (1-6)
    code_language VARCHAR,  -- python, js, etc.

    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Edges table (all relationship types)
CREATE TABLE edges (
    -- Identity
    id INTEGER PRIMARY KEY,
    from_id VARCHAR NOT NULL,
    to_id VARCHAR NOT NULL,
    type VARCHAR NOT NULL,  -- parent_of, contains, next, mentions, categorized_as, related

    -- Weights and scores
    weight DOUBLE,
    similarity DOUBLE,
    overlap_chars INTEGER,

    -- Source tracking
    source_file VARCHAR,

    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Foreign keys
    FOREIGN KEY (from_id) REFERENCES nodes(id),
    FOREIGN KEY (to_id) REFERENCES nodes(id)
);

-- =============================================================================
-- EMBEDDING TABLES (Matryoshka Strategy)
-- =============================================================================

-- Reduced-dimension embeddings for fast retrieval (in-memory)
CREATE TABLE chunk_embeddings_256d (
    chunk_id VARCHAR PRIMARY KEY,
    embedding DOUBLE[256],  -- Matryoshka truncated to 256 dims
    source_file VARCHAR,

    FOREIGN KEY (chunk_id) REFERENCES nodes(id)
);

-- Taxonomy embeddings (reduced)
CREATE TABLE taxonomy_embeddings_256d (
    category_id VARCHAR PRIMARY KEY,
    embedding DOUBLE[256],

    FOREIGN KEY (category_id) REFERENCES nodes(id)
);

-- =============================================================================
-- PARQUET REFERENCE TABLE (for re-ranking with full vectors)
-- =============================================================================

-- References to Parquet files with full 1024-dim embeddings
CREATE TABLE embedding_sources (
    source_file VARCHAR,
    parquet_path VARCHAR,
    embedding_dim INTEGER DEFAULT 1024,
    model VARCHAR,
    created_at TIMESTAMP
);

-- =============================================================================
-- INDEXES
-- =============================================================================

-- VSS indexes for semantic search (HNSW = Hierarchical Navigable Small World)
CREATE INDEX idx_chunk_embeddings_hnsw
    ON chunk_embeddings_256d
    USING HNSW (embedding);

CREATE INDEX idx_taxonomy_embeddings_hnsw
    ON taxonomy_embeddings_256d
    USING HNSW (embedding);

-- Standard B-tree indexes for filtering
CREATE INDEX idx_nodes_type ON nodes(type);
CREATE INDEX idx_nodes_source ON nodes(source_file);
CREATE INDEX idx_nodes_language ON nodes(language);
CREATE INDEX idx_edges_type ON edges(type);
CREATE INDEX idx_edges_from ON edges(from_id);
CREATE INDEX idx_edges_to ON edges(to_id);

-- =============================================================================
-- FULL-TEXT SEARCH
-- =============================================================================

-- FTS index on chunk text content
PRAGMA create_fts_index(
    'nodes',
    'id',
    'text', 'summary', 'title', 'description',
    overwrite=1
);

-- =============================================================================
-- PROPERTY GRAPH (DuckPGQ)
-- =============================================================================

-- Define property graph for DuckPGQ queries
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
);

-- =============================================================================
-- QUERY EXAMPLES
-- =============================================================================

/*
-- 1. Semantic Search (256d, fast)
SELECT
    n.id,
    n.text,
    n.summary,
    array_cosine_similarity(e.embedding, ?::DOUBLE[256]) as similarity
FROM chunk_embeddings_256d e
JOIN nodes n ON e.chunk_id = n.id
WHERE n.type = 'chunk'
ORDER BY similarity DESC
LIMIT 20;

-- 2. Full-Text Search (BM25)
SELECT
    id,
    text,
    summary,
    fts_main_nodes.match_bm25(id, 'jazz improvisation') as score
FROM nodes
WHERE fts_main_nodes.match_bm25(id, 'jazz improvisation') IS NOT NULL
ORDER BY score DESC
LIMIT 10;

-- 3. Hybrid Search (Semantic + BM25)
WITH semantic_results AS (
    SELECT
        n.id,
        array_cosine_similarity(e.embedding, ?::DOUBLE[256]) as sem_score
    FROM chunk_embeddings_256d e
    JOIN nodes n ON e.chunk_id = n.id
    WHERE n.type = 'chunk'
    ORDER BY sem_score DESC
    LIMIT 50
),
bm25_results AS (
    SELECT
        id,
        fts_main_nodes.match_bm25(id, ?) as bm25_score
    FROM nodes
    WHERE fts_main_nodes.match_bm25(id, ?) IS NOT NULL
    ORDER BY bm25_score DESC
    LIMIT 50
)
SELECT
    COALESCE(s.id, b.id) as id,
    n.text,
    n.summary,
    COALESCE(s.sem_score, 0) * 0.7 + COALESCE(b.bm25_score, 0) * 0.3 as hybrid_score
FROM semantic_results s
FULL OUTER JOIN bm25_results b ON s.id = b.id
JOIN nodes n ON n.id = COALESCE(s.id, b.id)
ORDER BY hybrid_score DESC
LIMIT 10;

-- 4. Metadata Filtering
SELECT
    n.id,
    n.text,
    n.summary,
    n.language,
    c.to_id as category,
    array_cosine_similarity(e.embedding, ?::DOUBLE[256]) as similarity
FROM chunk_embeddings_256d e
JOIN nodes n ON e.chunk_id = n.id
LEFT JOIN edges c ON c.from_id = n.id AND c.type = 'categorized_as'
WHERE
    n.type = 'chunk'
    AND n.language = 'de'
    AND c.to_id = 'musik'
ORDER BY similarity DESC
LIMIT 10;

-- 5. Graph Traversal (DuckPGQ)
-- Find all chunks in a section and their categories
SELECT
    n.id,
    n.type,
    n.text,
    e.type as relationship,
    target.title as related_to
FROM graph_table (brain_graph
    MATCH (n:Node)-[e:Relationship]->(target:Node)
    WHERE n.id = 'sec_103d1d72'
    COLUMNS (n.id, n.type, n.text, e.type, target.title)
);

-- Path query: Find connections between two nodes
SELECT path
FROM graph_table (brain_graph
    MATCH path = (start:Node)-[e:Relationship*1..3]->(end:Node)
    WHERE start.id = 'chunk_0aa6f3ec' AND end.type = 'category'
    COLUMNS (path)
);
*/
