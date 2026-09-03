# Quasar: Equality Saturation for Quantum Circuit Optimization

**[PLDI 2026]** Equality Saturation for Quantum Circuit Optimization

## Overview

Quasar is a quantum circuit optimizer based on equality saturation.
It uses an e-graph to compactly represent an exponential space of equivalent circuits and extracts the optimal one, avoiding the phase-ordering problem inherent in sequential rewrite-based optimizers.
Key techniques include atomic rule inference, dual e-graph representations (DAG-EG + Seq-EG), Scheduled Equality Saturation, and ILP-based Sequence Reordering.

![Quasar Overview](paper/quasar.overview.png)

---
## Artifact

### Hardware requirements

- **Paper experiments:** 24-core Intel i9-13900KF, 64 GB RAM, Ubuntu 22.04
- **Reproducing figures from pre-computed data:** Any machine with Python 3.10+ (< 1 min)
- **Quick test (kick-the-tires):** ~10 seconds, < 1 GB RAM
- **Full from-scratch run (176 circuits × 10 min):** ~2 hours wall-clock on 4 workers, peak ~64 GB RAM
- **Full paper reproduction (176 circuits × 2 hours):** ~22–40 hours on 4 workers, peak ~64 GB RAM

> **Memory note:** each seq-eg worker may use up to ~16 GB during e-graph saturation.
> We recommend `WORKERS=4` for machines with ≥ 64 GB RAM. On smaller machines or when
> the most reliable reproduction is desired, use `WORKERS=1` (single worker, longest
> wall-clock but no inter-worker contention).

## 1. Install

### Option A: Docker (recommended)

**A.1: Pull the pre-built image (fastest, avoids build-time network issues)**

```bash
docker pull ghcr.io/arxgy/quasar-artifact:v2
docker tag ghcr.io/arxgy/quasar-artifact:v2 quasar-artifact
docker run --rm -it -v $(pwd)/figures:/artifact/figures quasar-artifact bash
```

**A.2: Build locally from the Dockerfile (fallback if the registry is unreachable)**

```bash
docker build -t quasar-artifact .
docker run --rm -it -v $(pwd)/figures:/artifact/figures quasar-artifact bash
```

Either path drops you into an interactive shell with all dependencies pre-installed
(including the `dag-eg` Rust binary and the CBC ILP solver). Generated figures are
mounted back to `./figures/` on the host for viewing.

### Option B: Local installation

**Python (>= 3.10)**

```bash
pip install -r requirements.txt
```

**System packages**

```bash
# LaTeX (required for plot text rendering — Linux Libertine fonts)
sudo apt install texlive-latex-base texlive-latex-extra texlive-fonts-extra \
    texlive-fonts-recommended texlive-plain-generic cm-super dvipng fonts-linuxlibertine
```

**Dependency summary**

| Package | Version tested | Purpose |
|---------|---------------|---------|
| numpy | 2.3 | Numerical computation |
| pandas | 3.0 | CSV processing |
| matplotlib | 3.10 | Figure rendering |
| scipy | 1.17 | Statistical functions |
| egglog | 13.0 | E-graph equality saturation engine |
| networkx | 3.6 | Graph algorithms (circuit DAG) |
| pulp | 3.3 | ILP solver for Seq-EG gate reordering |
| ortools | 9.15 | CP-SAT solver for DAG-EG extraction |
| qiskit | 2.3 | Baseline optimizer + transpilation |
| pytket | 2.15 | Baseline optimizer (TKET) |

### Directory structure

```
quasar-artifact/
├── seq-eg/                 # Seq-EG optimizer (Python + egglog)
├── dag-eg/                 # DAG-EG optimizer (Rust + egg)
├── benchmarks/
│   ├── circuits/           # 176 input QASM files (IBM gate set)
│   └── baselines/          # External baseline results (see note below)
├── results_provided/       # Pre-computed results (shipped with artifact)
│   ├── summary.csv         # Per-case best metrics (cx, total, fidelity) + all baselines
│   ├── compare.csv         # 2-qubit gate comparison table
│   ├── baseline_depth.csv  # Baseline circuit depths
│   ├── runs/               # Per-case optimizer output QASMs
│   ├── timelines/          # Quality-vs-time merged CSVs
│   └── *.noguide.csv / *.noilp.csv  # Ablation variants
├── results_local/          # (generated) Fresh experiment outputs
├── figures/                # (generated) Output PDFs
├── scripts/                # Plotting and data pipeline scripts
├── draw_all.sh             # One-command figure generation
└── ARTIFACT.md             # This file
```

