"""
CIDF Dashboard
==============
Streamlit dashboard for the hardened CIDF results. It reads the machine-readable
output of ``scripts/run_methodology_audit.py`` (``results/audit_results.json``)
— it does not recompute or embed any values, and contains no Romania case.

Primary view (in order of analytical priority):
  1. evidence-aware TCI (floor / evidence-adjusted / assessed + coverage);
  2. individual IVA components;
  3. transparent case comparison.
Technical–Public Gap is shown only as a labelled diagnostic; CIDI only as an
optional exploratory synthesis. Neither is a headline metric.

Run:  streamlit run dashboard/app.py

Part of the CIDF framework — LUISS Guido Carli, 2026
Author: Giovanni Arosio
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results" / "audit_results.json"


def _fmt(x, nd=3):
    return "n/a" if x is None else f"{x:.{nd}f}"


def load_results() -> dict | None:
    if not RESULTS.exists():
        return None
    return json.loads(RESULTS.read_text(encoding="utf-8"))


st.set_page_config(page_title="CIDF — Methodology-Hardened Results",
                   layout="wide")
st.title("CIDF — Cyber-Interpretive Disruption Framework")
st.caption("Methodology-hardened results. Active cases only: NotPetya, "
           "KA-SAT / Viasat, PAP Hack. Romania is excluded (archived).")

results = load_results()
if results is None:
    st.warning(
        "No results found. Generate them first:\n\n"
        "```bash\npython scripts/run_methodology_audit.py\n```"
    )
    st.stop()

cases = results["cases"]
st.info("These results analyse a curated corpus of ~15 source-derived "
        "analytical summaries per case — not raw articles or the full public "
        "sphere. Read all scores as exploratory and corpus-bound.")

# --------------------------------------------------------------------------
# 1) Evidence-aware TCI (primary)
# --------------------------------------------------------------------------
st.header("1 · Technical Complexity Index (evidence-aware)")
st.caption("Unknown evidence is never treated as documented absence. "
           "Evidence coverage = documented / applicable components.")
tci_rows = []
for c in cases.values():
    t = c["tci"]
    tci_rows.append({
        "Case": c["label"],
        "Conservative floor": t["conservative_floor_score"],
        "Evidence-adjusted": t["evidence_adjusted_score"],
        "Assessed (incl. inferred)": t["assessed_score_including_inferred"],
        "Evidence coverage": t["evidence_coverage"],
        "Legacy float": t["legacy_calculate_tci"],
    })
tci_df = pd.DataFrame(tci_rows).set_index("Case")
st.dataframe(tci_df.style.format("{:.3f}"), use_container_width=True)

cols = st.columns(len(cases))
for col, c in zip(cols, cases.values()):
    t = c["tci"]
    with col:
        st.metric(c["label"] + " — evidence-adjusted TCI",
                  _fmt(t["evidence_adjusted_score"]),
                  help="Mean over documented components only.")
        st.progress(min(max(t["evidence_coverage"], 0.0), 1.0),
                    text=f"evidence coverage {t['evidence_coverage']:.0%}")

# --------------------------------------------------------------------------
# 2) Individual IVA components (primary)
# --------------------------------------------------------------------------
st.header("2 · Interpretive Void Analyzer — components (shown individually)")
st.caption("No forced IVA composite. Each component carries its own "
           "availability and caveats.")

for c in cases.values():
    st.subheader(c["label"])
    iva = c["iva"]
    a, b, d = st.columns(3)

    ad = iva["attribution_drift"]
    with a:
        st.markdown("**Attribution Drift**")
        if ad.get("available"):
            st.metric("score", _fmt(ad["composite_score"]))
            st.caption(f"coding coverage {ad['coding_coverage']:.0%} · "
                       f"actors {ad['components']['actor_plurality']['distinct_actors']}")
        else:
            st.warning(f"unavailable — {ad.get('reason')}")

    nf = iva["narrative_fragmentation"]
    with b:
        st.markdown("**Narrative Fragmentation** :grey[(exploratory · K-Means)]")
        if nf.get("available"):
            st.metric("score (primary k)", _fmt(nf["score"]))
            sens = pd.DataFrame(nf["sensitivity"])[["k", "score"]].set_index("k")
            st.caption("k-sensitivity:")
            st.bar_chart(sens, height=140)
        else:
            st.warning(f"unavailable — {nf.get('reason')}")

    rt = iva["response_timing_proxy"]
    with d:
        st.markdown("**Mainstream–Institutional Response Timing** "
                    ":grey[(exploratory proxy)]")
        if rt.get("available"):
            st.metric("proxy score", _fmt(rt["proxy_score"]))
            st.caption("Corpus-bound timing proxy; not real-world diffusion.")
        else:
            st.warning(f"unavailable — {rt.get('reason')}")

    with st.expander(f"{c['label']} — Technical–Public Gap (diagnostic only)"):
        tpg = iva["technical_public_gap_diagnostic"]
        comps = tpg.get("components")
        if comps:
            st.caption("Diagnostic only — excluded from every aggregate and CIDI.")
            st.json({
                "cosine_distance": comps["cosine_distance"],
                "jaccard_distance": comps["jaccard_distance"],
                "document_length_differential":
                    comps["document_length_differential"],
            })
            for w in tpg.get("warnings", []):
                st.caption("⚠ " + w)
        else:
            st.caption(tpg.get("status", "n/a"))

# --------------------------------------------------------------------------
# 3) Optional exploratory CIDI synthesis (NOT primary)
# --------------------------------------------------------------------------
st.header("3 · CIDI — optional exploratory synthesis (not the primary result)")
st.caption("Withheld whenever a required IVA component is unavailable or the "
           "TCI evidence-adjusted score is undefined.")
cidi_rows = []
for c in cases.values():
    cidi = c["cidi_exploratory"]
    cidi_rows.append({
        "Case": c["label"],
        "CIDI (exploratory)": _fmt(cidi.get("cidi")) if cidi.get("available")
        else "WITHHELD",
        "Status": "computed" if cidi.get("available") else cidi.get("reason", ""),
    })
st.dataframe(pd.DataFrame(cidi_rows).set_index("Case"), use_container_width=True)

st.divider()
st.subheader("Methodological limitations")
for n in results["notes"]:
    st.markdown(f"- {n}")
st.caption(f"Generated: {results['generated_utc']}")
