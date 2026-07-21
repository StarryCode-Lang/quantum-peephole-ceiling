# Hardware Validation of Peephole Optimization (E-HW)

> **Status label — READ FIRST:** All quantitative results in this document are
> **noise-model simulations** using IBM device calibration snapshots shipped in
> `qiskit_ibm_runtime.fake_provider` (FakeManilaV2, FakeNairobiV2) executed with
> `qiskit_aer.AerSimulator`. **No real quantum hardware was used.** A
> ready-to-run real-hardware protocol is included in Section 7 and implemented
> in `experiments/hardware_validation/real_hardware_protocol.py`; it executes
> unchanged as soon as an IBM Quantum token is available.

- **Experiment ID**: EHW
- **Date**: 2026-07-20
- **Script**: `experiments/hardware_validation/run.py` (v1.1.0)
- **Data**: `data/v8/hardware_validation/ehw_{runs,summary,metadata}_full_20260720_150931.*`
- **Environment**: qiskit 2.4.1, qiskit-aer 0.17.2, qiskit-ibm-runtime 0.47.0, numpy 1.26.4, pandas 2.2.2 (Python 3.12, Windows)

---

## 1. Historical audit: has this project ever used real hardware?

**No.** A full-repository audit (2026-07-20, current `HEAD`) found:

| Probe | Pattern | Result |
|---|---|---|
| IBM runtime imports | `qiskit_ibm_runtime`, `IBMQ`, `ibmq_`, `QiskitRuntimeService` | **0 matches** in code, docs, and data manifests |
| Fake backends | `fake_provider`, `FakeManila`, `FakeBrisbane`, `FakeBackend` | **0 matches** (before this experiment) |
| Noise simulation in experiments | `NoiseModel`, `AerSimulator`, `from_backend`, `depolarizing`, `thermal_relaxation`, `shots` | **0 matches** in `experiments/` |
| Real-backend references | `backend.name` (non-fake) | **0 matches** |

Consequences:

1. Every fidelity figure in the existing 34 canonical datasets
   (`release/release_manifest.json`; the count was 27 at the time of the
   original audit) is an **exact noiseless
   unitary-equivalence fidelity** (statevector/operator comparison), not a
   sampled or hardware fidelity.
2. Noise appears only as **future work** in the manuscript
   (`docs/manuscript/manuscript.md` §7.6 item 8, noise-aware ceilings; the
   EHW noise-model validation itself is now §7.4), in
   `docs/manuscript/appendix.md` §C item 11 / §15.16, and in
   `docs/results/experimental_design.md` §4. No noise model of any kind has
   been run in this repository before EHW.
3. There are **no historical real-hardware results to extract**.

## 2. Credential audit → route 3b

| Check | Result |
|---|---|
| `QISKIT_IBM_TOKEN` environment variable | **absent** |
| `~/.qiskit/qiskitrc` saved account | **absent** |
| Decision | **Route 3b**: fake-backend noise-model validation + ready-to-run real protocol |

No real-hardware data is fabricated anywhere in this wave; the
`credential_audit` block is embedded in every EHW metadata JSON.

## 3. Method

### 3.1 Circuits (n ≤ 5, three representative families)

| Circuit | Family | Qubits | Construction | Role |
|---|---|---|---|---|
| `ghz_n4` | GHZ | 4 | `make_ghz(4)` | Irreducible control (0% reduction in E11) |
| `oracle_bv_n4` | Oracle/BV | 4+1 ancilla | `make_bernstein_vazirani(4, seed=42)` | 1q-dominated reducibility |
| `random_uni_n4_d24_s7` | Random/UNIVERSAL | 4 | `generate_circuit(4, depth=24, seed=7)` | Mixed reducibility incl. 2q gates |

**Transparent random-instance selection.** Random UNIVERSAL circuits sit near
their structural ceiling (most instances show ~0% reduction), so a
deterministic in-script scan over depth ∈ {16, 24, 32} × seed ∈ {42, 7, 123,
2024} selects the first configuration with hybrid reduction ≥ 5% **and** ≥ 1
removed two-qubit gate. The scan runs live on every execution and the full
scan table is stored in the metadata JSON. Selected: depth=24, seed=7
(96 gates, 20 CX).

### 3.2 Optimizers

Identical to the E11 real-circuit benchmark configuration:
`greedy_phase1`, `commutation_phase2`, `hybrid_phase1_2`
(`success_reduction=0.01`). All optimized circuits verified unitarily
equivalent (exact fidelity = 1.0 to machine precision in every row).

### 3.3 Backends, transpilation, sampling

- **Fake backends**: FakeManilaV2 (5 qubits), FakeNairobiV2 (7 qubits) —
  calibration snapshots of retired IBM devices, the standard NISQ
  noise-model proxies.
- **Transpilation**: `seed_transpiler=12345`, at **both**
  `optimization_level=0` (layout/routing/basis translation only) and
  `optimization_level=1` (default light optimization). Two levels are
  required because level 1's own 1q-cancellation passes can absorb the
  project optimizers' reductions (Finding F2).
