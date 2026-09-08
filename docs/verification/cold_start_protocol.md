# Independent cold-start reproduction protocol

Status: **protocol prepared; independent execution pending**.

This procedure is for a fresh user account and a clean environment. The
executor must use the final published restore capsule and must not mix files
from the author's working tree into the extracted directory.

1. Download the published v12 restore capsule
   `release/prepaper_v12_restore_capsule.zip` and verify its SHA-256 against the
   release record before extraction:

   ```text
   e0699ce3cfe08b628f7f931813d4505016b8d3ea688ff15873a48ad03dc68ed5
   ```

2. Extract the archive into a new directory, create a fresh Python 3.12
   environment, and install the hash-pinned requirements:

   ```text
   python -m venv .venv
   python -m pip install --upgrade pip
   python -m pip install -r requirements-lock.txt --require-hashes
   ```

3. From the extracted project root, run the independent release verifier and
   the package verifiers. The v12 capsule contains both the historical
   pre-paper manifest and the v12 package verifier:

   ```text
   python scripts/verify_prepaper_release_manifest.py --manifest release/prepaper_release_manifest.json
   python scripts/verify_v12_readiness_package.py
   python scripts/verify_sbom.py
   ```

4. Run the regression suite and retain the complete console output plus the
   generated JUnit receipt:

   ```text
   python -m pytest -q --junitxml=release/cold_start_pytest_junit.xml
   ```

Expected acceptance is a zero exit code, a final `status` of `verified` from
each JSON verifier, zero pytest failures/errors/skips, and a recorded machine,
Python, package, start time, end time, and capsule SHA-256. Any missing file,
hash mismatch, dependency installation failure, non-zero verifier exit, or
test failure is an independent reproduction failure and must be retained with
the logs. No result is promoted by editing a verdict JSON after a failure.

The 2026-09-08 local cold-start work verified the base capsule SHA and its
historical release manifest in an isolated temporary directory, but that base
capsule does not contain `scripts/verify_v12_readiness_package.py`. The v12
capsule SHA was then verified and a 69-member sparse extraction independently
passed the v12 package verifier, including E38–E41 and 27 ledger evidence
entries. A full v12 capsule extraction reached Windows `WinError 1450`
(`系统资源不足，无法完成请求的服务。`), so the complete cold-start protocol
remains **protocol prepared; independent execution pending** until a fresh
machine or an equivalent resource-capable environment completes steps 1–4.
