# v14 execution status — 2026-09-07

This file records the scoped v14 engineering work. It is a derived execution
record; all sealed historical receipts remain unchanged.

| Phase | State | Evidence and boundary |
|---|---|---|
| A — evidence integration | OUT OF SCOPE | Manuscript integration and paper-only figures were removed from the active v14 workspace at the user's direction. Historical sealed evidence and independent receipts remain unchanged. |
| B0 — resource profile | COMPLETE | `docs/review/v14_e45_resource_profile_2026-09-07.md`; historical v13 resource boundary is preserved. |
| B1/B2 — safe search optimization | COMPLETE WITH RESOURCE BOUNDARY | `src/optimisation/certified_landscape.py`, `experiments/e45_development_grid/run.py`, and `experiments/e45_development_grid/exact_development.py`; compact exact BFS/minimax now uses first-operation-indexed matching, cached rule-id tables, canonical-byte splice hashing, lazy child byte materialization, safe peak-dominance pruning in the barrier traversal, single-action fast paths for deterministic local ordering, and cached structural-exchange classification, while the IDA* escape-depth engine uses an admissible gate-count lower bound plus exact `(state_hash, remaining_depth)` transposition memoization. Deadline checks now propagate through candidate generation and fail closed during high-branching action enumeration. Witness replay matches the recorded rule/location and checks only the rewritten local window, so large listings do not trigger full-circuit unitary multiplication. These changes pass exact-engine regression, including byte-stable certificate serialization, and preserve deterministic action order. The selected compact full panel records 93 complete finite-horizon certificates with 35 explicitly truncated cells; the selected screening arm has a 0.5359554 s p95 runtime, while the full exact arm has a 30.9174228 s p95 under the same 30 s cell budget. The complementary IDA* full panel records 63 exact escapes and 65 exact local optima, with zero time-budget boundaries under a 30 s cell budget. E44 oracle regression remains zero-mismatch. Reverse Quartz parameter-splitting edges remain illegal under the v13 contract. |
| B3 — v14 screening and development | COMPLETE WITH RESOURCE BOUNDARY | `data/v14/e45_development_grid/receipt.json`, `data/v14/e45_full_development/receipt.json`, `data/v14/e45_idastar_escape/receipt.json`, `release/v14_readiness_verdict.json`, and `docs/review/v14_e45_exact_development_2026-09-08.md`; screening covers 128 sources × 18 configurations × 6 arms = 13,824 rows, 18/18 eligible, selected `h3_b64_s200k`. The compact selected-configuration panel covers 128 sources × 6 arms = 768 rows, with 93 complete exact finite-horizon certificates and 35 resource-truncated cells. The complementary IDA* panel covers 128 rows, with 63 exact escapes and 65 exact local optima, with zero time-budget boundaries. The derived verdict remains `NOT_READY_FOR_PAPER` and `release/v13_readiness_verdict.json` is unchanged. |
| C1–C4 — manuscript work | OUT OF SCOPE | Paper writing, title selection, manuscript-only references, figures, and document compilation are excluded from the current objective. |
| D1 — CI | OUT OF SCOPE | GitHub Actions was removed at the user's direction. Local tests and verifiers remain the engineering gates. |
| D2 — Zenodo | MATERIALS PREPARED; AUTHORIZATION PENDING | `release/zenodo_deposit_metadata.json`; no license selection, upload, or DOI claim. |
| D3 — independent cold start | PROTOCOL PREPARED; EXTERNAL EXECUTION PENDING | `docs/verification/cold_start_protocol.md`; the v12 capsule SHA and a 69-member sparse package verification pass, including E38–E41, are recorded. Full extraction reached Windows `WinError 1450`, so a clean non-author execution has not been claimed. |
| D4 — real QPU | PROTOCOL PREPARED; AUTHORIZATION PENDING | `experiments/hardware_validation/real_qpu_protocol.json`; no token was used and no real-device result exists. |
| D5/E — publication and submission | OUT OF SCOPE | No paper writing, upload, or submission work is part of the current objective. |

The v14 artifacts are bounded engineering and screening evidence. The v14
verdict is generated from the receipt-bound artifacts and independently checked
by `scripts/verify_v14_readiness_verdict.py`. They do not change the historical
canonical totals, the v13 readiness verdict, or the external status of real
hardware and independent reproduction.
