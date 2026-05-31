# Q-research 全面优化计划 (Optimization Plan)
## 评估日期: 2026-05-30
## 当前版本: v2.1.0 → 目标版本: v3.0.0

---

# PART A: 严格评估报告 (Rigorous Assessment)

## A.1 总体评级: ❌ 未达到博士后/顶级期刊标准

当前项目具有**硕士论文中上水平**，但距离 Nature/Science/PRL/PRX Quantum 等顶级期刊发表存在**系统性差距**。以下是逐项评估。

---

## A.2 致命缺陷 (Critical Issues — 必须修复)

### C1. 论文内部自相矛盾 ⚠️⚠️⚠️
- **Abstract/Results 2.1**: 声称 GREEDY 表现最好 (14.4% reduction, 20% success)
- **Results 2.4**: 声称 SA/GA 表现最好 ("highest efficacy, successfully navigating local minima")
- **实际数据**: SA 0% success / 0.2% reduction, GA 0% success / 1% reduction
- **结论**: 论文文本与数据严重矛盾。2.4节的叙述完全错误，必须重写。

### C2. 缺乏与工业级编译器的对比 ⚠️⚠️⚠️
- 未与 Qiskit Transpiler (optimization_level=3) 对比
- 未与 TKET (pytket) 对比
- 未与 Qiskit 的 SabreSwap/Route 对比
- **没有 baseline，所有 "scaling law" 的结论都没有参照系**

### C3. 优化器实现质量低 ⚠️⚠️⚠️
- Greedy: 仅做相邻门消除，不做 commutation、不做 template matching
- SA: 仅支持 gate removal，不支持 gate insertion/swapping/commutation
- GA: crossover 操作会破坏电路的酉等价性（直接拼接两段不同电路）
- RLS: 同上，仅做 gate removal
- **结论**: SA/GA/RLS 的 0% success 率不是算法本身的问题，而是实现有 bug

### C4. 电路生成器过于简化 ⚠️⚠️
- 仅支持 {H, T, Rz, CNOT} 门集
- 无真实量子算法 benchmark (QAOA, VQE, Grover, QFT, etc.)
- "entanglement_density" 的定义不严格（仅控制 CNOT 出现概率）
- 不支持硬件拓扑约束 (coupling map)
- 不支持连续参数门 (Rx, Ry, Rz with arbitrary angles)

### C5. 保真度计算存在物理问题 ⚠️⚠️
- `calculate_fidelity`: 使用 `|Tr(U1† U2)|² / 4^n`
- 这是 normalized Hilbert-Schmidt inner product, **不是** average gate fidelity
- 正确的 average gate fidelity: `F_avg = (|Tr(U1† U2)|² + d) / (d² + d)`, d = 2^n
- 对于大 n，两种定义会有显著差异

### C6. FSS 分析无统计意义 ⚠️⚠️
- d_c(n) vs n 的拟合 R² = 0.09, p = 0.52
- **这不是一个有效结果，不应在论文中作为 positive finding 呈现**
- 需要更多 trials (≥500/depth) 和更大 qubit range

### C7. 无理论分析 ⚠️⚠️
- 全文纯 empirical，无任何定理/证明
- 对于 PRL/Nature Physics 级别，至少需要：
  - 一个简单的 toy model 解释指数衰减
  - 或一个信息论下界 (lower bound)
  - 或与已知复杂度理论的联系

---

## A.3 严重缺陷 (Major Issues — 强烈建议修复)

### M1. 无噪声模型
- NISQ 时代的优化必须考虑噪声
- 需加入 depolarizing noise / amplitude damping
- 展示优化后的电路在噪声下的实际保真度提升

### M2. 实验规模不足
- E2 仅 30 trials/density（报告中也承认了）
- E3 仅 50 trials/(n,d) pair
- E4 仅 100 trials/optimizer
- 顶级期刊通常需要 1000+ trials

### M3. 参考文献不足
- 仅 10 篇参考文献
- Nature/PRL 通常需要 30-50 篇
- 缺失关键引用：
  - Nash et al. (2020) quantum circuit optimization review
  - De Cross et al. (2023) computational power of quantum circuits
  - Pallasch et al. (2023) phase transitions in circuit optimization
  - Recent ZX-calculus based optimization papers

### M4. 无 LaTeX 版本
- 仅有 Markdown 草稿
- 物理学期刊必须使用 LaTeX
- 需要 RevTeX 或 Nature 模板

### M5. Landscape 分析方法论问题
- E5 的 "perturbation" 方法（随机交换/删除门）不改变电路的酉操作
- 交换非交换门会改变电路功能 → 这不是 landscape 探索
- 正确方法应在保持酉等价性的变换空间中采样

---

## A.4 中等缺陷 (Moderate Issues)

### m1. 代码质量
- "CNOT_DIHERDRAL" 拼写错误 (应为 DIHEDRAL)
- 无 unit tests
- 无 type checking (mypy)
- 无 CI/CD

### m2. 图表质量
- 需要确认 error bars 是否在所有图中
- 需要统一色彩方案 (色盲友好)
- 需要矢量格式 (PDF/SVG)
- 字体大小需符合期刊要求

