# Q-research 顶会/顶刊投稿优化计划

**版本**: v1.0  
**日期**: 2026-07-07  
**目标期刊/会议**: Quantum (quantum-journal.org) + IEEE Quantum Week (QCE) / TQC / DAC / ICCAD / ASP-DAC / DATE  
**优化目标**: 在论文写作前，将项目从"可投稿"提升至"顶会/顶刊 Best Paper 候选"水平（博士后级别、40+ 页完整论文）  
**制定依据**: 本项目全量文件审计 + 4 个并行研究代理对量子电路优化顶会标准、前沿论文、可复现性规范、理论-实验耦合规范的调研

---

## 1. 执行摘要

本项目已经具备了冲击顶会/顶刊的**核心科学贡献**和**大规模实验基础**：

- 53,300 条规范优化器试验 + 10,000 条 WCL/LBL 对比数据；
- 15 个真实电路族、6 种优化器、多编译器/多拓扑/多窗口的系统比较；
- 结构天花板（Structural Ceiling）框架 + Phase-1/Phase-2 层级理论；
- 诚实的自我修正流程（Phase-7/8 remediation）和 149 个通过的单元测试。

但与 Quantum / QCE / TQC / DAC 等顶会顶刊的"金标准"相比，项目在**数据溯源基础设施、理论-实验严格对齐、基准全面性、统计功效、可复现性包裹**等方面仍存在可感知的差距。

本计划将项目优化分为 **7 大流程、36 项重点任务、约 120 个可执行子任务**，覆盖从理论框架、实验设计、代码数据、统计分析、文献综述到投稿准备的完整科研链条。

---

## 2. 顶会/顶刊标准画像

### 2.1 目标 venue 特征

| Venue | 定位 | 页数 | 最看重 | 本项目当前匹配度 |
|---|---|---|---|---|
| **Quantum** | 开放获取顶刊 | 无严格限制 | 重大概念贡献、严格证明、清晰、可复现 | 高（理论-实验尚需对齐） |
| **IEEE QCE** | 量子系统工程旗舰会 | 8–10 页正文 | 可扩展工具、真实基准、开源实现 | 中（缺 Cirq/tket 完整基准） |
| **TQC** | 理论量子计算 | 15 页 LIPIcs | 数学严谨性、概念新颖性 | 中（需加强 Phase-2 形式化） |
| **DAC/ICCAD/ASP-DAC/DATE** | EDA/设计自动化 | 6–8 页 | 新算法、工程落地、强 baseline | 中（需补工业级 baseline） |

### 2.2 顶会论文的"金标准"清单

基于前沿论文调研（QUESO, Quarl, AlphaTensor-Quantum, VOQC, QuCLEAR, RL+ZX, PHOENIX, Benchpress 等），一篇能冲击 Best Paper 的量子电路优化论文应同时满足：

1. **基础洞察**：提出一个被精确定义、可验证的新概念（如 structural ceiling）；
2. **理论支撑**：有形式化定义、定理/引理、复杂度分类，且定理假设与实验严格对应；
3. **大规模、可复现实验**：使用标准化基准（MQT Bench / Benchpress / QUEKO / Qiskit Circuit Library），与至少 2–3 个 SOTA 编译器/优化器公平比较；
4. **统计严谨**：多重比较校正、效应量、置信区间、功效分析、足够随机种子；
5. **完整复现包裹**：Docker/Conda lock、版本控制、一键重跑、数据校验和、声明映射；
6. **诚实边界**：明确报告 null/负面结果、失败实验、理论-实验 regime 差异；
7. **开源工具化**：代码不仅是为了一篇论文，而是可作为社区工具；
8. **硬件或噪声视角**：即使是理想模型论文，也应讨论向真实设备迁移的局限。

---

## 3. 项目现状与差距分析

### 3.1 优势（Strengths）

