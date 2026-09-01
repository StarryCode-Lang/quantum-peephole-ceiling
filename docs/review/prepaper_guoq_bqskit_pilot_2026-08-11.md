# GUOQ+BQSKit bounded pilot (2026-08-11)

## Disposition

The official BQSKit resynthesis path is executable on this Windows host through
a resource-only service adapter. Three pre-registered inputs completed their
120-second budgets and retained exact-equivalent incumbents. This is a
successful executability pilot, but it is **not formal-comparison eligible** and
does not authorize the shared 520 run.

## Fixed configuration

- GUOQ official JAR and Nam-rule hashes are those recorded by the preceding
  GUOQ preflight; official artifact DOI `10.5281/zenodo.14057840`.
- Official `resynth.py` SHA-256:
  `f396195935932a3d682cd76fdfc798b561905346bcf465799e3df0eda256634f`.
- Isolated top-level dependencies: BQSKit 1.2.1, Qiskit 2.4.1, Requests 2.32.5.
  Every resolved wheel and SHA-256 is recorded in `dependency_lock.json`.
- GUOQ: Nam basis, `TWO_Q`, `BQSKIT`, default BQSKit optimization level 3,
  seed 0, 4 GiB Java heap, 120 seconds per input.
- The service adapter calls the official unmodified `bqskit_io`; it changes
  only `Compiler(num_workers=64)` to `Compiler(num_workers=1)` and records
  request timing. BLAS thread environment variables are fixed at one.

GUOQ performs rewrite search and BQSKit resynthesis asynchronously. Therefore
the first pilot's complete process tree was not single-core: combined CPU was
roughly twice wall time. This is reported as a resource-contract limitation,
not hidden as single-thread timing.

## Results

| Input | Status | BQSKit requests started/completed | Common gates in -> out | Common 2Q in -> out | Exact equivalent |
|---|---|---:|---:|---:|---:|
| `cnot_chain_4` | timeout incumbent | 1 / 1 | 24 -> 0 | 24 -> 0 | yes |
| `ghz_4` | timeout incumbent | 98 / 97, one censored | 6 -> 6 | 3 -> 3 | yes |
| `qft_4` | timeout incumbent | 16 / 15, one censored | 42 -> 136 | 12 -> 10 | yes |

The QFT result illustrates why the TWO_Q objective must not be summarized as a
general gate-count improvement: it reduced two-qubit count while increasing
total gates and depth.

## Timing semantics

- `adapter_parse_*`: adapter-side QASM parsing only; not claimed as GUOQ's
  internal Java parse time.
- `resynthesis_completed_*`: sum of completed official `bqskit_io` requests.
- `resynthesis_active_censored_*`: observed occupancy of a request killed at
  the 120-second boundary; never reported as a completed call.
- `rewrite_orchestration_residual_wall_seconds`: optimizer wall minus completed
  and censored server occupancy. It includes Java parsing, rewrite search,
  HTTP/serialization, incumbent output, and timeout overhead, because the
  unmodified JAR exposes no finer phase boundary.
- `pipeline_wall_seconds`: adapter parse + server startup + optimizer budget +
  independent verification.
- `combined_cpu_seconds` and `combined_peak_rss_bytes`: sampled over the Java,
  server, and BQSKit worker process tree.

The frozen source common-basis QASM defines input metrics. A post-run metric-only
audit corrected an initial adapter mistake that had retranspiled the Nam input;
raw pre-correction rows are retained under `raw_pre_metric_revalidation/`.

## Invalid overlap attempt

A later single-core-affinity verification rerun was stopped during its first
input when a concurrent heldout-v2 workload was detected. It is archived under
`preflight_invalid/bqskit_single_cpu_overlap_attempt_20260811/` and excluded
from every result and release gate. After termination, the complete GUOQ,
BQSKit, and Java process tree count was verified as zero.
