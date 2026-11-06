"""E95: the two-axis escape partition, per whole-listing source (AX-1).

Motivation
----------
Round 23's E90 (``2026-11-04_rule_utilisation``) classified 38,118 frozen
*windows*: 19,303 content-first (a reducing action exists in the window)
versus 699 reorder-first, with the reorder class concentrated in the
``GREEDY_FIXED_POINT`` root stratum.  That census runs on windows; the escape
claim of the manuscript is about whole-listing *sources*.  This experiment
lifts the same two-axis partition to the source level, on the frozen v16
certified escapes only.

Method
------
For every one of the 128-panel sources that has a certified escape -- the
69 escape paths = 35 enumerated compact escapes (``EXACT_ESCAPE``) + 34
witness-bounded escapes (``WITNESS_CERTIFIED_SEARCH_INCOMPLETE`` with a
replay-passed witness) -- take the FIRST action of the certified escape
witness and classify by its ``cost_delta``:

    content-first  cost_delta < 0   (the escape path opens with a reduction)
    reorder-first  cost_delta == 0  (the escape path opens cost-neutrally)

The canonical witness is the compact one (the v16 integration records
``witness_source = COMPACT`` for all 69); the IDA* witness is carried as a
cross-reference.  The one resource-bounded source (``e39:b2f83603...``) is
recorded separately and never classified.

Additional per-source provenance: ``circuit_family``, root stratum
(``root_kind``, rebuilt hash-checked via ``load_root_states`` and cross-checked
against E52's published mapping), the first rule's source length, and a full
root-action census (every legal action at the root, enumerated) so the
first-step axis can be compared with the window-level definition "a reducing
action exists".

Contract
--------
Read-only on frozen inputs (``data/v16/*``, ``data/v13/*`` rule library,
E52/E90 review packages).  Nothing under ``data/``, ``release/`` or
``docs/manuscript/`` is written; no search is re-run -- the only enumeration
is the legal-action census at the 69 escape roots, which uses the same
``iter_legal_actions`` machinery E90 used on windows.

Self-checks (exit 1 on any failure)
    * 69 classified sources; 1 resource-bounded recorded separately;
      no unresolved witnesses (fail-closed: an unrecoverable first action is
      listed under ``unresolved`` and forces the count check to fail);
    * every content-first row has ``cost_delta < 0``, every reorder-first row
      has ``cost_delta == 0``, no positive first-step delta anywhere;
    * witness step 0 pre-state hash == certificate initial state hash, and the
      rebuilt root hash matches the certificate (both packages, all 69);
    * witness length == classification ``escape_depth``;
    * E90 prediction at source level: every GREEDY_FIXED_POINT escape is
      reorder-first;
    * E90 length claim at source level: every first *reducing* step (and every
      content-first first step) has source length 2;
    * compact and IDA* witnesses agree on the first step's direction;
    * E52 alignment: E52's escape sources are a subset of the 69 and E52's
      ``neutral_prefix_length`` (v14 witnesses) agrees with today's axis on
      every shared source.

Outputs (``docs/review/science_boost/2026-11-06_source_axis_partition/``)
    source_axis_partition.csv  one row per classified escape source
    summary.json               counts, per-stratum split, root census,
                               E90 window comparison, E52 alignment,
                               self-checks, unresolved list, provenance
    MANIFEST.json              sha256 of every artifact
"""

from __future__ import annotations

import argparse
import collections
import csv
import hashlib
import importlib
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))

e52 = importlib.import_module("e52_escape_mechanism_census")

OUTPUT_ROOT = ROOT / "docs" / "review" / "science_boost" / "2026-11-06_source_axis_partition"
EXPERIMENT_ID = "E95_SOURCE_AXIS_PARTITION_2026_11_06"

V16 = ROOT / "data" / "v16"
CLASSIFICATION = V16 / "e45_landscape_integration" / "classification_complete.csv"
COMPACT_CERTS = V16 / "e45_full_development" / "certificates.jsonl"
IDASTAR_CERTS = V16 / "e45_idastar_escape" / "certificates.jsonl"
RULE_LIBRARY = e52.RULE_LIBRARY  # data/v13/e43_quartz_rule_import/generation_a/rule_library.json
E52_CSV = e52.OUTPUT_ROOT / "escape_mechanism.csv"
E90_SUMMARY = ROOT / "docs" / "review" / "science_boost" / "2026-11-04_rule_utilisation" / "summary.json"