| 维度 | 现状 | 顶会水准评估 |
|---|---|---|
| 核心科学问题 | "什么电路结构无法被窥孔优化，以及为什么" | 高；问题边界清晰 |
| 实验规模 | 53,300+ 试验、15 族真实电路、多优化器 | 高；超过多数同类论文 |
| 理论框架 | 12 定义、10 定理/引理、2 猜想 | 中高；Phase-1 天花板形式化较好 |
| 自我修正 | Phase-7/8 审计、FATAL/CRITICAL 问题清单 | 高；科学诚实度强 |
| 代码质量 | 149 单元测试通过、模块清晰 | 中高；测试覆盖可更细 |
| 统计分析 | BH-FDR、Cliff's delta、Bootstrap CI、功效分析 | 中；已实现但未充分报告 |

### 3.2 主要差距（Gaps）

| 差距类别 | 具体问题 | 顶会风险 | 优先级 |
|---|---|---|---|
| **数据溯源** | Release manifest 失效（哈希不匹配、引用不存在文件、dirty=true） | 可复现性质疑、 desk rejection | P0 |
| **理论-实验 regime 不匹配** | Theorem 8 适用于 Haar-随机酉，但实验使用浅层随机门序列 | 审稿人质疑核心结论普适性 | P0 |
| **理论未验证** | Theorem 6（AG canonical form）未测试；Theorem 7 构造未做实验 | 降低理论贡献可信度 | P1 |
| **基准不全面** | 缺少 MQT Bench、QUEKO、Benchpress 等行业基准；Cirq/tket 数据缺失 | 无法判断 practical impact | P0 |
| **统计功效不足** | E10/E11/E12 等每条件样本量过小，达不到 β≥0.80 | 结论脆弱、需补实验 | P1 |
| **Phase-2 形式化不一致** | Phase-2a 对易重写 vs Phase-2b 模板匹配定义混用 | 影响 Theorem 9 正确性 | P0 |
| **预测模型失败** | Held-out validation 完全失败（MAE=0.2775，Pearson=NaN） | 主要贡献崩塌风险 | P0 |
| **可复现性包裹** |  figures 仍为 PNG、无 Conda lock、路径硬编码、E20 仅 metadata | 审稿人难复现 | P1 |
| **文献覆盖** | 缺少 ~20 篇关键文献（Shende-Bullock-Markov、Nam et al.、ZX-calculus、最新 ML 优化器） | Related work 薄弱 | P1 |
| **噪声/硬件视角缺失** | 全部实验为 noiseless 理想模型，且未讨论迁移路径 | 在 QCE/DAC 被质疑现实意义 | P2 |
| **代码工程债务** | 硬编码路径、重复逻辑、死 API 字段、monolithic 测试 | 长期维护困难和可信度下降 | P2 |

---

## 4. 分流程优化计划

### 4.1 理论框架与形式化（Theory & Formalization）

#### 4.1.1 Phase-2 定义严格化

**目标**：消除 Phase-2a（commutation rewriting）与 Phase-2b（template matching）在形式化、实现、手稿中的混淆。

**行动项**：
- [ ] 在 `docs/theory/framework.md` 中新增一个独立小节，明确定义：
  - Phase-2a = 仅通过对易关系重排 gate 顺序以实现非相邻逆元相消；
  - Phase-2b = 使用模板/规则直接替换子电路（可改变 gate 计数和结构）；
  - Phase-3 = 全局优化（phase-polynomial、ZX、Clifford tableau、resynthesis）。
- [ ] 修改所有定理表述，明确标注 "Phase-2a" 或 "Phase-2b" 的适用范围：
  - Theorem 7（人工构造的 Phase-2b 优势）保持为 Phase-2b；
  - Theorem 9（BV Oracle）明确是 Phase-2b 模板匹配优势，并与 Phase-2a 的实验结果区分开；
  - 若 Phase-2a 对 BV 也有优势，需单独给出 Lemma 或 Theorem。
- [ ] 在 `docs/theory/formal_results.md` 中修正 C2：
  - 原表述："Phase 2 provides context-dependent super-constant improvement"；
  - 修正为："Phase-2b template matching can provide Ω(1) advantage over Phase-1/Phase-2a on certain circuit families; Phase-2a commutation rewriting provides O(1) small gains."
- [ ] 修改 `src/optimisation/phase2/commutation_rewriter.py` 的 docstring 和类型名，统一使用 `Phase2aCommutationRewriter`。
- [ ] 修改 `src/optimisation/phase2/template_matcher.py`，将类名改为 `Phase2bTemplateMatcher`。

