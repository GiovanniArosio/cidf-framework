"""
IVA Module 4 — Amplification Velocity
=======================================
Measures the speed at which non-institutional narratives
circulate in the early stages of a crisis.
Computes: information void duration, early non-institutional
ratio, peak velocity, institutional lag.

Input:  public corpus (JSON) with temporal metadata
Output: amplification velocity score (float, 0–1)

Part of the CIDF framework — LUISS Guido Carli, 2026
Author: Giovanni Arosio
"""

from __future__ import annotations
import json
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict


INSTITUTIONAL_SOURCES = {
    "institutional", "technical"
}

EARLY_WINDOW_DAYS = 3


def _load_corpus(corpus_path: str) -> list[dict]:
    """Load all JSON documents from a directory."""
    docs = []
    path = Path(corpus_path)
    for file in sorted(path.glob("*.json")):
        with open(file, "r", encoding="utf-8") as f:
            doc = json.load(f)
            if "date" in doc and "source_type" in doc:
                docs.append(doc)
    return docs


def _parse_date(date_str: str) -> datetime:
    """Parse date string to datetime."""
    for fmt in ("%Y-%m-%d", "%Y-%m", "%Y"):
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    raise ValueError(f"Cannot parse date: {date_str}")


def _information_void_duration(docs: list[dict], crisis_date: datetime) -> float:
    """
    Days before first institutional response, normalized.
    Higher = longer void = more amplification opportunity.
    """
    institutional_dates = []
    for doc in docs:
        if doc.get("source_type") in INSTITUTIONAL_SOURCES:
            try:
                d = _parse_date(doc["date"])
                institutional_dates.append(d)
            except ValueError:
                continue

    if not institutional_dates:
        return 1.0

    first_institutional = min(institutional_dates)
    void_days = (first_institutional - crisis_date).days
    void_days = max(0, void_days)
    return float(min(void_days / 30.0, 1.0))


def _early_non_institutional_ratio(
    docs: list[dict], crisis_date: datetime
) -> float:
    """
    Proportion of non-institutional sources in first 72 hours.
    Higher = more non-institutional early content.
    """
    early_cutoff = crisis_date + timedelta(days=EARLY_WINDOW_DAYS)
    early_docs = []
    for doc in docs:
        try:
            d = _parse_date(doc["date"])
            if crisis_date <= d <= early_cutoff:
                early_docs.append(doc)
        except ValueError:
            continue

    if not early_docs:
        return 0.5

    non_institutional = sum(
        1 for d in early_docs
        if d.get("source_type") not in INSTITUTIONAL_SOURCES
    )
    return float(non_institutional / len(early_docs))


def _peak_velocity(docs: list[dict], crisis_date: datetime) -> float:
    """
    Maximum daily publication rate of non-institutional content,
    normalized by total corpus size.
    """
    daily_counts: dict[str, int] = defaultdict(int)
    for doc in docs:
        if doc.get("source_type") not in INSTITUTIONAL_SOURCES:
            try:
                d = _parse_date(doc["date"])
                key = d.strftime("%Y-%m-%d")
                daily_counts[key] += 1
            except ValueError:
                continue

    if not daily_counts:
        return 0.0

    peak = max(daily_counts.values())
    return float(min(peak / max(len(docs), 1), 1.0))


def _institutional_lag(docs: list[dict], crisis_date: datetime) -> float:
    """
    Days between first non-institutional and first institutional publication.
    Higher = institutions responded later = more void.
    """
    non_inst_dates = []
    inst_dates = []

    for doc in docs:
        try:
            d = _parse_date(doc["date"])
            if doc.get("source_type") in INSTITUTIONAL_SOURCES:
                inst_dates.append(d)
            else:
                non_inst_dates.append(d)
        except ValueError:
            continue

    if not non_inst_dates or not inst_dates:
        return 0.5

    first_non_inst = min(non_inst_dates)
    first_inst = min(inst_dates)
    lag_days = (first_inst - first_non_inst).days
    lag_days = max(0, lag_days)
    return float(min(lag_days / 30.0, 1.0))


def calculate_amplification_velocity(
    public_corpus_path: str,
    crisis_date_str: str,
    weights: tuple[float, float, float, float] = (0.25, 0.25, 0.25, 0.25),
) -> float:
    """
    Compute the Amplification Velocity score.

    Args:
        public_corpus_path: path to public corpus directory.
        crisis_date_str: date of the crisis event (YYYY-MM-DD).
        weights: weights for (void_duration, early_ratio, peak_velocity, lag).

    Returns:
        Amplification velocity score as float in [0, 1].
    """
    docs = _load_corpus(public_corpus_path)
    if not docs:
        raise ValueError("Public corpus is empty.")

    crisis_date = _parse_date(crisis_date_str)

    void = _information_void_duration(docs, crisis_date)
    early = _early_non_institutional_ratio(docs, crisis_date)
    peak = _peak_velocity(docs, crisis_date)
    lag = _institutional_lag(docs, crisis_date)

    w1, w2, w3, w4 = weights
    score = w1 * void + w2 * early + w3 * peak + w4 * lag
    return float(min(max(score, 0.0), 1.0))


if __name__ == "__main__":
    cases = [
        ("notpetya", "data/notpetya/public", "2017-06-27"),
        ("pap_hack", "data/pap_hack/public", "2024-05-31"),
        ("romania", "data/romania/public", "2024-11-24"),
    ]
    for name, path, date in cases:
        score = calculate_amplification_velocity(path, date)
        print(f"Amplification Velocity [{name}]: {score:.3f}")
