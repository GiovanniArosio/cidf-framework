"""
TCI — Technical Complexity Index (evidence-aware)
=================================================
Measures the operational sophistication of cyber incidents using the
MITRE ATT&CK framework.

The legacy model averaged five equally weighted components and turned any
boolean ``false`` into a zero — so it could not distinguish *documented
absence* from *unknown*, *inferred judgement*, or *inapplicable* components.
That conflation produced a conservative lower bound that must not be presented
as a full observed-complexity score.

This module keeps the legacy scalar (``calculate_tci`` -> float) for backward
compatibility and adds an **evidence-aware** analysis (``analyze_tci``) that
returns, alongside the legacy-style floor, scores that are honest about which
components are actually documented.

Evidence statuses per component:
  * ``documented_present``  — present and evidenced
  * ``documented_absence``  — absent and evidenced (genuine absence)
  * ``inferred``            — analyst inference, not directly observed
  * ``unknown``             — not observable / not established by the evidence
  * ``inapplicable``        — component does not apply to this incident

Input:  ATT&CK incident dict (optionally carrying ``evidence_status``)
Output: legacy float (compat) OR a structured evidence-aware result dict

Part of the CIDF framework — LUISS Guido Carli, 2026
Author: Giovanni Arosio
"""

from __future__ import annotations

from typing import Any

# Normalization caps for the count-based components.
MAX_TACTICS = 10
MAX_TECHNIQUES = 20

# Number of equally weighted components in the baseline TCI.
_NUM_COMPONENTS = 5

COMPONENTS = ("tactics", "techniques", "stealth", "persistence", "lateral_movement")

_REQUIRED_KEYS = COMPONENTS

EVIDENCE_STATUSES = frozenset(
    {"documented_present", "documented_absence", "inferred", "unknown", "inapplicable"}
)

# Statuses that count as "documented" (directly evidenced, present or absent).
_DOCUMENTED = {"documented_present", "documented_absence"}
# Statuses whose raw value is credited toward the conservative floor.
_FLOOR_CREDITED = {"documented_present", "documented_absence", "inferred"}


class TCIValidationError(ValueError):
    """Raised when the TCI input payload is malformed."""


def _validate(incident: dict[str, Any]) -> None:
    """Validate the incident payload before scoring (legacy contract)."""
    if not isinstance(incident, dict):
        raise TCIValidationError("Input must be a dictionary.")

    missing = [key for key in _REQUIRED_KEYS if key not in incident]
    if missing:
        raise TCIValidationError(f"Missing required key(s): {', '.join(missing)}")

    if not isinstance(incident["tactics"], list):
        raise TCIValidationError("'tactics' must be a list.")
    if not isinstance(incident["techniques"], list):
        raise TCIValidationError("'techniques' must be a list.")

    stealth = incident["stealth"]
    # bool is a subclass of int — reject it explicitly so True/False is not
    # silently treated as a stealth level.
    if isinstance(stealth, bool) or not isinstance(stealth, (int, float)):
        raise TCIValidationError("'stealth' must be a number between 0 and 1.")
    if not 0.0 <= float(stealth) <= 1.0:
        raise TCIValidationError("'stealth' must be between 0 and 1.")

    if not isinstance(incident["persistence"], bool):
        raise TCIValidationError("'persistence' must be a boolean.")
    if not isinstance(incident["lateral_movement"], bool):
        raise TCIValidationError("'lateral_movement' must be a boolean.")


def _component_values(incident: dict[str, Any]) -> dict[str, float]:
    """Raw normalized component values (identical to the legacy model)."""
    return {
        "tactics": min(len(incident["tactics"]) / MAX_TACTICS, 1.0),
        "techniques": min(len(incident["techniques"]) / MAX_TECHNIQUES, 1.0),
        "stealth": float(incident["stealth"]),
        "persistence": 1.0 if incident["persistence"] else 0.0,
        "lateral_movement": 1.0 if incident["lateral_movement"] else 0.0,
    }


def calculate_tci(incident: dict[str, Any]) -> float:
    """Legacy Technical Complexity Index (conservative lower-bound float).

    Equal-weight average of the five raw component values, with every boolean
    ``false`` and the raw ``stealth`` value taken at face value. Preserved
    unchanged for backward compatibility; treats unobserved/unknown evidence
    implicitly as zero and therefore **must not** be presented as a full
    observed-complexity score. Use :func:`analyze_tci` for evidence-aware output.
    """
    _validate(incident)
    values = _component_values(incident)
    return sum(values.values()) / _NUM_COMPONENTS


def _resolve_statuses(incident: dict[str, Any]) -> tuple[dict[str, str], list[str]]:
    """Return (status_per_component, warnings).

    If ``evidence_status`` is absent the analysis cannot assess coverage and all
    components are marked ``unknown`` with a warning. Provided statuses are
    validated against ``EVIDENCE_STATUSES``.
    """
    warnings: list[str] = []
    raw = incident.get("evidence_status")
    if raw is None:
        return ({c: "unknown" for c in COMPONENTS},
                ["no 'evidence_status' provided; evidence coverage cannot be "
                 "assessed (all components treated as unknown)."])
    if not isinstance(raw, dict):
        raise TCIValidationError("'evidence_status' must be a dict.")

    statuses: dict[str, str] = {}
    for c in COMPONENTS:
        status = raw.get(c)
        if status is None:
            statuses[c] = "unknown"
            warnings.append(f"component '{c}' has no evidence_status (treated as unknown).")
            continue
        if status not in EVIDENCE_STATUSES:
            raise TCIValidationError(
                f"Invalid evidence_status for '{c}': {status!r}. "
                f"Expected one of: {', '.join(sorted(EVIDENCE_STATUSES))}."
            )
        statuses[c] = status
    extra = set(raw) - set(COMPONENTS)
    if extra:
        warnings.append(f"evidence_status has unexpected component(s): "
                        f"{', '.join(sorted(extra))} (ignored).")
    return statuses, warnings


