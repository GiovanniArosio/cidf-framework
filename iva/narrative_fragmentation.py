"""
IVA Module 2 — Narrative Fragmentation (exploratory)
====================================================
Measures the diversity of competing narratives using **embedding-based
K-Means clustering** of sentence-transformer document embeddings.

NOTE ON METHOD: this module does NOT use BERTopic. Earlier documentation
claimed BERTopic; that claim was inaccurate and has been removed. The method
is sentence-transformer embeddings (all-MiniLM-L6-v2) followed by K-Means
clustering with a fixed random state.

Computes: cluster dispersion (normalized entropy), dominance ratio,
inter-cluster semantic distance.

EXPLORATORY STATUS: each case corpus holds ~15 documents that are curated,
source-derived analytical summaries (not raw full-text articles and not the
full public sphere). With so few short summaries, a single cluster count is not
definitive. Results are exploratory; a k = 3/4/5 sensitivity routine is
provided and should be reported instead of a single number.

Input:  public corpus directory (JSON)
Output: scalar score (compat) OR a detailed dict with k-sensitivity

Part of the CIDF framework — LUISS Guido Carli, 2026
Author: Giovanni Arosio
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
from scipy.stats import entropy as scipy_entropy
from sklearn.cluster import KMeans
from sklearn.metrics.pairwise import cosine_distances
from sentence_transformers import SentenceTransformer

MODEL_NAME = "all-MiniLM-L6-v2"
_model = None
N_CLUSTERS = 4
RANDOM_STATE = 42
SENSITIVITY_K = (3, 4, 5)

CORPUS_CAVEAT = (
    "Exploratory: corpus is ~15 curated, source-derived analytical summaries "
    "per case (not raw articles or the full public sphere). Method is "
    "embedding-based K-Means clustering (not BERTopic). Interpret cluster "
    "counts as exploratory; see k-sensitivity."
)


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
    """Normalized Shannon entropy over the cluster distribution."""
    counts = np.bincount(labels, minlength=n_clusters).astype(float)
    counts = counts[counts > 0]
    probs = counts / counts.sum()
    h = scipy_entropy(probs)
    h_max = np.log(n_clusters)
    return float(h / h_max) if h_max > 0 else 0.0


def _dominance_ratio(labels: np.ndarray, n_clusters: int) -> float:
    """1 minus the proportion of documents in the largest cluster."""
    counts = np.bincount(labels, minlength=n_clusters).astype(float)
    dominant = counts.max() / counts.sum()
    return float(1.0 - dominant)


def _inter_cluster_distance(
    embeddings: np.ndarray, labels: np.ndarray, n_clusters: int
) -> float:
    """Average cosine distance between (non-empty) cluster centroids."""
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


def _score_for_k(
    embeddings: np.ndarray,
    n_clusters: int,
    weights: tuple[float, float, float],
) -> dict[str, Any]:
    """Cluster the embeddings for one k and return the components + score."""
    kmeans = KMeans(n_clusters=n_clusters, random_state=RANDOM_STATE, n_init=10)
    labels = kmeans.fit_predict(embeddings)

    dispersion = _cluster_dispersion(labels, n_clusters)
    dominance = _dominance_ratio(labels, n_clusters)
    inter_dist = _inter_cluster_distance(embeddings, labels, n_clusters)

    w1, w2, w3 = weights
    score = float(min(max(w1 * dispersion + w2 * dominance + w3 * inter_dist, 0.0), 1.0))
    return {
        "k": n_clusters,
        "score": score,
        "dispersion": dispersion,
        "dominance": dominance,
        "inter_cluster_distance": inter_dist,
        "cluster_sizes": np.bincount(labels, minlength=n_clusters).tolist(),
    }


def analyze_narrative_fragmentation(
    public_corpus_path: str,
    n_clusters: int = N_CLUSTERS,
    weights: tuple[float, float, float] = (0.4, 0.3, 0.3),
    sensitivity_k: tuple[int, ...] = SENSITIVITY_K,
) -> dict[str, Any]:
    """Detailed, exploratory Narrative Fragmentation analysis.

    Returns the primary (k=``n_clusters``) components plus a k-sensitivity
    table over the valid values in ``sensitivity_k`` (a value is valid only if
    ``k <= n_documents``). Deterministic (fixed random state).
    """
    texts = _load_corpus(public_corpus_path)
    n_docs = len(texts)
    warnings = [CORPUS_CAVEAT]

    if n_docs < min(sensitivity_k):
        return {
            "available": False,
            "reason": f"only {n_docs} documents; need at least {min(sensitivity_k)}.",
            "method": "embedding-based K-Means clustering",
            "n_documents": n_docs,
            "warnings": warnings,
        }

    embeddings = _get_model().encode(texts, show_progress_bar=False)

    valid_k = [k for k in sorted(set(sensitivity_k)) if k <= n_docs]
    skipped_k = [k for k in sorted(set(sensitivity_k)) if k > n_docs]
    if skipped_k:
        warnings.append(
            f"k={skipped_k} skipped (exceeds {n_docs} documents)."
        )

    sensitivity = [_score_for_k(embeddings, k, weights) for k in valid_k]

    primary_k = n_clusters if n_clusters <= n_docs else valid_k[-1]
    primary = _score_for_k(embeddings, primary_k, weights)

    scores = [s["score"] for s in sensitivity]
    score_range = (min(scores), max(scores)) if scores else (None, None)
    if scores and (max(scores) - min(scores)) > 0.15:
        warnings.append(
            f"score varies by {max(scores) - min(scores):.2f} across k="
            f"{valid_k}; the fragmentation value is sensitive to cluster count."
        )

    return {
        "available": True,
        "method": "embedding-based K-Means clustering",
        "n_documents": n_docs,
        "primary_k": primary_k,
        "primary": primary,
        "score": primary["score"],
        "weights": list(weights),
        "random_state": RANDOM_STATE,
        "sensitivity_k": valid_k,
        "sensitivity": sensitivity,
        "score_range_over_k": score_range,
        "warnings": warnings,
    }


def calculate_narrative_fragmentation(
    public_corpus_path: str,
    n_clusters: int = N_CLUSTERS,
    weights: tuple[float, float, float] = (0.4, 0.3, 0.3),
) -> float:
    """Backward-compatible scalar Narrative Fragmentation score (primary k).

    Exploratory — prefer :func:`analyze_narrative_fragmentation`, which reports
    the k-sensitivity rather than a single cluster count.
    """
    texts = _load_corpus(public_corpus_path)
    if len(texts) < n_clusters:
        raise ValueError(f"Need at least {n_clusters} documents, got {len(texts)}.")
    embeddings = _get_model().encode(texts, show_progress_bar=False)
    return _score_for_k(embeddings, n_clusters, weights)["score"]


if __name__ == "__main__":
    cases = [
        ("notpetya", "data/notpetya/public"),
        ("kasat_viasat", "data/kasat_viasat/public"),
        ("pap_hack", "data/pap_hack/public"),
    ]
    for name, path in cases:
        res = analyze_narrative_fragmentation(path)
        if res["available"]:
            sens = ", ".join(f"k{ s['k'] }={s['score']:.3f}" for s in res["sensitivity"])
            print(f"Narrative Fragmentation [{name}] "
                  f"(embedding-based K-Means, exploratory): "
                  f"primary k={res['primary_k']} score={res['score']:.3f} | {sens}")
        else:
            print(f"Narrative Fragmentation [{name}]: UNAVAILABLE — {res['reason']}")
