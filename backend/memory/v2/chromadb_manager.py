"""ChromaDB manager for vector storage and search."""
import logging
from typing import Any, Dict, List, Optional

import chromadb
from chromadb.config import Settings
from chromadb.api.models.Collection import Collection
from pathlib import Path

logger = logging.getLogger(__name__)

# Default ChromaDB persistence directory - project root
DEFAULT_PERSIST_DIR = Path(__file__).parent.parent.parent.parent / "chroma-db"


class ChromaDBManager:
    """ChromaDB manager for memory vector storage."""

    def __init__(
        self,
        persist_dir: Optional[str] = None,
        collection_name: str = "memories",
    ):
        """Initialize ChromaDB manager.

        Args:
            persist_directory: Directory for ChromaDB persistence
            collection_name: Name of the collection to use
        """
        # Use default if not provided
        if persist_dir is None:
            persist_dir = str(DEFAULT_PERSIST_DIR)

        self.client = chromadb.PersistentClient(
            path=persist_dir,
            settings=Settings()
        )

        self.collection: Collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"}
        )


    async def search_similar_memories(
        self,
        owner_space: Optional[str],
        category_uri_prefix: str,
        query_vector: List[float],
        limit: int = 5,
        level_filter: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Search for similar memories.

        Args:
            owner_space: Owner space filter (e.g., user or agent name)
            category_uri_prefix: Category URI prefix filter
            query_vector: Query embedding vector
            limit: Maximum number of results
            level_filter: If set, only search this level (0/1/2); None = all levels

        Returns:
            List of memory dicts with uri, abstract, content, etc.
        """
        where_conditions: list = [
            {"context_type": {"$eq": "memory"}},
        ]

        if level_filter is not None:
            where_conditions.append({"level": {"$eq": level_filter}})

        if owner_space:
            where_conditions.append({"owner_space": {"$eq": owner_space}})

        where_clause = {"$and": where_conditions} if len(where_conditions) > 1 else where_conditions[0]

        # When searching all levels, request more results since each logical memory
        # may have up to 3 records (L0, L1, L2)
        n_results = limit * 3 if level_filter is None else limit

        # 执行向量搜索
        results = self.collection.query(
            query_embeddings=[query_vector],
            n_results=n_results,
            where=where_clause,
            include=["metadatas", "distances", "documents"],
        )

        similar_memories = []
        if results["ids"] and results["ids"][0]:
            for i, memory_id in enumerate(results["ids"][0]):
                metadata = results["metadatas"][0][i] if results["metadatas"] else {}
                distance = results["distances"][0][i] if results["distances"] else 0

                # 后处理过滤 uri 前缀
                if category_uri_prefix and not metadata.get("uri", "").startswith(category_uri_prefix):
                    continue

                # ChromaDB cosine distance = 1 - cosine_similarity
                # distance=0 → identical (score=1), distance=1 → orthogonal (score=0)
                score = 1 - distance

                memory_record = {
                    "id": memory_id,
                    "_score": score,
                    **metadata,
                }
                similar_memories.append(memory_record)

        return similar_memories

    async def add_memory(
        self,
        memory_id: str,
        embedding: List[float],
        text: str,
        metadata: Dict[str, Any],
    ) -> bool:
        """Add a memory to ChromaDB.

        Args:
            memory_id: Unique ID for the memory
            embedding: Vector embedding
            text: Text content to store
            metadata: Metadata dict (uri, category, etc.)

        Returns:
            True if successful
        """
        try:
            self.collection.add(
                ids=[memory_id],
                embeddings=[embedding],
                documents=[text],
                metadatas=[metadata],
            )
            logger.info(f"Added memory to ChromaDB: {memory_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to add memory to ChromaDB: {e}")
            return False

    async def delete_memory(self, memory_id: str) -> bool:
        """Delete a single memory record from ChromaDB.

        Args:
            memory_id: ID of the memory record to delete

        Returns:
            True if successful
        """
        try:
            self.collection.delete(ids=[memory_id])
            logger.info(f"Deleted memory from ChromaDB: {memory_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete memory from ChromaDB: {e}")
            return False

    async def delete_memory_tree(self, base_id: str) -> bool:
        """Delete all level records (L0, L1, L2, chunks) for a base memory ID.

        Uses composite ID scheme: {base_id}__L0, {base_id}__L1,
        {base_id}__L2, {base_id}__L2__chunk_0, etc.

        Args:
            base_id: Base memory ID (without level suffix)

        Returns:
            True if successful
        """
        try:
            # Query by base_id metadata to find all related records
            results = self.collection.get(
                where={"base_id": {"$eq": base_id}},
                include=[],
            )

            ids_to_delete = list(results["ids"]) if results["ids"] else []

            # Also try the standard suffixed IDs as fallback
            for suffix in ["__L0", "__L1", "__L2"]:
                fallback_id = f"{base_id}{suffix}"
                if fallback_id not in ids_to_delete:
                    ids_to_delete.append(fallback_id)

            if ids_to_delete:
                self.collection.delete(ids=ids_to_delete)
                logger.info(
                    f"Deleted memory tree: {base_id} ({len(ids_to_delete)} records)"
                )
            return True
        except Exception as e:
            logger.error(f"Failed to delete memory tree {base_id}: {e}")
            return False
