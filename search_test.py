# from search import fuzzy_search
# import duckdb

# con = duckdb.connect(".brain_graph/brain.duckdb")
# results = fuzzy_search(con, "Mashinelles Lehrnen", limit=5)

# for i, r in enumerate(results, 1):
#     print(f"\n{i}. Score: {r['fuzzy_score']:.2f} | {r['matched_terms']} terms")
#     print(f"   ID: {r['chunk_id']}")
#     print(f"   Text: {r['text']}")

# from search import semantic_search, bm25_search, fuzzy_search, embed_query
# from file_utils import load_config
# import duckdb

# config = load_config()
# con = duckdb.connect(".brain_graph/brain.duckdb")
# query = "Neuronale Netze"

# print("=== SEMANTIC ===")
# emb = embed_query(query, config)
# for r in semantic_search(con, emb, 3):
#     print(f"{r['similarity']:.3f} | {r['chunk_id']}")

# print("\n=== BM25 ===")
# for r in bm25_search(con, query, 3):
#     print(f"{r['bm25_score']:.3f} | {r['chunk_id']}")

# print("\n=== FUZZY (mit Tippfehler) ===")
# for r in fuzzy_search(con, "Neuronale Netzee", 3):
#     print(f"{r['fuzzy_score']:.2f} | {r['chunk_id']}")

from search.reranking import multiway_search_with_rrf
from search import embed_query
from file_utils import load_config
import duckdb

config = load_config()
con = duckdb.connect(".brain_graph/brain.duckdb")
query = "Deep Learning"
emb = embed_query(query, config)

results = multiway_search_with_rrf(
    con, query, emb, initial_k=20, final_k=5, rerank_with_full=True
)

for i, r in enumerate(results, 1):
    score = r.get("similarity", r.get("rrf_score", 0))
    reranked = "✓" if r.get("reranked") else "○"
    print(f"{i}. [{score:.3f}] {reranked} {r['chunk_id']}")
    print(f"   {r['text'][:150]}...\n")
