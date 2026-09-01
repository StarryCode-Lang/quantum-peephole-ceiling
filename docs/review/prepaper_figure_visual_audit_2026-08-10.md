# Pre-paper figure visual audit (2026-08-10)

Scope: manual inspection of the final 600-dpi PNG render for every publication-
gate figure after the mechanical PDF/SVG/PNG/source-data audit.

| Figure | PNG SHA-256 | Manual findings | Decision |
|---|---|---|---|
| `fig01_rq1_listing_forest` | `392a58e3f2c266edb361d0568e3a3b06057b8703ebdcf379cfe892e5a733db41` | All 16 family intervals, the family-clustered aggregate, replication, zero line, and shaded +/-1 pp equivalence margin are visible; no clipping or legend collision. | pass |
| `fig02_heldout_generator_rates` | `e8ff92ccaee78c145d511f19ebcb8f8546307bf34911e670dd0fb628d490425c` | Initial render failed because the legend obscured bars.  The final render moves the legend into the right-side whitespace; all eight generator labels, zero-height categories, MCC annotation, colors, and hatches remain legible. | pass after correction |
| `fig03_tool_summary` | `ea5d70579e603e0bd76cc78a1c3b66231c2a4339b1690be688b9fb2a1cfbbf22` | Validity and common-basis ITT panels use the same method order; uncertainty intervals, zero line, negative expansion, colors, and method-specific hatches are visible without clipping. | pass |
| `fig04_external_baselines` | `b99f4e3bf7d074fcccf7946b2d4d019f0f85349f7c9bb395a85ad392a99d83c4` | Quasar/Quartz validity and ITT panels show full family-clustered intervals, including the Quartz interval crossing zero; zero line, labels, colors, and distinct hatches are legible. | pass |

Mechanical audit SHA-256:
`47458f196ab53a0b270afe4c08035727cbe7a60f695d80265db8f36f50d26587`.

The manual gate covers clipping, overlap, visual legibility, and whether the
graphics hide null/negative evidence.  It does not replace statistical or
claim-level review.