- **Exact reference**: statevector probabilities of each *transpiled*
  circuit on the full backend width (so SWAP permutations are accounted for
  in the ideal distribution itself).
- **Sampling**: 8192 shots × 3 independent simulator seeds
  ({101, 202, 303}) on (a) noiseless `AerSimulator` and (b)
  `AerSimulator.from_backend(fake_backend)` (full device noise model).
- **Metrics**: Hellinger fidelity and TVD against the exact distribution;
  *dominant-mode mass* = sampled probability on bitstrings with
  `p_exact ≥ 0.5·max(p_exact)` (GHZ: the two all-equal components; BV: the
  secret bitstring).

### 3.4 Full-run configuration

`--mode full`: 288 sampling rows = 3 circuits × 4 versions × 2 backends ×
2 transpile levels × 2 sampler types × 3 seeds; 48 summary rows.
Runtime ≈ 4 min on this workstation.

## 4. Results

### 4.1 Structural reductions (logical, noiseless — backend independent)

| Circuit | greedy | commutation | hybrid | Notes |
|---|---|---|---|---|
| GHZ n=4 | 0.0% | 0.0% | 0.0% | Irreducible — matches E11 (0% on GHZ at all sizes) |
| Oracle/BV n=4 | 0.0% | **46.15%** (13→7) | **46.15%** | Six redundant H pairs on data qubits with secret bit 0 |
| Random d24 s7 | 0.0% | **6.25%** (96→90) | **6.25%** | Includes 20→18 CX (−10% 2q) |

Exact unitary-equivalence fidelity = 1.0 for every optimized circuit.

### 4.2 Noisy sampled fidelity (fake backends, 8192 shots × 3 seeds)

Original-circuit baselines and optimized-version **gains vs original**
(noisy Hellinger fidelity; Δmass = dominant-mode-mass gain):

| Circuit | Backend | Level | Original H (±std) | Best optimized gain | Δmass |
|---|---|---|---|---|---|
| GHZ | Manila | 0/1 | 0.8140 ± 0.0011 | 0 (identical circuits) | 0 |
| GHZ | Nairobi | 0 | 0.8013 ± 0.0037 | 0 | 0 |
| GHZ | Nairobi | 1 | 0.8133 ± 0.0034 | 0 | 0 |
| Oracle/BV | Manila | 0 | 0.7784 ± 0.0080 | +0.0011 (comm./hybrid) | +0.0011 |
| Oracle/BV | Nairobi | 0 | 0.7529 ± 0.0023 | +0.0018 | +0.0018 |
| Oracle/BV | both | 1 | 0.8205 / 0.8252 | **0.0000** (absorbed) | 0 |
| Random | Manila | 0 | 0.9485 ± 0.0010 | **+0.0033** | **+0.0046** |
| Random | Manila | 1 | 0.9510 ± 0.0015 | **+0.0030** | **+0.0047** |
| Random | Nairobi | 0 | 0.8946 ± 0.0037 | **+0.0023** | **+0.0047** |
| Random | Nairobi | 1 | 0.8821 ± 0.0027 | **+0.0016** | **+0.0044** |

The greedy column is omitted: 0% reduction on all three circuits → identical
circuits → zero gain (see runs CSV).

### 4.3 Sanity checks

- Noiseless sampled Hellinger fidelity ≈ 0.9995–1.0000 everywhere (8192-shot
  sampling noise floor), confirming the transpiled circuits implement the
  intended unitaries on both backends and levels.
- GHZ noisy dominant-mode mass (≈ P(0000)+P(1111)) = 0.801–0.814 — consistent
  with published 4-qubit GHZ fidelities on this generation of IBM devices.

## 5. Findings

- **F1 — Gate reduction measurably improves noisy fidelity.** For the random
  instance (the only one with two-qubit-gate reduction), the optimized
  circuit beats the original on **all four** backend × level cells and on
  both metrics (Hellinger gain +0.0016…+0.0033; dominant-mass gain
  +0.0044…+0.0047, i.e. 1.5–3× the per-cell seed standard deviation). The
  sign consistency across independent noise snapshots (Manila, Nairobi) is
  the validation signal: fewer 2q gates → less accumulated noise.
- **F2 — Backend transpilers absorb 1q-type peephole reductions.** The BV
  optimized circuit (−46% gates, all 1q) is *bit-identical* to the
  transpiled original at `optimization_level=1` on both backends: the
  transpiler's own 1q-cancellation passes recover the entire reduction
  (original: 39→13 gates, noisy H 0.7784→0.8205 on Manila). Peephole
  optimization value over 1q structure **does not survive standard
  compilation** — it only matters if the backend compiler is run at level 0.
- **F3 — Irreducible circuits (GHZ) show exactly zero optimizer effect, as
  the structural-ceiling theory predicts.** All versions coincide; GHZ noisy
  fidelity is therefore a pure device benchmark (≈0.81).
- **F4 — At level 0, routing overhead can dwarf peephole savings.** The BV
  original (1 logical CX) inflates to 7 CX through SWAP insertion on Manila's
  coupling map; the random circuit's basis translation inflates 96 logical
  gates to 262 physical gates. At small n, mapping effects dominate 1q
  peephole gains; reductions in **2q gates** are the ones that matter
  physically.
