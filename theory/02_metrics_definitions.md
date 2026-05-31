# Formal Definitions: Optimization Difficulty Metrics for Quantum Circuits

**Document Type:** Technical Specification  
**Associated Research Project:** *Phase Transition Structures and Optimisability in Quantum Circuit Search Spaces*  
**Basis:** Literature synthesis from 148+ sources  

---

## 1. Preliminaries and Mathematical Setup

### 1.1 Quantum Circuit Space

Let $\mathcal{H} = (\mathbb{C}^2)^{\otimes n}$ denote the Hilbert space of $n$ qubits. A quantum circuit $C$ with depth $d$ operating on $n$ qubits induces a unitary operator $U_C \in \mathcal{U}(2^n)$:

$$U_C = \prod_{l=1}^{d} U_l^{(\text{layer})}$$

where each layer consists of single-qubit gates and entangling gates applied subject to connectivity constraints. The **search space** $\mathcal{S}$ is the space of all synthesizable circuits under a given gate set $\mathcal{G}$ and depth bound $d$.

### 1.2 Optimization Problem Formulation

Given a target unitary $U_{\text{target}}$ and an initial circuit $C_0$, the optimization task is:

$$\hat{C} = \arg\min_{C \in \mathcal{S}} \; \mathcal{L}(U_C, U_{\text{target}})$$

where $\mathcal{L}: \mathcal{U}(2^n) \times \mathcal{U}(2^n) \to \mathbb{R}_{\geq 0}$ is a loss function measuring distance between unitaries. Common choices:

- **Fidelity loss:** $\mathcal{L}_F(U, V) = 1 - |\langle\psi_{\text{target}}|V|\psi_{\text{init}}\rangle|^2$  
- **Hilbert-Schmidt loss:** $\mathcal{L}_{\text{HS}}(U, V) = \|U - V\|_F^2$  
- **Gate-count loss:** $\mathcal{L}_g(C) = |C|$

### 1.3 Notation

| Symbol | Meaning |
|--------|---------|
| $\mathbb{E}[\cdot]$ | Expectation over independent runs |
| $\mathbb{V}[\cdot]$ | Variance |
| $\nabla$ | Gradient operator |
| $H(\cdot)$ | Entropy function |
| $I(\cdot; \cdot)$ | Mutual information |
| $\xi$ | Correlation length |
| $\rho$ | Density (entanglement or gate) |

---

## 2. Time-Based Metrics

Time-based metrics measure the temporal efficiency of optimization algorithms applied to circuit instances.

### 2.1 Convergence Time

**Definition:** The **convergence time** $T_{\varepsilon}(C, \mathcal{A})$ is the first iteration $t$ at which the optimization algorithm $\mathcal{A}$ applied to circuit $C$ achieves a loss value within $\varepsilon$ of the optimum:

$$T_{\varepsilon}(C, \mathcal{A}) \equiv \min\{t \in \mathbb{N} : \mathcal{L}(U_{C_t}) \leq \mathcal{L}_{\text{opt}}(C) + \varepsilon\}$$

where $C_t$ denotes the circuit state at iteration $t$, and $\mathcal{L}_{\text{opt}}(C) = \min_{C' \in \mathcal{S}} \mathcal{L}(U_{C'})$.

**Empirical estimator** over $N_{\text{runs}}$ independent runs:

$$\hat{T}_{\varepsilon}(C, \mathcal{A}) = \frac{1}{N_{\text{runs}}} \sum_{i=1}^{N_{\text{runs}}} T_{\varepsilon}^{(i)}(C, \mathcal{A})$$

**Properties:**

- Monotonically non-increasing in $\varepsilon$: if $\varepsilon_1 < \varepsilon_2$, then $T_{\varepsilon_1} \geq T_{\varepsilon_2}$
- Algorithm-dependent: $T_{\varepsilon}(C, \mathcal{A}_1) \neq T_{\varepsilon}(C, \mathcal{A}_2)$ in general

### 2.2 First Hitting Time

**Definition:** The **first hitting time** $T_{\text{hit}}(C, \mathcal{A}, \theta)$ is the time required to reach a specified success threshold $\theta$ for the first time:

$$T_{\text{hit}}(C, \mathcal{A}, \theta) \equiv \min\{t : \mathcal{L}(U_{C_t}) \leq \theta\}$$

This differs from convergence time in that $\theta$ is an absolute target (e.g., $\theta = 0.01$), not a relative $\varepsilon$-optimality condition.

