"""
Residual Pyramid Module for RAG Daily Plugin.

Implements multi-level semantic residual analysis using Gram-Schmidt orthogonalization.
Provides hierarchical vector decomposition for enhanced semantic retrieval.
"""

import numpy as np
from typing import Dict, List, Optional, Tuple
from scipy.linalg import norm
import logging

from .math_utils import (
    normalize_vector,
    cosine_similarity,
    dot_product,
    orthogonalize_vectors,
)

logger = logging.getLogger(__name__)


class PyramidLevel:
    """A single level in the residual pyramid."""

    def __init__(
        self,
        level: int,
        residual: np.ndarray,
        energy: float,
        energy_ratio: float,
    ):
        self.level = level
        self.residual = residual  # Residual vector at this level
        self.energy = energy  # Energy (magnitude) of residual
        self.energy_ratio = energy_ratio  # Ratio to total energy

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "level": self.level,
            "residual": self.residual.tolist() if isinstance(self.residual, np.ndarray) else self.residual,
            "energy": self.energy,
            "energy_ratio": self.energy_ratio,
        }


class HandshakeFeature:
    """Features extracted from handshake analysis."""

    def __init__(
        self,
        domain: int,
        direction: float,
        cross_product: float,
        resonance: float,
    ):
        self.domain = domain  # Which semantic domain
        self.direction = direction  # Direction cosine
        self.cross_product = cross_product  # Cross product magnitude
        self.resonance = resonance  # Resonance score

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "domain": self.domain,
            "direction": self.direction,
            "cross_product": self.cross_product,
            "resonance": self.resonance,
        }


