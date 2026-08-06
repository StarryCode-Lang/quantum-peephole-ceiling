"""
E30: Direct quantitative validation of Theorem 1(a) under WCL
==============================================================

Purpose
-------
Prior to this experiment, Theorem 1(a) (expected density of listing-adjacent
inverse pairs under wire-consecutive listing) had never been directly tested:
E19 only provided directional evidence (WCL reduction 7.83% > 0).  E30
generates circuits under the exact layer model assumed by the theorem,
re-lists them in WCL, counts listing-adjacent inverse pairs, and compares
the empirical mean against the theoretical prediction cell by cell.

Corrected theorem constants (2026-08-06)
----------------------------------------
The theorem as originally stated in the manuscript carried two constant
errors, both fixed during the 2026-08-06 audit and validated here:

1. One-qubit term.  With single-qubit gates drawn uniformly from a set
   G1 of size g1 that contains k1 discrete gates (the continuous rotation
   families contribute measure-zero inverse matches),

       p_inv^(1q) = k1 / g1^2        (NOT 1/g1^2 and NOT <= 2/g1^2)

   The original statement omitted the discrete-gate count k1.

2. Two-qubit term.  A cancelling two-qubit pair was counted once per wire
   in the "sum over n wires" argument, double-counting each pair.  The
   correct per-pair expectation carries a factor 1/2:

       E[|A_adj|] = n(d-1) * [ (1-rho)^2 * k1/g1^2 + rho^2 / (2 g2 (n-1)) ]

Generator contract (faithful to the theorem's layer model)
----------------------------------------------------------
- Each layer: qubits are randomly permuted and paired consecutively; each
  pair receives a two-qubit gate with probability rho (uniform over
  {cx, cz}, cx directed min-qubit -> max-qubit so gate identity is
  direction-invariant); every qubit not covered by a placed two-qubit gate
  receives a one-qubit gate drawn uniformly from the 11-label set
  {h, t, tdg, s, sdg, rx, ry, rz, x, y, z} (rotations get theta ~ U(0, 2pi)).
  Hence P(qubit carries a 2-qubit gate) = rho for paired qubits.
- The WCL listing groups gates by wire in temporal order.
- A cancellable adjacent pair is counted once (two-qubit pairs are counted
  on the lower-index endpoint wire only, matching the theorem's notion of
  a distinct adjacent inverse pair).

Outputs
-------
    data/v10/e30/e30_thm1a_wcl_results.csv          (canonical, per trial)
    data/v10/e30/metadata.json
    data/v10/e30/derived/e30_thm1a_cell_summary.csv (per-cell vs theory)
"""

from __future__ import annotations

import json
import math
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.provenance import file_sha256, git_commit

EXPERIMENT_ID = "E30"
VERSION = "1.0.0"

# Theorem constants for the standard gate set (manuscript section 2.1).
G1_LABELS = ["h", "t", "tdg", "s", "sdg", "rx", "ry", "rz", "x", "y", "z"]
K1_DISCRETE = 8          # h, t, tdg, s, sdg, x, y, z (rotations: measure zero)
G1_SIZE = len(G1_LABELS)  # 11
G2_SIZE = 2               # {cx, cz}, both self-inverse

SELF_INVERSE = {"h", "x", "y", "z"}
INVERSE_PAIR = {"s": "sdg", "sdg": "s", "t": "tdg", "tdg": "t"}
ROTATIONS = {"rx", "ry", "rz"}


def _inverse_of(label: str, theta: float) -> tuple[str, float]:
    """Return (label, angle) of the inverse gate."""
    if label in SELF_INVERSE:
        return label, 0.0
    if label in INVERSE_PAIR:
        return INVERSE_PAIR[label], 0.0
    return label, (-theta) % (2 * math.pi)