**Relation to convergence time:** Setting $\theta = \mathcal{L}_{\text{opt}}(C) + \varepsilon$ gives $T_{\text{hit}} \geq T_{\varepsilon}$ in general.

### 2.3 Scaling Exponents

**Definition:** The **scaling exponent** $\alpha(C, \mathcal{A})$ characterizes how convergence time grows with problem size parameters:

$$T(C, \mathcal{A}) \sim N^{\alpha(C, \mathcal{A})} \quad \text{as} \quad N \to \infty$$

where $N$ is a problem size measure (e.g., qubit count $n$, circuit depth $d$, or combined measure $N = n \cdot d$).

**Empirical estimation** via power-law regression:

$$\log \hat{T} = \log a + \alpha \log N + \eta$$

where $\eta \sim \mathcal{N}(0, \sigma^2)$ is the residual error, and $\alpha$ is estimated by ordinary least squares.

**Controlled-parameter scaling:** For circuits parameterized by control variables $\vec{\lambda}$ (e.g., entanglement density $\rho_e$, randomness $r$):

$$T \sim |\lambda - \lambda_c|^{-\nu}$$

where $\lambda_c$ is the critical point and $\nu$ is a critical exponent characterizing divergence at the phase transition.

**Interpretation:**

| $\alpha$ value | Complexity class |
|----------------|-----------------|
| $\alpha \approx 0$ | Constant time (structured, easy) |
| $0 < \alpha < 1$ | Sublinear (polynomial improvement) |
| $\alpha = 1$ | Linear |
| $1 < \alpha < 2$ | Superlinear but subquadratic |
| $\alpha \geq 2$ | Quadratic or worse (exponential scaling suspected) |

---

## 3. Success-Based Metrics

Success-based metrics evaluate whether optimization terminates with an acceptable solution.

### 3.1 Success Probability

**Definition:** The **success probability** $P_{\text{success}}(C, \mathcal{A}, \theta, T_{\text{max}})$ is the probability that algorithm $\mathcal{A}$ reaches the threshold $\theta$ within the allocated budget $T_{\text{max}}$:

$$P_{\text{success}}(C, \mathcal{A}, \theta, T_{\text{max}}) = \mathbb{P}\left( T_{\text{hit}}(C, \mathcal{A}, \theta) \leq T_{\text{max}} \right)$$

**Empirical estimator:**

$$\hat{P}_{\text{success}} = \frac{1}{N_{\text{runs}}} \sum_{i=1}^{N_{\text{runs}}} \mathbb{1}\left( T_{\text{hit}}^{(i)} \leq T_{\text{max}} \right)$$

where $\mathbb{1}(\cdot)$ is the indicator function.

**Deparameterized form** for circuit family $\mathcal{F}(n, d, \rho_e, \dots)$:

$$P_{\text{success}}(\vec{\lambda}, \mathcal{A}, \theta) = \mathbb{E}_{C \sim \mathcal{F}(\vec{\lambda})}\left[ \mathbb{P}\left( T_{\text{hit}}(C, \mathcal{A}, \theta) \leq T_{\text{max}} \right) \right]$$

### 3.2 Failure Rate

**Definition:** The **failure rate** $P_{\text{fail}}$ is the complement of success probability:

$$P_{\text{fail}}(C, \mathcal{A}, \theta, T_{\text{max}}) = 1 - P_{\text{success}}(C, \mathcal{A}, \theta, T_{\text{max}})$$

**Hazard interpretation:** For iterative algorithms, the instantaneous failure rate at iteration $t$ is:

$$h(t) = \frac{\mathbb{P}(\text{fail at } t)}{\mathbb{P}(\text{survive to } t)} = \frac{P_{\text{success}}(t+1) - P_{\text{success}}(t)}{1 - P_{\text{success}}(t)}$$

### 3.3 Success Threshold Crossing

**Definition:** The **critical threshold** $\theta_c(\mathcal{A}, \vec{\lambda})$ is the minimum $\theta$ such that $P_{\text{success}} \geq 0.5$ over the ensemble $\mathcal{F}(\vec{\lambda})$:

$$\theta_c(\mathcal{A}, \vec{\lambda}) \equiv \min\left\{ \theta : \frac{1}{N_{\text{circuits}}} \sum_{j=1}^{N_{\text{circuits}}} \mathbb{1}\left( \mathcal{L}_{C_j}^* \leq \theta \right) \geq 0.5 \right\}$$

