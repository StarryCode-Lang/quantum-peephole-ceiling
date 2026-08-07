# Residual Issue Disposition

**Scope:** P1-P14 from the external third-round audit report dated 2026-08-07.

**Evidence boundary:** Current source, `data/DATA_CANONICAL.md`,
`release/release_manifest.json`, and the active claim map. Historical review
snapshots are provenance, not active evidence.

## Disposition

| Item | Status | Evidence or reason |
|---|---|---|
| P1 listing-potential theory | Deferred research | E19, E19-ext, E22, and E31 sample valid listings; no exhaustive topological-listing potential theorem is claimed. |
| P2 template-completeness hierarchy | Deferred research | E26 validates the recorded Phase-2b library; parity-gadget and exhaustive Clifford-template coverage remain outside scope. |
| P3 WCL x Phase-2b interaction | Bounded pilot only | E31 provides 396 non-canonical smoke rows and paired contrasts; full family x size/depth/seed factorial remains open. |
| P4 noise-aware ceiling | Deferred research | EHW is correctly labeled noise-model simulation; no analytic noise-transfer bound or real-device result is claimed. |
| P5 CODP/QMA spectrum | Open problem retained | `docs/theory/QMA_hardness_draft.md` remains conditional; the main manuscript does not promote its proof sketches to theorems. |
| P6 predictive validation | Boundary established | Held-out RepetitionCode failure is documented; no prospective preregistered prediction is presented as completed. |
| P7 monotone mechanism feature | Closed as bounded diagnostic | `min(1, 2d)` has 0/692 violations; learned family-level generalization remains explicitly exploratory. |
| P8 Solovay-Kitaev tradeoff | Deferred research | E18 exact Clifford+T evidence remains unchanged; approximate-decomposition tradeoff requires a separate protocol and error budget. |
| P9 zero-inflated inference | Closed for current analyses | Zero mass, conditional nonzero summaries, and degenerate-effect handling are implemented and tested. |
| P10 E30 distribution validation | Closed at aggregate level | 27/27 Poisson diagnostics are testable with 0 BH rejections; wire-level independence is unidentifiable from stored aggregates. |
| P11 classical compiler dialogue | Framing added; external verification open | Active manuscript now states the bounded-window/intermediate-representation analogy using existing references; novelty coverage still needs an independent literature search. |
| P12 phase-transition language | Closed as framing correction | Active text treats density/window/template thresholds as future hypotheses, not established critical phenomena. |
| P13 E20 Cirq rerun | Closed non-canonically | Corrected pipeline produces 1,070 rows with 390/390 Cirq success in `data/v11/e20_corrected/`; frozen E20 remains as-executed evidence. |
| P14 registry drift | Closed | Active manuscript includes E11/E13; E6 remains explicitly registered-not-executed; canonical totals and paths are routed through the manifest. |

## Repository-Side Completion

- Active documentation now distinguishes canonical, rerun, derived, pilot, and
  historical evidence.
- E31 commands, outputs, limitations, and paired analysis are reproducible from
  the repository root.
- Fidelity fallback wording now matches the global-Haar implementation and does
  not promise a universal Monte Carlo error rate.
- Publication-readiness status now distinguishes repository work from external
  submission requirements.

## External Requirements

The following are intentionally not represented as solved by repository code:

- independent quantum-compilation/complexity proof review;
- independent clean-checkout replication;
- real-device hardware validation;
- final author, funding, conflict, email, and ORCID declarations;
- archival DOI creation after an actual deposit;
- a prospective preregistered held-out experiment for P6.

Treating any of these as complete without the corresponding external evidence
would weaken, rather than strengthen, the release.