def _gates_cancel(a: tuple, b: tuple) -> bool:
    """True when gate record b is the inverse of gate record a.

    Gate record: (label, q0, q1_or_None, theta).
    For one-qubit gates q1 is None; two-qubit records store the normalized
    (min, max) pair plus direction flag encoded in q0 == control.
    """
    la, qa0, qa1, tha = a
    lb, qb0, qb1, thb = b
    if (qa1 is None) != (qb1 is None):
        return False
    if qa1 is None:
        # One-qubit gates on the same wire (guaranteed by construction).
        if la in SELF_INVERSE:
            return lb == la
        if la in INVERSE_PAIR:
            return lb == INVERSE_PAIR[la]
        if la in ROTATIONS:
            if lb != la:
                return False
            s = (tha + thb) % (2 * math.pi)
            return s < 1e-9 or abs(s - 2 * math.pi) < 1e-9
        return False
    # Two-qubit gates: identical gate on identical (normalized) pair.
    return la == lb and (qa0, qa1) == (qb0, qb1)


def generate_layer_model_circuit(n_qubits: int, depth: int, rho: float,
                                 rng: np.random.RandomState) -> list[list[tuple]]:
    """Generate one circuit as a list of layers under the theorem's model.

    Returns layers; each layer is a list of gate records
    (label, q0, q1_or_None, theta).
    """
    layers = []
    for _ in range(depth):
        perm = rng.permutation(n_qubits)
        layer: list[tuple] = [None] * n_qubits  # type: ignore
        i = 0
        while i + 1 < n_qubits:
            a, b = int(perm[i]), int(perm[i + 1])
            i += 2
            if rng.random() < rho:
                gate = "cx" if rng.random() < 0.5 else "cz"
                lo, hi = (a, b) if a < b else (b, a)
                # Store on BOTH qubits' slots; direction fixed lo->hi for cx.
                layer[a] = (gate, lo, hi, 0.0)
                layer[b] = (gate, lo, hi, 0.0)
            else:
                for q in (a, b):
                    label = G1_LABELS[int(rng.randint(0, G1_SIZE))]
                    theta = float(rng.uniform(0.0, 2 * math.pi)) if label in ROTATIONS else 0.0
                    layer[q] = (label, q, None, theta)
        if n_qubits % 2 == 1:
            q = int(perm[-1])
            label = G1_LABELS[int(rng.randint(0, G1_SIZE))]
            theta = float(rng.uniform(0.0, 2 * math.pi)) if label in ROTATIONS else 0.0
            layer[q] = (label, q, None, theta)
        layers.append(layer)
    return layers


def wcl_wire_blocks(layers: list[list[tuple]], n_qubits: int) -> list[list[tuple]]:
    """Re-list layers into wire-consecutive blocks (one block per wire)."""
    blocks = [[] for _ in range(n_qubits)]
    for layer in layers:
        for q in range(n_qubits):
            gate = layer[q]
            if gate is not None:
                blocks[q].append(gate)
    return blocks


def count_adjacent_inverse_pairs(blocks: list[list[tuple]]) -> tuple[int, int]:
    """Return (raw_distinct_pair_count, greedy_cancellation_count).

    raw: number of distinct adjacent inverse pairs in the WCL listing;
    two-qubit pairs are counted on the lower-index endpoint wire only.
    greedy: number of disjoint pairs removed by the stack (Phase-1) pass.
    """
    raw = 0
    greedy = 0
    for q, block in enumerate(blocks):
        stack: list[tuple] = []
        for idx in range(len(block)):
            gate = block[idx]
            # Raw adjacent-pair count against the previous gate on this wire.
            if idx > 0 and _gates_cancel(block[idx - 1], gate):
                lo, hi = gate[1], gate[2]
                if gate[2] is None or q == lo:
                    raw += 1
            # Greedy stack cancellation.
            if stack and _gates_cancel(stack[-1], gate):
                stack.pop()
                greedy += 1
            else:
                stack.append(gate)
    return raw, greedy


