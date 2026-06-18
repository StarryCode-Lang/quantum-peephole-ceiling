# E19: WCL Listing Validation — SCRIPTED, NOT FULL RUN

**Status**: Scripted with smoke/full CLI modes; no full canonical run is committed.

**Purpose**: Validate Phase-1 optimization under Wire-Consecutive Listing (WCL) versus Layer-by-Layer (LBL) listing. This experiment would answer:
1. How does the structural ceiling change under WCL vs LBL?
2. Does WCL expose new Phase-2 commutation opportunities?
3. Is the LBL→WCL gap (~18% observed in E1) consistent across all circuit families?

**How to run safely**: use `python experiments/e19_wcl_listing/run.py --mode smoke --depth-range 1 1 --trials 1` for a tiny validation. Full mode remains deferred due to computational cost and scope.

**Implementation note**: WCL uses `GreedyGateCancellation(..., wire_traversal=True)`; LBL uses `wire_traversal=False`. Metadata records mode, qubits, depth range, trials, optimizer selection, and the wire-traversal mapping.

**References**: framework.md §"Listing Model Dependency"; lemmas.md Theorem 1(a) vs 1(b); listing_models_and_dag_compilers.md.
