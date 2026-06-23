"""
CIDI — Cyber-Interpretive Disruption Index (scenario-based synthesis)
====================================================================
CIDI is a **scenario-based exploratory synthesis rather than a primary
inferential result**. Its purpose is to summarize alternative, transparent
modelling choices *after* the substantive comparison of evidence-aware TCI and
the individual IVA components. No unique empirically validated weighting
structure is claimed.

Two-level architecture
----------------------
* **CIDI Core** — the primary comparative synthesis, available for all three
  active cases. It combines TCI with the *Core Interpretive Vector* (IVC_core):

      IVC_core = 0.50 × Attribution Drift + 0.50 × Narrative Fragmentation

  The Core Interpretive Vector combines Attribution Drift and Narrative
  Fragmentation with equal weights because both directly represent instability
  in the attributional and narrative dimensions of the constructed corpus.

* **CIDI Extended** — a supplementary scenario that additionally includes the
  Response Timing Proxy, available only where that proxy is available:

      IVA_extended = 0.40 × Attribution Drift
                   + 0.40 × Narrative Fragmentation
                   + 0.20 × Response Timing Proxy

  The Extended Interpretive Vector incorporates the Response Timing Proxy with a
  lower weight because it captures contextual temporal pressure rather than an
  equivalent direct manifestation of interpretive instability.

Each level is evaluated under three transparent weight scenarios (neutral /
interpretive-prioritized / technical-prioritized). These are sensitivity
scenarios, NOT empirical estimates of true causal importance.

Hard rules
----------
* The TCI input is always the **evidence-adjusted** score.
* Evidence coverage is displayed alongside scores but is **never** mathematically
  folded into them.
* The Technical–Public Gap diagnostic is **excluded from every aggregate** and
  must never enter a CIDI formula.
* The Response Timing Proxy is unavailable for KA-SAT and is **never imputed**;
  Extended CIDI is therefore unavailable for KA-SAT (a valid data limitation).
* No silent/default equal-weight aggregation exists.

Part of the CIDF framework — LUISS Guido Carli, 2026
Author: Giovanni Arosio
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

# IVA components that may legitimately feed a CIDI aggregate. The Technical–
# Public Gap diagnostic is deliberately ABSENT and is rejected explicitly.
ALLOWED_CIDI_IVA_COMPONENTS = (
    "attribution_drift", "narrative_fragmentation", "response_timing_proxy",
)
FORBIDDEN_CIDI_INPUTS = frozenset(
    {"technical_public_gap", "technical_public_gap_diagnostic"}
)

CORE_IVA_WEIGHTS = {"attribution_drift": 0.50, "narrative_fragmentation": 0.50}
EXTENDED_IVA_WEIGHTS = {
    "attribution_drift": 0.40,
    "narrative_fragmentation": 0.40,
    "response_timing_proxy": 0.20,
}

EXPLORATORY_LABEL = (
    "CIDI is a scenario-based exploratory synthesis, not a primary inferential "
    "result; weights are transparent modelling choices, not empirically "
    "validated causal importance. Exploratory, corpus-bound, non-causal."
)


@dataclass(frozen=True)
class CidiScenario:
    """A named CIDI weighting scenario."""
    name: str
    model_type: str                 # "core" | "extended"
    iva_weights: dict[str, float]
    tci_weight: float               # alpha
    iva_weight: float               # beta
    rationale: str


# -- Core scenarios --------------------------------------------------------
_CORE_RATIONALE = (
    "Core Interpretive Vector = equal-weight Attribution Drift + Narrative "
    "Fragmentation (the two components most directly representing attributional "
    "and narrative instability)."
)
CORE_NEUTRAL = CidiScenario(
    "core_neutral", "core", CORE_IVA_WEIGHTS, 0.50, 0.50,
    _CORE_RATIONALE + " Neutral 0.50/0.50 split of TCI vs IVC_core.")
CORE_INTERPRETIVE_PRIORITIZED = CidiScenario(
    "core_interpretive_prioritized", "core", CORE_IVA_WEIGHTS, 0.40, 0.60,
    _CORE_RATIONALE + " Interpretive-prioritized 0.40/0.60 (thesis argument, "
    "not an empirical finding).")
CORE_TECHNICAL_PRIORITIZED = CidiScenario(
    "core_technical_prioritized", "core", CORE_IVA_WEIGHTS, 0.60, 0.40,
    _CORE_RATIONALE + " Technical-prioritized 0.60/0.40 (counterfactual "
    "sensitivity scenario).")

# -- Extended scenarios ----------------------------------------------------
_EXTENDED_RATIONALE = (
    "Extended Interpretive Vector adds the Response Timing Proxy at a lower "
    "weight (0.20) because it captures contextual temporal pressure rather than "
    "an equivalent direct manifestation of interpretive instability."
)
EXTENDED_NEUTRAL = CidiScenario(
    "extended_neutral", "extended", EXTENDED_IVA_WEIGHTS, 0.50, 0.50,
    _EXTENDED_RATIONALE + " Neutral 0.50/0.50 split of TCI vs IVA_extended.")
EXTENDED_INTERPRETIVE_PRIORITIZED = CidiScenario(
    "extended_interpretive_prioritized", "extended", EXTENDED_IVA_WEIGHTS, 0.40, 0.60,
    _EXTENDED_RATIONALE + " Interpretive-prioritized 0.40/0.60.")
EXTENDED_TECHNICAL_PRIORITIZED = CidiScenario(
    "extended_technical_prioritized", "extended", EXTENDED_IVA_WEIGHTS, 0.60, 0.40,
    _EXTENDED_RATIONALE + " Technical-prioritized 0.60/0.40.")

CORE_SCENARIOS: tuple[CidiScenario, ...] = (
    CORE_NEUTRAL, CORE_INTERPRETIVE_PRIORITIZED, CORE_TECHNICAL_PRIORITIZED,
)
EXTENDED_SCENARIOS: tuple[CidiScenario, ...] = (
    EXTENDED_NEUTRAL, EXTENDED_INTERPRETIVE_PRIORITIZED, EXTENDED_TECHNICAL_PRIORITIZED,
)


def _check_unit(value: Any, name: str) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError(f"{name} must be a number in [0, 1], got {value!r}")
    v = float(value)
    if not 0.0 <= v <= 1.0:
        raise ValueError(f"{name} must be in [0, 1], got {v}")
    return v


def calculate_cidi(tci: float, iva: float, alpha: float, beta: float) -> float:
    """CIDI = alpha·TCI + beta·IVA from validated scalar inputs."""
    tci = _check_unit(tci, "TCI")
    iva = _check_unit(iva, "IVA")
    if abs(alpha + beta - 1.0) > 1e-9:
        raise ValueError(f"alpha + beta must equal 1.0, got {alpha + beta}")
    return float(alpha * tci + beta * iva)


def calculate_weighted_iva(
    components: dict[str, Optional[float]],
    weights: dict[str, float],
    scenario_name: str,
    scenario_rationale: str,
) -> dict[str, Any]:
    """Explicit, scenario-weighted IVA aggregate (no silent equal-weight mean).

    Validates that every supplied component is allowed (the Technical–Public Gap
    diagnostic is rejected), that weights are defined for exactly the supplied
    components, and that weights sum to 1.0. Unavailable (``None``) components
    make the aggregate unavailable with a reason — never imputed.
    """
    forbidden = (set(components) | set(weights)) & FORBIDDEN_CIDI_INPUTS
    if forbidden:
        raise ValueError(
            f"{sorted(forbidden)} is a diagnostic and must never enter a CIDI "
            "formula."
        )
    not_allowed = (set(components) | set(weights)) - set(ALLOWED_CIDI_IVA_COMPONENTS)
    if not_allowed:
        raise ValueError(
            f"Unknown CIDI IVA component(s): {sorted(not_allowed)}. "
            f"Allowed: {list(ALLOWED_CIDI_IVA_COMPONENTS)}."
        )
    if set(components) != set(weights):
        raise ValueError(
            "weights must be defined for exactly the supplied components; "
            f"components={sorted(components)} weights={sorted(weights)}."
        )
    weight_sum = sum(weights.values())
    if abs(weight_sum - 1.0) > 1e-9:
        raise ValueError(f"weights must sum to 1.0, got {weight_sum}.")

    unavailable = sorted(k for k, v in components.items() if v is None)
    if unavailable:
        return {
            "available": False,
            "reason": f"unavailable component(s): {', '.join(unavailable)} "
                      "(not imputed).",
            "aggregate_score": None,
            "components": dict(components),
            "weights": dict(weights),
            "scenario_name": scenario_name,
            "scenario_rationale": scenario_rationale,
            "warnings": [EXPLORATORY_LABEL],
        }

    values = {k: _check_unit(v, f"IVA[{k}]") for k, v in components.items()}
    aggregate = float(sum(weights[k] * values[k] for k in values))
    return {
        "available": True,
        "aggregate_score": aggregate,
        "components": values,
        "weights": dict(weights),
        "scenario_name": scenario_name,
        "scenario_rationale": scenario_rationale,
        "warnings": [EXPLORATORY_LABEL],
    }


def compute_cidi_scenario(
    tci_value: Optional[float],
    tci_score_kind: str,
    tci_evidence_coverage: Optional[float],
    iva_result: dict[str, Any],
    alpha: float,
    beta: float,
    scenario_name: str,
    scenario_rationale: str,
) -> dict[str, Any]:
    """Compute one CIDI scenario transparently, or withhold it with a reason."""
    if tci_value is None:
        return {
            "available": False, "scenario_name": scenario_name,
            "scenario_rationale": scenario_rationale, "cidi": None,
            "reason": "TCI evidence-adjusted score undefined (no documented "
                      "components).",
            "iva": iva_result, "warnings": [EXPLORATORY_LABEL],
        }
    if not iva_result.get("available"):
        return {
            "available": False, "scenario_name": scenario_name,
            "scenario_rationale": scenario_rationale, "cidi": None,
            "reason": iva_result.get("reason", "IVA aggregate unavailable."),
            "iva": iva_result, "warnings": [EXPLORATORY_LABEL],
        }

    tci_value = _check_unit(tci_value, "TCI")
    cidi = calculate_cidi(tci_value, iva_result["aggregate_score"], alpha, beta)
    warnings = [EXPLORATORY_LABEL]
    if tci_evidence_coverage is not None:
        warnings.append(
            f"TCI input ({tci_score_kind}) rests on evidence coverage "
            f"{tci_evidence_coverage:.2f}; coverage is a separate caveat and is "
            "NOT folded into the score."
        )
    warnings.append("Technical–Public Gap is excluded from this aggregate.")
    return {
        "available": True,
        "scenario_name": scenario_name,
        "scenario_rationale": scenario_rationale,
        "cidi": cidi,
        "tci_value": tci_value,
        "tci_score_kind": tci_score_kind,
        "tci_evidence_coverage": tci_evidence_coverage,
        "weights": {"alpha": alpha, "beta": beta},
        "iva_aggregate": iva_result["aggregate_score"],
        "iva": iva_result,
        "warnings": warnings,
    }


def run_cidi_scenario(
    scenario: CidiScenario,
    *,
    tci_value: Optional[float],
    tci_score_kind: str,
    tci_evidence_coverage: Optional[float],
    iva_components: dict[str, Optional[float]],
) -> dict[str, Any]:
    """Convenience: build the scenario's IVA aggregate and CIDI in one call."""
    subset = {k: iva_components.get(k) for k in scenario.iva_weights}
    iva_result = calculate_weighted_iva(
        subset, scenario.iva_weights, scenario.name, scenario.rationale)
    result = compute_cidi_scenario(
        tci_value, tci_score_kind, tci_evidence_coverage, iva_result,
        scenario.tci_weight, scenario.iva_weight, scenario.name,
        scenario.rationale)
    result["model_type"] = scenario.model_type
    return result


def core_interpretive_vector(
    iva_components: dict[str, Optional[float]],
) -> dict[str, Any]:
    """IVC_core = 0.50·Attribution Drift + 0.50·Narrative Fragmentation."""
    subset = {k: iva_components.get(k) for k in CORE_IVA_WEIGHTS}
    return calculate_weighted_iva(
        subset, CORE_IVA_WEIGHTS, "ivc_core",
        "Core Interpretive Vector (equal-weight Attribution Drift + Narrative "
        "Fragmentation).")


if __name__ == "__main__":
    print("CIDI is a scenario-based exploratory synthesis; no single definitive "
          "value is produced.")
    demo_components = {
        "attribution_drift": 0.291,
        "narrative_fragmentation": 0.646,
        "response_timing_proxy": 0.422,
    }
    ivc = core_interpretive_vector(demo_components)
    print(f"IVC_core (illustrative) = {ivc['aggregate_score']:.3f}")
    for sc in CORE_SCENARIOS:
        r = run_cidi_scenario(sc, tci_value=0.662, tci_score_kind="evidence_adjusted",
                              tci_evidence_coverage=0.80, iva_components=demo_components)
        print(f"  {sc.name:32} cidi={r['cidi']:.3f}")
