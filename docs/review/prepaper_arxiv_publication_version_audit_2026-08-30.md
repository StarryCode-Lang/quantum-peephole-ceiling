# arXiv-to-publication comparator version audit (2026-08-30)

Status: targeted primary-record audit before manuscript writing. This is not a
systematic review and is not manuscript prose.

## Scope and method

The audit compares the current arXiv PDF with an author-hosted copy of the
formally published paper for the two external optimizers that have completed
the repository's strongest executable comparison path: Quartz and GUOQ. PDFs
were downloaded on 2026-08-30 from the primary records below, hashed byte for
byte, and inspected for page count, section hierarchy, abstract/central claim
changes, and publication-only or extended-version-only material.

## Quartz

- arXiv record: <https://arxiv.org/abs/2204.09033>; current version v2,
  2022-05-02. The official record labels it a 28-page extended version and says
  that v2 corrects typos and updates the artifact reference.
- Formal PLDI 2022 paper: <https://www.cs.cmu.edu/~zhihaoj2/papers/quartz-pldi22.pdf>,
  DOI <https://doi.org/10.1145/3519939.3523433>; 16 pages.
- Downloaded arXiv PDF: 41,885,020 bytes, SHA-256
  `36ef1c70876322c66b598baa77a31ec94aaa568920998b8ed375f369b4a53ce3`.
- Downloaded formal PDF: 756,401 bytes, SHA-256
  `5c593b4f633ddf2831cd1356921c4232e6e32a6e7bc387c0f4ef2f4aa2e6ed11`.

The two records share the complete section hierarchy from Abstract through
Conclusion. The arXiv version adds Appendix A, “Detailed Results,” after the
formal paper's references. No reversal was found in the abstract, method
identity, gate-set scope, or central evaluation claim. Formal-paper claims and
bibliography should be cited from the DOI version; appendix-only configuration
and sensitivity details should be attributed to arXiv v2.

## GUOQ

- arXiv record: <https://arxiv.org/abs/2411.04104>; current and only version v1,
  2024-11-06; 15 pages.
- Formal ASPLOS 2025 paper: <https://qqq-wisc.github.io/files/asplos25.pdf>,
  DOI <https://doi.org/10.1145/3669940.3707240>; 17 pages.
- Downloaded arXiv PDF: 1,826,374 bytes, SHA-256
  `615d625b7d3a2983665fd8278f166f6e41072c871409df505cf7dd5daa579332`.
- Downloaded formal PDF: 1,715,466 bytes, SHA-256
  `d50483c492301af1d8613cd42a04091ceaaa914c49660ce02e2bfedbdc25a4d9`.

The scientific section hierarchy is shared from Abstract through Conclusions,
Proofs, and Benchmark Data. The formal version adds acknowledgments and a full
Artifact Appendix C (checklist, installation, basic test, workflow,
customization, and methodology). No reversal was found in the abstract,
rewrite-plus-resynthesis method identity, or central evaluation claim. The
formal artifact appendix is the controlling source for reproduction workflow;
the arXiv record has no later revision that supersedes it.

## Disposition and boundary

Metric 3.18 is **PARTIAL**. The latest arXiv and formal versions of the two
closest executable comparators were compared directly, and publication-only
versus extended-only material is now separated. The audit does not yet compare
every arXiv/formal pair in the full manuscript bibliography, so it cannot prove
corpus-wide version reconciliation.

