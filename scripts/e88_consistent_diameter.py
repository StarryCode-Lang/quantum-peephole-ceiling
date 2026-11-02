"""E88: the panel diameter under a consistently closed generator set, and a
three-qubit lower bound.

Motivation
----------
Round 21 (`PD-1`) argued, correctly, that ``rz(theta)`` is one native panel gate
for every angle, so ``z = rz(pi)`` and ``s = rz(pi/2)`` each cost 1, and
therefore the generator set of the 2-qubit Clifford fragment is
``{h,x,z,s}`` per qubit plus both CX directions.  That gives group order 11,520
and Cayley diameter 9.

The same argument gives ``sdg = rz(-pi/2)`` at cost 1, and round 21's own source
comment names it (``scripts/e84_panel_gate_diameter.py``, "rz is native and
continuous => z = rz(pi), s = rz(pi/2), sdg = rz(-pi/2)") while leaving it out of
the generator list.  A metric that prices ``s`` at 1 but ``sdg`` at 2 is not the
panel's metric.  Part A measures what closing the set consistently does to the
diameter -- it can only shrink it, and the question is by how much.

Part B asks the question the project has never answered for three qubits:
``|C_3| = 92,897,280`` rules out a plain Python BFS, so ``D_3`` has never been
measured.  It does not have to be: two disjoint balls certify a lower bound.
If ``B_r(id)`` and ``B_r(g)`` are disjoint then ``d(g) > 2r``, hence
``D_3 >= 2r + 1``.  A ball of radius 5 in 21 generators is a few million
elements, which is a numpy array, not a cluster job.

Contract
--------
Read-only.  No frozen input is written; nothing under ``data/``, ``release/`` or
``docs/manuscript/`` is touched.  The cost model is word length in the declared
generator set -- the Cayley graph *is* the cost model, exactly as in E82/E84.

The tableau is E84's Z4-phase representation (``i^p X^x Z^z`` per row), imported
rather than re-derived, because the phase convention is the part that silently
produces a right group with a wrong metric.  Part A cross-checks every 2-qubit
diameter against a full BFS with E84's own scalar ``compose_z4``, and Part B
cross-checks the vectorised ball against the scalar composition on random words.

Outputs (``docs/review/science_boost/2026-11-02_three_qubit_diameter/``)
    diameter_variants.csv   Part A: one row per generator-set variant
    ball_growth.csv         Part B: |B_r| for r = 1..R on three qubits
    summary.json            contract, results, self-checks, provenance
    MANIFEST.json           sha256 of every artifact
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import random
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
for _p in (ROOT, ROOT / "scripts"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import numpy as np  # noqa: E402

EXPERIMENT_ID = "E88_CONSISTENT_DIAMETER_AND_THREE_QUBIT_FLOOR_2026_11_02"
OUTPUT_ROOT = ROOT / "docs" / "review" / "science_boost" / "2026-11-02_three_qubit_diameter"
E84_SUMMARY = ROOT / "docs" / "review" / "science_boost" / "2026-10-31_panel_diameter" / "summary.json"


def _load(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:  # pragma: no cover - defensive
        raise RuntimeError(f"cannot_load:{path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


E84 = _load("e84_panel_gate_diameter", ROOT / "scripts" / "e84_panel_gate_diameter.py")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fieldnames})


# --------------------------------------------------------------------- Part A
def part_a() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """2-qubit (and 1-qubit) diameters for four generator-set variants."""

    variants = [
        (
            "w2_no_s_round20",
            2,
            ["h0", "x0", "z0", "h1", "x1", "z1", "cx01", "cx10"],
            "round 20's set: no phase gate at all (order 1,152)",
        ),
        (
            "panel_2q_round21",
            2,
            ["h0", "h1", "x0", "x1", "z0", "z1", "s0", "s1", "cx01", "cx10"],
            "round 21's PD-1 set: + s, but sdg still costs 2",
        ),
        (
            "panel_2q_sdg",
            2,
            ["h0", "h1", "x0", "x1", "z0", "z1", "s0", "s1", "sdg0", "sdg1", "cx01", "cx10"],
            "consistently closed: sdg = rz(-pi/2) is one native gate too",
        ),
        (
            "panel_1q_round21",
            1,
            ["h0", "x0", "z0", "s0"],
            "the 24-element 1-qubit group with s, no sdg",
        ),
        (
            "panel_1q_sdg",
            1,
            ["h0", "x0", "z0", "s0", "sdg0"],
            "the same group with sdg closed in",
        ),
    ]
    rows: list[dict[str, Any]] = []
    detail: dict[str, Any] = {}
    for name, n, gens, note in variants:
        started = time.perf_counter()
        built = E84.generators_z4(n, gens)
        dist, histogram = E84.build_group_z4(n, built)
        diameter = max(dist.values())
        rows.append(
            {
                "variant": name,
                "num_qubits": n,
                "generator_count": len(gens),
                "group_order": len(dist),
                "diameter": diameter,
                "threshold": diameter + 1,
                "distance_histogram": json.dumps({str(k): v for k, v in histogram.items()}),
                "note": note,
                "runtime_seconds": round(time.perf_counter() - started, 1),
            }
        )
        detail[name] = {
            "num_qubits": n,
            "generators": gens,
            "generator_count": len(gens),
            "group_order": len(dist),
            "diameter": diameter,
            "threshold": diameter + 1,
            "distance_histogram": {str(k): v for k, v in histogram.items()},
        }
        print(f"  [A] {name}: order={len(dist)} D={diameter}", flush=True)
    return rows, detail


# --------------------------------------------------------------------- Part B
class BallOracle:
    """Vectorised BFS balls on the Z4-phase Clifford tableau.

    An element is the tuple of images of the 2n Pauli generators.  Each image is
    a Pauli on n qubits: a 2n-bit ``(x, z)`` mask plus a Z4 phase.  For n = 3
    that is 6 images x (6 mask bits + 2 phase bits) = 48 bits, one int64.

    Left multiplication by a generator is *row-local*: the image of row i under
    ``g . U`` depends only on row i of U.  So each generator gets a 64-entry
    lookup table (mask -> new mask, phase increment), built with E84's scalar
    ``compose_z4`` rather than by hand, and applying it is one fancy-index per
    row.  That is what makes a radius-5 ball on three qubits cheap.
    """

    def __init__(self, n: int, names: list[str]):
        self.n = n
        self.names = names
        self.width = 2 * n
        self.gens = E84.generators_z4(n, names)
        self.table: list[tuple[np.ndarray, np.ndarray]] = []
        for _name, (rows, phases) in self.gens:
            masks = np.arange(1 << self.width, dtype=np.int64)
            new_mask = np.zeros_like(masks)
            new_phase = np.zeros_like(masks)
            for value in range(1 << self.width):
                probe = (tuple(int(value) for _ in range(self.width)), tuple(phases))
                # compose(g, probe) with probe's phases zeroed: the increment is
                # exactly what g contributes on that row.
                probe = (probe[0], tuple(0 for _ in range(self.width)))
                out_rows, out_phases = E84.compose_z4((rows, phases), probe, self.n)
                new_mask[value] = out_rows[0]
                new_phase[value] = out_phases[0]
            self.table.append((new_mask, new_phase))

    # -- encoding ---------------------------------------------------------
    def identity(self) -> np.ndarray:
        rows = np.array([[1 << i for i in range(self.width)]], dtype=np.int64)
        phases = np.zeros((1, self.width), dtype=np.int64)
        return self.pack(rows, phases)

    def pack(self, rows: np.ndarray, phases: np.ndarray) -> np.ndarray:
        key = np.zeros(rows.shape[0], dtype=np.int64)
        for i in range(self.width):
            key |= rows[:, i] << (self.width * i)
            key |= phases[:, i] << (self.width * self.width + 2 * i)
        return key

    def unpack(self, key: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        rows = np.empty((key.shape[0], self.width), dtype=np.int64)
        phases = np.empty((key.shape[0], self.width), dtype=np.int64)
        for i in range(self.width):
            rows[:, i] = (key >> (self.width * i)) & ((1 << self.width) - 1)
            phases[:, i] = (key >> (self.width * self.width + 2 * i)) & 3
        return rows, phases

    # -- group action -----------------------------------------------------
    def apply(self, generator_index: int, keys: np.ndarray) -> np.ndarray:
        rows, phases = self.unpack(keys)
        new_mask, new_phase = self.table[generator_index]
        out_rows = new_mask[rows]
        out_phases = (phases + new_phase[rows]) % 4
        return self.pack(out_rows, out_phases)

    def apply_word(self, word: list[int], keys: np.ndarray) -> np.ndarray:
        out = keys
        for index in word:
            out = self.apply(index, out)
        return out

    # -- balls ------------------------------------------------------------
    def ball(self, radius: int, chunk: int = 6) -> tuple[np.ndarray, list[int]]:
        visited = self.identity()
        frontier = visited
        growth = [1]
        for _ in range(radius):
            parts: list[np.ndarray] = []
            for index in range(len(self.gens)):
                parts.append(self.apply(index, frontier))
                if len(parts) >= chunk:
                    parts = [np.unique(np.concatenate(parts))]
            candidate = np.unique(np.concatenate(parts))
            frontier = np.setdiff1d(candidate, visited, assume_unique=True)
            if frontier.size == 0:
                break
            visited = np.union1d(visited, frontier)
            growth.append(int(visited.size))
            print(f"    radius {len(growth) - 1}: |B| = {visited.size}", flush=True)
        return visited, growth

    def scalar_distance_check(self, word: list[int], keys: np.ndarray, rng: random.Random) -> bool:
        """Vectorised action must equal E84's scalar composition on the same word."""

        element = keys[:1]
        scalar = (tuple(1 << i for i in range(self.width)), tuple(0 for _ in range(self.width)))
        for index in word:
            element = self.apply(index, element)
            scalar = E84.compose_z4(self.gens[index][1], scalar, self.n)
        expected = self.pack(
            np.array([scalar[0]], dtype=np.int64), np.array([scalar[1]], dtype=np.int64)
        )
        return bool(element[0] == expected[0])