**Note on baseline data:** `benchmarks/baselines/` contains results from five baseline optimizers (Qiskit, TKET, Quartz, QUESO, GuoQ/Quarl), each run with a 2-hour timeout on the same 176 benchmarks.

---

## 2. Kick-the-Tires (~2 minutes)

### Single-case demo (~2 seconds)

Run Quasar on a small benchmark to verify the optimizer works:

```bash
python3 seq-eg/entry.py \
    --init benchmarks/circuits/rd32-v0_66.qasm \
    --final results_local/test_rd32.qasm \
    --step 8 --no-ilp
```

Expected output:
```
[iter 1] cx: 16 -> 10 (Δ=-6) ... step=8
[iter 2] cx: 10 ->  7 (Δ=-3) ... step=8
[iter 3] cx:  7 ->  7 (Δ=+0) ... step=8
[escalation] converged at step=8 → escalate to step=9
...
[escalation] reached cap=N; stop.
[done] wrote final QASM to results_local/test_rd32.qasm
```

The optimizer reduces `rd32-v0_66` from **16 → 7 CX gates** (56% reduction) in ~2 seconds.
Each iteration runs equality saturation (`--step 8` = 8 e-graph exploration steps),
then ILP extraction + Sequence Reordering. Scheduled Equality Saturation escalates the
exploration step until `--max-step` or `--time-limit` is reached.

**Key parameters:**
- `--step N`: initial number of e-graph exploration steps per iteration
- `--iters K`: max optimization iterations within one step
- `--max-step M`: cap on step escalation (default: no cap)
- `--time-limit T`: wall-clock budget in seconds (for anytime mode)
- `--timeline-csv F`: log per-iteration metrics (elapsed, cx, total, fidelity)
- `--snapshot-dir D`: write a per-step qasm snapshot (`step{N}.qasm`) after each
  successful iteration, so OOM/timeout kills preserve partial progress on disk

### Reproduce all figures from pre-computed data (~60 seconds)

```bash
bash draw_all.sh
ls figures/figure*.pdf
```

This generates `figures/figure14.pdf` through `figures/figure20.pdf`.

---

## 3. Figure Reproduction (Pre-computed Data)

All figures can be reproduced from the pre-computed data in `results_provided/`.
Run `bash draw_all.sh` to generate all at once, or individually:

### Fig 14 — Size-increasing rule effect

```bash
python3 scripts/draw_size_increasing_sample.py --out figures/figure14.pdf
```
- **Data:** hardcoded in script (collected from `multiply_10` benchmark)

### Fig 15 — Main comparison panel (3×5: 2q / total / fidelity)

```bash
python3 scripts/draw_2q.py results_provided/compare.csv --out-dir figures --sort ours \
    --quartz benchmarks/baselines/summary/quartz.csv \
    --queso  benchmarks/baselines/summary/queso.csv \
    --guoq   benchmarks/baselines/summary/guoq.csv \
    --tket   benchmarks/baselines/summary/tket.csv \
    --quarl  benchmarks/baselines/summary/quarl.csv

python3 scripts/draw_panel.py \
    --csv-2q figures/2q.csv --csv-fid results_provided/summary.csv \
    --out figures/figure15.pdf
```
- **Data:** `results_provided/compare.csv`, `results_provided/summary.csv`, `benchmarks/baselines/summary/*.csv`

### Fig 16 — Depth comparison (1×5)

```bash
python3 scripts/draw_depth.py \
    --csv-depth results_provided/baseline_depth.csv \
    --runs-dir results_provided/runs --summary-csv results_provided/summary.csv \
    --out figures/figure16.pdf
```
- **Data:** `results_provided/baseline_depth.csv`, `results_provided/runs/*.qasm`, `results_provided/summary.csv`

