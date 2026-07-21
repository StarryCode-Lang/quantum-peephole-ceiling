# E11 — Real-Circuit Optimizer Benchmark

**Canonical dataset**: `e11_merged_powered.csv` (519 rows) — merge of the
original full run (`e11_real_circuit_benchmark_e11_full_20260611_114615.csv`,
426 rows) and an independent supplemental replica of the underpowered
randomized families (Grover, IQP, Oracle/BV, UCCSD_inspired) added to reach
power beta >= 0.80.

## derived/

| File | Role |
|------|------|
| `derived/e11_real_circuit_benchmark_e11_supplemental_20260711_011036.csv` | Supplemental replica (93 rows), one of the two merge inputs |
| `derived/metadata_e11_supplemental_20260711_011036.json` | Run metadata of the supplemental replica (full provenance) |

The original full-run CSV is not present in this directory (superseded by the
merge); see `metadata.json` `merged_files` for its name and git history for its
content. Power analysis: Cohen's d = 0.3495, MWU power = 0.8595 (adequate).

Reproduce: `python experiments/e11_real_circuit_benchmark/run.py --mode full`
(then `run_supplemental.py` + merge) — see `metadata.json` `source_file`.
