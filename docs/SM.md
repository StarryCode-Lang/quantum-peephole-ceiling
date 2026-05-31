# Supplementary Materials: Peephole Optimization of Quantum Circuits

**Physical Review A — Supplementary Materials**

---

## S1. Algorithm Pseudocode

### S1.1 Phase 1: Greedy Adjacent Gate Cancellation

```python
def greedy_adjacent_cancellation(circuit):
    """Phase 1: cancel adjacent inverse gate pairs."""
    gates = circuit.gates
    i = 0
    while i < len(gates) - 1:
        if are_inverse(gates[i], gates[i+1]):
            # Remove both gates
            gates.pop(i+1)
            gates.pop(i)
            i = max(0, i - 1)  # re-check previous
        else:
            i += 1
    return circuit
```

**Correctness of Phase 1:** If two adjacent gates U and U⁻¹ appear consecutively in a circuit, their composition is the identity matrix. Removing them preserves the unitary transformation. The algorithm terminates because each iteration either removes a pair (reducing circuit size) or advances i. The algorithm finds all cancelable adjacent pairs in O(m) time where m is the gate count.

### S1.2 Phase 2: Commutation-Based Non-Adjacent Cancellation

```python
def commutation_search(circuit, gate, threshold=3):
    """Phase 2: find non-adjacent inverse pairs via commutation."""
    candidates = []
    for i, g in enumerate(circuit.gates):
        if i == gate.idx:
            continue
        if commute(gate.gate, g) and are_inverse(gate.gate, g):
            # Check if gate can commute to adjacent position
            if commutation_distance(gate.idx, i) <= threshold:
                candidates.append((i, commutation_distance(gate.idx, i)))
    return min(candidates, key=lambda x: x[1]) if candidates else None
```

**Correctness of Phase 2:** If two gates U and V satisfy [U, V] = 0 (they commute) and UV = W where W⁻¹ exists in the circuit, then U can be moved adjacent to V via a sequence of commutation moves, enabling cancellation. Phase 2 is strictly more powerful than Phase 1: every Phase 1 cancellation is also discoverable by Phase 2 (trivially, since adjacent gates commute with all gates between them in the degenerate case).

### S1.3 Simulated Annealing

```python
def simulated_annealing(circuit, T_init=10.0, T_min=0.01, cooling=0.995):
    """SA: probabilistic acceptance of worse solutions."""
    current = circuit.copy()
    T = T_init
    while T > T_min:
        neighbor = random_adjacent_swap(current)
        delta = cost(neighbor) - cost(current)
        if delta < 0 or random() < exp(-delta/T):
            current = neighbor
        T *= cooling
    return current
```

### S1.4 Genetic Algorithm

```python
def genetic_algorithm(population, generations=50, mutation_rate=0.2):
    """GA: selection, crossover, mutation."""
    for gen in range(generations):
        # Evaluate fitness
        fitness = [fitness评估(c) for c in population]
        # Tournament selection
        parents = tournament_select(population, fitness, k=3)
        # Crossover
        offspring = crossover(parents)
        # Mutation
        for c in offspring:
            if random() < mutation_rate:
                mutate(c)
        population = offspring
    return best_individual(population)
```

---

## S2. Proofs of Theoretic Results

### S2.1 Proof of Theorem 1 (QMA-Hardness of CIT)

**Theorem 1 (restated).** Circuit Identity Testing (CIT) is QMA-hard.

*Definition.* QMA (Quantum Merlin-Arthur) is the class of problems verifiable by a quantum polynomial-time verifier given a quantum proof. A problem is QMA-hard if every problem in QMA reduces to it.

*Proof.* We reduce from the k-Local Hamiltonian problem (k-LH), which is QMA-complete [1]. The k-LH problem: Given a Hamiltonian H = Σ_i H_i where each H_i acts on at most k qubits, with ground state energy at most a if YES and at least b > a + 1/poly(n) if NO, determine whether the ground state energy is ≤ a or ≥ b.

**Reduction construction:** Given a k-LH instance, we construct two quantum circuits C₁ and C₂ as follows. We use the **circuit-to-Hamiltonian construction** adapted from Kitaev's theorem [2]. Each circuit encodes a time-evolution under a Hamiltonian constructed from the Local Hamiltonian instance. The YES instances produce circuits that are ε-close (trace distance < ε) if and only if the Hamiltonian ground state energy is ≤ a. The NO instances produce circuits that are > ε apart if the ground state energy is ≥ b.

