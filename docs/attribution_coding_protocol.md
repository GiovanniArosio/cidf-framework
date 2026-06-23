# Attribution Coding Protocol

**CIDF — Cyber-Interpretive Disruption Framework**
LUISS Guido Carli, 2026 · Author: Giovanni Arosio

This protocol replaces the previous keyword/substring approach to attribution
detection, which produced false positives (e.g. the substring `pla` matching
"place", "platform", "explains") and conflated *mentions* of a country with
*attribution of responsibility*. Attribution is now a **manual, transparent,
text-grounded coding** stored as structured metadata on each active public
corpus document, and audited in `data/attribution_coding_audit.csv`.

---

## 1. Scope and a critical data limitation

The "public corpus" is **not** a collection of raw, full-text news articles.
Each entry is a **curated, source-derived analytical summary** — many begin
with formulaic constructions such as *"This article reports…"*,
*"This BBC report covers…"*, *"This exclusive Reuters article…"*. Coding
therefore describes **what the stored summary represents**, not the full
original article (which is not reproduced) and not the broader public sphere.

Consequently:

* All attribution coding reflects only the wording in the stored summary text.
* The coding is a corpus-bound, exploratory measurement, not a census of public
  discourse.
* The active public corpus contains **0 `non_institutional` documents**
  (16 institutional, 27 mainstream, 2 technical across 45 documents), so the
  corpus cannot characterise fringe, social-media, or unverified narrative
  circulation.

## 2. The five coded fields

Every active public corpus document carries these fields:

```json
"attribution_state":      "attributed | uncertain | no_claim | denial",
"attribution_actor":      "russia | china | belarus | iran | north_korea | criminal | other_state | unknown | none",
"attribution_confidence": "high | medium | low | none",
"attribution_basis":      "official_attribution | technical_assessment | investigative_reporting | public_speculation | no_claim",
"attribution_coding_note":"brief explanation grounded in the stored corpus text"
```

## 3. Coding rules

### State
* **`no_claim`** — the stored text contains no attribution attempt (no actor is
  blamed). Damage descriptions, malware-nature analysis, mitigation advice, and
  victim clarifications that name no perpetrator are `no_claim`.
* **`uncertain`** — the text explicitly signals uncertainty, an open
  investigation, unresolved responsibility, or speculation (e.g. "unknown
  origin", "uncertainty over the perpetrators").
* **`attributed`** — the text assigns responsibility to an actor with a stated
  basis (a hedge such as "probably"/"likely" lowers `attribution_confidence`
  but does not by itself demote the state to `uncertain`).
* **`denial`** — the text contains a denial or rebuttal of responsibility by an
  accused actor. (No active document is coded `denial`; the category is retained
  for completeness and is exercised by the test suite.)

### Actor
* **`none`** — only when state is `no_claim`.
* **`unknown`** — only when there *is* an attribution-related claim but no actor
  can be identified from the stored text (e.g. a generic "state-attributed"
  reference, or "of unknown origin").
* A specific actor is used only when the stored text names it as responsible.

### What must NOT drive coding
Per the project's hardening constraints, an actor is **never** coded from:

* source reputation (who published the summary);
* background or general knowledge of the case;
* the original article that may not be fully reproduced in the summary;
* a country appearing merely in **geopolitical context** (e.g. "coincided with
  Russia's invasion", "geopolitically motivated") — timing/motive context is
  **not** attribution.

### Coding note
Every document has a concise note that quotes or paraphrases the **stored text**
wording that justifies the coding.

## 4. Cross-field validation (machine-enforced)

`utils/corpus_schema.validate_attribution_payload` rejects malformed coding:

* `no_claim` ⇒ actor `none`, confidence `none`, basis `no_claim`.
* actor `none` is invalid unless state is `no_claim`.
* basis `no_claim` is invalid unless state is `no_claim`.
* actor `unknown` cannot co-occur with state `no_claim`.
* the coding note must be a non-empty string.

`scripts/validate_corpus.py` reports any public document missing or failing
attribution coding.

## 5. Multi-actor and edge cases

* **Co-attribution** (`pap_pub_013`: a network "tied to Belarusian and Russian
  intelligence") is coded with the **primary** actor (`russia`) and the
  secondary actor recorded in the coding note. The single-valued actor field
  therefore *under-counts* actor plurality by design; this is documented and
  visible in the audit CSV.
* **Pre-incident context** (`pap_pub_014`, dated before the incident) is coded
  on its own stored wording; the audit flags that this document predates the
  event and that its attribution is pattern-based.

## 6. Reproducing the coding

```bash
python scripts/apply_attribution_coding.py        # write coding into JSONs
python scripts/apply_attribution_coding.py --check # verify, no writes
python scripts/generate_attribution_audit.py       # regenerate the audit CSV
python scripts/validate_corpus.py                  # validate the corpora
```

`scripts/apply_attribution_coding.py` holds the canonical coding map (the single
source of truth) and validates every entry against the rules above before
writing. The CSV is regenerated **from the JSONs**, so it cannot drift from the
data.

## 7. How the coding feeds Attribution Drift

`iva/attribution_drift.py` reads these structured fields (no keyword matching).
Documents are sorted deterministically by `(date, doc_id)`. `no_claim` documents
are **excluded** from actor-transition calculations; `unknown` actors are handled
explicitly (tracked as unidentified claims, never counted as a distinct actor);
`state_actor` is **not** a separate actor category. See that module's docstring
for the component definitions (actor plurality, temporal instability,
convergence delay, confidence dispersion) and their exploratory caveats.
