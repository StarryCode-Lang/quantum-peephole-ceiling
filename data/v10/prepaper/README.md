# v10 pre-paper evidence packet

This tree contains post-audit confirmation evidence generated before any new
manuscript drafting. It is intentionally separate from the historical
canonical chain in `release/release_manifest.json`; the canonical manifest
generator excludes this directory.

## Contracts

- Frozen design: `experiments/prepaper_protocol.json` and
  `docs/review/prepaper_protocol_2026-08-09.md`.
- Failures, timeouts, unavailable fidelity, and invalid outputs remain in the
  intention-to-treat denominator; invalid reduction is zero, while unknown
  fidelity is never represented as zero.
- Exact equivalence is required wherever the actual width permits the frozen
  exact contract. Approved sampled evidence is explicitly labelled with its
  sampling uncertainty.
- Shared compiler inputs are immutable QASM plus a SHA-256 manifest. Cross-tool
  analysis requires identical instance keys, input hashes, and family labels.
- Files below `preflight_invalid/`, `smoke/`, and experiment-specific
  `chunks/` are provenance or interrupted-work evidence and never enter final
  estimates.

## Layout

- `e03`, `e14`, `e18`, `e23`, `e26`: corrected full reruns and metadata.
- `sota`: shared 520-input custom/Qiskit/Cirq/t|ket> benchmark.
- `heldout`: sealed model, 240 out-of-family inputs, external outcomes, and
  nested-bootstrap analysis.
- `external_baselines`: official Quasar/Quartz execution evidence plus
  documented dispositions for other strong methods.
- `analysis`: final RQ1, RQ3, and external-baseline statistical bundles
  (created only after all required raw outputs freeze).
- `figures`: source CSV plus PDF, SVG, and 600 dpi PNG outputs (created after
  final statistics).

## Completion gate

`scripts/generate_prepaper_release_manifest.py` refuses to emit a complete
manifest while a required external result, analysis audit, figure bundle, or
checkpoint is missing. This README describes the target packet; it does not by
itself assert that the gate has passed.
