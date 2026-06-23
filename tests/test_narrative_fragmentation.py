"""
Tests for Narrative Fragmentation (exploratory, embedding-based K-Means).
========================================================================
Proves:
  * the module is labelled embedding-based K-Means clustering, NOT BERTopic;
  * results are deterministic (fixed random state);
  * the k = 3/4/5 sensitivity routine runs and is reported;
  * the exploratory small-corpus caveat is surfaced.

A lightweight deterministic fake encoder is injected so the tests do not
require the sentence-transformer model download and stay fast.

Run:  pytest tests/test_narrative_fragmentation.py

Part of the CIDF framework — LUISS Guido Carli, 2026
Author: Giovanni Arosio
"""

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import iva.narrative_fragmentation as nf


class _FakeEncoder:
    """Deterministic text -> vector encoder (no model download)."""

    def encode(self, texts, show_progress_bar=False):
        vecs = []
        for t in texts:
            h = hashlib.sha256(t.encode("utf-8")).digest()
            seed = int.from_bytes(h[:4], "big")
            rng = np.random.default_rng(seed)
            vecs.append(rng.normal(size=16))
        return np.array(vecs)


@pytest.fixture(autouse=True)
def _patch_model(monkeypatch):
    monkeypatch.setattr(nf, "_get_model", lambda: _FakeEncoder())


def _corpus(tmp_path, n):
    d = tmp_path / "public"
    d.mkdir()
    for i in range(n):
        (d / f"doc_{i:03d}.json").write_text(
            json.dumps({"doc_id": f"d{i}", "text": f"narrative variant number {i} "
                        f"about a cyber incident and its public framing"}),
            encoding="utf-8",
        )
    return str(d)


def test_method_label_is_kmeans_not_bertopic(tmp_path):
    res = nf.analyze_narrative_fragmentation(_corpus(tmp_path, 15))
    assert res["method"] == "embedding-based K-Means clustering"
    assert "bertopic" not in res["method"].lower()


def test_module_source_does_not_claim_bertopic():
    src = Path(nf.__file__).read_text(encoding="utf-8").lower()
    # The module must carry an explicit "does not use BERTopic" disclaimer ...
    assert "does not use bertopic" in src or "not use bertopic" in src
    # ... and must NOT contain the old affirmative-use phrasing.
    for affirmative in ("bertopic topic modeling", "using bertopic", "uses bertopic"):
        assert affirmative not in src


def test_sensitivity_covers_k_3_4_5(tmp_path):
    res = nf.analyze_narrative_fragmentation(_corpus(tmp_path, 15))
    ks = [s["k"] for s in res["sensitivity"]]
    assert ks == [3, 4, 5]
    assert res["sensitivity_k"] == [3, 4, 5]


def test_deterministic(tmp_path):
    path = _corpus(tmp_path, 15)
    a = nf.analyze_narrative_fragmentation(path)
    b = nf.analyze_narrative_fragmentation(path)
    assert a["score"] == b["score"]
    assert [s["score"] for s in a["sensitivity"]] == [s["score"] for s in b["sensitivity"]]


def test_exploratory_caveat_present(tmp_path):
    res = nf.analyze_narrative_fragmentation(_corpus(tmp_path, 15))
    assert any("exploratory" in w.lower() for w in res["warnings"])
    assert any("summaries" in w.lower() for w in res["warnings"])


def test_unavailable_for_tiny_corpus(tmp_path):
    res = nf.analyze_narrative_fragmentation(_corpus(tmp_path, 2))
    assert res["available"] is False
    assert "2 documents" in res["reason"]


def test_context_preincident_excluded(tmp_path):
    d = tmp_path / "public"
    d.mkdir()
    for i in range(15):
        (d / f"doc_{i:03d}.json").write_text(
            json.dumps({"doc_id": f"d{i}", "text": f"variant {i} cyber incident framing"}),
            encoding="utf-8")
    (d / "ctx.json").write_text(
        json.dumps({"doc_id": "ctx", "text": "pre-incident context material",
                    "analysis_role": "context_preincident"}), encoding="utf-8")
    res = nf.analyze_narrative_fragmentation(str(d))
    assert res["n_documents"] == 15  # context document excluded


def test_score_in_range(tmp_path):
    res = nf.analyze_narrative_fragmentation(_corpus(tmp_path, 15))
    assert 0.0 <= res["score"] <= 1.0
    for s in res["sensitivity"]:
        assert 0.0 <= s["score"] <= 1.0


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
