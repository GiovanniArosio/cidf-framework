"""
Tests for the Technical–Public Gap diagnostic (declassified).
============================================================
Proves:
  * the module exports NO single aggregate/composite for IVA/CIDI use;
  * it is explicitly flagged as exploratory/diagnostic-only;
  * the length component reports mean words PER DOCUMENT (not sentence length
    and not "complexity");
  * a near-ceiling Jaccard distance raises an interpretability warning.

Run:  pytest tests/test_technical_public_gap.py

Part of the CIDF framework — LUISS Guido Carli, 2026
Author: Giovanni Arosio
"""

import json
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import iva.technical_public_gap as tpg


class _FakeEncoder:
    def encode(self, texts, show_progress_bar=False):
        # Distinct deterministic centroids for the two sets.
        return np.array([[float(len(t) % 7), 1.0, 0.0] for t in texts])


@pytest.fixture(autouse=True)
def _patch_model(monkeypatch):
    monkeypatch.setattr(tpg, "_get_model", lambda: _FakeEncoder())


def _corpus(tmp_path, name, texts):
    d = tmp_path / name
    d.mkdir()
    for i, t in enumerate(texts):
        (d / f"{name}_{i}.json").write_text(
            json.dumps({"doc_id": f"{name}_{i}", "text": t}), encoding="utf-8")
    return str(d)


def test_no_aggregate_exported(tmp_path):
    tech = _corpus(tmp_path, "technical", ["alpha beta gamma delta epsilon"] * 3)
    pub = _corpus(tmp_path, "public", ["one two three"] * 3)
    res = tpg.diagnose_technical_public_gap(tech, pub)
    assert res["included_in_aggregate"] is False
    assert res["status"] == "exploratory_diagnostic_only"
    # No composite/aggregate score key anywhere in the result.
    assert "composite" not in res
    assert "score" not in res
    assert not any("composite" in k for k in res)


def test_module_has_no_calculate_function():
    # The old public scoring entrypoint must be gone.
    assert not hasattr(tpg, "calculate_technical_public_gap")


def test_length_component_is_words_per_document(tmp_path):
    tech = _corpus(tmp_path, "technical", ["w " * 80])   # ~80 words/doc
    pub = _corpus(tmp_path, "public", ["w " * 50])       # ~50 words/doc
    res = tpg.diagnose_technical_public_gap(tech, pub)
    length = res["components"]["document_length_differential"]
    assert "mean_words_technical" in length
    assert "mean_words_public" in length
    assert round(length["mean_words_technical"]) == 80
    assert round(length["mean_words_public"]) == 50


def test_near_ceiling_jaccard_warns(tmp_path):
    # Disjoint vocabularies -> Jaccard distance ~1.0 (near ceiling).
    tech = _corpus(tmp_path, "technical", ["aaa bbb ccc ddd"] * 3)
    pub = _corpus(tmp_path, "public", ["xxx yyy zzz www"] * 3)
    res = tpg.diagnose_technical_public_gap(tech, pub)
    assert res["components"]["jaccard_distance"] >= tpg.JACCARD_CEILING
    assert any("near ceiling" in w for w in res["warnings"])


def test_context_preincident_excluded(tmp_path):
    tech = _corpus(tmp_path, "technical", ["alpha beta gamma"] * 3)
    pubd = tmp_path / "public"
    pubd.mkdir()
    for i in range(3):
        (pubd / f"p_{i}.json").write_text(
            json.dumps({"doc_id": f"p_{i}", "text": "one two three"}), encoding="utf-8")
    (pubd / "ctx.json").write_text(
        json.dumps({"doc_id": "ctx", "text": "pre-incident context",
                    "analysis_role": "context_preincident"}), encoding="utf-8")
    res = tpg.diagnose_technical_public_gap(tech, str(pubd))
    assert res["n_public_docs"] == 3  # context document excluded


def test_always_carries_diagnostic_caveat(tmp_path):
    tech = _corpus(tmp_path, "technical", ["alpha beta"] * 2)
    pub = _corpus(tmp_path, "public", ["alpha gamma"] * 2)
    res = tpg.diagnose_technical_public_gap(tech, pub)
    assert any("DIAGNOSTIC ONLY" in w for w in res["warnings"])


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
