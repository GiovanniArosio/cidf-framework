"""
Tests for the structured Attribution Drift module.
===================================================
Proves the keyword-era failure modes are gone:
  * ordinary words ("platform", "place", "explains") cannot create a China
    attribution;
  * actor selection is deterministic, never from unordered set iteration;
  * no_claim documents do not inflate actor plurality;
  * malformed / missing attribution coding is rejected or excluded explicitly;
  * the legacy ``state_actor`` pseudo-actor is not a valid category.

Run:  pytest tests/test_attribution_drift.py

Part of the CIDF framework — LUISS Guido Carli, 2026
Author: Giovanni Arosio
"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from iva.attribution_drift import (
    AttributionCodingError,
    analyze_attribution_drift,
    calculate_attribution_drift,
)
from utils.corpus_schema import CorpusValidationError, validate_attribution_payload


def _doc(doc_id, date, text, state, actor, confidence, basis, note="grounded note",
         source_type="mainstream"):
    return {
        "doc_id": doc_id,
        "case": "synthetic",
        "source_type": source_type,
        "source_name": "Test Source",
        "date": date,
        "text": text,
        "url": "https://example.test/" + doc_id,
        "attribution_state": state,
        "attribution_actor": actor,
        "attribution_confidence": confidence,
        "attribution_basis": basis,
        "attribution_coding_note": note,
    }


def _write_corpus(tmp_path, docs):
    d = tmp_path / "public"
    d.mkdir()
    for doc in docs:
        (d / f"{doc['doc_id']}.json").write_text(json.dumps(doc), encoding="utf-8")
    return str(d)


# --------------------------------------------------------------------------
def test_ordinary_words_cannot_create_china_attribution(tmp_path):
    """Texts full of 'platform'/'place'/'explains' coded no_claim => no China."""
    docs = [
        _doc("d1", "2024-01-01",
             "The platform explains that this took place on a large scale.",
             "no_claim", "none", "none", "no_claim"),
        _doc("d2", "2024-01-02",
             "Analysts explain the malware replaced files in many places.",
             "no_claim", "none", "none", "no_claim"),
        _doc("d3", "2024-01-03",
             "A spokesperson explains the platform was offline.",
             "no_claim", "none", "none", "no_claim"),
    ]
    res = analyze_attribution_drift(_write_corpus(tmp_path, docs))
    plurality = res["components"]["actor_plurality"]
    assert "china" not in plurality["distinct_actors"]
    assert plurality["distinct_actor_count"] == 0
    assert res["claim_actor_counts"] == {}


def test_no_claim_docs_do_not_inflate_plurality(tmp_path):
    """Many no_claim docs + one attributed russia => exactly one actor."""
    docs = [
        _doc("d1", "2024-01-01", "China platform place explains.",
             "no_claim", "none", "none", "no_claim"),
        _doc("d2", "2024-01-02", "Iran explains the place.",
             "no_claim", "none", "none", "no_claim"),
        _doc("d3", "2024-01-03", "Officials blamed Russia.",
             "attributed", "russia", "high", "official_attribution"),
        _doc("d4", "2024-01-04", "More context, no actor named.",
             "no_claim", "none", "none", "no_claim"),
    ]
    res = analyze_attribution_drift(_write_corpus(tmp_path, docs))
    plurality = res["components"]["actor_plurality"]
    assert plurality["distinct_actors"] == ["russia"]
    assert plurality["distinct_actor_count"] == 1
    assert plurality["score"] == 0.0  # single actor => no plurality drift


def test_actor_selection_is_deterministic_not_set_ordered(tmp_path):
    """Tied actors resolve deterministically (alphabetical), and repeated runs
    produce identical output — never order-of-set dependent."""
    docs = [
        _doc("d1", "2024-01-01", "x", "attributed", "russia", "high",
             "official_attribution"),
        _doc("d2", "2024-01-02", "x", "attributed", "china", "high",
             "technical_assessment"),
        _doc("d3", "2024-01-03", "x", "attributed", "iran", "high",
             "technical_assessment"),
    ]
    path = _write_corpus(tmp_path, docs)
    runs = [analyze_attribution_drift(path) for _ in range(5)]
    dominants = {r["components"]["convergence_delay"]["dominant_actor"] for r in runs}
    assert dominants == {"china"}  # alphabetical tie-break, stable
    # Full determinism of the composite score.
    assert len({r["composite_score"] for r in runs}) == 1
    # Three distinct actors => maximal plurality.
    assert runs[0]["components"]["actor_plurality"]["distinct_actor_count"] == 3
    assert runs[0]["components"]["actor_plurality"]["score"] == 1.0


def test_unknown_actor_handled_explicitly_not_as_distinct_actor(tmp_path):
    docs = [
        _doc("d1", "2024-01-01", "state-attributed incident, no actor named",
             "attributed", "unknown", "low", "investigative_reporting"),
        _doc("d2", "2024-01-02", "officials blamed Russia",
             "attributed", "russia", "high", "official_attribution"),
    ]
    res = analyze_attribution_drift(_write_corpus(tmp_path, docs))
    plurality = res["components"]["actor_plurality"]
    assert plurality["distinct_actors"] == ["russia"]
    assert plurality["unidentified_claim_count"] == 1


def test_malformed_coding_is_rejected(tmp_path):
    docs = [
        _doc("d1", "2024-01-01", "x", "attributed", "russia", "high",
             "official_attribution"),
    ]
    path = _write_corpus(tmp_path, docs)
    # Corrupt the coding: invalid state value.
    bad = json.loads((Path(path) / "d1.json").read_text())
    bad["attribution_state"] = "state_actor"  # not a valid state, not an actor
    (Path(path) / "d1.json").write_text(json.dumps(bad))
    with pytest.raises(AttributionCodingError):
        analyze_attribution_drift(path)


def test_state_actor_is_not_a_valid_actor_category():
    """The legacy 'state_actor' pseudo-actor must be rejected outright."""
    with pytest.raises(CorpusValidationError):
        validate_attribution_payload({
            "attribution_state": "attributed",
            "attribution_actor": "state_actor",
            "attribution_confidence": "high",
            "attribution_basis": "official_attribution",
            "attribution_coding_note": "n",
        }, doc_id="x")


def test_missing_coding_excluded_and_scalar_requires_full_coverage(tmp_path):
    coded = _doc("d1", "2024-01-01", "x", "attributed", "russia", "high",
                 "official_attribution")
    uncoded = {
        "doc_id": "d2", "case": "synthetic", "source_type": "mainstream",
        "source_name": "S", "date": "2024-01-02", "text": "no coding here",
        "url": "https://example.test/d2",
    }
    path = _write_corpus(tmp_path, [coded, uncoded])
    res = analyze_attribution_drift(path)
    assert res["available"] is True
    assert res["coding_coverage"] < 1.0
    assert any("coverage" in w for w in res["warnings"])
    with pytest.raises(AttributionCodingError):
        calculate_attribution_drift(path)


def test_no_claim_only_corpus_reports_no_convergence(tmp_path):
    docs = [
        _doc("d1", "2024-01-01", "x", "no_claim", "none", "none", "no_claim"),
        _doc("d2", "2024-01-02", "y", "no_claim", "none", "none", "no_claim"),
    ]
    res = analyze_attribution_drift(_write_corpus(tmp_path, docs))
    delay = res["components"]["convergence_delay"]
    assert delay["dominant_actor"] is None
    assert delay["score"] == 1.0


def test_active_corpora_scores_in_range_and_fully_coded():
    root = Path(__file__).resolve().parents[1]
    for case in ("notpetya", "kasat_viasat", "pap_hack"):
        res = analyze_attribution_drift(str(root / "data" / case / "public"))
        assert res["available"] is True
        assert res["coding_coverage"] == 1.0
        assert 0.0 <= res["composite_score"] <= 1.0
        # All three cases converge on a single identified actor (russia).
        assert res["components"]["actor_plurality"]["distinct_actors"] == ["russia"]


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
