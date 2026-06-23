"""
Tests for the structured Attribution Drift module (corrected uncertainty +
convergence + pre-incident context exclusion).
==========================================================================
Proves:
  * ordinary words ("platform"/"place"/"explains") cannot create a China
    attribution; no actor from unordered set iteration;
  * no_claim documents do not inflate plurality and do not alter the transition
    sequence;
  * uncertain/unknown documents appear explicitly in the attribution-related
    sequence and `unknown -> russia` raises temporal instability;
  * a first Russia attribution is NOT automatically convergence; three
    consecutive same-actor documents converge only on the THIRD;
  * context_preincident documents are excluded from event-level metrics;
  * malformed / missing coding is rejected or excluded explicitly; the legacy
    `state_actor` pseudo-actor is not a valid category.

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
         source_type="mainstream", analysis_role="analysis"):
    return {
        "doc_id": doc_id, "case": "synthetic", "source_type": source_type,
        "source_name": "Test Source", "date": date, "text": text,
        "url": "https://example.test/" + doc_id,
        "analysis_role": analysis_role,
        "attribution_state": state, "attribution_actor": actor,
        "attribution_confidence": confidence, "attribution_basis": basis,
        "attribution_coding_note": note,
    }


def _write_corpus(tmp_path, docs):
    d = Path(tmp_path) / "public"
    d.mkdir(parents=True, exist_ok=True)
    for doc in docs:
        (d / f"{doc['doc_id']}.json").write_text(json.dumps(doc), encoding="utf-8")
    return str(d)


def _russia(doc_id, date, conf="high"):
    return _doc(doc_id, date, "officials blamed Russia", "attributed", "russia",
                conf, "official_attribution")


def _unknown(doc_id, date):
    return _doc(doc_id, date, "investigation ongoing, origin unknown",
                "uncertain", "unknown", "none", "investigative_reporting")


def _no_claim(doc_id, date):
    return _doc(doc_id, date, "platform explains the place; damage described",
                "no_claim", "none", "none", "no_claim")


# --------------------------------------------------------------------------
def test_ordinary_words_cannot_create_china_attribution(tmp_path):
    docs = [_no_claim("d1", "2024-01-01"), _no_claim("d2", "2024-01-02"),
            _no_claim("d3", "2024-01-03")]
    res = analyze_attribution_drift(_write_corpus(tmp_path, docs))
    pl = res["components"]["actor_plurality"]
    assert "china" not in pl["distinct_actors"]
    assert pl["distinct_actor_count"] == 0
    assert res["attribution_related_sequence"] == []


def test_no_claim_docs_do_not_inflate_plurality(tmp_path):
    docs = [_no_claim("d1", "2024-01-01"), _no_claim("d2", "2024-01-02"),
            _russia("d3", "2024-01-03"), _no_claim("d4", "2024-01-04")]
    res = analyze_attribution_drift(_write_corpus(tmp_path, docs))
    pl = res["components"]["actor_plurality"]
    assert pl["distinct_actors"] == ["russia"]
    assert pl["score"] == 0.0


def test_no_claim_docs_do_not_alter_transition_sequence(tmp_path):
    """no_claim docs interleaved must not change the attribution-related
    sequence or the instability transitions."""
    plain = [_russia("a1", "2024-01-01"), _russia("a2", "2024-01-02"),
             _russia("a3", "2024-01-03")]
    interleaved = [_russia("b1", "2024-01-01"), _no_claim("b2", "2024-01-02"),
                   _russia("b3", "2024-01-03"), _no_claim("b4", "2024-01-04"),
                   _russia("b5", "2024-01-05")]
    r_plain = analyze_attribution_drift(_write_corpus(tmp_path / "p", plain))
    r_inter = analyze_attribution_drift(_write_corpus(tmp_path / "i", interleaved))
    seq_plain = [x["actor"] for x in r_plain["attribution_related_sequence"]]
    seq_inter = [x["actor"] for x in r_inter["attribution_related_sequence"]]
    assert seq_plain == ["russia", "russia", "russia"]
    assert seq_inter == ["russia", "russia", "russia"]
    assert r_plain["components"]["temporal_instability"]["transitions"] == 0
    assert r_inter["components"]["temporal_instability"]["transitions"] == 0


def test_unknown_to_russia_raises_temporal_instability(tmp_path):
    docs = [_unknown("d1", "2024-01-01"), _russia("d2", "2024-01-02"),
            _russia("d3", "2024-01-03"), _russia("d4", "2024-01-04")]
    res = analyze_attribution_drift(_write_corpus(tmp_path, docs))
    inst = res["components"]["temporal_instability"]
    assert inst["score"] > 0.0
    assert "unknown->russia" in inst["transition_pairs"]
    # unknown appears explicitly in the sequence and is reported as unresolved.
    assert [x["actor"] for x in res["attribution_related_sequence"]][0] == "unknown"
    assert res["unresolved_claim_count"] == 1


def test_first_russia_attribution_is_not_convergence(tmp_path):
    """A single (or non-tripled) Russia attribution must NOT count as
    convergence."""
    docs = [_russia("d1", "2024-01-01"), _unknown("d2", "2024-01-02"),
            _russia("d3", "2024-01-03"), _unknown("d4", "2024-01-04")]
    res = analyze_attribution_drift(_write_corpus(tmp_path, docs))
    conv = res["components"]["convergence_delay"]
    assert conv["converged"] is False
    assert conv["score"] is None
    assert any("non-convergence maximum" in w for w in res["warnings"])


def test_three_consecutive_russia_converges_on_third(tmp_path):
    docs = [_russia("d1", "2024-01-01"), _russia("d2", "2024-01-02"),
            _russia("d3", "2024-01-03"), _russia("d4", "2024-01-04")]
    res = analyze_attribution_drift(_write_corpus(tmp_path, docs))
    conv = res["components"]["convergence_delay"]
    assert conv["converged"] is True
    assert conv["converged_actor"] == "russia"
    assert conv["convergence_doc_id"] == "d3"        # the THIRD confirming doc
    assert conv["convergence_date"] == "2024-01-03"
    assert conv["raw_days"] == 2                       # 01-01 -> 01-03


def test_intervening_unknown_delays_convergence(tmp_path):
    docs = [_russia("d1", "2024-01-01"), _unknown("d2", "2024-01-02"),
            _russia("d3", "2024-01-03"), _russia("d4", "2024-01-04"),
            _russia("d5", "2024-01-05")]
    res = analyze_attribution_drift(_write_corpus(tmp_path, docs))
    conv = res["components"]["convergence_delay"]
    # First run of three consecutive russia is d3,d4,d5 -> convergence on d5.
    assert conv["converged"] is True
    assert conv["convergence_doc_id"] == "d5"


def test_context_preincident_excluded_from_metrics(tmp_path):
    docs = [
        _doc("ctx", "2023-12-01", "pre-incident pattern context",
             "attributed", "russia", "medium", "technical_assessment",
             analysis_role="context_preincident"),
        _russia("d1", "2024-01-01"),
        _unknown("d2", "2024-01-02"),
    ]
    res = analyze_attribution_drift(_write_corpus(tmp_path, docs))
    assert res["excluded_context_count"] == 1
    assert res["in_scope_document_count"] == 2
    # The context document's date must not appear in the in-scope sequence.
    dates = [x["date"] for x in res["attribution_related_sequence"]]
    assert "2023-12-01" not in dates


def test_unknown_actor_not_a_distinct_actor(tmp_path):
    docs = [_unknown("d1", "2024-01-01"), _russia("d2", "2024-01-02")]
    res = analyze_attribution_drift(_write_corpus(tmp_path, docs))
    pl = res["components"]["actor_plurality"]
    assert pl["distinct_actors"] == ["russia"]
    assert pl["unidentified_claim_count"] == 1


def test_deterministic(tmp_path):
    docs = [_russia("d1", "2024-01-01"), _unknown("d2", "2024-01-02"),
            _russia("d3", "2024-01-03"), _russia("d4", "2024-01-04"),
            _russia("d5", "2024-01-05")]
    path = _write_corpus(tmp_path, docs)
    runs = [analyze_attribution_drift(path) for _ in range(5)]
    assert len({r["composite_score"] for r in runs}) == 1
    seqs = {tuple(x["actor"] for x in r["attribution_related_sequence"]) for r in runs}
    assert len(seqs) == 1


def test_malformed_coding_is_rejected(tmp_path):
    docs = [_russia("d1", "2024-01-01")]
    path = _write_corpus(tmp_path, docs)
    bad = json.loads((Path(path) / "d1.json").read_text())
    bad["attribution_state"] = "state_actor"
    (Path(path) / "d1.json").write_text(json.dumps(bad))
    with pytest.raises(AttributionCodingError):
        analyze_attribution_drift(path)


def test_state_actor_is_not_a_valid_actor_category():
    with pytest.raises(CorpusValidationError):
        validate_attribution_payload({
            "attribution_state": "attributed", "attribution_actor": "state_actor",
            "attribution_confidence": "high",
            "attribution_basis": "official_attribution",
            "attribution_coding_note": "n",
        }, doc_id="x")


def test_missing_coding_excluded_and_scalar_requires_full_coverage(tmp_path):
    coded = _russia("d1", "2024-01-01")
    uncoded = {"doc_id": "d2", "case": "synthetic", "source_type": "mainstream",
               "source_name": "S", "date": "2024-01-02", "text": "no coding",
               "url": "https://example.test/d2"}
    path = _write_corpus(tmp_path, [coded, uncoded])
    res = analyze_attribution_drift(path)
    assert res["available"] is True
    assert res["coding_coverage"] < 1.0
    with pytest.raises(AttributionCodingError):
        calculate_attribution_drift(path)


def test_active_corpora_sequences_and_context_counts():
    root = Path(__file__).resolve().parents[1]
    expected_inscope = {"notpetya": 15, "kasat_viasat": 15, "pap_hack": 14}
    expected_ctx = {"notpetya": 0, "kasat_viasat": 0, "pap_hack": 1}
    for case in ("notpetya", "kasat_viasat", "pap_hack"):
        res = analyze_attribution_drift(str(root / "data" / case / "public"))
        assert res["available"] is True
        assert res["coding_coverage"] == 1.0
        assert res["in_scope_document_count"] == expected_inscope[case]
        assert res["excluded_context_count"] == expected_ctx[case]
        assert res["components"]["actor_plurality"]["distinct_actors"] == ["russia"]
        assert 0.0 <= res["composite_score"] <= 1.0
    # KA-SAT begins with two unresolved (unknown) attribution-related docs.
    kasat = analyze_attribution_drift(str(root / "data/kasat_viasat/public"))
    assert [x["actor"] for x in kasat["attribution_related_sequence"]][:2] == \
        ["unknown", "unknown"]
    assert kasat["components"]["convergence_delay"]["converged"] is True


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