**验收标准**：
- 全文检索 "Phase 2" 出现处，每个都有明确后缀 a/b/3；
- 无审稿人能从形式上挑出 Phase-2 范畴混淆的问题。

#### 4.1.2 Theorem 8 Regime 问题处理

**问题**：Theorem 8 讨论 Haar-随机酉的不可压缩性，但实验是浅层随机门序列，两者 regime 不同。

**行动项**：
- [ ] 在 `docs/theory/framework.md` 和 `docs/manuscript/manuscript.md` 中新增 "Regime mismatch and scope" 小节：
  - 承认 Theorem 8 的 Haar-随机酉假设；
  - 明确实验电路生成器（`generator_v2.py` 中的 `UniversalGenerator`、`CliffordGenerator`）产生的是浅层随机门序列，不是 Haar 样本；
  - 给出两者关系的讨论：浅层随机序列是否/何时近似 unitary design？
- [ ] 补充引用关于 "random circuits as approximate unitary designs" 的文献（如本计划末尾参考 [5]）。
- [ ] 若可能，设计一个小实验验证：对同一 n，比较 Haar 采样电路与浅层随机电路的 Phase-1 可压缩性差异。
- [ ] 将 Theorem 8 的表述弱化或重新定位：从"解释实验"改为"给出最坏情况/渐近上限"。

**验收标准**：
- 手稿中明确出现一句话："Theorem 8 applies to Haar-random unitaries, which is a different regime from the shallow random gate sequences used in E1–E5; we therefore treat it as an asymptotic worst-case bound rather than an explanation of the experimental data."

#### 4.1.3 Theorem 6 验证

**目标**：将 Theorem 6（Aaronson-Gottesman canonical form 下 Clifford 电路 Phase-1 天花板精确）从未验证提升为已验证。

**行动项**：
- [ ] 实现 AG canonical form 电路生成器（`src/circuits/ag_canonical.py`）；
- [ ] 编写实验 E23：在 AG canonical form 电路上运行 Phase-1 Greedy，验证 reduction 是否等于理论值；
- [ ] 将结果写入 `data/v7/e23/` 和 `docs/results/analysis_summary.md`；
- [ ] 更新 `docs/theory/formal_results.md` 中 Theorem 6 的标注为 "Empirically validated"。

**验收标准**：
- 至少 100 个 AG canonical form 电路通过验证，匹配率 ≥95%。

#### 4.1.4 Theorem 7 实验实例化

**目标**：将 Theorem 7 的人工构造电路族实例化并实验验证。

**行动项**：
- [ ] 从 `docs/theory/formal_results.md` 提取 Theorem 7 的构造细节；
- [ ] 在 `src/circuits/hardness_families.py` 中实现该构造；
- [ ] 设计实验 E24：比较 Phase-1/Phase-2a/Phase-2b 在该族上的 reduction；
- [ ] 验证实测 reduction 是否达到理论下界 Ω(1)。

**验收标准**：
- 实验数据支持 Theorem 7 的 Ω(1) Phase-2b 优势。

#### 4.1.5 复杂度分类补强

**目标**：提升复杂度讨论的严谨性。

**行动项**：
- [ ] 在 `docs/theory/framework.md` 中：
  - 引用并讨论 CIT 的 QMA-complete 经典结果；
  - 明确 CODP 的 QMA-hardness 仍为猜想，避免给出误导性表述；
  - 补充参数化复杂度（parameterized complexity）讨论。
- [ ] 引入 "circuit unoptimization" 文献（Phys. Rev. Research 7, 023139）作为反面视角，说明优化器边界研究的学术价值。

---

### 4.2 实验设计与数据（Experiments & Data）

#### 4.2.1 修复 Release Manifest

**目标**：使 manifest 成为可信赖的数据溯源文件。

**行动项**：
- [ ] 清理所有未提交修改 → `git commit`；
- [ ] 重新运行 `scripts/generate_release_manifest.py`，确保 `dirty=false`；
- [ ] 手动校验 manifest 中每个 CSV/代码文件的 SHA256 与实际文件一致；
- [ ] 将 `new_families_heldout.csv` 和 `qiskit_pass_isolation.csv` 纳入 manifest；
- [ ] 将 manifest 校验加入 CI（`.github/workflows/ci.yml`）。