- **F5 — Logical reduction ≠ physical reduction.** BV: 46.15% logical → 0%
  physical at level 1. Random: 6.25% logical → 10% physical 2q reduction on
  Manila (both levels). Any hardware-facing claim must quote **post-transpile
  2q-gate reduction**, not logical gate reduction.

## 6. Expected differences: fake-backend noise model vs real hardware

| Aspect | This study (fake backends) | Real IBM device (Section 7 protocol) |
|---|---|---|
| Noise source | Frozen calibration snapshot (T1/T2, gate/readout errors at snapshot time) | Live calibration, drifts daily; typically **worse** than snapshot by 10–50% on error rates |
| Correlated/crosstalk errors | Only what the snapshot's noise model encodes (mostly local) | Real crosstalk, frequency collisions, ZZ coupling present |
| Leakage & non-Markovianity | Not modeled | Present, small at n≤5 |
| Shot-to-shot drift | None (stationary) | Present; mitigated by interleaving reps |
| Queue/scheduling | None | Minutes–hours; recorded per job |
| Expected fidelity direction | Optimistic upper bound | Slightly lower absolute fidelity; **gain ordering (optimized ≥ original) expected to hold** because it is driven by 2q-gate count, not by absolute error rates |

## 7. Real-hardware protocol (ready to run; NOT executed — no credentials)

Implemented in `experiments/hardware_validation/real_hardware_protocol.py`
(reuses the validated `run.py` pipeline; credential guard verified: exits
with code 2 and setup instructions when no token is present).

1. **Setup (one-time)**: `export QISKIT_IBM_TOKEN=<token>` (or
   `QiskitRuntimeService.save_account(channel='ibm_quantum', token=...)`).
2. **Dry run** (prints plan, submits nothing):
   `/d/Downloads/miniforge3/python experiments/hardware_validation/real_hardware_protocol.py --dry-run`
3. **Execute**:
   `/d/Downloads/miniforge3/python experiments/hardware_validation/real_hardware_protocol.py --shots 8192 --seed-reps 3`
   — backend defaults to `least_busy(operational, real, ≥5 qubits)`;
   `--backend ibm_brisbane` etc. to pin a device.
4. **Circuits/shots**: identical to Section 3 (GHZ n4, BV n4+1, random d24 s7;
   original + 3 optimized versions; transpile levels 0 and 1 with
   `seed_transpiler=12345`; 8192 shots per PUB; 3 independent rep jobs per
   level — real hardware exposes no seed control, so repetitions replace
   simulator seeds).
5. **Cost estimate**: 24 PUBs per level-job × 2 levels × 3 reps = 6 jobs,
   72 PUB executions; ≈2–10 s QPU time per PUB at n≤5 → **≈3–8 min total
   QPU time**, within the Open Plan free quota (10 min/month). Queue time is
   recorded from `job.metrics()`/`job.usage()` per job.
6. **Success criteria**:
   - C1: for every circuit with logical reduction > 0, real-device noisy
     Hellinger fidelity of optimized ≥ original within 2 standard errors
     (per backend × level);
   - C2: GHZ dominant-mode mass ≥ 0.5 on the real device (entanglement
     witness threshold);
   - C3: BV success probability within ±0.15 of the fake-backend prediction
     at the same level (model-drift bound);
   - C4: random-instance dominant-mass gain of `hybrid_phase1_2` > 0
     (sign consistency with the noise-model prediction +0.0044…+0.0047).
7. **Outputs**: `data/v8/hardware_validation/ehw_real_runs_<ts>.csv` +
   `ehw_real_metadata_<ts>.json` (same schema family as the noise-model run,
   plus per-job queue/usage seconds).

## 8. Reproduction

```bash
PY=/d/Downloads/miniforge3/python
$PY experiments/hardware_validation/run.py --mode smoke   # ~1 min, 2048 shots, 1 seed
$PY experiments/hardware_validation/run.py --mode full    # ~4 min, 8192 shots, 3 seeds
```

Outputs (atomic writes, timestamped): `ehw_runs_<mode>_<ts>.csv` (per-sample
rows), `ehw_summary_<mode>_<ts>.csv` (aggregates + gains),
`ehw_metadata_<mode>_<ts>.json` (provenance, credential audit, random-scan
table, package versions).

## 9. Limitations

1. **Noise-model simulation, not hardware** (Section 6); absolute fidelities
   are optimistic upper bounds.
2. Two retired-device snapshots (Manila 5q, Nairobi 7q); current-generation
   devices (Heron/Eagle, 127–156 q) have different noise structure — the
   real protocol defaults to a live least-busy device for this reason.
3. One random instance (deterministically selected for reducibility); the
   fidelity-gain magnitude (+0.002…+0.003 Hellinger per −10% 2q gates) is an
   n=4 estimate and should not be extrapolated without the larger real-device
   study in Section 7.
4. Fake backends were sampled locally — no queue/cost data exists for this
   wave; both are estimated (not measured) in Section 7 and marked as such.
