# Pre-paper finalization command ledger

Status: execution ledger; amended 2026-08-24 to add post-run semantic and
provenance audits without changing the frozen E31 execution. Commands are run
only after external optimizer processes finish. Paths are relative to the
repository root unless absolute.

## RQ1 representation analysis

```powershell
D:\Downloads\miniforge3\python.exe analysis\prepaper_rq1_representation.py `
  --extended data\v7\e19_extended\e19_wcl_full_family.csv `
  --replication data\v6\e19\e19_wcl_listing_full_e19_full_20260620_123825.csv `
  --pilot data\v11\e31_listing_phase2b\e31_listing_phase2b_pilot.csv `
  --output-dir data\v10\prepaper\analysis\rq1
```

## RQ3 four-tool shared-input analysis

```powershell
D:\Downloads\miniforge3\python.exe analysis\prepaper_rq3_tool_comparison.py `
  --manifest data\v10\prepaper\sota\inputs\benchmark_manifest.csv `
  --custom data\v10\prepaper\sota\raw\custom_hybrid_20260809_170559_456518.csv `
  --qiskit data\v10\prepaper\sota\raw\qiskit_default_20260809_170559_395714.csv `
  --cirq data\v10\prepaper\sota\raw\cirq_default_20260810_020938_267115.csv `
  --tket data\v10\prepaper\sota\raw\tket_default_20260809_170602_708824.csv `
  --output-dir data\v10\prepaper\analysis\rq3
```

## External optimizer analysis

```powershell
D:\Downloads\miniforge3\python.exe analysis\revalidate_external_exact_fidelity.py `
  --quasar-raw data\v10\prepaper\external_baselines\quasar\shared_520\quasar_shared_520.csv `
  --quasar-manifest data\v10\prepaper\external_baselines\quasar\shared_520\inputs\benchmark_manifest.csv `
  --quartz-raw data\v10\prepaper\external_baselines\quartz\shared_520\quartz_shared_520.csv `
  --quartz-manifest data\v10\prepaper\external_baselines\quartz\shared_520\inputs\benchmark_manifest.csv `
  --audit data\v10\prepaper\external_baselines\exact_fidelity_revalidation.json

D:\Downloads\miniforge3\python.exe analysis\prepaper_external_baselines.py `
  --manifest data\v10\prepaper\external_baselines\quasar\shared_520\inputs\benchmark_manifest.csv `
  --quasar data\v10\prepaper\external_baselines\quasar\shared_520\quasar_shared_520_revalidated.csv `
  --quartz data\v10\prepaper\external_baselines\quartz\shared_520\quartz_shared_520_revalidated.csv `
  --output-dir data\v10\prepaper\analysis\external
```

## Publication-gate figures

```powershell
D:\Downloads\miniforge3\python.exe analysis\prepaper_figures.py `
  --rq1-dir data\v10\prepaper\analysis\rq1 `
  --heldout-dir data\v10\prepaper\heldout\analysis `
  --rq3-dir data\v10\prepaper\analysis\rq3 `
  --external-summary data\v10\prepaper\analysis\external\external_summary.csv `
  --output-dir data\v10\prepaper\figures
```

## E31 formal completion and integrated analysis

Run only after the formal orchestrator has exited cleanly, `formal.lock` is
absent, and the checkpoint contains the exact 28,152-row frozen schedule. This
single command creates the immutable CSV/SQLite seal and the formal
dual-estimand, factorial, Pareto, and hypervolume packet; the completion
manifest hashes both groups.

```powershell
D:\Downloads\miniforge3\python.exe analysis\e31_finalize_formal_run.py
```

## Final coverage, release, and verification

```powershell
D:\Downloads\miniforge3\python.exe scripts\audit_e31_first_party_import_closure.py
D:\Downloads\miniforge3\python.exe scripts\audit_equivalence_verifier_agreement.py
D:\Downloads\miniforge3\python.exe scripts\audit_semantic_mutation_sentinels.py
D:\Downloads\miniforge3\python.exe scripts\audit_rewrite_properties.py
D:\Downloads\miniforge3\python.exe scripts\audit_rewrite_order_confluence.py
D:\Downloads\miniforge3\python.exe scripts\audit_direct_dependencies.py
D:\Downloads\miniforge3\python.exe scripts\generate_sbom.py
D:\Downloads\miniforge3\python.exe scripts\verify_sbom.py
D:\Downloads\miniforge3\python.exe scripts\audit_external_links.py --live --strict
D:\Downloads\miniforge3\python.exe scripts\generate_metric_audit_ledger.py
D:\Downloads\miniforge3\python.exe scripts\verify_metric_audit_ledger.py
D:\Downloads\miniforge3\python.exe -m compileall -q analysis experiments scripts src tests
D:\Downloads\miniforge3\python.exe -m pytest tests -q
D:\Downloads\miniforge3\python.exe scripts\verify_prepaper_figures.py
D:\Downloads\miniforge3\python.exe scripts\audit_workspace_coverage.py
D:\Downloads\miniforge3\python.exe scripts\generate_prepaper_release_manifest.py
D:\Downloads\miniforge3\python.exe scripts\verify_prepaper_release_manifest.py
```

The import-closure audit is deliberately post-hoc: it proves that the identified
23-file closure equals the seven direct pre-run hashes plus the 16 disclosed
omissions, but it does not upgrade those 16 files to pre-run evidence. The
execution record must capture exit codes, hashes, model convergence/fallback
status, figure inspection, and final test counts. A command listed here is not
treated as complete merely because it is syntactically valid.

Tests and the figure verifier precede the final workspace scan so that their
generated caches and `figure_audit.json` are inside the scan boundary.  The
pre-paper manifest is then created from that immutable scan and deliberately
does not attempt to inventory itself.