### m3. 论文结构
- Methods 部分不完整
- 无 Supplementary Information
- 无 Author Contributions
- 无 Competing Interests 声明

---

# PART B: 优化执行计划 (Execution Plan)

## Phase 0: 紧急修复 (Day 1-2)
> 修复致命错误和内部矛盾

### Task 0.1: 修复论文自相矛盾
- [ ] 重写 Results 2.4，使文本与数据一致
- [ ] 统一 Abstract 和正文的叙述
- [ ] 确认所有统计数据引用准确

### Task 0.2: 修复优化器实现
- [ ] SA: 增加 gate swap, gate commutation, gate insertion moves
- [ ] GA: 修复 crossover 保持酉等价性
- [ ] RLS: 增加 move set 多样性
- [ ] 所有优化器增加 unit test

### Task 0.3: 修复保真度计算
- [ ] 改用正确的 average gate fidelity 公式
- [ ] 验证所有已有结果的 fidelity 值是否受影响
- [ ] 更新受影响的图表和数据

---

## Phase 1: 理论框架强化 (Day 3-5)
> 添加理论深度，达到博士后标准

### Task 1.1: 建立简单理论模型
- [ ] 推导: 随机电路中 adjacent gate cancellation 的概率模型
  - P(cancellation at depth d) ≈ f(d, n, gate_set)
  - 预期: 推导出的衰减形式应与实验的指数衰减吻合
- [ ] 推导: 门数量的信息论下界
  - 给定 n qubits 和 gate set G，最小电路深度的下界
- [ ] 推导: entanglement density 与优化难度的定量关系
  - 利用 Schmidt rank 论证

### Task 1.2: 与已知理论建立联系
- [ ] 与 barren plateau 理论的联系和区别
- [ ] 与 random circuit scrambling 的联系
- [ ] 与 computational complexity (QMA-hard) 的联系
- [ ] 添加 5-8 篇关键参考文献

### Task 1.3: 形式化定义
- [ ] 严格定义 "optimization landscape" (在什么空间上？)
- [ ] 严格定义 "ruggedness" (用什么度量？)
- [ ] 严格定义 "phase transition" (用什么序参量？)

---

## Phase 2: 实验重设计与执行 (Day 6-10)
> 补齐关键实验，提升统计力量

### Task 2.1: 添加工业级 Baseline 实验 (E6)
- [ ] 安装 Qiskit 和 TKET
- [ ] 实现 E6: 相同电路用 Qiskit optimization_level=3 优化
- [ ] 实现 E6: 相同电路用 TKET FullPeepholeOptimise 优化
- [ ] 记录 reduction, fidelity, runtime
- [ ] 参数: n=5-10, d=1-50, 100 trials

### Task 2.2: 添加真实算法 Benchmark (E7)
- [ ] 生成 QAOA 电路 (MaxCut, p=1-5)
- [ ] 生成 VQE 电路 (H2, LiH ansatz)
- [ ] 生成 QFT 电路 (n=4-8)
- [ ] 生成 Grover 电路 (n=3-5, 1-3 iterations)
- [ ] 对所有电路运行全部优化器
- [ ] 记录结果