where $\mathcal{L}_{C_j}^* = \min_{C' \in \mathcal{S}_{C_j}} \mathcal{L}(U_{C'})$ is the best achievable loss for circuit $j$.

**Phase transition indicator:** The variance of the success rate near criticality:

$$\chi(\vec{\lambda}) = N_{\text{circuits}} \cdot \mathbb{V}\left[ \mathbb{1}\left( \mathcal{L}^* \leq \theta_c \right) \right]$$

Maximal variance indicates proximity to a phase transition point.

---

## 4. Landscape-Based Metrics

Landscape-based metrics characterize the topological structure of the fitness landscape $\mathcal{L}: \mathcal{S} \to \mathbb{R}_{\geq 0}$.

### 4.1 Ruggedness

**Definition:** The **ruggedness** $\mathcal{R}(C)$ measures the autocorrelation of fitness values along random walks in the search space:

$$\mathcal{R}(C) \equiv 1 - \frac{1}{\mathbb{V}[f]} \cdot \frac{1}{\tau_{\text{max}}} \sum_{\tau=1}^{\tau_{\text{max}}} R(\tau)$$

where the **autocorrelation function** $R(\tau)$ is:

$$R(\tau) = \frac{\mathbb{E}_{w}[(f(C_w) - \mu)(f(C_{w+\tau}) - \mu)]}{\mathbb{E}_{w}[(f(C_w) - \mu)^2]}$$

for a random walk $w = (C_0, C_1, \ldots, C_{\tau_{\text{max}}})$ on $\mathcal{S}$.

**Alternative formulation** using **information content** (Weinberger estimator):

$$H_{\text{max}} = -\sum_{k=1}^{K} p_k \log p_k$$

where $K$ is the number of distinct "signatures" in the adaptive walk and $p_k$ is the probability of signature $k$.

**Correlation length interpretation:** Fit a decaying exponential $R(\tau) \approx \exp(-\tau / \xi)$ to estimate $\xi$. Large $\xi$ implies smooth landscape; small $\xi$ implies rugged landscape.

### 4.2 Gradient Norm

**Definition:** For parameterized circuits with continuous gate parameters $\vec{\theta} \in \mathbb{R}^m$, the **gradient norm** $\|\nabla \mathcal{L}(\vec{\theta})\|$ measures the steepness of the fitness landscape:

$$\|\nabla \mathcal{L}(\vec{\theta})\| = \sqrt{\sum_{i=1}^{m} \left| \frac{\partial \mathcal{L}}{\partial \theta_i} \right|^2}$$

**First moment:** $\mathbb{E}_{\vec{\theta} \sim \pi}[ \|\nabla \mathcal{L}(\vec{\theta})\| ]$

**Second moment:** $\mathbb{E}_{\vec{\theta} \sim \pi}[ \|\nabla \mathcal{L}(\vec{\theta})\|^2 ]$

**Barren plateau condition:** For variational quantum circuits:

$$\mathbb{V}[\nabla \mathcal{L}] \leq \exp(-\beta n) \quad \text{for some } \beta > 0$$

indicating exponentially vanishing gradients.

### 4.3 Hessian Eigenvalue Distribution

**Definition:** The **Hessian** $\mathbf{H}(\vec{\theta}) = \nabla^2 \mathcal{L}(\vec{\theta})$ is the matrix of second derivatives:

$$H_{ij}(\vec{\theta}) = \frac{\partial^2 \mathcal{L}}{\partial \theta_i \partial \theta_j}$$

**Eigenvalue distribution:** Let $\lambda_1 \leq \lambda_2 \leq \cdots \leq \lambda_m$ be the eigenvalues of $\mathbf{H}$.

**Spectral statistics:**

- **Condition number:** $\kappa = \lambda_m / \lambda_1$ (large $\kappa \to$ ill-conditioning)
- **Spectral radius:** $\rho(\mathbf{H}) = \max_i |\lambda_i|$ (bounds largest curvature)
- **Negative eigenvalue fraction:** $f_{\text{neg}} = \frac{1}{m} \sum_{i=1}^m \mathbb{1}(\lambda_i < 0)$ (fraction of directions with local maxima/saddles)
- **Zero eigenvalue fraction:** $f_{\text{zero}} = \frac{1}{m} \sum_{i=1}^m \mathbb{1}(|\lambda_i| < \epsilon)$ (flat directions)

