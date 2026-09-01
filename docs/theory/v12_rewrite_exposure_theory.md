# v12 Rewrite-Exposure Theory (Draft)

Status: `conjecture_or_draft_until_e38`.

This document defines the claim boundary for the v12 representation-robust
rewrite exposure method. It is not a manuscript chapter and does not alter
the historical E1--E37 record.

## 1. Scope and definitions

Let a circuit listing be a finite sequence

\[
  L=(g_0,g_1,\ldots,g_{n-1})
\]

of fully bound unitary gate instances. A gate instance includes its operation
name, ordered qubit operands, parameters, and original index. Global phase is
considered equivalent. Barriers are not gates to be rewritten; they are
fences that no legal listing may cross. Measurements, reset/initialize,
classical operands, control flow, conditions, free parameters, and unknown
qubit operands are outside the certificate domain and produce
`UNAVAILABLE`.

The core rule library is `pair_v1`: self-inverse pairs and inverse `T/TDG`
and `S/SDG` pairs have weight 2; same-axis rotations have weight 2 when their
normalized sum is zero and weight 1 otherwise. The tolerance is fixed at
`1e-10`. Three-gate templates are deliberately outside this certificate.

For a selected dependence model, construct a DAG `D=(V,E)` over instruction
indices. Every edge preserves original order. `wire_order_v1` adds an edge
between consecutive uses of each qubit and therefore permits only disjoint
gate exchanges. `conservative_commutation_v1` adds an edge for every
overlapping pair not proven commuting by the existing sufficient predicate
`gates_commute`; disjoint pairs may commute, and unknown overlapping pairs are
dependencies. A barrier adds a complete before-to-barrier and
barrier-to-after fence.

A legal listing is a topological order of `D`. The supported exposure weight
of a legal listing is the sum of the `pair_v1` weights for adjacent endpoint
pairs in that listing. The question is restricted to this rule library and
this dependency DAG; it is not a claim about arbitrary equivalent circuits,
synthesis, hardware cost, or global compiler optimality.

## 2. Five draft claims

### Claim 1 — trace semantics

**Draft statement.** Every topological order of `D` can be reached from the
original listing by adjacent exchanges of pairs that are safe under the
declared dependence model. Therefore the listing has the same circuit
semantics, up to the declared global-phase convention.

**Proof sketch.** The original order is a topological order. If two adjacent
vertices in another topological order are reversed relative to the original
order, no dependency edge can connect them in that direction; otherwise the
second order would violate the DAG. The construction of `D` makes such an
overlapping pair a proven commuting pair, or makes it disjoint. The standard
adjacent-swap connectivity of finite linear extensions then transforms one
topological order into the other. Barriers remain ordered by their fence
edges.

**Attack that would refute it.** A topological order that requires swapping an
overlapping non-commuting pair, a missing barrier edge, or a dependency cycle
that was incorrectly treated as a DAG.

### Claim 2 — pair exposure

**Draft statement.** For a supported candidate `(u,v)`, there exists a legal
listing in which `u` and `v` are adjacent if and only if they are incomparable
in the dependency partial order, or they are comparable with no vertex forced
strictly between them (a cover relation).

**Proof sketch.** If a legal listing places the endpoints adjacent, no vertex
can be forced between them, so comparability can only be a cover; if neither
endpoint precedes the other, they are incomparable. Conversely, for an
incomparable pair, contract the two endpoints while preserving their chosen
relative order; for a cover pair, contract the directed cover edge. The
resulting quotient remains acyclic for one pair, so a topological order of the
quotient expands to a legal order with the endpoints adjacent.

**Attack that would refute it.** An individually exposable pair whose
endpoint contraction creates a quotient cycle, or an incomparable/cover pair
for which no topological expansion places the endpoints consecutively.

### Claim 3 — joint exposure

**Draft statement.** A set of endpoint-disjoint supported candidates can be
made simultaneously adjacent exactly when contracting each pair to a block
leaves an acyclic quotient graph.

**Proof sketch.** Any simultaneous listing induces a block order, hence cannot
induce a cycle. In the other direction, a topological order of an acyclic
quotient, expanded by each pair's original endpoint order, is a topological
order of the original DAG and makes every block adjacent.

**Attack that would refute it.** A quotient DAG whose every expansion violates
an original dependency, or a legal simultaneous listing whose contracted
quotient contains a directed cycle.

### Claim 4 — matching certificate

**Draft statement.** Every simultaneously exposed set is a matching in the
pairwise-exposable candidate graph. Its maximum-weight matching is a safe
upper bound `UB`. A quotient-checked CGL block set is a constructive lower
bound `LB`. `UB=0` is a representation-robust zero certificate, and `LB=UB`
is an exact certificate within the declared rule/dependence scope.

