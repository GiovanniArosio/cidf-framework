"""
IVA Diagnostic — Technical–Public Gap (EXPLORATORY DIAGNOSTIC ONLY)
==================================================================
Quantifies the semantic distance between technical and public discourse using
sentence-transformer embeddings plus lexical and document-length contrasts.

STATUS — DIAGNOSTIC ONLY. This module is **excluded** from every IVA aggregate,
from CIDI, and from any headline/primary metric. On the active datasets the
composite barely varied across cases (≈0.48–0.49), driven by near-ceiling
lexical Jaccard distance and the fact that the corpus consists of standardized,
source-derived analytical summaries (not raw articles). The near-identical
values are an artefact, not a substantive finding. Outputs are retained only as
an exploratory diagnostic and must be read with that caveat.

Components (raw, preserved):
  * cosine distance between technical/public embedding centroids
  * Jaccard distance between the two vocabularies
  * document-length differential (difference in mean words PER DOCUMENT —
    this is NOT sentence length and NOT a "complexity" measure)

Input:  technical corpus + public corpus (JSON)
Output: diagnostic dict (raw components + warnings). No aggregate is exported
        for use in IVA/CIDI.

Part of the CIDF framework — LUISS Guido Carli, 2026
Author: Giovanni Arosio
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from utils.corpus_schema import is_active_analysis  # noqa: E402

MODEL_NAME = "all-MiniLM-L6-v2"
_model = None

# Diagnostic thresholds for surfacing interpretability caveats.
JACCARD_CEILING = 0.85           # near-ceiling lexical distance
DOC_LENGTH_NORM_WORDS = 50.0     # normalization scale for the length differential

DIAGNOSTIC_CAVEAT = (
    "EXPLORATORY DIAGNOSTIC ONLY — not part of any IVA/CIDI aggregate. The "
    "corpus consists of standardized, source-derived analytical summaries "
    "(not raw articles or the full public sphere); with small, summarized "
    "corpora the composite varies too little across cases to support "
    "comparative interpretation."
)


def _get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer(MODEL_NAME)
    return _model


def _load_corpus(corpus_path: str) -> list[str]:
    """Load in-scope document texts (excludes context_preincident material)."""
    texts = []
    path = Path(corpus_path)
    for file in sorted(path.glob("*.json")):
        with open(file, "r", encoding="utf-8") as f:
            doc = json.load(f)
            if not is_active_analysis(doc):
                continue
            if "text" in doc and doc["text"].strip():
                texts.append(doc["text"].strip())
    return texts


def _cosine_distance(texts_a: list[str], texts_b: list[str]) -> float:
    """Cosine distance between the embedding centroids of two text sets."""
    model = _get_model()
    emb_a = model.encode(texts_a, show_progress_bar=False)
    emb_b = model.encode(texts_b, show_progress_bar=False)
    centroid_a = np.mean(emb_a, axis=0, keepdims=True)
    centroid_b = np.mean(emb_b, axis=0, keepdims=True)
    similarity = cosine_similarity(centroid_a, centroid_b)[0][0]
    return float(1.0 - similarity)


def _jaccard_distance(texts_a: list[str], texts_b: list[str]) -> float:
    """Jaccard distance between the two corpora's vocabularies."""
    vocab_a = set(" ".join(texts_a).lower().split())
    vocab_b = set(" ".join(texts_b).lower().split())
    union = vocab_a | vocab_b
    if not union:
        return 0.0
    return float(1.0 - len(vocab_a & vocab_b) / len(union))


def _document_length_differential(texts_a: list[str], texts_b: list[str]) -> dict[str, float]:
    """Normalized difference in **mean words per document** (NOT sentence length).

    Returns the raw mean lengths alongside the normalized differential so the
    measure cannot be misread as a "complexity" or sentence-level statistic.
    """
    def mean_words(texts: list[str]) -> float:
        lengths = [len(t.split()) for t in texts]
        return float(np.mean(lengths)) if lengths else 0.0

    len_a = mean_words(texts_a)
    len_b = mean_words(texts_b)
    diff = abs(len_a - len_b)
    return {
        "score": float(min(diff / DOC_LENGTH_NORM_WORDS, 1.0)),
        "mean_words_technical": len_a,
        "mean_words_public": len_b,
        "abs_difference_words": diff,
    }


def diagnose_technical_public_gap(
    technical_corpus_path: str,
    public_corpus_path: str,
) -> dict[str, Any]:
    """Exploratory diagnostic. Returns raw components and interpretability
    warnings. Deliberately returns **no** single aggregate intended for use in
    an IVA or CIDI composite.
    """
    tech_texts = _load_corpus(technical_corpus_path)
    pub_texts = _load_corpus(public_corpus_path)
    if not tech_texts or not pub_texts:
        raise ValueError("One or both corpora are empty.")

    cosine = _cosine_distance(tech_texts, pub_texts)
    jaccard = _jaccard_distance(tech_texts, pub_texts)
    length = _document_length_differential(tech_texts, pub_texts)

    warnings = [DIAGNOSTIC_CAVEAT]
    if jaccard >= JACCARD_CEILING:
        warnings.append(
            f"Jaccard distance {jaccard:.3f} is near ceiling (>= {JACCARD_CEILING}); "
            "lexical distance is saturated and not discriminating between cases."
        )

    return {
        "status": "exploratory_diagnostic_only",
        "included_in_aggregate": False,
        "n_technical_docs": len(tech_texts),
        "n_public_docs": len(pub_texts),
        "components": {
            "cosine_distance": float(cosine),
            "jaccard_distance": float(jaccard),
            "document_length_differential": length,
        },
        "warnings": warnings,
    }


if __name__ == "__main__":
    import sys
    case = sys.argv[1] if len(sys.argv) > 1 else "notpetya"
    tech_path = f"data/{case}/technical"
    pub_path = f"data/{case}/public"
    diag = diagnose_technical_public_gap(tech_path, pub_path)
    c = diag["components"]
    print(f"Technical–Public Gap [{case}] (EXPLORATORY DIAGNOSTIC ONLY):")
    print(f"  cosine distance ............ {c['cosine_distance']:.3f}")
    print(f"  jaccard distance ........... {c['jaccard_distance']:.3f}")
    print(f"  document-length differential {c['document_length_differential']['score']:.3f} "
          f"(tech {c['document_length_differential']['mean_words_technical']:.0f} vs "
          f"public {c['document_length_differential']['mean_words_public']:.0f} words/doc)")
    for w in diag["warnings"]:
        print(f"  ! {w}")
