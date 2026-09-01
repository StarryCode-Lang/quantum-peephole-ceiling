# Pre-paper noise-aware hardware-surrogate validation (2026-08-11)

Status: **paired calibration-snapshot simulation; not a real-QPU result**.

## Frozen comparison contract

- Backends: `FakeManilaV2` and `FakeNairobiV2`, which package archived IBM
  calibration snapshots.
- Inputs: GHZ n=4, BV/oracle n=4, and the predeclared reducible
  random-UNIVERSAL n=4 instance.
- Treatments: original, Greedy, commutation Phase-2, and hybrid Phase-1+2.
- Original and optimized circuits share the identity initial layout, SABRE
  routing, translator basis conversion, transpiler seed 12345, and calibration
  snapshot. Transpiler optimization levels 0 and 1 are both reported.
- Sampling: 8192 shots at three fixed simulator seeds. Seeds are repeated
  measurements, not independent circuits.
- Semantic gate: every reduced result carries a verified numerical-unitary
  equivalence certificate. Unverified reduced outputs are rejected by the
  analysis.

The native resource vector includes 1Q/2Q/multi-Q counts, total and 2Q depth,
target-estimated scheduled duration, and a product-of-reported-gate-success
proxy. The latter ignores correlated errors, idling, context, and drift and is
not called hardware fidelity.

## Bounded result

The full run contains 288 sampling rows and 48 aggregate rows. Only two of the
three input circuits have a positive logical reduction. For each of
commutation Phase-2 and the hybrid pipeline there are eight eligible design
cells (two inputs x two snapshots x two transpiler levels):

- mean Hellinger-fidelity gain across cells: `+0.0018101`;
- positive Hellinger gain: 6/8 cells; worst cell: 0;
- mean scheduled-duration reduction: `4.7843%`;
- mean calibration-success-proxy gain: `+0.008084`.

The two optimizer labels produce identical output hashes in all eight eligible
cells, so they are not independent confirmations. GHZ shows no logical
reduction. The BV logical reduction is largely absorbed by backend compilation;
the random instance retains native 2Q and duration improvements. These three
inputs are descriptive mechanism checks, not a population sample.

## Claim boundary and remaining gate

This evidence supports only: *under two archived calibration snapshots and a
fixed paired mapping contract, one selected reducible random circuit retained a
small positive noise-model benefit after logical optimization*. It does not
establish real-device benefit, broad-family transfer, calibration-date
robustness, multiple-topology generality, or a hardware advantage.

The real-hardware protocol now has a credential-free dry-run and plans 24 PUBs
per repetition, three repetitions, and 8192 shots. It remains unexecuted because
no IBM Quantum credential is available. Real-QPU claims remain barred.

Machine-readable evidence:

- `data/v10/prepaper/hardware_validation/ehw_runs_full_20260811_123958.csv`
- `data/v10/prepaper/hardware_validation/ehw_summary_full_20260811_123958.csv`
- `data/v10/prepaper/hardware_validation/ehw_metadata_full_20260811_123958.json`
- `data/v10/prepaper/hardware_validation/analysis/paired_noise_aware_cells.csv`
- `data/v10/prepaper/hardware_validation/analysis/hardware_validation_report.json`