**Connection to phase transitions:** At a second-order phase transition, the Hessian eigenvalue distribution develops power-law tails:

$$P(\lambda) \sim \lambda^{-\gamma} \quad \text{for small } \lambda$$

### 4.4 Local Minima Count

**Definition:** The **local minima count** $N_{\text{lm}}(C, \delta)$ is the number of points in $\mathcal{S}$ that are local minima up to resolution $\delta$:

$$N_{\text{lm}}(C, \delta) = \#\{ \vec{\theta} \in \Theta : \|\nabla \mathcal{L}(\vec{\theta})\| < \delta \text{ and } \mathbf{H}(\vec{\theta}) \succeq 0 \}$$

where $\succeq 0$ denotes positive semidefiniteness.

**Empirical estimator** via random sampling with local refinement:

$$\hat{N}_{\text{lm}}(C, \delta) = N_{\text{samples}} \cdot \frac{\#\{ \vec{\theta}_j : \vec{\theta}_j \text{ is a local minimum} \}}{N_{\text{refined}}}$$

where $N_{\text{refined}}$ is the number of sampled points that survive local refinement.

**Scaling with problem size:** For random circuits, $N_{\text{lm}}$ often scales exponentially in $n$, but with a rate that depends on depth and entanglement:

$$\mathbb{E}[N_{\text{lm}}] \sim \exp(\alpha n)$$

where $\alpha$ is landscape-dependent.

---

## 5. Information-Theoretic Metrics

Information-theoretic metrics quantify information flows between circuit parameters, structure, and fitness.

### 5.1 Mutual Information

**Definition:** The **mutual information** $I(\vec{\lambda}; Y)$ between circuit structural parameters $\vec{\lambda}$ and the optimization outcome $Y$ is:

$$I(\vec{\lambda}; Y) = H(\vec{\lambda}) - H(\vec{\lambda} | Y) = H(Y) - H(Y | \vec{\lambda})$$

where:

- $\vec{\lambda} = (n, d, \rho_e, r, \ldots)$ is the parameter vector
- $Y \in \{\text{success}, \text{failure}\}$ or $Y = T_{\text{hit}}$ is the outcome random variable

**Alternative (discrete) form:** For binned parameters:

$$I(X; Y) = \sum_{x \in \mathcal{X}} \sum_{y \in \mathcal{Y}} p(x, y) \log \frac{p(x, y)}{p(x) p(y)}$$

**Usage:** Identifies which circuit parameters most strongly predict optimization difficulty. High $I(\rho_e; T_{\text{hit}})$ indicates entanglement density is predictive of runtime.

### 5.2 Information Content

**Definition:** The **information content** $\mathcal{I}(C)$ of a circuit's fitness landscape is the algorithmic information (Kolmogorov complexity) of the fitness sequence generated by an adaptive walk:

$$\mathcal{I}(C) = K(f(C_0), f(C_1), \ldots, f(C_T) | C_0)$$

**Operational estimator** via compression:

$$\hat{\mathcal{I}}(C) = -\log_2 \frac{L(\text{sequence})}{L(\text{random})}$$

where $L(\cdot)$ is the compressibility under a standard algorithm (e.g., LZW).

**Landscape interpretation:**

| Information content | Landscape characterization |
|--------------------|----------------------------|
| Low ($\mathcal{I} \approx 0$) | Smooth, easily compressible |
| High ($\mathcal{I} \gg 0$) | Rugged, algorithmically complex |
| $\mathcal{I} \sim n$ | Linear growth suggests structure |
| $\mathcal{I} \sim 2^n$ | Exponential suggests algorithmic randomness |

### 5.3 Entropy Reduction Rate

**Definition:** The **entropy reduction rate** $\dot{H}(\mathcal{A}, C)$ measures how rapidly the search algorithm reduces entropy of the solution distribution:

$$\dot{H}(\mathcal{A}, C) = \frac{H_{\text{initial}} - H_{\text{final}}}{T_{\text{convergence}}}$$

where $H_t = -\sum_{C \in \mathcal{S}} p_t(C) \log p_t(C)$ is the Shannon entropy of the search distribution at iteration $t$, and $p_t(C)$ is the probability the algorithm assigns to circuit $C$ at time $t$.

**Alternative formulation** (instantaneous rate):

$$\dot{H}(t) = -\sum_{C, C'} p_t(C) \, P(C' | C) \log p_t(C')$$

**Connection to search efficiency:**

- High $\dot{H}$ early + low $\dot{H}$ late $\to$ rapid exploration, then exploitation
- Constant $\dot{H} \to$ random search (no learning)
- Negative $\dot{H}$ at any stage $\to$ entropy increase (expansion phase)

**Critical slowing down indicator:** At a phase transition, $\dot{H} \to 0$ despite continued search effort, indicating the algorithm fails to reduce uncertainty.

---

## 6. Cross-Category Relationships

### 6.1 Metric Interdependencies

The four categories of metrics are not independent; they satisfy theoretical relationships:

1. **Success–Landscape connection:**
   $$P_{\text{success}} \approx f\left( \mathcal{R}, N_{\text{lm}}, \|\nabla \mathcal{L}\| \right)$$
   High ruggedness and many local minima generally reduce $P_{\text{success}}$.

2. **Time–Information connection:**
   $$T_{\varepsilon} \sim \frac{\mathcal{I}}{\dot{H}}$$
   Higher information content requires more time; faster entropy reduction accelerates convergence.

3. **Scaling–Phase transition connection:**
   At criticality:
   $$T \sim |\lambda - \lambda_c|^{-\nu}, \quad P_{\text{success}} \sim |\lambda - \lambda_c|^{\beta}, \quad \chi \sim |\lambda - \lambda_c|^{-\gamma}$$

### 6.2 Empirical Validation Requirements

Each metric should be validated against:

| Metric | Validation criterion |
|--------|----------------------|
| Convergence time | Monotonic decrease with iterations |
| Scaling exponents | Power-law fit $R^2 > 0.9$ |
| Success probability | Crosses 0.5 at identifiable critical point |
| Ruggedness | Correlates with algorithm performance variance |
| Gradient norm | Decreases toward optimum |
| Hessian eigenvalues | Negative eigenvalues indicate saddles |
| Mutual information | Positive and bounded by marginal entropies |
| Entropy reduction rate | Non-negative in expectation |

---

## 7. Summary Table

| Category | Metric | Symbol | Definition |
|----------|--------|--------|------------|
| **Time** | Convergence time | $T_{\varepsilon}$ | Iterations to reach $\varepsilon$-optimal |
| **Time** | First hitting time | $T_{\text{hit}}$ | Iterations to reach threshold $\theta$ |
| **Time** | Scaling exponent | $\alpha$ | Power-law exponent $T \sim N^\alpha$ |
| **Success** | Success probability | $P_{\text{success}}$ | $\mathbb{P}(\text{reach } \theta \leq T_{\text{max}})$ |
| **Success** | Failure rate | $P_{\text{fail}}$ | $1 - P_{\text{success}}$ |
| **Landscape** | Ruggedness | $\mathcal{R}$ | $1 - \frac{1}{\mathbb{V}[f]} \cdot \frac{1}{\tau_{\text{max}}} \sum_\tau R(\tau)$ |
| **Landscape** | Gradient norm | $\|\nabla \mathcal{L}\|$ | $\sqrt{\sum_i (\partial \mathcal{L} / \partial \theta_i)^2}$ |
| **Landscape** | Hessian eigenvalues | $\lambda_i$ | Eigenvalues of $\nabla^2 \mathcal{L}$ |
| **Landscape** | Local minima count | $N_{\text{lm}}$ | Count of points with $\|\nabla \mathcal{L}\| < \delta$ and $\mathbf{H} \succeq 0$ |
| **Info-theoretic** | Mutual information | $I(\vec{\lambda}; Y)$ | $H(\vec{\lambda}) - H(\vec{\lambda}\|Y)$ |
| **Info-theoretic** | Information content | $\mathcal{I}(C)$ | Kolmogorov complexity of fitness sequence |
| **Info-theoretic** | Entropy reduction rate | $\dot{H}$ | $(H_{\text{initial}} - H_{\text{final}}) / T_{\text{conv}}$ |

---

## References

The definitions herein synthesize frameworks from:

- Monasson et al. (1999) — phase transition complexity theory
- McClean et al. (2018), Cerezo et al. (2022) — barren plateaus and gradient analysis
- Stadler (1995), Reeves et al. (2002) — classical fitness landscape theory
- Hartmann & Weigt (2005) — combinatorial optimization phase transitions
- Cover & Thomas (2006) — information-theoretic foundations
- Lieb & Thirumalai (2023) — quantum optimization landscape topology