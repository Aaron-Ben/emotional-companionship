"""
Mathematical utility functions for RAG Daily Plugin.

Provides vector operations, similarity calculations, and other mathematical utilities.
"""

import numpy as np
from typing import List, Tuple, Optional
from collections import Counter
import logging

logger = logging.getLogger(__name__)


def normalize_vector(vec: np.ndarray) -> np.ndarray:
    """
    Normalize a vector to unit length.

    Args:
        vec: Input vector

    Returns:
        Normalized vector (unit length)
    """
    magnitude = np.linalg.norm(vec)
    if magnitude == 0:
        return vec
    return vec / magnitude


def cosine_similarity(vec1: np.ndarray, vec2: np.ndarray) -> float:
    """
    Calculate cosine similarity between two vectors.

    Args:
        vec1: First vector
        vec2: Second vector

    Returns:
        Cosine similarity value between -1 and 1
    """
    # Normalize both vectors
    norm1 = normalize_vector(vec1)
    norm2 = normalize_vector(vec2)
    return float(np.dot(norm1, norm2))


def dot_product(vec1: np.ndarray, vec2: np.ndarray) -> float:
    """
    Calculate dot product of two vectors.

    Args:
        vec1: First vector
        vec2: Second vector

    Returns:
        Dot product value
    """
    return float(np.dot(vec1, vec2))


def vector_magnitude(vec: np.ndarray) -> float:
    """
    Calculate the magnitude (length) of a vector.

    Args:
        vec: Input vector

    Returns:
        Vector magnitude
    """
    return float(np.linalg.norm(vec))


def dice_similarity(str1: str, str2: str) -> float:
    """
    Calculate Dice coefficient for string similarity.

    The Dice coefficient is a measure of similarity between two strings.
    It's calculated as 2 * |A ∩ B| / (|A| + |B|) where A and B are sets of character bigrams.

    Args:
        str1: First string
        str2: Second string

    Returns:
        Dice coefficient between 0 and 1
    """
    if not str1 or not str2:
        return 0.0

    # Create character bigrams
    def get_bigrams(s: str) -> set:
        return {s[i:i+2] for i in range(len(s) - 1)}

    bigrams1 = get_bigrams(str1.lower())
    bigrams2 = get_bigrams(str2.lower())

    if not bigrams1 or not bigrams2:
        return 0.0

    # Calculate Dice coefficient
    intersection = len(bigrams1 & bigrams2)
    total = len(bigrams1) + len(bigrams2)

    return (2 * intersection) / total if total > 0 else 0.0


def jaccard_similarity(vec1: np.ndarray, vec2: np.ndarray) -> float:
    """
    Calculate Jaccard similarity between two binary vectors.

    Args:
        vec1: First vector
        vec2: Second vector

    Returns:
        Jaccard similarity between 0 and 1
    """
    # Convert to binary (non-zero elements are 1)
    binary1 = (vec1 != 0).astype(int)
    binary2 = (vec2 != 0).astype(int)

    intersection = np.sum(binary1 & binary2)
    union = np.sum(binary1 | binary2)

    return float(intersection / union) if union > 0 else 0.0


def euclidean_distance(vec1: np.ndarray, vec2: np.ndarray) -> float:
    """
    Calculate Euclidean distance between two vectors.

    Args:
        vec1: First vector
        vec2: Second vector

    Returns:
        Euclidean distance
    """
    return float(np.linalg.norm(vec1 - vec2))


def manhattan_distance(vec1: np.ndarray, vec2: np.ndarray) -> float:
    """
    Calculate Manhattan (L1) distance between two vectors.

    Args:
        vec1: First vector
        vec2: Second vector

    Returns:
        Manhattan distance
    """
    return float(np.sum(np.abs(vec1 - vec2)))


def weighted_average(vectors: List[np.ndarray], weights: List[float]) -> np.ndarray:
    """
    Calculate weighted average of vectors.

    Args:
        vectors: List of vectors
        weights: List of weights (must match vectors length)

    Returns:
        Weighted average vector

    Raises:
        ValueError: If vectors and weights lengths don't match, or if weights contain invalid values
    """
    if len(vectors) != len(weights):
        raise ValueError("Vectors and weights must have the same length")

    if not vectors:
        raise ValueError("Vectors list cannot be empty")

    # Validate weights
    weights_array = np.array(weights, dtype=np.float64)
    if np.any(weights_array < 0):
        raise ValueError("Weights must be non-negative")
    if np.any(np.isnan(weights_array)) or np.any(np.isinf(weights_array)):
        raise ValueError("Weights must be finite numbers")

    total_weight = np.sum(weights_array)
    if total_weight == 0:
        raise ValueError("Total weight cannot be zero")

    # Convert to numpy array for efficient computation
    vectors_array = np.array(vectors)
    weights_array = weights_array.reshape(-1, 1)

    # Calculate weighted average
    weighted_sum = np.sum(vectors_array * weights_array, axis=0)
    return weighted_sum / total_weight


