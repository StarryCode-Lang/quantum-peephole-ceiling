# E31 Listing x Phase-2b Pilot (P3)

## Scope

E31 is a supporting, non-canonical pilot for P3: whether listing model and
optimizer phase interact. It is not a replacement for the unmeasured full
factorial experiment and does not support a confirmatory interaction claim.

## Protocol

The pilot evaluates 44 smoke-scale source circuits from 15 families under three
semantics-preserving listings: the original layer-by-layer listing (LBL),
wire-consecutive listing (WCL), and one seeded random topological listing
(SHUFFLE). Each listing is passed through Phase-1 greedy cancellation,
Phase-2a commutation rewriting, and Phase-2b template matching, producing 396
rows. Listing fidelity checks use a tolerance of `1e-10`.

Paired contrasts use the same source circuit across listings. The descriptive
`phase2b_over_phase1` interaction is:

```text
(alternative listing Phase-2b - alternative listing Phase-1)
- (LBL Phase-2b - LBL Phase-1)
```

No p-values or confirmatory thresholds are applied because this is a smoke-scale
pilot with one seed per source circuit.

## Cell Means

Mean gate-count reduction, in percent:

| Listing | Phase-1 | Phase-2a | Phase-2b |
|---|---:|---:|---:|
| LBL | 6.99 | 4.36 | 18.07 |
| WCL | 12.72 | 0.47 | 17.95 |
| SHUFFLE | 8.96 | 3.76 | 18.24 |

Phase-2b minus Phase-1 mean gains are 11.07 percentage points for LBL, 5.23
points for WCL, and 9.28 points for SHUFFLE.

## Paired Contrasts

Relative to LBL, mean listing deltas are:

| Listing | Phase-1 | Phase-2a | Phase-2b |
|---|---:|---:|---:|
| WCL | +5.72 pp | -3.89 pp | -0.12 pp |
| SHUFFLE | +1.97 pp | -0.60 pp | +0.17 pp |

Descriptive phase interactions relative to LBL are:

| Listing | Phase-2a over Phase-1 | Phase-2b over Phase-1 |
|---|---:|---:|
| WCL | -9.61 pp | -5.84 pp |
| SHUFFLE | -2.57 pp | -1.79 pp |

The pilot therefore shows a larger WCL Phase-1 gain while Phase-2b means stay
near the LBL mean. This is useful for designing the full experiment, but it is
not evidence that WCL suppresses or enhances Phase-2b in the population.

## Limitations and Disposition

- Smoke-scale suite; one seed per source circuit; 44 circuits are not a powered family-level sample.
- SHUFFLE is one random topological listing, not an estimate over the listing space.
- Full WCL/SHUFFLE x Phase-2b coverage across family, qubit count, depth, and seeds remains open.
- The Phase-2b template library is restricted; this pilot cannot establish template-completeness claims.
- P3 remains **deferred research**, not fixed or confirmed.

## Reproduction

```bash
python experiments/e31_listing_phase2b_interaction.py
python analysis/e31_listing_phase2b_analysis.py
```

Outputs:

- `data/v11/e31_listing_phase2b/e31_listing_phase2b_pilot.csv`
- `data/v11/e31_listing_phase2b/e31_cell_summary.csv`
- `data/v11/e31_listing_phase2b/e31_phase_delta_summary.csv`
- `data/v11/e31_listing_phase2b/e31_contrasts.csv`
- `data/v11/e31_listing_phase2b/e31_analysis_summary.json`
