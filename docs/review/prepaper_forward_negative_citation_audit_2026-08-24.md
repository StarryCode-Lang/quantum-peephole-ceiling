# Forward and negative citation audit (2026-08-24)

Status: targeted primary-source citation chase for the closest optimizer
comparators. This is supporting review evidence, not manuscript prose and not a
systematic-review completeness claim.

## Scope and method

The audit started from Quartz because it is an older, central direct comparator
for automatic rule discovery and search-based circuit optimization. Searches used
the exact title and DOI/arXiv identifiers, then retained only later papers whose
official manuscript could be opened and whose body made a substantive comparison.
Q-PreSyn is too recent for absence of citing papers to be informative. Citation
counts and search-engine snippets were not treated as substantive evidence.

## Verified forward and negative evidence

| Later work | Primary record inspected | Substantive use or criticism | Consequence for Q-research |
|---|---|---|---|
| Xu et al., *Optimizing Quantum Circuits, Fast and Slow* (GUOQ), ASPLOS 2025 | arXiv:2411.04104; DOI 10.1145/3669940.3707240; author-hosted paper | Treats Quartz as a beam-search rewrite-rule superoptimizer and runs it in a 247-benchmark comparison. The protocol reports best partial solutions for timeout-capable tools and shows GUOQ better/match/worse counts rather than relying on Quartz's original claims. | This is an independent downstream execution/comparison, not merely a citation. It reinforces the need for common inputs, explicit resource caps, failure accounting, and no generic superiority claim. |
| Arora et al., *Local Optimization of Quantum Circuits* (OAC/cut-and-meld), QCE 2025 | arXiv:2502.19526; DOI 10.1109/QCE65121.2025.00069; official author paper | Compares against Quartz, Queso, and VOQC after a common Quartz preprocessing step. With a 12-hour cutoff on circuits from thousands to millions of gates, Quartz and Queso consume the full allowance in every reported circuit; the paper attributes this to the large search space and contrasts it with OAC's local-optimality guarantee. | This is direct negative scalability evidence against treating search-based local optimization as budget-insensitive or quality-guaranteed. It also preempts broad local-optimality novelty. |
| Ghlib et al., *Scalable multi-objective genetic algorithm for quantum circuit optimization*, Scientific Reports 2026 | DOI 10.1038/s41598-026-47674-5 | Cites Quartz and Queso as exhaustive-rule search methods with exponential search cost and no large-circuit quality guarantee, then motivates block/window fidelity surrogates and a Pareto formulation. | This is a later negative/limiting citation and a direct collision with generic windowing, scalability, and multi-objective novelty. Its approximate fidelity contract remains different from Q-research's exact bounded contract. |

## Earlier-source check carried through the later papers

The inspected papers connect Quartz-style search to verified/manual rewriting,
Queso, VOQC, BQSKit/unitary synthesis, and earlier large-circuit optimization.
OAC additionally distinguishes rule synthesis from its cut-and-meld/local-optimum
construction. This confirms that the relevant lineage is not a single naming
tradition. The full reference lists of every paper in the 47-item manuscript
corpus have not been recursively chased.

## Disposition

- Metric 3.19 (later citing work): direct forward-citation evidence now exists,
  but a complete citation graph for every comparator remains unfinished.
- Metric 3.21 (negative citations and reproductions): direct negative scaling
  evidence and independent tool comparisons are included. There cannot yet be an
  independent reproduction of Q-research itself because the work is not released
  as a paper; this metric therefore remains partial.
- Metric 3.13 (the identical counterexample): the search confirms broader
  representation-dependence and scalability collisions, not an identical minimal
  counterexample. It remains fail-closed.

## Primary records

- https://arxiv.org/abs/2204.09033
- https://arxiv.org/abs/2411.04104
- https://doi.org/10.1145/3669940.3707240
- https://arxiv.org/abs/2502.19526
- https://doi.org/10.1109/QCE65121.2025.00069
- https://cs.nyu.edu/~shw8119/25/qce25-oac.pdf
- https://doi.org/10.1038/s41598-026-47674-5

