"""
IVA Module 3 — Technical-Public Gap
=====================================
Quantifies the semantic distance between expert and
public discourse using sentence-transformers.
Computes: cosine distance between corpus centroids,
Jaccard lexical distance, complexity differential.

Input:  technical corpus + public corpus (JSON)
Output: technical-public gap score (float, 0–1)

Part of the CIDF framework — LUISS Guido Carli, 2026
Author: Giovanni Arosio
"""

from __future__ import annotations
import json
import os
import numpy as np
from pathlib import Path
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

MODEL_NAME = "all-MiniLM-L6-v2"
_model = None


def _get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer(MODEL_NAME)
    return _model


def _load_corpus(corpus_path: str) -> list[str]:
    """Load all JSON documents from a directory and return texts."""
    texts = []
    path = Path(corpus_path)
    for file in sorted(path.glob("*.json")):
        with open(file, "r", encoding="utf-8") as f:
            doc = json.load(f)
            if "text" in doc and doc["text"].strip():
                texts.append(doc["text"].strip())
    return texts


def _cosine_distance(texts_a: list[str], texts_b: list[str]) -> float:
    """Compute cosine distance between centroids of two text sets."""
    model = _get_model()
    emb_a = model.encode(texts_a, show_progress_bar=False)
    emb_b = model.encode(texts_b, show_progress_bar=False)
    centroid_a = np.mean(emb_a, axis=0, keepdims=True)
    centroid_b = np.mean(emb_b, axis=0, keepdims=True)
    similarity = cosine_similarity(centroid_a, centroid_b)[0][0]
    return float(1.0 - similarity)


def _jaccard_distance(texts_a: list[str], texts_b: list[str]) -> float:
    """Compute Jaccard distance between vocabularies of two corpora."""
    vocab_a = set(" ".join(texts_a).lower().split())
    vocab_b = set(" ".join(texts_b).lower().split())
    intersection = vocab_a & vocab_b
    union = vocab_a | vocab_b
    if not union:
        return 0.0
    return float(1.0 - len(intersection) / len(union))


def _complexity_differential(texts_a: list[str], texts_b: list[str]) -> float:
    """Compute normalized difference in average sentence length."""
    def avg_length(texts):
        lengths = [len(t.split()) for t in texts]
        return np.mean(lengths) if lengths else 0.0
    len_a = avg_length(texts_a)
    len_b = avg_length(texts_b)
    diff = abs(len_a - len_b)
    return float(min(diff / 50.0, 1.0))


def calculate_technical_public_gap(
    technical_corpus_path: str,
    public_corpus_path: str,
    weights: tuple[float, float, float] = (0.5, 0.3, 0.2),
) -> float:
    """
    Compute the Technical-Public Gap score.

    Args:
        technical_corpus_path: path to technical corpus directory.
        public_corpus_path: path to public corpus directory.
        weights: weights for (cosine, jaccard, complexity).

    Returns:
        Gap score as float in [0, 1].
    """
    tech_texts = _load_corpus(technical_corpus_path)
    pub_texts = _load_corpus(public_corpus_path)

    if not tech_texts or not pub_texts:
        raise ValueError("One or both corpora are empty.")

    cosine = _cosine_distance(tech_texts, pub_texts)
    jaccard = _jaccard_distance(tech_texts, pub_texts)
    complexity = _complexity_differential(tech_texts, pub_texts)

    w1, w2, w3 = weights
    score = w1 * cosine + w2 * jaccard + w3 * complexity
    return float(min(max(score, 0.0), 1.0))


if __name__ == "__main__":
    import sys
    case = sys.argv[1] if len(sys.argv) > 1 else "notpetya"
    tech_path = f"data/{case}/technical"
    pub_path = f"data/{case}/public"
    score = calculate_technical_public_gap(tech_path, pub_path)
    print(f"Technical-Public Gap [{case}]: {score:.3f}")
