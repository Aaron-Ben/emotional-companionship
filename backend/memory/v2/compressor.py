"""Session Compressor for emotional-companionship.

Handles extraction of long-term memories from session conversations.
Uses MemoryExtractor for 6-category extraction and MemoryDeduplicator for LLM-based dedup.
"""

import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

import aiofiles

from memory.v2.chromadb_manager import ChromaDBManager
from memory.v2.model import (
    DedupDecision,
    MemoryActionDecision,
    MemoryContext,
)
from .memory_deduplicator import MemoryDeduplicator
from .memory_extractor import (
    CandidateMemory,
    MemoryCategory,
    MemoryExtractor,
)

logger = logging.getLogger(__name__)

# Categories that always merge (skip dedup)
ALWAYS_MERGE_CATEGORIES = {MemoryCategory.PROFILE}

# Categories that support MERGE decision
MERGE_SUPPORTED_CATEGORIES = {
    MemoryCategory.PREFERENCES,
    MemoryCategory.ENTITIES,
    MemoryCategory.PATTERNS,
}

# Data base directory
DATA_BASE_DIR = Path(__file__).parent.parent.parent.parent / "data"


@dataclass
class ExtractionStats:
    """Statistics for memory extraction."""

    created: int = 0
    merged: int = 0
    deleted: int = 0
    skipped: int = 0