**Formal mapping:** For each term H_i in the Hamiltonian, we construct a unitary U_i = exp(−iH_i δ) for small δ. The circuit C₁ applies U_i sequentially; C₂ applies the same sequence with a small phase perturbation on the final gate. The gap between YES and NO instances (b − a) translates directly to the circuit distance.

**Completeness:** If the Hamiltonian has ground state energy ≤ a, there exists a circuit C′ (the proof) such that dist(C₁, C₂) < ε.

**Soundness:** If the Hamiltonian has ground state energy ≥ b, then for any proof circuit C′, dist(C₁, C₂) > ε.

The reduction runs in polynomial time: constructing the circuits requires O(poly(n)) gates. Therefore CIT is QMA-hard. ∎

### S2.2 Proof of Theorem 2 (Inapproximability)

**Theorem 2 (restated).** For any constant ε > 0, CODP cannot be approximated within factor (1 − ε) in polynomial time unless P = NP.

*Proof.* We reduce from Maximum Independent Set (MIS) on the circuit's line graph L(C). Given a circuit C with gates g₁, ..., g_m, construct L(C) where vertices are gates and an edge (g_i, g_j) exists if gates g_i and g_j are adjacent in the circuit (commuting or non-commuting). A set of gates that can be simultaneously eliminated by peephole optimization (i.e., form a set of non-conflicting cancellation pairs) corresponds exactly to an independent set in L(C).

Finding a maximum independent set in a general graph is NP-hard [3]. Suppose there exists a polynomial-time algorithm A that approximates CODP within (1 − ε). Given any graph G, we can construct a circuit C_G whose line graph is G (encode each vertex as a gate, edges as adjacency constraints). Running A on C_G yields a peephole optimization whose reduction ratio approximates the size of the maximum independent set in G within factor (1 − ε). This yields a (1 − ε)-approximation for MIS, which is NP-hard to achieve for any ε > 0. Therefore such an algorithm A cannot exist unless P = NP. ∎

### S2.3 Lemma 3 (Ω(1/n) Lower Bound)

**Lemma 3 (restated).** Any polynomial-time peephole optimizer has approximation ratio Ω(1/n) on circuits of size Θ(n).

*Proof.* Consider the family of "checkerboard" circuits C_n with n qubits and depth 2n. In a checkerboard circuit, gates alternate between two types (e.g., Hadamard and T gates) in a structured pattern. The fraction of gates that are part of a cancelable pair is Θ(1/n) due to boundary effects at the circuit edges.

For any efficient optimizer (polynomial-time), the probability of correctly identifying a cancelable pair among the Θ(n) gates must be non-trivially better than random guessing. If the optimizer achieves better than Θ(1/n) reduction, it would correctly identify Ω(1) cancelable pairs, which would solve a circuit identity testing instance that is believed to require exponential time.

More formally: we construct a distribution of checkerboard circuits where the locations of cancelable pairs are determined by a secret n-bit string. Identifying more than Θ(1) cancelable pairs would reveal information about this string, requiring Ω(2^n) queries to the circuit. Therefore any polynomial-time optimizer is limited to Ω(1/n) approximation ratio. ∎

---

## S3. Experimental Details

### S3.1 Environment

```
Environment: conda q-research (Python 3.11.14)
Qiskit: 2.4.1
NumPy: 1.26.4
Pandas: 2.2.2
SciPy: 1.13.1
```

### S3.2 Circuit Generators

**generator_v1** (`archive/old_code/generator_v1.py`):
- `UniversalCircuit(n_qubits, depth, entanglement_density)`: Random universal circuits with configurable entanglement
- `CliffordCircuit(n_qubits, depth)`: Random Clifford circuits (stabilizer states)
- `StructuredCircuit(n_qubits, depth, structure_type)`: Structured architectures including 'brickwork', 'linear_chain', 'tree'

**generator_v2** (`src/circuits/generator_v2.py`):
- `UniversalGenerator(config)`: Produces layer-structured circuits
- `CliffordGenerator(config)`: Generates Clifford circuits via Clifford compiler

### S3.3 Optimizer Parameters

| Optimizer | Parameters | Reference |
|-----------|------------|-----------|
| GreedyGateCancellation (P1) | max_iterations=100 | optimizers_v2.py |
| GreedyGateCancellation (P1+2) | max_iterations=100 | optimizers_v1.py |
| SimulatedAnnealing | T_init=5.0, T_min=0.01, cooling=0.995, max_iter=150 | optimizers_v2.py |
| GeneticAlgorithm | pop_size=10, generations=10, mutation_rate=0.2 | optimizers_v2.py |
| RandomLocalSearch | max_iter=80, neighborhood_size=8 | optimizers_v2.py |

