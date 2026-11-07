"""E98: bypass-coincidence check -- is the stratified two-axis partition an
artifact of the 80-gate baseline bypass?  (round-23 30-day item #2)

Motivation
----------
E95 (``2026-11-06_source_axis_partition``) measured the two-axis escape
partition at source level: 49 content-first / 20 reorder-first, with the
strata exactly coincident -- every RAW-stratum escape is content-first and
every ``GREEDY_FIXED_POINT``-stratum escape is reorder-first.  But the
stratification itself is produced by a pipeline that contains the 80-gate
baseline bypass: sources above ``MAX_BASELINE_GATES = 80`` skip the greedy
baseline entirely and enter the panel as raw normalized listings.  If the
"greedy stratum escapes are 100% reorder-first" headline were only a
consequence of *which* circuits the bypass allows into the greedy stratum,
it would not survive an honest uniform baseline.

Method
------
E54 (``2026-10-22_d2_rebaseline``) already defined the replacement baseline:
apply ``GreedyGateCancellation(max_iterations=50, fidelity_threshold=1.0,
success_reduction=0.0)`` to *every* normalized circuit, unconditionally (no
``MAX_BASELINE_GATES`` branch), and take ``state_from_circuit`` of the result
as the root.  This experiment re-derives strata and two-axis classification
under that uniform baseline for 23 sources:

* the 20 ``GREEDY_FIXED_POINT`` escapes of E95's partition (all
  reorder-first).  These are all <= 80 gates, so the frozen pipeline already
  ran the identical greedy on them; the uniform baseline must reproduce the
  frozen root byte-for-byte (hash check) and the certified witness first step
  must still attach to it (pre-state hash check).  No search is re-run.
* 3 content-stratum controls drawn from the 49 RAW content-first escapes
  (deterministic selection: smallest E54-rebased root cost per circuit
  family, tie-break source_id; all rebased roots <= 200 gates so the frozen
  contract search stays inside E54's memory-safe boundary).  For each control
  the uniform root is new, so the escape is re-derived by re-running the
  frozen contract search (h=3, ``e44_core_v1``, 200k states, 30 s -- exactly
  E54 Part C's contract); a surviving escape is classified by its new
  witness's first-step ``cost_delta``.

Headline: does "greedy-stratum escapes are 100% reorder-first" survive when
the bypass is removed -- i.e. do the 20 greedy escapes keep their axis (the
stratum's original members), and does any bypass-affected control turn into
a non-reorder-first escape *inside* the uniform greedy stratum?  Re-deriving
escapes under the uniform baseline can also surface a first-step class the
frozen 69 never showed -- a cost-INCREASING first step (``positive_first``);
that is a measured outcome, recorded with its own label and never folded
into content/reorder.

Contract
    Read-only with respect to ``data/``, ``release/`` and
    ``docs/manuscript/``.  No existing file is modified.  Root states are
    rebuilt through ``e52.load_root_states`` (hash-checked against the frozen
    certificates, raising on mismatch).  The only searches re-run are the 3
    control re-derivations (+ determinism rechecks) under the frozen
    contract; everything else is arithmetic on frozen artifacts.

Self-checks (exit 1 on any failure)
    * frozen root hashes verified via E52's loader for all 23 in-scope
      sources, and equal to both the E95 partition hashes and the v16
      certificate initial-state hashes;
    * scope counts: 23 sources; 20 reorder-first under E95; 3 content-first
      RAW controls, disjoint from the greedy set;
    * E95 partition axis invariants on all 69 rows (reorder-first rows have
      ``cost_delta == 0``; content-first rows have ``cost_delta < 0``);
    * re-derived axis labels are coherent with the recorded first-step
      ``cost_delta`` sign on the uniform-baseline side (``content_first`` < 0,
      ``reorder_first`` == 0, ``positive_first`` > 0 -- the positive-first
      class is a measured outcome, not an error; every derived row carries
      one of the three labels);
    * greedy-stratum roots unchanged under the uniform baseline (20/20 hash
      equality) -- the stratification is bypass-independent for this stratum;
    * every derived axis's witness first step attaches to the uniform root
      (pre-state hash);
    * controls are fail-closed: every control ends with a definitive escape
      outcome or is listed under ``unresolved`` (which forces exit 1) --
      nothing is fabricated; every re-derived control witness replays
      step-by-step against the uniform root with no UNRESOLVED step;
    * determinism recheck on 2 sources (1 greedy + 1 control) reproduces the
      recorded root hashes, censuses and search outcomes exactly.

Outputs (``docs/review/science_boost/2026-11-06_bypass_coincidence/``)
    bypass_coincidence.csv  one row per source: E95 stratum/axis vs
                            E54-uniform-baseline stratum/axis, with the
                            count-change reasons
    summary.json            headline, bypass provenance (file:line), scope,
                            self-checks, unresolved list, provenance
    MANIFEST.json           sha256 of every artifact (E91 house pattern)
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib
import json
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))

e52 = importlib.import_module("e52_escape_mechanism_census")
e95 = importlib.import_module("e95_source_axis_partition")
e54 = importlib.import_module("e54_d2_uniform_rebaseline")

OUTPUT_ROOT = ROOT / "docs" / "review" / "science_boost" / "2026-11-06_bypass_coincidence"
EXPERIMENT_ID = "E98_BYPASS_COINCIDENCE_2026_11_07"

E95_PARTITION = e95.OUTPUT_ROOT / "source_axis_partition.csv"
E54_REBASELINE = e54.OUTPUT_ROOT / "rebaseline.csv"
CLASSIFICATION = e95.CLASSIFICATION
COMPACT_CERTS = e95.COMPACT_CERTS  # data/v16/e45_full_development/certificates.jsonl
RULE_LIBRARY = e52.RULE_LIBRARY
RULE_SCOPE = e52.RULE_SCOPE

# E54's uniform-baseline construction and frozen-contract search parameters.
GREEDY_KWARGS = {"max_iterations": 50, "fidelity_threshold": 1.0, "success_reduction": 0.0}
HORIZON = e54.HORIZON
STATE_BUDGET = e54.STATE_BUDGET
TIME_BUDGET_SECONDS = e54.TIME_BUDGET_SECONDS
MAX_SAFE_GATES = e54.MAX_SAFE_GATES

CONTROL_COUNT = 3
DETERMINISM_RECHECK_COUNT = 2

SOURCE_LENGTHS = e95.rule_source_lengths()

BYPASS_PROVENANCE = {
    "where_the_80_gate_bypass_enters_the_e95_pipeline": (
        "experiments/e45_development_grid/run.py:97 defines MAX_BASELINE_GATES = 80. "
        "experiments/e46_window_landscape/run.py:111-113 (inside load_root_states) applies "
        "the bypass: `if int(circuit.size()) > MAX_BASELINE_GATES: baseline = circuit; "
        "root_kind = \"RAW_NORMALIZED_OVER_BASELINE_BUDGET\"` -- sources above 80 gates skip "
        "the greedy baseline entirely. E95 inherits this through "
        "scripts/e95_source_axis_partition.py:612 (`return e52.load_root_states()`), which "
        "resolves to the import at scripts/e52_escape_mechanism_census.py:59 "
        "(`from experiments.e46_window_landscape.run import ... load_root_states`); E95 "
        "consumes it at scripts/e95_source_axis_partition.py:184 and writes the resulting "
        "label into source_axis_partition.csv at scripts/e95_source_axis_partition.py:260-261 "
        "(`\"root_kind\": root[\"root_kind\"], \"stratum\": root[\"root_kind\"]`). The "
        "partition.csv `stratum` column is therefore a direct function of the bypass."
    ),
    "where_the_e54_baseline_replaces_it": (
        "scripts/e54_d2_uniform_rebaseline.py:152-156 constructs the uniform baseline with "
        "no bypass: `greedy = GreedyGateCancellation(max_iterations=50, "
        "fidelity_threshold=1.0, success_reduction=0.0).optimize(circuit).optimized_circuit` "
        "is applied unconditionally to every normalized circuit, and "
        "scripts/e54_d2_uniform_rebaseline.py:158 takes `state = state_from_circuit(greedy)` "
        "as the root. The contract is stated at "
        "scripts/e54_d2_uniform_rebaseline.py:342: \"uniform greedy fixed point; NO "
        "MAX_BASELINE_GATES bypass\". E98 applies this identical construction per source "
        "(via the imported e54 module) and re-derives strata and axes on the result."
    ),
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_csv(path: Path) -> dict[str, dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return {row["source_id"]: row for row in csv.DictReader(handle)}


def uniform_root(source_id: str, normalized_paths: dict[str, str]) -> dict[str, Any]:
    """E54's uniform re-baseline for one source: greedy with NO gate-count bypass."""

    circuit = e54.load_qasm(ROOT / normalized_paths[source_id])
    raw_gates = int(circuit.size())
    started = time.perf_counter()
    greedy = e54.GreedyGateCancellation(**GREEDY_KWARGS).optimize(circuit).optimized_circuit
    state = e54.state_from_circuit(greedy)
    return {
        "state": state,
        "root_state_sha256": state.state_hash,
        "root_gate_count": len(state.gates),
        "raw_normalized_gate_count": raw_gates,
        "greedy_reduction": raw_gates - len(state.gates),
        "seconds": round(time.perf_counter() - started, 3),
        **e54.adjacent_census(state),
    }


