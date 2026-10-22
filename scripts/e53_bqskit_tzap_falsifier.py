"""E53: BQSKit and tzap as the fifth and sixth external optimizers.

Why this experiment
-------------------
E48 (2026-10-20) tested four external optimizers (Qiskit L3, tket
FullPeepholeOptimise, tket RemoveRedundancies, PyZX full_reduce).  Three review
rounds have listed BQSKit and tzap as the two mainstream tools that were never
run, and BQSKit is the one that could break the GHZ bound: it is the only
tested tool that performs *numerical resynthesis* rather than rewrite matching.

E52 (2026-10-22) also showed that only 14 of the 63 certified panel escapes sit
on a genuine greedy fixed point; the other 49 are depth-1 escapes on baselines
that were never optimised.  Those 14 are the cells that carry scientific weight,
so they are the panel part of this experiment.

Panels
------
A. ``ghz_n`` for n = 4..20: does any external tool beat ``n`` gates?
B. the 14 genuine escapes: does an external tool beat the certified
   ``best_cost``, i.e. is the certified optimum also a *global* optimum in a
   neutral basis?
C. the 8 SurfaceCode and 2 QFT sources: the two families that carry the
   remaining "ceiling" claim.

Cost model
----------
Identical to E48: the neutral basis translation (``optimization_level=0``) with
``cost_fair`` (single general 1q gate admitted) as the primary metric, plus
``two_qubit``, which is representation independent.  Equivalence is exact
unitary equality where the dense operator is affordable, otherwise reported as
``None`` and not used as evidence.

Outputs (``docs/review/science_boost/2026-10-22_bqskit_tzap/``):
    * ``bqskit_tzap_rows.csv``
    * ``summary.json``

Read-only with respect to ``data/`` and ``release/``.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import time
import warnings
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
for extra in (ROOT, ROOT / "scripts"):
    if str(extra) not in sys.path:
        sys.path.insert(0, str(extra))

warnings.filterwarnings("ignore")

from e48_external_falsifier import (  # noqa: E402
    CLASSIFICATION,
    MANIFEST,
    build_ghz,
    equivalent,
    metrics,
)

EXPERIMENT_ID = "E53_BQSKIT_TZAP_FALSIFIER_2026_10_22"
OUTPUT_ROOT = ROOT / "docs" / "review" / "science_boost" / "2026-10-22_bqskit_tzap"
E52_MECHANISM = ROOT / "docs" / "review" / "science_boost" / "2026-10-22_escape_mechanism" / "escape_mechanism.csv"
GHZ_SIZES = tuple(range(4, 21))
BQSKIT_SECONDS_HINT = "bqskit.compile with MachineModel(gate_set=[U3Gate, CNOTGate]), all-to-all"


def _load_panel_meta() -> dict[str, dict[str, str]]:
    with CLASSIFICATION.open(encoding="utf-8", newline="") as handle:
        return {row["source_id"]: row for row in csv.DictReader(handle)}


def _load_paths() -> dict[str, str]:
    with MANIFEST.open(encoding="utf-8", newline="") as handle:
        return {row["source_id"]: row["normalized_path"] for row in csv.DictReader(handle)}


def _genuine_escape_ids() -> list[str]:
    if not E52_MECHANISM.exists():
        return []
    with E52_MECHANISM.open(encoding="utf-8", newline="") as handle:
        return [
            row["source_id"]
            for row in csv.DictReader(handle)
            if row["root_kind"] == "GREEDY_FIXED_POINT" and row["status"] == "EXACT_ESCAPE"
        ]


# --------------------------------------------------------------------------- #
# external optimizers
# --------------------------------------------------------------------------- #
def run_bqskit(circuit: Any) -> Any:
    from bqskit import compile as bqskit_compile  # noqa: PLC0415
    from bqskit.compiler import MachineModel  # noqa: PLC0415
    from bqskit.ext import bqskit_to_qiskit, qiskit_to_bqskit  # noqa: PLC0415
    from bqskit.ir.gates import CNOTGate, U3Gate  # noqa: PLC0415

    inner = qiskit_to_bqskit(circuit)
    model = MachineModel(inner.num_qudits, gate_set=[U3Gate(), CNOTGate()])
    compiled = bqskit_compile(inner, model=model)
    return bqskit_to_qiskit(compiled)


def run_tzap(circuit: Any) -> Any:
    """tzap minimises CNOT count of the linear-reversible part only."""

    from tzap.framework import gauss  # noqa: PLC0415

    raise RuntimeError(f"tzap API unavailable in this environment: {gauss.__name__}")


OPTIMIZERS = {
    "bqskit_qsearch": run_bqskit,
}


def _row(
    panel: str,
    circuit_id: str,
    family: str,
    n_qubits: int,
    optimizer: str,
    baseline: dict[str, int],
    circuit: Any,
    reference_cost: int | None,
    theorem_bound: int | None = None,
) -> dict[str, Any]:
    record: dict[str, Any] = {
        "panel": panel,
        "circuit_id": circuit_id,
        "circuit_family": family,
        "n_qubits": n_qubits,
        "optimizer": optimizer,
        "reference_cost": reference_cost,
        "theorem_bound": theorem_bound,
        "baseline_cost_fair": baseline["cost_fair"],
        "baseline_two_qubit": baseline["two_qubit"],
        "status": "OK",
        "cost_fair": None,
        "cost_declared": None,
        "two_qubit": None,
        "delta_vs_baseline": None,
        "delta_vs_reference": None,
        "beats_baseline": None,
        "beats_reference": None,
        "beats_theorem": None,
        "equivalent": None,
        "seconds": None,
    }
    start = time.time()
    try:
        out = OPTIMIZERS[optimizer](circuit)
        measured = metrics(out)
        record.update(measured)
        record["delta_vs_baseline"] = baseline["cost_fair"] - measured["cost_fair"]
        record["beats_baseline"] = bool(measured["cost_fair"] < baseline["cost_fair"])
        if reference_cost is not None:
            record["delta_vs_reference"] = int(reference_cost) - measured["cost_fair"]
            record["beats_reference"] = bool(measured["cost_fair"] < int(reference_cost))
        if theorem_bound is not None:
            record["beats_theorem"] = bool(measured["cost_fair"] < theorem_bound)
        record["equivalent"] = equivalent(circuit, out)
    except Exception as exc:  # noqa: BLE001
        record["status"] = f"ERROR:{type(exc).__name__}:{exc}"[:200]
    record["seconds"] = round(time.time() - start, 2)
    return record


def part_a_ghz() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for n in GHZ_SIZES:
        base = build_ghz(n)
        baseline = metrics(base)
        for name in OPTIMIZERS:
            record = _row(
                "A_ghz_scaling",
                f"ghz_{n}_synthetic",
                "GHZ",
                n,
                name,
                baseline,
                base,
                reference_cost=n,
                theorem_bound=n,
            )
            rows.append(record)
            print(f"  A n={n:2d} {name:14s} {record['status'][:24]:24s} fair={record['cost_fair']}", flush=True)
    return rows


def part_bc_panel() -> list[dict[str, Any]]:
    meta = _load_panel_meta()
    paths = _load_paths()
    genuine = set(_genuine_escape_ids())
    from qiskit import qasm2  # noqa: PLC0415

    targets: list[tuple[str, str]] = []
    targets.extend(("B_genuine_escapes", source_id) for source_id in sorted(genuine))
    for source_id, row in sorted(meta.items()):
        if row["circuit_family"] in {"SurfaceCode", "QFT"} and source_id not in genuine:
            targets.append(("C_ceiling_families", source_id))

    rows: list[dict[str, Any]] = []
    for panel, source_id in targets:
        row = meta[source_id]
        circuit = qasm2.loads((ROOT / paths[source_id]).read_text(encoding="utf-8"))
        baseline = metrics(circuit)
        for name in OPTIMIZERS:
            record = _row(
                panel,
                row["circuit_id"],
                row["circuit_family"],
                int(row["n_qubits"]),
                name,
                baseline,
                circuit,
                reference_cost=int(row["best_cost"]) if row["best_cost"] else None,
            )
            record["source_id"] = source_id
            record["certified_status"] = row["classification_status"]
            record["certified_best_cost"] = row["best_cost"]
            record["baseline_cost_frozen"] = row["baseline_cost"]
            rows.append(record)
            print(
                f"  {panel[:1]} {row['circuit_family'][:16]:16s} {name:14s} "
                f"{record['status'][:20]:20s} fair={record['cost_fair']} ref={record['reference_cost']}",
                flush=True,
            )
    return rows


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-ghz", action="store_true")
    args = parser.parse_args()
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, Any]] = []
    if not args.skip_ghz:
        rows.extend(part_a_ghz())
    rows.extend(part_bc_panel())
    write_csv(OUTPUT_ROOT / "bqskit_tzap_rows.csv", rows)

    ok = [row for row in rows if row["status"] == "OK"]
    summary = {
        "experiment_id": EXPERIMENT_ID,
        "date": "2026-10-22",
        "optimizers": {
            name: (
                BQSKIT_SECONDS_HINT if name == "bqskit_qsearch" else "not available in this environment"
            )
            for name in OPTIMIZERS
        },
        "unavailable": {
            "tzap": (
                "no wheel for this interpreter; not installed. Reported as a gap, not as a negative result."
            ),
            "mqt_qcec": "installed but the Windows wheel has no DLL directory (mqt/core/bin); unusable.",
        },
        "row_count": len(rows),
        "ok_count": len(ok),
        "by_panel": {
            panel: {
                "rows": sum(1 for row in rows if row["panel"] == panel),
                "ok": sum(1 for row in ok if row["panel"] == panel),
                "beats_baseline": sum(1 for row in ok if row["panel"] == panel and row["beats_baseline"]),
                "beats_reference": sum(1 for row in ok if row["panel"] == panel and row["beats_reference"]),
                "beats_theorem": sum(1 for row in ok if row["panel"] == panel and row["beats_theorem"]),
                "equivalence_failures": sum(
                    1 for row in ok if row["panel"] == panel and row["equivalent"] is False
                ),
                "equivalence_unchecked": sum(
                    1 for row in ok if row["panel"] == panel and row["equivalent"] is None
                ),
            }
            for panel in sorted({row["panel"] for row in rows})
        },
        "ghz_by_size": {
            str(row["n_qubits"]): row["cost_fair"]
            for row in ok
            if row["panel"] == "A_ghz_scaling"
        },
        "reading": (
            "A tool that beats the theorem bound falsifies the GHZ claim; a tool that beats the "
            "certified reference cost demotes that cell's certificate from optimum to local optimum."
        ),
    }
    (OUTPUT_ROOT / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(f"[E53] wrote {OUTPUT_ROOT} ({len(rows)} rows)", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