def softmax(scores: np.ndarray, temperature: float = 1.0) -> np.ndarray:
    """
    Apply softmax function to an array of scores.

    Args:
        scores: Input scores
        temperature: Temperature parameter (higher = softer distribution)

    Returns:
        Softmax probabilities
    """
    scaled_scores = scores / temperature
    # Subtract max for numerical stability
    exp_scores = np.exp(scaled_scores - np.max(scaled_scores))
    return exp_scores / np.sum(exp_scores)


def batch_cosine_similarity(query: np.ndarray, vectors: np.ndarray) -> np.ndarray:
    """
    Calculate cosine similarity between a query vector and multiple vectors.

    Args:
        query: Query vector
        vectors: Matrix of vectors (n x dim)

    Returns:
        Array of similarity scores
    """
    # Normalize query
    query_norm = normalize_vector(query)

    # Normalize all vectors
    vectors_norm = vectors / np.linalg.norm(vectors, axis=1, keepdims=True)

    # Calculate dot products
    return np.dot(vectors_norm, query_norm)


def orthogonalize_vectors(vectors: List[np.ndarray]) -> List[np.ndarray]:
    """
    Apply Gram-Schmidt orthogonalization to a list of vectors.

    Args:
        vectors: List of vectors to orthogonalize

    Returns:
        List of orthogonalized vectors
    """
    if not vectors:
        return []

    result = []
    for vec in vectors:
        temp = vec.copy()
        for existing in result:
            # Subtract projection onto existing orthogonal vector
            projection = np.dot(temp, existing) * existing
            temp = temp - projection

        # Only keep non-zero vectors
        if np.linalg.norm(temp) > 1e-10:
            result.append(normalize_vector(temp))

    return result


def compute_pca(data: np.ndarray, n_components: int) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Compute Principal Component Analysis on data.

    Args:
        data: Data matrix (n_samples x n_features)
        n_components: Number of principal components to compute

    Returns:
        Tuple of (transformed_data, components, explained_variance)
    """
    # Center the data
    mean = np.mean(data, axis=0)
    centered_data = data - mean

    # Compute covariance matrix
    cov_matrix = np.cov(centered_data.T)

    # Compute eigenvalues and eigenvectors
    eigenvalues, eigenvectors = np.linalg.eigh(cov_matrix)

    # Sort by eigenvalue (descending)
    idx = np.argsort(eigenvalues)[::-1]
    eigenvalues = eigenvalues[idx]
    eigenvectors = eigenvectors[:, idx]

    # Take top n_components
    components = eigenvectors[:, :n_components]

    # Transform data
    transformed_data = np.dot(centered_data, components)

    # Explained variance ratio
    explained_variance = eigenvalues[:n_components] / np.sum(eigenvalues)

    return transformed_data, components, explained_variance


def string_similarity_tokens(str1: str, str2: str) -> float:
    """
    Calculate token-based string similarity (similar to JS _calculateSimilarity).

    This is a word-level Jaccard-like similarity.

    Args:
        str1: First string
        str2: Second string

    Returns:
        Similarity score between 0 and 1
    """
    if not str1 or not str2:
        return 0.0

    # Split into tokens
    tokens1 = set(str1.lower().split())
    tokens2 = set(str2.lower().split())

    if not tokens1 or not tokens2:
        return 0.0

    intersection = len(tokens1 & tokens2)
    union = len(tokens1 | tokens2)

    return float(intersection / union) if union > 0 else 0.0


def top_k_indices(values: np.ndarray, k: int, largest: bool = True) -> np.ndarray:
    """
    Get indices of top k values in an array.

    Args:
        values: Input array
        k: Number of top values to return
        largest: If True, return largest; if False, return smallest

    Returns:
        Array of indices
    """
    if largest:
        return np.argpartition(values, -k)[-k:][np.argsort(values[-k:])]
    else:
        return np.argpartition(values, k)[:k][np.argsort(values[:k])]


def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    """
    Safely divide two numbers, returning default if denominator is zero.

    Args:
        numerator: Numerator
        denominator: Denominator
        default: Default value to return if denominator is zero

    Returns:
        Division result or default
    """
    return numerator / denominator if denominator != 0 else default