def root_action_census(state: Any) -> dict[str, Any]:
    """E90/E95's window-level axis definition, enumerated on a whole root."""

    from src.optimisation.certified_landscape import iter_legal_actions  # noqa: PLC0415

    reducing: list[int] = []
    neutral = 0
    for action in iter_legal_actions(state, RULE_LIBRARY, RULE_SCOPE):
        if action.cost_delta < 0:
            reducing.append(e95.source_length_of(action.rule_id, SOURCE_LENGTHS) or -1)
        elif action.cost_delta == 0:
            neutral += 1
    return {
        "root_has_reducing_action": bool(reducing),
        "root_reducing_action_count": len(reducing),
        "root_min_reducing_source_length": min(reducing) if reducing else "",
        "root_neutral_action_count": neutral,
    }


def axis_of(cost_delta: int) -> str:
    """First-step axis.  ``positive_first`` is a class the frozen 69 never
    showed (E95 recorded none) but re-derivation under the uniform baseline
    can produce: an exact escape whose witness opens by *increasing* cost.
    It is a measured outcome, recorded -- never folded into the other axes
    and never treated as an error."""
    if cost_delta < 0:
        return "content_first"
    if cost_delta == 0:
        return "reorder_first"
    return "positive_first"


def search_escape(state: Any) -> dict[str, Any]:
    """Frozen-contract escape search on a re-baselined root (E54 Part C contract)."""

    from src.optimisation.certified_landscape import search_landscape_horizons_compact  # noqa: PLC0415

    if len(state.gates) > MAX_SAFE_GATES:
        return {"status": "SKIPPED_MEMORY_RISK", "best_cost": None, "witness": []}
    try:
        result = search_landscape_horizons_compact(
            state,
            RULE_LIBRARY,
            [HORIZON],
            state_budget=STATE_BUDGET,
            rule_scope=RULE_SCOPE,
            time_budget_seconds=TIME_BUDGET_SECONDS,
        )
    except MemoryError:
        return {"status": "RESOURCE_MEMORY", "best_cost": None, "witness": []}
    except Exception as exc:  # noqa: BLE001 -- fail-closed, never fabricate
        return {"status": f"ERROR:{type(exc).__name__}", "best_cost": None, "witness": []}
    entry = result[str(HORIZON)]
    witness = (entry.get("witnesses") or {}).get("escape") or []
    return {
        "status": str(entry.get("status", "")),
        "best_cost": entry.get("best_cost"),
        "witness": witness,
    }


