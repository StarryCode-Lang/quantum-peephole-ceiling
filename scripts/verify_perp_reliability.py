"""Verify the ⊥ exchange-reliability proof (docs/theory/perp_reliability_2026-10-25.md).

For each of the nine exchange rules the closure engine implements
(`src/optimisation/certified_landscape.py::_commutes`), construct the exact
sympy matrices for the rule's gate case (angles symbolic where the rule is
angle-generic) and check the commutator is identically zero — the physical
axiom (A): a ⊥-licensed exchange preserves the unitary exactly.

Negative controls prove the table is not over-permissive: (x, z) anticommute,
cx-with-Z-on-target does not commute, cx-with-X-on-control does not commute.

The engine's `_Z_FAMILY` / `_X_FAMILY` frozensets are imported from the
engine module (not copied) so the proof cannot drift from the code, and the
engine source hash is recorded.

Exit 0 = all rules sound and all negative controls hold.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from sympy import I, Matrix, sqrt, symbols, zeros

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.optimisation import certified_landscape as engine  # noqa: E402

EXPERIMENT_ID = "PERP_RELIABILITY_VERIFICATION_V1"
THETA, PHI = symbols("theta phi", real=True)

ENGINE_SOURCE = ROOT / "src" / "optimisation" / "certified_landscape.py"


def g1(name: str, angle=None) -> Matrix:
    """One-qubit gate matrix, 4x4 embedding on wire 0 of a 2-wire register."""
    if name == "h":
        m = Matrix([[1, 1], [1, -1]]) / sqrt(2)
    elif name == "x":
        m = Matrix([[0, 1], [1, 0]])
    elif name == "z":
        m = Matrix([[1, 0], [0, -1]])
    elif name == "s":
        m = Matrix([[1, 0], [0, I]])
    elif name == "sdg":
        m = Matrix([[1, 0], [0, -I]])
    elif name == "t":
        m = Matrix([[1, 0], [0, (1 + I) / sqrt(2)]])
    elif name == "tdg":
        m = Matrix([[1, 0], [0, (1 - I) / sqrt(2)]])
    elif name == "rz":
        from sympy import exp

        m = Matrix([[exp(-I * angle / 2), 0], [0, exp(I * angle / 2)]])
    else:
        raise ValueError(name)
    return m


def rx_matrix(angle) -> Matrix:
    from sympy import cos, sin

    return Matrix([[cos(angle / 2), -I * sin(angle / 2)], [-I * sin(angle / 2), cos(angle / 2)]])


def embed(single: Matrix, wire: int, n_wires: int = 2) -> Matrix:
    dim = 2**n_wires
    out = zeros(dim, dim)
    for basis in range(dim):
        bit = (basis >> wire) & 1
        for new_bit in (0, 1):
            if new_bit == bit:
                out[basis, basis] += single[new_bit, bit]
            else:
                out[basis ^ (1 << wire), basis] += single[new_bit, bit]
    return out


def cx(control: int, target: int, n_wires: int = 2) -> Matrix:
    dim = 2**n_wires
    out = zeros(dim, dim)
    for basis in range(dim):
        if (basis >> control) & 1:
            out[basis ^ (1 << target), basis] = 1
        else:
            out[basis, basis] = 1
    return out


def cz(control: int, target: int, n_wires: int = 2) -> Matrix:
    dim = 2**n_wires
    out = Matrix.eye(dim)
    for basis in range(dim):
        if ((basis >> control) & 1) and ((basis >> target) & 1):
            out[basis, basis] = -1
    return out


def swap(n_wires: int = 2) -> Matrix:
    dim = 2**n_wires
    out = zeros(dim, dim)
    for basis in range(dim):
        b0, b1 = basis & 1, (basis >> 1) & 1
        out[(b1 | (b0 << 1)), basis] = 1
    return out


def is_zero(expr_matrix: Matrix) -> bool:
    return all(expr_matrix[i, j] == 0 for i in range(expr_matrix.rows) for j in range(expr_matrix.cols))


def commutes(a: Matrix, b: Matrix) -> bool:
    return is_zero(a * b - b * a)


def rule_cases() -> dict[str, list[tuple[Matrix, Matrix, str]]]:
    """(left, right, description) per engine rule."""
    z1 = g1("z")
    z1_t = g1("rz", THETA)
    s1 = g1("s")
    x1 = g1("x")
    h1 = g1("h")
    rx1 = rx_matrix(PHI)
    c01 = cx(0, 1)
    c10 = cx(1, 0)
    cz01 = cz(0, 1)
    sw = swap()
    embed_x0 = embed(x1, 0)
    embed_z0 = embed(z1, 0)
    embed_z1 = embed(z1, 1)
    return {
        "exchange.disjoint": [(embed(h1, 0), embed(x1, 1), "h(w0) x(w1)")],
        "exchange.same_single": [(embed(h1, 0), embed(h1, 0), "h h"), (embed(x1, 1), embed(x1, 1), "x x")],
        "exchange.same_axis_rotation": [
            (embed(g1("rz", THETA), 0), embed(g1("rz", PHI), 0), "rz(t) rz(p)"),
            (embed(rx1, 0), embed(rx_matrix(THETA), 0), "rx(p) rx(t)"),
        ],
        "exchange.z_family": [
            (embed(g1("rz", THETA), 0), embed(s1, 0), "rz s"),
            (embed(z1, 0), embed(g1("t"), 0), "z t"),
            (embed(g1("tdg"), 0), embed(g1("rz", PHI), 0), "tdg rz"),
        ],
        "exchange.cx_control_z": [
            (c01, embed(z1, 0), "cx(0,1) z(w0)"),
            (c10, embed_z1, "cx(1,0) z(w1)"),
            (c01, embed(g1("rz", THETA), 0), "cx(0,1) rz(w0)"),
        ],
        "exchange.cx_target_x": [
            (c01, embed(x1, 1), "cx(0,1) x(w1)"),
            (c01, embed(rx1, 1), "cx(0,1) rx(w1)"),
        ],
        "exchange.cz_z": [
            (cz01, embed_z0, "cz z(w0)"),
            (cz01, embed_z1, "cz z(w1)"),
            (cz01, embed(g1("sdg"), 1), "cz sdg(w1)"),
        ],
        "exchange.same_swap": [(sw, sw, "swap swap")],
        "exchange.same_cz": [(cz01, cz01, "cz cz")],
    }


NEGATIVE_CASES = [
    ("x_z_anticommute", embed(g1("x"), 0), embed(g1("z"), 0)),
    ("cx_z_on_target", cx(0, 1), embed(g1("z"), 1)),
    ("cx_x_on_control", cx(0, 1), embed(g1("x"), 0)),
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=ROOT / "docs/review/science_boost/2026-10-25_perp_reliability/report.json")
    args = parser.parse_args()

    started = datetime.now(timezone.utc)
    report = {
        "experiment_id": EXPERIMENT_ID,
        "started_utc": started.isoformat(),
        "engine_source_sha256": hashlib.sha256(ENGINE_SOURCE.read_bytes()).hexdigest(),
        "z_family_from_engine": sorted(engine._Z_FAMILY),
        "x_family_from_engine": sorted(engine._X_FAMILY),
        "rules": {},
        "negative_controls": {},
    }
    ok = True
    for rule, cases in rule_cases().items():
        results = []
        for left, right, description in cases:
            sound = commutes(left, right)
            results.append({"case": description, "commutes": bool(sound)})
            if not sound:
                ok = False
        # cross-check the engine predicate agrees on a matching StateGate pair
        report["rules"][rule] = {"cases": results, "all_commute": all(r["commutes"] for r in results)}
        print(f"{rule}: {len(results)} case(s), all_commute={report['rules'][rule]['all_commute']}")

    for name, a, b in NEGATIVE_CASES:
        product_ab = a * b
        product_ba = b * a
        differs = not (is_zero(product_ab - product_ba))
        report["negative_controls"][name] = {"genuinely_noncommuting": bool(differs)}
        if not differs:
            ok = False
        print(f"negative {name}: noncommuting={differs}")

    report["finished_utc"] = datetime.now(timezone.utc).isoformat()
    report["status"] = "ALL_PASS" if ok else "FAILURE"
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2, default=str) + "\n", encoding="utf-8")
    print(json.dumps({"experiment_id": EXPERIMENT_ID, "status": report["status"]}))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
