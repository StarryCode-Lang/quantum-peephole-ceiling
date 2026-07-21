# Wave-1 Review — Reproducibility & Environment

Worker: Environment Engineer (Repro). Date: 2026-07-20.
Scope: `environment.yml`, `requirements.txt`, `requirements-lock.txt`, `Dockerfile`,
`.github/workflows/ci.yml`, `docs/reproducibility.md`, `scripts/reproduce_all.py`.

All edits were preceded by timestamped backups (`*.bak-20260720-225828`) and the lock
file was replaced atomically (write `requirements-lock.txt.tmp` → `mv`).

## 1. Dependency pins vs release manifest

Audited `requirements.txt` and `environment.yml` against the `environment.packages`
section of `release/release_manifest.json`:

| Package | Manifest | requirements.txt | environment.yml | requirements-lock.txt |
|---|---|---|---|---|
| python | 3.12.12 | n/a | `python=3.12` | compiled on Python 3.12 |
| qiskit | 2.4.1 | `==2.4.1` ✅ | `==2.4.1` (pip) ✅ | `==2.4.1` ✅ |
| numpy | 1.26.4 | `==1.26.4` ✅ | `==1.26.4` ✅ | `==1.26.4` ✅ |
| scipy | 1.13.1 | `==1.13.1` ✅ | `==1.13.1` ✅ | `==1.13.1` ✅ |
| matplotlib | 3.9.0 | `==3.9.0` ✅ | `==3.9.0` ✅ | `==3.9.0` ✅ |
| pandas | 2.2.2 | `==2.2.2` ✅ | `==2.2.2` ✅ | `==2.2.2` ✅ |
| tqdm | 4.66.4 | `==4.66.4` ✅ | `==4.66.4` ✅ | `==4.66.4` ✅ |

All seven manifest packages were already pinned exactly; no drift found.
Additions made while fixing the CI test step (see §4): `pytest-cov==5.0.0` and
`pytest-timeout==2.3.1` were added to `requirements.txt` and `environment.yml`
(conda deps). These are test tooling, outside the manifest's core-package list.

## 2. requirements-lock.txt regeneration

- Installed/confirmed `pip-tools` 7.5.3 in the project Python 3.12 and regenerated the
  lock with hashes:
  `python -m piptools compile --generate-hashes --output-file=requirements-lock.txt requirements.txt`
- Result: 1818-line lock, every transitive dependency pinned with SHA-256 hashes.
- Diff of the package set vs the previous lock: only `pytest-cov` and `pytest-timeout`
  added; no package removed; all 14 top-level pins match `requirements.txt` exactly.
- Known harmless warning: pip-compile notes `setuptools` is not pinned (same treatment
  as the previous lock; standard for `--generate-hashes` without `--allow-unsafe`).

## 3. Dockerfile

- Base image pinned: `continuumio/miniconda3:latest` → `continuumio/miniconda3:26.5.3-1`.
  Selection basis: Docker Hub API (queried 2026-07-20) shows `26.5.3` / `26.5.3-1` as the
  current stable tags (`last_updated` 2026-07-08) and `latest` aliases `26.5.3`.
- Layer order kept: dependency layer (`environment.yml` + `conda env create`) before
  code/data layers.
- Added `COPY release/ ./release/` — required because `--verify` now reads
  `release/release_manifest.json` (see §6); previously the image could not have passed
  manifest verification. Also added `requirements-lock.txt` to the copied files.
- `CMD` confirmed: `conda run -n q-research python scripts/reproduce_all.py --verify`.
- Not built locally: the Docker CLI is not available in this worker's shell
  (`docker: command not found`); tag existence was verified via the Docker Hub API instead.

## 4. CI (`.github/workflows/ci.yml`)

- Test matrix: `["3.10", "3.12"]` → `["3.12"]` (matches the Python 3.12.12 release env).
- `lint` job `setup-python`: `"3.10"` → `"3.12"`.
- `verify-data-integrity` job `setup-miniconda`: `"3.10"` → `"3.12"`.
- Lint step confirmed free of `--exit-zero` (both flake8 invocations fail on findings).
- Coverage flags confirmed present: `pytest tests/ -q --timeout=600 --cov=src --cov-report=term-missing`.
- **Bug fixed:** the test step previously ran `pip install pytest-cov` and used
  `--timeout=600`, but `pytest-timeout` was in neither `requirements.txt` nor
  `environment.yml` — the CI test job would have died with
  `unrecognized arguments: --timeout=600`. Both plugins are now pinned in the env files
  (and the lock), and the redundant `pip install pytest-cov` line was removed.
- YAML syntax validated with `yaml.safe_load`.

## 5. docs/reproducibility.md

- "No exact lock file"–class stale text: none remained (the Lock-files section was
  already accurate). Added the exact `pip-compile --generate-hashes` regeneration command.
- **Fixed stale commands:** the lightweight-checks block referenced the non-existent
  `tests/test_core.py` and `scripts/characterize_fidelity_fallback.py`; it now runs
  `python -m pytest tests/ -q` and `py_compile` on files that exist.
- Documented that `--verify` validates every canonical CSV against
  `release/release_manifest.json` (existence + SHA-256 + exact row count) before the
  per-experiment structural checks.
