# Listing Models, DAG Compilers, and the Scope of the Structural-Ceiling Framework

> **Document Status**: Scope clarification (addresses the LBL/WCL vs DAG gap identified in the independent audit).
> **Version**: 1.0
> **Date**: 2026-06-17
> **Dependencies**: `framework.md` (D1–D10, Listing Model Dependency), `lemmas.md` (Thm 1), `conjectures.md` (C1).

---

## Purpose

This document addresses a structural concern raised in the independent audit: production quantum compilers (Qiskit, Cirq, t|ket>) represent circuits as **directed acyclic graphs (DAGs)**, not as sequential gate listings. The structural-ceiling framework (Theorem 1, Conjecture C1) is formulated in terms of **listing models** (LBL / WCL). This raises two questions:

1. Does the listing-based framework apply to DAG-based compilers?
2. Is the "structural ceiling" an artifact of the listing representation, or a genuine property of the circuits?

This document clarifies the scope of the framework, explains the relationship between listing-based and DAG-based representations, and honestly states what the framework can and cannot claim.

---

## 1. Three Circuit Representations

Quantum circuits can be represented in (at least) three data structures, each affecting what "adjacency" means and therefore what a peephole optimizer can see:

### 1.1 Layer-by-Layer Listing (LBL)

- **Structure**: The circuit is a flat sequence $C = (g_1, \ldots, g_m)$ where gates are ordered layer by layer. Within each layer, gates on different qubits are listed in qubit-index order.
- **Adjacency**: Two gates are "listing-adjacent" if their indices differ by 1. Under LBL with $n \ge 2$ qubits, two gates on the *same* qubit are never listing-adjacent (they are separated by $n-1$ gates from other qubits).
- **Used by**: This project's `UniversalGenerator` (`src/circuits/generator_v2.py`).
- **Theorem 1(b) consequence**: $\mathcal{S}_1(C) = \emptyset$ structurally — Phase-1 action space is empty by construction.

### 1.2 Wire-Consecutive Listing (WCL)

- **Structure**: The circuit is a flat sequence where gates on the same qubit wire are listed consecutively.
- **Adjacency**: Two successive gates on the same qubit are listing-adjacent.
- **Used by**: Some synthesis tools; circuit diagrams (when read wire-by-wire).
- **Theorem 1(a) consequence**: $\mathcal{S}_1(C)$ is non-empty in expectation, with density $\approx p_{\text{cancel}}(n, \rho)$.

### 1.3 Directed Acyclic Graph (DAG)

- **Structure**: The circuit is a DAG $G = (V, E)$ where vertices are gates and edges encode data dependencies (a gate $g_j$ depends on $g_i$ if they share a qubit and $g_i$ precedes $g_j$ on that qubit).
- **Adjacency**: Two gates are "DAG-adjacent" if they share a qubit and no other gate on that qubit lies between them in the dependency order. This is **wire-level adjacency**, independent of any flat listing.
- **Used by**: Production compilers — Qiskit (`DAGCircuit`), Cirq, t|ket> (`Circuit` with command ordering).
- **Consequence**: A DAG-based peephole optimizer sees wire-level adjacency directly. It does not suffer from the LBL "blindness" where same-qubit gates are hidden behind cross-qubit gates in the listing.

---

## 2. The Listing–DAG Gap

**The core observation.** Theorem 1(b) proves that under LBL, $\mathcal{S}_1(C) = \emptyset$ for $n \ge 2$. This is a property of the *listing*, not of the *circuit*. The same circuit, represented as a DAG (or as WCL), would expose wire-level inverse pairs to a peephole optimizer.

**Implication for the structural ceiling.** The "structural ceiling" ($R_1 \approx 0\%$ on random circuits) observed in experiments E1–E5 is therefore **listing-conditional**:

$$
R_1^{\text{LBL}}(C) = 0 \quad \text{(Theorem 1(b), structural)} \\
R_1^{\text{WCL}}(C) \approx 2 p_{\text{cancel}}(n, \rho) \quad \text{(Theorem 1(a), small but non-zero)} \\
R_1^{\text{DAG}}(C) \approx R_1^{\text{WCL}}(C) \quad \text{(DAG sees wire-level adjacency, like WCL)}
$$

The empirical ~0% Phase-1 reduction in E1–E5 is explained by Theorem 1(b) (the LBL listing structurally empties the action space), **not** by any intrinsic incompressibility of the circuits. Under WCL or DAG representation, the same circuits would exhibit a small but non-zero Phase-1 reduction (~18% in our WCL experiment, consistent with Theorem 1(a)).

**This is not a flaw in the framework — it is a feature.** The framework's value is in *characterizing* how the listing model affects peephole optimization. The LBL→WCL gap (~18% vs 0%) is itself a measurable, theoretically-grounded result about the sensitivity of peephole optimization to circuit representation.

---

## 3. Relationship to Production DAG Compilers

Production compilers (Qiskit `transpile`, Cirq, t|ket>) use DAG representations and implement sophisticated optimization passes that go far beyond Phase-1 adjacent-cancellation. This raises the question: does the structural-ceiling framework say anything about production compilers?

### 3.1 What the framework DOES claim

1. **Listing-model sensitivity.** The framework proves that the choice of listing model (LBL vs WCL vs DAG) materially affects Phase-1 peephole performance. This is a genuine finding: a naive peephole optimizer on an LBL listing is structurally blind to same-qubit inverse pairs.