**验收标准**：
- `python scripts/reproduce_all.py --verify` 100% 通过。

#### 4.2.2 完成 Cirq / t|ket\> 多编译器比较（E20）

**目标**：从 Qiskit-only 提升到多编译器比较。

**行动项**：
- [ ] 完成 `experiments/e20_multi_compiler_full/run.py`，生成完整 CSV；
- [ ] 统一所有编译器的优化等级/目标（basis gate set、coupling map）；
- [ ] 对每个编译器记录：版本、优化参数、运行时间、输出 gate count/depth/T-count；
- [ ] 设计公平比较：相同 timeout、相同输入格式（QASM）、相同输出 metric；
- [ ] 将 E20 结果纳入 `analysis/generate_figures.py`。

**验收标准**：
- E20 CSV ≥ 500 行，覆盖 Qiskit/Cirq/tket/custom；
- 手稿 L3/L8 从 "Limitation" 升级为 "Result"。

#### 4.2.3 引入行业标准基准

**目标**：让实验结果能被 QCE/DAC/ICCAD 审稿人认可。

**行动项**：
- [ ] 接入 **MQT Bench**（若依赖复杂，至少选取代表性子集）：
  - 生成 QASM 输入，用自定义优化器 + Qiskit O3 处理；
- [ ] 接入 **QUEKO / QBench** 子集（已知近最优成本的电路）；
- [ ] 接入 **Benchpress** 测试子集（若可行）；
- [ ] 新增实验 E25：在行业标准基准上的 reduction 与 Qiskit/tket 对比。
- [ ] 为每个新增基准维护一个 `data/v7/e25/` 目录和 `metadata.json`。

**验收标准**：
- 至少新增 3 个标准基准来源；
- 手稿中出现 "We evaluate on MQT Bench, QUEKO, and the Qiskit Circuit Library..." 的表述。

#### 4.2.4 提升统计功效

**目标**：关键假设的检验功效 β ≥ 0.80。

**行动项**：
- [ ] 对 E10/E11/E12 重新做功效分析（power analysis），明确当前每条件样本量；
- [ ] 扩展 E10：每条件 N 从 9 提升到 ≥30（若效应量中位数，N=30 可达 β≈0.80）；
- [ ] 扩展 E11：每族样本从 ~24 提升到 ≥50；
- [ ] 扩展 E12：每优化级别每族样本 ≥30；
- [ ] 重新生成 canonical 数据，更新 `DATA_CANONICAL.md`。

**验收标准**：
- 主要假设（H1–H6）经事后或事前功效分析，β ≥ 0.80；
- `docs/results/experimental_design.md` 中记录样本量计算依据。

#### 4.2.5 完成 E21 Ceiling-Aware Optimizer 全量验证

**目标**：将 smoke-only 的 E21 提升为 full-mode 实验证据。

**行动项**：
- [ ] 运行 `experiments/e21_ceiling_aware/run.py --mode full`；
- [ ] 扩展电路族到 15 个真实族；
- [ ] 记录 speedup、reduction loss、正确性（fidelity）三项指标；
- [ ] 与 naive pipeline 做配对 t 检验 / Wilcoxon 检验。

**验收标准**：
- E21 CSV ≥ 1000 行；
- ceiling-aware 在保持 fidelity 前提下显著减少运行时间。

#### 4.2.6 处理 E18 幸存者偏差

**目标**：诚实地报告 Clifford+T 实验的失败率。

**行动项**：
- [ ] 在 `analysis/generate_figures.py` 中保留 `status` 列分析；
- [ ] 新增图表展示 E18 的失败率按 circuit family 分布；
- [ ] 在手稿 Limitations 和 Results 中明确说明："44.4% of E18 rows had decompose_error or fidelity=0 and were excluded; results are conditional on successful decomposition."

#### 4.2.7 重跑并归档 v1 buggy 数据

**目标**：明确区分 buggy v1 和 fixed v2 数据。

**行动项**：
- [ ] 确认 `archive/old_data/` 存在且 README 说明其状态；
- [ ] 在 `DATA_CANONICAL.md` 顶部加入警告："v1 data used a buggy `_are_inverse()`; do not use for publication."

