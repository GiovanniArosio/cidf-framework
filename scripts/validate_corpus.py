#!/usr/bin/env python3
"""
Corpus validation command
==========================
Validates the active CIDF corpora against the canonical schema and the
attribution coding protocol, using the non-destructive adapter in
``utils.corpus_schema`` (repository-native ``doc_id`` / ``source_name``
documents are accepted as-is).

Checks performed per document:
  * JSON syntax
  * required fields resolvable (directly or via alias)
  * ``source_type`` is one of the controlled vocabulary values
  * unsupported / unexpected fields are flagged (not rejected)
  * for PUBLIC corpus documents: attribution coding present and valid

Excluded / archived cases under ``data/_excluded_cases`` are ignored by
default and only scanned with ``--include-excluded``.

Usage:
    python scripts/validate_corpus.py
    python scripts/validate_corpus.py --data-dir data --include-excluded
    python scripts/validate_corpus.py --json        # machine-readable report

Exit code is non-zero if any error-level finding is present.

Part of the CIDF framework — LUISS Guido Carli, 2026
Author: Giovanni Arosio
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from utils.corpus_schema import (  # noqa: E402
    CorpusDocument,
    CorpusValidationError,
    unsupported_fields,
)

ACTIVE_CASES = ("notpetya", "kasat_viasat", "pap_hack")
EXCLUDED_DIR_NAME = "_excluded_cases"


@dataclass
class FileReport:
    path: str
    case: str
    layer: str  # "public" | "technical"
    doc_id: str | None = None
    source_type: str | None = None
    is_corpus_doc: bool = True
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def _looks_like_corpus_doc(data: dict) -> bool:
    """A corpus document has free text; ATT&CK input files do not."""
    return isinstance(data, dict) and "text" in data


def validate_file(path: Path, case: str, layer: str) -> FileReport:
    rep = FileReport(path=str(path), case=case, layer=layer)

    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        rep.errors.append(f"invalid JSON: {exc}")
        return rep
    except OSError as exc:
        rep.errors.append(f"cannot read file: {exc}")
        return rep

    if not _looks_like_corpus_doc(raw):
        # ATT&CK input or other non-corpus artifact; not validated here.
        rep.is_corpus_doc = False
        return rep

    rep.doc_id = raw.get("doc_id") or raw.get("id")
    rep.source_type = raw.get("source_type")

    try:
        doc = CorpusDocument.from_dict(raw)
    except CorpusValidationError as exc:
        rep.errors.append(str(exc))
        return rep

    for fld in unsupported_fields(raw):
        rep.warnings.append(f"unsupported/unexpected field: {fld!r}")

    # Attribution coding is required for PUBLIC corpus documents only.
    if layer == "public":
        if not doc.has_attribution_coding():
            rep.errors.append(
                "missing attribution coding (run the attribution coding "
                "workflow before Attribution Drift can be computed)"
            )
        else:
            try:
                doc.validate_attribution_coding()
            except CorpusValidationError as exc:
                rep.errors.append(str(exc))

    return rep


def discover(data_dir: Path, include_excluded: bool) -> list[FileReport]:
    reports: list[FileReport] = []
    for case_dir in sorted(data_dir.iterdir()):
        if not case_dir.is_dir():
            continue
        if case_dir.name == EXCLUDED_DIR_NAME:
            if not include_excluded:
                continue
            # Descend into each excluded case.
            for excase in sorted(case_dir.iterdir()):
                if excase.is_dir():
                    reports.extend(_scan_case(excase, f"{EXCLUDED_DIR_NAME}/{excase.name}"))
            continue
        reports.extend(_scan_case(case_dir, case_dir.name))
    return reports


def _scan_case(case_dir: Path, case_label: str) -> list[FileReport]:
    out: list[FileReport] = []
    for layer in ("public", "technical"):
        layer_dir = case_dir / layer
        if not layer_dir.is_dir():
            continue
        for f in sorted(layer_dir.glob("*.json")):
            out.append(validate_file(f, case_label, layer))
    return out


def build_summary(reports: list[FileReport]) -> dict:
    corpus = [r for r in reports if r.is_corpus_doc]
    errors = [r for r in corpus if r.errors]
    warnings = [r for r in corpus if r.warnings]
    source_types: dict[str, int] = {}
    for r in corpus:
        if r.source_type:
            source_types[r.source_type] = source_types.get(r.source_type, 0) + 1
    return {
        "files_scanned": len(reports),
        "corpus_documents": len(corpus),
        "non_corpus_files_skipped": len(reports) - len(corpus),
        "documents_with_errors": len(errors),
        "documents_with_warnings": len(warnings),
        "source_type_distribution": dict(sorted(source_types.items())),
        "ok": len(errors) == 0,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Validate CIDF corpora.")
    ap.add_argument("--data-dir", default="data", type=Path)
    ap.add_argument("--include-excluded", action="store_true",
                    help="Also validate archived cases under _excluded_cases.")
    ap.add_argument("--json", action="store_true",
                    help="Emit a machine-readable JSON report.")
    args = ap.parse_args()

    data_dir = args.data_dir
    if not data_dir.is_dir():
        print(f"ERROR: data directory not found: {data_dir}", file=sys.stderr)
        return 2

    reports = discover(data_dir, include_excluded=args.include_excluded)
    summary = build_summary(reports)

    if args.json:
        payload = {
            "summary": summary,
            "files": [
                {
                    "path": r.path, "case": r.case, "layer": r.layer,
                    "doc_id": r.doc_id, "source_type": r.source_type,
                    "is_corpus_doc": r.is_corpus_doc,
                    "errors": r.errors, "warnings": r.warnings,
                }
                for r in reports
            ],
        }
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return 0 if summary["ok"] else 1

    print("CIDF corpus validation")
    print("=" * 60)
    for r in reports:
        if not r.is_corpus_doc:
            continue
        if r.errors:
            print(f"[ERROR] {r.path}")
            for e in r.errors:
                print(f"        - {e}")
        elif r.warnings:
            print(f"[WARN ] {r.path}")
            for w in r.warnings:
                print(f"        - {w}")
    print("-" * 60)
    print(f"Files scanned ............ {summary['files_scanned']}")
    print(f"Corpus documents ......... {summary['corpus_documents']}")
    print(f"Non-corpus files skipped . {summary['non_corpus_files_skipped']}")
    print(f"Documents with errors .... {summary['documents_with_errors']}")
    print(f"Documents with warnings .. {summary['documents_with_warnings']}")
    print(f"Source-type distribution . {summary['source_type_distribution']}")
    print("=" * 60)
    print("RESULT:", "OK" if summary["ok"] else "ERRORS FOUND")
    return 0 if summary["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
