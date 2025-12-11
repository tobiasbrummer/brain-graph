"""
Search utilities for brain-graph-2 DuckDB database.

Modules:
- reranking: Two-stage retrieval with Matryoshka embeddings
"""

from .reranking import rerank_with_full_vectors, semantic_search_with_reranking

__all__ = [
    "rerank_with_full_vectors",
    "semantic_search_with_reranking",
]
