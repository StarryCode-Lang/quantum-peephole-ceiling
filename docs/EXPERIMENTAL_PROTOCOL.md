# Experimental Protocol: Phase Transitions in Quantum Circuit Optimization

## 1. Research Question (Refined)

**Primary Question:** Does the difficulty of optimizing random quantum circuits exhibit a phase transition as a function of circuit depth, and can this transition be characterized by entanglement entropy?

**Formal Hypotheses:**
- **H1 (Phase Transition):** There exists a critical depth $d_c(n)$ such that the optimization success rate $S(n, d)$ drops sharply from $S \approx 1$ to $S \approx 0$.
- **H2 (Scaling):** The critical depth follows $d_c(n) \propto n^\alpha$ with $\alpha > 0$.
- **H3 (Order Parameter):** Entanglement entropy $S_{vn}$ serves as an order parameter, with $S_{vn} / S_{Page} \approx 0.5$ at $d_c$.

## 2. Optimization Task Definition

**Task:** Given a random circuit $C$ with $n$ qubits and depth $d$, apply a greedy gate cancellation optimizer for a fixed budget of $K$ iterations. Define success as achieving ≥20% gate count reduction while preserving unitary equivalence (fidelity ≥ 0.99).

**Success Metric:**
$$S(n, d) = \frac{1}{N_{trials}} \sum_{i=1}^{N_{trials}} \mathbb{1}[\text{reduction}_i \geq 0.20 \land \text{fidelity}_i \geq 0.99]$$

## 3. Experimental Design

### Experiment 1: Phase Transition Detection (Primary)
- **Parameters:** $n \in \{3, 4, 5, 6, 7, 8\}$, $d \in \{1, 2, ..., 50\}$
- **Trials:** $N = 100$ per $(n, d)$ configuration
- **Total circuits:** $6 \times 50 \times 100 = 30,000$
- **Circuit family:** Universal (Haar-random single-qubit + CNOT)
- **Optimizer:** Greedy gate cancellation (max 100 iterations)

### Experiment 2: Finite-Size Scaling
- **Parameters:** $n \in \{3, 4, 5, 6, 7, 8, 9, 10\}$, $d \in \{1, 2, ..., 60\}$
- **Trials:** $N = 50$ per configuration
- **Total circuits:** $8 \times 60 \times 50 = 24,000$
- **Purpose:** Extract critical exponents via FSS

### Experiment 3: Entanglement-Order Parameter Correlation
- **Parameters:** $n = 6$, $d \in \{1, 2, ..., 50\}$
- **Trials:** $N = 200$ per depth
- **Measurements:** Record both success/failure AND entanglement entropy
- **Purpose:** Test H3 (entanglement as order parameter)

### Experiment 4: Algorithm Comparison Across Phases
- **Parameters:** $n = 5$, $d \in \{5, 10, 15, 20, 25, 30\}$
- **Optimizers:** Greedy, Random Local Search, Simulated Annealing, Genetic Algorithm
- **Trials:** $N = 100$ per (depth, algorithm)
- **Purpose:** Characterize algorithm performance across phases

### Experiment 5: Circuit Family Universality
- **Parameters:** $n = 5$, $d \in \{1, 2, ..., 40\}$
- **Families:** Universal, Clifford, CNOT-Dihedral, Brickwork
- **Trials:** $N = 50$ per configuration
- **Purpose:** Test universality of phase transition

## 4. Statistical Analysis Plan

### 4.1 Phase Transition Detection
- **Method:** Logistic regression with depth as predictor
- **Critical point:** $d_c$ where $S(d_c) = 0.5$
- **Sharpness:** Fit to sigmoid $S(d) = \frac{1}{1 + e^{-\beta(d - d_c)}}$

### 4.2 Finite-Size Scaling
- **Ansatz:** $S(n, d) = f((d - d_c) \cdot n^{1/\nu})$
- **Critical exponents:** Extract $\nu$ (correlation length), $\beta$ (order parameter)
- **Method:** Data collapse with $\chi^2$ minimization

### 4.3 Bootstrap Confidence Intervals
- **Resamples:** $B = 10,000$
- **Statistics:** $d_c$, $\alpha$, $\nu$, $\beta$
- **Report:** Median and 95% CI

### 4.4 Hypothesis Testing
- **H1 test:** Likelihood ratio test for sigmoid vs. linear model
- **H2 test:** Linear regression of $\log(d_c)$ vs. $\log(n)$
- **H3 test:** Pearson correlation between $S_{vn}$ and success rate

## 5. Data Management

- **Raw data:** CSV with columns: trial_id, n_qubits, depth, family, seed, gate_count, optimized_count, fidelity, success, entanglement_entropy, runtime_ms
- **Processed data:** Aggregated statistics with bootstrap CIs
- **Figures:** Publication-quality PNG/PDF with error bars
- **Code:** Version-tagged Git repository

## 6. Quality Assurance

- **Unit tests:** All generators, optimizers, analysis functions
- **Integration tests:** Full pipeline on small dataset (n=3, d=1-5)
- **Sanity checks:** Entropy bounds, fidelity bounds, monotonicity where expected
- **Reproducibility:** Docker container with fixed dependency versions
