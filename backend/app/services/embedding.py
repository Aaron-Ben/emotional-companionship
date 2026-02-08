"""Embedding service for vectorizing text with batching and concurrency support."""

import asyncio
import json
import os
from typing import List, Dict, Optional, Union
import logging

import httpx
from tiktoken import get_encoding

logger = logging.getLogger(__name__)

# Configuration from environment
EMBEDDING_MAX_TOKEN = int(os.getenv("WHITELIST_EMBEDDING_MODEL_MAX_TOKEN", "8000"))
SAFE_MAX_TOKENS = int(EMBEDDING_MAX_TOKEN * 0.85)
MAX_BATCH_ITEMS = int(os.getenv("WHITELIST_EMBEDDING_MODEL_LIST", "10"))
DEFAULT_CONCURRENCY = int(os.getenv("TAG_VECTORIZE_CONCURRENCY", "5"))

# Initialize tiktoken encoding
_encoding = get_encoding("cl100k_base")


class EmbeddingConfig:
    """Configuration for embedding service."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "text-embedding-v3",
        api_url: Optional[str] = None,
        max_tokens: int = SAFE_MAX_TOKENS,
        max_batch_items: int = MAX_BATCH_ITEMS,
        concurrency: int = DEFAULT_CONCURRENCY,
    ):
        """
        Initialize embedding configuration.

        Args:
            api_key: API key for embedding service
            model: Model name for embeddings
            api_url: Base URL for embedding API
            max_tokens: Maximum tokens per batch
            max_batch_items: Maximum items per batch
            concurrency: Number of concurrent requests
        """
        self.api_key = api_key
        self.model = model
        self.api_url = api_url
        self.max_tokens = max_tokens
        self.max_batch_items = max_batch_items
        self.concurrency = concurrency


class EmbeddingService:
    """Service for generating text embeddings with batching and concurrency."""

    def __init__(self, config: Optional[Union[EmbeddingConfig, Dict]] = None):
        """
        Initialize embedding service.

        Args:
            config: Configuration object or dict
        """
        if config is None:
            self.config = EmbeddingConfig()
        elif isinstance(config, dict):
            self.config = EmbeddingConfig(**config)
        else:
            self.config = config

        # Set defaults from environment if not provided
        if not self.config.api_key:
            self.config.api_key = os.getenv("OPENROUTER_API_KEY")
        if not self.config.api_url:
            self.config.api_url = os.getenv("API_URL", "https://openrouter.ai/api/v1")
        if not self.config.model or self.config.model == "text-embedding-v3":
            self.config.model = os.getenv("EmbeddingModel", "baai/bge-m3")

        if not self.config.api_key:
            raise ValueError("OPENROUTER_API_KEY environment variable or config.api_key is required")

        # Create async HTTP client
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create async HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=60.0)
        return self._client

    async def close(self):
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    def _count_tokens(self, text: str) -> int:
        """Count tokens in text using tiktoken."""
        return len(_encoding.encode(text))

    async def _send_batch(
        self,
        batch_texts: List[str],
        batch_number: int,
    ) -> List[List[float]]:
        """
        Send a single batch to the embedding API.

        Args:
            batch_texts: List of texts to embed
            batch_number: Batch number for logging

        Returns:
            List of embedding vectors

        Raises:
            httpx.HTTPStatusError: If the request fails after retries
            json.JSONDecodeError: If response is not valid JSON
            ValueError: If response structure is invalid
        """
        retry_attempts = 3
        base_delay = 1.0

        client = await self._get_client()
        # OpenRouter uses /embeddings endpoint
        request_url = f"{self.config.api_url}/embeddings"
        request_headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.config.api_key}",
        }
        request_body = {
            "model": self.config.model,
            "input": batch_texts,
        }

        for attempt in range(1, retry_attempts + 1):
            try:
                response = await client.post(
                    request_url,
                    headers=request_headers,
                    json=request_body,
                )

                response_text = response.text

                if not response.is_success:
                    if response.status_code == 429:
                        # Rate limited - wait longer with each attempt
                        wait_time = 5.0 * attempt
                        logger.warning(
                            f"[Embedding] Batch {batch_number} rate limited (429). "
                            f"Retrying in {wait_time}s... (attempt {attempt}/{retry_attempts})"
                        )
                        await asyncio.sleep(wait_time)
                        continue

                    raise httpx.HTTPStatusError(
                        f"API Error {response.status_code}: {response_text[:500]}",
                        request=response.request,
                        response=response,
                    )

                # Parse JSON response
                try:
                    data = response.json()
                except json.JSONDecodeError as e:
                    logger.error(f"[Embedding] JSON Parse Error for Batch {batch_number}:")
                    logger.error(f"Response (first 500 chars): {response_text[:500]}")
                    raise ValueError(f"Failed to parse API response as JSON: {e}") from e

                # Enhanced response structure validation
                if not data:
                    raise ValueError("API returned empty/null response")

                # Check for error response
                if "error" in data:
                    error_data = data["error"]
                    error_msg = error_data.get("message", json.dumps(error_data))
                    error_code = error_data.get("code", response.status_code)
                    logger.error(f"[Embedding] API Error for Batch {batch_number}:")
                    logger.error(f"  Error Code: {error_code}")
                    logger.error(f"  Error Message: {error_msg}")
                    logger.error(
                        f"  Hint: Check if embedding model '{self.config.model}' is available"
                    )
                    raise ValueError(f"API Error {error_code}: {error_msg}")

                if "data" not in data:
                    logger.error(
                        f"[Embedding] Missing 'data' field in response for Batch {batch_number}"
                    )
                    logger.error(f"Response keys: {list(data.keys())}")
                    logger.error(f"Response preview: {json.dumps(data)[:500]}")
                    raise ValueError("Invalid API response structure: missing 'data' field")

                if not isinstance(data["data"], list):
                    logger.error(
                        f"[Embedding] 'data' field is not an array for Batch {batch_number}"
                    )
                    logger.error(f"data type: {type(data['data'])}")
                    logger.error(f"data value: {json.dumps(data['data'])[:200]}")
                    raise ValueError("Invalid API response structure: 'data' is not a list")

                if len(data["data"]) == 0:
                    logger.warning(
                        f"[Embedding] Warning: Batch {batch_number} returned empty embeddings array"
                    )

                # Sort by index to maintain order and extract embeddings
                sorted_data = sorted(data["data"], key=lambda x: x.get("index", 0))
                embeddings = [item["embedding"] for item in sorted_data]

                # logger.info(
                #     f"[Embedding] Batch {batch_number} completed ({len(batch_texts)} items)."
                # )

                return embeddings

            except httpx.HTTPStatusError:
                # Re-raise HTTP errors without additional retry logic
                raise
            except (httpx.RequestError, ValueError, json.JSONDecodeError) as e:
                logger.warning(
                    f"[Embedding] Batch {batch_number}, Attempt {attempt} failed: {e}"
                )
                if attempt == retry_attempts:
                    raise
                await asyncio.sleep(base_delay * (2 ** attempt))

        # Should never reach here, but type checkers need it
        raise RuntimeError("Unexpected state in _send_batch")

    def _prepare_batches(self, texts: List[str]) -> List[List[str]]:
        """
        Split texts into batches based on token and item limits.

        Args:
            texts: List of texts to batch

        Returns:
            List of text batches
        """
        batches = []
        current_batch: List[str] = []
        current_batch_tokens = 0

        for text in texts:
            text_tokens = self._count_tokens(text)

            # Skip oversize texts
            if text_tokens > self.config.max_tokens:
                logger.warning(
                    f"[Embedding] Skipping text with {text_tokens} tokens "
                    f"(exceeds limit of {self.config.max_tokens})"
                )
                continue

            # Check if batch is full
            is_token_full = current_batch and (
                current_batch_tokens + text_tokens > self.config.max_tokens
            )
            is_item_full = len(current_batch) >= self.config.max_batch_items

            if is_token_full or is_item_full:
                batches.append(current_batch)
                current_batch = [text]
                current_batch_tokens = text_tokens
            else:
                current_batch.append(text)
                current_batch_tokens += text_tokens

        # Add remaining batch
        if current_batch:
            batches.append(current_batch)

        return batches

    async def get_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Get embeddings for multiple texts with batching and concurrency.

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors (flattened from all batches)
        """
        if not texts:
            return []

        # Step 1: Prepare batches (pure CPU operation)
        batches = self._prepare_batches(texts)

        logger.info(
            f"[Embedding] Prepared {len(batches)} batches. "
            f"Executing with concurrency: {self.config.concurrency}..."
        )

        # Step 2: Concurrent execution
        results: List[Optional[List[List[float]]]] = [None] * len(batches)
        cursor = 0
        batch_lock = asyncio.Lock()

        async def worker(worker_id: int) -> None:
            """Worker that processes batches from the queue."""
            nonlocal cursor

            while True:
                async with batch_lock:
                    batch_index = cursor
                    cursor += 1

                if batch_index >= len(batches):
                    break  # No more tasks

                batch_texts = batches[batch_index]
                results[batch_index] = await self._send_batch(batch_texts, batch_index + 1)

        # Launch workers
        workers = [worker(i) for i in range(self.config.concurrency)]
        await asyncio.gather(*workers)

        # Step 3: Flatten and filter results
        # Filter out None values (failed batches) and flatten
        return [embedding for batch in results if batch for embedding in batch]


async def get_embeddings_batch(
    texts: List[str],
    config: Optional[Union[EmbeddingConfig, Dict]] = None,
) -> List[List[float]]:
    """
    Convenience function to get embeddings for multiple texts.

    Args:
        texts: List of texts to embed
        config: Optional configuration object or dict

    Returns:
        List of embedding vectors
    """
    async with EmbeddingService(config) as service:
        return await service.get_embeddings_batch(texts)