### Task 2.3: 增加统计力量
- [ ] E2: 重新运行，100 trials/density (当前30)
- [ ] E3: 重新运行，100 trials/(n,d) (当前50)
- [ ] E4: 用修复后的优化器重新运行
- [ ] 所有实验增加 effect size 报告 (Cohen's d)

### Task 2.4: 添加噪声实验 (E8)
- [ ] 实现简单的 depolarizing noise model
- [ ] 测量: 优化前 vs 优化后的含噪声 fidelity
- [ ] 参数: noise_rate = 0.001, 0.01, 0.1
- [ ] 展示优化在 NISQ 条件下的实际价值

---

## Phase 3: 代码质量提升 (Day 11-13)
> 达到可发表、可重复的标准

### Task 3.1: 代码重构
- [ ] 修复 "CNOT_DIHERDRAL" → "CNOT_DIHEDRAL"
- [ ] 添加 proper type hints (全部模块)
- [ ] 添加 docstrings (Google style)
- [ ] 实现 proper circuit representation (DAG-based, not list-based)

### Task 3.2: 测试框架
- [ ] 添加 pytest 测试套件
  - test_generator.py: 电路生成的正确性
  - test_optimizers.py: 优化器的酉等价性保持
  - test_analysis.py: 统计分析的正确性
  - test_fidelity.py: 保真度计算的物理正确性
- [ ] 目标覆盖率: >80%

### Task 3.3: 可重复性
- [ ] 完善 Dockerfile
- [ ] 完善 environment.yml (pin versions)
- [ ] 添加 Makefile (make run-all, make test, make figures)
- [ ] 添加 README.md with reproduction instructions

---

## Phase 4: 论文重写 (Day 14-20)
> 从零重写，达到 PRL/PRX Quantum 标准

### Task 4.1: 新标题和定位
**建议新标题:**
> "Scaling Laws and the Absence of Phase Transitions in Heuristic Quantum Circuit Compilation"

或更有力度的:
> "Exponential Hardness of Quantum Circuit Optimization: Empirical Scaling Laws and Entanglement Thresholds"

**目标期刊 (按优先级):**
1. PRX Quantum (IF ~7.6, 最匹配)
2. Quantum (IF ~6.4, 开放获取)
3. Quantum Science and Technology (IF ~5.0)
4. Physical Review A (IF ~2.9, 保底)

### Task 4.2: LaTeX 论文结构
```
paper/
├── main.tex           (RevTeX 4-2 / Nature template)
├── figures/           (所有矢量图)
├── supplementary.tex  (详细方法、额外图表)
├── bibliography.bib   (40+ references)
└── response/          (未来审稿回复)
```

### Task 4.3: 论文章节重写
- [ ] **Abstract**: 精简至 150 词以内，突出 null result (no phase transition)
- [ ] **Introduction**: 重写，加入 barren plateau 和 quantum compilation hardness 的最新文献
- [ ] **Results**: 
  - 2.1 指数衰减 (保留，加强理论解释)
  - 2.2 纠缠密度 sweet spot (保留)
  - 2.3 幂律缩放 (保留，修复 FSS 的呈现)
  - 2.4 算法对比 (完全重写，修复矛盾)
  - 2.5 与工业编译器对比 (新增)
  - 2.6 真实算法 benchmark (新增)
  - 2.7 噪声环境下的优化效果 (新增)
- [ ] **Discussion**: 重写，加入理论意义和实际意义
- [ ] **Methods**: 完整重写
- [ ] **Supplementary**: 详细推导、额外图表、代码清单

### Task 4.4: 图表重新生成
- [ ] Fig 1: Phase transition (加入 theoretical prediction curve)
- [ ] Fig 2: Entanglement density (增加 error bars)
- [ ] Fig 3: FSS scaling (修复呈现方式)
- [ ] Fig 4: Algorithm comparison (加入 Qiskit/TKET baseline)
- [ ] Fig 5: Landscape (改进方法论)
- [ ] Fig 6 (新): Real algorithm benchmarks
- [ ] Fig 7 (新): Noise model results
- [ ] 所有图: 色盲友好配色，统一风格

---

## Phase 5: 质量验证 (Day 21-23)

### Task 5.1: 内部审查
- [ ] 全文一致性检查 (数据 vs 文本 vs 图表)
- [ ] 统计方法验证 (bootstrap 参数、CI 计算)
- [ ] 所有 p-values 独立验证
- [ ] 参考文献格式统一

### Task 5.2: 可重复性验证
- [ ] 从 clean environment 运行全部实验
- [ ] 验证所有图表可以从代码重新生成
- [ ] 验证所有数值结果一致

### Task 5.3: 外部审查准备
- [ ] Cover letter 撰写
- [ ] Suggested reviewers 列表
- [ ] 数据公开计划 (Zenodo/GitHub)

---

# PART C: 进度跟踪 (Progress Tracking)

## 里程碑

| 里程碑 | 目标日期 | 状态 | 描述 |
|--------|---------|------|------|
| M0 | Day 1-2 | ⬜ | 修复致命错误 |
| M1 | Day 3-5 | ⬜ | 理论框架强化 |
| M2 | Day 6-10 | ⬜ | 实验重设计与执行 |
| M3 | Day 11-13 | ⬜ | 代码质量提升 |
| M4 | Day 14-20 | ⬜ | 论文重写 |
| M5 | Day 21-23 | ⬜ | 质量验证 |

## 当前任务指针

**下一步行动**: Phase 0, Task 0.1 — 修复论文 Results 2.4 的内部矛盾

---

# PART D: 与当前草稿的具体差异 (Diff Summary)

## D.1 标题变更
- 旧: "Fundamental limits and scaling laws in heuristic quantum circuit optimization"
- 新: "Exponential Hardness of Quantum Circuit Optimization: Empirical Scaling Laws and Entanglement Thresholds"
- 理由: 更精确反映核心发现（指数衰减而非相变）

## D.2 核心论点变更
- 旧: 试图同时声称 "phase transition" 和 "no phase transition"
- 新: **明确主张**: 量子电路优化不存在 sharp phase transition，而是指数平滑衰减；这与 SAT 问题的行为根本不同，原因是量子电路的优化 landscape 具有连续而非离散的复杂度结构

## D.3 新增实验
- E6: 工业级编译器对比 (Qiskit, TKET)
- E7: 真实量子算法 benchmark
- E8: 噪声环境下的优化效果

## D.4 论文结构变更
- 新增: Theoretical Model 小节 (在 Results 之前)
- 新增: Comparison with Industrial Compilers 结果
- 新增: Real Algorithm Benchmarks 结果
- 重写: Algorithm Comparison (修复矛盾)
- 删除/弱化: FSS 分析 (R²=0.09 不应作为正面结果)

---

*本计划由 Hermes Agent 生成，可在模型切换后作为完整的进度恢复文档使用。*
*最后更新: 2026-05-30*
