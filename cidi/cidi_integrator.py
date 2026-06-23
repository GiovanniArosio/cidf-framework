"""
CIDI — Cyber-Interpretive Disruption Index (OPTIONAL EXPLORATORY SYNTHESIS)
==========================================================================
Integrates a TCI score and the available IVA components into a single
composite. CIDI is **not** the thesis's primary empirical result: the primary
outputs are evidence-aware TCI, the individual IVA components, and a transparent
case comparison. CIDI is retained only as an explicitly labelled, optional,
exploratory synthesis, computed **only when valid inputs exist**.

This module no longer contains any hard-coded case values (the previous module
embedded stale NotPetya / PAP / Romania numbers, including the now-excluded
Romania case). Nothing is auto-computed from defaults. Callers must pass
explicit, validated inputs.

Guards:
  * inputs must be floats in [0, 1];
  * CIDI is withheld when any required IVA component is unavailable
    (no aggregation over missing components);
  * the Technical–Public Gap diagnostic is NEVER an input;
  * TCI evidence coverage is surfaced (not silently thresholded) so a reader
    can judge whether the comparison is clean.

Input:  validated TCI score + a dict of available IVA component values
Output: CIDI synthesis dict (or an explicit withheld state)

Part of the CIDF framework — LUISS Guido Carli, 2026
Author: Giovanni Arosio
"""

from __future__ import annotations

from typing import Any, Optional

import numpy as np

DEFAULT_ALPHA = 0.40
DEFAULT_BETA = 0.60

# Component keys that may feed the IVA aggregate. The Technical–Public Gap
# diagnostic is deliberately ABSENT and must never be added here.
ALLOWED_IVA_COMPONENTS = ("attribution_drift", "narrative_fragmentation",
                          "response_timing_proxy")

EXPLORATORY_LABEL = (
    "CIDI is an optional, exploratory synthesis — not the primary result. It "
    "presupposes commensurability of a technical index and interpretive proxies "
    "measured on a small, curated corpus; treat it as illustrative only."
)


def _check_unit(value: float, name: str) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError(f"{name} must be a number in [0, 1], got {value!r}")
    v = float(value)
    if not 0.0 <= v <= 1.0:
        raise ValueError(f"{name} must be in [0, 1], got {v}")
    return v


def calculate_cidi(
    tci: float,
    iva: float,
    alpha: float = DEFAULT_ALPHA,
    beta: float = DEFAULT_BETA,
) -> float:
    """Compute CIDI = alpha·TCI + beta·IVA from validated scalar inputs.

    The asymmetric default weighting (alpha=0.40, beta=0.60) encodes the
    thesis's argument that the interpretive dimension carries more analytical
    weight. This is a modelling choice, not an empirical finding.
    """
    tci = _check_unit(tci, "TCI")
    iva = _check_unit(iva, "IVA")
    if abs(alpha + beta - 1.0) > 1e-6:
        raise ValueError(f"alpha + beta must equal 1.0, got {alpha + beta}")
    return float(alpha * tci + beta * iva)


def sensitivity_analysis(
    tci: float,
    iva: float,
    alpha_range: tuple[float, float] = (0.20, 0.60),
    steps: int = 9,
) -> dict[str, Any]:
    """Algebraic sensitivity of CIDI to the alpha/beta weight split.

    NOTE: a narrow band here reflects only how little the *formula* moves as the
    weight changes for these particular inputs. It does NOT establish empirical
    robustness of the underlying measurements.
    """
    alphas = np.linspace(alpha_range[0], alpha_range[1], steps)
    scores = [calculate_cidi(tci, iva, alpha=a, beta=1.0 - a) for a in alphas]
    return {
        "alphas": alphas.tolist(),
        "cidi_scores": scores,
        "baseline_cidi": calculate_cidi(tci, iva),
        "alpha_sensitivity_band": (min(scores), max(scores)),
        "band_width": max(scores) - min(scores),
        "caveat": "Band reflects algebraic weight sensitivity only, not "
                  "empirical robustness of the inputs.",
    }


