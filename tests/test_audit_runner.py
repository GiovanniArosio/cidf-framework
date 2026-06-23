"""
Tests for the audit runner's CIDI structure and ranking-stability logic.
=======================================================================
Proves (model-free, using synthetic per-component inputs):
  9.  The audit output exposes Core and Extended scenario sections rather than a
      single definitive `cidi` field.
 10.  Ranking-stability logic reports stable vs changed ordering correctly, with
      no causal claim, and Extended ranking excludes cases without timing.

Run:  pytest tests/test_audit_runner.py

Part of the CIDF framework — LUISS Guido Carli, 2026
Author: Giovanni Arosio
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cidi.cidi_integrator import CORE_SCENARIOS, EXTENDED_SCENARIOS
from scripts.run_methodology_audit import cidi_for_case, _scenario_ranking


def _tci(ev, cov=0.6):
    return {"evidence_adjusted_score": ev, "evidence_coverage": cov}


def _ad(score):
    return {"available": True, "composite_score": score}


def _nf(score):
    return {"available": True, "score": score}


def _rt(score):
    if score is None:
        return {"available": False, "reason": "no early-window docs"}
    return {"available": True, "proxy_score": score}


def _case(label, tci_ev, ad, nf, rt):
    return {
        "label": label,
        "cidi_synthesis": cidi_for_case(_tci(tci_ev), _ad(ad), _nf(nf), _rt(rt)),
    }


def test_output_has_core_and_extended_sections_not_single_cidi():
    res = cidi_for_case(_tci(0.66, 0.8), _ad(0.291), _nf(0.646), _rt(0.422))
    assert "cidi_core_scenarios" in res
    assert "cidi_extended_scenarios" in res
    assert "ivc_core" in res
    assert "cidi" not in res  # no single definitive value
    assert set(res["cidi_core_scenarios"]) == {sc.name for sc in CORE_SCENARIOS}
    assert set(res["cidi_extended_scenarios"]) == {sc.name for sc in EXTENDED_SCENARIOS}


def test_extended_unavailable_when_timing_missing_core_still_available():
    res = cidi_for_case(_tci(0.55, 0.6), _ad(0.174), _nf(0.509), _rt(None))
    for sc in CORE_SCENARIOS:
        assert res["cidi_core_scenarios"][sc.name]["available"] is True
    for sc in EXTENDED_SCENARIOS:
        ex = res["cidi_extended_scenarios"][sc.name]
        assert ex["available"] is False
        assert "response_timing_proxy" in ex["reason"]


def test_ranking_stable_when_one_case_dominates():
    cases = {
        "a": _case("A", 0.7, 0.3, 0.6, 0.4),
        "b": _case("B", 0.3, 0.1, 0.2, 0.1),
    }
    rk = _scenario_ranking(cases, CORE_SCENARIOS)
    assert rk["ranking_stable"] is True
    assert all(order == ["A", "B"] for order in rk["orderings"].values())
    assert "causal" in rk["note"].lower()  # explicitly no causal claim


def test_ranking_changes_when_weighting_flips_order():
    # X: high TCI, low IVC; Y: low TCI, high IVC -> order flips across scenarios.
    cases = {
        "x": _case("X", 0.9, 0.1, 0.1, 0.1),
        "y": _case("Y", 0.2, 0.9, 0.9, 0.9),
    }
    rk = _scenario_ranking(cases, CORE_SCENARIOS)
    assert rk["ranking_stable"] is False
    # technical-prioritized favors X; interpretive-prioritized favors Y.
    assert rk["orderings"]["core_technical_prioritized"][0] == "X"
    assert rk["orderings"]["core_interpretive_prioritized"][0] == "Y"


def test_extended_ranking_excludes_cases_without_timing():
    cases = {
        "a": _case("A", 0.66, 0.29, 0.65, 0.42),
        "b": _case("B", 0.55, 0.17, 0.51, None),   # no timing -> extended N/A
        "c": _case("C", 0.25, 0.11, 0.60, 0.17),
    }
    rk = _scenario_ranking(cases, EXTENDED_SCENARIOS)
    assert "B" not in rk["cases_included"]
    assert set(rk["cases_included"]) == {"A", "C"}
    for order in rk["orderings"].values():
        assert "B" not in order


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-v"]))
