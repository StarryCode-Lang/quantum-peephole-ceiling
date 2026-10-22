# Release-chain drift disposition — `metric_audit_ledger_2026-08-24.csv`

**Date:** 2026-10-18
**Scope:** one pre-existing failure in the pre-paper release chain. No file under
`data/` or `release/` was modified by this disposition; it is a record, not a repair.
**Trigger:** `scripts/verify_prepaper_release_manifest.py` exits non-zero.

```text
$ python scripts/verify_prepaper_release_manifest.py --manifest release/prepaper_release_manifest.json
RuntimeError: byte/hash mismatch: docs/review/metric_audit_ledger_2026-08-24.csv
```

## 1. What the manifest recorded

| Field | Recorded value |
|---|---|
| `sha256` | `f0a0ac1c05d92305a90fa88d5f8bf33d442c71df8b51538fa482ec5ae39b956b` |
| `bytes` | 1,091,059 |
| `rows` | 592 |
| manifest `created_utc` | 2026-08-31T09:44:39Z |
| manifest `git` | `7fdc0f77582c3e93af83a295e9ad340e5b94f09f`, **`dirty: true`** |

## 2. What is on disk

| Field | Actual value |
|---|---|
| `sha256` | `46bb73faebf4b6fc26849af31888b60e573ea84dd92bf57b737923674acd83c5` |
| `bytes` | 1,104,488 |
| `rows` | 592 |
| last commit touching the file | `87019d8fc` (2026-09-08, *feat: add bounded v14 certified landscape evidence*) |

## 3. Root cause — two independent facts

**(a) The manifest pinned an uncommitted variant.** It records `dirty: true`. The
file at the manifest's own parent commit (`87019d8fc^`) is **1,091,059 bytes —
the exact recorded size — but hashes to `a7cc6fd3…`, not `f0a0ac1c…`**. So the
recorded hash never existed in Git: it belongs to a working-tree state that was
never committed. This alone makes the entry unverifiable from history.

**(b) A post-manifest reassessment wave rewrote the assessment columns.** Commit
`87019d8fc` (2026-09-08, eight days after the manifest) rewrote the ledger. A
cell-level diff against `87019d8fc^` gives:

| Quantity | Value |
|---|---|
| Rows before / after | 592 / 592 (unchanged) |
| Schema before / after | identical (20 columns) |
| Changed cells | **708** |
| Changed columns | `observed_value`, `status`, `criterion_met`, `residual`, `evidence_refs_json`, `assessment_predicate_json`, `registry_sha256` |
| Unchanged columns | `metric_id`, `section`, `item`, `metric`, **`metric_sha256`**, `target`, **`target_sha256`**, `criterion`, `scope`, `assessed_utc` |
| Status transitions | `FAIL→EXTERNAL` ×6, `PARTIAL→PASS` ×8, `PARTIAL→NA` ×2 |

## 4. Assessment

**This is a re-pin gap, not a data-integrity breach.** Three facts support that
reading:

1. **No metric definition and no target moved.** `metric_sha256`, `target` and
   `target_sha256` are unchanged in all 592 rows, so the things a reader would
   compare against a claim are stable.
2. **The ledger declares its own status column non-authoritative.**
   `legacy_status_is_authoritative` is `False` on **all 592 rows**; the column was
   added precisely to stop the legacy `status` field from being cited as a
   verdict. The 16 transitions therefore live in a column the file itself
   disclaims.
3. **The change is attributable to one named commit** with a stated purpose (the
   v14 evidence wave), not to an unattributed edit.

What is *not* acceptable is leaving the chain failing silently: a cold-start
executor following `docs/verification/cold_start_protocol.md` hits this error at
step 3 and cannot distinguish "known drift" from "tampering". The protocol now
names it explicitly (Trap 3).

## 5. Required owner action

Exactly one of the following, recorded in `release/` — **neither is performed by
this run**, because `release/` hash manifests are outside this task's write scope:

- **Option A (preferred): re-pin.** Regenerate the manifest entry from commit
  `87019d8fc` (or later), record `dirty: false`, and add a one-line
  `supersession` note naming `f0a0ac1c…` as the retired hash.
- **Option B: supersede the file.** Freeze the ledger as
  `metric_audit_ledger_2026-08-24.csv` (historical) and add
  `metric_audit_ledger_2026-09-08.csv` as the active entry, leaving the old entry
  marked `superseded` exactly as `E29-smoke` and `E26-pilot` already are.

Option B matches the project's existing data-version policy
(`data/DATA_CANONICAL.md` §"Data version policy") and is the lower-risk choice.

## 6. Second drift that this run deliberately did **not** create

The 2026-10-17 scan left an open item to merge
`docs/references/reference_additions_2026-10-17.md` ([95]–[112]) into
`docs/references/unified_references.md`. That catalogue is path-bound in **three**
manifests (`prepaper_release_manifest.json`, `prepaper_v12_capsule_inner_manifest.json`,
`prepaper_capsule_inner_manifest.json`). Merging would have added a second,
larger drift on top of the one above for a purely editorial gain. The merge was
therefore **declined**, and the discoverability problem was solved instead with
`docs/references/README.md`, which is not path-bound. Merge remains available as
a single batched re-pin whenever Option A or B above is executed.
