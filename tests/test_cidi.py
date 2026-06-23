"""
Tests for the cleaned CIDI integrator.
======================================
Proves:
  * no hard-coded case values (NotPetya/PAP/Romania) drive computation;
  * CIDI is withheld when any required IVA component is unavailable;
  * the Technical–Public Gap diagnostic is rejected as a CIDI input;
  * inputs must be validated [0, 1];
  * the exploratory label and sensitivity caveat are always present.

Run:  pytest tests/test_cidi.py

Part of the CIDF framework — LUISS Guido Carli, 2026
Author: Giovanni Arosio
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cidi.cidi_integrator import (
    calculate_cidi,
    compute_cidi,
    sensitivity_analysis,
)


def test_formula_basic():
    assert round(calculate_cidi(0.5, 0.5), 3) == 0.5
    assert round(calculate_cidi(1.0, 0.0, alpha=0.4, beta=0.6), 3) == 0.4


def test_rejects_out_of_range_inputs():
    with pytest.raises(ValueError):
        calculate_cidi(1.5, 0.5)
    with pytest.raises(ValueError):
        compute_cidi(0.5, {"attribution_drift": 2.0})


def test_withheld_when_component_unavailable():
    res = compute_cidi(0.55, {
        "attribution_drift": 0.11,
        "narrative_fragmentation": 0.51,
        "response_timing_proxy": None,   # e.g. KA-SAT (no early-window docs)
    })
    assert res["available"] is False
    assert "response_timing_proxy" in res["unavailable_components"]
    assert res["cidi"] is None


def test_technical_public_gap_rejected_as_input():
    with pytest.raises(ValueError):
        compute_cidi(0.5, {
            "attribution_drift": 0.1,
            "technical_public_gap": 0.49,   # diagnostic — must not aggregate
        })


def test_available_when_all_components_present():
    res = compute_cidi(0.55, {
        "attribution_drift": 0.11,
        "narrative_fragmentation": 0.51,
        "response_timing_proxy": 0.42,
    }, tci_evidence_coverage=0.80, tci_score_kind="evidence_adjusted")
    assert res["available"] is True
    assert 0.0 <= res["cidi"] <= 1.0
    assert any("exploratory" in w.lower() for w in res["warnings"])
    assert any("Technical–Public Gap" in w for w in res["warnings"])
    assert res["tci_evidence_coverage"] == 0.80


def test_sensitivity_band_has_robustness_caveat():
    sens = sensitivity_analysis(0.5, 0.4)
    assert "caveat" in sens
    assert "robust" in sens["caveat"].lower()
    assert "alpha_sensitivity_band" in sens


def test_no_hardcoded_case_values_in_source():
    src = Path(__import__("cidi.cidi_integrator", fromlist=["x"]).__file__).read_text()
    # No Romania as a string-literal case label (the old hard-coded data form).
    assert '"Romania"' not in src
    assert "'Romania'" not in src
    # No hard-coded case tuples like ("NotPetya", 0.580, 0.528).
    assert '("NotPetya"' not in src
    assert '("PAP Hack"' not in src


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
