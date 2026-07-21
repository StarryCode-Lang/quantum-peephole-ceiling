# Wave-1 Completion Report — Hardware Validation (E-HW)

- **Worker**: 硬件验证员_Hardware (Real Hardware Validation)
- **Date**: 2026-07-20
- **Route taken**: 3b (noise-model simulation) — no IBM Quantum credentials on this machine
- **Status**: COMPLETE. All owned artifacts created; verification commands pass.

## 1. What was done

1. **Historical audit (task 1)**: full-repo grep for `qiskit_ibm_runtime`, `IBMQ`,
   `ibmq_`, `QiskitRuntimeService`, `fake_provider`, `FakeManila/FakeBrisbane`,
   `backend.name` → **zero matches**. The project has never run real IBM Quantum
   hardware; nothing historical to extract. Additional grep over `experiments/`
   for `NoiseModel|AerSimulator|from_backend|depolarizing|thermal_relaxation|shots`
   → **zero matches**: all existing experiments are noiseless; every published
   fidelity number in this repo is exact unitary-equivalence fidelity.
2. **Credential audit (task 2)**: `QISKIT_IBM_TOKEN` env var absent;
   `~/.qiskit/qiskitrc` absent → route 3b. No real-hardware data fabricated.
3. **Noise-model validation (task 3b)**: built `experiments/hardware_validation/run.py`
   and executed smoke + full modes with `/d/Downloads/miniforge3/python`.
   Three circuits (GHZ n4, Oracle/BV n4+1, random UNIVERSAL n4 d24 s7) ×
   {original, greedy, commutation, hybrid} × 2 fake backends (FakeManilaV2,
   FakeNairobiV2) × 2 transpile levels (0, 1) × {ideal, noisy} × 3 seeds,
   8192 shots. CSVs + metadata JSON landed in `data/v8/hardware_validation/`.
4. **Real-hardware protocol (task 3b deliverable)**:
   `experiments/hardware_validation/real_hardware_protocol.py` — ready to run
   once a token exists; guard verified (exits code 2 with setup instructions).
   Protocol (circuits, shots, cost estimate, success criteria C1–C4) documented
   in `docs/results/hardware_validation.md` §7.
5. **Noise-model audit + expected differences (task 4)**:
   `docs/results/hardware_validation.md` §1 (audit table) and §6
   (snapshot vs live calibration, crosstalk, drift, direction of expected gap).

## 2. Files created (all inside owned scope)

| File | Purpose |
|---|---|
| `experiments/hardware_validation/run.py` | E-HW noise-model experiment (v1.1.0) |
| `experiments/hardware_validation/real_hardware_protocol.py` | Token-gated real-device protocol (not executed) |
| `data/v8/hardware_validation/ehw_runs_smoke_20260720_150244.csv` | smoke run (superseded dev artifact) |
| `data/v8/hardware_validation/ehw_summary_smoke_20260720_150244.csv` | smoke summary (superseded) |
| `data/v8/hardware_validation/ehw_metadata_smoke_20260720_150244.json` | smoke metadata |
| `data/v8/hardware_validation/ehw_runs_smoke_20260720_150858.csv` | smoke re-run after level-0/1 redesign |
| `data/v8/hardware_validation/ehw_summary_smoke_20260720_150858.csv` | smoke summary |
| `data/v8/hardware_validation/ehw_metadata_smoke_20260720_150858.json` | smoke metadata |
| `data/v8/hardware_validation/ehw_runs_full_20260720_150931.csv` | **FULL run, 288 rows (canonical)** |
| `data/v8/hardware_validation/ehw_summary_full_20260720_150931.csv` | **FULL summary, 48 rows (canonical)** |
| `data/v8/hardware_validation/ehw_metadata_full_20260720_150931.json` | **FULL metadata (provenance + credential audit + random-scan table)** |
| `docs/results/hardware_validation.md` | Full results document incl. audit, findings F1–F5, real protocol §7 |
| `docs/review/wave1/hardware_validation.md` | This completion report |

No files outside the owned scope were modified. `docs/manuscript/manuscript.md`
untouched. No `git add/commit/push` performed.

## 3. Verification commands and results

```bash
PY=/d/Downloads/miniforge3/python
$PY experiments/hardware_validation/run.py --mode smoke
# -> runs=96 rows, summary=48 rows, exit 0
$PY experiments/hardware_validation/run.py --mode full
# -> runs=288 rows, summary=48 rows, exit 0 (~4 min)
$PY -m py_compile experiments/hardware_validation/real_hardware_protocol.py  # COMPILE OK
$PY experiments/hardware_validation/real_hardware_protocol.py --dry-run
# -> prints credential-absent instructions, exit code 2 (guard works as designed)
```

Data integrity spot checks (pandas, Windows paths):

- full runs CSV: 288 rows; `unitary_fidelity_exact == 1.0` in every row;
  `ideal_hellinger_mean` ∈ [0.9995, 1.0000] (8192-shot noise floor) — samplers
  and transpilation sane.
- full summary CSV: 48 rows = 3 circuits × 4 versions × 2 backends × 2 levels.
- metadata JSON: `credential_audit.route = 3b_noise_model_simulation_NOT_real_hardware`;
  package versions recorded (qiskit 2.4.1 / aer 0.17.2 / ibm-runtime 0.47.0).

## 4. Headline results (from actual runs; see docs/results/hardware_validation.md)

- GHZ: 0% reduction (all optimizers) — irreducible control; noisy Hellinger
  ≈ 0.814 (Manila) / 0.801–0.813 (Nairobi). Zero optimizer effect, as the
  structural-ceiling theory predicts (F3).
- Oracle/BV: 46.15% logical reduction (commutation/hybrid; 13→7 gates, 1q-only)
  but **0% physical reduction at transpile level 1** — transpiler absorbs all
  1q peephole gains (transpiled original ≡ transpiled optimized) (F2). At
  level 0 the gain is only +0.0011…+0.0018 Hellinger (F4: routing overhead
  dominates at small n).
- Random d24 s7: 6.25% logical reduction incl. 20→18 CX; noisy fidelity gains
  positive on **all 4 backend×level cells** (Hellinger +0.0016…+0.0033;
  dominant-mode mass +0.0044…+0.0047, 1.5–3× per-cell seed std) (F1).
- F5: hardware-facing claims must quote post-transpile 2q-gate reduction
  (BV 46%→0%; random 6.25%→10% physical 2q).

## 5. Remaining gaps / handoff notes

1. **Real-device execution still pending** — requires an IBM Quantum token
   (Open Plan suffices; est. 3–8 min QPU time). Run
   `real_hardware_protocol.py --dry-run` then `--shots 8192 --seed-reps 3`;
   compare against success criteria C1–C4 (docs/results §7).
2. **Manuscript integration**: if the integration worker cites EHW, use only
   the §7-labeled noise-model numbers with the explicit "noise-model
   simulation, not real hardware" label; F2/F5 motivate quoting
   post-transpile 2q reductions in hardware-related claims.
3. **Coverage**: 2 retired-device snapshots × 1 random instance × n≤5.
   Gain magnitudes are small-n estimates; do not extrapolate.
4. Smoke CSVs from the earlier single-level design (…_150244) are kept for
   provenance; canonical data = `*_full_20260720_150931.*`.
5. Queue time and cost are **estimates** (marked as such in §7); no measured
   values exist until the real protocol runs.
