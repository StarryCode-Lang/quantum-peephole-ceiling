"""E46: window-local certified landscape profiles over the frozen E45 panel.

The v14 exact panels certify whole-listing horizon neighborhoods.  E46 asks a
complementary, position-resolved question: along the search root listing (the
greedy fixed point of each panel input, raw for oversized inputs), which
windows of consecutive gates are themselves exact local optima within a finite
horizon, and which hide a certified escape?

A window state is a contiguous slice of the root listing.  Its landscape is
searched with the same certified engine, rule scope, and replay machinery as
E45, so every window claim is exact within the declared horizon or explicitly
resource-truncated.  Window claims are window-local by construction: actions
that consume gates outside the slice are invisible to the window.

The panel, root states, and root hashes are identical to the E45 fixed panel;
every root state is hash-checked against the frozen v14 certificate before
searching.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import multiprocessing
import os
import statistics
import sys
import time
from pathlib import Path
from typing import Any

from qiskit import qasm2

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments.e45_development_grid.exact_development import (  # noqa: E402
    atomic_text,
    fixed_panel,
    write_csv,
)
from experiments.e45_development_grid.run import (  # noqa: E402
    MAX_BASELINE_GATES,
    RULE_LIBRARY,
    state_from_circuit,
)
from src.optimisation.certified_landscape import (  # noqa: E402
    LandscapeState,
    replay_actions,
    search_landscape_horizons_compact,
)
from src.optimisation.phase1.greedy import GreedyGateCancellation  # noqa: E402

OUTPUT_ROOT = ROOT / "data" / "v15" / "e46_window_landscape"
COMPACT_CERTIFICATES = ROOT / "data" / "v14" / "e45_full_development" / "certificates.jsonl"
COMPACT_MANIFEST = ROOT / "data" / "v14" / "e45_full_development" / "normalization_manifest.csv"
RULE_SCOPE = "e44_core_v1"
EXPERIMENT_ID = os.environ.get("E46_EXPERIMENT_ID_OVERRIDE", "E46_WINDOW_LANDSCAPE_V15")

WINDOW_WIDTHS = (8, 16)
HORIZONS = (2, 3)
WINDOW_STATE_BUDGET = 20_000
WINDOW_TIME_BUDGET_SECONDS = 10.0
MAX_WINDOWS_PER_INPUT = 1024
WORKERS = 8


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def window_starts(gate_count: int, width: int) -> list[int]:
    if gate_count < width:
        return []
    stride = max(1, -(-gate_count // MAX_WINDOWS_PER_INPUT))
    return list(range(0, gate_count - width + 1, stride))


def window_state(state: LandscapeState, start: int, width: int) -> LandscapeState:
    return LandscapeState(state.num_qubits, state.gates[start : start + width]).normalized()


def load_root_states(root_ordering: str = "greedy") -> list[dict[str, Any]]:
    """Rebuild the E45 root states and hash-check them against v14 certificates.

    ``root_ordering="wcl"`` reorders each root listing into wire-consecutive
    order via ``state_wcl`` (unitarily equivalent, deterministic) before
    windowing; the root hash contract still pins the frozen pre-reorder state.
    """

    frozen = {
        json.loads(line)["source_id"]: json.loads(line)["certificate"]["initial_state_sha256"]
        for line in COMPACT_CERTIFICATES.read_text(encoding="utf-8").splitlines()
        if line.strip()
    }
    normalized_paths: dict[str, str] = {}
    with COMPACT_MANIFEST.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            normalized_paths[row["source_id"]] = row["normalized_path"]

    roots: list[dict[str, Any]] = []
    for source in fixed_panel():
        source_id = source["source_id"]
        expected = frozen.get(source_id)
        if expected is None:
            raise RuntimeError(f"source_missing_from_frozen_panel:{source_id}")
        circuit = qasm2.loads((ROOT / normalized_paths[source_id]).read_text(encoding="utf-8"))
        if int(circuit.size()) > MAX_BASELINE_GATES:
            baseline = circuit
            root_kind = "RAW_NORMALIZED_OVER_BASELINE_BUDGET"
        else:
            baseline = GreedyGateCancellation(
                max_iterations=50,
                fidelity_threshold=1.0,
                success_reduction=0.0,
            ).optimize(circuit).optimized_circuit
            root_kind = "GREEDY_FIXED_POINT"
        state = state_from_circuit(baseline)
        if state.state_hash != expected:
            raise RuntimeError(f"root_state_hash_mismatch:{source_id}")
        root_kind_value = root_kind
        if root_ordering == "wcl":
            from src.optimisation.certified_landscape import state_wcl

            state = state_wcl(state)
            root_kind_value = f"{root_kind}_WCL"
        roots.append(
            {
                "source_id": source_id,
                "source_kind": source["source_kind"],
                "circuit_id": source["circuit_id"],
                "circuit_family": source["circuit_family"],
                "n_qubits": source["n_qubits"],
                "root_state_sha256": expected,
                "root_kind": root_kind_value,
                "root_gate_count": len(state.gates),
                "state": state,
            }
        )
    return roots


def search_input(item: dict[str, Any]) -> dict[str, Any]:
    """Search every sampled window of one root state for all (width, horizon) configs."""

    os.environ.setdefault("OMP_NUM_THREADS", "1")
    state: LandscapeState = item.pop("state")
    rows: list[dict[str, Any]] = []
    escape_certificates: list[dict[str, Any]] = []
    stored_configs: set[tuple[int, int]] = set()
    for width in WINDOW_WIDTHS:
        for start in window_starts(len(state.gates), width):
            window = window_state(state, start, width)
            for horizon in HORIZONS:
                started = time.perf_counter()
                certificate = search_landscape_horizons_compact(
                    window,
                    RULE_LIBRARY,
                    (horizon,),
                    state_budget=WINDOW_STATE_BUDGET,
                    rule_scope=RULE_SCOPE,
                    time_budget_seconds=WINDOW_TIME_BUDGET_SECONDS,
                )[str(horizon)]
                runtime = time.perf_counter() - started
                del runtime  # wall-clock timing is intentionally not persisted; outputs stay byte-deterministic
                rows.append(
                    {
                        "experiment_id": EXPERIMENT_ID,
                        "source_id": item["source_id"],
                        "circuit_family": item["circuit_family"],
                        "root_state_sha256": item["root_state_sha256"],
                        "root_kind": item["root_kind"],
                        "root_gate_count": item["root_gate_count"],
                        "window_width": width,
                        "window_start": start,
                        "window_cost": window.cost,
                        "horizon": horizon,
                        "status": certificate["status"],
                        "escape_depth": certificate["escape_depth"],
                        "best_cost": certificate["best_cost"],
                        "barrier_height": certificate["barrier_height"],
                        "states_seen": certificate["states_seen"],
                        "resource_reason": certificate.get("resource_reason", ""),
                    }
                )
                if certificate["status"] == "EXACT_ESCAPE":
                    witness = certificate["witnesses"]["escape"]
                    replay = replay_actions(window, witness, RULE_LIBRARY, RULE_SCOPE)
                    if not replay.get("accepted"):
                        raise RuntimeError(
                            f"window_witness_replay_failed:{item['source_id']}:{width}:{start}:{horizon}"
                        )
                    if (width, horizon) not in stored_configs:
                        stored_configs.add((width, horizon))
                        escape_certificates.append(
                            {
                                "source_id": item["source_id"],
                                "window_width": width,
                                "window_start": start,
                                "window_state_sha256": window.state_hash,
                                "horizon": horizon,
                                "certificate": certificate,
                            }
                        )
    return {"item": item, "rows": rows, "escape_certificates": escape_certificates}


def run(
    output_root: Path = OUTPUT_ROOT,
    workers: int = WORKERS,
    source_limit: int | None = None,
    root_ordering: str = "greedy",
) -> dict[str, Any]:
    output_root = output_root.resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    roots = load_root_states(root_ordering)
    if source_limit is not None:
        roots = roots[:source_limit]

    payloads = [{key: value for key, value in item.items()} for item in roots]
    if workers > 1:
        with multiprocessing.Pool(processes=workers) as pool:
            results = pool.map(search_input, payloads)
    else:
        results = [search_input(item) for item in payloads]

    rows: list[dict[str, Any]] = []
    escapes: list[dict[str, Any]] = []
    for result in results:
        rows.extend(result["rows"])
        escapes.extend(result["escape_certificates"])

    summaries: list[dict[str, Any]] = []
    for item, result in zip(roots, results):
        for width in WINDOW_WIDTHS:
            for horizon in HORIZONS:
                selected = [
                    row
                    for row in result["rows"]
                    if row["window_width"] == width and row["horizon"] == horizon
                ]
                if not selected:
                    summaries.append(
                        {
                            "source_id": item["source_id"],
                            "circuit_family": item["circuit_family"],
                            "root_state_sha256": item["root_state_sha256"],
                            "root_kind": item["root_kind"],
                            "root_gate_count": item["root_gate_count"],
                            "window_width": width,
                            "horizon": horizon,
                            "window_count": 0,
                            "escape_count": 0,
                            "local_optimum_count": 0,
                            "resource_truncated_count": 0,
                            "escape_rate": "",
                            "first_escape_position": "",
                            "mean_escape_depth": "",
                        }
                    )
                    continue
                escape_rows = [row for row in selected if row["status"] == "EXACT_ESCAPE"]
                depths = [row["escape_depth"] for row in escape_rows]
                summaries.append(
                    {
                        "source_id": item["source_id"],
                        "circuit_family": item["circuit_family"],
                        "root_state_sha256": item["root_state_sha256"],
                        "root_kind": item["root_kind"],
                        "root_gate_count": item["root_gate_count"],
                        "window_width": width,
                        "horizon": horizon,
                        "window_count": len(selected),
                        "escape_count": len(escape_rows),
                        "local_optimum_count": sum(
                            row["status"] == "EXACT_H_LOCAL_OPTIMUM" for row in selected
                        ),
                        "resource_truncated_count": sum(
                            row["status"]
                            in {"WITNESS_CERTIFIED_SEARCH_INCOMPLETE", "RESOURCE_BOUNDED_NO_WITNESS"}
                            for row in selected
                        ),
                        "escape_rate": len(escape_rows) / len(selected),
                        "first_escape_position": escape_rows[0]["window_start"] if escape_rows else "",
                        "mean_escape_depth": statistics.fmean(depths) if depths else "",
                    }
                )

    protocol = {
        "experiment_id": EXPERIMENT_ID,
        "purpose": (
            "Position-resolved certified landscape: which windows of the E45 root "
            "listings are exact local optima within a finite horizon and which hide "
            "a certified escape.  Window claims are window-local by construction."
        ),
        "panel": {
            "source": "E45 fixed panel (96 E39 + 32 E44 sources in screening order)",
            "root_states": "greedy fixed point per input; raw normalized listing when the input exceeds the baseline gate budget",
            "root_ordering": root_ordering,
            "root_hash_contract": "every root state hash is checked against the frozen v14 compact certificate",
            "source_count": len(roots),
        },
        "window_contract": {
            "definition": "contiguous slice of the root listing, normalized per gate",
            "window_widths": list(WINDOW_WIDTHS),
            "sampling": f"stride 1 up to {MAX_WINDOWS_PER_INPUT} windows per input, then ceil(gates/{MAX_WINDOWS_PER_INPUT})",
            "boundary_semantics": "actions consuming gates outside the slice are invisible to the window",
        },
        "search_contract": {
            "engine": "search_landscape_horizons_compact (same certified engine as E45)",
            "rule_scope": RULE_SCOPE,
            "rule_library_sha256": sha256(RULE_LIBRARY),
            "horizons": list(HORIZONS),
            "state_budget": WINDOW_STATE_BUDGET,
            "time_budget_seconds": WINDOW_TIME_BUDGET_SECONDS,
            "witness_replay": "every EXACT_ESCAPE window witness is replayed in-runner; failure aborts",
            "witness_storage": "only the first escape certificate per (source, width, horizon) is stored; the deterministic runner regenerates the complete witness set on demand",
            "reverse_edges": "not used; rank-increasing reverse Quartz parameter-splitting remains illegal",
        },
        "resource_contracts": {
            "workers": workers,
            "determinism": "per-window results are deterministic; output ordering is sorted by source, width, start, horizon",
        },
    }
    atomic_text(output_root / "protocol.json", json.dumps(protocol, indent=2, sort_keys=True) + "\n")

    rows.sort(key=lambda row: (row["source_id"], row["window_width"], row["window_start"], row["horizon"]))
    write_csv(output_root / "window_results.csv", rows)
    summaries.sort(key=lambda row: (row["source_id"], row["window_width"], row["horizon"]))
    write_csv(output_root / "input_summaries.csv", summaries)
    atomic_text(
        output_root / "escape_certificates.jsonl",
        "".join(json.dumps(item, sort_keys=True) + "\n" for item in escapes),
    )

    total_windows = len(rows)
    truncated = sum(
        row["status"] in {"WITNESS_CERTIFIED_SEARCH_INCOMPLETE", "RESOURCE_BOUNDED_NO_WITNESS"}
        for row in rows
    )
    by_config: dict[str, dict[str, Any]] = {}
    for width in WINDOW_WIDTHS:
        for horizon in HORIZONS:
            selected = [
                row for row in rows if row["window_width"] == width and row["horizon"] == horizon
            ]
            escape_rows = [row for row in selected if row["status"] == "EXACT_ESCAPE"]
            by_config[f"w{width}_h{horizon}"] = {
                "window_count": len(selected),
                "escape_count": len(escape_rows),
                "local_optimum_count": sum(
                    row["status"] == "EXACT_H_LOCAL_OPTIMUM" for row in selected
                ),
                "escape_rate": len(escape_rows) / len(selected) if selected else 0.0,
                "inputs_with_escape": len({row["source_id"] for row in escape_rows}),
            }
    receipt = {
        "status": "PANEL_COMPLETE" if truncated == 0 else "PANEL_COMPLETE_WITH_RESOURCE_BOUNDARY",
        "experiment_id": EXPERIMENT_ID,
        "protocol_sha256": sha256(output_root / "protocol.json"),
        "window_results_sha256": sha256(output_root / "window_results.csv"),
        "input_summaries_sha256": sha256(output_root / "input_summaries.csv"),
        "escape_certificates_sha256": sha256(output_root / "escape_certificates.jsonl"),
        "source_count": len(roots),
        "window_rows": total_windows,
        "escape_row_count": sum(row["status"] == "EXACT_ESCAPE" for row in rows),
        "escape_certificate_count": len(escapes),
        "witness_storage": "FIRST_ESCAPE_PER_SOURCE_AND_CONFIG; full witness sets are deterministically regenerable by the runner",
        "resource_truncated_windows": truncated,
        "by_config": by_config,
    }
    atomic_text(output_root / "receipt.json", json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", type=Path, default=OUTPUT_ROOT)
    parser.add_argument("--workers", type=int, default=WORKERS)
    parser.add_argument("--source-limit", type=int)
    parser.add_argument("--experiment-id")
    parser.add_argument("--root-ordering", choices=("greedy", "wcl"), default="greedy")
    args = parser.parse_args()
    if args.experiment_id:
        # spawn workers re-import this module, so the override must be visible
        # in the environment before the pool is created
        os.environ["E46_EXPERIMENT_ID_OVERRIDE"] = args.experiment_id
        globals()["EXPERIMENT_ID"] = args.experiment_id
    print(
        json.dumps(
            run(args.output_root, args.workers, args.source_limit, args.root_ordering),
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
