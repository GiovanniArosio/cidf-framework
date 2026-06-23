# Methodology Hardening Report

**CIDF — Cyber-Interpretive Disruption Framework**
LUISS Guido Carli, 2026 · Author: Giovanni Arosio
Branch: `methodology-hardening`

This report documents the changes made to make the framework methodologically
defensible, reproducible, transparent about uncertainty, and safe from false
quantitative claims. It records what was wrong, what was changed, and what
remains uncertain. No evidence, source, case fact, ATT&CK mapping, or numerical
output was fabricated.

---

## 0. Active scope

Active scored cases: **NotPetya**, **KA-SAT / Viasat**, **PAP Hack**.
**Romania is excluded** from all active analysis (no defensible MITRE ATT&CK
Enterprise case); its raw materials remain archived under
`data/_excluded_cases/romania/` and are never read by active runners, the
dashboard, CIDI, or scored tables.

Valid source-type vocabulary: `institutional`, `mainstream`,
`non_institutional`, `technical`. The active public corpus contains
**16 institutional, 27 mainstream, 2 technical, and 0 non_institutional**
documents (45 total).

> **Corpus nature (applies to every NLP output).** The "public corpus" is a
> curated set of **source-derived analytical summaries** (~15 per case), many
> beginning *"This article reports…"*. It is **not** raw full-text articles and
> **not** the full public sphere. Every NLP result is therefore exploratory and
> corpus-bound, and is labelled as such in code, output warnings, and below.

---

## 1. Corpus schema & validation (non-destructive)

* The active files use `doc_id` / `source_name`; the canonical schema uses
  `id` / `source`. Rather than rewrite 45 raw files, `utils/corpus_schema.py`
  now contains a **non-destructive adapter** (`normalize_raw_document`,
  `CorpusDocument.from_dict`) that accepts both conventions and preserves the
  original payload in `raw`. Unsupported/unexpected fields are *flagged*, not
  rejected.
* `scripts/validate_corpus.py` validates JSON syntax, required fields, the
  `source_type` vocabulary, and (for public documents) the presence and
  validity of attribution coding. Archived cases are ignored unless
  `--include-excluded` is passed.

## 2. Attribution Drift — keyword matching → structured coding

**Problem.** Substring matching produced false positives (`pla` ∈
"place"/"platform"/"explains"), counted `state_actor` as a separate actor,
chose a "dominant" actor via non-deterministic `list(set)[0]`, derived
confidence from the first matched keyword, and treated country mentions as
attribution.

**Fix.**
* A manual, text-grounded coding protocol (`docs/attribution_coding_protocol.md`)
  with five fields per public document, validated by machine
  (`validate_attribution_payload`) against cross-field rules.
* `iva/attribution_drift.py` reads the structured fields only — no keyword
  matching. Documents are sorted by `(date, doc_id)`; `no_claim` documents are
  excluded from actor-transition calculations; `unknown` actors are handled
  explicitly (counted as unidentified claims, never as a distinct actor);
  `state_actor` is not a category. The dominant actor is chosen by count with an
  alphabetical tie-break (deterministic).
* Coding is the single source of truth in the JSONs;
  `data/attribution_coding_audit.csv` is regenerated from them.

**Result (composite, exploratory).** NotPetya 0.114, KA-SAT 0.029,
PAP 0.020. All three cases converge on a single identified actor (`russia`), so
actor-plurality and actor-switching drift are ≈ 0; the differentiation lies in
**convergence timing** (NotPetya took longest). Previous keyword-era scores are
invalid and were not retained.

## 3. TCI — absence/“unknown” conflation → evidence-aware

**Problem.** The binary model turned every `false` into `0`, conflating
documented absence, unknown, inferred judgement, and inapplicability.

**Fix.** `tci/tci_calculator.py` keeps the legacy `calculate_tci()` float
(unchanged) and adds `analyze_tci()` returning a structured result with
`conservative_floor_score`, `evidence_adjusted_score`,
`assessed_score_including_inferred`, `evidence_coverage`, `assessment_coverage`,
per-component results, and warnings. Each component carries an `evidence_status`
(`documented_present` / `documented_absence` / `inferred` / `unknown` /
`inapplicable`), added to the active ATT&CK JSONs and grounded in repository
material:

| Component | NotPetya | KA-SAT | PAP |
|---|---|---|---|
| tactics | documented_present | documented_present | documented_present |
| techniques | documented_present | documented_present | documented_present |
| stealth | inferred | inferred | unknown |
| persistence | documented_absence | unknown | unknown |
| lateral_movement | documented_present | documented_present | unknown |

* **KA-SAT** persistence is `unknown` (per `KASAT_EVIDENCE.md`), not documented
  false; stealth is `inferred`, not directly observed.
