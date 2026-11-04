"""E90: which rules the frozen window panel actually uses.

Motivation
----------
The project's price law (``PR-1``, E87) is stated about the *length budget* of a
rewrite library: a library whose maximal source length is ``L`` cannot be
complete past the fragment's Cayley diameter.  That statement is measured on
2-qubit Clifford fragments.  It says nothing about which rules a real circuit
panel actually needs, and the two questions have different answers in principle.

This experiment measures the second one directly, on the frozen E46 panel:
every window of every root listing, every legal action under the declared rule
scope ``e44_core_v1``, and a census of

* which rule ids ever fire at all,
* which of them fire as a *reducing* action (``cost_delta < 0``),
* the source-length distribution of the firing rules,
* and how that distribution splits by the frozen E46 status
  (``EXACT_ESCAPE`` vs ``LOCAL_OPTIMUM``) and by root stratum.

The question it answers is not "is the library incomplete" but "**is the
library's length budget the constraint that binds on this panel**".  A library
whose length-3/4/5 rules never fire is not length-limited on this workload, no
matter what the fragment price says.

Contract
--------
Read-only on frozen inputs: the E46 root states (hash-checked by
``load_root_states``), the E46 ``window_results.csv``, and the frozen rule
library (sha256 recorded).  Windows are rebuilt with the same
``window_state`` helper the E46 runner uses, so the listings are the frozen
ones and not a re-derivation.  Nothing under ``data/``, ``release/`` or
``docs/manuscript/`` is written.

Outputs (``docs/review/science_boost/2026-11-04_rule_utilisation/``)
    window_demand.csv    one row per unique (source, width, start) window
    rule_usage.csv       one row per rule id in the declared scope
    summary.json         contract, cross-tabs, self-checks, provenance
    MANIFEST.json        sha256 of every artifact
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from experiments.e46_window_landscape.run import (  # noqa: E402
    RULE_SCOPE,
    load_root_states,
    window_state,
)
from src.optimisation.certified_landscape import (  # noqa: E402
    filter_rule_scope,
    legal_actions,
    _rule_library,
)

OUTPUT_ROOT = ROOT / "docs" / "review" / "science_boost" / "2026-11-04_rule_utilisation"
RULE_LIBRARY = ROOT / "data" / "v13" / "e43_quartz_rule_import" / "generation_a" / "rule_library.json"
WINDOW_RESULTS = ROOT / "data" / "v16" / "e46_window_landscape" / "window_results.csv"
EXPERIMENT_ID = "E90_RULE_UTILISATION_2026_11_04"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def rule_source_lengths() -> tuple[dict[str, int], dict[str, str], dict[str, int]]:
    """rule_id -> source gate count, rule family, cost delta (declared scope only)."""

    quartz, _ = _rule_library(RULE_LIBRARY)
    scoped = filter_rule_scope(quartz, RULE_SCOPE)
    lengths: dict[str, int] = {}
    families: dict[str, str] = {}
    deltas: dict[str, int] = {}
    for rule in scoped:
        rule_id = rule["rule_id"]
        lengths[rule_id] = int(rule["source_gate_count"])
        families[rule_id] = str(rule.get("rule_family", "quartz_v1"))
        deltas[rule_id] = int(rule.get("cost_delta", 0))
    return lengths, families, deltas


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit-sources", type=int, default=0)
    parser.add_argument("--deadline-seconds", type=float, default=3600.0)
    args = parser.parse_args()

    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()

    lengths, families, deltas = rule_source_lengths()
    print(f"[E90] declared scope: {len(lengths)} quartz rules")

    # frozen status per (source, width, start, horizon)
    status: dict[tuple[str, int, int, int], dict[str, str]] = {}
    with WINDOW_RESULTS.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            key = (row["source_id"], int(row["window_width"]), int(row["window_start"]), int(row["horizon"]))
            status[key] = {
                "status": row["status"],
                "escape_depth": row["escape_depth"],
                "window_cost": row["window_cost"],
                "family": row["circuit_family"],
                "root_kind": row["root_kind"],
            }

    roots = {row["source_id"]: row for row in load_root_states()}
    print(f"[E90] roots rebuilt and hash-checked: {len(roots)}")

    unique_windows = sorted({(key[0], key[1], key[2]) for key in status})
    if args.limit_sources:
        keep = {row["source_id"] for row in list(roots.values())[: args.limit_sources]}
        unique_windows = [w for w in unique_windows if w[0] in keep]
    print(f"[E90] unique windows: {len(unique_windows)}")

    fired_any: Counter[str] = Counter()
    fired_reducing: Counter[str] = Counter()
    rows: list[dict[str, Any]] = []
    for index, (source_id, width, start) in enumerate(unique_windows, start=1):
        if time.perf_counter() - started > args.deadline_seconds:
            raise SystemExit("deadline_exceeded")
        root = roots[source_id]
        state = window_state(root["state"], start, width)
        actions = legal_actions(state, RULE_LIBRARY, RULE_SCOPE)
        reducing = [action for action in actions if action.cost_delta < 0]
        for action in actions:
            fired_any[action.rule_id] += 1
        for action in reducing:
            fired_reducing[action.rule_id] += 1
        # pair_v1 rules are not in the quartz library; their source length is 2
        def source_length(rule_id: str) -> int:
            if rule_id.startswith("pair_v1"):
                return 2
            if rule_id.startswith("exchange"):
                return 2
            return lengths.get(rule_id, -1)

        min_reducing_length = min((source_length(a.rule_id) for a in reducing), default=None)
        statuses = [status[(source_id, width, start, h)]["status"] for h in (2, 3) if (source_id, width, start, h) in status]
        rows.append(
            {
                "source_id": source_id,
                "circuit_family": status[(source_id, width, start, 2)]["family"],
                "root_kind": status[(source_id, width, start, 2)]["root_kind"],
                "window_width": width,
                "window_start": start,
                "window_cost": status[(source_id, width, start, 2)]["window_cost"],
                "actions_total": len(actions),
                "actions_reducing": len(reducing),
                "min_reducing_source_length": "" if min_reducing_length is None else min_reducing_length,
                "quartz_actions": sum(1 for a in actions if a.rule_id.startswith("quartz")),
                "pair_actions": sum(1 for a in actions if a.rule_id.startswith("pair_v1")),
                "exchange_actions": sum(1 for a in actions if a.rule_id.startswith("exchange")),
                "status_h2": status[(source_id, width, start, 2)]["status"],
                "status_h3": status[(source_id, width, start, 3)]["status"],
                "any_escape": "EXACT_ESCAPE" if "EXACT_ESCAPE" in statuses else "LOCAL_OPTIMUM",
            }
        )
        if index % 5000 == 0:
            print(f"[E90] {index}/{len(unique_windows)} windows, {time.perf_counter() - started:.0f}s", flush=True)

    # ---- cross-tabs --------------------------------------------------------
    def rate(numerator: int, denominator: int) -> float | None:
        return round(numerator / denominator, 6) if denominator else None

    by_status: dict[str, Any] = {}
    for label in ("EXACT_ESCAPE", "LOCAL_OPTIMUM"):
        subset = [row for row in rows if row["any_escape"] == label]
        by_status[label] = {
            "windows": len(subset),
            "with_reducing_action": sum(1 for row in subset if row["actions_reducing"] > 0),
            "with_quartz_action": sum(1 for row in subset if row["quartz_actions"] > 0),
            "length_histogram": dict(sorted(Counter(row["min_reducing_source_length"] for row in subset if row["min_reducing_source_length"] != "").items())),
        }
    by_stratum: dict[str, Any] = {}
    for label in ("GREEDY_FIXED_POINT", "RAW_NORMALIZED_OVER_BASELINE_BUDGET"):
        subset = [row for row in rows if row["root_kind"] == label]
        by_stratum[label] = {
            "windows": len(subset),
            "with_reducing_action": sum(1 for row in subset if row["actions_reducing"] > 0),
            "min_reducing_length_histogram": dict(sorted(Counter(row["min_reducing_source_length"] for row in subset if row["min_reducing_source_length"] != "").items())),
        }

    scope_size = len(lengths)
    ever_fired = {rule_id for rule_id in fired_any if rule_id in lengths}
    ever_reducing = {rule_id for rule_id in fired_reducing if rule_id in lengths}
    usage_rows = [
        {
            "rule_id": rule_id,
            "rule_family": families[rule_id],
            "source_gate_count": lengths[rule_id],
            "declared_cost_delta": deltas[rule_id],
            "times_fired": fired_any.get(rule_id, 0),
            "times_fired_reducing": fired_reducing.get(rule_id, 0),
        }
        for rule_id in sorted(lengths)
    ]
    usage_rows.sort(key=lambda row: (-row["times_fired"], row["rule_id"]))

    firing_by_length: dict[str, Any] = {}
    for length in sorted({lengths[rule_id] for rule_id in lengths}):
        ids = [rule_id for rule_id in lengths if lengths[rule_id] == length]
        firing_by_length[str(length)] = {
            "rules_in_scope": len(ids),
            "rules_that_fire": sum(1 for rule_id in ids if fired_any.get(rule_id, 0) > 0),
            "rules_that_fire_reducing": sum(1 for rule_id in ids if fired_reducing.get(rule_id, 0) > 0),
        }

    neutral_first = [row for row in rows if row["any_escape"] == "EXACT_ESCAPE" and row["actions_reducing"] == 0]
    checks = {
        "windows_processed": len(rows) == len(unique_windows),
        "every_window_has_status": all(row["status_h2"] and row["status_h3"] for row in rows),
        # Not an assumption: round 19 established that a horizon search can escape a
        # window through a cost-neutral move first.  The check asserts the *counting*
        # consistency of that class, and the class itself is a finding.
        "neutral_first_escapes_are_counted": all(
            row["actions_total"] > 0 for row in neutral_first
        ),
        "local_optima_have_no_reducing_action": all(
            row["actions_reducing"] == 0 for row in rows if row["any_escape"] == "LOCAL_OPTIMUM"
        ),
        "reducing_lengths_within_scope": all(
            row["min_reducing_source_length"] in ("", 2, 3, 4, 5) for row in rows
        ),
    }

    summary = {
        "experiment_id": EXPERIMENT_ID,
        "contract": {
            "rule_library": str(RULE_LIBRARY.relative_to(ROOT)),
            "rule_library_sha256": sha256_file(RULE_LIBRARY),
            "window_results": str(WINDOW_RESULTS.relative_to(ROOT)),
            "window_results_sha256": sha256_file(WINDOW_RESULTS),
            "rule_scope": RULE_SCOPE,
            "roots": "rebuilt via load_root_states (hash-checked against the v14 certificates)",
            "writes": ["docs/review/science_boost/2026-11-04_rule_utilisation/"],
        },
        "totals": {
            "unique_windows": len(rows),
            "windows_with_any_action": sum(1 for row in rows if row["actions_total"] > 0),
            "windows_with_reducing_action": sum(1 for row in rows if row["actions_reducing"] > 0),
            "windows_with_quartz_action": sum(1 for row in rows if row["quartz_actions"] > 0),
            "windows_without_any_action": sum(1 for row in rows if row["actions_total"] == 0),
            "escapes_without_reducing_action": len(neutral_first),
            "escapes_without_reducing_action_rate": rate(len(neutral_first), sum(1 for row in rows if row["any_escape"] == "EXACT_ESCAPE")),
            "rules_in_declared_scope": scope_size,
            "rules_that_fire_at_all": len(ever_fired),
            "rules_that_fire_as_reducing": len(ever_reducing),
            "rule_utilisation": rate(len(ever_fired), scope_size),
        },
        "firing_by_source_length": firing_by_length,
        "by_e46_status": by_status,
        "by_root_stratum": by_stratum,
        "self_checks": checks,
        "runtime_seconds": round(time.perf_counter() - started, 1),
    }

    with (OUTPUT_ROOT / "window_demand.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    with (OUTPUT_ROOT / "rule_usage.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(usage_rows[0]))
        writer.writeheader()
        writer.writerows(usage_rows)
    with (OUTPUT_ROOT / "summary.json").open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2, sort_keys=True)

    manifest = {
        "experiment_id": EXPERIMENT_ID,
        "artifacts": {
            path.name: {"sha256": sha256_file(path), "bytes": path.stat().st_size}
            for path in sorted(OUTPUT_ROOT.glob("*"))
            if path.is_file() and path.name != "MANIFEST.json"
        },
    }
    with (OUTPUT_ROOT / "MANIFEST.json").open("w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2, sort_keys=True)

    print(json.dumps(summary["totals"], indent=1))
    print(json.dumps(summary["by_e46_status"], indent=1))
    failed = [key for key, value in checks.items() if value is False]
    print(f"[E90] self-checks: {len(checks) - len(failed)}/{len(checks)} true")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
