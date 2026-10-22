# Independent cold-start reproduction protocol

Status: **protocol prepared; independent execution pending** (`external_cold_start: OPEN`
in `release/v15_readiness_verdict.json`).

This procedure is for a fresh user account and a clean environment. The executor
must start from a pinned Git revision of this repository and must not mix files
from the author's working tree into the extracted directory.

> **Revision note (2026-10-18).** Steps 1–2 previously instructed the reader to
> download `release/prepaper_v12_restore_capsule.zip`. That archive was **retired
> on 2026-10-11** (`docs/review/v15_cleanup_2026-10-11.md`): it was tracked but
> unpinned by any manifest and is fully recoverable from Git history. The protocol
> below therefore uses Git as the transport. It also adds the v13–v15 verifier
> chain, which the v12-era capsule never contained, and a list of known traps.

## 1. Obtain the pinned tree

```text
git clone <repository-url> q-research-cold-start
cd q-research-cold-start
git checkout <PINNED_COMMIT_SHA>
git rev-parse HEAD          # must equal the pinned SHA; record it in the receipt
git status --porcelain      # must be empty
```

`<PINNED_COMMIT_SHA>` is the commit named in the release record you are
reproducing. For the v15 wave that is `5b08f60fc` (`docs: reconcile manuscript
v14 counts to frozen receipts and record v15 landscape`). Do not substitute a
branch name: a branch head is not a reproducible input.

## 2. Create the environment

Python 3.12 is required. Install the hash-pinned lock file; do not resolve
versions freely.

```text
python -m venv .venv
.venv/bin/python -m pip install --upgrade pip        # Windows: .venv\Scripts\python
.venv/bin/python -m pip install -r requirements-lock.txt --require-hashes
.venv/bin/python -c "import qiskit; print(qiskit.__version__)"   # must print 2.4.1
```

**Trap 1 — the Qiskit pin is load-bearing.** The frozen E45/E46 evidence was
produced under `qiskit==2.4.1`. Qiskit 2.6.0 was released on 2026-10-16, so a
free resolve now installs a different minor version, and root-listing
reconstruction (`normalize_circuit` → `Greedy` → `state_from_circuit`) is not
guaranteed to be byte-stable across that jump. Reproduce under 2.4.1; if you
deliberately test a newer version, record it as a **divergence experiment**, not
as a reproduction.

## 3. Verify the frozen evidence chain

Run in this order and retain every stdout/stderr and every exit code.

```text
python scripts/reproduce_all.py --verify
python scripts/verify_e45_development_grid.py --output-root data/v14/e45_development_grid
python scripts/verify_e45_exact_development.py --output-root data/v14/e45_full_development
python scripts/verify_v14_idastar_escape.py --output-root data/v14/e45_idastar_escape
python scripts/verify_v14_readiness_verdict.py
python scripts/verify_v15_landscape_integration.py
python scripts/verify_e46_window_landscape.py
python scripts/verify_v15_readiness_verdict.py
python scripts/verify_certificate_qrcert_v1.py        # independent qrcert/v1 verifier
python scripts/verify_sbom.py
```

`scripts/verify_certificate_qrcert_v1.py` is the only verifier that re-derives
the published v15 quantities **without importing any producer verifier**; it
emits `CERTIFIED_CONSISTENT` on 20/20 checks. Treat it as the primary
third-party entry point.

**Trap 2 — the 80-gate baseline branch.** `experiments/e45_development_grid/run.py`
takes the certified root as `state_from_circuit(Greedy(normalize(source)))`, but
every baseline arm is skipped when the normalized circuit exceeds
`MAX_BASELINE_GATES = 80`, in which case the root is the *normalized* circuit
itself. An independent re-implementation that misses this branch disagrees with
the frozen `baseline_cost` on **49 of 128** sources. Confirmed 2026-10-17 by
bit-exact reconstruction of 128/128 roots.

**Trap 3 — the manifest that is expected to fail.** `scripts/verify_prepaper_release_manifest.py`
exits non-zero with a `byte/hash mismatch` on
`docs/review/metric_audit_ledger_2026-08-24.csv`. This is a **pre-existing,
recorded drift**, not a cold-start failure.

As of 2026-10-22 the drift is fully enumerated and attributable, so you can
*distinguish* it from tampering instead of just tolerating it:

```text
python scripts/verify_release_chain_with_dispositions.py
```

Expected output on a clean tree:

```text
[verify] 35042 manifest entries, 15 registered drifts
[verify] {'KNOWN_DRIFT_ACCEPTED': 15, 'MATCH': 35027}
[verify] verdict=PASS_WITH_ACCEPTED_DRIFT
```

If you see `DRIFT_UNREGISTERED` or `MISSING`, stop: that is a real integrity
failure, not the known one. The 15 registered entries are recorded with the
observed hash, the attributed commit and a recommended re-pin in
`docs/review/release_drift_register.json`. Background:
`docs/review/release_drift_disposition_2026-10-18.md`.

Note the original single-error report was misleading: that script aborts on the
first mismatch, so it showed 1 drift where there are 15. All 15 are edits made
after the manifest's 2026-08-31 snapshot; none is unattributed.

## 4. Run the regression suite

```text
python -m pytest -q --junitxml=cold_start_pytest_junit.xml
```

## Acceptance

A zero exit code from every verifier above, a final `status` of `verified` (or
`CERTIFIED_CONSISTENT` for `qrcert/v1`) from each JSON verifier, zero pytest
failures/errors, and a recorded machine, OS, Python, package, start time, end
time, and commit SHA. Any missing file, unexpected hash mismatch, dependency
installation failure, non-zero verifier exit, or test failure is an independent
reproduction failure and must be retained with the logs. No result is promoted by
editing a verdict JSON after a failure.

## History

The 2026-09-08 local cold-start work verified the base capsule SHA and its
historical release manifest in an isolated temporary directory, but that base
capsule did not contain `scripts/verify_v12_readiness_package.py`. The v12
capsule SHA was then verified and a 69-member sparse extraction independently
passed the v12 package verifier, including E38–E41 and 27 ledger evidence
entries. A full v12 capsule extraction reached Windows `WinError 1450`
(`系统资源不足，无法完成请求的服务。`). All of that predates v13–v15: **no
capsule ever contained the v14/v15 certified-landscape evidence**, which is why
the Git-based transport above is now the only complete route.