* **PAP** persistence, lateral movement and stealth are `unknown` (incomplete
  public evidence), not documented absence.
* The binary `false` values are retained only for legacy-floor compatibility.

**Result.**

| Case | floor | evidence-adjusted | assessed (incl. inferred) | coverage | legacy |
|---|---|---|---|---|---|
| NotPetya | 0.580 | 0.662 | 0.580 | 0.80 | 0.580 |
| KA-SAT | 0.370 | 0.550 | 0.463 | 0.60 | 0.370 |
| PAP | 0.100 | 0.250 | 0.250 | 0.40 | 0.200 |

The floor equals the legacy float for NotPetya/KA-SAT and is **stricter** for
PAP, where the `0.5` stealth placeholder (now `unknown`) contributes zero.
Coverage (0.80 / 0.60 / 0.40) makes documentation quality explicit.

## 4. Narrative Fragmentation — false BERTopic claim → labelled K-Means

The module never used BERTopic. All claims now say **embedding-based K-Means
clustering**. `analyze_narrative_fragmentation()` adds an explicit small-corpus
exploratory warning, a **k = 3/4/5 sensitivity** routine (reported instead of a
single cluster count), detailed components, and a fixed random state.

## 5. Amplification Velocity → Mainstream–Institutional Response Timing Proxy

**Problem.** It lumped `mainstream` with non-institutional, normalised a "peak
velocity" by total corpus size (sample-size dependent), and imputed `0.5`
fallbacks. With **0 non_institutional documents**, it could not measure
non-institutional amplification at all.

**Fix.** Renamed and reframed (`iva/amplification_velocity.py`): explicit source
groups (`official`=institutional; `public_facing`=mainstream+non_institutional;
`technical` kept separate), within-group peak concentration (no corpus-size
denominator), and an explicit **unavailable** state with a reason when the early
window holds too few sampled documents — no imputation. It measures only the
relative timing/concentration of sampled mainstream vs institutional documents,
not real-world diffusion.

**Result.** NotPetya 0.422, PAP 0.167, **KA-SAT unavailable** (no documents in
its early window) — a correct, honest withholding.

## 6. Technical–Public Gap — declassified to a diagnostic

`iva/technical_public_gap.py` is now diagnostic-only and exports **no aggregate**
for IVA/CIDI. The misnamed "complexity differential" is renamed
**document-length differential** (mean words per document; reports raw means). A
near-ceiling Jaccard warning and the standardized-summary caveat are emitted.
On the active data the composite barely varied (≈0.48–0.49) — an artefact of
near-ceiling lexical distance, not a finding.

## 7. CIDI — de-emphasised and cleaned

`cidi/cidi_integrator.py` no longer contains hard-coded NotPetya/PAP/Romania
values and does not auto-run on defaults. `compute_cidi()` requires explicit,
validated inputs, rejects the Technical–Public Gap diagnostic as an input, and
**withholds** CIDI when any required IVA component is unavailable. Sensitivity is
exposed but explicitly labelled as algebraic weight-sensitivity, not empirical
robustness.

**Result.** NotPetya 0.501 and PAP 0.261 (exploratory); **KA-SAT withheld**
(response-timing proxy unavailable).

## 8. Reproducibility

```bash
python scripts/apply_attribution_coding.py     # (re)apply attribution coding
python scripts/generate_attribution_audit.py   # regenerate audit CSV
python scripts/validate_corpus.py              # validate corpora
python scripts/run_methodology_audit.py        # full audit -> results/
streamlit run dashboard/app.py                 # read-only dashboard
pytest                                          # test suite
```

`scripts/run_methodology_audit.py` writes `results/audit_results.json`
(machine-readable) and `results/audit_summary.md` (human-readable). It asserts
**no final ranked conclusion**.

---

## 9. Assumptions and unresolved evidence gaps

* **NotPetya persistence** is coded `documented_absence` (well-established
  destructive wiper without foothold retention); the ATT&CK mapping's Persistence
  tactic / Scheduled Task technique relate to reboot-triggering, noted inline.
* **Stealth** is treated as an analyst inference everywhere it is scored (no
  source directly measures it); coded `unknown` for PAP where even an inference
  is ungrounded.
* **`pap_pub_014`** (NASK) predates the incident and its attribution is
  pattern-based; coded on its stored wording and flagged.
* **`pap_pub_013`** names a network "tied to Belarusian and Russian
  intelligence"; coded with Russia primary and Belarus recorded in the note, so
  the single-valued actor field under-counts plurality by one (documented).
* All scores rest on ~15 curated summaries per case and are exploratory; none is
  predictive or causal, and missing evidence is never treated as evidence of
  absence.
