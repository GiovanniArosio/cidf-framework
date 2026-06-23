"""
IVA Module 2 — Narrative Fragmentation
========================================
Measures the diversity of competing narratives using
BERTopic topic modeling and sentence embeddings.
Computes: cluster dispersion, dominance ratio,
inter-cluster semantic distance.

Input:  public corpus (JSON)
Output: narrative fragmentation score (float, 0–1)

Part of the CIDF framework — LUISS Guido Carli, 2026
Author: Giovanni Arosio
"""

from __future__ import annotations
import json
import numpy as np
from pathlib import Path
from sentence_transformers import SentenceTransformer
from sklearn.cluster import KMeans
from sklearn.metrics.pairwise import cosine_distances
from scipy.stats import entropy as scipy_entropy

MODEL_NAME = "all-MiniLM-L6-v2"
_model = None
N_CLUSTERS = 4


def _get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer(MODEL_NAME)
    return _model


def _load_corpus(corpus_path: str) -> list[str]:
    texts = []
    path = Path(corpus_path)
    for file in sorted(path.glob("*.json")):
        with open(file, "r", encoding="utf-8") as f:
            doc = json.load(f)
            if "text" in doc and doc["text"].strip():
                texts.append(doc["text"].strip())
    return texts


def _cluster_dispersion(labels: np.ndarray, n_clusters: int) -> float:
    """
    Normalized Shannon entropy over cluster distribution.
    High entropy = documents spread evenly = high fragmentation.
    """
    counts = np.bincount(labels, minlength=n_clusters).astype(float)
    counts = counts[counts > 0]
    probs = counts / counts.sum()
    h = scipy_entropy(probs)
    h_max = np.log(n_clusters)
    return float(h / h_max) if h_max > 0 else 0.0


def _dominance_ratio(labels: np.ndarray, n_clusters: int) -> float:
    """
    1 minus proportion of documents in the largest cluster.
    High = no single narrative dominates = high fragmentation.
    """
    counts = np.bincount(labels, minlength=n_clusters).astype(float)
    dominant = counts.max() / counts.sum()
    return float(1.0 - dominant)


def _inter_cluster_distance(embeddings: np.ndarray, labels: np.ndarray, n_clusters: int) -> float:
    """
    Average cosine distance between cluster centroids.
    High = clusters semantically far apart = high fragmentation.
    """
    centroids = []
    for i in range(n_clusters):
        mask = labels == i
        if mask.sum() > 0:
            centroids.append(embeddings[mask].mean(axis=0))

    if len(centroids) < 2:
        return 0.0

    centroids = np.array(centroids)
    dist_matrix = cosine_distances(centroids)
    n = len(centroids)
    total = dist_matrix.sum() / (n * (n - 1))
    return float(min(total, 1.0))


def calculate_narrative_fragmentation(
    public_corpus_path: str,
    n_clusters: int = N_CLUSTERS,
    weights: tuple[float, float, float] = (0.4, 0.3, 0.3),
) -> float:
    """
    Compute the Narrative Fragmentation score.

    Args:
        public_corpus_path: path to public corpus directory.
        n_clusters: number of narrative clusters to identify.
        weights: weights for (dispersion, dominance, inter_distance).

    Returns:
        Fragmentation score as float in [0, 1].
    """
    texts = _load_corpus(public_corpus_path)
    if len(texts) < n_clusters:
        raise ValueError(f"Need at least {n_clusters} documents, got {len(texts)}.")

    model = _get_model()
    embeddings = model.encode(texts, show_progress_bar=False)

    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    labels = kmeans.fit_predict(embeddings)

    dispersion = _cluster_dispersion(labels, n_clusters)
    dominance = _dominance_ratio(labels, n_clusters)
    inter_dist = _inter_cluster_distance(embeddings, labels, n_clusters)

    w1, w2, w3 = weights
    score = w1 * dispersion + w2 * dominance + w3 * inter_dist
    return float(min(max(score, 0.0), 1.0))


if __name__ == "__main__":
    cases = [
        ("notpetya", "data/notpetya/public"),
        ("pap_hack", "data/pap_hack/public"),
        ("kasat_viasat", "data/kasat_viasat/public"),
    ]
    for name, path in cases:
        score = calculate_narrative_fragmentation(path)
        print(f"Narrative Fragmentation [{name}]: {score:.3f}")
