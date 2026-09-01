# E31 factorial contrast-expansion limitation (2026-08-24)

Status: frozen before inspection of aggregate treatment effects. This document does not modify E31 execution, outcomes, ITT rules, factor levels, budgets, or the separately frozen primary contrast.

## Limitation

The pre-run protocol froze marginal main effects averaged over the other factors and supportive two-way interactions other than the primary contrast. It did not uniquely preregister how multi-level factors would be expanded into scalar contrasts, the reference levels, the exact member list, or the Holm multiplicity family.

Accordingly, the 30 contrasts below are a post-hoc operationalization of a frozen analysis class. They are supportive, not confirmatory, and must not be described as a fully preregistered 30-contrast family.

## Frozen post-hoc operationalization

- Reference levels are `LBL`, `COMMUTATION_ONLY`, window 4, and budget 1.
- Each non-reference level is contrasted with its reference level.
- Main effects and two-way differences-in-differences are averaged with equal weight over every level of every nuisance factor and then equally over the 391 frozen input hashes.
- The separately frozen primary `WCL × COMMUTATION_PLUS_TEMPLATES` interaction is excluded.
- The remaining 30 scalar contrasts form one Holm family (`E31_POSTHOC_MARGINAL_30`).
- The generalized estimand-B primary sensitivity is outside this family because it is the same separately frozen primary contrast under a different population extrapolation; it remains non-confirmatory and model-based.

The exact member list is machine-pinned in `posthoc_contrast_expansion_gate.json`. Any change to a reference, member, weighting rule, exclusion, or family size invalidates the formal analysis packet.

