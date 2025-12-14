#!/usr/bin/env python3
"""Test script for reranker integration"""

import duckdb
from search.reranking import multiway_search_with_all_reranking
from search import embed_query
from file_utils import load_config

# Load config and DB
config = load_config()
con = duckdb.connect(".brain_graph/brain.duckdb", read_only=True)

# Test query
query = "Saurer Regen"
print(f"Query: {query}\n")

# Get query embedding
print("Generating query embedding...")
query_emb = embed_query(query, config)
print(f"  ✓ Got {len(query_emb)}d embedding\n")

# Test multi-way search with all reranking stages
print("=== Multi-way Search with Full Pipeline ===")
print("Pipeline: Semantic + BM25 + Fuzzy → RRF → 1024d Rerank → Model Rerank\n")

results = multiway_search_with_all_reranking(
    con,
    query,
    query_emb,
    config,
    initial_k=20,  # Retrieve 20 candidates per method
    final_k=5,  # Return top 5
    rerank_with_full=True,  # Use full 1024d vectors
    rerank_with_model_enable=True,  # Use reranker model
)

print(f"\n=== Final Results (Top {len(results)}) ===\n")
for i, r in enumerate(results, 1):
    # Get the highest score available
    score = r.get("rerank_score", r.get("similarity", r.get("rrf_score", 0)))
    score_type = (
        "rerank" if "rerank_score" in r else ("1024d" if "similarity" in r else "rrf")
    )

    print(f"{i}. [{score:.4f} {score_type}] {r['chunk_id']}")

    # Show snippet
    text = r.get("summary") or r.get("text", "")
    snippet = text[:150].replace("\n", " ")
    print(f"   {snippet}...")
    print()

con.close()
