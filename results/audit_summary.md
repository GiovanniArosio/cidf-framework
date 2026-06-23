# CIDF Methodology Audit — Summary

_Generated: 2026-06-23T14:19:08.954204+00:00_

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
- Attribution Drift: 0.291 (in-scope docs 15, context excluded 0, coding coverage 1.00)
    - distinct identified actors: ['russia']; unresolved claims: 1 (0.14)
    - convergence: converged @ 2018-02-15 (actor russia, 233d)
    - attribution-related sequence: russia → russia → russia → russia → russia → unknown → russia
- Narrative Fragmentation (exploratory, K-Means): 0.646 | sensitivity k3=0.580, k4=0.646, k5=0.683
- Response Timing Proxy (exploratory): 0.422
- Technical–Public Gap (DIAGNOSTIC ONLY, never a CIDI/IVA input): cosine 0.286, jaccard 0.843
- IVC_core (0.5·AttrDrift + 0.5·NarrFrag): 0.468

### KA-SAT / Viasat
- Attribution Drift: 0.174 (in-scope docs 15, context excluded 0, coding coverage 1.00)
    - distinct identified actors: ['russia']; unresolved claims: 2 (0.17)
    - convergence: converged @ 2022-05-09 (actor russia, 59d)
    - attribution-related sequence: unknown → unknown → russia → russia → russia → russia → russia → russia → russia → russia → russia → russia
- Narrative Fragmentation (exploratory, K-Means): 0.509 | sensitivity k3=0.524, k4=0.509, k5=0.550
- Response Timing Proxy: UNAVAILABLE — only 0 institutional/mainstream document(s) in the early window [2022-02-24 .. 2022-02-27]; need >= 2. No fallback value imputed.
- Technical–Public Gap (DIAGNOSTIC ONLY, never a CIDI/IVA input): cosine 0.354, jaccard 0.909
- IVC_core (0.5·AttrDrift + 0.5·NarrFrag): 0.342

### PAP Hack
- Attribution Drift: 0.110 (in-scope docs 14, context excluded 1, coding coverage 1.00)
    - distinct identified actors: ['russia']; unresolved claims: 1 (0.10)
    - convergence: converged @ 2024-06-01 (actor russia, 1d)
    - attribution-related sequence: russia → unknown → russia → russia → russia → russia → russia → russia → russia → russia
- Narrative Fragmentation (exploratory, K-Means): 0.595 | sensitivity k3=0.515, k4=0.595, k5=0.627
- Response Timing Proxy (exploratory): 0.167
- Technical–Public Gap (DIAGNOSTIC ONLY, never a CIDI/IVA input): cosine 0.272, jaccard 0.898
- IVC_core (0.5·AttrDrift + 0.5·NarrFrag): 0.353

## CIDI Core scenarios (exploratory synthesis — not a primary inferential result)
TCI input = evidence-adjusted score; evidence coverage is a separate caveat, never folded in.
| Case | core_neutral (0.5/0.5) | core_interpretive (0.4/0.6) | core_technical (0.6/0.4) | (coverage caveat) |
|---|---|---|---|---|
| NotPetya | 0.565 | 0.546 | 0.585 | cov 0.80 |
| KA-SAT / Viasat | 0.446 | 0.425 | 0.467 | cov 0.60 |
| PAP Hack | 0.301 | 0.312 | 0.291 | cov 0.40 |

## CIDI Extended scenarios (supplementary; includes Response Timing Proxy)
Extended scores are NOT comparable across cases when timing data is unavailable.
| Case | extended_neutral | extended_interpretive | extended_technical | status |
|---|---|---|---|---|
| NotPetya | 0.561 | 0.540 | 0.581 | available |
| KA-SAT / Viasat | — | — | — | UNAVAILABLE: unavailable component(s): response_timing_proxy (not imputed). |
| PAP Hack | 0.283 | 0.289 | 0.276 | available |

## Ranking robustness
### Core scenarios
- cases included: KA-SAT / Viasat, NotPetya, PAP Hack
- core_neutral: NotPetya > KA-SAT / Viasat > PAP Hack
- core_interpretive_prioritized: NotPetya > KA-SAT / Viasat > PAP Hack
- core_technical_prioritized: NotPetya > KA-SAT / Viasat > PAP Hack
- ranking stable across scenarios: **YES**
- Descriptive ordering across weighting scenarios for the cases with available scores only. No causal or out-of-sample claim is made.

### Extended scenarios (available cases only)
- cases included: NotPetya, PAP Hack
- extended_neutral: NotPetya > PAP Hack
- extended_interpretive_prioritized: NotPetya > PAP Hack
- extended_technical_prioritized: NotPetya > PAP Hack
- ranking stable across scenarios: **YES**
- Descriptive ordering across weighting scenarios for the cases with available scores only. No causal or out-of-sample claim is made.

## Methodological limitations
- CIDI is a scenario-based exploratory synthesis, not a primary inferential result; no unique validated weighting is claimed.
- Technical–Public Gap is an exploratory diagnostic, excluded from every aggregate and from every CIDI formula.
- Response Timing Proxy is unavailable for KA-SAT and is never imputed; Extended CIDI is therefore unavailable for KA-SAT.
- Evidence coverage is shown alongside scores but never folded into them.
- The corpus consists of curated, source-derived analytical summaries (~14-15/case), not raw articles or the full public sphere.
- All outputs are exploratory, corpus-bound and non-causal; no final ranked conclusion is asserted beyond the three available cases.
