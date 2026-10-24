# Upstream report draft — Qiskit `optimization_level=3` is not monotone under a restricted basis

**Status**: draft only, **not submitted**. Prepared 2026-10-24 from experiment E61
(`scripts/e61_opt_level_monotonicity.py`,
`docs/review/science_boost/2026-10-24_opt_level_monotonicity/`).

**Why it is not submitted**: filing a public issue is an external action that needs the
owner's explicit go-ahead. Everything needed to file it is in this file.

---

## Summary

With `basis_gates=['h', 'x', 'rz', 'cx']`, `transpile(..., optimization_level=3)` returns
circuits containing **adjacent `rz`-`rz` pairs on the same qubit** that
`optimization_level=2` merges. On a 101-circuit panel, level 3 is **worse than level 2 on 6
circuits, better on 0**, for a net **+226 gates (+6.9%)**.

The pairs are genuine missed optimisations: merging them preserves the unitary exactly
(verified with `Operator.equiv` on all 6 circuits), and removes 207 gates.

The defect does not appear with the default basis (`optimization_level=3`, no
`basis_gates`) on the same circuits, so it is specific to the restricted-basis path.

## Environment

| | |
|---|---|
| Qiskit | 2.4.1 |
| Python | 3.12.12 |
| OS | Windows 11 (also worth checking on Linux before filing) |
| Transpiler args | `layout_method='trivial'`, `routing_method='basic'`, `seed_transpiler=42` |

## Minimal reproduction

```python
import qiskit
from qiskit import QuantumCircuit, transpile
from qiskit.quantum_info import Operator

BASIS = ["h", "x", "rz", "cx"]

# 4-qubit VQE-style ansatz, already normalised into BASIS.
# Full circuit: data/v14/.../normalized qasm for source e39 (see the CSV below).
base = QuantumCircuit.from_qasm_str(QASM)          # 128 gates, 4 qubits

l2 = transpile(base, basis_gates=BASIS, optimization_level=2,
               layout_method="trivial", routing_method="basic", seed_transpiler=42)
l3 = transpile(base, basis_gates=BASIS, optimization_level=3,
               layout_method="trivial", routing_method="basic", seed_transpiler=42)

def adjacent_rz_pairs(c):
    d = c.data
    return sum(
        1 for i in range(len(d) - 1)
        if d[i].operation.name == "rz" and d[i+1].operation.name == "rz"
        and d[i].qubits == d[i+1].qubits
    )

print(l2.size(), adjacent_rz_pairs(l2))   # 76   0
print(l3.size(), adjacent_rz_pairs(l3))   # 128  49
```

Merging the 49 adjacent pairs in `l3` by summing their angles gives **91 gates**, and
`Operator(l3).equiv(Operator(merged))` is `True`.

## Panel result

101 circuits from the project's frozen 128-source panel (root size <= 300 gates), all
normalised into `{h,x,rz,cx}` at `optimization_level=0` before transpiling:

| level | total gates | two-qubit gates | adjacent same-axis 1q rotation pairs | circuits affected |
|---|---|---|---|---|
| 0 | 4,790 | 803 | 803 | 22 |
| 1 | 4,750 | 803 | 781 | 18 |
| **2** | **3,291** | 717 | **0** | **0** |
| **3** | **3,517** | 717 | **191** | **6** |
| 3 (default basis) | 1,742 | 717 | 0 | 0 |

Level 3 vs level 2: worse on 6, better on 0, equal on 95; worst single-circuit regression
**+57 gates**; two-qubit counts identical (717), so the entire difference is single-qubit.

## Affected circuits

| family | n | L2 | L3 | adjacent pairs in L3 | closure fix | unitary check |
|---|---|---|---|---|---|---|
| VQE | 4 | 76 | 128 | 49 | 77 | pass |
| VQE | 4 | 79 | 133 | 50 | 79 | pass |
| VQE | 4 | 76 | 124 | 45 | 76 | pass |
| IQP | 6 | 43 | 62 | 16 | 43 | pass |
| RandomClifford | 4 | 31 | 48 | 16 | 31 | pass |
| RandomClifford | 4 | 28 | 46 | 16 | 28 | pass |

("closure fix" is the gate count after applying a commutation-closure pass that merges
adjacent same-axis rotations; it reproduces the level-2 count exactly on all six.)

## Expected behaviour

`optimization_level=3` should not produce a circuit that a single post-pass over adjacent
same-axis rotations can shorten. Either level 3 should run `Optimize1qGatesDecomposition`
to a fixed point after its final layout/routing passes, or the level ordering should be
documented as non-monotone for restricted bases.

## Notes for the maintainer

- The level-3 output is not a fixed point of its own single-qubit pass, which suggests a
  pass-ordering issue: a later level-3 pass re-introduces adjacent rotations after the 1q
  optimisation ran.
- Level 2 is clean on this panel, so the regression is introduced by something only level 3
  does.
- Worth checking whether the same happens with `optimization_level=3` and
  `basis_gates=['rz','sx','x','cx']` (the IBM default family), i.e. whether the trigger is
  the restricted basis or the specific `{h,rz}` single-qubit set.

## Data

- `docs/review/science_boost/2026-10-24_opt_level_monotonicity/level_sweep.csv` — all
  101 circuits x 5 configurations
- `docs/review/science_boost/2026-10-24_opt_level_monotonicity/fix_check.csv` — the 6
  affected circuits, with the closure fix and the unitary verdict
- `docs/review/science_boost/2026-10-24_opt_level_monotonicity/summary.json` — aggregates
