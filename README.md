# CIDF — Cyber-Interpretive Disruption Framework

> A computational framework for measuring the relationship between technical complexity of cyber-attacks and communicative disruption in the European public sphere.

**Institution:** LUISS Guido Carli — Department of Political Science  
**Thesis:** The Interpretive Void: Technical Complexity, Crisis Communication and Narrative Competition in European Cyber Crises  
**Supervisor:** Prof. Donatella Selva  
**Author:** Giovanni Arosio  
**Academic Year:** 2025/2026  

---

## Academic Context

This framework was developed as the empirical component of a Master's thesis in International Relations / Security Studies. The research investigates how the technical complexity of cyber-attacks shapes crisis communication processes and narrative competition within the European public sphere — generating what the thesis terms the "interpretive void."

The CIDF operationalizes this relationship through three integrated instruments:

---

## Framework Architecture

![CIDF Architecture — Figure 1](docs/figures/Figure_1___CIDF_Architecture.png)

*Figure 1 — CIDF Architecture: from corpus ingestion to empirical output.*

---

## Components

### TCI — Technical Complexity Index (evidence-aware)
Measures the operational sophistication of cyber incidents using the MITRE ATT&CK framework across five components (tactics, techniques, stealth, persistence, lateral movement). The model is **evidence-aware**: each component carries a status (`documented_present`, `documented_absence`, `inferred`, `unknown`, `inapplicable`), and the output distinguishes a conservative floor, an evidence-adjusted score, an assessed score including inference, and the underlying evidence coverage. Unknown evidence is never treated as documented absence. The legacy scalar is preserved for compatibility.

### IVA — Interpretive Void Analyzer
A set of NLP instruments measuring communicative disruption — reported **individually**, not as a single forced composite:
- **Attribution Drift** — instability of responsibility claims over time, from a manual, text-grounded **structured coding** protocol (no keyword/LLM extraction). Uncertain/unknown claims appear explicitly in the temporal sequence (so early unresolved attribution counts); convergence requires three consecutive documents naming the same specific actor.
- **Narrative Fragmentation** — diversity of competing narratives via **embedding-based K-Means clustering** of sentence embeddings (not BERTopic), reported with k = 3/4/5 sensitivity. Exploratory.
- **Mainstream–Institutional Response Timing Proxy** — relative timing/concentration of sampled mainstream vs institutional documents (formerly "Amplification Velocity"). Exploratory; corpus-bound; returns an explicit unavailable state when early-window evidence is insufficient.
- **Technical–Public Gap** — semantic/lexical/length distance between technical and public summaries. **Diagnostic only** — excluded from every aggregate.

### CIDI — Cyber-Interpretive Disruption Index (optional, exploratory)
An **optional, exploratory** synthesis (CIDI = 0.40 × TCI + 0.60 × IVA), **not** the primary result. It is computed only when valid inputs exist and is withheld when any required IVA component is unavailable. The asymmetric weighting is a modelling choice reflecting the thesis's argument that the interpretive dimension carries greater analytical weight — not an empirical finding.

> **Primary result architecture:** (1) evidence-aware TCI, (2) individual IVA components, (3) transparent case comparison, (4) optional exploratory CIDI as a supplementary synthesis only.

---

## Case Studies

| Case | Date | Notes |
|------|------|-------|
| NotPetya | June 2017 | Comparatively well documented; highest TCI evidence coverage |
| KA-SAT / Viasat | February 2022 | Documented wiper; persistence unknown, stealth inferred |
| PAP Hack | May 2024 | Incomplete public technical evidence; low TCI evidence coverage |

> Romania has been **removed** from the active scored dataset (not a defensible MITRE ATT&CK Enterprise case). Its raw materials are archived under `data/_excluded_cases/romania/` as a methodological boundary case and are never used in active analysis.

> **Pre-incident context exclusion.** `pap_pub_014` (dated 2024-05-15, before the 2024-05-31 PAP event) is marked `"analysis_role": "context_preincident"` and excluded from every event-level metric, leaving **14 in-scope** analytical documents for PAP (NotPetya and KA-SAT have 15 each). It remains visible in the audit CSV as retained context.

---

## Data Sources

All corpus documents are drawn exclusively from publicly available sources. No proprietary or scraped data is included. Source-type vocabulary: `institutional`, `mainstream`, `non_institutional`, `technical`. The active public corpus contains 16 institutional, 27 mainstream, 2 technical, and **0 non_institutional** documents (45 total).

> **Important limitation.** The "public corpus" consists of curated, **source-derived analytical summaries** (~15 per case), not raw full-text articles and not the full public sphere. All NLP outputs (Attribution Drift, Narrative Fragmentation, Technical–Public Gap, Response Timing) are therefore **exploratory and corpus-bound**, and must not be read as a census of public discourse, viral amplification, or non-institutional narrative circulation.

---

## Tech Stack

- Python 3.10+
- `sentence-transformers` — semantic embeddings (all-MiniLM-L6-v2)
- `scikit-learn` + `scipy` — K-Means clustering and metrics (Narrative Fragmentation)
- `streamlit` — read-only results dashboard
- `pandas`, `numpy` — data processing
- `pytest` — test suite

> Attribution is coded **manually** from the stored corpus text (see `docs/attribution_coding_protocol.md`) — no LLM extraction is used. Narrative Fragmentation uses embedding-based K-Means, **not** BERTopic.

---

## Repository Structure
cidf-framework/
├── data/           # Corpora (JSON); active cases + archived _excluded_cases/romania
├── utils/          # Canonical corpus schema + non-destructive adapter
├── tci/            # Technical Complexity Index (evidence-aware)
├── iva/            # Interpretive Void Analyzer modules (reported individually)
├── cidi/           # Optional exploratory CIDI synthesis
├── dashboard/      # Streamlit dashboard (reads results/)
├── scripts/        # Validation, attribution coding, audit runner
├── results/        # Machine- and human-readable audit output
├── docs/           # Methodology report + attribution coding protocol
└── tests/          # Test suite

---

## Reproducibility

```bash
python scripts/validate_corpus.py            # validate active corpora
python scripts/apply_attribution_coding.py   # (re)apply attribution coding to JSONs
python scripts/generate_attribution_audit.py # regenerate data/attribution_coding_audit.csv
python scripts/run_methodology_audit.py      # full audit -> results/audit_results.json + summary
streamlit run dashboard/app.py               # read-only dashboard over results/
pytest                                        # run the test suite
```

See `docs/methodology_hardening_report.md` for what changed and why, and
`docs/attribution_coding_protocol.md` for the attribution coding rules.

---

## Citation

If you use this framework in your research, please cite:

> Arosio, G. (2026). *The Interpretive Void: Technical Complexity, Crisis Communication and Narrative Competition in European Cyber Crises*. Master's Thesis, LUISS Guido Carli.

---

*This project is released under the MIT License for academic and research purposes.*
