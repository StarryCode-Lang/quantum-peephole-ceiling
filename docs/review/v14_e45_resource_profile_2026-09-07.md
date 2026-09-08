# v14 E45 resource profile (B0)

Date: 2026-09-07
Scope: the existing `data/v13/e45_development_grid/` screening package only.  No
sealed E45 artifact was modified.

## Historical screening profile

The E45 package contains 128 sources, 18 configurations, and 6 arms.  The
following counts are for the `certificate_guided_escape` arm (2,304 rows):

| Quantity | Observed value |
|---|---:|
| Resource-bounded rows from `precheck_gate_or_qubit_work_budget` | 1,458 / 2,304 (63.28125%) |
| Resource-bounded rows per configuration | 81 / 128 |
| Sources reaching the bounded search per configuration | 47 / 128 |
| Search rows marked `WITNESS_CERTIFIED_SEARCH_INCOMPLETE` | 846 |
| Search rows marked `ERROR` | 0 |
| E44-core Quartz rules | 149 (10 one-qubit, 139 two-qubit) |

The resource failure is therefore repeated by every configuration and is
dominated by the conservative precheck.  The CSV does not record per-process
RSS, so a historical memory peak cannot be reconstructed from this package.

Among rows that reached the search, the maximum observed state and expansion
counts grew with the horizon:

| Horizon | Maximum `states_seen` | Maximum `expanded` | Observed all-row p95 wall time |
|---:|---:|---:|---:|
| 2 | 45 | 9 | 0.02 s |
| 3 | 169 | 45 | 0.05 s |
| 4 | 457 | 109 | 0.08 s |

The precheck boundary is distributed across the panel: all Adder, Grover,
HaarRandom, HardwareEfficient, QAOA, QFT, QuantumWalk, RandomClifford,
UCCSD-involved, and VQE screening sources that were rejected were rejected at
that boundary, while the E44 neutral-exposure cases all passed it.  The exact
per-family source counts remain in `grid_results.csv` and are not reclassified
here.

## Diagnostic probes before the v14 implementation changes

For a diagnostic-only run, the two precheck constants were overridden in
memory; the E45 output files were not touched.  With `H=2`, `beam_width=16`,
and `state_budget=10,000`, the following probes completed:

| Probe | Normalized state | Wall time | States seen | RSS change |
|---|---:|---:|---:|---:|
| `iqp_4` | 4 qubits, 29 gates | 0.590 s | 211 | +3.42 MiB |
| `clifford_4` | 4 qubits, 29 gates | 1.597 s | 210 | +0.69 MiB |
| `bv_7` | 8 qubits, 22 gates | 0.309 s | 150 | +0.15 MiB |

A separate 4-qubit high-width probe above the old precheck boundary did not
finish within 80 seconds and was terminated as a diagnostic.  It is not a
formal E45 result.  The probes show that the historical failure percentage
cannot be interpreted as a measured memory failure for every rejected source;
the large-width tail still requires bounded instrumentation before a threshold
is raised.

## Optimization boundary for v14

The method contract defines the complete ordered normalized listing as the
state key; qubit relabeling is therefore not a semantics-preserving merge under
the current contract.  The v14 implementation now uses complete source
signature lookup, first-operation-constrained qubit mapping, one-pass state
normalization, full 256-bit digest bookkeeping, bounded top-K candidate
retention, and lazy adjacent-pair evaluation for terminal Greedy.  Guided beam
ranking uses the deterministic state-cost/pair-exposure tuple, and stops after
the first retained improving witness with an explicit `HEURISTIC_OMISSION`
reason.  No `EXACT_*` status is inferred from this bounded arm.

The optimized core passed the independent E44 oracle again: 1,024 cases,
5,120 rows, zero mismatches, zero replay failures, and zero determinism
failures.  This is an engineering regression result; it does not upgrade the
historical E45 resource verdict.

The subsequent B2 pass adds a safe peak-dominance prune to the compact
layered minimax traversal and an exact IDA* transposition table keyed by
`(state_hash, remaining_depth)`.  The former cannot improve a path whose
current peak already exceeds the best known barrier; the latter reuses only
fully explored failures whose successors and goal predicate are identical for
the same remaining depth.  Both preserve the ordered-listing state key and
the fail-closed `EXACT_*` contract.  The formal v14 panels were regenerated
after these changes and retain their recorded resource boundaries.

## v14 screening result (B3)

The v14 screening writes to `data/v14/e45_development_grid/` and leaves the
sealed v13 directory unchanged.  It uses the same 128-input scope (96 E39
inputs plus 32 E44 cases), 18 configurations, and 6 arms: 13,824 result rows.
For the resource gate, the `certificate_guided_escape` arm has 5 bounded rows
per configuration, or 90/2,304 rows = 3.90625%; all other guided rows have no
semantic failure.  All 18 configurations are eligible under the ≤5% gate.

The selected screening configuration is `h3_b64_s200k` (horizon 3,
beam width 64, state budget 200,000), with 40.8610127192 percentage points
paired ITT family-mean reduction and a 0.5359554-second all-row p95 runtime.
The v14 receipt is bound to these artifacts:

| Artifact | SHA-256 |
|---|---|
| `protocol.json` | `af47aaf5b910273a6780c438d6aa92d0f6e9dd546c26d9d1b657345a8c3f9843` |
| `normalization_manifest.csv` | `0f4babe8cd8a2b07efd5ee826152775ae0bc290649a4f48bd39eb25a811b4e09` |
| `grid_results.csv` | `4bac8e8a1189881c80f45aaae291d08316815e6b1042ac88af003fdb10a11683` |
| `config_summaries.json` | `7ddf4928d7bfc465cd8f87c38da86f681e3e214d9d6bbd2a99de3eec25a4226e` |
| `selection.json` | `877946a997cda4b7aca48b1adcfe0eae29c8f499ef7a43a91917c4d0ee70a556` |

The executable check is:
`python scripts/verify_e45_development_grid.py --output-root data/v14/e45_development_grid`.
It returns `PASS`.  This is a new bounded v14 development result; the
historical v13 receipt and `release/v13_readiness_verdict.json` remain
unchanged and are not manually upgraded by this screening.