- Full-reproduction section now states that `--all` runs pinned `--mode smoke`
  experiments and that full reruns use `--mode full` per the manifest's
  `full_experiment_entrypoints` (was: vague "E1-E18" note).
- Fidelity-fallback section rewritten honestly: the standalone characterization script
  is **not shipped** in this release (it exists nowhere in the repo, and
  `docs/verification/` does not exist); the structural-similarity fallback in
  `src/optimisation/base.py` is described with its uncharacterized-precision caveat.
- `environment.yml` YAML validated.

## 6. scripts/reproduce_all.py audit & fixes

Findings and fixes:

1. **`--verify` did not check the release manifest at all** (the core gap). Added
   `verify_release_manifest()`: loads `release/release_manifest.json` and fails on any
   missing file, SHA-256 mismatch, unreadable CSV, or row-count mismatch, across **all**
   manifest dataset entries (33 entries in the current manifest, incl. datasets whose
   experiments are not in the run registry, e.g. HELDOU/ISOLATION/SOTA/E10_PHASE2B_FULL/
   HARDWARE_VALIDATION). `--verify` now returns `manifest_ok AND structural_ok`.
2. **`--tests` was broken**: `run_tests()` invoked `tests/test_core.py`, which does not
   exist. Replaced with `python -m pytest tests/ -q`, mirroring CI exactly.
3. **`--all` ran experiments with implicit defaults.** Every registry entry whose script
   supports `--mode` is now pinned explicitly to `--mode smoke` (14 entries), so a future
   default change cannot silently turn `--all` into a multi-hour full run. Verified each
   script's argparse accepts the pinned flags.
4. **Registry coverage gaps fixed:** added E22 (`experiments/gate_shuffle_ablation.py`),
   E26 (`experiments/phase2b_full_validation.py`), E29 (`experiments/multi_seed_e04.py`)
   with matching output dirs and column rules (E22: n_qubits/reduction/fidelity; E26:
   accept-any theory-bounds schema; E29: default schema). Registry now has 24 entries;
   all script paths verified to exist.
5. Source-hash drift reporting kept warning-only (unchanged semantics).

## Validation performed

| Command | Result |
|---|---|
| `python -m py_compile scripts/reproduce_all.py` | OK |
| `python scripts/reproduce_all.py --verify` (run 3×) | **PASS** — all 33 manifest checksums + rows OK; all 24 structural checks OK; exit 0 |
| Pre-check of manifest SHA-256 vs files on disk | 0 problems |
| `pytest tests/test_statistical_analysis.py tests/test_commutation_bug_reproduction.py tests/test_gate_predicates.py tests/test_ag_canonical.py -q` | 117 passed in 3.82s |
| `pytest tests/ --collect-only -q` | 278 tests collected |
| `flake8 scripts/reproduce_all.py --max-line-length=120 --select=E9,F63,F7,F82` | clean |
| `yaml.safe_load` on `environment.yml`, `ci.yml` | OK |
| Registry script-path existence check (24 entries) | none missing |
| Docker Hub API check for `continuumio/miniconda3:26.5.3-1` | tag exists (`last_updated` 2026-07-08) |

## Changed files (this worker only)

- `requirements.txt` (+ pytest-cov==5.0.0, pytest-timeout==2.3.1)
- `environment.yml` (+ pytest-cov==5.0.0, pytest-timeout==2.3.1)
- `requirements-lock.txt` (regenerated with hashes on Python 3.12)
- `Dockerfile` (pinned base tag, added `release/` + lock to context, comments)
- `.github/workflows/ci.yml` (3.12-only, removed redundant pip install)
- `docs/reproducibility.md` (stale commands fixed, manifest-verify + lock docs)
- `scripts/reproduce_all.py` (manifest verification, run_tests fix, pinned smoke args, E22/E26/E29)
- Backups: the seven `*.bak-20260720-225828` files next to each edited file.
- This report: `docs/review/wave1/reproducibility.md`.

## Remaining gaps / notes for other workers

1. **Release manifest `reproduction.entrypoints` still references `tests/test_core.py`**,
   which does not exist (manifest owner's file; not regenerated by this worker).
2. **`experiments/e23_ag_canonical/run.py` rewrites the canonical CSV in place**
   (fixed filename, deterministic seeds `seed_base=2026`). A `--all` smoke run therefore
   overwrites `data/v7/e23/e23_ag_canonical_results.csv`; determinism makes this benign
   today, but timestamped outputs would be safer. Experiment scripts are outside this
   worker's scope.
3. **Full pytest suite exceeds 300 s locally** (killed by the worker tool limit mid-run);
   CI's 30-minute job timeout plus per-test `--timeout=600` covers it. 278 tests collect
   cleanly and the representative subset passes.
4. **Docker image not built** (no Docker CLI in this shell); base tag verified via the
   Docker Hub API. Recommend a CI or manual `docker build` sanity check before release.
5. `uv pip install --python /d/Downloads/miniforge3/python` failed to resolve the
   interpreter (`No virtual environment or system Python installation found`); the env's
   own `python -m pip` was used instead for the single local install (`pytest-timeout`).
6. `release/release_manifest.json` was regenerated by another worker during this pass
   (45 → 33 dataset entries, added `data/v8/hardware_validation`). `--verify` tracks the
   live manifest and passes against its current revision.