---

### 4.3 代码与工程（Code & Engineering）

#### 4.3.1 消除硬编码路径

**行动项**：
- [ ] 修复 `scripts/phase5_feature_extraction.py`、`phase5_ceiling_analysis.py`、`phase5_optimize_or_skip.py` 中的 `D:\Desktop\Q-research` 硬编码路径；
- [ ] 统一使用 `Path(__file__).resolve().parents[2]` 或项目根目录环境变量 `QRESEARCH_ROOT`；
- [ ] 新增 `src/config.py` 集中管理路径。

#### 4.3.2 统一真实电路生成器

**问题**：`run_expanded.py`、`run_phase2b.py`、`run_real_variance.py` 中重复实现了 `make_qft` 等函数。

**行动项**：
- [ ] 将 `make_qft`、`make_ghz`、`make_bv` 等统一迁移到 `src/circuits/real_benchmarks.py`；
- [ ] 实验脚本只调用 `generate_real_circuit_suite()` 和 `make_*` 函数；
- [ ] 删除重复代码。

#### 4.3.3 修复 Phase-2 模板匹配器

**行动项**：
- [ ] 扩展 `Phase2bTemplateMatcher` 支持 H 在 target qubit 的情况；
- [ ] 增加更多 Clifford 模板（如 `S-S†`、`CZ-CZ`、Hadamard 消去等）；
- [ ] 在 `tests/test_phase2b_template_matcher.py` 中补充对应测试。

#### 4.3.4 合并重复的 commutation/self-inverse 逻辑

**行动项**：
- [ ] 将 `_gates_commute`、`_is_self_inverse_pair` 统一放在 `src/optimisation/_gate_predicates.py`；
- [ ] `BaseOptimizer` 继承或委托给公共实现；
- [ ] 确保 numeric commutation fallback 在所有调用点可用。

#### 4.3.5 完善依赖与锁定

**行动项**：
- [ ] 将 `scikit-learn` 加入 `requirements.txt` 和 `environment.yml`；
- [ ] 生成 `requirements-lock.txt`（或 Conda lockfile），记录精确版本；
- [ ] 新增 `Dockerfile` 构建测试，确保 `docker build` 成功。

#### 4.3.6 测试拆分与扩展

**行动项**：
- [ ] 将 `tests/test_core.py` 拆分为：
  - `test_circuit_generation.py`
  - `test_optimizers.py`
  - `test_commutation.py`
  - `test_phase2b.py`
  - `test_provenance.py`
- [ ] 为 `RandomLocalSearch`、`SimulatedAnnealing`、`GeneticAlgorithm` 增加种子可复现性测试；
- [ ] 修复 `test_statistical_analysis.py` 中的重复定义和外部导入问题。

---

### 4.4 统计分析与报告（Statistics & Reporting）

#### 4.4.1 完整报告效应量

**行动项**：
- [ ] 在 `analysis/generate_figures.py` 中调用 `analysis/phase1_statistics/effect_size.py` 生成 Cliff's delta / Hedges' g；
- [ ] 在图注/表中同时报告 p 值、效应量、95% CI；
- [ ] 修改 `docs/results/experimental_design.md` 中的统计协议，明确效应量要求。

#### 4.4.2 统一随机种子与方差估计

**行动项**：
- [ ] 对 E4 等随机优化器实验，使用 ≥10 个独立种子；
- [ ] 报告均值 ± 标准差或 95% CI，而非单点值；
- [ ] 在 `PROJECT_SUMMARY.md` 更新"随机种子"策略。

#### 4.4.3 重命名/降级预测模型

**行动项**：
- [x] 将 "Universal Predictive Law" 改为 "Empirical Correlation Model"；
- [x] 在手稿中诚实报告 held-out validation 失败（MAE=0.2775，Pearson=NaN）；
- [x] 若保留该模型，仅作为 exploratory observation，不列为核心贡献。

---

### 4.5 可复现性包裹（Reproducibility Package）

#### 4.5.1 Docker 与 Conda lock

