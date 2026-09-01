# Pre-paper ScholarEval Gate (top-tier standard)

Status: final research-package evaluation before manuscript drafting. The
manuscript is deliberately excluded, so this gate does not assert that a paper
is written or submission-ready.

## Decision rule and result

Weights follow the ScholarEval rubric. Passing requires weighted score at least
4.0/5.0, Methodology/Data/Analysis each at least 4.0, no unresolved critical
evidence issue, an evidence path and limitation for every score, and no upward
rounding. Final weighted score: **4.33/5.00; PASS for the pre-paper research
package only**. All three hard dimensions pass.

| Dimension | Weight | Score | Exact evidence | Limitation preventing a higher score |
|---|---:|---:|---|---|
| Problem formulation & research questions | 15% | 4.5 | Frozen RQ1--RQ3, estimands, success/falsification rules and deviation log in `prepaper_protocol_2026-08-09.md`; outputs map to `analysis/rq1`, `analysis/rq3`, held-out and external gates | RQ3 combines tool validity and common-basis gate count but does not measure hardware execution quality |
| Literature review | 15% | 4.1 | Primary-source search ledger, unified references and feature matrix include Quartz, Quanto, Quarl, relaxed peephole, Q-PreSyn, cut-and-meld/OAC, GUOQ and classic non-identity/equivalence work | Search cannot prove absence; fast-moving 2025--2026 preprints may change priority before submission |
| Methodology & research design | 20% | **4.4** | Frozen manifests; 520 matched inputs; sealed 240-instance out-of-family prediction; repaired ITT and exact-fidelity contracts; official Quasar/Quartz artifacts/configs; rerun/deviation provenance | Synthetic/logical circuits dominate; only two external artifacts complete; official configs do not equalize internal compute budgets |
| Data collection & sources | 10% | **4.5** | Raw successes, errors and timeouts retained; 12,000-row E3, 2,130-row E14, 1,080-row E18, 160-row E23, 2,427-row E26, 520-per-tool SOTA and external outputs; SHA-pinned manifests and schema checks | No device-level executions; Quarl/GUOQ/OAC are not local quantitative rows for documented hardware/resource/artifact reasons |
| Analysis & interpretation | 15% | **4.4** | Family-outer/instance-inner 10,000-replicate bootstrap, cluster sign permutations, paired tests/effect sizes, Holm, LOFO, MDE/equivalence and negative-result retention; machine audits in `data/v10/prepaper/analysis` | RQ1/RQ3 mixed models did not converge; cluster counts are modest and the external two-endpoint Holm p-values are 0.05799 |
| Results & findings | 10% | 4.4 | RQ1 5.901 pp with 95% CI 2.004--10.615; sealed MCC 0.731 with 95% CI 0.425--1; exact-valid/ITT tables for six optimizers; four source-backed vector/600-dpi figures; refutations and failures reported | Held-out CI is wide; Quartz ITT CI crosses zero; no confirmatory Quasar--Quartz endpoint survives cluster-level Holm at 0.05 |
| Scholarly writing & presentation | 10% | 4.0 | Structured protocol, data dictionaries, theory gate, novelty matrix, execution dispositions, visual audit and reproducible finalization commands | This score covers the evidence package only; manuscript argument, exposition and journal formatting have not been drafted or evaluated |
| Citations & references | 5% | 4.2 | Primary DOI/arXiv/Zenodo records, search provenance and numeric reference reconciliation with zero missing/duplicate definitions at audit time | Final manuscript-level claim-to-citation placement and a fresh pre-submission literature update remain future work |

Weighted calculation (unrounded components):
`0.15*4.5 + 0.15*4.1 + 0.20*4.4 + 0.10*4.5 + 0.15*4.4 + 0.10*4.4 + 0.10*4.0 + 0.05*4.2 = 4.33`.

## Critical-issue disposition

1. Quasar and Quartz completed all 520 frozen inputs; exact fidelity was
   independently revalidated from emitted QASM.
2. RQ1, RQ3 and external cluster-aware analyses completed. Nonconvergent mixed
   models are disclosed and the preregistered nonparametric fallback is used.
3. Four figures have PDF, SVG, 600-dpi PNG and source CSV; mechanical and manual
   visual audits pass.
4. The pre-paper manifest, full tests, workspace coverage and final independent
   verifier are execution gates. Their final run identifiers and counts are
   recorded in `prepaper_final_audit_2026-08-10.md`; this score is void if any
   gate is not PASS.
5. Historical barred claims remain visibly withdrawn. The frozen manuscript is
   not an input and must not be treated as publication-ready.

## Interpretation

The package clears a high pre-paper evidence threshold because it now has
prospective tests, explicit failure semantics, independent external artifacts,
cluster-aware uncertainty and auditable negative results. Its strongest
contribution is not a universal optimization ceiling. It is a reproducible,
model-conditional account of how flat circuit listing and local-rule contracts
alter accessible reductions, with family decomposition and sealed transfer
evidence. Hardware relevance, broader external-method coverage and manuscript
quality remain open future gates.