def _effective_two_qubit_prob(n: int, rho: float) -> float:
    """Per-qubit two-qubit placement probability under the matching model.

    The generator pairs qubits via a random permutation matching; when n is
    odd, one qubit per layer is necessarily left over and always receives a
    one-qubit gate, so the effective placement probability is
    rho * (n-1)/n rather than rho.  For even n this reduces to rho.
    """
    return rho * (2 * (n // 2)) / n


def _pair_coverage_prob(n: int, rho: float) -> float:
    """Probability that a specific qubit pair is covered by one layer.

    The generator pairs qubits via a random-permutation matching.  A fixed
    pair {q, p} lands on a pair boundary with probability 1/(n-1) for even
    n, but only 1/n for odd n (one qubit per layer is necessarily left
    over).  Multiplying by the activation probability rho gives the
    per-layer coverage probability.
    """
    boundary_prob = 1.0 / (n - 1) if n % 2 == 0 else 1.0 / n
    return rho * boundary_prob


def theory_expected_a_adj(n: int, d: int, rho: float) -> float:
    rho_eff = _effective_two_qubit_prob(n, rho)
    e_1q = n * (d - 1) * ((1.0 - rho_eff) ** 2) * K1_DISCRETE / (G1_SIZE ** 2)
    p_cov = _pair_coverage_prob(n, rho)
    e_2q = (d - 1) * (n * (n - 1) / 2.0) * (p_cov ** 2) / G2_SIZE
    return e_1q + e_2q


def theory_p_cancel(n: int, rho: float) -> float:
    """Effective per-wire cancellation probability (E[A_adj] / (n(d-1)))."""
    return theory_expected_a_adj(n, 2, rho) / n


def theory_expected_gates(n: int, d: int, rho: float) -> float:
    # Paired qubits contribute a two-qubit gate with prob rho (1 gate shared
    # by 2 qubits); the rest receive one one-qubit gate.
    pairs = n // 2
    per_layer = rho * pairs + (n - 2 * pairs) + (1 - rho) * 2 * pairs
    return d * per_layer


def run_e30(ns=(4, 5, 8), depths=(10, 20, 40), rhos=(0.0, 0.3, 0.6),
            n_trials: int = 500, seed_base: int = 300_000) -> pd.DataFrame:
    output_dir = PROJECT_ROOT / "data/v10/e30"
    derived_dir = output_dir / "derived"
    output_dir.mkdir(parents=True, exist_ok=True)
    derived_dir.mkdir(parents=True, exist_ok=True)

    rows = []
    cell_rows = []
    cell_idx = 0
    total_cells = len(ns) * len(depths) * len(rhos)

    for n in ns:
        for d in depths:
            for rho in rhos:
                cell_idx += 1
                raw_counts = []
                greedy_counts = []
                m_counts = []
                print(f"[{cell_idx}/{total_cells}] n={n} d={d} rho={rho}")
                for trial in range(n_trials):
                    seed = seed_base + cell_idx * 1_000_000 + trial
                    rng = np.random.RandomState(seed)
                    layers = generate_layer_model_circuit(n, d, rho, rng)
                    blocks = wcl_wire_blocks(layers, n)
                    raw, greedy = count_adjacent_inverse_pairs(blocks)
                    m = sum(len(b) for b in blocks)
                    raw_counts.append(raw)
                    greedy_counts.append(greedy)
                    m_counts.append(m)
                    rows.append({
                        "experiment_id": EXPERIMENT_ID,
                        "n_qubits": n,
                        "depth": d,
                        "rho": rho,
                        "trial": trial,
                        "seed": seed,
                        "m_gates": m,
                        "a_adj_raw": raw,
                        "a_adj_greedy": greedy,
                        "reduction_greedy": (2.0 * greedy / m) if m else 0.0,
                    })

                raw_arr = np.asarray(raw_counts, dtype=float)
                m_mean = float(np.mean(m_counts))
                theory = theory_expected_a_adj(n, d, rho)
                std = float(raw_arr.std(ddof=1)) if n_trials > 1 else 0.0
                se = std / math.sqrt(n_trials)
                z = (float(raw_arr.mean()) - theory) / se if se > 0 else 0.0
                p_cancel = theory_p_cancel(n, rho)
                theory_r = 2.0 * p_cancel * (n * (d - 1)) / theory_expected_gates(n, d, rho) \
                    if theory_expected_gates(n, d, rho) > 0 else 0.0
                cell_rows.append({
                    "experiment_id": EXPERIMENT_ID,
                    "n_qubits": n,
                    "depth": d,
                    "rho": rho,
                    "trials": n_trials,
                    "mean_a_adj": float(raw_arr.mean()),
                    "theory_a_adj": theory,
                    "rel_err": (float(raw_arr.mean()) - theory) / theory if theory > 0 else None,
                    "z_score": z,
                    "mean_m_gates": m_mean,
                    "theory_m_gates": theory_expected_gates(n, d, rho),
                    "mean_reduction_greedy": float(np.mean(
                        [2.0 * g / m if m else 0.0 for g, m in zip(greedy_counts, m_counts)])),
                    "theory_r_adj_upper": theory_r,
                    "p_cancel": p_cancel,
                })

    df = pd.DataFrame(rows)
    csv_path = output_dir / "e30_thm1a_wcl_results.csv"
    df.to_csv(csv_path, index=False)

    cell_df = pd.DataFrame(cell_rows)
    cell_path = derived_dir / "e30_thm1a_cell_summary.csv"
    cell_df.to_csv(cell_path, index=False)

    max_abs_z = float(cell_df["z_score"].abs().max())
    median_rel_err = float(cell_df.loc[cell_df["rho"] > 0, "rel_err"].abs().median()) \
        if (cell_df["rho"] > 0).any() else None

    metadata = {
        "experiment_id": EXPERIMENT_ID,
        "description": (
            "Direct quantitative validation of Theorem 1(a) (WCL adjacent "
            "inverse-pair density) under the corrected constants: "
            "p_inv^(1q) = k1/g1^2 with k1 = 8 discrete gates, g1 = 11; "
            "two-qubit term without per-wire double counting "
            "(rho^2 / (2 g2 (n-1)), g2 = 2)."
        ),
        "timestamp": datetime.now().isoformat(),
        "version": VERSION,
        "parameters": {
            "ns": list(ns),
            "depths": list(depths),
            "rhos": list(rhos),
            "n_trials": n_trials,
            "seed_base": seed_base,
        },
        "theory_constants": {
            "g1": G1_SIZE,
            "k1_discrete": K1_DISCRETE,
            "g2": G2_SIZE,
            "g1_labels": G1_LABELS,
        },
        "n_rows": len(df),
        "n_cells": len(cell_df),
        "max_abs_z_score": max_abs_z,
        "median_abs_rel_err_rho_positive": median_rel_err,
        "canonical_data_file": "e30_thm1a_wcl_results.csv",
        "derived_files": ["derived/e30_thm1a_cell_summary.csv"],
        "seed": seed_base,
        "python_version": sys.version.split()[0],
        "git_commit": git_commit(PROJECT_ROOT),
        "script_sha256": file_sha256(Path(__file__)),
        "notes": [
            "Generator implements the exact layer model assumed by Thm 1(a): "
            "per layer, random pairing; each pair gets a 2-qubit gate with "
            "probability rho (cx directed min->max for direction-invariant "
            "identity); unpaired slots get a uniform 1-qubit gate from the "
            "11-label set (rotations theta ~ U(0, 2pi)).",
            "Adjacent inverse pairs are counted once per distinct pair "
            "(two-qubit pairs on the lower-index endpoint wire only).",
            "Corrects the two constant errors in the original theorem "
            "statement (missing k1 factor; double-counted 2-qubit term); "
            "see docs/theory/formal_results.md correction note 2026-08-06.",
        ],
    }
    with open(output_dir / "metadata.json", "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    print(f"\nE30 complete: {len(df)} trials across {len(cell_df)} cells")
    print(f"  max |z| = {max_abs_z:.3f}   (well-calibrated theory: |z| < ~4)")
    print(f"  median |rel err| (rho>0) = {median_rel_err:.4f}")
    print(f"  CSV: {csv_path}")
    return df


if __name__ == "__main__":
    run_e30()