**行动项**：
- [ ] 更新 `Dockerfile`，使其包含完整依赖并可运行全部实验；
- [ ] 生成 `conda-lock.yml` 或 `requirements-lock.txt`；
- [ ] 在 README 中增加 "Reproducing in Docker" 小节。

#### 4.5.2 矢量图与 Figure 规范

**行动项**：
- [ ] 将 `analysis/figures/` 中的 PNG 全部替换为 PDF/SVG；
- [ ] 更新 `analysis/generate_figures.py` 默认输出 `*.pdf`；
- [ ] 统一 figure 字体、字号、配色（建议使用色盲友好调色板）。

#### 4.5.3 声明-证据映射表

**行动项**：
- [ ] 在 `docs/manuscript/appendix.md` 基础上扩展为 `docs/06_manuscript/claim_evidence_table.csv`；
- [ ] 每行包含：Claim ID、手稿位置、实验/定理证据、代码脚本、数据文件、限制/警告。

#### 4.5.4 一键重跑脚本

**行动项**：
- [ ] 增强 `scripts/reproduce_all.py`，支持：
  - `--stage theory`：验证定理 1/2/6/7/9；
  - `--stage experiments`：运行 canonical 实验；
  - `--stage figures`：生成所有 figure；
  - `--stage verify`：校验 manifest 和数据；
- [ ] 在 CI 中运行 smoke 版本的 `reproduce_all.py`。

---

### 4.6 文献综述（Related Work）

#### 4.6.1 补充关键文献

**必须补充的文献类别**：
- 经典 CNOT 下界与最优门合成：**Shende-Bullock-Markov (2006)** 系列；
- 量子电路最优综合：**Nam et al. (2018)** / *Optimizing Quantum Circuits for General Gate Sets*；
- 等价性验证：**Yamashita et al. (2011)**、VOQC、参数化电路等价检查；
- ZX-calculus 与 PyZX；
- 最新 ML/RL 优化器：QUESO、Quarl、AlphaTensor-Quantum、RL+ZX；
- 多编译器基准：Benchpress、MQT Bench、QUEKO；
- 量子电路反优化（Circuit Unoptimization）作为边界研究参考。

#### 4.6.2 统一引用格式

**行动项**：
- [ ] 将所有引用合并到 `docs/references/unified_references.md`；
- [ ] 统一使用 `[Number]` 格式；
- [ ] 补充 DOI / arXiv ID；
- [ ] 在 LaTeX 写作时使用 `.bib` 文件导出。

---

### 4.7 手稿结构与写作（Manuscript）

#### 4.7.1 手稿结构调整

建议采用以下结构（40+ 页）：

1. **Abstract**（250 词）
2. **Introduction**（4 页）
   - 背景与动机
   - 当前优化器的局部性局限
   - 我们的问题：结构天花板
   - 贡献列表
3. **Related Work**（4 页）
4. **Preliminaries and Definitions**（3 页）
5. **Theoretical Framework**（6 页）
   - Phase-1 ceiling
   - Phase-2a/2b separation
   - Complexity classification
6. **Methodology**（4 页）
   - Optimizers
   - Circuit families
   - Metrics
7. **Experimental Design**（4 页）
   - Hypotheses
   - Statistical protocol
8. **Results**（8 页）
   - Random circuits
   - Real circuits
   - Compiler comparison
   - Ceiling-aware optimizer
9. **Discussion & Limitations**（3 页）
10. **Conclusion & Future Work**（2 页）
11. **Supplementary Materials**（10+ 页）

#### 4.7.2 摘要与贡献精炼

**建议贡献点**：
1. 提出并形式化"结构天花板"概念，证明/验证 Phase-1 在 LBL/WCL 下的极限；
2. 首次大规模系统比较 Phase-1、Phase-2a、Phase-2b 与 SOTA 编译器；
3. 建立 listing model 敏感性的理论与实验联系；
4. 提出 ceiling-aware optimizer 并在真实电路族上验证加速效果；
5. 诚实报告优化器边界、失败实验和 regime 限制。

---

### 4.8 投稿准备（Submission）

#### 4.8.1 选择投稿路径

建议顺序：
1. **Quantum** 首投（最匹配理论-实验混合、开放科学）
2. 若被拒或需要更 engineering 的 venue，转 **IEEE QCE (QSYS track)**
3. 若理论分量进一步加强，可投 **TQC**

