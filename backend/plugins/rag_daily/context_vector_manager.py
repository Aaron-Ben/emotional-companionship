"""
Context Vector Manager for RAG Daily Plugin.

Manages conversation message vectors with decay aggregation and semantic segmentation.
Maintains a sliding window of context vectors with fuzzy matching capabilities.
"""

import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import json
import logging

from .math_utils import (
    normalize_vector,
    cosine_similarity,
    dice_similarity,
    weighted_average,
)

logger = logging.getLogger(__name__)


class ContextSegment:
    """A semantic segment of context with associated vectors."""

    def __init__(
        self,
        segment_id: str,
        messages: List[Dict],
        vector: np.ndarray,
        timestamp: float,
    ):
        self.segment_id = segment_id
        self.messages = messages
        self.vector = vector
        self.timestamp = timestamp

    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return {
            "segment_id": self.segment_id,
            "messages": self.messages,
            "vector": self.vector.tolist() if isinstance(self.vector, np.ndarray) else self.vector,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "ContextSegment":
        """Create from dictionary."""
        return cls(
            segment_id=data["segment_id"],
            messages=data["messages"],
            vector=np.array(data["vector"]),
            timestamp=data["timestamp"],
        )


class ContextVectorManager:
    """
    Manages context vectors for conversation messages.

    Features:
    - Decay-based vector aggregation
    - Semantic segmentation of message context
    - Fuzzy matching for context retrieval
    - Logic depth computation
    """

    def __init__(
        self,
        decay_rate: float = 0.75,
        max_context_window: int = 10,
        fuzzy_threshold: float = 0.85,
        dimension: int = 1024,
    ):
        """
        Initialize the context vector manager.

        Args:
            decay_rate: Decay rate for temporal aggregation (default: 0.75)
            max_context_window: Maximum number of context segments to keep
            fuzzy_threshold: Threshold for fuzzy matching (default: 0.85)
            dimension: Vector dimension (default: 1024 for bge-m3)
        """
        self.decay_rate = decay_rate
        self.max_context_window = max_context_window
        self.fuzzy_threshold = fuzzy_threshold
        self.dimension = dimension

        # Context storage
        self.segments: List[ContextSegment] = []
        self.message_vectors: Dict[str, np.ndarray] = {}  # message_id -> vector
        self.role_vectors: Dict[str, List[np.ndarray]] = {"user": [], "assistant": [], "system": []}

        # Timing
        self.last_update_time: Optional[float] = None

    def update_context(
        self,
        messages: List[Dict],
        message_vectors: Optional[Dict[str, np.ndarray]] = None,
        allow_api: bool = False,
    ) -> None:
        """
        Update context vectors with new messages.

        Args:
            messages: List of message dictionaries with 'role', 'content', 'id' keys
            message_vectors: Optional pre-computed vectors for messages
            allow_api: Whether to allow API calls for missing vectors (not used in this implementation)
        """
        current_time = datetime.now().timestamp()
        self.last_update_time = current_time

        # Process new messages
        for msg in messages:
            msg_id = msg.get("id", f"msg_{current_time}_{len(self.message_vectors)}")

            if msg_id in self.message_vectors:
                continue  # Already processed

            # Store vector if provided
            if message_vectors and msg_id in message_vectors:
                vector = message_vectors[msg_id]
            else:
                # No vector provided, skip (embedding service should be called externally)
                continue

            self.message_vectors[msg_id] = vector

            # Store by role
            role = msg.get("role", "user")
            if role in self.role_vectors:
                self.role_vectors[role].append(vector)

        # Segment context if needed
        if len(messages) > 0:
            self.segment_context(messages)

        # Trim context window
        self._trim_context_window()

        logger.debug(f"[ContextVectorManager] Updated context with {len(messages)} messages")

    def aggregate_context(self, role: str = "assistant") -> Optional[np.ndarray]:
        """
        Aggregate vectors for a specific role with decay.

        Args:
            role: Role to aggregate ('assistant', 'user', 'system')

        Returns:
            Aggregated vector with decay weights, or None if no vectors
        """
        vectors = self.role_vectors.get(role, [])

        if not vectors:
            return None

        if len(vectors) == 1:
            return vectors[0]

        # Apply decay weights (most recent = highest weight)
        weights = [self.decay_rate ** (len(vectors) - 1 - i) for i in range(len(vectors))]

        return weighted_average(vectors, weights)

    def segment_context(
        self,
        messages: List[Dict],
        threshold: float = 0.70,
    ) -> List[ContextSegment]:
        """
        Segment messages into semantic groups based on vector similarity.

        Args:
            messages: List of messages to segment
            threshold: Similarity threshold for segmentation (default: 0.70)

        Returns:
            List of context segments
        """
        if not messages:
            return []

        new_segments = []
        current_segment_messages = []
        current_segment_vectors = []

        for i, msg in enumerate(messages):
            msg_id = msg.get("id", f"msg_{i}")
            vector = self.message_vectors.get(msg_id)

            if vector is None:
                continue

            current_segment_messages.append(msg)
            current_segment_vectors.append(vector)

            # Check if we should segment (at least 2 messages in current segment)
            if len(current_segment_vectors) >= 2:
                # Calculate similarity with segment average
                segment_avg = np.mean(current_segment_vectors[:-1], axis=0)
                similarity = cosine_similarity(vector, segment_avg)

                if similarity < threshold:
                    # Create new segment
                    segment_id = f"seg_{len(self.segments) + len(new_segments)}_{datetime.now().timestamp()}"
                    segment_vector = np.mean(current_segment_vectors[:-1], axis=0)

                    segment = ContextSegment(
                        segment_id=segment_id,
                        messages=current_segment_messages[:-1].copy(),
                        vector=segment_vector,
                        timestamp=datetime.now().timestamp(),
                    )

                    new_segments.append(segment)

                    # Start new segment with current message
                    current_segment_messages = [msg]
                    current_segment_vectors = [vector]

        # Add the last segment
        if current_segment_messages:
            segment_id = f"seg_{len(self.segments) + len(new_segments)}_{datetime.now().timestamp()}"
            segment_vector = np.mean(current_segment_vectors, axis=0)

            segment = ContextSegment(
                segment_id=segment_id,
                messages=current_segment_messages,
                vector=segment_vector,
                timestamp=datetime.now().timestamp(),
            )

            new_segments.append(segment)

        # Merge new segments with existing
        self.segments.extend(new_segments)

        # Trim to max window
        if len(self.segments) > self.max_context_window:
            self.segments = self.segments[-self.max_context_window:]

        logger.debug(f"[ContextVectorManager] Created {len(new_segments)} new segments")

        return new_segments

    def compute_logic_depth(
        self,
        vector: np.ndarray,
        top_k: int = 64,
    ) -> float:
        """
        Compute the logic depth index of a vector.

        Logic depth measures how "specialized" a vector is by comparing
        it to the context segments. Higher values indicate more specialized
        (less common) semantic content.

        Args:
            vector: Input vector
            top_k: Number of top segments to consider

        Returns:
            Logic depth value (higher = more specialized)
        """
        if not self.segments:
            return 0.0

        # Calculate similarities with all segments
        similarities = []
        for segment in self.segments:
            sim = cosine_similarity(vector, segment.vector)
            similarities.append(sim)

        # Sort and take top k
        similarities.sort(reverse=True)
        top_similarities = similarities[:top_k]

        # Logic depth is inversely related to average similarity
        avg_similarity = np.mean(top_similarities) if top_similarities else 0

        # Return 1 - avg_similarity (higher = more specialized/unique)
        return float(1.0 - avg_similarity)

    def fuzzy_match_context(
        self,
        query: str,
        query_vector: np.ndarray,
        threshold: Optional[float] = None,
    ) -> List[Tuple[ContextSegment, float]]:
        """
        Find context segments that fuzzy match the query.

        Args:
            query: Query text (for string matching)
            query_vector: Query vector
            threshold: Override default fuzzy threshold

        Returns:
            List of (segment, similarity_score) tuples
        """
        threshold = threshold or self.fuzzy_threshold

        results = []

        for segment in self.segments:
            # Vector similarity
            vector_sim = cosine_similarity(query_vector, segment.vector)

            # String similarity with messages
            string_sims = []
            for msg in segment.messages:
                content = msg.get("content", "")
                string_sim = dice_similarity(query.lower(), content.lower())
                string_sims.append(string_sim)

            string_sim = max(string_sims) if string_sims else 0

            # Combined score
            combined_score = 0.7 * vector_sim + 0.3 * string_sim

            if combined_score >= threshold:
                results.append((segment, combined_score))

        # Sort by similarity
        results.sort(key=lambda x: x[1], reverse=True)

        return results

    def get_context_summary(self) -> Dict:
        """
        Get a summary of the current context state.

        Returns:
            Dictionary with context statistics
        """
        return {
            "total_messages": len(self.message_vectors),
            "total_segments": len(self.segments),
            "role_counts": {
                role: len(vectors) for role, vectors in self.role_vectors.items()
            },
            "last_update": self.last_update_time,
        }

    def clear_context(self) -> None:
        """Clear all context data."""
        self.segments.clear()
        self.message_vectors.clear()
        for role in self.role_vectors:
            self.role_vectors[role].clear()
        self.last_update_time = None
        logger.debug("[ContextVectorManager] Context cleared")

    def _trim_context_window(self) -> None:
        """Trim the context window to max_context_window."""
        if len(self.segments) > self.max_context_window:
            removed = len(self.segments) - self.max_context_window
            self.segments = self.segments[-self.max_context_window:]
            logger.debug(f"[ContextVectorManager] Trimmed {removed} old segments")

        # Also trim role vectors (keep most recent)
        for role in self.role_vectors:
            if len(self.role_vectors[role]) > self.max_context_window * 2:
                removed = len(self.role_vectors[role]) - self.max_context_window * 2
                self.role_vectors[role] = self.role_vectors[role][-self.max_context_window * 2:]
                logger.debug(f"[ContextVectorManager] Trimmed {removed} old {role} vectors")

    def export_state(self) -> Dict:
        """
        Export the current state for serialization.

        Returns:
            Dictionary containing all state data
        """
        return {
            "segments": [seg.to_dict() for seg in self.segments],
            "role_vector_keys": list(self.role_vectors.keys()),
            "last_update_time": self.last_update_time,
            "config": {
                "decay_rate": self.decay_rate,
                "max_context_window": self.max_context_window,
                "fuzzy_threshold": self.fuzzy_threshold,
                "dimension": self.dimension,
            },
        }

    def import_state(self, state: Dict) -> None:
        """
        Import state from serialized data.

        Args:
            state: Dictionary containing exported state
        """
        self.segments = [ContextSegment.from_dict(seg) for seg in state.get("segments", [])]
        self.last_update_time = state.get("last_update_time")

        # Restore config
        config = state.get("config", {})
        self.decay_rate = config.get("decay_rate", 0.75)
        self.max_context_window = config.get("max_context_window", 10)
        self.fuzzy_threshold = config.get("fuzzy_threshold", 0.85)
        self.dimension = config.get("dimension", 1024)

        logger.debug("[ContextVectorManager] State imported")
