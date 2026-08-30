# Q-research 592-item metric evidence ledger v2

Status: supersedes the legacy section-status/shared-evidence ledger.

- Registry: `docs/review/metric_evidence_registry_2026-08-26.json`
- Registry SHA-256: `2aff0cc729383a72123ee07b6e532d2c44d79dac0df0bd01589e7f58e1fc9ee2`
- Catalog SHA-256: `eb5f039ae5cfcd97e205afae9febb25f7b69bd52e57f4af4cdb8997d0393d36b`
- Item-specific PASS coverage: **175/592**.
- Status counts: `{"EXTERNAL": 4, "FAIL": 39, "NA": 29, "PARTIAL": 345, "PASS": 175}`.

A row is PASS only when item-specific satisfaction evidence is a file, its current SHA-256 matches, its selector/predicate passes, and the registry assessment predicate is true. Directories and criterion-source references cannot satisfy a metric.

The former CSV/summary contents are stale and superseded. Their section-level PASS values must not be cited as evidence of completion.
