"""
Tests for the scenario-based Core/Extended CIDI synthesis.
=========================================================
Proves:
  1. Core IVC uses only Attribution Drift and Narrative Fragmentation.
  2. Technical–Public Gap cannot be passed into any CIDI scenario.
  3. All scenario component weights must sum to 1.0.
  4. Every required component must be available (None -> unavailable).
  5. Core scenarios remain available for KA-SAT-like inputs (no timing).
  6. Extended scenarios are unavailable when the Response Timing Proxy is None.
  7. Scenario labels, weights and rationales are present in the result.
  8. No function silently applies an equal-weight mean.
  9. (audit output structure) — covered in test_audit_runner.py.
 10. Ranking stability logic — covered in test_audit_runner.py.

Run:  pytest tests/test_cidi.py

Part of the CIDF framework — LUISS Guido Carli, 2026
Author: Giovanni Arosio
"""

import inspect
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import cidi.cidi_integrator as ci
from cidi.cidi_integrator import (
    CORE_IVA_WEIGHTS,
    CORE_SCENARIOS,
    EXTENDED_IVA_WEIGHTS,
    EXTENDED_SCENARIOS,
    calculate_cidi,
    calculate_weighted_iva,
    core_interpretive_vector,
    run_cidi_scenario,
)


# 1. Core IVC uses only Attribution Drift + Narrative Fragmentation.
def test_core_ivc_uses_only_attrdrift_and_narrfrag():
    assert set(CORE_IVA_WEIGHTS) == {"attribution_drift", "narrative_fragmentation"}
    assert "response_timing_proxy" not in CORE_IVA_WEIGHTS
    res = core_interpretive_vector({"attribution_drift": 0.2,
                                    "narrative_fragmentation": 0.6,
                                    "response_timing_proxy": 0.9})
    # response_timing_proxy is ignored by the Core vector.
    assert set(res["components"]) == {"attribution_drift", "narrative_fragmentation"}
    assert res["aggregate_score"] == pytest.approx(0.4)


# 2. Technical–Public Gap cannot enter any CIDI scenario.
def test_technical_public_gap_rejected_everywhere():
    with pytest.raises(ValueError):
        calculate_weighted_iva(
            {"attribution_drift": 0.1, "technical_public_gap_diagnostic": 0.5},
            {"attribution_drift": 0.5, "technical_public_gap_diagnostic": 0.5},
            "x", "y")
    with pytest.raises(ValueError):
        calculate_weighted_iva({"technical_public_gap": 0.4},
                               {"technical_public_gap": 1.0}, "x", "y")


# 3. Scenario weights must sum to 1.0 (both the IVA weights and TCI/IVA split).
def test_all_scenario_weights_sum_to_one():
    for sc in (*CORE_SCENARIOS, *EXTENDED_SCENARIOS):
        assert sum(sc.iva_weights.values()) == pytest.approx(1.0)
        assert sc.tci_weight + sc.iva_weight == pytest.approx(1.0)
    # And calculate_weighted_iva rejects non-normalized weights.
    with pytest.raises(ValueError):
        calculate_weighted_iva({"attribution_drift": 0.5, "narrative_fragmentation": 0.5},
                               {"attribution_drift": 0.7, "narrative_fragmentation": 0.7},
                               "x", "y")


# 4. Every required component must be available.
def test_unavailable_component_makes_aggregate_unavailable():
    res = calculate_weighted_iva(
        {"attribution_drift": 0.2, "narrative_fragmentation": None},
        CORE_IVA_WEIGHTS, "x", "y")
    assert res["available"] is False
    assert "narrative_fragmentation" in res["reason"]
    assert res["aggregate_score"] is None


# 5. Core scenarios remain available without any timing data (KA-SAT-like).
def test_core_available_without_timing():
    comps = {"attribution_drift": 0.174, "narrative_fragmentation": 0.509,
             "response_timing_proxy": None}
    for sc in CORE_SCENARIOS:
        r = run_cidi_scenario(sc, tci_value=0.55, tci_score_kind="evidence_adjusted",
                              tci_evidence_coverage=0.60, iva_components=comps)
        assert r["available"] is True
        assert 0.0 <= r["cidi"] <= 1.0


# 6. Extended scenarios unavailable when Response Timing Proxy is None.
def test_extended_unavailable_without_timing():
    comps = {"attribution_drift": 0.174, "narrative_fragmentation": 0.509,
             "response_timing_proxy": None}
    for sc in EXTENDED_SCENARIOS:
        r = run_cidi_scenario(sc, tci_value=0.55, tci_score_kind="evidence_adjusted",
                              tci_evidence_coverage=0.60, iva_components=comps)
        assert r["available"] is False
        assert "response_timing_proxy" in r["reason"]
        assert r["cidi"] is None


# 7. Scenario labels, weights and rationales are present in the result.
def test_scenario_metadata_present_in_result():
    comps = {"attribution_drift": 0.291, "narrative_fragmentation": 0.646,
             "response_timing_proxy": 0.422}
    r = run_cidi_scenario(EXTENDED_SCENARIOS[0], tci_value=0.662,
                          tci_score_kind="evidence_adjusted",
                          tci_evidence_coverage=0.80, iva_components=comps)
    assert r["scenario_name"] == "extended_neutral"
    assert r["model_type"] == "extended"
    assert r["scenario_rationale"]
    assert r["iva"]["weights"] == EXTENDED_IVA_WEIGHTS
    assert r["weights"] == {"alpha": 0.50, "beta": 0.50}


# 8. No silent equal-weight mean anywhere in the module.
def test_no_silent_equal_weight_mean():
    src = inspect.getsource(ci)
    assert "np.mean" not in src
    assert "statistics.mean" not in src
    # weighted aggregation must reference explicit weights
    assert "weights[k] * values[k]" in src


# Extra: coverage is never folded into the score.
def test_coverage_not_folded_into_score():
    comps = {"attribution_drift": 0.2, "narrative_fragmentation": 0.6}
    a = run_cidi_scenario(CORE_SCENARIOS[0], tci_value=0.5,
                          tci_score_kind="evidence_adjusted",
                          tci_evidence_coverage=0.40, iva_components=comps)
    b = run_cidi_scenario(CORE_SCENARIOS[0], tci_value=0.5,
                          tci_score_kind="evidence_adjusted",
                          tci_evidence_coverage=0.90, iva_components=comps)
    # Different coverage, identical CIDI -> coverage is not in the formula.
    assert a["cidi"] == b["cidi"]


def test_calculate_cidi_validates_units_and_weights():
    assert calculate_cidi(0.5, 0.5, 0.5, 0.5) == pytest.approx(0.5)
    with pytest.raises(ValueError):
        calculate_cidi(1.5, 0.5, 0.5, 0.5)
    with pytest.raises(ValueError):
        calculate_cidi(0.5, 0.5, 0.4, 0.4)   # alpha+beta != 1


def test_no_quoted_romania_in_source():
    src = Path(ci.__file__).read_text()
    assert '"Romania"' not in src and "'Romania'" not in src


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
