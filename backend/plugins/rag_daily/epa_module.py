"""
Embedding Projection Analysis (EPA) Module for RAG Daily Plugin.

Implements weighted PCA projection and K-Means clustering for semantic space analysis.
Provides cross-domain resonance detection and semantic clustering capabilities.
"""

import numpy as np
from typing import Dict, List, Optional, Tuple, Callable, Any
from scipy.cluster.vq import kmeans2, whiten
from scipy.spatial.distance import cdist
from scipy.linalg import qr
import json
import logging

from .math_utils import (
    normalize_vector,
    cosine_similarity,
    compute_pca,
    weighted_average,
)

logger = logging.getLogger(__name__)


class EPAModule:
    """
    Embedding Projection Analysis module.

    Features:
    - Weighted PCA for semantic space projection
    - K-Means clustering for semantic groups
    - Cross-domain resonance detection
    - Orthogonal basis vector management
    """

    EPA_BASIS_KEY = "epa_basis_vectors"
    EPA_CLUSTERS_KEY = "epa_cluster_centers"

    def __init__(
        self,
        max_basis_dim: int = 64,
        cluster_count: int = 32,
        dimension: int = 1024,
    ):
        """
        Initialize the EPA module.

        Args:
            max_basis_dim: Maximum basis dimension for projection (default: 64)
            cluster_count: Number of clusters for K-Means (default: 32)
            dimension: Vector dimension (default: 1024 for bge-m3)
        """
        self.max_basis_dim = max_basis_dim
        self.cluster_count = cluster_count
        self.dimension = dimension

        # Basis vectors (orthogonal projection matrix)
        self.basis_vectors: Optional[np.ndarray] = None

        # Cluster centers for semantic grouping
        self.cluster_centers: Optional[np.ndarray] = None

        # Cluster metadata
        self.cluster_metadata: Dict[int, Dict] = {}

        # Initialization flag
        self._initialized = False

    async def initialize(
        self,
        tags_vectors: Optional[List[np.ndarray]] = None,
        kv_store_get_func: Optional[Callable[[], Any]] = None,
    ) -> None:
        """
        Initialize EPA basis vectors from tags or cached storage.

        Args:
            tags_vectors: Optional list of tag vectors to compute basis from
            kv_store_get_func: Optional function to retrieve cached basis from KV store
        """
        # Try to load from cache first
        if kv_store_get_func:
            try:
                cached_basis = await kv_store_get_func(self.EPA_BASIS_KEY)
                if cached_basis:
                    basis_data = json.loads(cached_basis)
                    self.basis_vectors = np.array(basis_data["vectors"])
                    self.max_basis_dim = self.basis_vectors.shape[1]
                    logger.info(f"[EPA] Loaded {self.max_basis_dim} basis vectors from cache")

                    # Also load cluster centers if available
                    cached_clusters = await kv_store_get_func(self.EPA_CLUSTERS_KEY)
                    if cached_clusters:
                        cluster_data = json.loads(cached_clusters)
                        self.cluster_centers = np.array(cluster_data["centers"])
                        self.cluster_metadata = cluster_data.get("metadata", {})
                        logger.info(f"[EPA] Loaded {len(self.cluster_centers)} cluster centers from cache")

                    self._initialized = True
                    return
            except Exception as e:
                logger.warning(f"[EPA] Failed to load cached basis: {e}")

        # Compute from tags vectors if provided
        if tags_vectors and len(tags_vectors) >= self.cluster_count:
            self._compute_basis_from_tags(tags_vectors)
            self._initialized = True
            logger.info("[EPA] Initialized from tag vectors")
        else:
            logger.warning("[EPA] Insufficient tag vectors for initialization, using random basis")
            # Initialize with random orthonormal basis
            self._initialize_random_basis()

        self._initialized = True

    def _initialize_random_basis(self) -> None:
        """Initialize with random orthonormal basis vectors."""
        # Create random matrix
        random_matrix = np.random.randn(self.dimension, self.max_basis_dim)

        # Apply QR decomposition to get orthonormal basis
        from scipy.linalg import qr
        self.basis_vectors, _ = qr(random_matrix)

        logger.info(f"[EPA] Initialized random orthonormal basis: {self.basis_vectors.shape}")

    def _compute_basis_from_tags(self, tags_vectors: List[np.ndarray]) -> None:
        """
        Compute orthogonal basis vectors from tag vectors using weighted PCA.

        Args:
            tags_vectors: List of tag vectors
        """
        if not tags_vectors:
            return

        # Stack vectors into matrix
        vectors_matrix = np.array(tags_vectors)

        # Ensure we have enough dimensions
        n_components = min(self.max_basis_dim, vectors_matrix.shape[0], vectors_matrix.shape[1])

        # Compute weighted PCA
        _, components, _ = compute_pca(vectors_matrix, n_components)

        # Store as basis vectors (transpose for projection)
        self.basis_vectors = components

        # Compute clusters
        self._cluster_tags(tags_vectors, self.cluster_count)

        logger.info(f"[EPA] Computed basis: {self.basis_vectors.shape}, clusters: {len(self.cluster_centers)}")

    def project(self, vector: np.ndarray) -> np.ndarray:
        """
        Project a vector onto the semantic space defined by basis vectors.

        Args:
            vector: Input vector to project

        Returns:
            Projected vector in semantic space
        """
        if self.basis_vectors is None:
            logger.warning("[EPA] Basis vectors not initialized, returning input")
            return vector

        # Normalize input
        normalized = normalize_vector(vector)

        # Project onto basis
        projection = np.dot(normalized, self.basis_vectors)

        return projection

    def inverse_project(self, projected: np.ndarray) -> np.ndarray:
        """
        Reconstruct a vector from its projection.

        Args:
            projected: Projected vector in semantic space

        Returns:
            Reconstructed vector in original space
        """
        if self.basis_vectors is None:
            return projected

        # Reconstruct using basis vectors
        reconstructed = np.dot(projected, self.basis_vectors.T)

        return normalize_vector(reconstructed)

    def detect_cross_domain_resonance(
        self,
        vector: np.ndarray,
        top_k: int = 5,
    ) -> List[Tuple[int, float]]:
        """
        Detect cross-domain resonance by checking projection onto different clusters.

        Args:
            vector: Input vector
            top_k: Number of top resonant domains to return

        Returns:
            List of (cluster_id, resonance_score) tuples
        """
        if self.cluster_centers is None:
            return []

        # Project the vector
        projected = self.project(vector)

        # Calculate distance to each cluster center
        if len(self.cluster_centers) > 0:
            # Reshape projected for distance calculation
            projected_reshaped = projected.reshape(1, -1)

            # Calculate distances
            distances = cdist(projected_reshaped, self.cluster_centers, metric='euclidean')[0]

            # Convert distances to resonance scores (higher = more resonant)
            max_dist = np.max(distances) if np.max(distances) > 0 else 1.0
            resonance_scores = 1.0 - (distances / max_dist)

            # Get top k
            top_indices = np.argsort(resonance_scores)[-top_k:][::-1]

            results = [(int(i), float(resonance_scores[i])) for i in top_indices]
        else:
            results = []

        return results

    def _cluster_tags(
        self,
        tags: List[np.ndarray],
        k: int,
    ) -> np.ndarray:
        """
        Perform robust K-Means clustering on tag vectors.

        Args:
            tags: List of tag vectors
            k: Number of clusters

        Returns:
            Cluster centers
        """
        if not tags or len(tags) < k:
            logger.warning(f"[EPA] Insufficient tags for clustering: {len(tags)} < {k}")
            k = max(1, len(tags))

        tags_array = np.array(tags)

        # Whiten the data for better clustering
        whitened = whiten(tags_array)

        try:
            # Perform K-Means with multiple iterations for stability
            centroids, _ = kmeans2(whitened, k, minit='points', iter=20)

            # Transform back to original space
            # Compute std dev used in whiten
            std_dev = np.std(tags_array, axis=0)
            std_dev[std_dev == 0] = 1.0  # Avoid division by zero

            self.cluster_centers = centroids * std_dev

            # Compute cluster metadata
            self._compute_cluster_metadata(tags_array)

        except Exception as e:
            logger.error(f"[EPA] K-Means clustering failed: {e}")
            # Fallback: use random selection
            indices = np.random.choice(len(tags_array), min(k, len(tags_array)), replace=False)
            self.cluster_centers = tags_array[indices]

        return self.cluster_centers

    def _compute_cluster_metadata(self, tags_array: np.ndarray) -> None:
        """
        Compute metadata for each cluster.

        Args:
            tags_array: Array of tag vectors
        """
        if self.cluster_centers is None:
            return

        self.cluster_metadata = {}

        for i, center in enumerate(self.cluster_centers):
            # Calculate distances to all tags
            distances = cdist([center], tags_array, metric='euclidean')[0]

            # Find nearest tags
            nearest_indices = np.argsort(distances)[:5]

            self.cluster_metadata[i] = {
                "center_size": float(np.linalg.norm(center)),
                "avg_distance": float(np.mean(distances)),
                "nearest_indices": nearest_indices.tolist(),
            }

    def _compute_weighted_pca(
        self,
        vectors: np.ndarray,
        weights: Optional[np.ndarray] = None,
    ) -> np.ndarray:
        """
        Compute weighted PCA on vectors.

        Args:
            vectors: Matrix of vectors (n_samples x n_features)
            weights: Optional weights for each vector

        Returns:
            Principal components
        """
        if weights is None:
            weights = np.ones(len(vectors))

        # Normalize weights
        weights = weights / np.sum(weights)

        # Compute weighted mean
        weighted_mean = np.average(vectors, axis=0, weights=weights)

        # Center the data
        centered = vectors - weighted_mean

        # Apply sqrt of weights
        sqrt_weights = np.sqrt(weights).reshape(-1, 1)
        weighted_centered = centered * sqrt_weights

        # Compute covariance
        cov_matrix = np.dot(weighted_centered.T, weighted_centered)

        # Compute eigendecomposition
        eigenvalues, eigenvectors = np.linalg.eigh(cov_matrix)

        # Sort by eigenvalue (descending)
        idx = np.argsort(eigenvalues)[::-1]
        eigenvectors = eigenvectors[:, idx]

        return eigenvectors

    def get_semantic_neighbors(
        self,
        vector: np.ndarray,
        candidates: List[np.ndarray],
        top_k: int = 10,
    ) -> List[Tuple[int, float]]:
        """
        Find semantically similar vectors in the projected space.

        Args:
            vector: Query vector
            candidates: List of candidate vectors
            top_k: Number of neighbors to return

        Returns:
            List of (index, similarity) tuples
        """
        if not candidates:
            return []

        # Project all vectors
        projected_query = self.project(vector)
        projected_candidates = np.array([self.project(v) for v in candidates])

        # Calculate cosine similarities in projected space
        similarities = []
        for i, pc in enumerate(projected_candidates):
            sim = cosine_similarity(projected_query, pc)
            similarities.append((i, sim))

        # Sort by similarity
        similarities.sort(key=lambda x: x[1], reverse=True)

        return similarities[:top_k]

    def export_state(self) -> Dict:
        """
        Export EPA state for caching.

        Returns:
            Dictionary with EPA state
        """
        state = {
            "config": {
                "max_basis_dim": self.max_basis_dim,
                "cluster_count": self.cluster_count,
                "dimension": self.dimension,
            }
        }

        if self.basis_vectors is not None:
            state["vectors"] = self.basis_vectors.tolist()

        if self.cluster_centers is not None:
            state["centers"] = self.cluster_centers.tolist()
            state["metadata"] = self.cluster_metadata

        return state

    async def save_to_cache(self, kv_store_set_func: Callable[..., Any]) -> None:
        """
        Save EPA state to KV store cache.

        Args:
            kv_store_set_func: Async function to set values in KV store
        """
        if self.basis_vectors is not None:
            basis_state = {
                "vectors": self.basis_vectors.tolist(),
                "config": {
                    "max_basis_dim": self.max_basis_dim,
                    "dimension": self.dimension,
                }
            }
            try:
                await kv_store_set_func(
                    self.EPA_BASIS_KEY,
                    json.dumps(basis_state),
                    None
                )
            except Exception as e:
                logger.error(f"[EPA] Failed to save basis vectors: {e}")

        if self.cluster_centers is not None:
            cluster_state = {
                "centers": self.cluster_centers.tolist(),
                "metadata": self.cluster_metadata,
            }
            try:
                await kv_store_set_func(
                    self.EPA_CLUSTERS_KEY,
                    json.dumps(cluster_state),
                    None
                )
            except Exception as e:
                logger.error(f"[EPA] Failed to save cluster centers: {e}")

        logger.info("[EPA] State saved to cache")
