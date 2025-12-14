# DuckDB Integration für Brain Graph 2

+doc:planning +project:brain-graph-2

## Überblick

Integration von DuckDB als In-Memory-Datenbank für semantische, Volltext- und Graph-basierte Suche über die brain-graph-2 Pipeline-Outputs.

## Kern-Architektur

### Matryoshka-Strategie
- **In-Memory (DuckDB)**: Reduzierte 256-dim Vektoren für schnelle Retrieval
- **On-Disk (Parquet)**: Volle 1024-dim Vektoren für präzises Re-Ranking
- **Vorteil**: 75% RAM-Einsparung, 90%+ Retrieval-Qualität erhalten

### Drei-Schicht-Ansatz
1. **Retrieval-Layer**: VSS mit 256D (schnell, Top-K Kandidaten)
2. **Re-Ranking-Layer**: 1024D aus Parquet (präzise Sortierung)
3. **Graph-Layer**: DuckPGQ für strukturelle Queries

## DuckDB-Schema

### Core Tables

**nodes** - Alle Node-Typen (section, chunk, code, entity, category)
```sql
CREATE TABLE nodes (
    id VARCHAR PRIMARY KEY,
    ulid VARCHAR NOT NULL,
    type VARCHAR NOT NULL,
    source_file VARCHAR,
    -- Content (varies by type)
    title VARCHAR,
    text VARCHAR,
    description VARCHAR,
    keywords VARCHAR[],
    -- Chunk-specific
    language VARCHAR,
    char_start INTEGER,
    char_end INTEGER,
    summary VARCHAR,
    -- Entity-specific
    entity_type VARCHAR,
    occurrences INTEGER,
    mentioned_in VARCHAR[],
    -- Section/Code-specific
    level INTEGER,
    code_language VARCHAR
);
```

**edges** - Alle Relationen (parent_of, contains, next, mentions, categorized_as, related)
```sql
CREATE TABLE edges (
    id INTEGER PRIMARY KEY,
    from_id VARCHAR NOT NULL,
    to_id VARCHAR NOT NULL,
    type VARCHAR NOT NULL,
    weight DOUBLE,
    similarity DOUBLE,
    overlap_chars INTEGER,
    source_file VARCHAR,
    FOREIGN KEY (from_id) REFERENCES nodes(id),
    FOREIGN KEY (to_id) REFERENCES nodes(id)
);
```

**chunk_embeddings_256d** - Matryoshka-reduzierte Embeddings
```sql
CREATE TABLE chunk_embeddings_256d (
    chunk_id VARCHAR PRIMARY KEY,
    embedding DOUBLE[256],
    source_file VARCHAR,
    FOREIGN KEY (chunk_id) REFERENCES nodes(id)
);
```

**taxonomy_embeddings_256d** - Kategorie-Embeddings
```sql
CREATE TABLE taxonomy_embeddings_256d (
    category_id VARCHAR PRIMARY KEY,
    embedding DOUBLE[256],
    FOREIGN KEY (category_id) REFERENCES nodes(id)
);
```

**embedding_sources** - Referenzen zu Parquet-Files für Re-Ranking
```sql
CREATE TABLE embedding_sources (
    source_file VARCHAR,
    parquet_path VARCHAR,
    embedding_dim INTEGER DEFAULT 1024,
    model VARCHAR,
    created_at TIMESTAMP
);
```

### Extensions & Indexes

**Extensions:**
- `vss` - Vector Similarity Search (HNSW)
- `fts` - Full-Text Search (BM25)
- DuckPGQ - Property Graph Queries (built-in)

**Indexes:**
- HNSW auf chunk_embeddings_256d.embedding
- HNSW auf taxonomy_embeddings_256d.embedding
- B-tree auf nodes(type, source_file, language)
- B-tree auf edges(type, from_id, to_id)
- FTS auf nodes(text, summary, title, description)

**Property Graph:**
```sql
CREATE PROPERTY GRAPH brain_graph
VERTEX TABLES (nodes LABEL Node)
EDGE TABLES (edges LABEL Relationship);
```

## Implementierung

### build_db.py - Haupt-Import-Skript

**Klasse: BrainGraphDB**
- `__init__(db_path)` - DB-Connection + Extensions laden
- `_create_schema()` - Tables erstellen
- `import_nodes(nodes_path, source_file)` - JSON → nodes table
- `import_edges(edges_path, source_file)` - JSON → edges table
- `import_embeddings(parquet_path, source_file, target_dim=256)` - Parquet → truncated embeddings
- `import_taxonomy(nodes_path, parquet_path)` - Taxonomy import
- `import_directory(data_dir)` - Batch-Import aller Dokumente
- `build_indexes()` - Alle Indexes erstellen
- `stats()` - Statistiken ausgeben

**Matryoshka-Truncation:**
```python
def truncate_embedding(full_vector: list[float], target_dim: int = 256) -> list[float]:
    return full_vector[:target_dim]
```

**Directory-Import-Logik:**
- Findet alle `*.md.nodes.json` Dateien
- Verwendet längsten Dateinamen (= am meisten prozessiert)
- Importiert nodes, edges, embeddings für jedes Dokument
- Importiert taxonomy separat

### Re-Ranking-Funktion

```python
def rerank_with_full_vectors(
    candidate_ids: list[str],
    query_embedding_full: list[float],
    parquet_path: str,
    top_k: int = 10
) -> list[dict]:
    """Re-rank mit vollen 1024-dim Vektoren aus Parquet."""
    # Load Parquet, filter to candidates, compute cosine sim
```