### Fig 17 — Seq-EG vs DAG-EG case studies

```bash
python3 scripts/draw_performance.py \
    results_provided/performance_csla_mux_3.csv results_provided/performance_radd_250.csv \
    --out-prefix figures/figure17a --out-prefix figures/figure17b
```
- **Data:** `results_provided/performance_csla_mux_3.csv`, `results_provided/performance_radd_250.csv`

### Fig 18 — Quality-vs-time frontier

```bash
python3 scripts/draw_quality_time.py \
    --merged-csv results_provided/timelines/atomic_merged.csv \
    --prefill-csv results_provided/timelines/prefill_merged.csv \
    --baseline GuoQ:benchmarks/baselines/guoq.csv \
    --baseline Qiskit:benchmarks/baselines/qiskit.csv \
    --baseline Tket:benchmarks/baselines/tket.csv \
    --baseline Quartz:benchmarks/baselines/quartz.csv \
    --baseline Queso:benchmarks/baselines/queso.csv \
    --log-x --max-time 7200 --num-points 60 \
    --case-list results_provided/summary.csv \
    --out figures/quality_time_log_2h.pdf --out-embedded figures/figure18.pdf
```
- **Data:** `results_provided/timelines/atomic_merged.csv`, `benchmarks/baselines/*.csv`

### Fig 19(a)(b) — Ablation: Scheduled Equality Saturation + Sequence Reordering

```bash
python3 scripts/draw_ablation_total.py \
    --ours results_provided/summary.csv --noguide results_provided/summary.noguide.csv --noilp results_provided/summary.noilp.csv \
    --cmp results_provided/compare.csv --cmp_noguide results_provided/compare.noguide.csv --cmp_noilp results_provided/compare.noilp.csv \
    --out figures/ablation.pdf \
    --out-noschedule figures/figure19a.pdf --out-noreorder figures/figure19b.pdf
```
- **Data:** `results_provided/summary{,.noguide,.noilp}.csv`, `results_provided/compare{,.noguide,.noilp}.csv`

### Fig 20 — Ablation: rule configurations

```bash
python3 scripts/draw_ablation_rule.py \
    --atomic results_provided/timelines/atomic_merged.csv \
    --pairwise results_provided/timelines/pairwise_merged.csv \
    --raw results_provided/timelines/raw_merged.csv \
    --out figures/figure20.pdf --log-x --num-points 60 \
    --case-list results_provided/summary.csv
```
- **Data:** `results_provided/timelines/{atomic,pairwise,raw}_merged.csv`

---

## 4. Figure Reproduction (From Scratch)

This section describes how to re-run experiments from scratch and regenerate all data.
Fresh results are written to `results_local/` (never overwrites `results_provided/`).

### Estimated machine time

| Experiment | Figure | Quick test (1 min/case) | Full (2 hr/case) |
|-----------|--------|------------------------|------------------|
| Main optimization (atomic rules) | Fig 15, 16, 18 | ~45 min | ~6–10 h |
| Ablation: no Scheduled Equality Saturation | Fig 19a | ~45 min | ~6–10 h |
| Ablation: no Sequence Reordering | Fig 19b | ~45 min | ~6–10 h |
| Rule ablation: pairwise rules | Fig 20 | ~45 min | ~6–10 h |
| Rule ablation: raw/full rules | Fig 20 | ~45 min | ~6–10 h |

All times assume 4 parallel workers with ≥ 64 GB RAM.

> For a quick sanity check, use `--time-limit 60` (1 min/case). This completes in ~45 minutes
> and already shows significant optimization on most benchmarks.
> For full paper-quality results, use `--time-limit 7200` (2 hr/case).

### Handling OOM failures

With high worker counts, large circuits may be killed by the OS (exit code -9, OOM).
The pipeline now handles this transparently through two mechanisms:

1. **Per-case starting step** (via `case_step_config.csv`): `run_main.sh` passes
   `--step-config case_step_config.csv` to `batch_run_timed.py`, which looks up
   each case's paper-configured starting step. This avoids the coarse LOC-based
   heuristic that previously triggered OOM on reversible benchmarks like
   `vbe_adder_3`, `sym9_146`, `hwb6`.
