"""
IVA Module 1 — Attribution Drift (structured coding)
====================================================
Measures the instability of attribution-of-responsibility claims over time,
using the **manual, text-grounded attribution coding** stored on each public
corpus document (see ``docs/attribution_coding_protocol.md``).

This module replaces the previous keyword/substring approach, which produced
false positives (the substring ``pla`` matching "place"/"platform"/"explains"),
treated country *mentions* as attribution, counted ``state_actor`` as a separate
actor, and used non-deterministic ``list(set)[0]`` actor selection. None of those
behaviours remain.

Components (each in [0, 1], higher = more drift):
  * actor plurality        — distinct *identified* actors blamed
  * temporal instability   — actor changes between consecutive attributed docs
  * convergence delay      — time from first document to first dominant-actor claim
  * confidence dispersion  — variance of attribution confidence among claims

Determinism: documents are sorted by ``(date, doc_id)``. No ``set`` iteration is
ever used to choose an actor.

Input:  public corpus directory (JSON) with attribution coding fields
Output: scalar drift score (compat) OR a detailed diagnostics dict

Caveat: the corpus consists of curated, source-derived analytical summaries
(~15 per case), not raw full-text articles or the full public sphere. Results
are exploratory and corpus-bound.

Part of the CIDF framework — LUISS Guido Carli, 2026
Author: Giovanni Arosio
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from utils.corpus_schema import (  # noqa: E402
    CorpusDocument,
    CorpusValidationError,
)

# Map qualitative confidence to a numeric level for dispersion only.
CONFIDENCE_LEVELS = {"high": 1.0, "medium": 0.6, "low": 0.3, "none": 0.0}

# Normalisation horizon for convergence delay, in days.
CONVERGENCE_HORIZON_DAYS = 365.0

# States that constitute an actor-bearing attribution claim.
_CLAIM_STATES = {"attributed", "denial"}

DEFAULT_WEIGHTS = (0.30, 0.25, 0.25, 0.20)


class AttributionCodingError(ValueError):
    """Raised when required attribution coding is missing or invalid."""


def _parse_date(date_str: str) -> datetime:
    for fmt in ("%Y-%m-%d", "%Y-%m", "%Y"):
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    raise ValueError(f"Cannot parse date: {date_str}")


def _load_coded_docs(corpus_path: str) -> tuple[list[dict[str, Any]], list[str]]:
    """Load public corpus docs, deterministically sorted by ``(date, doc_id)``.

    Returns ``(coded_docs, warnings)`` where ``coded_docs`` contains only
    documents carrying valid attribution coding. Missing coding is reported via
    ``warnings``; malformed coding raises ``AttributionCodingError`` (a hard
    failure, per the coding protocol).
    """
    path = Path(corpus_path)
    if not path.is_dir():
        raise AttributionCodingError(f"Corpus path is not a directory: {corpus_path}")

    raw_docs: list[tuple[datetime, str, CorpusDocument]] = []
    for file in sorted(path.glob("*.json")):
        data = json.loads(file.read_text(encoding="utf-8"))
        try:
            doc = CorpusDocument.from_dict(data)
        except CorpusValidationError as exc:
            raise AttributionCodingError(f"{file.name}: {exc}") from exc
        try:
            sort_date = _parse_date(doc.date)
        except ValueError as exc:
            raise AttributionCodingError(f"{file.name}: {exc}") from exc
        raw_docs.append((sort_date, doc.id, doc))

    raw_docs.sort(key=lambda t: (t[0], t[1]))

    coded: list[dict[str, Any]] = []
    warnings: list[str] = []
    for sort_date, doc_id, doc in raw_docs:
        if not doc.has_attribution_coding():
            warnings.append(f"{doc_id}: missing attribution coding (excluded)")
            continue
        # Malformed coding is a hard error.
        try:
            doc.validate_attribution_coding()
        except CorpusValidationError as exc:
            raise AttributionCodingError(str(exc)) from exc
        rec = dict(doc.raw)
        rec["_sort_date"] = sort_date
        rec["_doc_id"] = doc_id
        coded.append(rec)
    return coded, warnings


# --------------------------------------------------------------------------
# Component calculations (all deterministic; no set-ordering actor selection)
# --------------------------------------------------------------------------
def _identified_actor_sequence(docs: list[dict]) -> list[str]:
    """Temporally ordered actors from attributed docs with an identified actor.

    Excludes ``no_claim`` and ``uncertain`` documents and ``unknown`` actors
    (handled explicitly elsewhere). Order follows the ``(date, doc_id)`` sort
    already applied to ``docs``.
    """
    seq = []
    for d in docs:
        if d["attribution_state"] in _CLAIM_STATES:
            actor = d["attribution_actor"]
            if actor not in ("unknown", "none"):
                seq.append(actor)
    return seq


def _actor_plurality(docs: list[dict]) -> dict[str, Any]:
    """Number of distinct *identified* actors blamed.

    Single consistently-named actor -> 0 (no plurality-driven drift). Each
    additional distinct actor adds drift, saturating at 3+ actors. ``unknown``
    actors are reported separately and never counted as a distinct actor.
    """
    actors = Counter(_identified_actor_sequence(docs))
    distinct = sorted(actors)
    unidentified = sum(
        1 for d in docs
        if d["attribution_state"] in _CLAIM_STATES
        and d["attribution_actor"] == "unknown"
    )
    score = float(min(max(len(distinct) - 1, 0) / 2.0, 1.0))
    return {
        "score": score,
        "distinct_actors": distinct,
        "distinct_actor_count": len(distinct),
        "actor_counts": dict(actors),
        "unidentified_claim_count": unidentified,
    }


def _temporal_instability(docs: list[dict]) -> dict[str, Any]:
    """Fraction of consecutive attributed docs whose identified actor changes."""
    seq = _identified_actor_sequence(docs)
    if len(seq) < 2:
        return {
            "score": 0.0,
            "transitions": 0,
            "sequence_length": len(seq),
            "note": "fewer than two identified-actor claims; instability not "
                    "computable, reported as 0.0 (not imputed).",
        }
    transitions = sum(1 for i in range(1, len(seq)) if seq[i] != seq[i - 1])
    return {
        "score": float(transitions / (len(seq) - 1)),
        "transitions": transitions,
        "sequence_length": len(seq),
    }


def _convergence_delay(docs: list[dict]) -> dict[str, Any]:
    """Days from the first document to the first dominant-actor claim.

    Dominant actor = the most frequently identified actor among attributed
    documents (ties broken deterministically by actor name). If no identified
    attribution exists, drift is maximal (1.0) and flagged.
    """
    if not docs:
        return {"score": 1.0, "raw_days": None, "dominant_actor": None,
                "note": "empty corpus"}

    first_date = docs[0]["_sort_date"]
    actors = Counter(_identified_actor_sequence(docs))
    if not actors:
        return {
            "score": 1.0,
            "raw_days": None,
            "dominant_actor": None,
            "note": "no identified attribution; convergence never reached "
                    "(score 1.0, not imputed).",
        }

    # Deterministic dominant actor: highest count, then alphabetical.
    max_count = max(actors.values())
    dominant = sorted(a for a, c in actors.items() if c == max_count)[0]

    convergence_date = None
    for d in docs:
        if (d["attribution_state"] in _CLAIM_STATES
                and d["attribution_actor"] == dominant):
            convergence_date = d["_sort_date"]
            break

    raw_days = max((convergence_date - first_date).days, 0)
    return {
        "score": float(min(raw_days / CONVERGENCE_HORIZON_DAYS, 1.0)),
        "raw_days": raw_days,
        "dominant_actor": dominant,
        "horizon_days": CONVERGENCE_HORIZON_DAYS,
    }


def _confidence_dispersion(docs: list[dict]) -> dict[str, Any]:
    """Variance of attribution confidence among attributed documents."""
    scores = [
        CONFIDENCE_LEVELS[d["attribution_confidence"]]
        for d in docs
        if d["attribution_state"] in _CLAIM_STATES
    ]
    if len(scores) < 2:
        return {
            "score": 0.0,
            "n_claims": len(scores),
            "variance": 0.0,
            "note": "fewer than two attribution claims; dispersion not "
                    "computable, reported as 0.0 (not imputed).",
        }
    variance = float(np.var(scores))
    return {
        "score": float(min(variance * 4.0, 1.0)),
        "n_claims": len(scores),
        "variance": variance,
    }


# --------------------------------------------------------------------------
# Public API
# --------------------------------------------------------------------------
def analyze_attribution_drift(
    public_corpus_path: str,
    weights: tuple[float, float, float, float] = DEFAULT_WEIGHTS,
) -> dict[str, Any]:
    """Detailed, diagnostics-first Attribution Drift analysis.

    Returns a dict with the composite score (when available), each component's
    score and diagnostics, document/state/actor counts, coding coverage, and
    warnings. ``available`` is False (with a reason) when no validly coded
    document exists.
    """
    coded, warnings = _load_coded_docs(public_corpus_path)

    total_files = len(coded) + sum(1 for w in warnings if "missing" in w)
    coding_coverage = (len(coded) / total_files) if total_files else 0.0

    state_counts = Counter(d["attribution_state"] for d in coded)
    actor_counts = Counter(
        d["attribution_actor"] for d in coded
        if d["attribution_state"] in _CLAIM_STATES
    )

    if not coded:
        return {
            "available": False,
            "reason": "no validly coded documents",
            "composite_score": None,
            "document_count": 0,
            "coding_coverage": coding_coverage,
            "warnings": warnings or ["corpus empty or uncoded"],
        }
    if coding_coverage < 1.0:
        warnings.append(
            f"coding coverage {coding_coverage:.2f} < 1.0; composite computed "
            "over coded documents only"
        )

    plurality = _actor_plurality(coded)
    instability = _temporal_instability(coded)
    delay = _convergence_delay(coded)
    dispersion = _confidence_dispersion(coded)

    w1, w2, w3, w4 = weights
    composite = (
        w1 * plurality["score"]
        + w2 * instability["score"]
        + w3 * delay["score"]
        + w4 * dispersion["score"]
    )
    composite = float(min(max(composite, 0.0), 1.0))

    n_claims = state_counts.get("attributed", 0) + state_counts.get("denial", 0)
    if n_claims < 3:
        warnings.append(
            f"only {n_claims} actor-bearing claim(s); temporal components are "
            "weakly determined by a small, curated corpus (exploratory)."
        )

    return {
        "available": True,
        "composite_score": composite,
        "weights": list(weights),
        "document_count": len(coded),
        "coding_coverage": coding_coverage,
        "state_counts": dict(state_counts),
        "claim_actor_counts": dict(actor_counts),
        "components": {
            "actor_plurality": plurality,
            "temporal_instability": instability,
            "convergence_delay": delay,
            "confidence_dispersion": dispersion,
        },
        "warnings": warnings,
    }


def calculate_attribution_drift(
    public_corpus_path: str,
    weights: tuple[float, float, float, float] = DEFAULT_WEIGHTS,
) -> float:
    """Backward-compatible scalar Attribution Drift score.

    Requires complete, valid attribution coding; raises
    ``AttributionCodingError`` otherwise (attribution must only be computed when
    coding is complete — see the coding protocol).
    """
    result = analyze_attribution_drift(public_corpus_path, weights=weights)
    if not result["available"]:
        raise AttributionCodingError(result["reason"])
    if result["coding_coverage"] < 1.0:
        raise AttributionCodingError(
            f"attribution coding incomplete (coverage "
            f"{result['coding_coverage']:.2f}); complete coding before scoring."
        )
    return result["composite_score"]


if __name__ == "__main__":
    cases = [
        ("notpetya", "data/notpetya/public"),
        ("kasat_viasat", "data/kasat_viasat/public"),
        ("pap_hack", "data/pap_hack/public"),
    ]
    for name, path in cases:
        res = analyze_attribution_drift(path)
        if res["available"]:
            c = res["components"]
            print(f"Attribution Drift [{name}]: {res['composite_score']:.3f}  "
                  f"(plurality={c['actor_plurality']['score']:.2f}, "
                  f"instability={c['temporal_instability']['score']:.2f}, "
                  f"convergence={c['convergence_delay']['score']:.2f}, "
                  f"dispersion={c['confidence_dispersion']['score']:.2f}, "
                  f"coverage={res['coding_coverage']:.2f})")
        else:
            print(f"Attribution Drift [{name}]: UNAVAILABLE — {res['reason']}")