def part_b(n: int, radius: int, trials: int, seed: int, word_length: int) -> dict[str, Any]:
    names = [f"h{q}" for q in range(n)] + [f"x{q}" for q in range(n)] + [f"z{q}" for q in range(n)]
    names += [f"s{q}" for q in range(n)] + [f"sdg{q}" for q in range(n)]
    names += [f"cx{c}{t}" for c in range(n) for t in range(n) if c != t]
    oracle = BallOracle(n, names)
    print(f"  [B] n={n} generators={len(names)}", flush=True)
    started = time.perf_counter()
    ball_id, growth = oracle.ball(radius)
    # One radius further, so a witness can be *pinned* to an exact distance:
    # B_r(id) and B_r(g) disjoint gives d(g) > 2r; B_{r+1}(id) meeting B_r(g)
    # gives d(g) <= 2r+1.  Both together give d(g) = 2r+1 exactly.
    ball_id_next, growth_next = oracle.ball(radius + 1)
    elapsed = round(time.perf_counter() - started, 1)

    rng = random.Random(seed)
    identity = oracle.identity()
    scalar_ok = all(
        oracle.scalar_distance_check([rng.randrange(len(names)) for _ in range(6)], identity, rng)
        for _ in range(20)
    )

    # Negative control: a short word must produce an intersecting pair of balls.
    control_word = [rng.randrange(len(names)) for _ in range(2)]
    control_ball = oracle.apply_word(control_word, ball_id)
    control_intersects = int(np.intersect1d(ball_id, control_ball, assume_unique=True).size)

    # Positive search: a long random word should be far from the identity.
    witness: dict[str, Any] | None = None
    attempts = 0
    sampled_ceiling: int | None = None
    for _ in range(trials):
        attempts += 1
        word = [rng.randrange(len(names)) for _ in range(word_length)]
        element = oracle.apply_word(word, identity)
        other = oracle.apply_word(word, ball_id)
        overlap = int(np.intersect1d(ball_id, other, assume_unique=True).size)
        if overlap == 0:
            near = oracle.apply_word(word, ball_id_next)
            pinned = int(np.intersect1d(ball_id_next, other, assume_unique=True).size) > 0
            witness = {
                "word": [names[i] for i in word],
                "word_length": word_length,
                "element_key": int(element[0]),
                "in_own_ball": bool(np.isin(element, ball_id).any()),
                "intersection_size": overlap,
                "certified_lower_bound": 2 * radius + 1,
                "pinned_exact_distance": 2 * radius + 1 if pinned else None,
                "pin_evidence": {
                    "ball_r_plus_1_size": int(ball_id_next.size),
                    "intersection_with_ball_r_of_g": int(
                        np.intersect1d(ball_id_next, other, assume_unique=True).size
                    ),
                    "ball_r_plus_1_of_g_size": int(near.size),
                },
            }
            break
        # Every sampled element whose two radius-(r+1) balls meet has d <= 2r+2.
        if sampled_ceiling is None:
            wide = oracle.apply_word(word, ball_id_next)
            if int(np.intersect1d(ball_id_next, wide, assume_unique=True).size) > 0:
                sampled_ceiling = 2 * radius + 2
    return {
        "num_qubits": n,
        "generators": names,
        "generator_count": len(names),
        "radius": radius,
        "ball_sizes": growth,
        "ball_sizes_next": growth_next,
        "ball_size_at_radius": int(ball_id.size),
        "ball_runtime_seconds": elapsed,
        "scalar_cross_check_ok": scalar_ok,
        "negative_control_word": [names[i] for i in control_word],
        "negative_control_intersection": control_intersects,
        "negative_control_detects_nearby": control_intersects > 0,
        "trials": attempts,
        "witness": witness,
        "diameter_lower_bound": 2 * radius + 1 if witness else None,
        "exact_distance_witness": (witness or {}).get("pinned_exact_distance"),
        "sampled_no_element_above": sampled_ceiling,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--radius", type=int, default=5)
    parser.add_argument("--trials", type=int, default=40)
    parser.add_argument("--word-length", type=int, default=20)
    parser.add_argument("--seed", type=int, default=20261102)
    parser.add_argument("--output-root", type=Path, default=OUTPUT_ROOT)
    parser.add_argument("--skip-part-a", action="store_true")
    args = parser.parse_args()
    out = args.output_root
    out.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()

    rows_a: list[dict[str, Any]] = []
    detail_a: dict[str, Any] = {}
    if not args.skip_part_a:
        print("Part A: 2-qubit and 1-qubit diameters", flush=True)
        rows_a, detail_a = part_a()

    print("Part B: three-qubit ball and disjointness certificate", flush=True)
    detail_b = part_b(3, args.radius, args.trials, args.seed, args.word_length)

    # ---- self-checks ---------------------------------------------------------
    e84 = {}
    if E84_SUMMARY.exists():
        e84 = json.loads(E84_SUMMARY.read_text(encoding="utf-8"))
    e84_rows = {row: value for row, value in (e84.get("fragments", {}) or {}).items()} if e84 else {}
    checks = {
        "round20_subgroup_reproduced": detail_a.get("w2_no_s_round20", {}).get("diameter") == 7,
        "round21_panel_reproduced": detail_a.get("panel_2q_round21", {}).get("diameter") == 9,
        "round21_one_qubit_reproduced": detail_a.get("panel_1q_round21", {}).get("diameter") == 4,
        "e84_summary_agrees_on_panel": (
            e84_rows.get("panel_2q", {}).get("diameter") == detail_a.get("panel_2q_round21", {}).get("diameter")
            if e84_rows
            else None
        ),
        "sdg_cannot_grow_the_group": (
            detail_a.get("panel_2q_sdg", {}).get("group_order") == detail_a.get("panel_2q_round21", {}).get("group_order")
            if detail_a
            else None
        ),
        "sdg_cannot_increase_the_diameter": (
            detail_a.get("panel_2q_sdg", {}).get("diameter", 99)
            <= detail_a.get("panel_2q_round21", {}).get("diameter", -1)
            if detail_a
            else None
        ),
        "scalar_and_vectorised_agree": detail_b["scalar_cross_check_ok"],
        "negative_control_detects_nearby": detail_b["negative_control_detects_nearby"],
        "ball_is_monotone": all(
            detail_b["ball_sizes"][i] < detail_b["ball_sizes"][i + 1]
            for i in range(len(detail_b["ball_sizes"]) - 1)
        ),
        "witness_found": detail_b["witness"] is not None,
        "witness_distance_pinned_exactly": detail_b.get("exact_distance_witness") is not None,
        "three_qubit_bound_exceeds_two_qubit": (
            (detail_b["diameter_lower_bound"] or 0) > detail_a.get("panel_2q_sdg", {}).get("diameter", 99)
            if detail_a
            else None
        ),
    }

    summary = {
        "experiment_id": EXPERIMENT_ID,
        "as_of": "2026-11-02",
        "purpose": (
            "(A) close the generator set consistently -- if rz is native then sdg = rz(-pi/2) is "
            "native too -- and measure what that does to the panel diameter; "
            "(B) certify a lower bound on the 3-qubit diameter, which |C_3| = 92,897,280 puts out "
            "of reach of a plain BFS"
        ),
        "contract": {
            "cost_model": "word length in the declared generator set (the Cayley graph is the cost model)",
            "tableau": "E84 Z4-phase representation, imported not re-derived",
            "read_only": ["data/", "release/", "docs/manuscript/"],
            "lower_bound_argument": "B_r(id) and B_r(g) disjoint => d(g) > 2r => D >= 2r + 1",
        },
        "part_a_diameters": detail_a,
        "part_b_three_qubit": detail_b,
        "self_checks": checks,
        "runtime_seconds": round(time.perf_counter() - started, 1),
    }

    if rows_a:
        _write_csv(
            out / "diameter_variants.csv",
            rows_a,
            [
                "variant",
                "num_qubits",
                "generator_count",
                "group_order",
                "diameter",
                "threshold",
                "distance_histogram",
                "note",
                "runtime_seconds",
            ],
        )
    _write_csv(
        out / "ball_growth.csv",
        [
            {"radius": r, "ball_size": size}
            for r, size in enumerate(detail_b["ball_sizes"])
        ],
        ["radius", "ball_size"],
    )
    (out / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    (out / "MANIFEST.json").write_text(
        json.dumps(
            {
                "experiment_id": EXPERIMENT_ID,
                "generated": "2026-11-02",
                "script": "scripts/e88_consistent_diameter.py",
                "artifacts": {
                    name: sha256_file(out / name)
                    for name in ("diameter_variants.csv", "ball_growth.csv", "summary.json")
                    if (out / name).exists()
                },
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    print(json.dumps({"self_checks": checks, "three_qubit": detail_b}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