2. **Per-iteration snapshots** (`--snapshot-dir`): the optimizer writes
   `runs/<case>/step{N}.qasm` after every successful iteration. Even if the
   process is SIGKILL'd mid-run, the most recent successful iteration's qasm is
   preserved on disk, and downstream figures pick it up automatically.

If OOM still persists on your hardware, reduce `--workers` (e.g., 2 or 1) —
fewer concurrent workers leaves more memory per case. Partial progress is
always preserved via the snapshot mechanism, so no re-run is required.

Manual recovery is only needed for truly intractable cases (e.g., `rd53_130`
at step 1, which we have pre-configured to start at step 5). To re-run one case:

```bash
python3 seq-eg/batch_run_timed.py \
    --list-file failed_cases.txt \
    --time-limit 7200 \
    --out-dir results_local/timelines/atomic \
    --save-runs-dir results_local/runs \
    --step-config case_step_config.csv \
    --workers 1
```

### Fig 15 — Main comparison (2q / total / fidelity vs 5 baselines)

`run_main.sh` runs all 176 circuits in two rounds, then draws Figure 15:

- **Round 1 (seq-eg, ILP on):** All cases with per-case starting step from
  `case_step_config.csv` (derived from paper snapshots); natural escalation
  up to `--max-step 15` or `--time-limit`.
- **Round 2 (seq-eg, ILP off):** Retry any Round-1 failures with `--no-ilp`
  as a lower-memory fallback; same per-case starting step.

After both rounds complete, a fallback-seeding step guarantees that every case
directory contains at least one qasm for downstream figures, so Figure 16
(depth) always covers the full 176 cases even under adversarial OOM.

```bash
# Quick test (~45 min): 1 min/case, 4 workers
bash scripts/run_main.sh 60 4

# Paper setup (~6–10 hours): 2h/case, 4 workers
bash scripts/run_main.sh 7200 4
```

**`SKIP_RUNS=1` — redraw figures from existing data (no experiments):**

```bash
SKIP_RUNS=1 bash scripts/run_main.sh
```

Useful after editing a plotting script, or to refresh figures mid-run while a
long experiment is still executing (invoke it from a second terminal via
`docker exec <container> ...` if you are running inside Docker).

**Live progress monitoring (optional, in a second terminal):**

```bash
tail -f results_local/timelines/atomic/<case>.csv    # per-case iter progress
```

Each iteration appends `(elapsed, iter, step, cx, total, fidelity)` to the
timeline CSV, so you can follow any case in real time.

> **Estimated wall-clock:** Quick test: ~45 min. Paper setup: ~6–10 hours
> (4 workers, 64 GB RAM). The per-case step config makes Round 1 far less
> OOM-prone than in previous versions of the artifact; per-iteration
> snapshots (`runs/<case>/step{N}.qasm`) preserve partial progress even
> if a case is SIGKILL'd mid-run.

### Fig 16 — Depth comparison

Uses the same `results_local/runs/` output from Fig 15. No additional experiment needed.

```bash
# Copy baseline depth data (external baselines, not regenerated)
cp results_provided/baseline_depth.csv results_local/baseline_depth.csv

# Draw
python3 scripts/draw_depth.py \
    --csv-depth results_local/baseline_depth.csv \
    --runs-dir results_local/runs --summary-csv results_local/summary.csv \
    --out figures/figure16.pdf
```

> **No additional CPU time** — reuses QASMs from Fig 15.

### Fig 17 — Seq-EG vs DAG-EG case studies

Requires both Seq-EG and DAG-EG runs on `csla_mux_3` and `radd_250` at varying step sizes.
Use pre-computed data for this figure.

### Fig 18 — Quality-vs-time (atomic rules)

No additional experiment needed — the Fig 15 batch already produces
`results_local/timelines/atomic_merged.csv` with per-case quality-over-time data.

