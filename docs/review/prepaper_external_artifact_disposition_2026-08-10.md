# External optimizer artifact disposition (pre-paper)

Status: execution audit, not a performance claim and not manuscript prose.

## Selection rule

An external method enters the quantitative table only if its released
implementation can consume the frozen logical inputs, emit inspectable circuit
artifacts, use a documented fixed configuration and timeout, and pass the
repository's independent exact-equivalence plus ITT contract. Published table
numbers are never substituted for local outputs.

## Selected formal executions

- **Quasar**: official Zenodo v3 artifact, archive MD5
  `ff3a49973c97316bca0fb2d347ea5478`; fixed Seq-EG step 8, three iterations,
  no ILP or escalation, one worker, 120 s internal budget. The Windows wrapper
  execution is segmented and checkpointed in
  `data/v10/prepaper/external_baselines/quasar/shared_520/execution_segments.json`.
  Formal execution is complete: 520 unique rows, 428 emitted outputs, 42 outer
  timeouts, 50 errors, and 408 outputs passing the independent exact
  average-gate-fidelity threshold. The revalidated result SHA-256 is
  `54542229e9d11a913b2473b9c9e9f1e49ef9e5ae54efd16f54b09e4acb29f884`.
- **Quartz**: official repository commit
  `c4abf876608b111b2900d59a3c4efd7982063c20`; the adapter changes only the
  test executable's input/ECC/output plumbing and leaves `Graph::optimize`
  unchanged. The official ECC set and patched test executable were built with
  MSVC, and the formal execution is complete: 520 unique rows, no wrapper
  timeout/error, and 519 outputs passing independent exact fidelity. The one
  invalid output is `vqe_twolocal_8`, trial 3 (average gate fidelity 0.56912).
  The revalidated result SHA-256 is
  `da3a3a50fd8d6a50a1e8452a61e6eb3442670601e574f1e8956a45caaae86a85`.

Both raw adapter validity fields were independently recomputed with
`(abs(Tr(U^dagger V))^2 + d)/(d^2+d) >= 1-1e-10`; raw files are retained.
Quasar remains at 408 valid, while Quartz changes from the adapter's stricter
`Operator.equiv` count of 399 to 519 under the frozen fidelity rule. Formal
statistical outputs are in `data/v10/prepaper/analysis/external/`.

## Quarl preflight disposition

Primary artifact: Zenodo record `10.5281/zenodo.10463907`, version v1. The
11.6 kB reproduction guide was downloaded and its MD5 exactly matches the
record (`205546c37b04746d599c1065463a9de3`). The guide states that training used
A100/V100 GPUs, its evaluator path requests four A5000 GPUs, the supplied
cluster credentials are placeholders, and the search commands use GPU-indexed
pretrained checkpoints plus Weights & Biases authentication. The current host
does not expose `nvidia-smi` and therefore has no locally callable NVIDIA/CUDA
runtime.

Disposition: **not quantitatively run on this host**. This is a hardware/runtime
contract mismatch, not evidence against Quarl. Paper-reported results remain
literature context only. A CPU rewrite or a reimplementation would be a new
method and is forbidden as an artifact comparison.

## GUOQ preflight disposition

Primary paper DOI: `10.1145/3669940.3707240`; artifact concept DOI:
`10.5281/zenodo.14055562`, resolving to version DOI
`10.5281/zenodo.14057840`. The current Zenodo API record contains 13.08 GB of
compressed files in total, including a 5.77 GB GUOQ Docker image and a 7.29 GB
Quarl image. The official README targets Linux/amd64 Docker, recommends at
least 32 GB RAM, and estimates about 26 hours for the limited workflow and four
years for the full workflow. It also states that new benchmarks can be
supplied, so lack of input extensibility is **not** a blocker.

Updated 2026-08-11 disposition: **three-input native rewrite-only smoke passed;
formal comparison not run**. The checksum-pinned official JAR emitted an
incumbent for each input, and all three passed independent exact equivalence.
The host still fails the official container preflight (Docker absent; 15.79 GiB
RAM), and BQSKit resynthesis was not assessed. See
`docs/review/prepaper_guoq_go_no_go_2026-08-11.md`. These smoke rows establish
executability only and remain excluded from quantitative ranking.

A subsequent bounded pilot also exercised the official BQSKit resynthesis path
for the same three pre-registered inputs at 120 seconds each. All retained
incumbents passed exact equivalence, but the run remains non-comparative:
BQSKit used one compiler worker and single-threaded BLAS, while GUOQ rewrite and
resynthesis execute asynchronously and the complete process tree was not
single-core. See `docs/review/prepaper_guoq_bqskit_pilot_2026-08-11.md`.

## Cut-and-meld / OAC preflight disposition

Primary records: arXiv:2502.19526 and IEEE QCE 2025 DOI
`10.1109/QCE65121.2025.00069`. The paper describes an SML/MLton implementation
with a C++ QASM oracle wrapper and reports VOQC/Quartz/QUESO oracle experiments.
Searches of the official arXiv record, paper/author pages, GitHub, and Zenodo on
2026-08-10 did not locate a released OAC code artifact or an executable record.

Disposition: **artifact unavailable after documented search**. Reimplementing
the pseudocode would test this repository's implementation, not the authors'
system, so it is excluded from quantitative ranking. Its proofs and reported
results remain mandatory novelty/claim-boundary context.

## Q-PreSyn scope disposition

Primary record: arXiv:2601.19738. It optimizes downstream Clifford+T T-count
through learned representation-changing edits, whereas the frozen 520-input
external table uses common-basis total gate count on general logical circuits.
It is therefore a direct novelty comparator but not a like-for-like metric
comparator under the frozen RQ3 contract. No paper number is imported into the
table.

## Interpretation boundary

Availability, hardware, and resource dispositions above are properties of this
replication environment. They do not establish method quality. Final external
validity is limited to tools that complete the exact shared-input contract, and
all unavailable methods remain named limitations. The formal comparison also
uses official documented configurations rather than an equalized internal
compute budget, so it is a reproducibility comparison under fixed configs, not
a hardware-normalized algorithmic ranking. Across the Quasar--Quartz validity
and gate-reduction endpoints, both family-cluster permutation p-values are
0.05799 after Holm correction; no confirmatory winner is declared.