def compute_cidi(
    tci_value: float,
    iva_components: dict[str, Optional[float]],
    *,
    alpha: float = DEFAULT_ALPHA,
    beta: float = DEFAULT_BETA,
    tci_evidence_coverage: Optional[float] = None,
    tci_score_kind: str = "unspecified",
) -> dict[str, Any]:
    """Compute the optional CIDI synthesis, or explicitly withhold it.

    Args:
        tci_value: a validated TCI score in [0, 1] (caller chooses which TCI
            figure — e.g. evidence-adjusted — and names it in ``tci_score_kind``).
        iva_components: mapping of IVA component name -> value or ``None`` when
            that component is unavailable for the case.
        tci_evidence_coverage: optional TCI evidence coverage to surface as a
            caveat (not used as a hidden threshold).
        tci_score_kind: label describing which TCI figure was supplied.

    Returns:
        dict with ``available`` True/False. When False, ``reason`` explains the
        withholding (e.g. unavailable IVA components). When True, includes the
        CIDI value, the IVA aggregate, the components used, the sensitivity band,
        and warnings (always including the exploratory label).
    """
    unexpected = sorted(set(iva_components) - set(ALLOWED_IVA_COMPONENTS))
    if unexpected:
        raise ValueError(
            f"Unexpected IVA component(s) for CIDI: {unexpected}. "
            f"Allowed: {list(ALLOWED_IVA_COMPONENTS)} "
            "(Technical–Public Gap is a diagnostic and must not be aggregated)."
        )

    tci_value = _check_unit(tci_value, "TCI")
    unavailable = sorted(k for k, v in iva_components.items() if v is None)
    if unavailable:
        return {
            "available": False,
            "reason": f"CIDI withheld: unavailable IVA component(s): "
                      f"{', '.join(unavailable)}. No aggregation over missing "
                      "components.",
            "cidi": None,
            "unavailable_components": unavailable,
            "warnings": [EXPLORATORY_LABEL],
        }
    if not iva_components:
        return {
            "available": False,
            "reason": "CIDI withheld: no IVA components supplied.",
            "cidi": None,
            "warnings": [EXPLORATORY_LABEL],
        }

    values = {k: _check_unit(v, f"IVA[{k}]") for k, v in iva_components.items()}
    iva_aggregate = float(np.mean(list(values.values())))
    cidi = calculate_cidi(tci_value, iva_aggregate, alpha, beta)
    sens = sensitivity_analysis(tci_value, iva_aggregate)

    warnings = [EXPLORATORY_LABEL]
    if tci_evidence_coverage is not None:
        warnings.append(
            f"TCI input ({tci_score_kind}) rests on evidence coverage "
            f"{tci_evidence_coverage:.2f}; lower coverage means a less clean "
            "comparison."
        )
    warnings.append(
        "Technical–Public Gap diagnostic is excluded from this aggregate.")

    return {
        "available": True,
        "cidi": cidi,
        "iva_aggregate": iva_aggregate,
        "tci_value": tci_value,
        "tci_score_kind": tci_score_kind,
        "tci_evidence_coverage": tci_evidence_coverage,
        "weights": {"alpha": alpha, "beta": beta},
        "components_used": values,
        "sensitivity": sens,
        "warnings": warnings,
    }


if __name__ == "__main__":
    # No hard-coded case values, no auto-computation from stale defaults.
    print("CIDI is an optional, exploratory synthesis and requires explicit, "
          "validated inputs.")
    print("Use scripts/run_methodology_audit.py to compute it only where valid "
          "inputs exist.")
    print("\nIllustrative call with explicit inputs:")
    demo = compute_cidi(
        tci_value=0.55,
        iva_components={
            "attribution_drift": 0.11,
            "narrative_fragmentation": 0.51,
            "response_timing_proxy": 0.42,
        },
        tci_evidence_coverage=0.80,
        tci_score_kind="evidence_adjusted (illustrative)",
    )
    print(f"  available={demo['available']}  cidi={demo['cidi']:.3f}  "
          f"iva_aggregate={demo['iva_aggregate']:.3f}")
