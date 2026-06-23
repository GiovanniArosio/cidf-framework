"""
IVA Module 4 — Mainstream–Institutional Response Timing Proxy (exploratory)
==========================================================================
FORMERLY "Amplification Velocity". That label was inaccurate: the active
corpus has **zero** non_institutional documents (16 institutional, 27
mainstream, 2 technical across 45 docs), so it cannot measure circulation of
fringe, social-media, Telegram, or otherwise non-institutional narratives. The
metric is therefore reframed and renamed.

WHAT THIS MEASURES (and only this): the relative *timing and concentration* of
**sampled mainstream vs institutional documents** within this manually
assembled corpus. It is NOT a measure of real-world information diffusion,
virality, or non-institutional amplification.

Source groups (explicit and inspectable):
  * official       : ``institutional``
  * public_facing  : ``mainstream`` + ``non_institutional``
                     (currently only ``mainstream`` is present)
  * technical      : ``technical``  — kept analytically SEPARATE; never
                     silently counted as official or public-facing.

If the early window holds insufficient sampled documents, the proxy returns an
explicit unavailable state with a reason — no imputed/fallback value.

Input:  public corpus directory (JSON) with temporal metadata + crisis date
Output: detailed diagnostics dict (preferred) OR a scalar proxy (compat)

Part of the CIDF framework — LUISS Guido Carli, 2026
Author: Giovanni Arosio
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from utils.corpus_schema import is_active_analysis  # noqa: E402

OFFICIAL_SOURCES = frozenset({"institutional"})
PUBLIC_FACING_SOURCES = frozenset({"mainstream", "non_institutional"})
TECHNICAL_SOURCES = frozenset({"technical"})

EARLY_WINDOW_DAYS = 3
MIN_EARLY_DOCS = 2          # minimum sampled docs in the early window
VOID_HORIZON_DAYS = 30.0
LAG_HORIZON_DAYS = 30.0

METHOD_NOTE = (
    "Mainstream–Institutional Response Timing Proxy. Corpus-bound and "
    "exploratory: it describes only the relative timing/concentration of the "
    "sampled mainstream vs institutional documents in this curated corpus, not "
    "real-world diffusion, virality, or non-institutional amplification. "
    "Technical sources are reported separately and excluded from the "
    "official/public-facing comparison."
)


def _load_corpus(corpus_path: str) -> list[dict]:
    """Load in-scope documents (excludes context_preincident material)."""
    docs = []
    path = Path(corpus_path)
    for file in sorted(path.glob("*.json")):
        with open(file, "r", encoding="utf-8") as f:
            doc = json.load(f)
            if not is_active_analysis(doc):
                continue
            if "date" in doc and "source_type" in doc:
                docs.append(doc)
    return docs


def _parse_date(date_str: str) -> datetime:
    for fmt in ("%Y-%m-%d", "%Y-%m", "%Y"):
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    raise ValueError(f"Cannot parse date: {date_str}")


def _group(source_type: str) -> str:
    if source_type in OFFICIAL_SOURCES:
        return "official"
    if source_type in PUBLIC_FACING_SOURCES:
        return "public_facing"
    if source_type in TECHNICAL_SOURCES:
        return "technical"
    return "other"


def _first_date(dated: list[datetime]) -> datetime | None:
    return min(dated) if dated else None


def analyze_response_timing(
    public_corpus_path: str,
    crisis_date_str: str,
) -> dict[str, Any]:
    """Detailed, diagnostics-first response-timing analysis.

    Always returns the raw diagnostics (group counts, first dates, early-window
    composition, peak publication day). Returns ``available=False`` with a
    reason when the proxy cannot be computed (no early-window evidence, or no
    institutional/mainstream documents to compare).
    """
    raw_docs = _load_corpus(public_corpus_path)
    crisis_date = _parse_date(crisis_date_str)
    warnings: list[str] = [METHOD_NOTE]

    by_group: dict[str, list[datetime]] = defaultdict(list)
    by_source_type: dict[str, int] = defaultdict(int)
    early = {"official": 0, "public_facing": 0, "technical": 0, "other": 0}
    early_cutoff = crisis_date + timedelta(days=EARLY_WINDOW_DAYS)
    daily_public: dict[str, int] = defaultdict(int)

    for doc in raw_docs:
        st = doc.get("source_type", "")
        by_source_type[st] += 1
        try:
            d = _parse_date(doc["date"])
        except ValueError:
            warnings.append(f"unparseable date skipped: {doc.get('date')!r}")
            continue
        g = _group(st)
        by_group[g].append(d)
        if crisis_date <= d <= early_cutoff:
            early[g] += 1
        if g == "public_facing":
            daily_public[d.strftime("%Y-%m-%d")] += 1

    first_official = _first_date(by_group.get("official", []))
    first_public = _first_date(by_group.get("public_facing", []))
    first_technical = _first_date(by_group.get("technical", []))

    # Peak concentration — within-group (NOT normalized by total corpus size).
    n_public = len(by_group.get("public_facing", []))
    peak_day, peak_count = (None, 0)
    if daily_public:
        peak_day = max(daily_public, key=lambda k: (daily_public[k], k))
        peak_count = daily_public[peak_day]
    peak_concentration = (peak_count / n_public) if n_public else None

    diagnostics = {
        "crisis_date": crisis_date_str,
        "early_window_days": EARLY_WINDOW_DAYS,
        "source_type_counts": dict(sorted(by_source_type.items())),
        "group_counts": {g: len(v) for g, v in sorted(by_group.items())},
        "non_institutional_count": by_source_type.get("non_institutional", 0),
        "first_official_date": first_official.strftime("%Y-%m-%d") if first_official else None,
        "first_public_facing_date": first_public.strftime("%Y-%m-%d") if first_public else None,
        "first_technical_date": first_technical.strftime("%Y-%m-%d") if first_technical else None,
        "early_window_composition": dict(early),
        "peak_public_day": peak_day,
        "peak_public_count": peak_count,
        "peak_public_concentration": peak_concentration,
    }

    # ---- availability conditions (no imputation) ----
    if first_official is None or first_public is None:
        return {
            "available": False,
            "reason": "need at least one institutional and one mainstream/"
                      "public-facing document to compare timing.",
            "method": "mainstream_institutional_response_timing_proxy",
            "proxy_score": None,
            "diagnostics": diagnostics,
            "warnings": warnings,
        }

    early_official = early["official"]
    early_public = early["public_facing"]
    early_total = early_official + early_public
    if early_total < MIN_EARLY_DOCS:
        return {
            "available": False,
            "reason": (
                f"only {early_total} institutional/mainstream document(s) in the "
                f"early window [{crisis_date_str} .. "
                f"{early_cutoff.strftime('%Y-%m-%d')}]; need >= {MIN_EARLY_DOCS}. "
                "No fallback value imputed."
            ),
            "method": "mainstream_institutional_response_timing_proxy",
            "proxy_score": None,
            "diagnostics": diagnostics,
            "warnings": warnings,
        }

    # ---- components (each in [0, 1]) ----
    void_days = max((first_official - crisis_date).days, 0)
    void_duration = min(void_days / VOID_HORIZON_DAYS, 1.0)

    early_public_share = early_public / early_total

    lag_days = max((first_official - first_public).days, 0)
    institutional_lag = min(lag_days / LAG_HORIZON_DAYS, 1.0)

    proxy_score = float((void_duration + early_public_share + institutional_lag) / 3.0)

    components = {
        "void_duration": {
            "score": float(void_duration), "raw_days": void_days,
            "horizon_days": VOID_HORIZON_DAYS,
            "definition": "days from crisis date to first sampled institutional doc",
        },
        "early_public_share": {
            "score": float(early_public_share),
            "early_public_facing": early_public, "early_official": early_official,
            "definition": "share of early-window docs that are mainstream/"
                          "public-facing vs institutional",
        },
        "institutional_lag": {
            "score": float(institutional_lag), "raw_days": lag_days,
            "horizon_days": LAG_HORIZON_DAYS,
            "definition": "days between first sampled mainstream and first "
                          "institutional doc",
        },
    }

    if diagnostics["non_institutional_count"] == 0:
        warnings.append(
            "0 non_institutional documents in corpus; the public-facing group "
            "is entirely mainstream — no fringe/social/unverified layer exists "
            "to measure."
        )

    return {
        "available": True,
        "method": "mainstream_institutional_response_timing_proxy",
        "proxy_score": proxy_score,
        "components": components,
        "diagnostics": diagnostics,
        "warnings": warnings,
    }


def calculate_response_timing_proxy(
    public_corpus_path: str,
    crisis_date_str: str,
) -> float:
    """Backward-compatible scalar proxy. Raises if the proxy is unavailable
    (no early-window evidence) — never imputes a fallback value."""
    res = analyze_response_timing(public_corpus_path, crisis_date_str)
    if not res["available"]:
        raise ValueError(f"Response timing proxy unavailable: {res['reason']}")
    return res["proxy_score"]


# Deprecated legacy name. The "amplification velocity" framing is inaccurate for
# this corpus; retained only so any external caller does not break.
def calculate_amplification_velocity(public_corpus_path: str, crisis_date_str: str,
                                     *_, **__) -> float:
    """DEPRECATED alias for :func:`calculate_response_timing_proxy`."""
    return calculate_response_timing_proxy(public_corpus_path, crisis_date_str)


if __name__ == "__main__":
    cases = [
        ("notpetya", "data/notpetya/public", "2017-06-27"),
        ("kasat_viasat", "data/kasat_viasat/public", "2022-02-24"),
        ("pap_hack", "data/pap_hack/public", "2024-05-31"),
    ]
    for name, path, date in cases:
        res = analyze_response_timing(path, date)
        if res["available"]:
            print(f"Response Timing Proxy [{name}] (exploratory): "
                  f"{res['proxy_score']:.3f}")
        else:
            print(f"Response Timing Proxy [{name}]: UNAVAILABLE — {res['reason']}")