#### 4.8.2 附件材料

**提交时必须附带**：
- [ ] 完整代码仓库（GitHub / Zenodo DOI）；
- [ ] 数据可用性声明；
- [ ] Docker/Conda 环境文件；
- [ ] 补充材料（完整实验参数、统计表、证明细节）；
- [ ] 视频或在线 appendix（可选但加分）。

---

## 5. 可执行任务清单（Master Task List）

### 5.1 立即执行（P0，投稿前必须完成）

| 序号 | 任务 | 负责人 | 依赖 | 预计工时 | 状态 |
|---|---|---|---|---|---|
| T1 | 清理 git 工作树，生成干净 commit | 学生/作者 | 无 | 2h | ⬜ |
| T2 | 修复并重新生成 release manifest | 学生/作者 | T1 | 4h | ⬜ |
| T3 | 完成 Cirq/tket 多编译器实验（E20） | 学生/作者 | T2 | 16h | ⬜ |
| T4 | 将 Phase-2a/2b 定义严格化并改代码/文档 | 学生/作者 | 无 | 8h | ⬜ |
| T5 | 处理 Theorem 8 regime mismatch（加讨论/实验） | 学生/作者 | 无 | 6h | ⬜ |
| T6 | 重命名/降级预测模型，诚实报告 held-out 失败 | 学生/作者 | 无 | 4h | ⬜ |
| T7 | 修复 `DATA_CANONICAL.md` 中 E10 路径错误 | 学生/作者 | T2 | 1h | ⬜ |
| T8 | 将 figures 从 PNG 转为 PDF/SVG | 学生/作者 | T2 | 4h | ⬜ |
| T9 | 修复硬编码路径 | 学生/作者 | 无 | 3h | ⬜ |
| T10 | 生成 Conda lock 文件 / 完善 Dockerfile | 学生/作者 | T9 | 4h | ⬜ |

### 5.2 短期执行（P1，显著提升顶会竞争力）

| 序号 | 任务 | 负责人 | 依赖 | 预计工时 | 状态 |
|---|---|---|---|---|---|
| T11 | 验证 Theorem 6（AG canonical form 实验 E23） | 学生/作者 | T10 | 12h | ⬜ |
| T12 | 实例化并验证 Theorem 7（E24） | 学生/作者 | T10 | 12h | ⬜ |
| T13 | 提升 E10/E11/E12 样本量至 β≥0.80 | 学生/作者 | T10 | 24h | ⬜ |
| T14 | 完成 E21 ceiling-aware full-mode 实验 | 学生/作者 | T10 | 16h | ⬜ |
| T15 | 引入 MQT Bench / QUEKO / Benchpress 基准（E25） | 学生/作者 | T10 | 20h | ⬜ |
| T16 | 扩展 Phase-2b 模板库 | 学生/作者 | T4 | 12h | ⬜ |
| T17 | 补充 ~20 篇关键文献并统一引用格式 | 学生/作者 | 无 | 16h | ⬜ |
| T18 | 完整报告效应量（Cliff's delta / Hedges' g） | 学生/作者 | 无 | 8h | ⬜ |
| T19 | 拆分 monolithic 测试文件 | 学生/作者 | 无 | 8h | ⬜ |
| T20 | 编写 claim-evidence 映射表 | 学生/作者 | 无 | 6h | ⬜ |

### 5.3 中期执行（P2，冲击 Best Paper）

| 序号 | 任务 | 负责人 | 依赖 | 预计工时 | 状态 |
|---|---|---|---|---|---|
| T21 | 加入噪声/硬件拓扑敏感性实验 | 学生/作者 | T15 | 24h | ⬜ |
| T22 | 实现 OpenQASM 3.0 输入/输出支持 | 学生/作者 | T10 | 16h | ⬜ |
| T23 | 开发可视化 dashboard 或 web appendix | 学生/作者 | T20 | 20h | ⬜ |
| T24 | 申请 Zenodo DOI 并准备 artifact badge | 学生/作者 | T10 | 4h | ⬜ |
| T25 | 邀请外部 reviewer 预评审 | 导师/合作者 | T20 | 8h | ⬜ |
| T26 | 完成 LaTeX 模板适配与格式检查 | 学生/作者 | T17 | 8h | ⬜ |

