"""Cached OpenAI-compatible embedding client."""
from __future__ import annotations

from functools import lru_cache
from typing import Any

from openai import OpenAI


# Module-level client cache (one client per base_url + api_key combo)
_clients: dict[tuple[str, str], OpenAI] = {}


def get_embedding_client(config: dict[str, Any]) -> OpenAI:
    """
    Get or create a cached OpenAI client for embeddings.

    Args:
        config: Configuration dict with embedding_base_url and embedding_api_key

    Returns:
        Cached OpenAI client instance
    """
    base_url = config["embedding_base_url"]
    api_key = config["embedding_api_key"]
    cache_key = (base_url, api_key)

    if cache_key not in _clients:
        _clients[cache_key] = OpenAI(base_url=base_url, api_key=api_key)

    return _clients[cache_key]


@lru_cache(maxsize=128)
def _cached_embed(text: str, model: str, base_url: str, api_key: str) -> tuple[float, ...]:
    """
    Cached embedding for a single text.

    Uses LRU cache to avoid redundant API calls for identical queries.
    Returns tuple (hashable) instead of list.
    """
    client = _clients.get((base_url, api_key))
    if client is None:
        client = OpenAI(base_url=base_url, api_key=api_key)
        _clients[(base_url, api_key)] = client

    response = client.embeddings.create(input=[text], model=model)
    return tuple(response.data[0].embedding)


def embed_single_cached(text: str, config: dict[str, Any]) -> list[float]:
    """
    Embed a single text with caching.

    Useful for query embeddings that may be repeated.

    Args:
        text: Text to embed
        config: Configuration dict

    Returns:
        Embedding as list of floats
    """
    result = _cached_embed(
        text,
        config["embedding_model"],
        config["embedding_base_url"],
        config["embedding_api_key"],
    )
    return list(result)


def embed_batch(texts: list[str], config: dict[str, Any]) -> list[list[float]]:
    """
    Embed multiple texts in a batch.

    Does not use cache (batch embeddings are typically unique documents).

    Args:
        texts: List of texts to embed
        config: Configuration dict

    Returns:
        List of embeddings
    """
    client = get_embedding_client(config)
    batch_size = config.get("embedding_batch_size", 32)

    embeddings = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        response = client.embeddings.create(
            input=batch,
            model=config["embedding_model"],
        )
        # Sort by index in case API returns out of order
        batch_embeddings = sorted(response.data, key=lambda x: x.index)
        embeddings.extend([e.embedding for e in batch_embeddings])

    return embeddings


def clear_cache() -> None:
    """Clear the embedding cache."""
    _cached_embed.cache_clear()
    _clients.clear()
