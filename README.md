# Brain Graph

Semantic knowledge base with vector search and graph queries.

## Installation

```bash
pip install -e .
pip install -e ".[dev]"  # pytest/ruff/black
```

## Usage

### Search
```bash
# Hybrid search (semantic + BM25)
brain search "your query"

# Fuzzy search only
brain search fuzzy "your query"

# Semantic search only
brain search semantic "your query"
```

### Pipeline Processing
```bash
# Process markdown file
brain pipeline chunk file.md
brain pipeline embed file.md
brain pipeline taxonomy-embed
brain pipeline taxonomy file.md
brain pipeline summarize file.md

# Process all files
brain pipeline process-all
```

### Database
```bash
# Build database from processed files
brain db build

# Test database
brain db test
```

### Search Daemon (for better performance)
```bash
# Start daemon in background
brain daemon start -b

# Check status
brain daemon status

# Stop daemon
brain daemon stop
```

### Agent Commands
```bash
# Get documentation for a tool
brain agent docs embedder
brain agent docs searcher --format=json
```

## Configuration

Create `.brain_graph/config/config.json` (or `config.json` as fallback):

```json
{
  "embedding_base_url": "http://localhost:11434/v1",
  "embedding_api_key": "ollama",
  "embedding_model": "jina/jina-embeddings-v3:latest",
  "llm_base_url": "http://localhost:11434/v1",
  "llm_api_key": "ollama",
  "llm_model": "qwen2.5:14b"
}
```

## Architecture

- **brain_graph/pipeline/** - Document processing pipeline (chunking, embedding, etc.)
- **brain_graph/db/** - DuckDB database builder and queries
- **brain_graph/search/** - Search interfaces (semantic, BM25, fuzzy, hybrid)
- **brain_graph/cli/** - Command-line interface
- **brain_graph/utils/** - Utilities and helpers

## Features

- Semantic search with matryoshka embeddings (256d fast search, 1024d reranking)
- BM25 full-text search with German stemming
- Fuzzy search with edit distance
- Hybrid search combining multiple strategies
- Graph-based knowledge representation
- Link extraction and backlink computation
- Taxonomy-based categorization
- Named entity recognition
- Persistent search daemon for low-latency queries

## License

MIT
