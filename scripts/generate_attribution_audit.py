#!/usr/bin/env python3
"""
Generate the attribution coding audit CSV
=========================================
Reads the attribution coding directly from the active public corpus JSON
documents (the single source of truth) and writes
``data/attribution_coding_audit.csv``. Generating the CSV from the JSONs
guarantees the audit table can never silently diverge from the data.

Usage:
    python scripts/generate_attribution_audit.py

Part of the CIDF framework — LUISS Guido Carli, 2026
Author: Giovanni Arosio
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from utils.corpus_schema import ATTRIBUTION_FIELDS  # noqa: E402

PUBLIC_GLOBS = (
    ("notpetya", "data/notpetya/public/*.json"),
    ("kasat_viasat", "data/kasat_viasat/public/*.json"),
    ("pap_hack", "data/pap_hack/public/*.json"),
)

HEADER = [
    "case", "doc_id", "date", "source_type", "source_name", "analysis_role",
    *ATTRIBUTION_FIELDS,
]


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    out_path = root / "data" / "attribution_coding_audit.csv"

    rows = []
    for case, pattern in PUBLIC_GLOBS:
        for path in sorted(root.glob(pattern)):
            d = json.loads(path.read_text(encoding="utf-8"))
            rows.append({
                "case": case,
                "doc_id": d.get("doc_id") or d.get("id"),
                "date": d.get("date"),
                "source_type": d.get("source_type"),
                "source_name": d.get("source_name") or d.get("source"),
                "analysis_role": d.get("analysis_role", "analysis"),
                **{f: d.get(f) for f in ATTRIBUTION_FIELDS},
            })

    rows.sort(key=lambda r: (r["case"], r["date"], r["doc_id"]))

    with out_path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=HEADER)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote {len(rows)} rows to {out_path.relative_to(root)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
