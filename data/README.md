# Data guide

The data tree contains several evidence roles. Directory age alone does not
determine whether a file can be deleted.

| Role | Location | Rule |
|---|---|---|
| Canonical historical data | Paths listed by `DATA_CANONICAL.md` and `release/release_manifest.json` | Immutable and hash-verified |
| Sealed extensions | Primarily v11 E31-E37 packages and independent receipts | Preserve raw rows, certificates, and manifests |
| Bounded research extensions | `v12/`, `v13/`, `v14/` | Keep versioned receipts and explicit failure states |
| Derived output | Analysis summaries and generated figures | May be regenerated from pinned inputs |
| Local runtime copies | Ignored caches, logs, and repeated v14 QASM copies | Do not publish |

`v9` and selected v11 directories contain rerun or reconciliation evidence.
They do not replace canonical data unless a release manifest explicitly says
so. The v13 and v14 packages are separate: v14 demonstrates the later resource
improvement while preserving v13 as the fixed baseline.

Before changing any evidence file, check whether it appears in a manifest or is
referenced by a receipt. A successful verifier supports only its declared
scope; it does not promote bounded data into a universal claim.
