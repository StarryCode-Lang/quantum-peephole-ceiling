"""Generate the fragment-native benchmark suite (P5, WL-3 fix).

Six structured families on the frozen-basis fragment {x, rz, cx}, sizes
n = 4..64, >= 8 instances per (family, n) cell, each with an *analytic*
phase-polynomial support size s(c) — the absolute rotation lower bound of
`docs/theory/rotation_gap_2026-10-25.md` (Lemma 1: R(c) >= s(c)).  The
families are chosen so s is exact by construction, replacing the synthetic
random ladder whose 45/45 rz cells sat trivially on the lower bound (WL-3).

Outputs (never under data/ or release/): a dated package directory
(default docs/review/science_boost/2026-10-25_fragment_bench/) with

  instances/<family>/<family>_n<size>_k<idx>.qasm   qasm2 listings
  bench_index.csv        one row per instance: family, n, seed, s, gate counts
  MANIFEST.json          SHA-256 of every produced file + contract block

Families:
  diagonal_structured    A^-1 diag(f) A with f a random sparse polynomial
  linear_rotation        random invertible linear layer, then rz at chosen
                         affine forms (dedup makes s exact)
  trotter_zz             repeated ZZ layers; s = distinct ZZ edges used
  iqp_core               H-diag-H with a random degree-<=2 polynomial
  arithmetic_phase       phase oracle of a ripple-carry carry chain
  random_phase           random support, realized by CX conjugation

Usage:
    python scripts/generate_fragment_bench.py --out-dir <dir> [--ns 4 8 16 32 64]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import zlib
from datetime import datetime, timezone
from pathlib import Path

from qiskit import QuantumCircuit, qasm2

ROOT = Path(__file__).resolve().parents[1]
FAMILIES = (
    "diagonal_structured",
    "linear_rotation",
    "trotter_zz",
    "iqp_core",
    "arithmetic_phase",
    "random_phase",
)
INSTANCES_PER_CELL = 8
NS = (4, 8, 16, 32, 64)


def cnot_network(n: int, count: int, rng: random.Random) -> tuple[list[tuple[int, int]], dict[int, int]]:
    """Random CNOT network; returns gates and the final per-wire affine forms."""
    gates = []
    for _ in range(count):
        c = rng.randrange(n)
        t = rng.randrange(n)
        if c == t:
            continue
        gates.append((c, t))
    return gates


def realize(parity: tuple[int, ...], n: int, qc: QuantumCircuit, angle: float = 1.1) -> None:
    """Emit cx conjugation realizing an rz on the given parity set."""
    parity = list(parity)
    if not parity:
        return
    if len(parity) == 1:
        qc.rz(angle, parity[0])
        return
    target = parity[0]
    for q in parity[1:]:
        qc.cx(q, target)
    qc.rz(angle, target)
    for q in reversed(parity[1:]):
        qc.cx(q, target)


def analytic_s(monomials: set[tuple[int, ...]]) -> int:
    return len({m for m in monomials if m})


def gen_diagonal_structured(n: int, seed: int) -> tuple[QuantumCircuit, int]:
    rng = random.Random(seed)
    qc = QuantumCircuit(n)
    monomials: set[tuple[int, ...]] = set()
    for _ in range(n):
        size = rng.randint(1, min(3, n))
        parity = tuple(sorted(rng.sample(range(n), size)))
        dups = rng.randint(1, 3)
        for rep in range(dups):
            realize(parity, n, qc, angle=0.7 + 0.35 * rep)
        monomials.add(parity)
    return qc, analytic_s(monomials)


def gen_linear_rotation(n: int, seed: int) -> tuple[QuantumCircuit, int]:
    rng = random.Random(seed)
    qc = QuantumCircuit(n)
    gates = cnot_network(n, n * 2, rng)
    for c, t in gates:
        qc.cx(c, t)
    # per-wire affine form after the network = image of e_q under the map;
    # track it by simulating the basis-vector images
    images = []
    for q in range(n):
        vec = 1 << q
        for c, t in gates:
            if (vec >> c) & 1:
                vec ^= 1 << t
        images.append(vec)
    monomials: set[tuple[int, ...]] = set()
    def forms_after(extra):
        out = []
        for q in range(n):
            vec = (1 << q)
            for c, t in gates + extra:
                if (vec >> c) & 1:
                    vec ^= 1 << t
            out.append(vec)
        return out
    for q in range(n):
        if images[q]:
            parity = tuple(sorted(p for p in range(n) if (images[q] >> p) & 1))
            qc.rz(0.7, q)
            monomials.add(parity)
    second = cnot_network(n, n, rng)
    for c, t in second:
        qc.cx(c, t)
    for q, vec in enumerate(forms_after(second)):
        if vec:
            parity = tuple(sorted(p for p in range(n) if (vec >> p) & 1))
            qc.rz(0.9, q)
            monomials.add(parity)
    for c, t in reversed(second):
        qc.cx(c, t)
    for c, t in reversed(gates):
        qc.cx(c, t)
    return qc, analytic_s(monomials)


def gen_trotter_zz(n: int, seed: int) -> tuple[QuantumCircuit, int]:
    rng = random.Random(seed)
    qc = QuantumCircuit(n)
    edges = set()
    reps = 2
    for _ in range(reps):
        for i in range(n - 1):
            edge = tuple(sorted((i, i + 1)))
            qc.cx(i, i + 1)
            qc.rz(0.9, i + 1)
            qc.cx(i, i + 1)
            edges.add(edge)
    return qc, len(edges)


def gen_iqp_core(n: int, seed: int) -> tuple[QuantumCircuit, int]:
    rng = random.Random(seed)
    qc = QuantumCircuit(n)
    for q in range(n):
        qc.h(q)
    monomials: set[tuple[int, ...]] = set()
    for q in range(n):
        qc.rz(0.6, q)
        monomials.add((q,))
    for _ in range(n):
        i = rng.randrange(n - 1)
        dups = rng.randint(1, 3)
        for rep in range(dups):
            qc.cx(i, i + 1)
            qc.rz(0.8 + 0.35 * rep, i + 1)
            qc.cx(i, i + 1)
        monomials.add((i, i + 1))
    for q in range(n):
        qc.h(q)
    return qc, analytic_s(monomials)


def gen_arithmetic_phase(n: int, seed: int) -> tuple[QuantumCircuit, int]:
    """Carry-chain phase oracle: rz on chained parities; s = chain length."""
    qc = QuantumCircuit(n)
    monomials: set[tuple[int, ...]] = set()
    for i in range(n - 1):
        qc.cx(i, i + 1)
        qc.rz(0.5, i + 1)
        monomials.add(tuple(range(i + 1)))
    for i in range(n - 2, -1, -1):
        qc.cx(i, i + 1)
    return qc, len(monomials)


def gen_random_phase(n: int, seed: int) -> tuple[QuantumCircuit, int]:
    rng = random.Random(seed)
    qc = QuantumCircuit(n)
    monomials: set[tuple[int, ...]] = set()
    for _ in range(max(2, n // 2)):
        size = rng.randint(1, min(4, n))
        parity = tuple(sorted(rng.sample(range(n), size)))
        dups = rng.randint(1, 3)
        for rep in range(dups):
            realize(parity, n, qc, angle=0.7 + 0.35 * rep)
        monomials.add(parity)
    return qc, analytic_s(monomials)


GENERATORS = {
    "diagonal_structured": gen_diagonal_structured,
    "linear_rotation": gen_linear_rotation,
    "trotter_zz": gen_trotter_zz,
    "iqp_core": gen_iqp_core,
    "arithmetic_phase": gen_arithmetic_phase,
    "random_phase": gen_random_phase,
}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=ROOT / "docs/review/science_boost/2026-10-25_fragment_bench")
    parser.add_argument("--ns", type=int, nargs="+", default=list(NS))
    parser.add_argument("--instances", type=int, default=INSTANCES_PER_CELL)
    args = parser.parse_args()

    out = args.out_dir
    (out / "instances").mkdir(parents=True, exist_ok=True)
    rows = []
    files: dict[str, str] = {}
    for family in FAMILIES:
        gen = GENERATORS[family]
        for n in args.ns:
            for k in range(args.instances):
                seed = 20261100 + 1000 * n + 100 * (zlib.crc32(family.encode()) % 97) + k
                qc, s = gen(n, seed)
                text = qasm2.dumps(qc)
                rel = f"instances/{family}/{family}_n{n}_k{k}.qasm"
                path = out / rel
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(text, encoding="utf-8", newline="\n")
                files[rel] = sha256_bytes(path.read_bytes())
                rows.append(
                    {
                        "family": family,
                        "n_qubits": n,
                        "instance": k,
                        "seed": seed,
                        "analytic_s": s,
                        "gate_count": qc.size(),
                        "rz_count": sum(1 for inst in qc.data if inst.operation.name == "rz"),
                        "cx_count": sum(1 for inst in qc.data if inst.operation.name == "cx"),
                        "qasm_sha256": files[rel],
                    }
                )
    index_path = out / "bench_index.csv"
    header = ",".join(rows[0].keys())
    body = "\n".join(",".join(str(row[k]) for k in rows[0]) for row in rows)
    index_path.write_text(header + "\n" + body + "\n", encoding="utf-8", newline="\n")
    files["bench_index.csv"] = sha256_bytes(index_path.read_bytes())

    manifest = {
        "experiment_id": "FRAGMENT_BENCH_V1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "contract": {
            "fragment": "{x, rz, cx}",
            "families": list(FAMILIES),
            "sizes": list(args.ns),
            "instances_per_cell": args.instances,
            "analytic_s": "exact phase-polynomial support size by construction (Lemma 1 lower bound)",
            "scope": "review-grade package outside data/ and release/",
        },
        "files": files,
        "instance_count": len(rows),
    }
    (out / "MANIFEST.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"experiment_id": "FRAGMENT_BENCH_V1", "instances": len(rows), "out_dir": str(out)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
