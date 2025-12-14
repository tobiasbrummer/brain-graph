"""
Search utilities for brain-graph-2 DuckDB database.

Modules:
- reranking: Two-stage retrieval with Matryoshka embeddings
"""

from .search import fuzzy_search, semantic_search, bm25_search, embed_query
from .reranking import rerank_with_full_vectors, semantic_search_with_reranking

__all__ = [
    "rerank_with_full_vectors",
    "semantic_search_with_reranking",
    "fuzzy_search",
    "semantic_search",
    "bm25_search",
    "embed_query",
]