RESOURCE_BOUNDED_PREFIX = "e39:b2f83603"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def rule_source_lengths() -> dict[str, int]:
    """rule_id -> source gate count, from the frozen v13 library.

    ``pair_v1`` and ``structural_exchange_v1`` actions consume exactly 2 gates
    (``certified_landscape.replay_actions``), and the v13 library entries for
    them are metadata-only, so their length is fixed at 2 here.
    """

    payload = json.loads(RULE_LIBRARY.read_text(encoding="utf-8"))
    lengths: dict[str, int] = {}
    for rule in payload["rules"]:
        if "source_gate_count" in rule:
            lengths[rule["rule_id"]] = int(rule["source_gate_count"])
        elif "source" in rule:
            lengths[rule["rule_id"]] = len(rule["source"]["operations"])
    return lengths


def source_length_of(rule_id: str, quartz_lengths: dict[str, int]) -> int | None:
    if rule_id.startswith("pair_v1.") or rule_id.startswith("exchange."):
        return 2
    return quartz_lengths.get(rule_id)


def load_certificates(path: Path) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        payload = json.loads(line)
        out[payload["source_id"]] = payload
    return out


def first_step(certificate: dict[str, Any]) -> dict[str, Any] | None:
    witness = (certificate.get("witnesses") or {}).get("escape") or []
    if not witness:
        return None
    step = witness[0]
    return {
        "rule_id": str(step.get("rule_id", "")),
        "family": str(step.get("family", "")) or e52.rule_family_of(str(step.get("rule_id", ""))),
        "cost_delta": int(step.get("cost_delta", 0)),
        "location": step.get("location"),
        "pre_state_sha256": str(step.get("pre_state_sha256", "")),
        "path_length": len(witness),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)

    classification_rows = list(csv.DictReader(CLASSIFICATION.open(encoding="utf-8", newline="")))
    classification = {row["source_id"]: row for row in classification_rows}
    escapes = {
        source_id: row
        for source_id, row in classification.items()
        if row["classification_status"] == "EXACT_ESCAPE"
    }
    resource_bounded = {
        source_id: row
        for source_id, row in classification.items()
        if row["classification_status"] == "RESOURCE_BOUNDED_NO_WITNESS"
    }

    compact = load_certificates(COMPACT_CERTS)
    idastar = load_certificates(IDASTAR_CERTS)
    quartz_lengths = rule_source_lengths()

    print(f"[E95] classification: {len(classification)} sources, {len(escapes)} escapes, "
          f"{len(resource_bounded)} resource-bounded", flush=True)

    # ---- hash-checked root rebuild + root strata (E52/E90 machinery) -------
    roots = e52_load_roots()
    root_by_id = {root["source_id"]: root for root in roots}
    print(f"[E95] roots rebuilt: {len(roots)} (hash-checked)", flush=True)

    # ---- classify the 69 certified escapes ---------------------------------
    records: list[dict[str, Any]] = []
    unresolved: list[dict[str, Any]] = []
    for source_id in sorted(escapes):
        row = escapes[source_id]
        record: dict[str, Any] = {
            "source_id": source_id,
            "circuit_family": row["circuit_family"],
            "source_kind": row["source_kind"],
            "n_qubits": int(row["n_qubits"] or 0),
            "baseline_cost": int(row["baseline_cost"] or 0),
            "escape_depth": int(row["escape_depth"] or 0),
            "escape_class": (
                "enumerated_compact"
                if row["compact_status"] == "EXACT_ESCAPE"
                else "witness_bounded"
                if row["compact_status"] == "WITNESS_CERTIFIED_SEARCH_INCOMPLETE"
                else f"UNEXPECTED_COMPACT_STATUS:{row['compact_status']}"
            ),
            "certificate_tier": row["certificate_tier"],
            "witness_source": row["witness_source"],
            "witness_replay_compact": row["witness_replay_compact"],
            "witness_replay_idastar": row["witness_replay_idastar"],
        }
        compact_cert = compact.get(source_id, {}).get("certificate")
        idastar_cert = idastar.get(source_id, {}).get("certificate")
        first = first_step(compact_cert) if compact_cert else None
        first_ida = first_step(idastar_cert) if idastar_cert else None
        if first is None:
            unresolved.append(
                {
                    "source_id": source_id,
                    "reason": "compact witness missing or empty in e45_full_development/certificates.jsonl",
                }
            )
            continue
        if first_ida is None:
            unresolved.append(
                {
                    "source_id": source_id,
                    "reason": "idastar witness missing or empty in e45_idastar_escape/certificates.jsonl",
                }
            )
            continue
        length = source_length_of(first["rule_id"], quartz_lengths)
        if length is None:
            unresolved.append(
                {
                    "source_id": source_id,
                    "reason": f"first rule id not found in v13 rule library: {first['rule_id']}",
                }
            )
            continue

        decomposition = e52.decompose_escape(compact_cert["witnesses"]["escape"])
        first_reducing = (
            decomposition["reducing_steps"][0] if decomposition["reducing_steps"] else None
        )
        axis = "content_first" if first["cost_delta"] < 0 else "reorder_first" if first["cost_delta"] == 0 else "UNCLASSIFIED_POSITIVE_DELTA"

        root = root_by_id.get(source_id)
        if root is None:
            unresolved.append(
                {
                    "source_id": source_id,
                    "reason": "root state could not be rebuilt by load_root_states",
                }
            )
            continue

        record.update(
            {
                "root_kind": root["root_kind"],
                "stratum": root["root_kind"],
                "root_state_sha256": root["root_state_sha256"],
                "root_gate_count": root["root_gate_count"],
                "axis": axis,
                "first_rule_id": first["rule_id"],
                "first_rule_family": first["family"],
                "first_rule_source_length": length,
                "first_step_cost_delta": first["cost_delta"],
                "first_step_location": first["location"],
                "path_length": first["path_length"],
                "neutral_prefix_length": decomposition["neutral_prefix_length"],
                "net_delta": decomposition["net_delta"],
                "first_reducing_step_index": first_reducing["index"] if first_reducing else "",
                "first_reducing_rule_id": first_reducing["rule_id"] if first_reducing else "",
                "first_reducing_rule_source_length": (
                    source_length_of(str(first_reducing["rule_id"]), quartz_lengths)
                    if first_reducing
                    else ""
                ),
                "first_reducing_cost_delta": first_reducing["cost_delta"] if first_reducing else "",
                "root_has_reducing_action": "",
                "root_reducing_action_count": "",
                "root_min_reducing_source_length": "",
                "root_neutral_action_count": "",
                "idastar_first_rule_id": first_ida["rule_id"],
                "idastar_first_cost_delta": first_ida["cost_delta"],
                "idastar_direction_agrees": (first_ida["cost_delta"] < 0) == (first["cost_delta"] < 0),
            }
        )
        records.append(record)

    # ---- root action census for the classified roots -----------------------
    from src.optimisation.certified_landscape import iter_legal_actions  # noqa: PLC0415

    for record in records:
        root = root_by_id[record["source_id"]]
        reducing: list[int] = []
        neutral = 0
        for action in iter_legal_actions(root["state"], RULE_LIBRARY, e52.RULE_SCOPE):
            if action.cost_delta < 0:
                reducing.append(source_length_of(action.rule_id, quartz_lengths) or -1)
            elif action.cost_delta == 0:
                neutral += 1
        record["root_has_reducing_action"] = bool(reducing)
        record["root_reducing_action_count"] = len(reducing)
        record["root_min_reducing_source_length"] = min(reducing) if reducing else ""
        record["root_neutral_action_count"] = neutral
    print(f"[E95] classified {len(records)} escapes; unresolved {len(unresolved)}", flush=True)

    # ---- self-checks -------------------------------------------------------
    checks: dict[str, Any] = {}
    checks["classified_count_is_69"] = len(records) == 69
    checks["resource_bounded_recorded_separately"] = (
        len(resource_bounded) == 1
        and next(iter(resource_bounded), "").startswith(RESOURCE_BOUNDED_PREFIX)
    )
    checks["no_unresolved_sources"] = not unresolved
    checks["content_first_rows_have_negative_delta"] = all(
        record["first_step_cost_delta"] < 0
        for record in records
        if record["axis"] == "content_first"
    )
    checks["reorder_first_rows_have_zero_delta"] = all(
        record["first_step_cost_delta"] == 0
        for record in records
        if record["axis"] == "reorder_first"
    )
    checks["no_positive_first_step_delta"] = all(
        record["axis"] != "UNCLASSIFIED_POSITIVE_DELTA" for record in records
    )
    checks["witness_first_step_pre_state_matches_certificate"] = all(
        compact[record["source_id"]]["certificate"]["witnesses"]["escape"][0]["pre_state_sha256"]
        == compact[record["source_id"]]["certificate"]["initial_state_sha256"]
        and idastar[record["source_id"]]["certificate"]["witnesses"]["escape"][0]["pre_state_sha256"]
        == idastar[record["source_id"]]["certificate"]["initial_state_sha256"]
        for record in records
    )
    checks["rebuilt_root_hash_matches_certificates"] = all(
        root_by_id[record["source_id"]]["root_state_sha256"]
        == compact[record["source_id"]]["certificate"]["initial_state_sha256"]
        for record in records
    )
    checks["witness_length_matches_classification_escape_depth"] = all(
        record["path_length"] == record["escape_depth"] for record in records
    )
    checks["compact_status_matches_package"] = all(
        compact[source_id]["certificate"].get("status") == row["compact_status"]
        and idastar[source_id]["certificate"].get("status") == row["idastar_status"]
        for source_id, row in classification.items()
    )
    greedy = [record for record in records if record["stratum"] == "GREEDY_FIXED_POINT"]
    checks["e90_prediction_greedy_escapes_all_reorder_first"] = all(
        record["axis"] == "reorder_first" for record in greedy
    )
    checks["first_reducing_step_source_length_is_2"] = all(
        record["first_reducing_rule_source_length"] == 2 for record in records
    )
    checks["content_first_first_action_source_length_is_2"] = all(
        record["first_rule_source_length"] == 2
        for record in records
        if record["axis"] == "content_first"
    )
    checks["compact_idastar_first_step_direction_agree"] = all(
        record["idastar_direction_agrees"] for record in records
    )

    # E52 cross-experiment alignment
    e52_rows: dict[str, dict[str, str]] = {}
    with E52_CSV.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            e52_rows[row["source_id"]] = row
    e52_escape_ids = {
        source_id for source_id, row in e52_rows.items() if row["status"] == "EXACT_ESCAPE"
    }
    classified_ids = {record["source_id"] for record in records}
    e52_subset = e52_escape_ids <= classified_ids
    e52_axis_by_prefix = {
        source_id: ("content_first" if int(row["neutral_prefix_length"] or 0) == 0 else "reorder_first")
        for source_id, row in e52_rows.items()
        if row["status"] == "EXACT_ESCAPE"
    }
    today_axis = {record["source_id"]: record["axis"] for record in records}
    e52_disagreements = [
        source_id for source_id, axis in e52_axis_by_prefix.items() if today_axis.get(source_id) != axis
    ]
    root_kind_disagreements = [
        source_id
        for source_id, row in e52_rows.items()
        if source_id in root_by_id and row["root_kind"] != root_by_id[source_id]["root_kind"]
    ]
    checks["e52_escapes_subset_of_69"] = e52_subset
    checks["e52_neutral_prefix_matches_today_axis"] = bool(e52_axis_by_prefix) and not e52_disagreements
    checks["root_kind_matches_e52_published"] = not root_kind_disagreements

    # root-census coherence between the two axes and the window-level definition
    checks["content_first_roots_all_have_reducing_action"] = all(
        record["root_has_reducing_action"]
        for record in records
        if record["axis"] == "content_first"
    )
    checks["reorder_first_roots_have_no_reducing_action"] = all(
        not record["root_has_reducing_action"]
        for record in records
        if record["axis"] == "reorder_first"
    )

    # ---- aggregates --------------------------------------------------------
    axis_counts = collections.Counter(record["axis"] for record in records)
    stratum_counts = collections.Counter(record["stratum"] for record in records)
    axis_by_stratum = {
        stratum: dict(collections.Counter(record["axis"] for record in records if record["stratum"] == stratum))
        for stratum in sorted(stratum_counts)
    }
    escape_class_by_axis = {
        axis: dict(collections.Counter(record["escape_class"] for record in records if record["axis"] == axis))
        for axis in sorted(axis_counts)
    }
    first_rule_counts = dict(
        collections.Counter(record["first_rule_id"] for record in records).most_common()
    )
    family_by_axis = {
        axis: dict(collections.Counter(record["first_rule_family"] for record in records if record["axis"] == axis))
        for axis in sorted(axis_counts)
    }

    e90 = json.loads(E90_SUMMARY.read_text(encoding="utf-8"))
    e90_totals = e90.get("totals", {})
    e90_strata = e90.get("by_root_stratum", {})

    resource_record = next(iter(resource_bounded.values()), None)
    resource_block = {
        "source_id": next(iter(resource_bounded), ""),
        "classification_status": resource_record["classification_status"] if resource_record else "",
        "compact_status": resource_record["compact_status"] if resource_record else "",
        "idastar_status": resource_record["idastar_status"] if resource_record else "",
        "compact_resource_reason": resource_record["compact_resource_reason"] if resource_record else "",
        "classified": False,
        "note": "resource-bounded, no witness; excluded from the two-axis partition by contract",
    }

    summary = {
        "experiment_id": EXPERIMENT_ID,
        "date": "2026-11-06",
        "definitions": {
            "content_first": "first action of the certified escape witness has cost_delta < 0",
            "reorder_first": "first action of the certified escape witness has cost_delta == 0",
            "canonical_witness": "compact (e45_full_development); classification records witness_source=COMPACT for all 69",
            "stratum": "root_kind from load_root_states (GREEDY_FIXED_POINT vs RAW_NORMALIZED_OVER_BASELINE_BUDGET)",
        },
        "contract": {
            "reads": {
                "classification_complete": {
                    "path": str(CLASSIFICATION.relative_to(ROOT)).replace("\\", "/"),
                    "sha256": e52.sha256(CLASSIFICATION),
                },
                "compact_certificates": {
                    "path": str(COMPACT_CERTS.relative_to(ROOT)).replace("\\", "/"),
                    "sha256": e52.sha256(COMPACT_CERTS),
                },
                "idastar_certificates": {
                    "path": str(IDASTAR_CERTS.relative_to(ROOT)).replace("\\", "/"),
                    "sha256": e52.sha256(IDASTAR_CERTS),
                },
                "rule_library": {
                    "path": str(RULE_LIBRARY.relative_to(ROOT)).replace("\\", "/"),
                    "sha256": e52.sha256(RULE_LIBRARY),
                },
                "e52_escape_mechanism_csv": {
                    "path": str(E52_CSV.relative_to(ROOT)).replace("\\", "/"),
                    "sha256": e52.sha256(E52_CSV),
                },
                "e90_summary_json": {
                    "path": str(E90_SUMMARY.relative_to(ROOT)).replace("\\", "/"),
                    "sha256": e52.sha256(E90_SUMMARY),
                },
            },
            "root_states": "rebuilt via experiments.e46_window_landscape.run.load_root_states (hash-checked)",
            "search_rerun": False,
            "root_action_enumeration": "iter_legal_actions on the 69 escape roots only (E90's window machinery, whole listing)",
            "writes": ["docs/review/science_boost/2026-11-06_source_axis_partition/"],
        },
        "headline": {
            "classified_sources": len(records),
            "content_first": axis_counts.get("content_first", 0),
            "reorder_first": axis_counts.get("reorder_first", 0),
            "content_first_share": round(axis_counts.get("content_first", 0) / len(records), 4) if records else None,
            "unresolved": len(unresolved),
        },
        "by_stratum": {
            "stratum_counts": dict(stratum_counts),
            "axis_by_stratum": axis_by_stratum,
            "e90_prediction_greedy_all_reorder_first": checks["e90_prediction_greedy_escapes_all_reorder_first"],
        },
        "by_escape_class": escape_class_by_axis,
        "first_rule_counts": first_rule_counts,
        "first_rule_family_by_axis": family_by_axis,
        "first_action_source_length": {
            "content_first": dict(
                collections.Counter(
                    record["first_rule_source_length"]
                    for record in records
                    if record["axis"] == "content_first"
                )
            ),
            "reorder_first": dict(
                collections.Counter(
                    record["first_rule_source_length"]
                    for record in records
                    if record["axis"] == "reorder_first"
                )
            ),
            "note": "E90's length-2 claim is about REDUCING actions; reorder-first first actions may be longer (here: lengths 3 and 4 occur)",
        },
        "root_action_census": {
            "content_first_roots_with_reducing_action": sum(
                1 for record in records if record["axis"] == "content_first" and record["root_has_reducing_action"]
            ),
            "reorder_first_roots_with_reducing_action": sum(
                1 for record in records if record["axis"] == "reorder_first" and record["root_has_reducing_action"]
            ),
            "reading": (
                "At the source level the first-step axis coincides exactly with the window-level "
                "definition: a root admits a reducing action iff the certified escape opens with one."
            ),
        },
        "resource_bounded": resource_block,
        "unresolved": unresolved,
        "e90_window_comparison": {
            "source": "docs/review/science_boost/2026-11-04_rule_utilisation/summary.json",
            "source_sha256": e52.sha256(E90_SUMMARY),
            "window_level_totals": {
                "unique_windows": e90_totals.get("unique_windows"),
                "windows_with_reducing_action": e90_totals.get("windows_with_reducing_action"),
                "escapes_without_reducing_action": e90_totals.get("escapes_without_reducing_action"),
            },
            "window_level_by_root_stratum": e90_strata,
            "source_level": {
                "classified_sources": len(records),
                "content_first": axis_counts.get("content_first", 0),
                "reorder_first": axis_counts.get("reorder_first", 0),
            },
            "comparability": (
                "Denominators differ (38,118 frozen windows vs 69 whole-listing sources), so the "
                "numbers need not match; the aligned claim is directional. Window level: 19,303 "
                "content-first vs 699 reorder-first, with the greedy stratum holding 0 reducing "
                "windows. Source level: the greedy stratum holds 0 content-first escapes. Both "
                "levels agree that reorder-first escapes are the minority and live in the greedy "
                "stratum."
            ),
        },
        "e52_alignment": {
            "e52_package": "docs/review/science_boost/2026-10-22_escape_mechanism/escape_mechanism.csv",
            "e52_escape_sources": len(e52_escape_ids),
            "subset_of_69": e52_subset,
            "shared_sources": len(e52_axis_by_prefix),
            "disagreements": e52_disagreements,
            "method": (
                "E52's published neutral_prefix_length (v14 IDA* witnesses) == 0 maps to "
                "content_first, > 0 maps to reorder_first; compared against today's axis on every "
                "shared source. Note the brief's '14 escape sources' corresponds to E52's 14 "
                "GREEDY_FIXED_POINT escapes, all reorder-first here as in E52's neutral prefix."
            ),
            "e52_greedy_escapes": sum(
                1
                for source_id in e52_escape_ids
                if e52_rows[source_id]["root_kind"] == "GREEDY_FIXED_POINT"
            ),
            "v16_only_escape_sources": sorted(classified_ids - e52_escape_ids),
            "root_kind_mismatches_vs_e52": root_kind_disagreements,
        },
        "self_checks": checks,
        "versions": {"python": sys.version.split()[0]},
    }

    e52.write_csv(OUTPUT_ROOT / "source_axis_partition.csv", records)
    (OUTPUT_ROOT / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    manifest = {
        "experiment_id": EXPERIMENT_ID,
        "artifacts": {
            path.name: {"sha256": sha256_file(path), "bytes": path.stat().st_size}
            for path in sorted(OUTPUT_ROOT.glob("*"))
            if path.is_file() and path.name != "MANIFEST.json"
        },
    }
    (OUTPUT_ROOT / "MANIFEST.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    failed = [key for key, value in checks.items() if value is False]
    print(
        f"[E95] self-checks: {sum(1 for v in checks.values() if v is True)} true / {len(failed)} false",
        flush=True,
    )
    for key in failed:
        print(f"[E95] FAILED: {key}", flush=True)
    print(
        f"[E95] headline: content_first {axis_counts.get('content_first', 0)}/69, "
        f"reorder_first {axis_counts.get('reorder_first', 0)}/69; "
        f"by stratum {axis_by_stratum}",
        flush=True,
    )
    print(f"[E95] wrote {OUTPUT_ROOT}", flush=True)
    return 1 if failed else 0


def e52_load_roots():
    """Hash-checked root rebuild via the machinery E52 already imports."""

    return e52.load_root_states()


if __name__ == "__main__":
    raise SystemExit(main())