class Compressor:
    """Session memory compressor with 6-category memory extraction."""

    def __init__(
        self,
        chromadb: ChromaDBManager,
    ):
        """Initialize session compressor."""
        self.chromadb = chromadb
        self.extractor = MemoryExtractor()
        self.deduplicator = MemoryDeduplicator(chromadb_manager=chromadb)
        self._pending_changes: Dict[str, Dict[str, set]] = {}

    async def _get_embedding(self, text: str) -> List[float]:
        """Get embedding for text asynchronously."""
        from app.services.embedding import get_embeddings_batch

        results = await get_embeddings_batch([text])
        return results[0] if results else []

    async def _get_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Get embeddings for multiple texts asynchronously."""
        from app.services.embedding import get_embeddings_batch

        return await get_embeddings_batch(texts)

    def _record_change(
        self, file_uri: str, change_type: str, parent_uri: Optional[str] = None
    ) -> None:
        """Record a file change for batch processing."""
        if change_type not in ("added", "modified", "deleted"):
            logger.warning(f"Invalid change_type: {change_type}, skipping")
            return

        if not parent_uri:
            parent_uri = "/".join(file_uri.rsplit("/", 1)[:-1])

        if not parent_uri:
            logger.warning(f"Could not determine parent URI for {file_uri}, skipping")
            return

        if parent_uri not in self._pending_changes:
            self._pending_changes[parent_uri] = {
                "added": set(),
                "modified": set(),
                "deleted": set(),
            }

        self._pending_changes[parent_uri][change_type].add(file_uri)
        logger.debug(f"Recorded change: {change_type} {file_uri} in {parent_uri}")

    @staticmethod
    def _chunk_text(text: str, chunk_size: int, overlap: int) -> List[str]:
        """Split text into overlapping chunks, preferring paragraph boundaries."""
        if len(text) <= chunk_size:
            return [text]

        chunks = []
        start = 0
        while start < len(text):
            end = start + chunk_size

            if end < len(text):
                boundary = text.rfind("\n\n", start, end)
                if boundary > start + chunk_size // 2:
                    end = boundary + 2

            chunks.append(text[start:end].strip())
            start = end - overlap
            if start >= len(text):
                break

        return [c for c in chunks if c]

    async def _index_memory(
        self, memory: MemoryContext, change_type: str = "added"
    ) -> bool:
        """Index memory to ChromaDB with multi-level records (L0, L1, L2 + chunks).

        Creates separate ChromaDB records for each level using composite IDs:
        {base_id}__L0, {base_id}__L1, {base_id}__L2, {base_id}__L2__chunk_N
        """
        has_content = bool(memory.abstract or memory.overview or memory.content)
        if not has_content:
            logger.warning(f"Empty text for memory {memory.uri}, skipping indexing")
            return False

        base_id = memory.id

        try:
            # Common metadata shared across all levels
            common_meta = {
                "uri": memory.uri,
                "parent_uri": memory.parent_uri,
                "base_id": base_id,
                "category": memory.category,
                "session_id": memory.session_id,
                "user": memory.user,
                "context_type": "memory",
                "owner_space": memory.user,
            }

            # --- L0: Abstract ---
            if memory.abstract:
                abstract_embedding = await self._get_embedding(memory.abstract)
                await self.chromadb.add_memory(
                    memory_id=f"{base_id}__L0",
                    embedding=abstract_embedding,
                    text=memory.abstract,
                    metadata={
                        **common_meta,
                        "abstract": memory.abstract,
                        "level": 0,
                    },
                )

            # --- L1: Overview ---
            if memory.overview:
                overview_embedding = await self._get_embedding(memory.overview)
                await self.chromadb.add_memory(
                    memory_id=f"{base_id}__L1",
                    embedding=overview_embedding,
                    text=memory.overview,
                    metadata={
                        **common_meta,
                        "overview": memory.overview,
                        "level": 1,
                    },
                )

            # --- L2: Content (with chunking for large text) ---
            content_text = memory.content or ""
            if content_text:
                chunks = self._chunk_text(content_text, chunk_size=8000, overlap=800)

                if len(chunks) > 1:
                    chunk_embeddings = await self._get_embeddings_batch(chunks)
                    for i, (chunk_text, chunk_embedding) in enumerate(
                        zip(chunks, chunk_embeddings)
                    ):
                        await self.chromadb.add_memory(
                            memory_id=f"{base_id}__L2__chunk_{i:04d}",
                            embedding=chunk_embedding,
                            text=chunk_text,
                            metadata={
                                **common_meta,
                                "abstract": memory.abstract,
                                "overview": memory.overview,
                                "content": chunk_text,
                                "chunk_index": i,
                                "total_chunks": len(chunks),
                                "level": 2,
                            },
                        )
                else:
                    content_embedding = await self._get_embedding(content_text)
                    await self.chromadb.add_memory(
                        memory_id=f"{base_id}__L2",
                        embedding=content_embedding,
                        text=content_text,
                        metadata={
                            **common_meta,
                            "abstract": memory.abstract,
                            "overview": memory.overview,
                            "content": content_text,
                            "level": 2,
                        },
                    )

            self._record_change(memory.uri, change_type, parent_uri=memory.parent_uri)
            logger.info(f"Indexed memory to ChromaDB (multi-level): {memory.uri}")
            return True

        except Exception as e:
            logger.error(f"Failed to index memory {memory.uri}: {e}")
            return False

    async def _merge_into_existing(
        self,
        candidate: CandidateMemory,
        target_memory: MemoryContext,
    ) -> bool:
        """Merge candidate content into an existing memory file and re-index."""
        try:
            # Read existing content
            file_path = DATA_BASE_DIR / target_memory.uri
            if not file_path.exists():
                logger.error(f"Target memory file not found: {file_path}")
                return False

            async with aiofiles.open(file_path, "r", encoding="utf-8") as f:
                existing_content = await f.read()

            # Use LLM to merge
            payload = await self.extractor.merge_memory_bundle(
                existing_abstract=target_memory.abstract,
                existing_overview=target_memory.overview or "",
                existing_content=existing_content,
                new_abstract=candidate.abstract,
                new_overview=candidate.overview,
                new_content=candidate.content,
                category=candidate.category.value,
            )

            if not payload:
                return False

            # Write merged content
            async with aiofiles.open(file_path, "w", encoding="utf-8") as f:
                await f.write(payload.content)

            # Update memory context
            target_memory.abstract = payload.abstract
            target_memory.overview = payload.overview
            target_memory.content = payload.content

            # Re-index: delete old multi-level records, then re-create
            await self.chromadb.delete_memory_tree(target_memory.id)
            await self._index_memory(target_memory, change_type="modified")

            logger.info(f"Merged and re-indexed memory {target_memory.uri}")
            return True

        except Exception as e:
            logger.error(f"Failed to merge memory {target_memory.uri}: {e}")
            return False

    async def _delete_existing_memory(
        self, memory: MemoryContext
    ) -> bool:
        """Hard delete an existing memory file and clean up its vector record."""
        try:
            # Delete file
            file_path = DATA_BASE_DIR / memory.uri
            if file_path.exists():
                os.remove(file_path)
                logger.info(f"Deleted memory file: {memory.uri}")
            else:
                logger.warning(f"Memory file not found for deletion: {memory.uri}")
        except Exception as e:
            logger.error(f"Failed to delete memory file {memory.uri}: {e}")
            return False

        try:
            # Delete all multi-level records from ChromaDB
            await self.chromadb.delete_memory_tree(memory.id)
        except Exception as e:
            logger.warning(f"Failed to remove vector record for {memory.uri}: {e}")

        self._record_change(memory.uri, "deleted", parent_uri=memory.parent_uri)
        return True

    async def extract_long_term_memories(
        self,
        messages: List[Dict],
        user: str,
        session_id: str,
    ) -> List[MemoryContext]:
        """Extract long-term memories from messages.

        Args:
            messages: List of message dicts from session
            user: User identifier
            session_id: Current session ID

        Returns:
            List of MemoryContext objects for created/merged memories
        """
        if not messages:
            return []

        self._pending_changes.clear()
        context = {"messages": messages}

        try:
            # Extract candidate memories
            candidates = await self.extractor.extract(context, user, session_id)

            if not candidates:
                return []

            memories: List[MemoryContext] = []
            stats = ExtractionStats()
            batch_memories: List[tuple[List[float], MemoryContext]] = []

            for candidate in candidates:
                # Profile: always merge, skip dedup
                if candidate.category in ALWAYS_MERGE_CATEGORIES:
                    memory = await self.extractor.create_memory(
                        candidate, user, session_id
                    )
                    if memory:
                        memories.append(memory)
                        stats.created += 1
                        await self._index_memory(memory)
                    else:
                        stats.skipped += 1
                    continue

                # Dedup check
                result = await self.deduplicator.deduplicate(
                    candidate, batch_memories=batch_memories
                )
                actions = result.actions or []
                decision = result.decision

                if decision == DedupDecision.CREATE and any(
                    a.decision == MemoryActionDecision.MERGE for a in actions
                ):
                    logger.warning(f"Normalizing create+merge to none: {candidate.abstract}")
                    decision = DedupDecision.NONE

                if decision == DedupDecision.SKIP:
                    stats.skipped += 1
                    continue

                if decision == DedupDecision.NONE:
                    if not actions:
                        stats.skipped += 1
                        continue

                    for action in actions:
                        if action.decision == MemoryActionDecision.DELETE:
                            if await self._delete_existing_memory(action.memory):
                                stats.deleted += 1
                                batch_memories = [
                                    (v, m) for v, m in batch_memories
                                    if m.uri != action.memory.uri
                                ]
                            else:
                                stats.skipped += 1

                        elif action.decision == MemoryActionDecision.MERGE:
                            if candidate.category in MERGE_SUPPORTED_CATEGORIES:
                                if await self._merge_into_existing(
                                    candidate, action.memory
                                ):
                                    stats.merged += 1
                                    batch_memories = [
                                        (v, m)
                                        for v, m in batch_memories
                                        if m.uri != action.memory.uri
                                    ]
                                    # Update the memory in results
                                    merged_text = f"{action.memory.abstract} {candidate.content}"
                                    merged_embed = await self._get_embedding(merged_text)
                                    batch_memories.append(
                                        (merged_embed, action.memory)
                                    )
                                else:
                                    stats.skipped += 1
                            else:
                                stats.skipped += 1
                    continue

                if decision == DedupDecision.CREATE:
                    for action in actions:
                        if action.decision == MemoryActionDecision.DELETE:
                            if await self._delete_existing_memory(action.memory):
                                stats.deleted += 1
                                batch_memories = [
                                    (v, m) for v, m in batch_memories
                                    if m.uri != action.memory.uri
                                ]
                            else:
                                stats.skipped += 1

                    memory = await self.extractor.create_memory(
                        candidate, user, session_id
                    )
                    if memory:
                        memories.append(memory)
                        stats.created += 1
                        await self._index_memory(memory)
                        if result.query_vector:
                            batch_memories.append((result.query_vector, memory))
                    else:
                        stats.skipped += 1

            logger.info(
                f"Memory extraction: created={stats.created}, "
                f"merged={stats.merged}, deleted={stats.deleted}, skipped={stats.skipped}"
            )
            return memories

        except Exception:
            self._pending_changes.clear()
            raise