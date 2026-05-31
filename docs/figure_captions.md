# Figure Captions — Quantum Circuit Optimization: Exponential Decay Without Phase Transition

> Reference: `manuscript_v4.md`

---

**Fig. 1 | Phase transition test: exponential decay versus sigmoid model.**  
**a**, Success probability $P(d)$ across $n \\in [3, 5, 7]$ qubits. Lines show exponential fit $P(d) = P_0 \\exp(-d/d_0)$; shaded bands are 95% bootstrap confidence intervals ($N=10,000$ resamples). **b**, Sigmoid fit to test phase transition hypothesis. Red line: sigmoid with fitted $d_c$ and width $\\sigma$. Inset: residuals showing systematic deviation from sigmoid form. **c**, AIC/BIC comparison: $\\Delta$AIC and $\\Delta$BIC consistently favour exponential model across all qubit counts. **d**, Statistical power analysis: $\\beta(d)$ (power to detect a transition) exceeds 0.80 at all depths, confirming the null result is not underpowered.

---

**Fig. 2 | Finite-size scaling of decay depth $d_0$.**  
**a**, Extracted decay depth $d_0$ versus qubit count $n$. The flat trend ($R^2 = 0.085$, $p = 0.52$) shows no systematic scaling, ruling out a thermodynamic phase transition. **b**, Bootstrap distribution of $d_0$ estimates for each $n$. Error bars: 95% CI. **c**, Extracted asymptotic success rate $P_0$ versus $n$. **d**, Goodness-of-fit ($R^2$) for exponential model across all system sizes. All values exceed 0.80, confirming model adequacy.

---

**Fig. 3 | Entanglement density sweep: identifying the optimization sweet spot.**  
**a**, Success probability as a function of entanglement density $\\rho = N_{\\text{ent}} / N_{\\text{total}}$. Each point represents the mean over 300 randomized trials (10 depths × 30 trials). The solid line is a locally weighted scatterplot smoothing (LOESS) fit. Peak success occurs at $\\rho \\in [0.3, 0.5]$. **b**, Success rate heatmap: colour encodes $P_{\\text{success}}$ in the ($\\rho$, depth) plane. White dashed line traces the ridge of maximum success. **c**, Gate reduction versus entanglement density, showing a separate optimum at $\\rho \\approx 0.4$.

---

**Fig. 4 | Algorithm comparison: deterministic greedy dominance over stochastic global search.**  
**a**, Success rate comparison across four optimizer classes: Greedy (deterministic local), SA (stochastic global, Metropolis), GA (stochastic global, evolutionary), and Random (baseline). Greedy achieves 20.0% success versus 0.0% for SA and GA. Error bars: bootstrap 95% CI ($N=10,000$). **b**, Runtime comparison (log scale). Greedy operates in the millisecond regime, three orders of magnitude faster than stochastic methods. **c**, Gate reduction vs. runtime Pareto front. Greedy dominates SA and GA in both axes ($p < 10^{-17}$, Wilcoxon rank-sum). **d**, Success rate as a function of SA temperature schedule parameter $\\alpha$. Performance remains near zero across the full range $\\alpha \\in [0.80, 0.9999]$.

---

**Fig. 5 | Optimization landscape: gate reduction scaling and parameter sensitivity.**  
**a**, Mean gate reduction $\\Delta G$ versus circuit size $n$ (left panel). Error bars: 95% bootstrap CI ($N=10,000$). Solid line: power-law fit $\\Delta G = a \\cdot n^b$ with $a = 0.682$ [95% CI: $(0.591, 0.784)$], $b = 0.281$ [95% CI: $(0.254, 0.308)$]. Right panel: log-log representation confirming linear scaling. **b**, Parameter sensitivity analysis: performance robustness across optimizer hyperparameter space. **c**, Gate reduction rate $\\Delta G / n$ decreasing with system size, indicating diminishing per-qubit optimization returns for larger circuits. **d**, Iteration convergence profiles for each optimizer class.

---

**Fig. 6 | Industrial baseline comparison: Qiskit transpiler benchmark.**  
**a**, Gate reduction rate: Qiskit Level 2 achieves 55.0% reduction, substantially outperforming all prototype optimizers. **b**, Success rate: Qiskit L0–L3 achieve 100% success across all depths, versus $\\sim$20% (Greedy) and $\\sim$0% (SA/GA). **c**, Fidelity and runtime trade-off. Qiskit preserves perfect fidelity (1.000) while operating in the 10–20 ms range, demonstrating that production-grade peephole optimization with correct unitary equivalence checking outperforms all tested heuristic approaches.
