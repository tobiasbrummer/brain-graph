# Session Notes: Code Chunking & Embedding Implementation

## Status: Phase 1-4 Complete ✅

### Completed Work

**Phase 1: Tree-sitter Code Chunking** ✅
- Tree-sitter integration for Python, JavaScript, TypeScript
- Parses code blocks into semantic units: functions, classes, methods
- Extracts signatures, docstrings, parameters
- New edge types: `calls`, `defines` (plus reserved: `imports`, `inherits`)
- Fallback to atomic code blocks if Tree-sitter unavailable
- Files: `chunker.py` (+300 Lines), `code.schema.json`, `edge.schema.json`

**Phase 2: Code Embedder** ✅
- Separate embedding pipeline for code units
- Filter: type IN ('function', 'class', 'method')
- Context: Signature + Docstring + Code body
- Prefix: "Code: " for asymmetric search
- Output: `*.code.parquet`
- Config: `code_embedding_model` (separate from `text_embedding_model`)
- Files: `code_embedder.py` (~260 Lines), `config.md`, `pipeline_cli.py`

**Phase 3: DB Schema & Import** ✅
- `code_embeddings_256d` table with language column
- Import logic in `import_directory()` via UNNEST(d.nodes.codes)
- HNSW index with metric='cosine'
- Files: `db_builder.py` (+90 Lines)
- Refactoring: Removed legacy "fast" suffix from import_directory

**Phase 4: Code Search** ✅
- `code_search()` function in searcher.py (~65 Lines)
- CLI: `--mode code`, `--languages python,javascript`
- Query embedding with "Query:" prefix
- Returns: name, signature, docstring, similarity, language
- Files: `searcher.py` (+78 Lines)

### Current Architecture

```
Markdown with Code Blocks
    ↓
[Chunker + Tree-sitter]
    ↓
*.nodes.json (functions/classes/methods with metadata)
*.edges.json (contains, defines, calls)
    ↓
[Code Embedder]
    ↓
*.code.parquet (768d embeddings)
    ↓
[DB Builder]
    ↓
code_embeddings_256d (HNSW indexed)
    ↓
[Code Search]
```

### Key Decisions Made

1. **Config Naming**: `text_embedding_model`, `code_embedding_model` (future: `image_embedding_model`)
2. **Call Graph**: Implemented in Phase 1 (simple name-based heuristic)
3. **Comments**: Kept in embeddings for context
4. **Multi-file references**: Deferred to later phase

### Configuration

**config.md:**
- Text Embedding: localhost:8200, jina-embeddings-v3-Q8_0 (1024d)
- Code Embedding: localhost:8201, jina-embeddings-v2-base-code-q8_0 (768d)
- Both truncated to 256d for HNSW index

### CLI Usage

```bash
# Chunk with Tree-sitter
brain pipeline chunk file.md

# Embed text chunks
brain pipeline embed file.md

# Embed code units
brain pipeline code-embed file.md

# Build DB
brain db import .brain_graph/data

# Search code
brain search "parse json" --mode code --languages python --limit 5
```

### What's Left (Phase 5)

**Testing & Integration:**
1. End-to-end test: markdown with code → chunk → embed → search
2. Verify Tree-sitter parsing for Python/JS/TS
3. Verify HNSW index utilization (check query plans)
4. Test language filtering
5. Test call graph edges
6. Performance benchmarks

**Optional Enhancements (Future):**
- More languages: Go, Rust, Java, C++
- AST-based call graph (instead of name matching)
- Cross-file imports/calls
- Code complexity metrics
- Method/function search with semantic similarity to docstrings

### Known Issues / Limitations

1. Call graph uses simple name matching (not AST analysis)
2. Code embeddings use separate model (768d) - may need tuning
3. No cross-file reference tracking yet
4. Tree-sitter errors are silently handled (fallback to atomic blocks)

### Files Modified (Summary)

**New Files:**
- `brain_graph/schema/code.schema.json`
- `brain_graph/pipeline/code_embedder.py`
- `brain_graph/utils/embedding_client.py` (from earlier work)

**Modified Files:**
- `brain_graph/pipeline/chunker.py` (+300 Lines)
- `brain_graph/schema/edge.schema.json` (4 new edge types)
- `brain_graph/db/db_builder.py` (+90 Lines)
- `brain_graph/search/searcher.py` (+78 Lines)
- `brain_graph/cli/pipeline_cli.py` (added code-embed)
- `config/config.md` (Text/Code sections)
- `pyproject.toml` (tree-sitter deps)

### Commits Created

1. `33982b7` - Phase 1 & 2: Tree-sitter + Code Embedder (735 Lines added)
2. `c3463dd` - Phase 3: DB Schema & Import (90 Lines added)
3. `5e34e83` - Refactoring: Remove "fast" suffix
4. `58991da` - Phase 4: Code Search (78 Lines added)

### Next Session TODO

1. **Test the full pipeline:**
   - Create test markdown with Python code
   - Run chunk → code-embed → db import → search
   - Verify results

2. **Verify HNSW performance:**
   - Check query plans (`EXPLAIN` in DuckDB)
   - Compare with/without HNSW

3. **Test edge cases:**
   - Nested classes/functions
   - Mixed languages in one file
   - Code without docstrings
   - Very large functions

4. **Documentation:**
   - Update README with code search usage
   - Add examples to docs/

5. **Consider optimizations:**
   - Batch code embedding (currently per-file)
   - Improve call graph detection (AST-based)
   - Add more languages

### Notes

- Context usage was at ~68% (135k/200k tokens) before compaction
- All phases completed successfully without major blockers
- Code quality good: docstrings, error handling, fallbacks
- Ready for real-world testing
