# Documentation

This directory separates current project guidance from immutable evidence and
historical research records.

## Start here

| Question | Document |
|---|---|
| What is complete, improved, or still open? | [`PROJECT_STATUS.md`](PROJECT_STATUS.md) |
| How did the experiments evolve? | [`EXPERIMENT_HISTORY.md`](EXPERIMENT_HISTORY.md) |
| How can the results be reproduced? | [`reproducibility.md`](reproducibility.md) |
| Which data are canonical or derived? | [`../data/README.md`](../data/README.md) |
| What are the data fields? | [`data_dictionary.md`](data_dictionary.md) |
| What was the experimental design? | [`results/experimental_design.md`](results/experimental_design.md) |
| What are the aggregate findings? | [`results/analysis_summary.md`](results/analysis_summary.md) |
| What is the theoretical framework? | [`theory/framework.md`](theory/framework.md) |

## Directory roles

- `analysis/` contains issue-specific analyses that remain useful for
  interpreting results.
- `results/` contains experiment design and result summaries.
- `theory/` contains definitions, proofs, scope notes, and proof audits.
- `review/` contains hash-bound audit records plus the active v12-v14 execution
  state. Dated files are evidence records, not the recommended reading order.
- `verification/` contains independent and cold-start verification protocols.
- `references/` contains the literature record and search ledger.
- `manuscript/` is retained as research material but is outside the current
  implementation and repository-cleanup scope.

## Evidence boundaries

Historical canonical totals are controlled by `data/DATA_CANONICAL.md` and
`release/release_manifest.json`. E31-E37 and v12-v14 are separately bounded
packages. Status labels such as `PASS`, `RESOURCE_BOUNDED`, `EXTERNAL`, and
`NOT_READY_FOR_PAPER` are distinct and must remain distinct.

Older process notes removed from the live documentation remain recoverable
from the frozen restore capsule and Git history. Their useful conclusions are
summarized in [`EXPERIMENT_HISTORY.md`](EXPERIMENT_HISTORY.md).
