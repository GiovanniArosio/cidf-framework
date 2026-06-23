"""
IVA Module 1 — Attribution Drift
==================================
Measures the instability of responsibility claims over time.
Computes: actor plurality, temporal instability,
convergence delay, confidence dispersion.

Input:  public corpus (JSON) with temporal metadata
Output: attribution drift score (float, 0–1)

Part of the CIDF framework — LUISS Guido Carli, 2026
Author: Giovanni Arosio
"""

from __future__ import annotations
import json
import re
import numpy as np
from datetime import datetime
from pathlib import Path
from collections import Counter


# Attribution actors to search for in texts
ATTRIBUTION_ACTORS = {
    "russia": ["russia", "russian", "kremlin", "gru", "fsb", "sandworm",
               "apt28", "apt29", "cozy bear", "fancy bear", "telebot"],
    "belarus": ["belarus", "belarusian", "lukashenko"],
    "china": ["china", "chinese", "pla", "apt41", "apt40"],
    "iran": ["iran", "iranian", "apt33", "apt34"],
    "north_korea": ["north korea", "lazarus", "kimsuky"],
    "criminal": ["criminal", "ransomware gang", "cybercriminal", "organized crime"],
    "unknown": ["unknown", "unidentified", "unclear", "undetermined",
                "unattributed", "mystery"],
    "state_actor": ["state actor", "state-sponsored", "nation state",
                    "foreign actor", "foreign state"],
}

CONFIDENCE_KEYWORDS = {
    "high": ["confirmed", "definitively", "formally attributed", "indicted",
             "evidence shows", "conclusively"],
    "medium": ["likely", "probably", "assessed", "believed", "suspected",
               "indicates", "suggests", "pointing to"],
    "low": ["possible", "speculative", "rumored", "alleged", "unclear",
            "unconfirmed", "may have", "might be"],
    "denial": ["denied", "rejected", "no evidence", "not responsible",
                "unfounded", "false claim"],
}

CONFIDENCE_SCORES = {"high": 1.0, "medium": 0.6, "low": 0.3, "denial": 0.0}


def _load_corpus(corpus_path: str) -> list[dict]:
    docs = []
    path = Path(corpus_path)
    for file in sorted(path.glob("*.json")):
        with open(file, "r", encoding="utf-8") as f:
            doc = json.load(f)
            if "text" in doc and "date" in doc:
                docs.append(doc)
    return sorted(docs, key=lambda d: d["date"])


def _parse_date(date_str: str) -> datetime:
    for fmt in ("%Y-%m-%d", "%Y-%m", "%Y"):
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    raise ValueError(f"Cannot parse date: {date_str}")


def _extract_actors(text: str) -> set[str]:
    text_lower = text.lower()
    found = set()
    for actor, keywords in ATTRIBUTION_ACTORS.items():
        if any(kw in text_lower for kw in keywords):
            found.add(actor)
    return found


def _extract_confidence(text: str) -> float:
    text_lower = text.lower()
    for level, keywords in CONFIDENCE_KEYWORDS.items():
        if any(kw in text_lower for kw in keywords):
            return CONFIDENCE_SCORES[level]
    return 0.5


def _actor_plurality(docs: list[dict]) -> float:
    """
    Number of distinct actors blamed across all documents, normalized.
    Higher = more actors blamed = more drift.
    """
    all_actors = set()
    for doc in docs:
        all_actors |= _extract_actors(doc["text"])
    return float(min(len(all_actors) / 5.0, 1.0))


def _temporal_instability(docs: list[dict]) -> float:
    """
    How often the dominant attributed actor changes over time.
    Higher = more shifts = more drift.
    """
    if len(docs) < 3:
        return 0.5

    dominant_per_doc = []
    for doc in docs:
        actors = _extract_actors(doc["text"])
        if actors:
            dominant_per_doc.append(list(actors)[0])
        else:
            dominant_per_doc.append("unknown")

    shifts = sum(
        1 for i in range(1, len(dominant_per_doc))
        if dominant_per_doc[i] != dominant_per_doc[i - 1]
    )
    return float(min(shifts / max(len(dominant_per_doc) - 1, 1), 1.0))


def _convergence_delay(docs: list[dict]) -> float:
    """
    Days until attribution stabilizes (same actor in 3 consecutive docs).
    Higher = longer wait = more drift.
    """
    if len(docs) < 3:
        return 1.0

    try:
        first_date = _parse_date(docs[0]["date"])
        last_date = _parse_date(docs[-1]["date"])
        total_days = max((last_date - first_date).days, 1)
    except ValueError:
        return 0.5

    actors_sequence = []
    for doc in docs:
        actors = _extract_actors(doc["text"])
        actors_sequence.append(frozenset(actors))

    for i in range(len(actors_sequence) - 2):
        if (actors_sequence[i] == actors_sequence[i + 1] ==
                actors_sequence[i + 2] and actors_sequence[i]):
            try:
                convergence_date = _parse_date(docs[i]["date"])
                delay = (convergence_date - first_date).days
                return float(min(delay / 365.0, 1.0))
            except ValueError:
                pass

    return 1.0


def _confidence_dispersion(docs: list[dict]) -> float:
    """
    Variance in confidence levels across documents.
    Higher variance = more uncertainty = more drift.
    """
    scores = [_extract_confidence(doc["text"]) for doc in docs]
    if len(scores) < 2:
        return 0.5
    variance = float(np.var(scores))
    return float(min(variance * 4.0, 1.0))


def calculate_attribution_drift(
    public_corpus_path: str,
    weights: tuple[float, float, float, float] = (0.30, 0.25, 0.25, 0.20),
) -> float:
    """
    Compute the Attribution Drift score.

    Args:
        public_corpus_path: path to public corpus directory.
        weights: weights for (actor_plurality, temporal_instability,
                 convergence_delay, confidence_dispersion).

    Returns:
        Attribution drift score as float in [0, 1].
    """
    docs = _load_corpus(public_corpus_path)
    if not docs:
        raise ValueError("Public corpus is empty.")

    plurality = _actor_plurality(docs)
    instability = _temporal_instability(docs)
    delay = _convergence_delay(docs)
    dispersion = _confidence_dispersion(docs)

    w1, w2, w3, w4 = weights
    score = w1 * plurality + w2 * instability + w3 * delay + w4 * dispersion
    return float(min(max(score, 0.0), 1.0))


if __name__ == "__main__":
    cases = [
        ("notpetya", "data/notpetya/public"),
        ("pap_hack", "data/pap_hack/public"),
        ("kasat_viasat", "data/kasat_viasat/public"),
    ]
    for name, path in cases:
        score = calculate_attribution_drift(path)
        print(f"Attribution Drift [{name}]: {score:.3f}")
