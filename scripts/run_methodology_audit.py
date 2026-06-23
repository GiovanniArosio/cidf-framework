#!/usr/bin/env python3
"""
Reproducible methodology audit runner
=====================================
Single entry point that runs the hardened CIDF pipeline over the three active
cases (NotPetya, KA-SAT/Viasat, PAP Hack) and writes both machine-readable and
human-readable results to ``results/``.

It deliberately:
  * validates all active corpora first;
  * runs evidence-aware TCI (floor / evidence-adjusted / assessed + coverage);
  * runs Attribution Drift ONLY when attribution coding is complete;
  * runs Narrative Fragmentation WITH the k = 3/4/5 sensitivity routine;
  * runs the Mainstream–Institutional Response Timing Proxy with availability
    diagnostics (no imputation);
  * runs Technical–Public Gap ONLY as an exploratory diagnostic (never in an
    aggregate);
  * computes CIDI ONLY when its prerequisites exist, and otherwise records an
    explicit withheld state;
  * does NOT fabricate a final ranked conclusion.

Romania is excluded from the active run (archived under data/_excluded_cases).

Usage:
    python scripts/run_methodology_audit.py
    python scripts/run_methodology_audit.py --skip-embeddings   # no model needed

Part of the CIDF framework — LUISS Guido Carli, 2026
Author: Giovanni Arosio
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Prefer offline model load; the model is expected to be cached.
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tci.tci_calculator import analyze_tci, calculate_tci  # noqa: E402
from iva.attribution_drift import analyze_attribution_drift  # noqa: E402
from iva.amplification_velocity import analyze_response_timing  # noqa: E402
from cidi.cidi_integrator import compute_cidi  # noqa: E402
from scripts.validate_corpus import discover, build_summary  # noqa: E402

ACTIVE_CASES = {
    "notpetya": {"label": "NotPetya", "crisis_date": "2017-06-27"},
    "kasat_viasat": {"label": "KA-SAT / Viasat", "crisis_date": "2022-02-24"},
    "pap_hack": {"label": "PAP Hack", "crisis_date": "2024-05-31"},
}


def _attck_path(case: str) -> Path:
    mapping = {
        "notpetya": "data/notpetya/technical/notpetya_attck.json",
        "kasat_viasat": "data/kasat_viasat/technical/kasat_attck.json",
        "pap_hack": "data/pap_hack/technical/pap_attck.json",
    }
    return ROOT / mapping[case]


def run_validation() -> dict:
    reports = discover(ROOT / "data", include_excluded=False)
    summary = build_summary(reports)
    errors = [
        {"path": r.path, "errors": r.errors}
        for r in reports if r.is_corpus_doc and r.errors
    ]
    return {"summary": summary, "errors": errors}


def run_tci(case: str) -> dict:
    incident = json.loads(_attck_path(case).read_text(encoding="utf-8"))
    res = analyze_tci(incident)
    res["legacy_calculate_tci"] = calculate_tci(incident)
    return res


def run_attribution(case: str) -> dict:
    return analyze_attribution_drift(str(ROOT / "data" / case / "public"))


def run_narrative(case: str, skip_embeddings: bool) -> dict:
    if skip_embeddings:
        return {"available": False, "reason": "skipped (--skip-embeddings)",
                "method": "embedding-based K-Means clustering"}
    try:
        from iva.narrative_fragmentation import analyze_narrative_fragmentation
        return analyze_narrative_fragmentation(str(ROOT / "data" / case / "public"))
    except Exception as exc:  # noqa: BLE001 — degrade gracefully, do not crash
        return {"available": False, "reason": f"embedding model error: {exc}",
                "method": "embedding-based K-Means clustering"}


def run_response_timing(case: str) -> dict:
    crisis = ACTIVE_CASES[case]["crisis_date"]
    return analyze_response_timing(str(ROOT / "data" / case / "public"), crisis)


def run_tpg(case: str, skip_embeddings: bool) -> dict:
    if skip_embeddings:
        return {"status": "skipped (--skip-embeddings)", "included_in_aggregate": False}
    try:
        from iva.technical_public_gap import diagnose_technical_public_gap
        return diagnose_technical_public_gap(
            str(ROOT / "data" / case / "technical"),
            str(ROOT / "data" / case / "public"),
        )
    except Exception as exc:  # noqa: BLE001
        return {"status": f"diagnostic error: {exc}", "included_in_aggregate": False}


def maybe_cidi(tci: dict, attribution: dict, narrative: dict, response: dict) -> dict:
    """Compute CIDI only when prerequisites exist; otherwise withhold."""
    tci_value = tci.get("evidence_adjusted_score")
    if tci_value is None:
        return {"available": False,
                "reason": "CIDI withheld: TCI evidence-adjusted score undefined "
                          "(no documented components).",
                "cidi": None}

    iva_components = {
        "attribution_drift": (
            attribution.get("composite_score") if attribution.get("available") else None
        ),
        "narrative_fragmentation": (
            narrative.get("score") if narrative.get("available") else None
        ),
        "response_timing_proxy": (
            response.get("proxy_score") if response.get("available") else None
        ),
    }
    return compute_cidi(
        tci_value,
        iva_components,
        tci_evidence_coverage=tci.get("evidence_coverage"),
        tci_score_kind="evidence_adjusted",
    )


def build_results(skip_embeddings: bool) -> dict:
    validation = run_validation()
    cases = {}
    for case, meta in ACTIVE_CASES.items():
        tci = run_tci(case)
        attribution = run_attribution(case)
        narrative = run_narrative(case, skip_embeddings)
        response = run_response_timing(case)
        tpg = run_tpg(case, skip_embeddings)
        cidi = maybe_cidi(tci, attribution, narrative, response)
        cases[case] = {
            "label": meta["label"],
            "crisis_date": meta["crisis_date"],
            "tci": tci,
            "iva": {
                "attribution_drift": attribution,
                "narrative_fragmentation": narrative,
                "response_timing_proxy": response,
                "technical_public_gap_diagnostic": tpg,
            },
            "cidi_exploratory": cidi,
        }

    return {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "active_cases": list(ACTIVE_CASES),
        "excluded_cases": ["romania (archived under data/_excluded_cases)"],
        "validation": validation,
        "cases": cases,
        "notes": [
            "Technical–Public Gap is an exploratory diagnostic and is excluded "
            "from every aggregate and from CIDI.",
            "CIDI is an optional exploratory synthesis, not the primary result.",
            "The corpus consists of curated, source-derived analytical summaries "
            "(~15/case), not raw articles or the full public sphere.",
            "No final ranked conclusion is asserted; see coverage and warnings.",
        ],
    }


def _fmt(x, nd=3):
    return "n/a" if x is None else f"{x:.{nd}f}"


def write_summary(results: dict, out_path: Path) -> None:
    L = []
    L.append("# CIDF Methodology Audit — Summary\n")
    L.append(f"_Generated: {results['generated_utc']}_\n")
    v = results["validation"]["summary"]
    L.append("## Corpus validation")
    L.append(f"- corpus documents: {v['corpus_documents']}, "
             f"errors: {v['documents_with_errors']}, "
             f"result: {'OK' if v['ok'] else 'ERRORS'}")
    L.append(f"- source-type distribution: {v['source_type_distribution']}")
    L.append(f"- active cases: {', '.join(results['active_cases'])}")
    L.append(f"- excluded: {', '.join(results['excluded_cases'])}\n")

    L.append("## Evidence-aware TCI")
    L.append("| Case | floor | evidence-adjusted | assessed (incl. inferred) | "
             "evidence coverage | legacy |")
    L.append("|---|---|---|---|---|---|")
    for c in results["cases"].values():
        t = c["tci"]
        L.append(f"| {c['label']} | {_fmt(t['conservative_floor_score'])} | "
                 f"{_fmt(t['evidence_adjusted_score'])} | "
                 f"{_fmt(t['assessed_score_including_inferred'])} | "
                 f"{_fmt(t['evidence_coverage'],2)} | "
                 f"{_fmt(t['legacy_calculate_tci'])} |")
    L.append("")

    L.append("## IVA components (individual; no forced composite)")
    for c in results["cases"].values():
        L.append(f"### {c['label']}")
        ad = c["iva"]["attribution_drift"]
        if ad.get("available"):
            conv = ad["components"]["convergence_delay"]
            conv_str = (f"converged @ {conv['convergence_date']} "
                        f"(actor {conv['converged_actor']}, "
                        f"{conv['raw_days']}d)") if conv["converged"] else "NOT CONVERGED"
            seq = " → ".join(
                f"{x['actor']}" for x in ad["attribution_related_sequence"])
            L.append(
                f"- Attribution Drift: {_fmt(ad['composite_score'])} "
                f"(in-scope docs {ad['in_scope_document_count']}, "
                f"context excluded {ad['excluded_context_count']}, "
                f"coding coverage {_fmt(ad['coding_coverage'],2)})")
            L.append(f"    - distinct identified actors: "
                     f"{ad['components']['actor_plurality']['distinct_actors']}; "
                     f"unresolved claims: {ad['unresolved_claim_count']} "
                     f"({_fmt(ad['unresolved_claim_proportion'],2)})")
            L.append(f"    - convergence: {conv_str}")
            L.append(f"    - attribution-related sequence: {seq}")
        else:
            L.append(f"- Attribution Drift: UNAVAILABLE — {ad.get('reason')}")
        nf = c["iva"]["narrative_fragmentation"]
        if nf.get("available"):
            sens = ", ".join(f"k{s['k']}={s['score']:.3f}" for s in nf["sensitivity"])
            L.append(f"- Narrative Fragmentation (exploratory, K-Means): "
                     f"{_fmt(nf['score'])} | sensitivity {sens}")
        else:
            L.append(f"- Narrative Fragmentation: UNAVAILABLE — {nf.get('reason')}")
        rt = c["iva"]["response_timing_proxy"]
        if rt.get("available"):
            L.append(f"- Response Timing Proxy (exploratory): {_fmt(rt['proxy_score'])}")
        else:
            L.append(f"- Response Timing Proxy: UNAVAILABLE — {rt.get('reason')}")
        tpg = c["iva"]["technical_public_gap_diagnostic"]
        comps = tpg.get("components")
        if comps:
            L.append(f"- Technical–Public Gap (DIAGNOSTIC ONLY, excluded from "
                     f"aggregates): cosine {_fmt(comps['cosine_distance'])}, "
                     f"jaccard {_fmt(comps['jaccard_distance'])}")
        else:
            L.append(f"- Technical–Public Gap (DIAGNOSTIC ONLY): {tpg.get('status')}")
        cidi = c["cidi_exploratory"]
        if cidi.get("available"):
            L.append(f"- CIDI (exploratory synthesis): {_fmt(cidi['cidi'])} "
                     f"[not a primary result]")
        else:
            L.append(f"- CIDI: WITHHELD — {cidi.get('reason')}")
        L.append("")

    L.append("## Methodological limitations")
    for n in results["notes"]:
        L.append(f"- {n}")
    L.append("")
    out_path.write_text("\n".join(L), encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description="Run the CIDF methodology audit.")
    ap.add_argument("--skip-embeddings", action="store_true",
                    help="Skip embedding-based modules (Narrative Fragmentation, "
                         "Technical–Public Gap) when the model is unavailable.")
    ap.add_argument("--results-dir", default=str(ROOT / "results"), type=Path)
    args = ap.parse_args()

    results = build_results(skip_embeddings=args.skip_embeddings)

    results_dir = Path(args.results_dir)
    results_dir.mkdir(parents=True, exist_ok=True)
    (results_dir / "audit_results.json").write_text(
        json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    write_summary(results, results_dir / "audit_summary.md")

    v = results["validation"]["summary"]
    print("CIDF methodology audit complete.")
    print(f"  corpus validation: {'OK' if v['ok'] else 'ERRORS'} "
          f"({v['corpus_documents']} docs)")
    print(f"  results: {results_dir / 'audit_results.json'}")
    print(f"  summary: {results_dir / 'audit_summary.md'}")
    return 0 if v["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
