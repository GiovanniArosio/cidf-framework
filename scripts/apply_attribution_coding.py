#!/usr/bin/env python3
"""
Apply manual attribution coding to the active public corpora
============================================================
Single source of truth for the manual attribution coding of every active
public corpus document. Running this script appends the five attribution
fields (see ``docs/attribution_coding_protocol.md``) to each public JSON
document **without** modifying any existing field, then validates the
result against the protocol's cross-field rules.

The coding was performed by reading ONLY the stored corpus text. Each note
references the wording represented in the stored summary. No attribution was
inferred from source reputation, background knowledge, the (not fully
reproduced) original article, or a country merely appearing in geopolitical
context.

This script is idempotent: existing attribution fields are overwritten with
the canonical coding below, all other fields and key order are preserved.

Usage:
    python scripts/apply_attribution_coding.py            # write coding
    python scripts/apply_attribution_coding.py --check    # verify only

Part of the CIDF framework — LUISS Guido Carli, 2026
Author: Giovanni Arosio
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from utils.corpus_schema import (  # noqa: E402
    ATTRIBUTION_FIELDS,
    CorpusValidationError,
    validate_attribution_payload,
)

# doc_id -> (state, actor, confidence, basis, coding_note)
# Notes quote/paraphrase ONLY the stored corpus text for that document.
CODING: dict[str, tuple[str, str, str, str, str]] = {
    # ----------------------------- NotPetya -----------------------------
    "notpetya_pub_001": (
        "no_claim", "none", "none", "no_claim",
        "Frames the event as 'financially motivated ransomware demanding "
        "Bitcoin payment'; no responsible actor named in the stored text.",
    ),
    "notpetya_pub_002": (
        "no_claim", "none", "none", "no_claim",
        "Describes a cyberattack that 'started in Ukraine before rippling "
        "across Europe'; no responsible actor named in the stored text.",
    ),
    "notpetya_pub_003": (
        "no_claim", "none", "none", "no_claim",
        "Reports Kaspersky's conclusion that the campaign was 'a wiper "
        "pretending to be ransomware'; concerns the malware's nature, not "
        "attribution; no actor named.",
    ),
    "notpetya_pub_004": (
        "no_claim", "none", "none", "no_claim",
        "Technical analysis arguing NotPetya 'is more akin to a wiper'; the "
        "stored text makes no attribution claim and names no actor.",
    ),
    "notpetya_pub_005": (
        "no_claim", "none", "none", "no_claim",
        "Calls the campaign 'destructive and geopolitically motivated' and "
        "tied to the M.E.Doc supply chain; per the coding rule, geopolitical "
        "motive framing without a named actor is not treated as attribution.",
    ),
    "notpetya_pub_006": (
        "no_claim", "none", "none", "no_claim",
        "States the US-CERT alert 'focused on mitigation rather than "
        "attribution'; no responsible actor named.",
    ),
    "notpetya_pub_007": (
        "attributed", "russia", "high", "official_attribution",
        "Ukraine's SBU 'stated they had evidence the cyberattack was "
        "organized by the Russian Federation'; explicit state attribution.",
    ),
    "notpetya_pub_008": (
        "attributed", "russia", "high", "official_attribution",
        "UK government 'judges that the Russian government, specifically the "
        "Russian military, was responsible'.",
    ),
    "notpetya_pub_009": (
        "attributed", "russia", "high", "official_attribution",
        "White House statement: 'the Russian military launched the most "
        "destructive and costly cyber attack in history'.",
    ),
    "notpetya_pub_010": (
        "attributed", "russia", "high", "official_attribution",
        "Reports the United States 'publicly blamed Russia' and 'formally "
        "holding Russia accountable'.",
    ),
    "notpetya_pub_011": (
        "attributed", "russia", "high", "official_attribution",
        "Reports 'the UK government judged Russia's military to be "
        "responsible' for the attack.",
    ),
    "notpetya_pub_012": (
        "no_claim", "none", "none", "no_claim",
        "Covers damage scale and the 'wiper masquerading as ransomware' "
        "nature; the stored summary names no responsible actor.",
    ),
    "notpetya_pub_013": (
        "attributed", "unknown", "low", "investigative_reporting",
        "Refers to 'large-scale state-attributed cyber incidents' in an "
        "acts-of-war insurance context; the stored text references state "
        "attribution but names no specific actor (coded actor 'unknown').",
    ),
    "notpetya_pub_014": (
        "no_claim", "none", "none", "no_claim",
        "Discusses NotPetya as a case study for EU operational cooperation "
        "and preparedness; no attribution claim in the stored text.",
    ),
    "notpetya_pub_015": (
        "attributed", "russia", "high", "official_attribution",
        "EU sanctions text targets 'Russian military agents tied to attacks "
        "on Ukrainian infrastructure' including NotPetya.",
    ),
    # ----------------------------- KA-SAT ------------------------------
    "kasat_pub_001": (
        "attributed", "russia", "high", "official_attribution",
        "Reports the US, Britain, Canada, Estonia and the EU 'publicly blamed "
        "Russia for a large cyberattack on Viasat's KA-SAT'.",
    ),
    "kasat_pub_002": (
        "attributed", "russia", "high", "official_attribution",
        "BBC reports the UK is 'almost certain Russia was responsible' for "
        "the KA-SAT attack.",
    ),
    "kasat_pub_003": (
        "uncertain", "unknown", "none", "investigative_reporting",
        "Highlights 'uncertainty over the perpetrators' and an ongoing "
        "investigation; Russian military movement appears only as timing "
        "context, not attribution.",
    ),
    "kasat_pub_004": (
        "attributed", "russia", "high", "official_attribution",
        "Reports the UK government 'stated it believed Russia carried out the "
        "24 February cyber operation' against KA-SAT.",
    ),
    "kasat_pub_005": (
        "attributed", "russia", "high", "official_attribution",
        "Summarises 'Western officials' claims that Russia conducted a "
        "cyberattack against the KA-SAT satellite network'.",
    ),
    "kasat_pub_006": (
        "uncertain", "unknown", "none", "investigative_reporting",
        "Emphasises 'lingering uncertainty about the attackers and motives'; "
        "Russia's invasion is referenced only as timing context.",
    ),
    "kasat_pub_007": (
        "attributed", "russia", "medium", "investigative_reporting",
        "Reports US intelligence analysts 'concluded Russian military hackers "
        "were responsible', explicitly framed as a 'private assessment at the "
        "time' citing unnamed US sources.",
    ),
    "kasat_pub_008": (
        "attributed", "russia", "medium", "investigative_reporting",
        "States 'Russian government hackers have been linked to' the attack "
        "per US intelligence and researchers, while noting 'formal public "
        "attribution was still developing'.",
    ),
    "kasat_pub_009": (
        "attributed", "russia", "high", "official_attribution",
        "Reports the 'US, UK and EU formally blamed Russia for a large-scale "
        "cyberattack' against Viasat.",
    ),
    "kasat_pub_010": (
        "no_claim", "none", "none", "no_claim",
        "Discusses the wiper malware role and impacts citing Viasat and "
        "SentinelLabs; the stored text names no responsible actor.",
    ),
    "kasat_pub_011": (
        "no_claim", "none", "none", "no_claim",
        "Reports Viasat describing the incident as 'a deliberate, "
        "multifaceted cyberattack'; intentionality is asserted but no "
        "responsible actor is named.",
    ),
    "kasat_pub_012": (
        "attributed", "russia", "high", "official_attribution",
        "Reports the 'US, Canada and European allies attributed the 24 "
        "February attack on Viasat to Russia', referencing Russia's "
        "intelligence directorate.",
    ),
    "kasat_pub_013": (
        "attributed", "russia", "high", "official_attribution",
        "Reports the EU 'officially accused Russian authorities of carrying "
        "out a cyberattack' on the KA-SAT network.",
    ),
    "kasat_pub_014": (
        "attributed", "russia", "high", "official_attribution",
        "EU High Representative declaration 'condemning Russian cyber "
        "operations' with specific reference to the KA-SAT attack.",
    ),
    "kasat_pub_015": (
        "no_claim", "none", "none", "no_claim",
        "European Commission item describes 'a likely cyberattack' affecting "
        "EU users 'without going into technical detail'; no actor named.",
    ),
    # ------------------------------ PAP --------------------------------
    "pap_pub_001": (
        "no_claim", "none", "none", "no_claim",
        "PAP states it 'had not been the source' of the false dispatch and "
        "'blocked the exploit'; the stored text blames no external actor.",
    ),
    "pap_pub_002": (
        "attributed", "russia", "medium", "investigative_reporting",
        "Reports the hack was 'probably the work of Russia-sponsored hackers' "
        "aimed at interfering with the EU election; hedged attribution to "
        "Russia.",
    ),
    "pap_pub_003": (
        "uncertain", "unknown", "none", "investigative_reporting",
        "Describes 'fake news of unknown origin'; the stored text explicitly "
        "leaves responsibility unresolved.",
    ),
    "pap_pub_004": (
        "no_claim", "none", "none", "no_claim",
        "Government spokesperson denies the false dispatch's content as "
        "'false'; the stored text attributes the act to no external actor.",
    ),
    "pap_pub_005": (
        "attributed", "russia", "high", "official_attribution",
        "Digital Affairs Minister states 'we are dealing with a cyberattack "
        "coming from the Russian side' and 'we are at cyberwar with Russia'.",
    ),
    "pap_pub_006": (
        "attributed", "russia", "high", "official_attribution",
        "PM Tusk calls it part of 'the Russian destabilization strategy' and "
        "'Russia's attempts to destabilise the European Union'.",
    ),
    "pap_pub_007": (
        "attributed", "russia", "medium", "official_attribution",
        "ABW spokesperson cites a 'probable Russian cyberattack' and 'most "
        "likely a Russian disinformation operation'; investigation references "
        "persons 'acting on behalf of foreign intelligence'.",
    ),
    "pap_pub_008": (
        "attributed", "russia", "medium", "official_attribution",
        "Reports the Polish government said the false story was 'likely a "
        "Russian cyberattack' aimed at destabilising the EU.",
    ),
    "pap_pub_009": (
        "attributed", "russia", "medium", "investigative_reporting",
        "Reports Polish intelligence 'investigating' and officials 'pointing "
        "to Russian state-sponsored actors as the likely perpetrators'.",
    ),
    "pap_pub_010": (
        "no_claim", "none", "none", "no_claim",
        "PAP confirms 'a hacking attack on the agency's servers' and "
        "identifies the leaked-data source; no external actor named in the "
        "stored text.",
    ),
    "pap_pub_011": (
        "attributed", "russia", "medium", "official_attribution",
        "Reports 'Polish officials blamed Russian hackers for the content "
        "injection attack' on the national press agency.",
    ),
    "pap_pub_012": (
        "attributed", "russia", "medium", "investigative_reporting",
        "Think-tank assessment: the attack was 'most likely perpetrated by a "
        "Kremlin-affiliated actor' within a series of Russian operations.",
    ),
    "pap_pub_013": (
        "attributed", "russia", "medium", "official_attribution",
        "Reports Poland dismantled a cyber-espionage network 'tied to "
        "Belarusian and Russian intelligence' that attacked PAP; coded with "
        "Russia as primary, Belarus recorded as a secondary co-attribution.",
    ),
    "pap_pub_014": (
        "attributed", "russia", "medium", "technical_assessment",
        "NASK text states prior APT28/GRU activity 'informed the attribution "
        "of the PAP hack to Russian state-sponsored actors as part of a "
        "larger pattern'; pattern-based assessment, document dated before the "
        "incident.",
    ),
    "pap_pub_015": (
        "no_claim", "none", "none", "no_claim",
        "Fact-checker 'amplified PAP's correction' and labelled the message "
        "fakenews; the stored text attributes the act to no external actor.",
    ),
}

PUBLIC_GLOBS = (
    "data/notpetya/public/*.json",
    "data/kasat_viasat/public/*.json",
    "data/pap_hack/public/*.json",
)


def _public_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for pattern in PUBLIC_GLOBS:
        files.extend(sorted(root.glob(pattern)))
    return files


def apply_coding(root: Path, check_only: bool) -> int:
    files = _public_files(root)
    doc_ids_on_disk = set()
    changed, errors = 0, 0

    for path in files:
        data = json.loads(path.read_text(encoding="utf-8"))
        doc_id = data.get("doc_id") or data.get("id")
        doc_ids_on_disk.add(doc_id)
        if doc_id not in CODING:
            print(f"[ERROR] no coding entry for {doc_id} ({path})")
            errors += 1
            continue

        state, actor, conf, basis, note = CODING[doc_id]
        payload = {
            "attribution_state": state,
            "attribution_actor": actor,
            "attribution_confidence": conf,
            "attribution_basis": basis,
            "attribution_coding_note": note,
        }
        try:
            validate_attribution_payload(payload, doc_id=doc_id)
        except CorpusValidationError as exc:
            print(f"[ERROR] invalid coding for {doc_id}: {exc}")
            errors += 1
            continue

        needs_update = any(data.get(k) != v for k, v in payload.items())
        if check_only:
            if needs_update:
                print(f"[CHECK] {doc_id}: coding missing or differs from canonical")
                errors += 1
            continue

        if needs_update:
            # Preserve all existing fields and key order; append coding fields.
            for k in ATTRIBUTION_FIELDS:
                data.pop(k, None)
            data.update(payload)
            path.write_text(
                json.dumps(data, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            changed += 1

    # Coding entries with no corresponding file are an error too.
    orphans = sorted(set(CODING) - doc_ids_on_disk)
    for orphan in orphans:
        print(f"[ERROR] coding entry has no file on disk: {orphan}")
        errors += 1

    print("-" * 60)
    print(f"Public documents .... {len(files)}")
    print(f"Coding entries ...... {len(CODING)}")
    if check_only:
        print(f"Mismatches .......... {errors}")
        print("RESULT:", "OK" if errors == 0 else "MISMATCH")
    else:
        print(f"Files updated ....... {changed}")
        print(f"Errors .............. {errors}")
        print("RESULT:", "OK" if errors == 0 else "ERRORS")
    return 0 if errors == 0 else 1


def main() -> int:
    ap = argparse.ArgumentParser(description="Apply attribution coding.")
    ap.add_argument("--root", default=".", type=Path)
    ap.add_argument("--check", action="store_true",
                    help="Verify coding without writing files.")
    args = ap.parse_args()
    return apply_coding(args.root, check_only=args.check)


if __name__ == "__main__":
    raise SystemExit(main())