def analyze_tci(incident: dict[str, Any]) -> dict[str, Any]:
    """Evidence-aware TCI analysis.

    Returns:
        dict with:
          * ``conservative_floor_score`` — fixed-denominator (/5) score where
            ``unknown``/``inapplicable`` components contribute zero. Equals the
            legacy :func:`calculate_tci` float except where a non-zero placeholder
            value was attached to an unknown component (then it is stricter).
          * ``evidence_adjusted_score`` — mean over **documented** components
            (present or absent) only; ``None`` if none are documented.
          * ``assessed_score_including_inferred`` — mean over documented **and
            inferred** components; ``None`` if none qualify. Includes analyst
            inference and is labelled as such.
          * ``evidence_coverage`` — documented / applicable components.
          * ``assessment_coverage`` — (documented + inferred) / applicable.
          * ``component_results`` — per-component status, raw value, and the
            aggregates it contributes to.
          * ``legacy_score`` — the unchanged legacy float, for reference.
          * ``warnings`` — coverage and data-quality notes.
    """
    _validate(incident)
    values = _component_values(incident)
    statuses, warnings = _resolve_statuses(incident)

    applicable = [c for c in COMPONENTS if statuses[c] != "inapplicable"]
    documented = [c for c in applicable if statuses[c] in _DOCUMENTED]
    inferred = [c for c in applicable if statuses[c] == "inferred"]
    unknown = [c for c in applicable if statuses[c] == "unknown"]

    # Conservative floor: fixed denominator of 5; unknown/inapplicable -> 0.
    floor = sum(
        values[c] if statuses[c] in _FLOOR_CREDITED else 0.0
        for c in COMPONENTS
    ) / _NUM_COMPONENTS

    def _mean(cols: list[str]) -> float | None:
        return (sum(values[c] for c in cols) / len(cols)) if cols else None

    evidence_adjusted = _mean(documented)
    assessed_incl_inferred = _mean(documented + inferred)

    n_applicable = len(applicable)
    evidence_coverage = (len(documented) / n_applicable) if n_applicable else 0.0
    assessment_coverage = (
        (len(documented) + len(inferred)) / n_applicable if n_applicable else 0.0
    )

    if evidence_adjusted is None:
        warnings.append(
            "no documented components; evidence_adjusted_score is undefined."
        )
    if unknown:
        warnings.append(
            "unknown components excluded from evidence-adjusted score: "
            + ", ".join(unknown) + " (not treated as documented absence)."
        )
    if inferred:
        warnings.append(
            "assessed_score_including_inferred includes analyst inference for: "
            + ", ".join(inferred) + "."
        )

    component_results = {}
    for c in COMPONENTS:
        st = statuses[c]
        component_results[c] = {
            "status": st,
            "raw_value": values[c],
            "in_floor": st in _FLOOR_CREDITED,
            "in_evidence_adjusted": st in _DOCUMENTED,
            "in_assessed": st in _DOCUMENTED or st == "inferred",
            "applicable": st != "inapplicable",
        }

    return {
        "conservative_floor_score": float(floor),
        "evidence_adjusted_score": (
            float(evidence_adjusted) if evidence_adjusted is not None else None
        ),
        "assessed_score_including_inferred": (
            float(assessed_incl_inferred)
            if assessed_incl_inferred is not None else None
        ),
        "evidence_coverage": float(evidence_coverage),
        "assessment_coverage": float(assessment_coverage),
        "documented_components": documented,
        "inferred_components": inferred,
        "unknown_components": unknown,
        "applicable_component_count": n_applicable,
        "component_results": component_results,
        "legacy_score": float(sum(values.values()) / _NUM_COMPONENTS),
        "warnings": warnings,
    }


if __name__ == "__main__":
    import json
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    cases = {
        "NotPetya": root / "data/notpetya/technical/notpetya_attck.json",
        "KA-SAT / Viasat": root / "data/kasat_viasat/technical/kasat_attck.json",
        "PAP Hack": root / "data/pap_hack/technical/pap_attck.json",
    }
    print(f"{'Case':<18} {'floor':>6} {'evid':>6} {'assess':>7} {'cov':>5}")
    print("-" * 50)
    for name, path in cases.items():
        incident = json.loads(path.read_text(encoding="utf-8"))
        r = analyze_tci(incident)
        ev = r["evidence_adjusted_score"]
        ai = r["assessed_score_including_inferred"]
        print(f"{name:<18} {r['conservative_floor_score']:>6.3f} "
              f"{ev if ev is None else f'{ev:.3f}':>6} "
              f"{ai if ai is None else f'{ai:.3f}':>7} "
              f"{r['evidence_coverage']:>5.2f}")
