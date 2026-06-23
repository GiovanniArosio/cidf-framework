"""
Tests for the Mainstream–Institutional Response Timing Proxy.
============================================================
Proves:
  * the metric is no longer framed as "non-institutional amplification";
  * source groups are explicit; technical is kept separate from official;
  * the peak metric is NOT normalized by total corpus size;
  * insufficient early-window evidence yields an explicit unavailable state
    with a reason — never an imputed 0.5 fallback;
  * the active KA-SAT corpus (no early-window docs) is correctly unavailable.

Run:  pytest tests/test_response_timing.py

Part of the CIDF framework — LUISS Guido Carli, 2026
Author: Giovanni Arosio
"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import iva.amplification_velocity as rt
from iva.amplification_velocity import (
    analyze_response_timing,
    calculate_response_timing_proxy,
)


def _doc(doc_id, date, source_type):
    return {
        "doc_id": doc_id, "case": "synthetic", "source_type": source_type,
        "source_name": "S", "date": date, "text": "t",
        "url": "https://example.test/" + doc_id,
    }


def _corpus(tmp_path, docs):
    d = tmp_path / "public"
    d.mkdir()
    for doc in docs:
        (d / f"{doc['doc_id']}.json").write_text(json.dumps(doc), encoding="utf-8")
    return str(d)


def test_module_is_not_amplification_framed(tmp_path):
    src = Path(rt.__file__).read_text(encoding="utf-8").lower()
    assert "response timing proxy" in src
    assert "formerly" in src  # carries the reframing disclaimer
    # The output method label is the proxy, not amplification.
    docs = [_doc("m1", "2024-01-01", "mainstream"),
            _doc("i1", "2024-01-01", "institutional")]
    res = analyze_response_timing(_corpus(tmp_path, docs), "2024-01-01")
    assert res["method"] == "mainstream_institutional_response_timing_proxy"


def test_groups_are_explicit_and_technical_separate():
    assert rt.OFFICIAL_SOURCES == frozenset({"institutional"})
    assert rt.PUBLIC_FACING_SOURCES == frozenset({"mainstream", "non_institutional"})
    assert rt.TECHNICAL_SOURCES == frozenset({"technical"})
    # technical must not be in either comparison group
    assert not (rt.TECHNICAL_SOURCES & rt.OFFICIAL_SOURCES)
    assert not (rt.TECHNICAL_SOURCES & rt.PUBLIC_FACING_SOURCES)


def test_unavailable_when_no_early_window_docs(tmp_path):
    # All docs well after the early window.
    docs = [
        _doc("a", "2024-02-01", "mainstream"),
        _doc("b", "2024-02-02", "institutional"),
    ]
    path = _corpus(tmp_path, docs)
    res = analyze_response_timing(path, "2024-01-01")
    assert res["available"] is False
    assert "early window" in res["reason"]
    assert res["proxy_score"] is None
    with pytest.raises(ValueError):
        calculate_response_timing_proxy(path, "2024-01-01")


def test_no_0_5_fallback_in_source():
    src = Path(rt.__file__).read_text(encoding="utf-8")
    # The old code imputed 0.5 for missing observations; ensure it's gone.
    assert "0.5" not in src
    assert "return 0.5" not in src


def test_technical_not_counted_as_official_or_public(tmp_path):
    docs = [
        _doc("m1", "2024-01-01", "mainstream"),
        _doc("i1", "2024-01-02", "institutional"),
        _doc("t1", "2024-01-01", "technical"),
    ]
    res = analyze_response_timing(_corpus(tmp_path, docs), "2024-01-01")
    diag = res["diagnostics"]
    assert diag["group_counts"]["technical"] == 1
    assert diag["group_counts"]["official"] == 1
    assert diag["group_counts"]["public_facing"] == 1
    # early-window composition keeps technical out of the official/public split
    assert res["components"]["early_public_share"]["early_official"] == 1
    assert res["components"]["early_public_share"]["early_public_facing"] == 1


def test_peak_concentration_not_corpus_size_normalized(tmp_path):
    # 3 mainstream on the same day, 1 institutional, plus many later institutional
    docs = [
        _doc("m1", "2024-01-01", "mainstream"),
        _doc("m2", "2024-01-01", "mainstream"),
        _doc("m3", "2024-01-01", "mainstream"),
        _doc("i1", "2024-01-02", "institutional"),
        _doc("i2", "2024-02-01", "institutional"),
        _doc("i3", "2024-03-01", "institutional"),
    ]
    res = analyze_response_timing(_corpus(tmp_path, docs), "2024-01-01")
    diag = res["diagnostics"]
    # peak concentration = peak_count / public_facing_count = 3/3 = 1.0,
    # independent of the 6-document corpus size.
    assert diag["peak_public_count"] == 3
    assert diag["peak_public_concentration"] == 1.0


def test_active_kasat_corpus_is_unavailable():
    root = Path(__file__).resolve().parents[1]
    res = analyze_response_timing(str(root / "data/kasat_viasat/public"), "2022-02-24")
    assert res["available"] is False
    assert "early window" in res["reason"]


def test_active_notpetya_available_and_in_range():
    root = Path(__file__).resolve().parents[1]
    res = analyze_response_timing(str(root / "data/notpetya/public"), "2017-06-27")
    assert res["available"] is True
    assert 0.0 <= res["proxy_score"] <= 1.0
    assert res["diagnostics"]["non_institutional_count"] == 0


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