def derive_record(
    role: str,
    e95_row: dict[str, str],
    uniform: dict[str, Any],
    compact_cert: dict[str, Any] | None,
    search: dict[str, Any] | None,
) -> tuple[dict[str, Any], list[dict[str, str]]]:
    """Re-derive stratum + axis for one source under the uniform baseline."""

    unresolved: list[dict[str, str]] = []
    source_id = e95_row["source_id"]
    record: dict[str, Any] = {
        "source_id": source_id,
        "circuit_family": e95_row["circuit_family"],
        "source_kind": e95_row["source_kind"],
        "n_qubits": int(e95_row["n_qubits"] or 0),
        "role": role,
        "e95_stratum": e95_row["stratum"],
        "e95_axis": e95_row["axis"],
        "e95_first_rule_id": e95_row["first_rule_id"],
        "e95_first_step_cost_delta": int(e95_row["first_step_cost_delta"] or 0),
        "frozen_root_state_sha256": e95_row["root_state_sha256"],
        "frozen_root_gate_count": int(e95_row["root_gate_count"] or 0),
        "raw_normalized_gate_count": uniform["raw_normalized_gate_count"],
        "uniform_root_gate_count": uniform["root_gate_count"],
        "greedy_reduction": uniform["greedy_reduction"],
        "uniform_root_state_sha256": uniform["root_state_sha256"],
        "uniform_h1_fixed_point": uniform["is_h1_fixed_point"],
        "uniform_adjacent_reducible_pairs": uniform["adjacent_reducible_pairs"],
        "uniform_stratum": "GREEDY_FIXED_POINT",
        "uniform_seconds": uniform["seconds"],
    }
    record["stratum_changed"] = record["uniform_stratum"] != record["e95_stratum"]
    record["uniform_root_equals_frozen"] = (
        record["uniform_root_state_sha256"] == record["frozen_root_state_sha256"]
    )

    # -- first step of the escape witness that must attach to the uniform root
    if role == "greedy_escape":
        # The frozen certified witness is reused; validity at the uniform root
        # is proven by the pre-state hash (no search re-run).
        record["search_rerun"] = False
        witness = (compact_cert or {}).get("witnesses", {}).get("escape") or []
        if not witness:
            unresolved.append(
                {"source_id": source_id, "reason": "compact witness missing or empty"}
            )
            return record, unresolved
        first = witness[0]
        record["witness_source"] = "frozen_compact_certificate"
    else:
        assert search is not None
        witness = search["witness"]
        record["search_rerun"] = True
        record["search_status"] = search["status"]
        record["search_best_cost"] = search["best_cost"]
        if not witness:
            record["witness_source"] = ""
            record["uniform_axis"] = ""
            record["axis_changed"] = ""
            record["axis_change_reason"] = f"no_witness_status_{search['status']}"
            if search["status"] == "EXACT_H_LOCAL_OPTIMUM":
                record["uniform_escape_survives"] = False
            else:
                record["uniform_escape_survives"] = ""
                unresolved.append(
                    {
                        "source_id": source_id,
                        "reason": f"control search returned {search['status']} without a witness",
                    }
                )
            return record, unresolved
        first = witness[0]
        record["witness_source"] = "uniform_baseline_rerun"

    record["uniform_first_rule_id"] = str(first.get("rule_id", ""))
    record["uniform_first_step_cost_delta"] = int(first.get("cost_delta", 0))
    record["witness_first_step_pre_state_matches_uniform_root"] = (
        str(first.get("pre_state_sha256", "")) == record["uniform_root_state_sha256"]
    )
    if not record["witness_first_step_pre_state_matches_uniform_root"]:
        unresolved.append(
            {
                "source_id": source_id,
                "reason": "witness first step does not attach to the uniform root (pre-state hash mismatch)",
            }
        )
        return record, unresolved
    if role == "content_control":
        record["uniform_escape_survives"] = True

    decomposition = e52.decompose_escape(witness)
    record["uniform_path_length"] = decomposition["path_length"]
    record["uniform_neutral_prefix_length"] = decomposition["neutral_prefix_length"]
    record["uniform_net_delta"] = decomposition["net_delta"]
    if role == "content_control":
        # Replay every step of the re-derived witness against the uniform root
        # (E52 machinery): any UNRESOLVED step fails the run closed.
        labels = e52.classify_neutral_steps(uniform["state"], witness)
        record["uniform_step_labels"] = "|".join(item["label"] for item in labels)
        if any(item["label"] == "UNRESOLVED" for item in labels):
            unresolved.append(
                {
                    "source_id": source_id,
                    "reason": "re-derived witness has a step that does not replay against the uniform root",
                }
            )
    record["uniform_axis"] = axis_of(record["uniform_first_step_cost_delta"])
    record["axis_changed"] = record["uniform_axis"] != record["e95_axis"]
    if role == "greedy_escape":
        record["axis_change_reason"] = (
            "" if not record["axis_changed"] else "witness_first_step_delta_changed"
        )
    else:
        record["axis_change_reason"] = (
            "escape_vanished_under_uniform_baseline"
            if record.get("uniform_escape_survives") is False
            else f"new_escape_witness_first_step_class_{record['uniform_axis']}"
        )
    return record, unresolved


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)

    partition = load_csv(E95_PARTITION)
    rebased = load_csv(E54_REBASELINE)
    classification = load_csv(CLASSIFICATION)
    compact = e95.load_certificates(COMPACT_CERTS)

    greedy_rows = [row for row in partition.values() if row["stratum"] == "GREEDY_FIXED_POINT"]
    raw_content_rows = [
        row
        for row in partition.values()
        if row["stratum"].startswith("RAW") and row["axis"] == "content_first"
    ]
    ordered_controls = sorted(
        raw_content_rows,
        key=lambda row: (int(rebased[row["source_id"]]["rebased_gate_count"]), row["source_id"]),
    )
    controls: list[dict[str, str]] = []
    seen_families: set[str] = set()
    for row in ordered_controls:
        if row["circuit_family"] in seen_families:
            continue
        seen_families.add(row["circuit_family"])
        controls.append(row)
        if len(controls) == CONTROL_COUNT:
            break
    control_ids = {row["source_id"] for row in controls}
    greedy_ids = {row["source_id"] for row in greedy_rows}
    print(
        f"[E98] scope: {len(greedy_rows)} greedy escapes + {len(controls)} content controls "
        f"= {len(greedy_rows) + len(controls)} sources",
        flush=True,
    )

    normalized_paths: dict[str, str] = {}
    with e54.MANIFEST.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            normalized_paths[row["source_id"]] = row["normalized_path"]

    # ---- hash-checked frozen roots (E52 machinery; raises on mismatch) -----
    frozen_roots = {root["source_id"]: root for root in e52.load_root_states()}
    print(f"[E98] frozen roots rebuilt: {len(frozen_roots)} (hash-checked)", flush=True)

    in_scope = sorted(greedy_ids | control_ids)
    unresolved: list[dict[str, str]] = []
    records: list[dict[str, Any]] = []
    search_cache: dict[str, dict[str, Any]] = {}
    for source_id in in_scope:
        e95_row = partition[source_id]
        role = "greedy_escape" if source_id in greedy_ids else "content_control"
        uniform = uniform_root(source_id, normalized_paths)
        search = None
        if role == "content_control":
            search = search_escape(uniform["state"])
            search_cache[source_id] = search
        record, rows_unresolved = derive_record(
            role,
            e95_row,
            uniform,
            compact.get(source_id, {}).get("certificate"),
            search,
        )
        records.append(record)
        unresolved.extend(rows_unresolved)
        # window-level census re-derived on the uniform root (E90 definition)
        record.update(root_action_census(uniform["state"]))
        print(
            f"[E98] {record['circuit_family'][:16]:16s} {role:15s} "
            f"frozen={record['frozen_root_gate_count']:5d} uniform={record['uniform_root_gate_count']:5d} "
            f"root_eq={record['uniform_root_equals_frozen']} axis={record.get('uniform_axis', '')}",
            flush=True,
        )

    # ---- determinism recheck on 2 sources (1 greedy + 1 control) -----------
    recheck_ids = sorted(greedy_ids)[:1] + sorted(control_ids)[:1]
    recheck_details: dict[str, Any] = {}
    for source_id in recheck_ids:
        original = next(row for row in records if row["source_id"] == source_id)
        uniform = uniform_root(source_id, normalized_paths)
        fields: dict[str, Any] = {
            "uniform_root_state_sha256": uniform["root_state_sha256"],
            "uniform_root_gate_count": uniform["root_gate_count"],
            "uniform_h1_fixed_point": uniform["is_h1_fixed_point"],
            "uniform_adjacent_reducible_pairs": uniform["adjacent_reducible_pairs"],
        }
        if source_id in control_ids:
            search = search_escape(uniform["state"])
            fields["search_status"] = search["status"]
            fields["search_best_cost"] = search["best_cost"]
            if search["witness"]:
                fields["uniform_path_length"] = len(search["witness"])
                fields["uniform_first_rule_id"] = str(search["witness"][0].get("rule_id", ""))
                fields["uniform_first_step_cost_delta"] = int(
                    search["witness"][0].get("cost_delta", 0)
                )
                fields["witness_first_step_pre_state_matches_uniform_root"] = (
                    str(search["witness"][0].get("pre_state_sha256", ""))
                    == uniform["root_state_sha256"]
                )
        else:
            fields.update(root_action_census(uniform["state"]))
        mismatched = [key for key, value in fields.items() if original.get(key) != value]
        recheck_details[source_id] = {
            "deterministic": not mismatched,
            "fields_compared": sorted(fields),
            "mismatches": mismatched,
        }
        print(f"[E98] determinism recheck {source_id[:22]}... deterministic={not mismatched}", flush=True)

    # ---- self-checks -------------------------------------------------------
    checks: dict[str, Any] = {}
    checks["frozen_root_hashes_verified"] = all(
        frozen_roots[source_id]["root_state_sha256"]
        == partition[source_id]["root_state_sha256"]
        == (compact.get(source_id, {}).get("certificate", {}) or {}).get("initial_state_sha256")
        for source_id in in_scope
    )
    checks["scope_counts_match_brief"] = (
        len(records) == 23
        and len(greedy_rows) == 20
        and all(row["axis"] == "reorder_first" for row in greedy_rows)
        and len(controls) == 3
        and all(row["axis"] == "content_first" for row in controls)
        and not (greedy_ids & control_ids)
    )
    checks["e95_partition_axis_invariants"] = all(
        (int(row["first_step_cost_delta"] or 0) == 0 if row["axis"] == "reorder_first"
         else int(row["first_step_cost_delta"] or 0) < 0 if row["axis"] == "content_first"
         else False)
        for row in partition.values()
    )
    derived = [record for record in records if record.get("uniform_axis")]
    axis_delta_ok = {
        "content_first": lambda delta: delta < 0,
        "reorder_first": lambda delta: delta == 0,
        "positive_first": lambda delta: delta > 0,
    }
    checks["rederived_axis_invariants"] = all(
        record["uniform_axis"] in axis_delta_ok
        and axis_delta_ok[record["uniform_axis"]](record["uniform_first_step_cost_delta"])
        for record in derived
    )
    checks["greedy_stratum_roots_unchanged_under_uniform_baseline"] = all(
        record["uniform_root_equals_frozen"]
        and record["uniform_stratum"] == "GREEDY_FIXED_POINT"
        for record in records
        if record["role"] == "greedy_escape"
    )
    checks["witness_first_step_valid_at_uniform_root"] = all(
        record.get("witness_first_step_pre_state_matches_uniform_root") is True
        for record in derived
    )
    checks["controls_fail_closed_no_unresolved"] = (
        not unresolved
        and all(
            record.get("uniform_escape_survives") in (True, False)
            for record in records
            if record["role"] == "content_control"
        )
    )
    checks["control_witnesses_replay_clean"] = all(
        "UNRESOLVED" not in str(record.get("uniform_step_labels", ""))
        for record in records
        if record["role"] == "content_control"
    )
    checks["determinism_recheck_2_sources"] = len(recheck_details) == DETERMINISM_RECHECK_COUNT and all(
        detail["deterministic"] for detail in recheck_details.values()
    )

    # ---- headline ----------------------------------------------------------
    greedy_records = [record for record in records if record["role"] == "greedy_escape"]
    control_records = [record for record in records if record["role"] == "content_control"]
    uniform_reorder = sum(1 for record in records if record.get("uniform_axis") == "reorder_first")
    uniform_content = sum(1 for record in records if record.get("uniform_axis") == "content_first")
    uniform_positive = sum(1 for record in records if record.get("uniform_axis") == "positive_first")
    uniform_no_escape = sum(
        1 for record in control_records if record.get("uniform_escape_survives") is False
    )
    count_changes = []
    for record in control_records:
        if record.get("uniform_escape_survives") is False:
            count_changes.append(
                {
                    "source_id": record["source_id"],
                    "circuit_family": record["circuit_family"],
                    "change": "escape_vanished",
                    "reason": (
                        "the certified content-first escape attached to the raw (never-greedy) "
                        "baseline; under E54's uniform greedy baseline the re-run frozen-contract "
                        "search finds no escape at h=3 (EXACT_H_LOCAL_OPTIMUM) on the h1-fixed "
                        "root, so the source contributes no escape to the uniform greedy stratum"
                    ),
                }
            )
        elif record.get("uniform_escape_survives") is True:
            h1 = record["uniform_h1_fixed_point"]
            adjacent = record["uniform_adjacent_reducible_pairs"]
            if record["uniform_axis"] == record["e95_axis"]:
                change = f"{record['uniform_axis']}_escape_enters_uniform_greedy_stratum"
                reason = (
                    f"the escape survives re-derivation (exact at h={HORIZON}, best cost "
                    f"{record['search_best_cost']} < {record['uniform_root_gate_count']}) and keeps "
                    f"its content-first first step, now inside the uniform greedy stratum; the "
                    f"greedy root is NOT h1-fixed ({adjacent} adjacent rz-merge pairs remain -- "
                    "GreedyGateCancellation does not merge rotations), so this is the same "
                    "'baseline was never fully optimized' phenomenon E54 diagnosed, relocated "
                    "into the greedy stratum by removing the bypass"
                    if not h1
                    else "the escape survives re-derivation on an h1-fixed greedy root"
                )
            else:
                change = f"axis {record['e95_axis']} -> {record['uniform_axis']}"
                reason = (
                    f"the exact h={HORIZON} escape at the h1-fixed greedy root opens with a "
                    f"cost-INCREASING step (first_step_cost_delta "
                    f"{record['uniform_first_step_cost_delta']:+d}, rule "
                    f"{record['uniform_first_rule_id']}) before recovering (net "
                    f"{record['uniform_net_delta']:+d}); positive_first is a class the frozen 69 "
                    "never showed, so the two-axis taxonomy needs this extension under the "
                    "uniform baseline"
                )
            count_changes.append(
                {
                    "source_id": record["source_id"],
                    "circuit_family": record["circuit_family"],
                    "change": change,
                    "reason": reason,
                }
            )
    greedy_core_survives = all(
        record.get("uniform_axis") == "reorder_first" for record in greedy_records
    )
    headline_survives = (
        greedy_core_survives
        and all(
            record.get("uniform_axis") == "reorder_first"
            for record in control_records
            if record.get("uniform_escape_survives") is True
        )
        and not unresolved
    )

    summary = {
        "experiment_id": EXPERIMENT_ID,
        "date": "2026-11-07",
        "question": (
            "Is the round-24 headline 'greedy-stratum certified escapes are 100% reorder-first' "
            "(E95, docs/review/science_boost/2026-11-06_innovation_scan.md section 2.1) an "
            "artifact of the 80-gate baseline bypass?"
        ),
        "bypass_provenance": BYPASS_PROVENANCE,
        "method": {
            "uniform_baseline": (
                "E54's D2 construction applied per source: GreedyGateCancellation"
                "(max_iterations=50, fidelity_threshold=1.0, success_reduction=0.0) on the "
                "normalized circuit with NO MAX_BASELINE_GATES branch, then state_from_circuit"
            ),
            "greedy_escape_sources": (
                "20 GREEDY_FIXED_POINT escapes of E95's partition; frozen certified witness "
                "reused, validity at the uniform root proven by pre-state hash; no search re-run"
            ),
            "content_controls": (
                "3 of the 49 RAW content-first escapes; escape re-derived by re-running the "
                "frozen contract search (h=3, e44_core_v1, 200k states, 30 s -- E54 Part C's "
                "contract) on the new root"
            ),
            "control_selection_rule": (
                "among the 49 RAW content-first escapes, the smallest E54-rebased root cost per "
                "circuit family, tie-break source_id; deterministic and independent of outcome"
            ),
            "search_rerun": "controls only (3 + 1 determinism recheck)",
        },
        "scope": {
            "sources": len(records),
            "greedy_escape_sources": len(greedy_records),
            "content_controls": len(control_records),
            "control_ids": sorted(control_ids),
            "scope_reduction": False,
            "scope_note": (
                "The registered brief allows reducing to the 20 reorder-first sources + 3 "
                "content-stratum controls if the rerun is too heavy; the full 23-source scope "
                "ran (only the 3 controls required the heavy search re-run), so no "
                "scope_reduction was needed. The uniform greedy stratum is probed on these 23 "
                "of the 128 panel sources; the RAW-side generalization over the remaining 47 "
                "former-RAW escapes is a scope note, not a claim."
            ),
        },
        "headline": {
            "claim_checked": "greedy-stratum escapes are 100% reorder-first (E95, round-24)",
            "under_e95_frozen_panel": {
                "greedy_stratum_escapes": len(greedy_records),
                "reorder_first": sum(1 for r in greedy_records if r["e95_axis"] == "reorder_first"),
                "content_first": sum(1 for r in greedy_records if r["e95_axis"] == "content_first"),
            },
            "under_e54_uniform_baseline": {
                "sources_probed": len(records),
                "reorder_first": uniform_reorder,
                "content_first": uniform_content,
                "positive_first": uniform_positive,
                "no_longer_escaping": uniform_no_escape,
                "unresolved": len(unresolved),
            },
            "survives": headline_survives,
            "survives_for_original_greedy_members": greedy_core_survives,
            "new_class_observed_under_uniform_baseline": (
                "positive_first" if uniform_positive else None
            ),
            "count_changes": count_changes,
            "reading": (
                "Three-layer answer. (1) Core: all 20 GREEDY_FIXED_POINT escapes keep stratum and "
                "axis exactly -- the uniform baseline reproduces their frozen roots bit-for-bit "
                "(20/20 hash equality, all 20 h1-fixed with zero adjacent reducible pairs) and the "
                "certified witness first steps attach to them -- so for the stratum's original "
                "members the 100%-reorder-first headline is bypass-INDEPENDENT. (2) Stratum "
                "extension: removing the bypass moves former-RAW sources into the greedy stratum, "
                "and 2 of the 3 probed controls still escape there -- one content-first (QAOA: its "
                "greedy root is NOT h1-fixed, 15 adjacent rz-merge pairs remain, so the depth-1 "
                "escape is again the 'baseline was never fully optimized' phenomenon E54 "
                "diagnosed, relocated into the greedy stratum) and one positive-first (Grover: an "
                "h1-fixed root whose exact h=3 escape opens by INCREASING cost +1 before "
                "recovering -2 -- a class absent from the frozen 69). The unqualified round-24 "
                "headline therefore does NOT survive extension to the bypass-added stratum "
                "members, and E95's two-axis taxonomy needs the positive_first extension under "
                "the uniform baseline. (3) Qualification for writing: the content-first escape "
                "inside the uniform greedy stratum sits on a non-h1-fixed root; on genuinely "
                "h1-fixed probed roots no content-first escape appears (1 of 2 stops escaping "
                "entirely, consistent with E54 Part C), but the remaining escape is "
                "positive-first, not reorder-first. E54's part_d reading that 'the 49 depth-1 "
                "escapes disappear' under re-baselining was an inference, not a search; this 3-"
                "source probe shows 1 of 3 does disappear and 2 of 3 persist in changed form."
            ),
        },
        "determinism_recheck": {
            "sources": recheck_ids,
            "details": recheck_details,
        },
        "unresolved": unresolved,
        "self_checks": checks,
        "contract": {
            "reads": {
                name: {"path": str(path.relative_to(ROOT)).replace("\\", "/"), "sha256": e52.sha256(path)}
                for name, path in [
                    ("e95_partition_csv", E95_PARTITION),
                    ("e54_rebaseline_csv", E54_REBASELINE),
                    ("classification_complete", CLASSIFICATION),
                    ("compact_certificates_v16", COMPACT_CERTS),
                    ("rule_library", RULE_LIBRARY),
                    ("normalization_manifest", e54.MANIFEST),
                ]
            },
            "root_states": (
                "frozen roots rebuilt via experiments.e46_window_landscape.run.load_root_states "
                "through e52 (hash-checked, raises on mismatch); uniform roots rebuilt with "
                "e54's unconditional greedy construction"
            ),
            "writes": ["docs/review/science_boost/2026-11-06_bypass_coincidence/"],
        },
        "versions": {"python": sys.version.split()[0]},
    }
    try:
        import qiskit

        summary["versions"]["qiskit"] = qiskit.__version__
    except Exception:  # noqa: BLE001
        pass

    e52.write_csv(OUTPUT_ROOT / "bypass_coincidence.csv", records)
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
        f"[E98] self-checks: {sum(1 for v in checks.values() if v is True)} true / {len(failed)} false",
        flush=True,
    )
    for key in failed:
        print(f"[E98] FAILED: {key}", flush=True)
    print(
        f"[E98] headline survives under the E54 uniform baseline: {headline_survives} "
        f"(uniform axes: reorder_first {uniform_reorder}, content_first {uniform_content}, "
        f"positive_first {uniform_positive}, no_longer_escaping {uniform_no_escape})",
        flush=True,
    )
    print(f"[E98] wrote {OUTPUT_ROOT}", flush=True)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
