# brain-graph Configuration

Configuration for embedding, chunking, and summarization.

## Text Embedding

+base_url:<http://localhost:8200/v1>
+model:jina-embeddings-v3-Q8_0
+dim:1024
+api_key:unused
+batch_size:16

## Code Embedding

+base_url:<http://localhost:8201/v1>
+model:jina-embeddings-v2-base-code-q8_0
+dim:768
+api_key:unused
+batch_size:16

## Chunking

+target_tokens:384
+min_tokens:100
+overlap_tokens:50
+language:de

## Summary

+base_url:<http://localhost:8100/v1>
+model:Qwen3-VL-4B-Thinking-Q4_K_M
+api_key:unused

## Reranker

+base_url:<http://localhost:8300/v1>
+model:jina-reranker-v2-base-multilingual-q8_0
+api_key:unused