**Draw:**
```bash
python3 scripts/draw_quality_time.py \
    --merged-csv results_local/timelines/atomic_merged.csv \
    --baseline GuoQ:benchmarks/baselines/guoq.csv \
    --baseline Qiskit:benchmarks/baselines/qiskit.csv \
    --baseline Tket:benchmarks/baselines/tket.csv \
    --baseline Quartz:benchmarks/baselines/quartz.csv \
    --baseline Queso:benchmarks/baselines/queso.csv \
    --log-x --max-time 60 --num-points 30 \
    --case-list results_local/summary.csv \
    --out figures/quality_time.pdf --out-embedded figures/figure18.pdf
```

> Adjust `--max-time` to match your `--time-limit` (60 for quick test, 7200 for paper).

### Fig 19(a)(b) — Ablation: no Scheduled Equality Saturation / no Sequence Reordering

**Experiment:** Run two ablation variants in parallel.

```bash
# No Scheduled Equality Saturation (--no-escalate)
python3 seq-eg/batch_run_timed.py \
    --list-file results_provided/list_full.txt \
    --time-limit 60 \
    --out-dir results_local/ablation/noguide_timelines \
    --save-runs-dir results_local/ablation/noguide_runs \
    --step-config case_step_config.csv \
    --max-step 15 --workers 4 \
    -- --no-escalate

# No Sequence Reordering (--no-ilp)
python3 seq-eg/batch_run_timed.py \
    --list-file results_provided/list_full.txt \
    --time-limit 60 \
    --out-dir results_local/ablation/noilp_timelines \
    --save-runs-dir results_local/ablation/noilp_runs \
    --step-config case_step_config.csv \
    --max-step 15 --workers 4 \
    -- --no-ilp
```

**Post-process:**

```bash
python3 scripts/build_ablation.py \
    --runs-root results_local/ablation/noguide_runs \
    --out-summary results_local/summary.noguide.csv \
    --out-compare results_local/compare.noguide.csv

python3 scripts/build_ablation.py \
    --runs-root results_local/ablation/noilp_runs \
    --out-summary results_local/summary.noilp.csv \
    --out-compare results_local/compare.noilp.csv
```

**Draw:**
```bash
python3 scripts/draw_ablation_total.py \
    --ours results_local/summary.csv \
    --noguide results_local/summary.noguide.csv \
    --noilp results_local/summary.noilp.csv \
    --cmp results_local/compare.csv \
    --cmp_noguide results_local/compare.noguide.csv \
    --cmp_noilp results_local/compare.noilp.csv \
    --out figures/ablation.pdf \
    --out-noschedule figures/figure19a.pdf \
    --out-noreorder figures/figure19b.pdf
```

> **Estimated CPU time:** 2 × ~45 min wall-clock (4 workers) with `--time-limit 60`.
> For paper results: use `--time-limit 7200` (2 × ~6–10 h).

### Fig 20 — Ablation: rule configurations (pairwise + raw/full rules)

**Experiment:** Run the optimizer with pairwise (3,067 rules) and raw/full (9,044 rules) rule sets.
These are much larger than the atomic rules (65 rules), so we use `--step 3` instead of `--step 8`.

```bash
# Pairwise rules
python3 seq-eg/batch_run_timed.py \
    --list-file results_provided/list_full.txt \
    --time-limit 60 \
    --out-dir results_local/timelines/pairwise \
    --merged-csv results_local/timelines/pairwise_merged.csv \
    --step 3 --workers 4 \
    -- --rules seq-eg/rules_pairwise.txt

# Raw/full rules
python3 seq-eg/batch_run_timed.py \
    --list-file results_provided/list_full.txt \
    --time-limit 60 \
    --out-dir results_local/timelines/raw \
    --merged-csv results_local/timelines/raw_merged.csv \
    --step 3 --workers 4 \
    -- --rules seq-eg/rules_full.txt
```

**Draw:**
```bash
python3 scripts/draw_ablation_rule.py \
    --atomic results_local/timelines/atomic_merged.csv \
    --pairwise results_local/timelines/pairwise_merged.csv \
    --raw results_local/timelines/raw_merged.csv \
    --out figures/figure20.pdf --log-x --num-points 30 \
    --max-time 60 --case-list results_local/summary.csv
```

> **Estimated CPU time:** 2 × ~45 min wall-clock (4 workers) with `--time-limit 60`.
> For paper results: use `--time-limit 7200` (2 × ~6–10 h), keep `--step 3`.

---