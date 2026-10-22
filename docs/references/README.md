# References — reading order and authority

Three files live here. They are **not** interchangeable, and one of them is
deliberately not merged into another.

| File | Authority | Status |
|---|---|---|
| `unified_references.md` | **Bibliographic authority for the catalogue.** 94 entries, v2.2 (2026-08-06). | **Path-bound** in `release/prepaper_release_manifest.json`, `release/prepaper_v12_capsule_inner_manifest.json`, `release/prepaper_capsule_inner_manifest.json`. Do not edit in place without a planned re-pin. |
| `reference_additions_2026-10-17.md` | **Additive companion**: entries [95]–[112] plus a 6-item defect register against the catalogue. | Not path-bound. Verified against the arXiv API on the dates recorded in each row. |
| `literature_review.md` | Narrative companion. **Not authoritative for citation count.** | Historical. |
| `search_ledger.md` | Log of the literature searches performed, with queries and dates. | Historical record. |

**The manuscript's own reference numbering governs citations in the paper.**
Where the manuscript and this catalogue disagree on numbering, the manuscript
wins; where they disagree on bibliographic detail, this catalogue wins.

## Why the addendum is not merged

`unified_references.md` is hash-pinned in three release manifests. Merging [95]–[112]
into it would break three hashes for an editorial gain, and the release chain is
already carrying one recorded drift
(`docs/review/release_drift_disposition_2026-10-18.md`). The merge is deferred to
a single batched re-pin; until then, **cite from both files** and check the
addendum first for anything published after 2026-08-06.

## Known catalogue defects

The six-item register in `reference_additions_2026-10-17.md` §B lists the
inconsistencies found in the catalogue (stale URLs, numbering collisions,
duplicate entries). None of them is a citation-integrity failure; all are
recorded there rather than fixed here, for the same re-pin reason.