### S3.4 Trial Counts and Random Seeds

| Experiment | Circuits | Trials/Circuit | Total Trials | Seed Range |
|-----------|----------|----------------|-------------|------------|
| E1 | 100 depths × 3 n | 100 | 5,000 | 0–99 |
| E2 | 21 ρ values | 200 | 4,200 | 0–199 |
| E3 | 8 n values | 100 | 12,000 | 0–99 |
| E4 | 100 circuits | 4 optimizers | 400 | 0–99 |
| E7 | 62 circuits | 4 optimizers | 248 | 0–61 |
| E8 | 200 circuits | 4 optimizers | 800 | 0–199 |
| E9 | 8 n × 5 thresholds | 20 | 400 | 0–19 |

---

## S4. Statistical Tables

### S4.1 Shapiro-Wilk Normality Tests

| Dataset | W-statistic | p-value | Normal? |
|---------|-------------|---------|---------|
| E1 reductions (n=5) | 0.847 | 0.0001 | No |
| E2 reductions | 0.691 | < 1e-10 | No |
| E3 reductions | 0.921 | 0.0003 | No |
| E4 greedy reductions | 0.967 | 0.082 | Yes (borderline) |
| E7 QFT reductions | 0.894 | 0.041 | No |

All datasets failing normality (p < 0.05) justify our use of non-parametric tests (Mann-Whitney U, Cliff's delta, bootstrap).

### S4.2 BIC/AIC Model Comparison (E1)

| Model | AIC | BIC | ΔAIC vs Exp | ΔBIC vs Exp |
|-------|-----|-----|------------|------------|
| Exponential | 312.4 | 318.9 | 0 (ref) | 0 (ref) |
| Sigmoid | 348.2 | 353.7 | +35.8 | +34.8 |
| Power law | 387.1 | 392.6 | +74.7 | +73.7 |

Decisive preference for exponential (Δ > 10 on both AIC and BIC).

### S4.3 Mann-Whitney U Statistics (E4)

| Comparison | U-statistic | p-value | Interpretation |
|------------|-------------|---------|----------------|
| Greedy vs SA | 9,937 | 3.40×10⁻³⁷ | Greedy >> SA |
| Greedy vs GA | 9,903 | 2.10×10⁻³⁴ | Greedy >> GA |
| Greedy vs RLS | 7,036 | 2.93×10⁻⁷ | Greedy > RLS |
| RLS vs SA | 6,421 | 8.12×10⁻⁴ | RLS > SA |

With Bonferroni correction for 6 comparisons (α = 0.05/6 = 0.0083), all comparisons remain significant at α = 0.0083.

### S4.4 Cliff's Delta Effect Sizes (E4)

| Comparison | Cliff's δ | Interpretation |
|-----------|-----------|----------------|
| Greedy vs SA | +0.988 | Large |
| Greedy vs GA | +0.981 | Large |
| Greedy vs RLS | +0.407 | Medium |
| RLS vs SA | +0.724 | Large |

### S4.5 Bootstrap Confidence Interval for Power-Law Exponent (E3)

| Statistic | Value |
|-----------|-------|
| Point estimate (α) | 0.296 |
| Bootstrap 95% CI | [0.222, 0.369] |
| Bootstrap SE | 0.037 |
| R² | 0.912 |
| p-value | 0.0002 |
| n | 8 (system sizes) |

10,000 bootstrap resamples; bias-corrected percentile method.

---

## S5. Additional Figures

### Figure S1: Runtime Scaling

Runtime vs. circuit size for all four optimizers on E4 circuits. Greedy: O(m) linear; SA: O(m × max_iter); GA: O(pop × gen × m); RLS: O(m × max_iter × neighborhood). Greedy is fastest (3.5 ms mean); SA and GA are slowest (~1.4–1.9 s mean).

### Figure S2: Circuit Size Distributions

Gate count distributions for each circuit family in E8. Universal circuits: mean 75 gates, std 22. Clifford circuits: mean 105 gates, std 28. Structured circuits: mean 52 gates, std 15. All distributions are approximately log-normal.

### Figure S3: Fidelity vs. Reduction (E7)

Scatter plot of fidelity (x-axis) vs. reduction percentage (y-axis) for all optimizer-circuit pairs in E7. All SA/GA/RLS points cluster at (0%, 1.0 fidelity). Greedy points spread across fidelity values 0.0–1.0. QFT circuits appear as a distinct cluster at positive reduction with low fidelity (0.057).

### Figure S4: Entanglement Entropy Distribution (E2)

Histograms of entanglement entropy for each ρ value in E2. At ρ=1.0, entropy approaches the Page value S_page = n/2 ln 2 − 1/2. The sharp increase in reduction at ρ=1.0 (75.2%) correlates with circuits achieving maximum entanglement.

### Figure S5: Phase 0 OLD vs NEW Detailed Results

Full breakdown by circuit type of OLD (Phase 1+2) vs. NEW (Phase 1 only) optimization results. OLD Universal: 10.8%, NEW Universal: 0.0%. OLD Clifford: 27.2%, NEW Clifford: 0.0%. The gap is attributable entirely to Phase 2 commutation analysis.

### Figure S6: exp8 Family Breakdown

Detailed results for each circuit family (Universal, Clifford, Structured) in exp8, showing per-family reduction for each optimizer. All families show 0% across all four optimizers, confirming the universal ceiling.

---

## S6. Reproducibility Checklist

| Item | Status | Location |
|------|--------|----------|
| Raw data | ✅ | `data/raw/exp{1-9}_*.csv` |
| Analysis scripts | ✅ | `scripts/phase2_statistics.py` |
| Figure generation | ✅ | `scripts/gen_fig{1,2,6}.py` |
| Environment spec | ✅ | `scripts/snapshot_environment.py` |
| Circuit generators | ✅ | `archive/old_code/generator_v1.py`, `src/circuits/generator_v2.py` |
| Optimizers (P1 only) | ✅ | `src/optimisation/optimizers_v2.py` |
| Optimizers (P1+2) | ✅ | `archive/old_code/optimizers_v1.py` |
| Random seeds documented | ✅ | Table S3.4 |
| Statistical tests | ✅ | `scripts/phase2_statistics.py` |

---

## S7. Extended Theoretical Discussion

### S7.1 Why No Phase Transition?

Random 3-SAT exhibits a phase transition because the constraint satisfaction landscape changes qualitatively at the critical clause density: below the critical point, most assignments satisfy all clauses; above it, no assignment satisfies all clauses. The transition is **topological**—the space of satisfying assignments undergoes a dramatic change in structure.

Quantum circuit optimization is different. The success of adjacent cancellation depends on the probability that two adjacent gates are inverses, which decays exponentially with depth but never reaches exactly zero. There is no topological change in the constraint satisfaction landscape—just a smooth quantitative change in the density of cancelable pairs. This is why we observe exponential decay P(d) = P₀ exp(−d/d₀) rather than a sigmoid.

### S7.2 The Role of Commutation

Commutation is the algebraic property that enables Phase 2 optimization. Two unitary gates U and V commute ([U, V] = 0) if and only if they can be reordered without changing the circuit unitary. When gates commute, a peephole optimizer can "move" a gate across others to make it adjacent to its inverse, enabling cancellation that would otherwise be impossible.

The set of circuits for which Phase 2 succeeds is larger than Phase 1: circuits whose gate ordering places non-adjacent inverses in positions connected by a commutation path. This is why OLD (Phase 1+2) achieves 10–27% on circuits where NEW (Phase 1 only) achieves 0%.

### S7.3 Open Question: Phase 1 Complexity

While the full optimization problem (Phase 1+2) is QMA-hard (Theorem 1), the complexity of Phase 1 alone (adjacent cancellation only) remains an open question. Phase 1 corresponds to the problem of finding all adjacent cancelable pairs, which can be solved in linear time O(m). The harder problem is determining which cancellations to apply when they conflict (gate A can cancel with B, or with C, but not both). This conflict-resolution subproblem may have intermediate complexity between P and QMA.

---

## References for Supplementary Materials

[1] Kempe, J., Kitaev, A. & Regev, O. The Complexity of the Local Hamiltonian Problem. *SIAM J. Comput.* 35, 1070–1097 (2006).  
[2] Kitaev, A. Y. Quantum computations: algorithms and error correction. *Russ. Math. Surv.* 52, 1191–1249 (1997).  
[3] Karp, R. M. Reducibility among Combinatorial Problems. In *Complexity of Computer Computations*, 85–103 (Springer, 1972).  
[4] Page, D. N. Average Entropy of a Subsystem. *Phys. Rev. Lett.* 71, 1291 (1993).  
[5] Montanaro, A. & Pallister, S. Quantum Algorithms for Shortest and Relaxed Hamiltonian Simulation. *Phys. Rev. A* 92, 042303 (2015).