class ResidualPyramid:
    """
    Residual Pyramid for multi-level semantic analysis.

    Features:
    - Gram-Schmidt orthogonal projection
    - Multi-level residual decomposition
    - Handshake feature extraction
    - Energy-based level selection
    """

    def __init__(
        self,
        max_levels: int = 3,
        top_k: int = 10,
        min_energy_ratio: float = 0.1,
        dimension: int = 1024,
    ):
        """
        Initialize the residual pyramid.

        Args:
            max_levels: Maximum pyramid levels (default: 3)
            top_k: Top k items to retrieve at each level (default: 10)
            min_energy_ratio: Minimum energy ratio to continue decomposition (default: 0.1)
            dimension: Vector dimension (default: 1024)
        """
        self.max_levels = max_levels
        self.top_k = top_k
        self.min_energy_ratio = min_energy_ratio
        self.dimension = dimension

        # Storage for analysis results
        self.levels: List[PyramidLevel] = []
        self.orthogonal_basis: List[np.ndarray] = []
        self.handshake_features: List[HandshakeFeature] = []

    def analyze(
        self,
        query_vector: np.ndarray,
        tags: Optional[List[Dict]] = None,
    ) -> Dict[str, any]:
        """
        Analyze a query vector using the residual pyramid.

        Args:
            query_vector: Input query vector
            tags: Optional list of tags with vectors for orthogonal basis

        Returns:
            Analysis results dictionary
        """
        self.levels.clear()
        self.orthogonal_basis.clear()
        self.handshake_features.clear()

        # Initialize
        current_residual = normalize_vector(query_vector.copy())
        total_energy = norm(current_residual)

        # Extract tag vectors if provided
        tag_vectors = []
        if tags:
            for tag in tags:
                vec = tag.get("vector")
                if vec is not None:
                    if isinstance(vec, list):
                        vec = np.array(vec)
                    tag_vectors.append(vec)

        # Build orthogonal basis from tags
        if tag_vectors:
            self.orthogonal_basis = orthogonalize_vectors(tag_vectors[:self.top_k])

        # Decompose through levels
        for level in range(self.max_levels):
            energy = norm(current_residual)
            energy_ratio = energy / total_energy if total_energy > 0 else 0

            # Create pyramid level
            pyramid_level = PyramidLevel(
                level=level,
                residual=current_residual.copy(),
                energy=float(energy),
                energy_ratio=float(energy_ratio),
            )
            self.levels.append(pyramid_level)

            # Check if we should stop
            if energy_ratio < self.min_energy_ratio:
                logger.debug(f"[ResidualPyramid] Stopped at level {level}, energy ratio: {energy_ratio:.3f}")
                break

            # Compute orthogonal projection if we have basis
            if self.orthogonal_basis:
                current_residual = self._compute_orthogonal_projection(
                    current_residual,
                    self.orthogonal_basis
                )

        # Compute handshake features
        if tags and self.orthogonal_basis:
            self.handshake_features = self._compute_handshakes(
                query_vector,
                tags[:self.top_k],
            )

        return self._compile_results()

    def _compute_orthogonal_projection(
        self,
        vector: np.ndarray,
        basis: List[np.ndarray],
    ) -> np.ndarray:
        """
        Compute orthogonal projection using Gram-Schmidt.

        Projects the vector onto the orthogonal complement of the basis.

        Args:
            vector: Input vector
            basis: List of orthogonal basis vectors

        Returns:
            Residual vector (orthogonal component)
        """
        residual = vector.copy()

        for basis_vec in basis:
            # Subtract projection onto each basis vector
            projection_coeff = dot_product(residual, basis_vec)
            residual = residual - (projection_coeff * basis_vec)

        return normalize_vector(residual) if norm(residual) > 1e-10 else residual

    def _compute_handshakes(
        self,
        query: np.ndarray,
        tags: List[Dict],
    ) -> List[HandshakeFeature]:
        """
        Compute handshake features between query and tags.

        Handshake features capture the semantic relationship between
        query vectors and tag vectors in the orthogonalized space.

        Args:
            query: Query vector
            tags: List of tags with vectors

        Returns:
            List of handshake features
        """
        features = []
        normalized_query = normalize_vector(query)

        for i, tag in enumerate(tags):
            vec = tag.get("vector")
            if vec is None:
                continue

            if isinstance(vec, list):
                vec = np.array(vec)

            normalized_vec = normalize_vector(vec)

            # Direction cosine
            direction = cosine_similarity(normalized_query, normalized_vec)

            # Cross product magnitude (2D approximation)
            cross = self._compute_cross_magnitude(normalized_query, normalized_vec)

            # Resonance (combined metric)
            resonance = (direction + (1.0 - cross)) / 2.0

            feature = HandshakeFeature(
                domain=i,
                direction=float(direction),
                cross_product=float(cross),
                resonance=float(resonance),
            )
            features.append(feature)

        return features

    def _compute_cross_magnitude(
        self,
        vec1: np.ndarray,
        vec2: np.ndarray,
    ) -> float:
        """
        Compute cross product magnitude as a measure of orthogonality.

        Args:
            vec1: First vector
            vec2: Second vector

        Returns:
            Cross product magnitude (normalized)
        """
        # For high-dimensional vectors, we use sin of angle
        cos_sim = cosine_similarity(vec1, vec2)
        sin_sim = np.sqrt(1.0 - min(1.0, cos_sim ** 2))
        return float(sin_sim)

    def _analyze_handshakes(
        self,
        handshakes: List[HandshakeFeature],
        dim: int,
    ) -> Dict[str, any]:
        """
        Analyze handshake features to extract semantic patterns.

        Args:
            handshakes: List of handshake features
            dim: Dimension to analyze

        Returns:
            Analysis results
        """
        if not handshakes:
            return {}

        # Sort by resonance
        sorted_handshakes = sorted(handshakes, key=lambda h: h.resonance, reverse=True)

        # Find dominant domains
        dominant = [h for h in sorted_handshakes if h.resonance > 0.7]

        # Compute statistics
        directions = [h.direction for h in handshakes]
        cross_products = [h.cross_product for h in handshakes]
        resonances = [h.resonance for h in handshakes]

        return {
            "dominant_domains": [{"domain": h.domain, "resonance": h.resonance} for h in dominant[:5]],
            "avg_direction": float(np.mean(directions)) if directions else 0,
            "avg_cross_product": float(np.mean(cross_products)) if cross_products else 0,
            "avg_resonance": float(np.mean(resonances)) if resonances else 0,
            "max_resonance": float(np.max(resonances)) if resonances else 0,
            "std_resonance": float(np.std(resonances)) if resonances else 0,
        }

    def _compile_results(self) -> Dict[str, any]:
        """
        Compile analysis results into a structured output.

        Returns:
            Dictionary with all analysis results
        """
        handshake_analysis = self._analyze_handshakes(
            self.handshake_features,
            self.dimension
        )

        return {
            "levels": [level.to_dict() for level in self.levels],
            "handshake_features": [f.to_dict() for f in self.handshake_features],
            "handshake_analysis": handshake_analysis,
            "orthogonal_basis_size": len(self.orthogonal_basis),
            "total_levels": len(self.levels),
            "residual_energy": self.levels[-1].energy if self.levels else 0,
        }

    def get_residual_at_level(self, level: int) -> Optional[np.ndarray]:
        """
        Get the residual vector at a specific level.

        Args:
            level: Level index

        Returns:
            Residual vector or None if level doesn't exist
        """
        if 0 <= level < len(self.levels):
            return self.levels[level].residual
        return None

    def get_energy_profile(self) -> List[float]:
        """
        Get the energy profile across all levels.

        Returns:
            List of energy ratios
        """
        return [level.energy_ratio for level in self.levels]

    def compute_level_scores(
        self,
        candidates: List[Dict],
    ) -> List[Tuple[int, float, int]]:
        """
        Compute relevance scores for candidates at each pyramid level.

        Args:
            candidates: List of candidates with vectors

        Returns:
            List of (candidate_index, score, level) tuples
        """
        results = []

        for level in self.levels:
            if level.energy_ratio < self.min_energy_ratio:
                continue

            residual = level.residual

            for i, candidate in enumerate(candidates):
                vec = candidate.get("vector")
                if vec is None:
                    continue

                if isinstance(vec, list):
                    vec = np.array(vec)

                # Compute similarity with residual at this level
                similarity = cosine_similarity(residual, vec)

                # Weight by energy ratio
                weighted_score = similarity * level.energy_ratio

                results.append((i, weighted_score, level.level))

        # Sort by score
        results.sort(key=lambda x: x[1], reverse=True)

        return results

    def enhance_query_with_pyramid(
        self,
        query: np.ndarray,
        weights: Optional[List[float]] = None,
    ) -> np.ndarray:
        """
        Enhance a query vector by combining residuals from all levels.

        Args:
            query: Original query vector
            weights: Optional weights for each level

        Returns:
            Enhanced query vector
        """
        if not self.levels:
            return query

        if weights is None:
            # Use energy ratios as weights
            weights = [level.energy_ratio for level in self.levels]

        # Normalize weights
        total_weight = sum(weights)
        if total_weight == 0:
            return query

        weights = [w / total_weight for w in weights]

        # Combine residuals
        enhanced = np.zeros_like(query)

        for level, weight in zip(self.levels, weights):
            enhanced += weight * level.residual

        # Normalize
        return normalize_vector(enhanced)

    def export_state(self) -> Dict:
        """
        Export pyramid state.

        Returns:
            Dictionary with pyramid state
        """
        return {
            "levels": [level.to_dict() for level in self.levels],
            "orthogonal_basis": [b.tolist() for b in self.orthogonal_basis],
            "handshake_features": [f.to_dict() for f in self.handshake_features],
            "config": {
                "max_levels": self.max_levels,
                "top_k": self.top_k,
                "min_energy_ratio": self.min_energy_ratio,
                "dimension": self.dimension,
            }
        }

    def clear(self) -> None:
        """Clear all stored data."""
        self.levels.clear()
        self.orthogonal_basis.clear()
        self.handshake_features.clear()
