"""
IVA Module 1 — Attribution Drift (structured coding)
====================================================
Measures the instability of attribution-of-responsibility claims over time,
using the **manual, text-grounded attribution coding** stored on each public
corpus document (see ``docs/attribution_coding_protocol.md``).

This module replaces the previous keyword/substring approach (the ``pla`` ∈
"place"/"platform"/"explains" false positives, ``state_actor`` as a separate
actor, non-deterministic ``list(set)[0]`` selection). None of that remains.

Uncertainty handling (corrected)
--------------------------------
Two state sets are kept deliberately distinct::

    ATTRIBUTION_RELATED_STATES = {"attributed", "uncertain", "denial"}
    IDENTIFIED_ACTOR_STATES    = {"attributed", "denial"}

* ``no_claim`` documents are excluded from temporal actor transitions.
* An ordered **attribution-related sequence** includes every attribution-related
  document; an ``uncertain`` document with actor ``unknown`` appears explicitly
  as ``unknown``.
* **Actor plurality** counts only distinct *identified* actors; ``unknown``
  never inflates plurality.
* **Temporal instability** compares consecutive items in the FULL
  attribution-related sequence, so ``unknown -> russia``, ``russia -> unknown``
  and ``russia -> china`` all register.

Convergence (corrected)
-----------------------
Convergence = the first point at which **three consecutive** attribution-related
documents identify the **same specific actor**, with no intervening ``unknown``,
competing actor, or ``denial``. The convergence date is the **third** confirming
document's date (when stability becomes observable). Delay is measured from the
first in-scope event document. If no qualifying run exists, ``converged`` is
False, the component score is ``None``, and the composite uses an explicitly
labelled non-convergence maximum with a warning.

Analytical scope
----------------
Only ``analysis_role == "analysis"`` documents feed the metrics; pre-incident
context material (e.g. ``pap_pub_014``) is excluded and reported separately.

Determinism: documents are sorted by ``(date, doc_id)``. No ``set`` iteration is
ever used to choose an actor.

Caveat: the corpus is curated, source-derived analytical summaries (~15/case),
not raw articles or the full public sphere. Results are exploratory.

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

CONFIDENCE_LEVELS = {"high": 1.0, "medium": 0.6, "low": 0.3, "none": 0.0}

CONVERGENCE_HORIZON_DAYS = 365.0
CONVERGENCE_RUN_LENGTH = 3

# Distinct, deliberately separate state sets (see module docstring).
ATTRIBUTION_RELATED_STATES = {"attributed", "uncertain", "denial"}
IDENTIFIED_ACTOR_STATES = {"attributed", "denial"}
_NON_ACTOR_LABELS = {"unknown", "none"}

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


def _load_coded_docs(
    corpus_path: str,
) -> tuple[list[dict[str, Any]], list[str], int]:
    """Load in-scope public docs, sorted by ``(date, doc_id)``.

    Returns ``(coded_docs, warnings, excluded_context_count)``. Only documents
    with ``analysis_role == "analysis"`` are returned; pre-incident context
    documents are excluded and counted. Missing coding is reported via
    ``warnings``; malformed coding raises ``AttributionCodingError``.
    """
    path = Path(corpus_path)
    if not path.is_dir():
        raise AttributionCodingError(f"Corpus path is not a directory: {corpus_path}")

    raw_docs: list[tuple[datetime, str, CorpusDocument]] = []
    excluded_context = 0
    for file in sorted(path.glob("*.json")):
        data = json.loads(file.read_text(encoding="utf-8"))
        try:
            doc = CorpusDocument.from_dict(data)
        except CorpusValidationError as exc:
            raise AttributionCodingError(f"{file.name}: {exc}") from exc
        if not doc.is_active_analysis:
            excluded_context += 1
            continue
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
        try:
            doc.validate_attribution_coding()
        except CorpusValidationError as exc:
            raise AttributionCodingError(str(exc)) from exc
        rec = dict(doc.raw)
        rec["_sort_date"] = sort_date
        rec["_doc_id"] = doc_id
        coded.append(rec)
    return coded, warnings, excluded_context


# --------------------------------------------------------------------------
# Sequences
# --------------------------------------------------------------------------
def _attribution_related_sequence(docs: list[dict]) -> list[dict[str, Any]]:
    """Ordered attribution-related documents (attributed/uncertain/denial).

    Each item carries the actor *token* as it should appear in the temporal
    sequence — an ``uncertain``/``unknown`` document appears explicitly as
    ``"unknown"``. ``no_claim`` documents are excluded entirely.
    """
    seq = []
    for d in docs:
        if d["attribution_state"] in ATTRIBUTION_RELATED_STATES:
            seq.append({
                "doc_id": d["_doc_id"],
                "date": d["_sort_date"],
                "state": d["attribution_state"],
                "actor": d["attribution_actor"],   # specific actor or "unknown"
                "confidence": d["attribution_confidence"],
            })
    return seq


def _identified_actors(docs: list[dict]) -> list[str]:
    """Sorted distinct *identified* actors (IDENTIFIED_ACTOR_STATES only)."""
    return sorted({
        d["attribution_actor"] for d in docs
        if d["attribution_state"] in IDENTIFIED_ACTOR_STATES
        and d["attribution_actor"] not in _NON_ACTOR_LABELS
    })


# --------------------------------------------------------------------------
# Components
# --------------------------------------------------------------------------
def _actor_plurality(docs: list[dict], related_seq: list[dict]) -> dict[str, Any]:
    """Distinct *identified* actors. ``unknown`` is reported but never counted."""
    distinct = _identified_actors(docs)
    unidentified = sum(1 for item in related_seq if item["actor"] == "unknown")
    score = float(min(max(len(distinct) - 1, 0) / 2.0, 1.0))
    return {
        "score": score,
        "distinct_actors": distinct,
        "distinct_actor_count": len(distinct),
        "unidentified_claim_count": unidentified,
    }


def _temporal_instability(related_seq: list[dict]) -> dict[str, Any]:
    """Fraction of consecutive transitions in the FULL attribution-related
    sequence whose actor token changes (including unknown<->actor)."""
    tokens = [item["actor"] for item in related_seq]
    if len(tokens) < 2:
        return {
            "score": 0.0, "transitions": 0, "sequence_length": len(tokens),
            "note": "fewer than two attribution-related documents; instability "
                    "not computable, reported as 0.0 (not imputed).",
        }
    transitions = sum(1 for i in range(1, len(tokens)) if tokens[i] != tokens[i - 1])
    return {
        "score": float(transitions / (len(tokens) - 1)),
        "transitions": transitions,
        "sequence_length": len(tokens),
        "transition_pairs": [
            f"{tokens[i - 1]}->{tokens[i]}"
            for i in range(1, len(tokens)) if tokens[i] != tokens[i - 1]
        ],
    }


def _convergence(docs: list[dict], related_seq: list[dict]) -> dict[str, Any]:
    """Convergence = first run of ``CONVERGENCE_RUN_LENGTH`` consecutive
    attribution-related docs naming the SAME specific actor (no intervening
    unknown/competing/denial). Delay = first in-scope doc -> third confirming
    doc. Not converged -> ``converged=False`` and ``score=None``.
    """
    if not docs:
        return {"converged": False, "score": None, "raw_days": None,
                "converged_actor": None,
                "reason": "no in-scope documents."}

    first_inscope_date = docs[0]["_sort_date"]
    tokens = [item["actor"] for item in related_seq]

    for i in range(len(tokens) - CONVERGENCE_RUN_LENGTH + 1):
        window = tokens[i:i + CONVERGENCE_RUN_LENGTH]
        head = window[0]
        if head not in _NON_ACTOR_LABELS and all(w == head for w in window):
            third = related_seq[i + CONVERGENCE_RUN_LENGTH - 1]
            raw_days = max((third["date"] - first_inscope_date).days, 0)
            return {
                "converged": True,
                "score": float(min(raw_days / CONVERGENCE_HORIZON_DAYS, 1.0)),
                "raw_days": raw_days,
                "converged_actor": head,
                "convergence_doc_id": third["doc_id"],
                "convergence_date": third["date"].strftime("%Y-%m-%d"),
                "first_inscope_date": first_inscope_date.strftime("%Y-%m-%d"),
                "run_length": CONVERGENCE_RUN_LENGTH,
                "horizon_days": CONVERGENCE_HORIZON_DAYS,
            }

    return {
        "converged": False,
        "score": None,
        "raw_days": None,
        "converged_actor": None,
        "run_length": CONVERGENCE_RUN_LENGTH,
        "reason": (
            f"no run of {CONVERGENCE_RUN_LENGTH} consecutive attribution-related "
            "documents naming the same specific actor was observed."
        ),
    }


def _confidence_dispersion(related_seq: list[dict]) -> dict[str, Any]:
    """Variance of attribution confidence across attribution-related docs
    (uncertain documents carry confidence ``none`` = 0.0)."""
    scores = [CONFIDENCE_LEVELS[item["confidence"]] for item in related_seq]
    if len(scores) < 2:
        return {
            "score": 0.0, "n_claims": len(scores), "variance": 0.0,
            "note": "fewer than two attribution-related documents; dispersion "
                    "not computable, reported as 0.0 (not imputed).",
        }
    variance = float(np.var(scores))
    return {"score": float(min(variance * 4.0, 1.0)),
            "n_claims": len(scores), "variance": variance}


# --------------------------------------------------------------------------
# Public API
# --------------------------------------------------------------------------
def analyze_attribution_drift(
    public_corpus_path: str,
    weights: tuple[float, float, float, float] = DEFAULT_WEIGHTS,
) -> dict[str, Any]:
    """Detailed, diagnostics-first Attribution Drift analysis (in-scope docs)."""
    coded, warnings, excluded_context = _load_coded_docs(public_corpus_path)
    if excluded_context:
        warnings.append(
            f"{excluded_context} context_preincident document(s) excluded from "
            "event-level metrics (retained in the corpus/CSV only)."
        )

    total_inscope = len(coded) + sum(1 for w in warnings if "missing attribution" in w)
    coding_coverage = (len(coded) / total_inscope) if total_inscope else 0.0

    state_counts = Counter(d["attribution_state"] for d in coded)

    if not coded:
        return {
            "available": False,
            "reason": "no validly coded in-scope documents",
            "composite_score": None,
            "in_scope_document_count": 0,
            "excluded_context_count": excluded_context,
            "coding_coverage": coding_coverage,
            "warnings": warnings or ["corpus empty or uncoded"],
        }
    if coding_coverage < 1.0:
        warnings.append(
            f"coding coverage {coding_coverage:.2f} < 1.0; composite computed "
            "over coded in-scope documents only"
        )

    related_seq = _attribution_related_sequence(coded)
    plurality = _actor_plurality(coded, related_seq)
    instability = _temporal_instability(related_seq)
    convergence = _convergence(coded, related_seq)
    dispersion = _confidence_dispersion(related_seq)

    # Convergence contribution: use the score, or an explicitly labelled
    # non-convergence maximum (1.0) with a warning when it did not converge.
    if convergence["converged"]:
        convergence_contrib = convergence["score"]
    else:
        convergence_contrib = 1.0
        warnings.append(
            "no convergence observed (no run of "
            f"{CONVERGENCE_RUN_LENGTH} consecutive same-actor documents); "
            "convergence term set to the non-convergence maximum (1.0)."
        )

    w1, w2, w3, w4 = weights
    composite = (
        w1 * plurality["score"]
        + w2 * instability["score"]
        + w3 * convergence_contrib
        + w4 * dispersion["score"]
    )
    composite = float(min(max(composite, 0.0), 1.0))

    unresolved_count = plurality["unidentified_claim_count"]
    unresolved_proportion = (
        unresolved_count / len(related_seq) if related_seq else 0.0
    )

    n_related = len(related_seq)
    if n_related < 3:
        warnings.append(
            f"only {n_related} attribution-related document(s); temporal "
            "components are weakly determined by a small, curated corpus."
        )

    return {
        "available": True,
        "composite_score": composite,
        "weights": list(weights),
        "in_scope_document_count": len(coded),
        "excluded_context_count": excluded_context,
        "coding_coverage": coding_coverage,
        "state_counts": dict(state_counts),
        "attribution_related_sequence": [
            {"doc_id": x["doc_id"], "date": x["date"].strftime("%Y-%m-%d"),
             "state": x["state"], "actor": x["actor"],
             "confidence": x["confidence"]}
            for x in related_seq
        ],
        "identified_actor_sequence": [
            x["actor"] for x in related_seq
            if x["state"] in IDENTIFIED_ACTOR_STATES
            and x["actor"] not in _NON_ACTOR_LABELS
        ],
        "unresolved_claim_count": unresolved_count,
        "unresolved_claim_proportion": float(unresolved_proportion),
        "components": {
            "actor_plurality": plurality,
            "temporal_instability": instability,
            "convergence_delay": convergence,
            "confidence_dispersion": dispersion,
        },
        "warnings": warnings,
    }


def calculate_attribution_drift(
    public_corpus_path: str,
    weights: tuple[float, float, float, float] = DEFAULT_WEIGHTS,
) -> float:
    """Backward-compatible scalar Attribution Drift score.

    Requires complete, valid attribution coding for all in-scope documents;
    raises ``AttributionCodingError`` otherwise.
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
            conv = c["convergence_delay"]
            conv_str = (f"{conv['score']:.2f} @ {conv['convergence_date']}"
                        if conv["converged"] else "NOT CONVERGED")
            seq = " ".join(x["actor"][:3] for x in res["attribution_related_sequence"])
            print(f"[{name}] drift={res['composite_score']:.3f} | "
                  f"in-scope={res['in_scope_document_count']} "
                  f"(ctx excluded={res['excluded_context_count']}) | "
                  f"plur={c['actor_plurality']['score']:.2f} "
                  f"instab={c['temporal_instability']['score']:.2f} "
                  f"conv={conv_str} disp={c['confidence_dispersion']['score']:.2f}")
            print(f"        seq: {seq}")
        else:
            print(f"[{name}] UNAVAILABLE — {res['reason']}")
