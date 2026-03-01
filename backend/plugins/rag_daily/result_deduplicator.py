"""
Result Deduplicator Module for RAG Daily Plugin.

Implements intelligent result deduplication using SVD-based topic analysis
and residual pyramid projection for redundancy detection.
"""

import numpy as np
from typing import Dict, List, Optional, Tuple, Set
from scipy.linalg import svd
from scipy.spatial.distance import cosine
import logging

from .math_utils import (
    normalize_vector,
    cosine_similarity,
)

logger = logging.getLogger(__name__)


class ResultDeduplicator:
    """
    Intelligent result deduplicator for RAG retrieval results.

    Features:
    - SVD-based topic analysis
    - Redundancy threshold filtering
    - Diversity-maximizing selection
    - Semantic clustering for result grouping
    """

    def __init__(
        self,
        max_results: int = 20,
        topic_count: int = 8,
        redundancy_threshold: float = 0.85,
        diversity_weight: float = 0.3,
    ):
        """
        Initialize the result deduplicator.

        Args:
            max_results: Maximum number of results to return (default: 20)
            topic_count: Number of SVD topics for analysis (default: 8)
            redundancy_threshold: Similarity threshold for redundancy (default: 0.85)
            diversity_weight: Weight for diversity in scoring (default: 0.3)
        """
        self.max_results = max_results
        self.topic_count = topic_count
        self.redundancy_threshold = redundancy_threshold
        self.diversity_weight = diversity_weight

    async def deduplicate(
        self,
        candidates: List[Dict],
        query_vector: np.ndarray,
        pyramid_features: Optional[Dict] = None,
    ) -> List[Dict]:
        """
        Deduplicate and rank candidate results.

        Args:
            candidates: List of candidate results with 'vector' and 'score' fields
            query_vector: Original query vector
            pyramid_features: Optional pyramid features for enhanced deduplication

        Returns:
            Deduplicated and ranked list of results
        """
        if not candidates:
            return []

        logger.info(f"[ResultDeduplicator] Processing {len(candidates)} candidates")

        # Extract vectors and metadata
        vectors, metadata = self._extract_vectors(candidates)

        if not vectors:
            return candidates[:self.max_results]

        # Normalize vectors
        normalized_vectors = np.array([normalize_vector(v) for v in vectors])

        # Compute query similarities
        query_similarities = np.array([
            cosine_similarity(query_vector, vec) for vec in normalized_vectors
        ])

        # Apply SVD for topic analysis
        topic_similarities = self._compute_topic_similarities(
            normalized_vectors,
            query_vector,
        )

        # Apply pyramid-based diversity scoring if available
        diversity_scores = self._compute_diversity_scores(
            normalized_vectors,
            pyramid_features,
        )

        # Combine scores
        combined_scores = self._combine_scores(
            query_similarities,
            topic_similarities,
            diversity_scores,
        )

        # Find and remove redundant items
        selected_indices = self._remove_redundant(
            normalized_vectors,
            combined_scores,
        )

        # Build results
        results = []
        for idx in selected_indices[:self.max_results]:
            result = metadata[idx].copy()
            result["dedup_score"] = float(combined_scores[idx])
            result["query_similarity"] = float(query_similarities[idx])
            result["diversity_score"] = float(diversity_scores[idx]) if idx < len(diversity_scores) else 0.0
            results.append(result)

        logger.info(f"[ResultDeduplicator] Returned {len(results)} deduplicated results")

        return results

    def _extract_vectors(
        self,
        candidates: List[Dict],
    ) -> Tuple[List[np.ndarray], List[Dict]]:
        """
        Extract vectors and metadata from candidates.

        Args:
            candidates: List of candidate dictionaries

        Returns:
            Tuple of (vectors list, metadata list)
        """
        vectors = []
        metadata = []

        for candidate in candidates:
            vec = candidate.get("vector")
            if vec is None:
                continue

            if isinstance(vec, list):
                vec = np.array(vec)

            vectors.append(vec)
            metadata.append(candidate)

        return vectors, metadata

    def _compute_topic_similarities(
        self,
        vectors: np.ndarray,
        query_vector: np.ndarray,
    ) -> np.ndarray:
        """
        Compute topic-based similarities using SVD.

        Args:
            vectors: Matrix of candidate vectors
            query_vector: Query vector

        Returns:
            Array of topic similarity scores
        """
        n_samples, n_features = vectors.shape

        # Adjust topic count based on data size
        k = min(self.topic_count, n_samples, n_features)

        if k < 2:
            # Not enough data for SVD, return cosine similarities
            return np.array([
                cosine_similarity(query_vector, vec)
                for vec in vectors
            ])

        try:
            # Perform SVD
            U, S, Vt = svd(vectors, full_matrices=False)

            # Use top k components
            U_k = U[:, :k]
            S_k = S[:k]
            Vt_k = Vt[:k, :]

            # Transform query to topic space
            query_topic = np.dot(query_vector, Vt_k.T)

            # Transform vectors to topic space
            vectors_topic = np.dot(vectors, Vt_k.T)

            # Compute similarities in topic space
            similarities = np.array([
                cosine_similarity(query_topic, vec_topic)
                for vec_topic in vectors_topic
            ])

            return similarities

        except Exception as e:
            logger.warning(f"[ResultDeduplicator] SVD computation failed: {e}, falling back to cosine similarity")
            return np.array([
                cosine_similarity(query_vector, vec)
                for vec in vectors
            ])

    def _compute_diversity_scores(
        self,
        vectors: np.ndarray,
        pyramid_features: Optional[Dict],
    ) -> np.ndarray:
        """
        Compute diversity scores for each vector.

        Args:
            vectors: Matrix of candidate vectors
            pyramid_features: Optional pyramid features

        Returns:
            Array of diversity scores
        """
        n = len(vectors)
        diversity_scores = np.zeros(n)

        # Use pyramid features if available
        if pyramid_features and "handshake_features" in pyramid_features:
            handshake_features = pyramid_features["handshake_features"]

            if handshake_features:
                # Compute diversity based on handshake domain distribution
                domains = [f.get("domain", 0) for f in handshake_features]
                unique_domains = len(set(domains))
                diversity_scores = np.full(n, unique_domains / len(handshake_features))

        # Compute pairwise diversity
        for i in range(n):
            # Average distance to other vectors
            distances = []
            for j in range(n):
                if i != j:
                    # Use 1 - cosine similarity as distance
                    sim = cosine_similarity(vectors[i], vectors[j])
                    distances.append(1.0 - sim)

            if distances:
                diversity_scores[i] = max(diversity_scores[i], np.mean(distances))

        return diversity_scores

    def _combine_scores(
        self,
        query_similarities: np.ndarray,
        topic_similarities: np.ndarray,
        diversity_scores: np.ndarray,
    ) -> np.ndarray:
        """
        Combine different scoring components.

        Args:
            query_similarities: Direct query similarity scores
            topic_similarities: Topic-based similarity scores
            diversity_scores: Diversity scores

        Returns:
            Combined scores
        """
        # Normalize all scores to [0, 1]
        def normalize_scores(scores: np.ndarray) -> np.ndarray:
            min_val = np.min(scores)
            max_val = np.max(scores)
            if max_val - min_val == 0:
                return np.ones_like(scores) * 0.5
            return (scores - min_val) / (max_val - min_val)

        norm_query = normalize_scores(query_similarities)
        norm_topic = normalize_scores(topic_similarities)
        norm_diversity = normalize_scores(diversity_scores)

        # Combine: relevance + diversity
        relevance = 0.7 * norm_query + 0.3 * norm_topic
        combined = (1 - self.diversity_weight) * relevance + self.diversity_weight * norm_diversity

        return combined

    def _remove_redundant(
        self,
        vectors: np.ndarray,
        scores: np.ndarray,
    ) -> List[int]:
        """
        Remove redundant items based on similarity threshold.

        Args:
            vectors: Matrix of vectors
            scores: Associated scores

        Returns:
            List of non-redundant indices (sorted by score)
        """
        n = len(vectors)
        selected: Set[int] = set()

        # Sort by score (descending)
        sorted_indices = np.argsort(scores)[::-1]

        for idx in sorted_indices:
            # Check if this vector is redundant with any selected
            is_redundant = False

            for selected_idx in selected:
                similarity = cosine_similarity(vectors[idx], vectors[selected_idx])

                if similarity >= self.redundancy_threshold:
                    is_redundant = True
                    break

            if not is_redundant:
                selected.add(idx)

        # Return sorted by score
        return sorted(selected, key=lambda i: scores[i], reverse=True)

    def cluster_results(
        self,
        results: List[Dict],
        n_clusters: int = 5,
    ) -> List[List[Dict]]:
        """
        Cluster results into semantic groups.

        Args:
            results: List of results with vectors
            n_clusters: Number of clusters to create

        Returns:
            List of result clusters
        """
        if not results or len(results) <= n_clusters:
            return [[r] for r in results]

        # Extract vectors
        vectors = []
        for result in results:
            vec = result.get("vector")
            if vec is not None:
                if isinstance(vec, list):
                    vec = np.array(vec)
                vectors.append(vec)

        if len(vectors) < n_clusters:
            return [[r] for r in results]

        vectors_array = np.array(vectors)

        # Simple clustering using similarity-based grouping
        clusters = [[] for _ in range(n_clusters)]
        cluster_centers = [vectors_array[i] for i in range(n_clusters)]

        for i, result in enumerate(results):
            if i >= len(vectors):
                break

            vec = vectors[i]

            # Find nearest cluster
            best_cluster = 0
            best_similarity = -1

            for j, center in enumerate(cluster_centers):
                sim = cosine_similarity(vec, center)
                if sim > best_similarity:
                    best_similarity = sim
                    best_cluster = j

            clusters[best_cluster].append(result)

            # Update cluster center
            cluster_vectors = [r.get("vector") for r in clusters[best_cluster] if r.get("vector")]
            if cluster_vectors:
                cluster_arrays = [np.array(v) if isinstance(v, list) else v for v in cluster_vectors]
                cluster_centers[best_cluster] = np.mean(cluster_arrays, axis=0)

        return [c for c in clusters if c]

    def get_result_summary(
        self,
        results: List[Dict],
    ) -> Dict:
        """
        Get a summary of deduplicated results.

        Args:
            results: Deduplicated results

        Returns:
            Summary dictionary
        """
        if not results:
            return {
                "count": 0,
                "avg_score": 0,
                "avg_similarity": 0,
                "topics_covered": 0,
            }

        scores = [r.get("dedup_score", 0) for r in results]
        similarities = [r.get("query_similarity", 0) for r in results]

        return {
            "count": len(results),
            "avg_score": float(np.mean(scores)) if scores else 0,
            "avg_similarity": float(np.mean(similarities)) if similarities else 0,
            "max_score": float(np.max(scores)) if scores else 0,
            "topics_covered": min(self.topic_count, len(results)),
        }
