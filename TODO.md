# TODOs - Brain Graph 2

## Workflow Implementation

### Deduplication Workflow
- [ ] Implement workflow orchestration that ensures DuckDB index exists before chunker.py
- [ ] Workflow steps:
  1. Check if DuckDB index exists (`.brain_graph/brain.duckdb` or in-memory)
  2. If not: Run `build_db.py --data-dir .brain_graph/data --output .brain_graph/brain.duckdb`
  3. Run `check_duplicate.py input.md --db .brain_graph/brain.duckdb`
  4. If duplicate (exit code 1): Skip or warn
  5. If OK (exit code 0): Run `chunker.py -i input.md`
- [ ] Decision: In-memory (`:memory:`) vs persistent (`brain.duckdb`) for dedup checks?
  - In-memory: Faster, but needs rebuild on each workflow run
  - Persistent: Slower, but only needs incremental updates

### Incremental Index Updates
- [ ] Implement incremental index updates instead of full rebuild
- [ ] Track last_indexed timestamp in meta
- [ ] Only re-import changed/new files

### Automation
- [ ] File watcher for `inbox/` directory
- [ ] Auto-trigger workflow when new .md files appear
- [ ] Email/notification on duplicates

## Pipeline Improvements

### Error Handling
- [ ] Graceful handling when processing steps fail
- [ ] Retry logic for transient failures (LLM API, etc.)
- [ ] Rollback mechanism for partial failures

### Parallel Processing
- [ ] Process multiple documents in parallel
- [ ] Batch embeddings API calls
- [ ] Parallel taxonomy matching

### Testing
- [ ] Unit tests for all core functions
- [ ] Integration tests for full pipeline
- [ ] Test data fixtures

## Features

### Taxonomy
- [ ] Add `importance`, `decay`, `usage` fields to taxonomy
- [ ] Relevance scoring algorithm
- [ ] Temporal decay implementation

### Search
- [ ] Implement hybrid search (semantic + BM25 + graph)
- [ ] Re-ranking with full 1024d vectors
- [ ] Graph-based retrieval (DuckPGQ)

### UI
- [ ] Simple web UI for search
- [ ] Visualization of document graph
- [ ] Browse by category/entity

## Infrastructure

### Performance
- [ ] Benchmark pipeline throughput
- [ ] Optimize embedding truncation
- [ ] Cache LLM results

### Monitoring
- [ ] Log processing times per step
- [ ] Track error rates
- [ ] Dashboard for pipeline status

### Documentation
- [ ] README with full pipeline documentation
- [ ] Architecture diagram
- [ ] API documentation for search
