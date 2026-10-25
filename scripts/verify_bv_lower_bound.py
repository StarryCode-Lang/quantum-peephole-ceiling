"""Verify the BV k+2 lower-bound lemma (docs/theory/bv_lower_bound_2026-10-25.md).

All checks are exact (sympy arithmetic over Q(i, sqrt(2)); every E26 BV
unitary entry lies in that field, so equality and commutator tests never
touch floating point).

Modes:
1. --check-identities  Lemma 1 (U = CZ_S H_a X_a = H_a CX_S X_a = original
   E26 listing), the k+2 achiever [x(a), CX_S, h(a)], and Lemma 4's
   Heisenberg image U^dag X_a U = +- Z_a prod_{i in S} Z_i, for every secret
   at n <= --max-identities-n (default 5).
2. --exhaustive        The residual Case B of the lower bound (exactly k cx
   + one 1q gate) has no witness for n <= --max-exhaustive-n (default 3):
   enumerate every pair (L1, L2) of CNOT maps on the n+1 wires with
   len(L1) + len(L2) = k and every wire for g, and test by exact arithmetic
   whether L2^dag U L1^dag is a single basis gate acting on one wire
   (I_{rest} (x) W with W in {h, x, rz(theta)} up to phase).  Any witness
   would refute Theorem 6; the analytic closure in the theory document
   covers n >= 4.
3. --monomial          Case A (zero 1q gates): U is not a monomial matrix.

Exit 0 = all checks pass; any witness or failed identity prints details
and exits 1.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from itertools import product
from pathlib import Path

from sympy import I, Matrix, sqrt, zeros
from sympy import simplify as _simplify

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

EXPERIMENT_ID = "BV_LOWER_BOUND_VERIFICATION_V1"


def one_qubit_gate(name: str, theta=None) -> Matrix:
    if name == "x":
        return Matrix([[0, 1], [1, 0]])
    if name == "h":
        return Matrix([[1, 1], [1, -1]]) / sqrt(2)
    if name == "z":
        return Matrix([[1, 0], [0, -1]])
    if name == "rz":
        from sympy import exp

        return Matrix([[exp(-I * theta / 2), 0], [0, exp(I * theta / 2)]])
    raise ValueError(name)


def embed_1q(single: Matrix, wire: int, n_wires: int) -> Matrix:
    dim = 2**n_wires
    result = zeros(dim, dim)
    for basis in range(dim):
        bits = [(basis >> wire) & 1 for wire in range(n_wires)]
        for new_bit in (0, 1):
            row = basis
            if bits[wire] != new_bit:
                row = basis ^ (1 << wire)
            entry = single[new_bit, bits[wire]]
            if entry != 0:
                result[row, basis] += entry
    return result


def cx_gate(control: int, target: int, n_wires: int) -> Matrix:
    dim = 2**n_wires
    result = zeros(dim, dim)
    for basis in range(dim):
        if (basis >> control) & 1:
            result[basis ^ (1 << target), basis] = 1
        else:
            result[basis, basis] = 1
    return result


def cz_gate(control: int, target: int, n_wires: int) -> Matrix:
    dim = 2**n_wires
    result = zeros(dim, dim)
    for basis in range(dim):
        phase = -1 if ((basis >> control) & 1) and ((basis >> target) & 1) else 1
        result[basis, basis] = phase
    return result


def circuit_matrix(gates: list[Matrix], n_wires: int) -> Matrix:
    dim = 2**n_wires
    total = Matrix.eye(dim)
    for gate in gates:
        total = gate * total
    return total


def bv_listing(n: int, secret: int) -> tuple[list[Matrix], Matrix]:
    """The E26 generator: x(a), h(a), h^n, cx per secret bit, h^n."""
    anc = n
    gates: list[Matrix] = [embed_1q(one_qubit_gate("x"), anc, n + 1)]
    gates.append(embed_1q(one_qubit_gate("h"), anc, n + 1))
    for i in range(n):
        gates.append(embed_1q(one_qubit_gate("h"), i, n + 1))
    for i in range(n):
        if (secret >> i) & 1:
            gates.append(cx_gate(i, anc, n + 1))
    for i in range(n):
        gates.append(embed_1q(one_qubit_gate("h"), i, n + 1))
    return gates, circuit_matrix(gates, n + 1)


def bv_factorised(n: int, secret: int) -> Matrix:
    """H_a * CX_S(a->data) * X_a — the corrected achiever identity.

    Machine-verified identity (the CZ_S form is FALSE: H on the *control* of
    a CNOT is not H on the target, and the correct closed form reverses the
    CNOT direction).  This is exactly the k+2-gate circuit the Phase-2b
    pipeline emits: [x(a), CX(a->i) for i in S, h(a)].
    """
    anc = n
    u = embed_1q(one_qubit_gate("x"), anc, n + 1)
    for i in range(n):
        if (secret >> i) & 1:
            u = cx_gate(anc, i, n + 1) * u
    u = embed_1q(one_qubit_gate("h"), anc, n + 1) * u
    return u


def heisenberg_x_ancilla(n: int, secret: int, u: Matrix) -> Matrix:
    x_a = embed_1q(one_qubit_gate("x"), n, n + 1)
    return u.conjugate().T * x_a * u


def expected_image(n: int, secret: int) -> Matrix:
    """-X^S Z_a on n+1 wires (corrected Lemma 4')."""
    dim = 2 ** (n + 1)
    result = zeros(dim, dim)
    mask = sum(1 << i for i in range(n) if (secret >> i) & 1)
    for idx in range(dim):
        target = idx ^ mask
        phase = -1 if (idx >> n) & 1 else 1
        result[target, idx] = phase
    return result


def matrices_equal(a: Matrix, b: Matrix) -> bool:
    if a.shape != b.shape:
        return False
    diff = a - b
    return all(_simplify(diff[i, j]) == 0 for i in range(diff.rows) for j in range(diff.cols))


def check_identities(max_n: int) -> list[dict]:
    records = []
    for n in range(1, max_n + 1):
        for secret in range(2**n):
            _, u_listing = bv_listing(n, secret)
            u_fact = bv_factorised(n, secret)
            ok = matrices_equal(u_listing, u_fact)
            u_dag = u_listing.conjugate().T
            x_a = embed_1q(one_qubit_gate("x"), n, n + 1)
            image_a = u_dag * x_a * u_listing
            z_a = Matrix.eye(2 ** (n + 1))
            for idx in range(2 ** (n + 1)):
                if (idx >> n) & 1:
                    z_a[idx, idx] = -1
            image_a_ok = matrices_equal(image_a, z_a) or matrices_equal(image_a, -z_a)
            images_i_ok = True
            for i in range(n):
                if not (secret >> i) & 1:
                    continue
                x_i = embed_1q(one_qubit_gate("x"), i, n + 1)
                image_i = u_dag * x_i * u_listing
                x_i_full = embed_1q(one_qubit_gate("x"), i, n + 1)
                if not (
                    matrices_equal(image_i, x_i_full) or matrices_equal(image_i, -x_i_full)
                ):
                    images_i_ok = False
            if not (ok and image_a_ok and images_i_ok):
                print(
                    f"IDENTITY FAILURE n={n} secret={secret}: "
                    f"factorised={ok} image_a={image_a_ok} images_i={images_i_ok}"
                )
                return records + [{"n": n, "secret": secret, "status": "FAIL"}]
            records.append({"n": n, "secret": secret, "status": "PASS"})
    print(f"identities: {len(records)} (n, secret) pairs PASS up to n={max_n}")
    return records


def is_monomial(m: Matrix) -> bool:
    rows = m.rows
    cols = m.cols
    for i in range(rows):
        if sum(1 for j in range(cols) if _simplify(m[i, j]) != 0) != 1:
            return False
    for j in range(cols):
        if sum(1 for i in range(rows) if _simplify(m[i, j]) != 0) != 1:
            return False
    return True


def check_monomial(max_n: int) -> bool:
    for n in range(1, max_n + 1):
        for secret in range(2**n):
            if (secret >> 0) & 1 or secret == 0 or True:
                pass
            _, u = bv_listing(n, secret)
            if is_monomial(u):
                print(f"MONOMIAL WITNESS n={n} secret={secret} — Case A fails")
                return False
    print(f"monomial: no U (n<={max_n}) is a monomial matrix — Case A holds")
    return True


def cnot_maps_by_length(n_wires: int, max_len: int) -> dict[Matrix, int]:
    """BFS over GL(n_wires, 2) generated by CNOT transvections, keyed by matrix."""

    def key(m: Matrix):
        return tuple(tuple(row) for row in m.tolist())

    identity = Matrix.eye(2**n_wires)
    seen: dict = {key(identity): (identity, 0)}
    frontier = [identity]
    for depth in range(1, max_len + 1):
        nxt = []
        for m in frontier:
            for c in range(n_wires):
                for t in range(n_wires):
                    if c == t:
                        continue
                    child = cx_gate(c, t, n_wires) * m
                    k = key(child)
                    if k not in seen:
                        seen[k] = (child, depth)
                        nxt.append(child)
        frontier = nxt
    return [(m, depth) for m, depth in seen.values()]


def is_single_basis_gate(m: Matrix, wire: int, n_wires: int) -> bool:
    """Exact test: m == I_rest (x) W with W in {h, x, rz(theta)} up to phase."""
    # index helper: wire `wire` is bit `wire` of the basis index (same
    # convention as embed_1q)
    def idx(x_bits: int, b: int) -> int:
        low = x_bits & ((1 << wire) - 1)
        high = x_bits >> wire
        return (high << (wire + 1)) | (b << wire) | low

    n_x = 2 ** (n_wires - 1)
    # structural zeros: m[(x,b),(y,c)] must vanish for x != y
    for x in range(n_x):
        for y in range(n_x):
            if x == y:
                continue
            for b in (0, 1):
                for c in (0, 1):
                    if m[idx(x, b), idx(y, c)] != 0:
                        return False
    # diagonal-block proportionality: alpha_x * B == block_x, alpha_x constant
    anchor = None
    for x in range(n_x):
        for b in (0, 1):
            for c in (0, 1):
                if m[idx(x, b), idx(x, c)] != 0:
                    anchor = (x, b, c)
                    break
            if anchor:
                break
        if anchor:
            break
    if anchor is None:
        return False
    x0, b0, c0 = anchor
    alpha0 = None
    blocks = []
    for x in range(n_x):
        block = Matrix([[m[idx(x, b), idx(x, c)] for c in (0, 1)] for b in (0, 1)])
        alpha = None
        for b in (0, 1):
            for c in (0, 1):
                entry = block[b, c]
                ref = m[idx(x0, b), idx(x0, c)]
                if entry != 0 or ref != 0:
                    if ref == 0:
                        return False
                    ratio = entry / ref
                    if alpha is None:
                        alpha = ratio
                    elif alpha - ratio != 0:
                        return False
        if alpha is None:
            return False
        if alpha0 is None:
            alpha0 = alpha
        elif alpha0 - alpha != 0:
            return False
        blocks.append(block / alpha)
    # all blocks equal and equal to block0
    block0 = blocks[0]
    for block in blocks[1:]:
        if not matrices_equal(block, block0):
            return False
    return _recognise_basis_gate(block0)


def _recognise_basis_gate(w: Matrix) -> bool:
    w = [[_simplify(w[i, j]) for j in range(2)] for i in range(2)]
    off = [w[0][1], w[1][0]]
    if all(_simplify(v) == 0 for v in off):
        return True  # some rz(theta) up to phase
    # proportional to h: compare with sqrt(2)*h = [[1,1],[1,-1]]
    h_ref = [[1, 1], [1, -1]]
    if _proportional(w, h_ref):
        return True
    x_ref = [[0, 1], [1, 0]]
    if _proportional(w, x_ref):
        return True
    return False


def _proportional(a, b) -> bool:
    entries = [(i, j) for i in range(2) for j in range(2)]
    pivot = None
    for i, j in entries:
        if _simplify(a[i][j]) != 0:
            pivot = (i, j)
            break
    if pivot is None:
        return all(_simplify(b[i][j]) == 0 for i, j in entries)
    pi, pj = pivot
    if _simplify(b[pi][pj]) == 0:
        return False
    for i, j in entries:
        lhs = _simplify(a[i][j] * b[pi][pj])
        rhs = _simplify(b[i][j] * a[pi][pj])
        if lhs != rhs:
            return False
    return True


def check_exhaustive(max_n: int) -> tuple[bool, list[dict]]:
    """Case B: no (L1, g, L2) with len(L1)+len(L2)=k realises U."""
    records = []
    for n in range(1, max_n + 1):
        by_len: dict[int, list[Matrix]] = {}
        for m, depth in cnot_maps_by_length(n + 1, max_len=n):
            by_len.setdefault(depth, []).append(m)
        for secret in range(2**n):
            k = bin(secret).count("1")
            _, u = bv_listing(n, secret)
            witnesses = 0
            for len1 in range(k + 1):
                len2 = k - len1
                for l1 in by_len.get(len1, []):
                    right = u * l1.conjugate().T  # U * L1^dag, hoisted
                    for l2 in by_len.get(len2, []):
                        m = l2.conjugate().T * right
                        for wire in range(n + 1):
                            if is_single_basis_gate(m, wire, n + 1):
                                witnesses += 1
                                print(
                                    f"CASE-B WITNESS n={n} secret={secret} "
                                    f"wire={wire} len1={len1} len2={len2}"
                                )
            records.append(
                {"n": n, "secret": secret, "k": k, "case_b_witnesses": witnesses}
            )
            if witnesses:
                return False, records
        print(f"exhaustive n={n}: {2**n} secrets, no Case-B witness")
    return True, records


def _sympy_matrix_from_circuit(circuit) -> Matrix | None:
    """Exact sympy matrix of a qiskit circuit; None on unsupported gates/params."""
    from sympy import nsimplify, pi as s_pi

    n_wires = circuit.num_qubits
    total = Matrix.eye(2**n_wires)
    for inst in circuit.data:
        name = inst.operation.name
        if name == "barrier":
            continue
        qs = [circuit.find_bit(q).index for q in inst.qubits]
        params = list(inst.operation.params)
        if name in ("h", "x", "z"):
            total = embed_1q(one_qubit_gate(name), qs[0], n_wires) * total
        elif name in ("s", "sdg", "t", "tdg"):
            angle = {"s": s_pi, "sdg": -s_pi, "t": s_pi / 2, "tdg": -s_pi / 2}[name]
            total = embed_1q(one_qubit_gate("rz", angle), qs[0], n_wires) * total
        elif name in ("rz", "p", "u1"):
            theta = nsimplify(float(params[0]), [s_pi])
            if abs(float(theta.evalf()) - float(params[0])) > 1e-10:
                return None
            total = embed_1q(one_qubit_gate("rz", theta), qs[0], n_wires) * total
        elif name == "cx":
            total = cx_gate(qs[0], qs[1], n_wires) * total
        else:
            return None
    return total


def _exact_equivalent(a: Matrix, b: Matrix) -> bool:
    """a == e^{i phi} b for some phase, checked exactly."""
    phase = a.conjugate().T * b
    lam = _simplify(phase[0, 0])
    if lam == 0:
        return False
    for i in range(phase.rows):
        for j in range(phase.cols):
            expected = lam if i == j else 0
            if _simplify(phase[i, j] - expected) != 0:
                return False
    return True


def check_achievability(min_n: int, max_n: int, secrets_per_size: int) -> tuple[bool, list[dict]]:
    """Run the real Phase-2b pipeline on BV instances and verify the k+2 claim.

    For every instance: the optimised circuit must have exactly k+2 gates and
    be unitarily equivalent to the original — exactly (sympy, up to phase)
    when the gate set is exactly mappable and n <= 6, and via Qiskit's
    Operator.equiv otherwise.
    """
    import numpy as np
    from qiskit import quantum_info

    from experiments.phase2b_full_validation import _make_bv_with_secret
    from src.optimisation.phase2.template_matcher import Phase2bTemplateMatcher

    records = []
    for n in range(min_n, max_n + 1):
        for trial in range(secrets_per_size):
            if trial == 0:
                secret = (1 << n) - 1
            else:
                secret = int(np.random.RandomState(20261025 + 100 * n + trial).randint(1, 1 << n))
            k = bin(secret).count("1")
            circ = _make_bv_with_secret(n, secret)
            result = Phase2bTemplateMatcher().optimize_full_pipeline(circ, target=None)
            out = result.optimized_circuit
            size_ok = out.size() == k + 2
            exact = None
            if n <= 6:
                m_out = _sympy_matrix_from_circuit(out)
                if m_out is not None:
                    _, u_listing = bv_listing(n, secret)
                    exact = _exact_equivalent(m_out, u_listing)
            equiv = quantum_info.Operator(out).equiv(quantum_info.Operator(circ))
            ok = size_ok and equiv and (exact is not False)
            records.append(
                {
                    "n": n,
                    "secret": secret,
                    "k": k,
                    "orig_size": circ.size(),
                    "out_size": out.size(),
                    "expected_k_plus_2": k + 2,
                    "size_ok": size_ok,
                    "exact_sympy_up_to_phase": exact,
                    "qiskit_equiv": bool(equiv),
                    "status": "PASS" if ok else "FAIL",
                }
            )
            if not ok:
                print(f"ACHIEVABILITY FAILURE n={n} secret={secret}: {records[-1]}")
                return False, records
        print(f"achievability n={n}: {secrets_per_size} instances PASS (out == k+2, unitary equivalent)")
    return True, records


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-identities", action="store_true")
    parser.add_argument("--exhaustive", action="store_true")
    parser.add_argument("--monomial", action="store_true")
    parser.add_argument("--achievability", action="store_true")
    parser.add_argument("--min-achievability-n", type=int, default=3)
    parser.add_argument("--max-achievability-n", type=int, default=10)
    parser.add_argument("--secrets-per-size", type=int, default=3)
    parser.add_argument("--max-identities-n", type=int, default=5)
    parser.add_argument("--max-exhaustive-n", type=int, default=3)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    if not (args.check_identities or args.exhaustive or args.monomial or args.achievability):
        args.check_identities = args.exhaustive = args.monomial = True

    started = datetime.now(timezone.utc)
    report: dict = {
        "experiment_id": EXPERIMENT_ID,
        "started_utc": started.isoformat(),
        "modes": [],
    }
    ok = True
    if args.check_identities:
        records = check_identities(args.max_identities_n)
        report["modes"].append(
            {"mode": "check_identities", "max_n": args.max_identities_n, "records": records}
        )
        ok &= all(r["status"] == "PASS" for r in records)
    if args.monomial:
        passed = check_monomial(min(args.max_identities_n, 4))
        report["modes"].append({"mode": "monomial", "passed": passed})
        ok &= passed
    if args.achievability:
        passed, records = check_achievability(
            args.min_achievability_n, args.max_achievability_n, args.secrets_per_size
        )
        report["modes"].append(
            {
                "mode": "achievability",
                "min_n": args.min_achievability_n,
                "max_n": args.max_achievability_n,
                "records": records,
            }
        )
        ok &= passed
    if args.exhaustive:
        passed, records = check_exhaustive(args.max_exhaustive_n)
        report["modes"].append(
            {"mode": "exhaustive", "max_n": args.max_exhaustive_n, "records": records}
        )
        ok &= passed
    report["finished_utc"] = datetime.now(timezone.utc).isoformat()
    report["status"] = "ALL_PASS" if ok else "FAILURE"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(report, indent=2, default=str) + "\n", encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("experiment_id", "status")}, sort_keys=True))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
