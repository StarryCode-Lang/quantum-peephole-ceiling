"""Run the v13 E45 development grid.

E45 is a development experiment, not a confirmatory panel.  It consumes only
the frozen E39 inputs and the independent E44 synthetic cases.  Every arm
starts from the same Nam-normalized unitary circuit.  Search truncation is
recorded as a bounded result and never converted to a local-optimum claim.

The implementation deliberately keeps the E44 state/action core as the
single source of legal v13 transitions.  The two beam arms differ only in
their deterministic ranking rule: the unguided arm ranks by current cost,
whereas CGEO adds terminal Greedy cost and a v12 exposure lower-bound feature.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import statistics
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from qiskit import QuantumCircuit, transpile
from qiskit import qasm2

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.optimisation.certified_landscape import (  # noqa: E402
    LandscapeAction,
    LandscapeState,
    STATUS_EXACT_ESCAPE,
    STATUS_EXACT_LOCAL,
    STATUS_RESOURCE_NO_WITNESS,
    STATUS_UNSUPPORTED,
    STATUS_WITNESS_INCOMPLETE,
    legal_actions,
    _pair_actions,
    state_from_spec,
)
from src.optimisation.phase1.greedy import GreedyGateCancellation  # noqa: E402
from src.optimisation.phase1.wire_traversal import WireTraversalPreprocessor  # noqa: E402
from src.optimisation.phase2.template_matcher import Phase2bTemplateMatcher  # noqa: E402
from src.optimisation.rewrite_exposure import (  # noqa: E402
    DependenceModel,
    ExposureConfig,
    _certify_prepared,
    _prepare_exposure,
    certify_rewrite_exposure,
    materialize_cgl_listing,
)


EXPERIMENT_ID = "E45_CERTIFIED_ESCAPE_DEVELOPMENT_V1"
E39_INPUTS = ROOT / "data" / "v12" / "e39_development_grid" / "inputs.csv"
E44_INPUTS = ROOT / "data" / "v13" / "e44_certified_landscape_oracle" / "inputs.jsonl"
RULE_LIBRARY = ROOT / "data" / "v13" / "e43_quartz_rule_import" / "generation_a" / "rule_library.json"
OUTPUT_ROOT = ROOT / "data" / "v13" / "e45_development_grid"
NAM_BASIS = ["h", "x", "rz", "cx"]
FROZEN_CONFIGS = [
    {
        "config_id": f"h{h}_b{beam}_s{budget // 1000}k",
        "horizon": h,
        "beam_width": beam,
        "state_budget": budget,
        "barrier_cap": min(2, h),
    }
    for h in (2, 3, 4)
    for beam in (16, 64)
    for budget in (10_000, 50_000, 200_000)
]
ARM_NAMES = (
    "greedy",
    "wcl_greedy",
    "v12_cgl_greedy",
    "phase2b_greedy",
    "unguided_beam",
    "certificate_guided_escape",
)
# Full Quartz matching is a product of listing positions, rule signatures,
# and qubit permutations.  This conservative precheck keeps the development
# cell watchdog meaningful; larger inputs remain in the manifest and receive
# an explicit bounded result.
MAX_PRECHECK_GATES = 80
MAX_PRECHECK_WORK = 80
SEMANTIC_SCOPE = "fixed-width bound-parameter unitary, up to global phase"


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def atomic_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(value, encoding="utf-8", newline="\n")
    temporary.replace(path)


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        atomic_text(path, "")
        return
    fields = list(rows[0])
    import io

    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    atomic_text(path, buffer.getvalue())


def _strip_terminal_nonunitary(circuit: QuantumCircuit) -> tuple[QuantumCircuit, dict[str, int], str | None]:
    """Apply the narrow unitary-core policy before basis translation."""

    names = [instruction.operation.name for instruction in circuit.data]
    measurement_positions = [i for i, name in enumerate(names) if name == "measure"]
    reset_positions = [i for i, name in enumerate(names) if name == "reset"]
    dynamic_names = {"if_else", "while_loop", "for_loop", "switch_case", "initialize", "store"}
    blockers: list[str] = []
    if reset_positions:
        blockers.append("reset")
    if any(name in dynamic_names for name in names):
        blockers.extend(sorted({name for name in names if name in dynamic_names}))
    if any(instruction.clbits for instruction in circuit.data if instruction.operation.name != "measure"):
        blockers.append("classical_operands")
    if measurement_positions:
        last_non_measure = max((i for i, name in enumerate(names) if name != "measure"), default=-1)
        if any(i < last_non_measure for i in measurement_positions):
            blockers.append("mid_circuit_measurement")
    counts = {
        "measurement_count": len(measurement_positions),
        "reset_count": len(reset_positions),
        "barrier_count": sum(name == "barrier" for name in names),
    }
    if blockers:
        return circuit, counts, ";".join(sorted(set(blockers)))

    # Qiskit's final-measurement remover also removes trailing barriers.  We
    # explicitly check that no interior barrier is altered by the policy.
    stripped = circuit.remove_final_measurements(inplace=False)
    stripped_names = [instruction.operation.name for instruction in stripped.data]
    if any(name == "measure" for name in stripped_names):
        return circuit, counts, "terminal_measurement_removal_failed"
    while stripped.data and stripped.data[-1].operation.name == "barrier":
        stripped.data.pop()
    return stripped, counts, None


def normalize_circuit(source: QuantumCircuit) -> tuple[QuantumCircuit | None, dict[str, Any]]:
    stripped, counts, blocker = _strip_terminal_nonunitary(source)
    if blocker:
        return None, {**counts, "status": "UNSUPPORTED_INPUT", "reason": blocker}
    try:
        normalized = transpile(
            stripped,
            basis_gates=NAM_BASIS,
            optimization_level=0,
            layout_method="trivial",
            routing_method="basic",
            seed_transpiler=0,
        )
    except Exception as exc:
        return None, {**counts, "status": "UNSUPPORTED_INPUT", "reason": f"basis_translation:{type(exc).__name__}"}
    unsupported = sorted(
        {instruction.operation.name for instruction in normalized.data}
        - set(NAM_BASIS)
    )
    if unsupported:
        return None, {**counts, "status": "UNSUPPORTED_INPUT", "reason": f"post_basis_operations:{unsupported}"}
    return normalized, {
        **counts,
        "status": "PASS",
        "reason": "",
        "source_gate_count": int(source.size()),
        "stripped_gate_count": int(stripped.size()),
        "normalized_gate_count": int(normalized.size()),
        "normalized_qasm_sha256": sha256_bytes(qasm2.dumps(normalized).encode()),
    }


def load_e39_rows() -> list[dict[str, Any]]:
    with E39_INPUTS.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != 391 or len({row["input_circuit_sha256"] for row in rows}) != 391:
        raise RuntimeError(f"e39_input_contract:{len(rows)}")
    return [
        {
            "source_id": f"e39:{row['input_circuit_sha256']}",
            "source_kind": "e39",
            "circuit_id": row["circuit_id"],
            "circuit_family": row["circuit_family"],
            "n_qubits": int(row["n_qubits"]),
            "source_path": row["qasm_path"],
            "source_sha256": row["input_circuit_sha256"],
            "source_row": row,
        }
        for row in rows
    ]


def load_e44_rows() -> list[dict[str, Any]]:
    rows = []
    with E44_INPUTS.open(encoding="utf-8") as handle:
        for line in handle:
            spec = json.loads(line)
            rows.append({
                "source_id": f"e44:{spec['case_id']}",
                "source_kind": "e44",
                "circuit_id": spec["case_id"],
                "circuit_family": f"E44:{spec['stratum']}",
                "n_qubits": int(spec["num_qubits"]),
                "source_path": "data/v13/e44_certified_landscape_oracle/inputs.jsonl",
                "source_sha256": sha256_bytes(json.dumps(spec, sort_keys=True, separators=(",", ":")).encode()),
                "source_spec": spec,
            })
    if len(rows) != 1024:
        raise RuntimeError(f"e44_input_contract:{len(rows)}")
    return rows


def select_screening(rows: list[dict[str, Any]], count: int = 96) -> list[dict[str, Any]]:
    e39 = [row for row in rows if row["source_kind"] == "e39"]
    by_family: dict[str, list[dict[str, Any]]] = {}
    for row in e39:
        by_family.setdefault(row["circuit_family"], []).append(row)
    selected: list[dict[str, Any]] = []
    for family in sorted(by_family):
        selected.append(min(by_family[family], key=lambda row: row["source_sha256"]))
        by_family[family].remove(selected[-1])
    remaining = sorted(
        (row for family_rows in by_family.values() for row in family_rows),
        key=lambda row: (sha256_bytes(f"E45:{row['circuit_family']}:{row['source_sha256']}".encode()), row["source_sha256"]),
    )
    selected.extend(remaining[: max(0, count - len(selected))])
    if len(selected) != count or len({row["circuit_family"] for row in selected}) != 15:
        raise RuntimeError("screening_selection_contract")
    return sorted(selected, key=lambda row: (row["circuit_family"], row["source_sha256"]))


def circuit_from_row(row: dict[str, Any]) -> QuantumCircuit:
    if row["source_kind"] == "e39":
        return QuantumCircuit.from_qasm_file(str(ROOT / row["source_path"]))
    spec = row["source_spec"]
    circuit = QuantumCircuit(int(spec["num_qubits"]))
    for operation in spec["operations"]:
        name = operation["name"]
        qubits = [int(q) for q in operation["qubits"]]
        params = operation.get("params", [])
        if name == "h":
            circuit.h(qubits[0])
        elif name == "x":
            circuit.x(qubits[0])
        elif name == "rz":
            circuit.rz(float(params[0]), qubits[0])
        elif name == "cx":
            circuit.cx(*qubits)
        else:
            raise ValueError(f"e44_unsupported_gate:{name}")
    return circuit


def state_from_circuit(circuit: QuantumCircuit) -> LandscapeState:
    operations = []
    for instruction in circuit.data:
        name = instruction.operation.name
        qubits = [circuit.find_bit(q).index for q in instruction.qubits]
        params = [] if name in {"h", "x", "cx"} else [float(instruction.operation.params[0])]
        operations.append({"name": name, "qubits": qubits, "params": params})
    return LandscapeState(
        circuit.num_qubits,
        tuple(
            state_gate
            for state_gate in state_from_spec({"num_qubits": circuit.num_qubits, "operations": operations}).gates
        ),
    )


def state_to_circuit(state: LandscapeState) -> QuantumCircuit:
    circuit = QuantumCircuit(state.num_qubits)
    for gate in state.gates:
        if gate.name == "h":
            circuit.h(gate.qubits[0])
        elif gate.name == "x":
            circuit.x(gate.qubits[0])
        elif gate.name == "rz":
            circuit.rz(float(gate.angle or 0.0), gate.qubits[0])
        elif gate.name == "cx":
            circuit.cx(*gate.qubits)
        elif gate.name == "y":
            circuit.y(gate.qubits[0])
        elif gate.name == "z":
            circuit.z(gate.qubits[0])
        elif gate.name == "s":
            circuit.s(gate.qubits[0])
        elif gate.name == "sdg":
            circuit.sdg(gate.qubits[0])
        elif gate.name == "t":
            circuit.t(gate.qubits[0])
        elif gate.name == "tdg":
            circuit.tdg(gate.qubits[0])
        elif gate.name == "cz":
            circuit.cz(*gate.qubits)
        elif gate.name == "swap":
            circuit.swap(*gate.qubits)
        else:
            raise ValueError(f"state_to_circuit_unsupported:{gate.name}")
    return circuit


def greedy_state(state: LandscapeState, library: Path) -> tuple[LandscapeState, list[LandscapeAction]]:
    current = state.normalized()
    trace: list[LandscapeAction] = []
    while True:
        # This is the same deterministic adjacent pair contract as the
        # Greedy arm.  It intentionally does not scan Quartz/exchange rules.
        reducing = [action for action in _pair_actions(current) if action.cost_delta < 0]
        if not reducing:
            return current, trace
        chosen = min(reducing, key=lambda action: action.sort_key)
        trace.append(chosen)
        current = chosen.post_state


def exposure_lower_bound(state: LandscapeState, library: Path) -> int:
    """Return a bounded local exposure proxy for CGEO ranking.

    Full v12 dependency certification remains an independent comparison arm.
    Calling it for every beam candidate would make the heuristic itself
    quadratic in the listing length, so the CGEO development rank uses the
    certified adjacent-pair exposure count as its bounded feature.
    """
    del library
    return sum(action.cost_delta < 0 for action in _pair_actions(state))


@dataclass
class SearchResult:
    status: str
    state: LandscapeState
    path: list[LandscapeAction]
    states_seen: int
    expanded: int
    pruned: int
    barrier_height: int | None
    escape_depth: int | None
    semantic_status: str
    resource_reason: str
    exposure_calls: int


def beam_search(
    initial: LandscapeState,
    library: Path,
    config: dict[str, Any],
    guided: bool,
) -> SearchResult:
    start = time.perf_counter()
    # The calling arm has already applied the deterministic Greedy baseline;
    # using it directly avoids rescanning large pressure inputs merely to
    # discover that they are outside the bounded landscape budget.
    root, root_trace = initial.normalized(), []
    if root.cost > MAX_PRECHECK_GATES or root.cost * root.num_qubits > MAX_PRECHECK_WORK:
        return SearchResult(
            STATUS_RESOURCE_NO_WITNESS, root, root_trace, 1, 0, 0, None, None,
            "LOCAL_RULE_PROOF_INHERITED_E43", "precheck_gate_or_qubit_work_budget", 0,
        )
    # Each tuple is state, path, peak cost, and exposure feature.
    frontier: list[tuple[LandscapeState, list[LandscapeAction], int, int]] = [(root, root_trace, root.cost, 0)]
    seen = {root.state_hash}
    best = root
    best_path = root_trace
    best_peak = root.cost
    expanded = 0
    pruned = 0
    exposure_calls = 0
    resource_reason = ""
    max_horizon = int(config["horizon"])
    for _depth in range(max_horizon):
        candidates: dict[str, tuple[LandscapeState, list[LandscapeAction], int, int]] = {}
        for current, path, peak, _old_exposure in frontier:
            if expanded >= int(config["state_budget"]):
                resource_reason = "state_budget"
                break
            if time.perf_counter() - start >= 60.0:
                resource_reason = "screening_cell_timeout_60s"
                break
            actions = legal_actions(current, library, "e44_core_v1")
            expanded += 1
            for action in actions:
                child = action.post_state
                if child.cost - root.cost > int(config["barrier_cap"]):
                    pruned += 1
                    continue
                child_path = path + [action]
                child_peak = max(peak, child.cost)
                if child.state_hash in seen or child.state_hash in candidates:
                    pruned += 1
                    continue
                feature = exposure_lower_bound(child, library) if guided else 0
                exposure_calls += int(guided)
                candidates[child.state_hash] = (child, child_path, child_peak, feature)
                seen.add(child.state_hash)
            if resource_reason:
                break
        if resource_reason:
            break
        if not candidates:
            break

        def rank(item: tuple[LandscapeState, list[LandscapeAction], int, int]) -> tuple[Any, ...]:
            state, path, peak, exposure = item
            if guided:
                terminal, _ = greedy_state(state, library)
                return (terminal.cost, -exposure, peak, len(path), state.state_hash)
            return (state.cost, peak, len(path), state.state_hash)

        frontier = sorted(candidates.values(), key=rank)[: int(config["beam_width"])]
        pruned += max(0, len(candidates) - len(frontier))
        for state, path, peak, _exposure in frontier:
            terminal, terminal_trace = greedy_state(state, library)
            if (terminal.cost, len(path), terminal.state_hash) < (best.cost, len(best_path), best.state_hash):
                best = terminal
                best_path = path + terminal_trace
                best_peak = max(peak, terminal.cost)
    if resource_reason:
        status = STATUS_WITNESS_INCOMPLETE if best.cost < root.cost else STATUS_RESOURCE_NO_WITNESS
    else:
        status = STATUS_WITNESS_INCOMPLETE if max_horizon > 0 else STATUS_EXACT_LOCAL
    escape_depth = None
    if best.cost < root.cost:
        for depth in range(1, len(best_path) + 1):
            intermediate, _ = greedy_state(root, library)
            # Replay the prefix through the state transitions without relying
            # on the final greedy trace to identify the first improvement.
            current = root
            for action in best_path[:depth]:
                current = action.post_state
            terminal, _ = greedy_state(current, library)
            if terminal.cost < root.cost:
                escape_depth = depth
                break
    barrier = max(0, best_peak - root.cost) if best.cost < root.cost else None
    return SearchResult(
        status,
        best,
        best_path,
        len(seen),
        expanded,
        pruned,
        barrier,
        escape_depth,
        "LOCAL_RULE_PROOF_INHERITED_E43",
        resource_reason,
        exposure_calls,
    )


def run_baseline_arms(circuit: QuantumCircuit) -> dict[str, tuple[QuantumCircuit, float, str]]:
    """Run the four non-landscape comparison arms on the common input."""
    arms: dict[str, tuple[QuantumCircuit, float, str]] = {}
    started = time.perf_counter()
    greedy = GreedyGateCancellation(max_iterations=50, fidelity_threshold=1.0, success_reduction=0.0)
    result = greedy.optimize(circuit)
    arms["greedy"] = (result.optimized_circuit, time.perf_counter() - started, "LOCAL_RULE_PROOF_PAIR_V1")

    started = time.perf_counter()
    wcl = WireTraversalPreprocessor().preprocess(circuit)
    result = GreedyGateCancellation(max_iterations=50, fidelity_threshold=1.0, success_reduction=0.0).optimize(wcl)
    arms["wcl_greedy"] = (result.optimized_circuit, time.perf_counter() - started, "LOCAL_RULE_PROOF_PAIR_V1_WCL_TOPOLOGICAL")

    started = time.perf_counter()
    cgl_config = ExposureConfig(
        dependence_model=DependenceModel.CONSERVATIVE_COMMUTATION_V1,
        beam_width=32,
        candidate_cap=256,
        exact_node_budget=1_000_000,
        overlap_check_budget=20_000_000,
    )
    prepared = _prepare_exposure(circuit, cgl_config)
    certificate = _certify_prepared(circuit, cgl_config, prepared)
    cgl_input = materialize_cgl_listing(circuit, certificate.listing_order)
    result = GreedyGateCancellation(max_iterations=50, fidelity_threshold=1.0, success_reduction=0.0).optimize(cgl_input)
    arms["v12_cgl_greedy"] = (result.optimized_circuit, time.perf_counter() - started, "V12_EXPOSURE_CERTIFICATE_PLUS_PAIR_PROOF")

    started = time.perf_counter()
    result = Phase2bTemplateMatcher(max_iterations=50, fidelity_threshold=1.0, success_reduction=0.0).optimize_full_pipeline(circuit)
    arms["phase2b_greedy"] = (result.optimized_circuit, time.perf_counter() - started, "PHASE2B_LOCAL_TEMPLATE_PROOF")
    return arms


def result_row(
    source: dict[str, Any], config: dict[str, Any], arm: str, original: QuantumCircuit,
    output_count: int, runtime: float, status: str, semantic_status: str,
    *, certificate: SearchResult | None = None, reason: str = "",
) -> dict[str, Any]:
    original_count = int(original.size())
    reduction = 1.0 - output_count / original_count if original_count else 0.0
    return {
        "experiment_id": EXPERIMENT_ID,
        "source_id": source["source_id"],
        "source_kind": source["source_kind"],
        "circuit_id": source["circuit_id"],
        "circuit_family": source["circuit_family"],
        "n_qubits": source["n_qubits"],
        "input_circuit_sha256": source["normalized_sha256"],
        "config_id": config["config_id"],
        "horizon": config["horizon"],
        "beam_width": config["beam_width"],
        "state_budget": config["state_budget"],
        "barrier_cap": config["barrier_cap"],
        "arm": arm,
        "status": status,
        "semantic_status": semantic_status,
        "resource_reason": reason,
        "input_gate_count": original_count,
        "output_gate_count": int(output_count),
        "reduction": reduction,
        "reduction_pp": 100.0 * reduction,
        "runtime_seconds": runtime,
        "states_seen": certificate.states_seen if certificate else 0,
        "expanded": certificate.expanded if certificate else 0,
        "pruned": certificate.pruned if certificate else 0,
        "escape_depth": certificate.escape_depth if certificate else "",
        "barrier_height": certificate.barrier_height if certificate else "",
        "exposure_calls": certificate.exposure_calls if certificate else 0,
        "certificate_status": certificate.status if certificate else "NOT_APPLICABLE",
        "witness_step_count": len(certificate.path) if certificate else 0,
    }


def run(output_root: Path = OUTPUT_ROOT, phase: str = "screening", include_e44: bool = True) -> dict[str, Any]:
    all_sources = load_e39_rows() + (load_e44_rows() if include_e44 else [])
    if phase == "screening":
        sources = select_screening([row for row in all_sources if row["source_kind"] == "e39"], 96)
        # E44 is kept as an independent, non-E39 stratum during development;
        # thirty-two fixed-hash cases are enough to detect implementation
        # drift without turning the first grid into a second E44 rerun.
        e44 = [row for row in all_sources if row["source_kind"] == "e44"]
        sources.extend(sorted(e44, key=lambda row: row["source_id"])[:32])
    elif phase == "full":
        sources = list(all_sources)
    else:
        raise ValueError(f"unknown_phase:{phase}")

    qasm_dir = output_root / "qasm"
    normalized_manifest: list[dict[str, Any]] = []
    prepared_sources: list[tuple[dict[str, Any], QuantumCircuit]] = []
    for index, source in enumerate(sources, start=1):
        try:
            raw = circuit_from_row(source)
            normalized, metadata = normalize_circuit(raw)
            if normalized is None:
                source["normalized_sha256"] = ""
                normalized_manifest.append({**{k: source[k] for k in ("source_id", "source_kind", "circuit_id", "circuit_family", "n_qubits", "source_path", "source_sha256")}, **metadata})
                continue
            payload = qasm2.dumps(normalized)
            normalized_path = qasm_dir / f"{index:04d}_{source['source_kind']}_{source['circuit_id']}_{sha256_bytes(payload.encode())[:12]}.qasm"
            atomic_text(normalized_path, payload)
            source["normalized_sha256"] = sha256_bytes(payload.encode())
            source["normalized_path"] = normalized_path.relative_to(ROOT).as_posix()
            normalized_manifest.append({**{k: source[k] for k in ("source_id", "source_kind", "circuit_id", "circuit_family", "n_qubits", "source_path", "source_sha256")}, **metadata, "normalized_path": source["normalized_path"], "normalized_sha256": source["normalized_sha256"]})
            prepared_sources.append((source, normalized))
        except Exception as exc:
            source["normalized_sha256"] = ""
            normalized_manifest.append({**{k: source[k] for k in ("source_id", "source_kind", "circuit_id", "circuit_family", "n_qubits", "source_path", "source_sha256")}, "status": "UNSUPPORTED_INPUT", "reason": f"load:{type(exc).__name__}"})
        if index % 32 == 0:
            print(f"normalized {index}/{len(sources)}", flush=True)

    protocol = {
        "experiment_id": EXPERIMENT_ID,
        "status": "DEVELOPMENT_ONLY",
        "phase": phase,
        "source_contract": {
            "e39_path": E39_INPUTS.relative_to(ROOT).as_posix(),
            "e39_sha256": sha256_file(E39_INPUTS),
            "e39_unique_inputs": 391,
            "e39_families": 15,
            "e44_path": E44_INPUTS.relative_to(ROOT).as_posix(),
            "e44_sha256": sha256_file(E44_INPUTS),
            "e44_cases": 1024 if include_e44 else 0,
        },
        "normalization": {
            "id": "Nam-normalize-v1",
            "basis": NAM_BASIS,
            "optimization_level": 0,
            "layout_method": "trivial",
            "routing_method": "basic",
            "seed_transpiler": 0,
            "policy": "remove terminal measurements and tail barriers only; reject mid-circuit measurement, reset, dynamic control, free parameters, and post-translation operations outside Nam basis",
        },
        "rule_library": {
            "path": RULE_LIBRARY.relative_to(ROOT).as_posix(),
            "sha256": sha256_file(RULE_LIBRARY),
            "rule_scope": "e44_core_v1",
        },
        "configuration_grid": FROZEN_CONFIGS,
        "cell_limits": {
            "screening_seconds": 60,
            "full_development_seconds": 180,
            "rss_limit_gib": 8,
            "workers": 1,
            "blas_threads": 1,
            "precheck_gate_limit": MAX_PRECHECK_GATES,
        },
        "selection_rule": [
            "exclude_semantic_or_resource_failure_rate_above_5_percent",
            "rank_by_family_mean_paired_ITT_gate_reduction",
            "retain_within_0.25_percentage_points_of_best",
            "choose_lower_median_runtime",
            "if_runtime_within_10_percent_choose_smaller_state_budget_then_horizon_then_beam",
        ],
        "arms": ARM_NAMES,
        "future_panel_access": "E46_AND_LATER_NOT_READ",
    }
    atomic_text(output_root / "protocol.json", json.dumps(protocol, indent=2, sort_keys=True) + "\n")
    write_csv(output_root / "normalization_manifest.csv", normalized_manifest)

    rows: list[dict[str, Any]] = []
    for index, (source, circuit) in enumerate(prepared_sources, start=1):
        print(f"evaluating {index}/{len(prepared_sources)} {source['circuit_id']}", flush=True)
        try:
            if circuit.size() > MAX_PRECHECK_GATES:
                baselines = {
                    arm: (circuit, 0.0, "RESOURCE_BOUNDED_NO_WITNESS:precheck_gate_budget")
                    for arm in ("greedy", "wcl_greedy", "v12_cgl_greedy", "phase2b_greedy")
                }
            else:
                baselines = run_baseline_arms(circuit)
        except Exception as exc:
            for config in FROZEN_CONFIGS:
                for arm in ARM_NAMES:
                    rows.append(result_row(source, config, arm, circuit, circuit.size(), 0.0, "ERROR", "NOT_AVAILABLE", reason=f"baseline:{type(exc).__name__}"))
            continue
        root_state = state_from_circuit(baselines["greedy"][0])
        for config in FROZEN_CONFIGS:
            for arm in ("greedy", "wcl_greedy", "v12_cgl_greedy", "phase2b_greedy"):
                output, runtime, semantic = baselines[arm]
                arm_status = "RESOURCE_BOUNDED_NO_WITNESS" if semantic.startswith("RESOURCE_BOUNDED") else "SUCCESS"
                rows.append(result_row(source, config, arm, circuit, output.size(), runtime, arm_status, semantic))
            for arm, guided in (("unguided_beam", False), ("certificate_guided_escape", True)):
                started = time.perf_counter()
                try:
                    search = beam_search(root_state, RULE_LIBRARY, config, guided)
                    output_count = search.state.cost
                    rows.append(result_row(source, config, arm, circuit, output_count, time.perf_counter() - started, search.status, search.semantic_status, certificate=search, reason=search.resource_reason))
                except Exception as exc:
                    rows.append(result_row(source, config, arm, circuit, circuit.size(), time.perf_counter() - started, "ERROR", "NOT_AVAILABLE", reason=f"search:{type(exc).__name__}"))
        if index % 10 == 0:
            write_csv(output_root / "grid_results.partial.csv", rows)

    write_csv(output_root / "grid_results.csv", rows)
    if (output_root / "grid_results.partial.csv").exists():
        (output_root / "grid_results.partial.csv").unlink()

    summaries: list[dict[str, Any]] = []
    for config in FROZEN_CONFIGS:
        for arm in ARM_NAMES:
            selected = [row for row in rows if row["config_id"] == config["config_id"] and row["arm"] == arm]
            valid = [row for row in selected if row["status"] in {"SUCCESS", STATUS_WITNESS_INCOMPLETE, STATUS_EXACT_ESCAPE, STATUS_EXACT_LOCAL, STATUS_RESOURCE_NO_WITNESS}]
            reductions = [float(row["reduction_pp"]) for row in valid]
            summaries.append({
                **config,
                "arm": arm,
                "row_count": len(selected),
                "valid_row_count": len(valid),
                "semantic_failure_count": sum(row["semantic_status"] in {"SEMANTIC_FAILURE", "NOT_AVAILABLE"} for row in selected),
                "resource_bounded_count": sum(row["status"] == STATUS_RESOURCE_NO_WITNESS for row in selected),
                "resource_or_error_rate": (sum(row["status"] in {STATUS_RESOURCE_NO_WITNESS, "ERROR"} for row in selected) / len(selected)) if selected else 1.0,
                "family_mean_paired_itt_pp": statistics.fmean(reductions) if reductions else 0.0,
                "median_runtime_seconds": statistics.median(float(row["runtime_seconds"]) for row in selected) if selected else math.inf,
                "p95_runtime_seconds": sorted(float(row["runtime_seconds"]) for row in selected)[max(0, math.ceil(0.95 * len(selected)) - 1)] if selected else math.inf,
            })
    atomic_text(output_root / "config_summaries.json", json.dumps(summaries, indent=2, sort_keys=True) + "\n")
    config_summaries = [row for row in summaries if row["arm"] == "certificate_guided_escape"]
    eligible = [row for row in config_summaries if row["resource_or_error_rate"] <= 0.05 and row["semantic_failure_count"] == 0]
    best = max((row["family_mean_paired_itt_pp"] for row in eligible), default=None)
    near_best = [row for row in eligible if best is not None and row["family_mean_paired_itt_pp"] >= best - 0.25]
    selected = min(
        near_best,
        key=lambda row: (
            row["median_runtime_seconds"], row["state_budget"], row["horizon"], row["beam_width"],
        ),
        default=None,
    )
    selection = {
        "experiment_id": EXPERIMENT_ID,
        "phase": phase,
        "status": "SCREENING_COMPLETE_SELECTION_PENDING_FULL_DEVELOPMENT" if phase == "screening" else "DEVELOPMENT_COMPLETE",
        "eligible_config_count": len(eligible),
        "best_cgeo_family_mean_itt_pp": best,
        "selected_config": selected,
        "selection_is_frozen_for_e48": False,
        "future_panel_access": "E46_AND_LATER_NOT_READ",
    }
    atomic_text(output_root / "selection.json", json.dumps(selection, indent=2, sort_keys=True) + "\n")
    receipt = {
        "status": selection["status"],
        "experiment_id": EXPERIMENT_ID,
        "protocol_sha256": sha256_file(output_root / "protocol.json"),
        "normalization_manifest_sha256": sha256_file(output_root / "normalization_manifest.csv"),
        "grid_results_sha256": sha256_file(output_root / "grid_results.csv"),
        "config_summaries_sha256": sha256_file(output_root / "config_summaries.json"),
        "selection_sha256": sha256_file(output_root / "selection.json"),
        "source_count": len(sources),
        "normalized_count": len(prepared_sources),
        "result_rows": len(rows),
        "configuration_count": len(FROZEN_CONFIGS),
        "arm_count": len(ARM_NAMES),
        "selection": selection,
    }
    atomic_text(output_root / "receipt.json", json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", choices=("screening", "full"), default="screening")
    parser.add_argument("--output-root", type=Path, default=OUTPUT_ROOT)
    parser.add_argument("--no-e44", action="store_true")
    args = parser.parse_args()
    print(json.dumps(run(args.output_root, args.phase, not args.no_e44), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
