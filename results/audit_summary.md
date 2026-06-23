# CIDF Methodology Audit — Summary

_Generated: 2026-06-23T13:44:15.890092+00:00_

## Corpus validation
- corpus documents: 53, errors: 0, result: OK
- source-type distribution: {'institutional': 16, 'mainstream': 27, 'technical': 10}
- active cases: notpetya, kasat_viasat, pap_hack
- excluded: romania (archived under data/_excluded_cases)

## Evidence-aware TCI
| Case | floor | evidence-adjusted | assessed (incl. inferred) | evidence coverage | legacy |
|---|---|---|---|---|---|
| NotPetya | 0.580 | 0.662 | 0.580 | 0.80 | 0.580 |
| KA-SAT / Viasat | 0.370 | 0.550 | 0.463 | 0.60 | 0.370 |
| PAP Hack | 0.100 | 0.250 | 0.250 | 0.40 | 0.200 |

## IVA components (individual; no forced composite)
### NotPetya
- Attribution Drift: 0.114 (coding coverage 1.00; distinct actors ['russia'])
- Narrative Fragmentation (exploratory, K-Means): 0.646 | sensitivity k3=0.580, k4=0.646, k5=0.683
- Response Timing Proxy (exploratory): 0.422
- Technical–Public Gap (DIAGNOSTIC ONLY, excluded from aggregates): cosine 0.286, jaccard 0.843
- CIDI (exploratory synthesis): 0.501 [not a primary result]

### KA-SAT / Viasat
- Attribution Drift: 0.029 (coding coverage 1.00; distinct actors ['russia'])
- Narrative Fragmentation (exploratory, K-Means): 0.509 | sensitivity k3=0.524, k4=0.509, k5=0.550
- Response Timing Proxy: UNAVAILABLE — only 0 institutional/mainstream document(s) in the early window [2022-02-24 .. 2022-02-27]; need >= 2. No fallback value imputed.
- Technical–Public Gap (DIAGNOSTIC ONLY, excluded from aggregates): cosine 0.354, jaccard 0.909
- CIDI: WITHHELD — CIDI withheld: unavailable IVA component(s): response_timing_proxy. No aggregation over missing components.

### PAP Hack
- Attribution Drift: 0.020 (coding coverage 1.00; distinct actors ['russia'])
- Narrative Fragmentation (exploratory, K-Means): 0.617 | sensitivity k3=0.535, k4=0.617, k5=0.639
- Response Timing Proxy (exploratory): 0.167
- Technical–Public Gap (DIAGNOSTIC ONLY, excluded from aggregates): cosine 0.272, jaccard 0.901
- CIDI (exploratory synthesis): 0.261 [not a primary result]

## Methodological limitations
- Technical–Public Gap is an exploratory diagnostic and is excluded from every aggregate and from CIDI.
- CIDI is an optional exploratory synthesis, not the primary result.
- The corpus consists of curated, source-derived analytical summaries (~15/case), not raw articles or the full public sphere.
- No final ranked conclusion is asserted; see coverage and warnings.