**Proof sketch.** One instruction cannot occupy two adjacent pairs in one
listing, yielding the matching constraint. Dropping the quotient-cycle
constraint can only enlarge the feasible set, so maximum matching upper-bounds
the joint problem. CGL materializes a feasible block set, so its measured
weight is a lower bound. Equality closes the interval; zero upper bound
excludes every supported pairwise opportunity under the model.

Candidate caps remain fail-closed: discarded candidate weights are added to a
conservative residual upper bound, so truncation can never be reported as an
exact certificate.

**Attack that would refute it.** A legal listing with weight above `UB`, a
CGL listing below its reported `LB`, or a zero-`UB` circuit with a supported
pairwise opportunity.

### Claim 5 — algorithm soundness

**Draft statement.** CGL's output is a topological order of the original
dependency DAG and its actual adjacent `pair_v1` weight is at least the
reported `LB`.

**Proof sketch.** CGL first verifies endpoint-disjointness and quotient
acyclicity, then runs a deterministic minimum-original-index topological sort
on the quotient. Expansion preserves every cross-block edge and keeps each
selected pair contiguous. The resulting listing is independently rescanned;
the selected blocks therefore realize their declared weights.

**Attack that would refute it.** A returned listing containing a dependency
edge in reverse order, a selected pair not adjacent, an equivalence failure,
or a measured exposed weight below `LB`.

## 3. Minimal counterexample-attack panel

The following panel is implemented by
`tests/test_rewrite_exposure.py` and is intended to be expanded by E38's
exhaustive oracle. The `conservative` label refers to
`conservative_commutation_v1`.

| ID | Minimal construction | Expected attack target |
|---|---|---|
| A01 | `H0,H0` | adjacent self-inverse, exact weight 2 |
| A02 | `H0,X1,H0` (conservative) | overlapping-free/incomparable exposure |
| A03 | `H0,H0` | cover exposure |
| A04 | `H0,X0,H0` | forced open-interval node blocks exposure |
| A05 | `H0,H1,H0,H1` | two disjoint pairs jointly expose |
| A06 | synthetic `0→2, 1→3`, pairs `(0,3),(1,2)` | quotient contraction cycle |
| A07 | `H0, barrier, H0` | barrier fence cannot be crossed |
| A08 | `H0, unknown0, H0` | unknown overlapping operation is dependent |
| A09 | `H0, unknown0, H1` | unknown disjoint operation may reorder |
| A10 | `X0,X0` | second self-inverse rule |
| A11 | `CX01,CX01` | two-qubit endpoint identity |
| A12 | `CZ01,CZ01` | two-qubit diagonal identity |
| A13 | `SWAP01,SWAP01` | swap identity |
| A14 | `T0,TDG0` | inverse phase-pair rule |
| A15 | `S0,SDG0` | inverse phase-pair rule |
| A16 | `RZ(0.5),RZ(-0.5)` | normalized zero rotation, weight 2 |
| A17 | `RX(0.5),RX(0.25)` | nonzero rotation merge, weight 1 |
| A18 | `RY(π),RY(π)` | zero modulo `2π`, global phase allowed |
| A19 | `CX01,CX10` | reversed operands are not a pair |
| A20 | `H0,measure0` | non-unitary fail-closed scope |
| A21 | `H0,reset0` | reset fail-closed scope |
| A22 | `RZ(θ)` | free parameter fail-closed scope |
| A23 | conditional `H0` | conditional instruction fail-closed scope |
| A24 | eight `H0` gates, cap 2 | truncation and residual UB |
| A25 | conservative overlap budget 1 | explicit wire-model fallback |
| A26 | invalid beam width 0 | invalid configuration unavailable |
| A27 | empty unitary circuit | exact-zero boundary |
| A28 | non-circuit input | unavailable input contract |

These cases are attacks on the definitions and implementation contracts, not
evidence that the claims are already theorems. E38 is the zero-tolerance
exhaustive validation gate.

## 4. Implementation correspondence

`src/optimisation/rewrite_exposure.py` implements the immutable input hash,
both dependence models, `pair_v1`, pairwise exposure, quotient contraction,
matching upper bounds, exact branch-and-bound/beam lower bounds, deterministic
CGL materialization, fail-closed scope checks, and source/listing hashes.
Existing WCL, Greedy, CeilingAware, and Phase2b paths are unchanged unless a
caller explicitly imports and invokes `CertificateGuidedPreprocessor`.