2. **Phase-2 commutation value.** Phase-2 commutation rewriting (which operates on wire-level structure, not listing order) is listing-independent. The framework's Phase-2 results (Theorem 7, Theorem 9) hold regardless of the listing model, because commutation is a wire-level algebraic property.

3. **Ceiling is representation-dependent, not algorithm-dependent.** Within a fixed listing model, all Phase-1 optimizers (greedy, SA, GA, RLS) converge to the same ceiling (Theorem 2). The ceiling is a property of the representation + circuit structure, not of the search algorithm.

### 3.2 What the framework does NOT claim

1. **Not a lower bound on DAG-compiler performance.** The framework does *not* claim that production DAG-based compilers are bounded by the LBL ceiling. A DAG-based compiler that performs wire-level cancellation directly would bypass Theorem 1(b) entirely. The empirical result that Qiskit O3 achieves ~23% reduction on real circuits (E12) — far above our prototype's ~11% — is consistent with this: Qiskit operates on a DAG and employs passes (commutation analysis, template matching, resynthesis) that go beyond Phase-1 listing-adjacent cancellation.

2. **Not a complexity-theoretic lower bound.** The structural ceiling is a limit on a specific class of *classical algorithms* (listing-based peephole rewriters) applied to a specific *data structure* (gate listings). It is not a lower bound on quantum circuit complexity (which concerns the minimum number of gates to represent a unitary, regardless of algorithm or representation).

3. **Not a claim about all peephole optimizers.** The framework's Phase-1 ceiling applies to optimizers that scan a listing and cancel listing-adjacent inverses. A DAG-based peephole optimizer that scans wire-adjacent gates is effectively operating in the WCL regime and is subject to Theorem 1(a), not Theorem 1(b).

### 3.3 Honest scope statement

The structural-ceiling framework should be read as: **"For listing-based peephole optimizers operating on LBL representations, Phase-1 reduction is structurally zero; the gap to WCL/DAG representations is ~18%, explainable by Theorem 1(a). Production DAG compilers operate in a different regime and are not bounded by this ceiling."**

This is a narrower, more honest claim than "quantum circuits cannot be optimized by peephole methods." The narrower claim is defensible and useful; the broader claim is not supported.

---

## 4. Qiskit Pass Isolation: Honest Status

The independent audit flagged that the Qiskit pass-isolation analysis (identifying which Qiskit transpiler pass is responsible for reduction on each circuit family) covers only **5 of 15** circuit families. For the remaining 10 families, the mechanism attribution is speculative.

### 4.1 Current coverage

| Family | Pass isolation performed? | Mechanism confidence |
|--------|--------------------------|---------------------|
| (5 families) | Yes — pass-level breakdown available | High |
| (10 families) | No — only aggregate O3 reduction reported | **Speculative** |

### 4.2 Honest remediation

Rather than presenting speculative mechanism attributions as findings, the manuscript should:

1. **Report only the 5 isolated families as mechanism findings.**
2. **For the 10 non-isolated families, report only the aggregate reduction** and explicitly state: "Mechanism attribution for these families is not established; we report the aggregate Qiskit O3 reduction without claiming which specific pass is responsible."
3. **Move full pass-isolation of all 15 families to Future Work.**

This is a scope reduction, but it converts speculative claims into honest ones. A reviewer who asks "how do you know pass X caused the reduction on family Y?" for a non-isolated family would otherwise have no answer.

---

## 5. Recommendations for the Manuscript

Based on this analysis, the manuscript should:

1. **Add a "Scope and Representation" subsection** in the Methodology chapter, explicitly stating that the structural ceiling is listing-conditional (LBL) and that DAG-based compilers operate in a different regime.

2. **Reframe the central claim** from "Phase-1 peephole optimization achieves ~0% on random circuits" to "Phase-1 peephole optimization on LBL representations achieves ~0% on random circuits; under WCL/DAG representations, ~18% is achievable, consistent with Theorem 1(a)."

3. **Include a DAG comparison discussion** noting that production compilers (Qiskit O3 ~23%) exceed the prototype's Phase-1+2 (~11%) because they operate on DAGs and employ passes beyond the prototype's scope. This is not a failure of the framework — it is a difference in representation and pass sophistication.

4. **Reduce the Qiskit pass-isolation claims** to the 5 families with actual data, and move the rest to Future Work.

5. **Explicitly list as a limitation** that the framework's theoretical results (Theorems 1–9) are formulated for listing-based representations, and extending them to DAG-based representations is an open direction.

---

## 6. Summary

| Question | Answer |
|----------|--------|
| Is the structural ceiling listing-conditional? | **Yes.** Theorem 1(b) is an LBL property; WCL/DAG expose ~18% reduction. |
| Does the framework bound DAG-compiler performance? | **No.** DAG compilers bypass Theorem 1(b). The framework does not claim to bound them. |
| Is the LBL→WCL gap a real finding? | **Yes.** It quantifies representation sensitivity of peephole optimization. |
| Is the Qiskit pass-isolation complete? | **No.** Only 5/15 families isolated; the rest must be downgraded to Future Work. |
| Should the central claim be reframed? | **Yes.** From "0% on random circuits" to "0% under LBL; ~18% under WCL/DAG." |

---

*Document version: 1.0*
*Last updated: 2026-06-17*
*Author: Q-research Theoretical Framework Team*