---

## 6. 时间线建议

| 阶段 | 时间 | 产出 |
|---|---|---|
| **P0 修复** | 第 1–2 周 | 干净 manifest、修正 Phase-2 定义、修复路径、矢量 figures |
| **P1 补强** | 第 3–6 周 | E20/E21/E23/E24/E25 数据、统计效应量、文献补充、测试重构 |
| **手稿写作** | 第 7–9 周 | 40+ 页完整论文 + supplementary |
| **内部评审** | 第 10 周 | 预评审报告、返修 |
| **投稿** | 第 11 周 | 提交至 Quantum / QCE / TQC |

---

## 7. 验收标准（Definition of Done）

### 7.1 硬性门槛
- [ ] `python scripts/reproduce_all.py --all` 在干净环境中通过；
- [ ] Release manifest `dirty=false`，所有文件 SHA256 匹配；
- [ ] 149+ 单元测试通过，新增测试 ≥30 个；
- [ ] 所有 figures 为矢量格式（PDF/SVG）；
- [ ] 主要假设 β≥0.80 或明确说明不足；
- [ ] Phase-2a/2b/3 定义全文一致；
- [ ] 无硬编码绝对路径；
- [ ] 引用 ≥80 篇且格式统一。

### 7.2 软性门槛
- [ ] 论文可被外部 reviewer 在 2 小时内理解核心贡献；
- [ ] 每个核心 claim 都有对应的实验/定理/数据文件；
- [ ] 负面/失败结果被诚实讨论；
- [ ] 代码仓库可被社区复用。

---

## 8. 风险提示

1. **时间风险**：E20/E21/E25 需要大量编译器运行时间，建议尽早开始并使用高性能计算资源。
2. **依赖风险**：pytket / Cirq 版本可能与 Qiskit 冲突，建议用独立 Conda 环境或 Docker 隔离。
3. **理论风险**：Theorem 8 regime mismatch 若无法完全弥合，需调整论文叙事，避免审稿人认为核心结论不成立。
4. **学术诚信风险**：必须移除任何未实际运行实验的"详细结果"，包括 E19/E20/E21 在手稿中的 preliminary 数据。

---

## 9. 参考文献（关键顶会/顶刊论文与标准）

1. **Xu et al.**, "Synthesizing Quantum-Circuit Optimizers", PLDI 2023.  
2. **Li et al.**, "Quarl: A Learning-Based Quantum Circuit Optimizer", OOPSLA 2024.  
3. **Ruiz et al.**, "Quantum Circuit Optimization with AlphaTensor", Nature Machine Intelligence 2025.  
4. **Hietala et al.**, "A Verified Optimizer for Quantum Circuits", TOPLAS 2023.  
5. **Random unitaries in extremely low depth**, arXiv:2407.07754 (for regime discussion).  
6. **Benchpress team**, "Benchmarking Quantum Software", arXiv:2409.08844.  
7. **QuCLEAR**: Clifford Extraction and Absorption, arXiv:2408.13316.  
8. **Riu et al.**, "Reinforcement Learning Based Quantum Circuit Optimization via ZX-Calculus", Quantum 2025.  
9. **PHOENIX**, Pauli-Based High-Level Optimization, DAC 2025.  
10. **Multilevel Circuit Optimization**, arXiv:2505.09320.  
11. **Quantum circuit unoptimization**, Phys. Rev. Research 7, 023139 (2025).  
12. **Shende, Bullock & Markov**, "The minimal Toffoli gate count", 2006.  
13. **Nam et al.**, "A cost model for quantum circuit optimization", 2018.  
14. **Yamashita et al.**, "Equivalence checking of quantum circuits", 2011.  
15. **Quantum journal author/referee instructions**: https://quantum-journal.org/instructions/  

---

**备注**：本计划应与 `docs/COMPREHENSIVE_REVIEW_REPORT.md` 中的 FATAL/CRITICAL/HIGH 问题清单交叉使用。建议每完成一项任务就在本计划对应条目打勾，并定期更新进度。
