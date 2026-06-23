"""
Tests for the TCI calculator — legacy + evidence-aware.
=======================================================
Covers:
  * legacy ``calculate_tci`` float compatibility (unchanged behaviour);
  * unknown differs from documented absence;
  * inapplicable differs from unknown;
  * evidence-coverage calculations;
  * PAP and KA-SAT structured outputs (grounded in repository ATT&CK files);
  * invalid evidence-status rejection.

Run with pytest:    pytest tests/test_tci.py

Part of the CIDF framework — LUISS Guido Carli, 2026
Author: Giovanni Arosio
"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tci.tci_calculator import (
    TCIValidationError,
    analyze_tci,
    calculate_tci,
)

ROOT = Path(__file__).resolve().parents[1]

# NotPetya-style incident (June 2017): high-impact, self-propagating wiper.
NOTPETYA_INCIDENT = {
    "tactics": ["execution", "lateral_movement", "impact"],
    "techniques": [
        "EternalBlue", "supply_chain_compromise", "credential_dumping", "wiper",
    ],
    "stealth": 0.4,
    "persistence": False,
    "lateral_movement": True,
}


def _load(case_path: str) -> dict:
    return json.loads((ROOT / case_path).read_text(encoding="utf-8"))


# --------------------------- legacy compatibility --------------------------
def test_returns_float():
    assert isinstance(calculate_tci(NOTPETYA_INCIDENT), float)


def test_score_within_bounds():
    assert 0.0 <= calculate_tci(NOTPETYA_INCIDENT) <= 1.0


def test_notpetya_score_is_positive():
    assert calculate_tci(NOTPETYA_INCIDENT) > 0.0


def test_legacy_floats_unchanged_for_active_cases():
    """Pin the legacy scalar so backward compatibility is guaranteed."""
    assert round(calculate_tci(_load("data/notpetya/technical/notpetya_attck.json")), 3) == 0.580
    assert round(calculate_tci(_load("data/kasat_viasat/technical/kasat_attck.json")), 3) == 0.370
    assert round(calculate_tci(_load("data/pap_hack/technical/pap_attck.json")), 3) == 0.200


def test_floor_equals_legacy_when_no_unknown_placeholder():
    """For NotPetya/KA-SAT the conservative floor equals the legacy float."""
    for case in ("data/notpetya/technical/notpetya_attck.json",
                 "data/kasat_viasat/technical/kasat_attck.json"):
        inc = _load(case)
        r = analyze_tci(inc)
        assert round(r["conservative_floor_score"], 6) == round(calculate_tci(inc), 6)


def test_floor_is_stricter_than_legacy_for_pap():
    """PAP stealth is unknown (placeholder 0.5), so the floor zeros it out."""
    inc = _load("data/pap_hack/technical/pap_attck.json")
    r = analyze_tci(inc)
    assert r["conservative_floor_score"] < calculate_tci(inc)
    assert round(r["conservative_floor_score"], 3) == 0.100


# ------------------------- unknown vs documented absence -------------------
def _base_incident(**overrides):
    inc = {
        "tactics": ["a", "b", "c", "d"],            # 4 -> 0.4
        "techniques": ["t1", "t2"],                 # 2 -> 0.1
        "stealth": 0.5,
        "persistence": False,
        "lateral_movement": False,
        "evidence_status": {
            "tactics": "documented_present",
            "techniques": "documented_present",
            "stealth": "inferred",
            "persistence": "unknown",
            "lateral_movement": "unknown",
        },
    }
    inc.update(overrides)
    return inc


def test_unknown_differs_from_documented_absence():
    """Same raw values; persistence unknown vs documented_absence must differ
    in coverage and in the evidence-adjusted score (absence counts as a 0,
    unknown is excluded)."""
    unknown_inc = _base_incident()
    absence_inc = _base_incident()
    absence_inc["evidence_status"] = dict(unknown_inc["evidence_status"])
    absence_inc["evidence_status"]["persistence"] = "documented_absence"

    r_unknown = analyze_tci(unknown_inc)
    r_absence = analyze_tci(absence_inc)

    # Floor is identical (false persistence contributes 0 either way).
    assert r_unknown["conservative_floor_score"] == r_absence["conservative_floor_score"]
    # Coverage and the evidence-adjusted score must change.
    assert r_absence["evidence_coverage"] > r_unknown["evidence_coverage"]
    assert r_absence["evidence_adjusted_score"] != r_unknown["evidence_adjusted_score"]
    assert "persistence" in r_unknown["unknown_components"]
    assert "persistence" in r_absence["documented_components"]


def test_inapplicable_differs_from_unknown():
    """Inapplicable shrinks the applicable denominator; unknown does not."""
    unknown_inc = _base_incident()
    inappl_inc = _base_incident()
    inappl_inc["evidence_status"] = dict(unknown_inc["evidence_status"])
    inappl_inc["evidence_status"]["persistence"] = "inapplicable"

    r_unknown = analyze_tci(unknown_inc)
    r_inappl = analyze_tci(inappl_inc)

    assert r_unknown["applicable_component_count"] == 5
    assert r_inappl["applicable_component_count"] == 4
    # Same documented set (2), but coverage rises because the denominator drops.
    assert r_inappl["evidence_coverage"] > r_unknown["evidence_coverage"]


def test_evidence_coverage_values_for_active_cases():
    assert round(analyze_tci(_load("data/notpetya/technical/notpetya_attck.json"))["evidence_coverage"], 2) == 0.80
    assert round(analyze_tci(_load("data/kasat_viasat/technical/kasat_attck.json"))["evidence_coverage"], 2) == 0.60
    assert round(analyze_tci(_load("data/pap_hack/technical/pap_attck.json"))["evidence_coverage"], 2) == 0.40


def test_kasat_structured_output():
    r = analyze_tci(_load("data/kasat_viasat/technical/kasat_attck.json"))
    # Persistence must NOT be a documented false claim.
    assert r["component_results"]["persistence"]["status"] == "unknown"
    # Stealth must be inferred, not directly observed.
    assert r["component_results"]["stealth"]["status"] == "inferred"
    assert round(r["evidence_adjusted_score"], 3) == 0.550
    assert round(r["assessment_coverage"], 2) == 0.80


def test_pap_structured_output():
    r = analyze_tci(_load("data/pap_hack/technical/pap_attck.json"))
    # Persistence and lateral movement must not be documented absence.
    assert r["component_results"]["persistence"]["status"] == "unknown"
    assert r["component_results"]["lateral_movement"]["status"] == "unknown"
    assert r["component_results"]["stealth"]["status"] == "unknown"
    assert round(r["evidence_adjusted_score"], 3) == 0.250
    assert "persistence" in r["unknown_components"]


def test_notpetya_persistence_documented_absence():
    r = analyze_tci(_load("data/notpetya/technical/notpetya_attck.json"))
    assert r["component_results"]["persistence"]["status"] == "documented_absence"
    assert round(r["evidence_adjusted_score"], 3) == 0.662
    assert round(r["assessment_coverage"], 2) == 1.00


def test_invalid_evidence_status_rejected():
    bad = _base_incident()
    bad["evidence_status"] = dict(bad["evidence_status"])
    bad["evidence_status"]["persistence"] = "totally_unknown"  # not a valid status
    with pytest.raises(TCIValidationError):
        analyze_tci(bad)


def test_missing_evidence_status_is_handled_not_crashing():
    """A legacy incident without evidence_status still analyses, flagged."""
    r = analyze_tci(NOTPETYA_INCIDENT)
    assert r["evidence_adjusted_score"] is None
    assert any("evidence_status" in w for w in r["warnings"])


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