## Query-Patterns

### 1. Semantic Search (256d, schnell)
```sql
SELECT n.id, n.text,
       array_cosine_similarity(e.embedding, ?::DOUBLE[256]) as similarity
FROM chunk_embeddings_256d e
JOIN nodes n ON e.chunk_id = n.id
ORDER BY similarity DESC LIMIT 20;
```

### 2. Full-Text Search (BM25)
```sql
SELECT id, text,
       fts_main_nodes.match_bm25(id, 'query') as score
FROM nodes
WHERE fts_main_nodes.match_bm25(id, 'query') IS NOT NULL
ORDER BY score DESC LIMIT 10;
```

### 3. Hybrid Search (Semantic + BM25)
```sql
WITH semantic AS (...), bm25 AS (...)
SELECT id,
       COALESCE(sem_score, 0) * 0.7 + COALESCE(bm25_score, 0) * 0.3 as hybrid_score
FROM semantic FULL OUTER JOIN bm25 USING (id)
ORDER BY hybrid_score DESC;
```

### 4. Metadata-Filterung
```sql
SELECT n.id, n.text, similarity
FROM chunk_embeddings_256d e
JOIN nodes n ON e.chunk_id = n.id
LEFT JOIN edges c ON c.from_id = n.id AND c.type = 'categorized_as'
WHERE n.language = 'de' AND c.to_id = 'musik'
ORDER BY similarity DESC;
```

### 5. Graph-Traversal (DuckPGQ)
```sql
-- Alle Chunks in einer Section + deren Kategorien
SELECT n.id, n.type, e.type, target.title
FROM graph_table (brain_graph
    MATCH (n:Node)-[e:Relationship]->(target:Node)
    WHERE n.id = 'sec_103d1d72'
    COLUMNS (n.id, n.type, e.type, target.title)
);
```

### 6. Hybrid + Graph (Python)
```python
def hybrid_graph_search(db, query_text, expand_depth=1):
    # 1. Hybrid search → Top-5 chunks
    # 2. Graph expansion → Related categories, entities, sections
    # 3. Return expanded context
```

## Verzeichnisstruktur

```
brain-graph-2/
├── build_db.py              # Haupt-Import-Skript (NEU)
├── db_schema.sql            # Schema-Referenz (NEU)
├── search/                  # (NEU, optional für Phase 2)
│   ├── reranking.py         # Re-Ranking mit full vectors
│   ├── hybrid.py            # Hybrid search
│   └── graph.py             # Graph utilities
├── db/
│   └── brain.duckdb         # Generierte DB (optional persistent)
├── data/
│   ├── taxonomy.nodes.json
│   ├── taxonomy.edges.json
│   └── taxonomy.parquet
├── test_data/output/        # Pipeline outputs
└── config.json
```

## Implementierungsschritte

### Phase 1: Basis-Setup
1. `db_schema.sql` erstellen mit vollem Schema
2. `build_db.py` Grundgerüst mit BrainGraphDB-Klasse
3. Extension-Setup (VSS, FTS laden)

### Phase 2: Matryoshka-Integration
4. `truncate_embedding()` Funktion implementieren
5. Parquet-Import mit Truncation
6. `embedding_sources` Table füllen

### Phase 3: Daten-Import
7. `import_nodes()` - JSON → Table
8. `import_edges()` - JSON → Table
9. `import_taxonomy()` - Taxonomy nodes + embeddings
10. `import_directory()` - Batch-Import

### Phase 4: Indexing
11. HNSW-Indexes auf embeddings
12. B-tree-Indexes auf metadata
13. FTS-Index auf text
14. Property Graph Definition

### Phase 5: Re-Ranking-Modul
15. `search/__init__.py` erstellen
16. `search/reranking.py` mit Two-Stage-Retrieval implementieren
17. Integration in Query-Workflows

### Phase 6: Testing
18. Manuelle SQL-Tests im DuckDB CLI
19. Python Test-Script für Validierung
20. Query-Beispiele dokumentieren

## Performance-Ziele

- **RAM-Einsparung**: 75% durch 256d statt 1024d
- **Retrieval-Speed**: <5ms für 256d VSS
- **Re-Ranking**: <50ms für Top-50 Kandidaten mit 1024d
- **Hybrid Query**: <100ms total
- **Graph Traversal**: <10ms in-memory

## Testing-Workflow

```bash
# Build database
python build_db.py --data-dir test_data/output --output brain.duckdb

# Test mit DuckDB CLI
duckdb brain.duckdb
D SELECT COUNT(*) FROM nodes WHERE type='chunk';
D SELECT * FROM nodes WHERE type='category' LIMIT 5;

# Python tests
python test_db.py
```

## Kritische Dateien

- `build_db.py` - Haupt-Import (neu erstellen)
- `db_schema.sql` - Schema-Referenz (neu erstellen)
- `search/reranking.py` - Re-Ranking-Logik (optional, Phase 2)
- `embedder.py` - Referenz für Embedding-API (existiert bereits)

## Finalisierte Entscheidungen

- **DB-Modus**: Rein In-Memory (`:memory:`)
  → DB wird bei jedem Start neu aus Parquet/JSON gebaut
  → Optional: Parameter `--output` für persistent mode beim Testing

- **Re-Ranking**: Vollständig implementieren
  → `search/reranking.py` Modul mit Two-Stage-Retrieval
  → 256d für schnelle Kandidatensuche, 1024d für präzises Re-Ranking

- **Embedding-Dimension**: 256d als Standard
  → Kann experimentell angepasst werden (Parameter `--embedding-dim`)
