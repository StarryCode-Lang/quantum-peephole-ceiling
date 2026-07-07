# E19: WCL Listing Validation — FULL RUN COMPLETED

**Status**: Full canonical run completed (2026-06-20). 10000 rows generated.

**Canonical data file**: `e19_wcl_listing_full_e19_full_20260620_123825.csv`

**Purpose**: Validate Phase-1 optimization under Wire-Consecutive Listing (WCL) versus Layer-by-Layer (LBL) listing. This experiment answers:
1. How does the structural ceiling change under WCL vs LBL?
2. Does WCL expose new Phase-2 commutation opportunities?
3. Is the LBL->WCL gap consistent across all depths?

**Key Results** (full mode, 5 qubits, depth 1-50, 100 trials/depth, seed=42):
- LBL mean reduction: 0.000000 (zero reduction across all 5000 circuits)
- WCL mean reduction: 0.078285 (7.83% average, max 33.3%)
- Both models maintain perfect fidelity (1.0)
- WCL > LBL at all depths >= 2
- **CONCLUSION**: WCL produces non-zero Phase 1 reduction. The structural ceiling is listing-dependent. This confirms Theorem 1(a).

**Run parameters**:
- Mode: full
- Qubits: 5
- Depth range: 1-50
- Trials per depth: 100
- Total circuits: 5000 (10000 rows with both LBL and WCL)
- Seed: 42
- Optimizer: GreedyGateCancellation with success_reduction=0.01

**How to reproduce**: `python experiments/e19_wcl_listing/run.py --mode full --seed 42`

**Smoke test**: `python experiments/e19_wcl_listing/run.py --mode smoke --depth-range 1 1 --trials 1`

**Implementation note**: WCL uses `GreedyGateCancellation(..., wire_traversal=True)`; LBL uses `wire_traversal=False`. Metadata records mode, qubits, depth range, trials, optimizer selection, and the wire-traversal mapping.

**References**: framework.md "Listing Model Dependency"; lemmas.md Theorem 1(a) vs 1(b); listing_models_and_dag_compilers.md.
