# brain-graph Configuration

Configuration for embedding, chunking, and summarization.

## Embedding

+base_url:<http://localhost:8200/v1>
+model:jina-embeddings-v3-Q4_K_M
+dim:1024
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
