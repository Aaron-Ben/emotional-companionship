"""Intelligent text chunker with token-based splitting and overlap support."""

import os
import re
from typing import List
from tiktoken import get_encoding

# Initialize tiktoken encoding (cl100k_base for GPT-4, GPT-3.5, embedding models)
_encoding = get_encoding("cl100k_base")

# Configuration from environment
EMBEDDING_MAX_TOKEN = int(os.getenv("WHITELIST_EMBEDDING_MODEL_MAX_TOKEN", "8000"))
SAFE_MAX_TOKENS = int(EMBEDDING_MAX_TOKEN * 0.85)
DEFAULT_OVERLAP_TOKENS = int(SAFE_MAX_TOKENS * 0.1)  # 10% overlap

print(f"[TextChunker] Config loaded: MaxToken={EMBEDDING_MAX_TOKEN}, "
      f"SafeMaxTokens={SAFE_MAX_TOKENS}, OverlapTokens={DEFAULT_OVERLAP_TOKENS}")


def _count_tokens(text: str) -> int:
    """Count tokens in text using tiktoken."""
    return len(_encoding.encode(text))


def _split_sentences(text: str) -> List[str]:
    """
    Split text into sentences while preserving delimiters.

    Splits on: 。？！.!?\n
    """
    # Split on sentence boundaries, keeping the delimiters
    sentences = re.split(r'(?<=[。？！.!?\n])', text)
    return [s for s in sentences if s]


def _force_split_long_text(
    text: str,
    max_tokens: int,
    overlap_tokens: int
) -> List[str]:
    """
    Force split text that exceeds max_tokens.

    Args:
        text: Text to split
        max_tokens: Maximum tokens per chunk
        overlap_tokens: Overlap tokens between chunks

    Returns:
        List of text chunks
    """
    chunks = []
    tokens = _encoding.encode(text)

    start = 0
    while start < len(tokens):
        end = min(start + max_tokens, len(tokens))

        # Try to break at a natural position (avoid breaking in middle of word)
        if end < len(tokens):
            chunk_tokens = tokens[start:end]
            chunk_text = _encoding.decode(chunk_tokens)

            # Try to break at punctuation or whitespace
            break_points = ['\n', '。', '！', '？', '，', '；', '：', ' ', '\t']
            best_break_point = -1

            # Look for break point in last 200 characters
            search_start = max(0, len(chunk_text) - 200)
            for i in range(len(chunk_text) - 1, search_start - 1, -1):
                if chunk_text[i] in break_points:
                    best_break_point = i + 1
                    break

            if best_break_point > 0:
                chunk_text = chunk_text[:best_break_point]
                new_tokens = _encoding.encode(chunk_text)
                end = start + len(new_tokens)

            chunks.append(chunk_text.strip())
        else:
            # Last chunk
            chunk_tokens = tokens[start:]
            chunks.append(_encoding.decode(chunk_tokens).strip())

        # Calculate next start position (considering overlap)
        start = max(start + 1, end - overlap_tokens)

    return [chunk for chunk in chunks if chunk]


def chunk_text(
    text: str,
    max_tokens: int = SAFE_MAX_TOKENS,
    overlap_tokens: int = DEFAULT_OVERLAP_TOKENS
) -> List[str]:
    """
    Intelligently chunk text based on token count with overlap.

    Args:
        text: Original text to chunk
        max_tokens: Maximum tokens per chunk (default: SAFE_MAX_TOKENS)
        overlap_tokens: Overlap tokens between chunks for context continuity
                        (default: DEFAULT_OVERLAP_TOKENS)

    Returns:
        List of text chunks

    Example:
        >>> text = "这是第一句。这是第二句。这是第三句。"
        >>> chunks = chunk_text(text, max_tokens=100, overlap_tokens=20)
    """
    if not text:
        return []

    sentences = _split_sentences(text)
    chunks = []
    current_chunk = ""
    current_tokens = 0

    for i, sentence in enumerate(sentences):
        sentence_tokens = _count_tokens(sentence)

        # Handle oversized sentences: force split if single sentence exceeds max_tokens
        if sentence_tokens > max_tokens:
            # Save current chunk first (if has content)
            if current_chunk.strip():
                chunks.append(current_chunk.strip())
                current_chunk = ""
                current_tokens = 0

            # Force split the oversized sentence
            force_split_chunks = _force_split_long_text(sentence, max_tokens, overlap_tokens)
            chunks.extend(force_split_chunks)
            continue

        # Check if adding this sentence would exceed max_tokens
        if current_tokens + sentence_tokens > max_tokens:
            chunks.append(current_chunk.strip())

            # Create overlap chunk
            overlap_chunk = ""
            overlap_token_count = 0
            for j in range(i - 1, -1, -1):
                prev_sentence = sentences[j]
                prev_sentence_tokens = _count_tokens(prev_sentence)
                if overlap_token_count + prev_sentence_tokens > overlap_tokens:
                    break
                overlap_chunk = prev_sentence + overlap_chunk
                overlap_token_count += prev_sentence_tokens

            current_chunk = overlap_chunk
            current_tokens = overlap_token_count

        current_chunk += sentence
        current_tokens += sentence_tokens

    # Add remaining content
    if current_chunk.strip():
        chunks.append(current_chunk.strip())

    return chunks


# Convenience function for direct usage
async def chunk_text_async(
    text: str,
    max_tokens: int = SAFE_MAX_TOKENS,
    overlap_tokens: int = DEFAULT_OVERLAP_TOKENS
) -> List[str]:
    """
    Async wrapper for chunk_text (for consistency with async services).

    This is a simple wrapper since the operation is CPU-bound and synchronous.
    For true async processing of multiple texts, consider using asyncio.to_thread.
    """
    return chunk_text(text, max_tokens, overlap_tokens)
