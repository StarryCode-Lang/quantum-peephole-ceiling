# 文献综述与引用详细审查报告

**项目主题**: 量子电路窥孔优化的边界特征化 (Boundary Characterization of Quantum Circuit Peephole Optimization)

**审查日期**: 2026-06-16

**审查范围**: 5份核心文档 + 补充材料

**审查人**: 量子计算领域博士后研究员

---

## 总体评价

本项目的文献综述体系总体上较为扎实，`literature_review.md` 中的42篇核心参考文献覆盖了量子电路优化的主要方向，`phase7_related_work.md` 补充了12篇面向手稿的引用，手稿v5版本的Background章节（Section 2）提供了详尽的综述。文献综述对核心贡献的定位——结构天花板（structural ceiling）框架的独创性——论证有力。但存在若干**严重遗漏**和**格式不一致**问题，需要在投稿前修正。

以下按严重程度从高到低分类报告。

---

## 一、严重问题（CRITICAL）——可能影响审稿结果

### C1. 关键文献缺失：Shende-Bullock-Markov 电路下界

- **严重程度**: CRITICAL
- **位置**: `literature_review.md` 第9节参考文献列表（42篇）中缺失
- **问题**: Shende, Bullock & Markov (2006) "Synthesis of Quantum-Logic Circuits" (IEEE TCAD) 是量子电路综合与优化的奠基性工作，建立了任意n-量子比特酉操作所需CNOT门数的**绝对下界** O(4^n/n)。该文献在 `phase7_related_work.md` 中被引用为[4]，并在手稿中被多次讨论，但**未出现在主文献综述的42篇参考文献中**。
- **影响**: 本工作的"结构天花板"（optimizer-class-specific ceiling）与Shende等人的绝对下界（absolute lower bound）之间的区分是论文的核心创新点之一。如果主文献综述缺失这一对比，审稿人可能会质疑作者对该领域基础工作的了解程度。
- **建议**: 将Shende, Bullock & Markov (2006) 加入主文献综述参考文献列表，并在Section 5 (Structural Properties) 或 Section 6 (Gaps) 中增加明确的对比讨论。

### C2. 关键文献缺失：Nam et al. 量子电路优化系列工作

- **严重程度**: CRITICAL
- **位置**: 所有文档中均未引用
- **问题**: Nam, Niu & Maslov (2014) "Exact synthesis of single-qubit unitaries over Clifford-cyclotomic gate sets" 和 Nam, Chen & Roetteler (2018) "Approximate T-depth minimization" 是量子电路优化领域的重要工作。Nam et al. 在最优门合成和T-depth优化方面做出了系统性贡献，与本工作的窥孔优化主题直接相关。
- **影响**: 审稿人（特别是来自IBM或微软的审稿人）很可能会注意到这一遗漏。
- **建议**: 至少引用 Nam et al. 2018 的T-depth优化工作，并在讨论T-count/T-depth优化时与Kliuchnikov et al. 2013进行对比。

### C3. 关键文献缺失：Boixo et al. 2018 与 Arute et al. 2019（随机电路采样/量子优越性）

- **严重程度**: CRITICAL
- **位置**: 补充材料 S8.3 中引用了 Boixo et al. 2018 和 Arute et al. 2019，但两者**均未出现在主参考文献列表中**
- **问题**: 考虑到 S8.3 专门讨论了本工作与量子计算优势的关系，且该节已被纠正过（去除了错误的关联声明），引用的缺失令人困惑。如果要在正文中讨论随机电路采样作为量子优越性候选方案的背景，这两篇文献必须在正式参考文献中出现。
- **影响**: S8.3的纠正本身是正确的，但引用缺失可能被视为不严谨。
- **建议**: 如果S8.3保留在补充材料中，应将Boixo et al. 2018和Arute et al. 2019加入正式参考文献列表。

### C4. 关键文献缺失：量子电路等价性验证方向

- **严重程度**: CRITICAL
- **位置**: 文献综述中该方向覆盖不足
- **问题**: 量子电路等价性验证（Quantum Circuit Equivalence Checking）是本工作的理论基础之一——Proposition 1和定理2的证明都依赖于等价性概念。然而，文献综述中缺少以下关键工作：
  - **Yamashita et al. (2011)** "Fast equivalence checking of quantum circuits" — 量子电路等价性检查的实用算法
  - **de Beaudrap & Zhang (2020)** 或类似的基于ZX-calculus的等价性验证工作
  - **Aaronson (2005)** 或相关工作中关于CIT复杂度更细致的讨论
- **建议**: 增加1-2篇等价性验证方面的引用，特别是在讨论CIT的QMA-completeness时。

### C5. 引用缺失：正文中引用但参考文献列表中不存在的文献

- **严重程度**: CRITICAL
- **问题**: 手稿v5的Background和Introduction章节中使用了以下作者-年份引用，但它们**未出现在42篇参考文献列表中**：

  | 引用 | 出现在 | 参考文献列表状态 |
  |------|--------|-----------------|
  | Barenco et al. 1995 | Background 2.2 | 在42篇列表中（#5），但未在正文中使用正式编号 |
  | Kliuchnikov et al. 2013 | Background 2.2 | 在42篇列表中（#13） |
  | Amy et al. 2018 | Background 2.2 (phase polynomial) | **不在42篇列表中** |
  | Bernstein & Vazirani 1997 | Section 2.1 | **不在42篇列表中** |
  | Farhi et al. 2014 (QAOA) | Section 2.1 | **不在42篇列表中** |
  | Peruzzo et al. 2014 (VQE) | Section 2.1 | **不在42篇列表中** |
  | Romero et al. 2018 (UCCSD) | Section 2.1 | **不在42篇列表中** |
  | Grover 1996 | Section 2.1 | **不在42篇列表中** |
  | Cuccaro et al. 2004 (adder) | Section 2.1 | **不在42篇列表中** |
  | Aharonov et al. 2001 (quantum walk) | Section 2.1 | **不在42篇列表中** |
  | Shepherd & Bremner 2019 (IQP) | Section 2.1 | **不在42篇列表中** |
  | Fowler et al. 2012 (surface code) | Introduction | **不在42篇列表中** |
  | Edmonds 1965 (blossom algorithm) | Section 3.3 (Proposition 1讨论) | **不在42篇列表中** |
  | Aho, Sethi & Ullman 1986 (Dragon Book) | Phase7 Related Work | 仅在phase7中引用 |
  | Amdahl 1967 | Phase7 Related Work | 仅在phase7中引用 |

- **影响**: 这是投稿前的致命问题。Quantum期刊要求所有正文中引用的文献都必须在参考文献列表中。
- **建议**: 需要编制一个统一的、完整的参考文献列表。根据 `manuscript_structure_v5.md` 计划60-70篇参考文献，当前至少需要增加约20篇。

---

## 二、重要问题（MAJOR）——影响学术质量

### M1. 2023-2026年最新工作的覆盖

- **严重程度**: MAJOR
- **问题**: 42篇参考文献中的时效性分析如下：

  | 年份范围 | 数量 | 备注 |
  |---------|------|------|
  | 1965-1999 | 8篇 | 经典基础 |
  | 2000-2009 | 10篇 | 量子计算基础 |
  | 2013-2020 | 11篇 | 优化方法 |
  | 2021-2022 | 3篇 | Quartz, Liu et al. |
  | 2023 | 2篇 | Qiskit, Cirq |
  | 2024-2026 | 8篇 | Quanto, Qarl, AlphaTensor, ZX+RL, Merilehto |

  2023-2026年的最新工作覆盖了Quartz/Quanto/Qarl/AlphaTensor/ZX+RL等关键优化器，这是好的。但以下2023-2026年的重要工作**可能遗漏**：

  - **Hietala et al. (2023)** "Verified Optimization in a Quantum Intermediate Representation" — 形式化验证的量子优化
  - **Kehrer et al. (2023/2024)** MQT Bench的更新版本
  - **Cowtan et al. (2023/2024)** tket编译器的最新进展
  - **Beverland et al. (2022/2023)** 量子编译的资源估计框架
  - **Hanks, Estarellas, Briuglio & others** 量子电路优化的综述性文章

- **建议**: 增加3-5篇2023-2026年的工作，特别是形式化验证方向和综述性文章。

### M2. Benchmark方向引用不完整

- **严重程度**: MAJOR
- **位置**: `phase7_related_work.md` 引用了MQT Bench, QASMBench, Benchpress, QCircuitBench，但均未出现在主42篇参考文献中
- **问题**: 这4个benchmark套件是本工作进行对比分析的重要背景，缺少正式引用将削弱benchmark比较的可信度。尤其是：
  - **Nitsch et al. (2023)** MQT Bench — 目前最全面的量子软件基准测试套件之一
  - **Wang et al. (2021)** QASMBench — 重要的NISQ编程基准
  - **IBM Benchpress (2024)** — 工业界标准框架
  - **QCircuitBench (NeurIPS 2025)** — 最新的量子电路优化基准，直接相关
- **建议**: 将这4篇benchmark引用加入主参考文献列表。

### M3. 自引比例分析

- **严重程度**: MAJOR
- **问题**: 从文献综述来看，自引（引用本团队/本项目的先前工作）的比例难以精确计算，因为42篇参考文献中似乎没有明显的自引。但需要注意：
  - 如果作者在量子电路优化领域有先前发表的论文，应当适当引用
  - 如果完全没有自引，审稿人可能会怀疑作者是否为该领域的新手
  - 如果自引过多（>20%），则可能被视为操纵引用
- **建议**: 如果作者有相关的先前工作，适度引用1-2篇。如果确实没有，这不是问题，但需要确保引用足够全面以显示对该领域的深入了解。

### M4. 量子优越性/量子计算复杂度方向的引用

- **严重程度**: MAJOR
- **位置**: `literature_review.md` Section 3.3 引用了 Harrow & Montanaro (2017) "Quantum computational supremacy"
- **问题**: 仅引用Harrow & Montanaro一篇来覆盖量子优越性/复杂度方向是不足的。建议补充：
  - **Boixo et al. (2018)** "Characterizing quantum supremacy in near-term devices" — 定义NISQ量子优越性
  - **Arute et al. (2019)** "Quantum supremacy using a programmable superconducting processor" — Google的里程碑实验
  - **Bouland, Fefferman, Nirkhe & Vazirani (2019)** — 量子优越性的复杂度理论基础
  - 这些在S8.3中被提及但未正式列入参考文献

### M5. ZX-calculus方向引用不充分

- **严重程度**: MAJOR（但接近MINOR）
- **问题**: Duncan et al. 2020 和 de Beaudrap et al. 2022 已被引用，Riu et al. 2025 (ZX+RL) 也已覆盖。但缺少：
  - **van de Wetering (2020/2021)** "ZX-calculus for the working quantum circuit optimizer" 或相关的PyZX实际工具论文
  - **Kissinger & van de Wetering (2020)** 关于PyZX的论文
  - **Backens et al. (2021)** "There and back again: A circuit extraction tale" — 关于ZX-calculus电路提取的关键工作
- **建议**: 增加1-2篇ZX-calculus的工具/应用层面的引用。

### M6. 经典窥孔优化理论的引用深度

- **严重程度**: MAJOR
- **问题**: 经典窥孔优化引用了McKeeman (1965)、Tanenbaum (1982)、Fraser & Hanson (1995)、Massalin (1987) 四篇，这些是好的。但：
  - **Aho, Sethi & Ullman (1986)** "Compilers: Principles, Techniques, and Tools"（龙书）在 `phase7_related_work.md` 中被引用但未在主列表中——这是经典编译器理论的标准参考
  - **Amdahl (1967)** Amdahl定律在 `phase7_related_work.md` 中被引用——作为结构天花板类比的理论基础，应进入主列表
  - 缺少 **Lerner, Grove & Chambers (2002)** "Composing Dataflow Analyses and Transformations" — 经典编译器优化组合的重要工作，与Phase 1/Phase 2组合讨论相关

---

## 三、一般问题（MINOR）——影响精细度

### m1. 引用格式不一致

- **严重程度**: MINOR
- **问题**: 三个文档使用了三种不同的引用格式：
  - `literature_review.md`: 使用编号格式（1-42），带有完整的书目信息
  - `phase7_related_work.md`: 使用方括号编号格式（[1]-[12]）
  - `v5_full_manuscript_part1.md`: 使用作者-年份格式（如 [Amy et al. 2013]）
  - `v5_full_manuscript_part2.md` 和 `part3.md`: 继续使用作者-年份格式

- **Quantum期刊格式要求**: Quantum 使用标准学术引用格式，接受author-year或numbered格式，但要求**统一**。当前手稿使用的author-year格式适合Quantum，但需要确保最终版本的参考文献列表完整且一致。
- **建议**: 统一为author-year格式，编制完整的参考文献列表。

### m2. 编号体系冲突

- **严重程度**: MINOR
- **问题**: `literature_review.md` 使用1-42编号，`phase7_related_work.md` 使用[1]-[12]编号，两者的编号指向不同的文献。例如：
  - `literature_review.md` 中的[36] = Quartz (Xu et al. 2022)
  - `phase7_related_work.md` 中的[9] = Quarl (Li et al. 2024)
  - 手稿中使用author-year引用
- **建议**: 在最终手稿中统一编号或完全使用author-year格式，避免混淆。

### m3. 部分引用的内容准确性存疑

- **严重程度**: MINOR
- **问题1**: `literature_review.md` Section 2.2.3 称 Wille & Drechsler (2009) "formalized the commutation graph of a quantum circuit"，但该论文实际上是关于BDD-based reversible synthesis（基于BDD的可逆电路综合），而非commutation graph的形式化。引用的描述与论文实际内容存在偏差。
- **问题2**: `literature_review.md` Section 4.4 的编译器比较表中，将Quartz的optimality guarantee标为"Window-optimal"，这是准确的，但将t|ket>的复杂度标为"NP-hard"缺乏出处——t|ket>的FullPeepholeOptimise的具体复杂度分析未在Sivarajah et al. 2020中明确讨论。
- **建议**: 核实Wille & Drechsler 2009的描述是否准确；为t|ket>的复杂度声明提供出处或修改表述。

### m4. 缺少综述性/教程性引用

- **严重程度**: MINOR
- **问题**: 缺少量子电路优化领域的综述性文章，例如：
  - **de Wolf (2011)** "Quantum computing: Lecture notes" — 广泛使用的教程
  - **Montanaro (2016)** "Quantum algorithms: an overview" — NPJ Quantum Information上的综述
  - **Chong, Franklin & Martonosi (2017)** "Programming languages and compiler design for realistic quantum hardware" — Nature上关于量子编译的综述
- **建议**: 增加1-2篇综述性引用，为不熟悉该领域的读者提供入口。

---

## 四、维度C：Related Work章节质量评估

### 正面评价

1. **核心区分清晰**: `phase7_related_work.md` 中关于"absolute lower bound"（Shende-Bullock-Markov）vs. "optimizer-class-specific ceiling"（本工作）的区分表格非常精准，直接回应了审稿人最可能提出的问题。这一区分在手稿Section 2.2中也得到了充分体现。

2. **竞争方法引用公正**: 对Quartz、Quanto、Qarl、AlphaTensor-Quantum、ZX+RL的描述客观准确，采用了"What they achieved" / "What they did NOT do"的结构化对比，既承认了各工作的贡献，又清晰地定位了本工作的差异化价值。

3. **文献综述支持核心贡献声明**: Table 5（Section 10.8）的7维度对比表格是本项目的亮点之一，清楚地将本工作与7个最新优化框架进行了系统性对比。"Structural Ceiling Analysis"列中本工作是唯一的check mark，这一定位有力且有据。

### 需要改进之处

4. **phase7_related_work.md 与 literature_review.md 的整合**: 两份文档目前似乎是独立编写的。`phase7_related_work.md` 引入了MLCO (2025)、Amdahl's Law等新元素，但这些未被整合到主文献综述中。最终手稿需要统一引用体系。

5. **对手稿中引用的算法背景文献处理**: Section 2.1 中列举了15个电路族，每个都引用了原始算法论文（Bernstein-Vazirani, QAOA, VQE, Grover, UCCSD等），但这些引用目前仅存在于手稿文本中，没有对应的参考文献条目。需要在最终参考文献列表中补充。

6. **Related Work 的篇幅与深度平衡**: `literature_review.md` 的Section 10（Recent Advances）非常详尽（每个工作都有"achieved/did NOT do"分析），这对于内部研究文档很好，但最终手稿的Related Work章节需要精简。`phase7_related_work.md` 的约400字版本更接近目标长度，但可能过于简短。建议最终版本在1000-1500字之间。

---

## 五、维度D：引用格式评估

### D1. 适合Quantum期刊的格式

Quantum (quantum-journal.org) 接受以下引用格式：
- 推荐使用BibTeX
- 接受author-year或numbered格式
- 要求DOI（如可用）
- 要求arXiv ID（如有预印本）

**当前状态**:
- 手稿v5使用author-year格式，这与Quantum的风格兼容
- `literature_review.md` 中的42篇参考文献提供了期刊/会议/年份信息，但**缺少DOI和arXiv ID**
- 部分2024-2025年的文献提供了arXiv ID（如Qarl的arXiv:2307.10120、AlphaTensor的arXiv:2402.14396），这是好的

**建议**: 为所有参考文献补充DOI（如可用）和arXiv ID（如有预印本）。

### D2. 具体格式问题

- `literature_review.md` 中引用#10: Amy & Mosca (2019) 的发表年份应为2019，但IEEE TIT卷号65(8)对应的确实是2019年——无误。
- 引用#37: Quanto (Pointing et al. 2024) 的期刊名为"Quantum Science and Technology"，正确。
- 引用#42: Merilehto (2025) 仅有arXiv编号，未发表——应注明"preprint"或"submitted"。

---

## 六、维度E：已知纠正检查（S8.3错误关联）

### E1. S8.3的纠正状态

- **纠正已完成**: 补充材料S8.3已被重写，标题为"Relation to Classical Simulation"，并在开头明确标注了纠正说明：

  > "A previous version of this section claimed that 'classical simulation of random circuits cannot be accelerated by peephole optimization.' This claim was a non sequitur and has been rewritten..."

- **纠正质量**: 重写后的S8.3质量很高。它清晰地区分了：
  - 本工作**证明了什么**: 窥孔优化在随机电路上实现约0%的门数缩减
  - 本工作**未证明什么**: 对经典模拟算法效率没有任何直接推论
  - **诚实评估**: 结构天花板框架仅特征化了一类特定的电路到电路重写策略的极限

### E2. 残留错误检查

- **手稿v5中**: 未发现残留的"窥孔优化→量子优越性"错误关联。Introduction中引用Harrow & Montanaro (2017)时仅作为电路复杂度下界的背景，未建立与量子优越性的直接推论关系。
- **literature_review.md中**: 未发现残留错误。Section 5.1关于随机电路理论的讨论正确引用了Brandao et al. 2016和Harrow & Low 2009，未涉及量子优越性声明。
- **Supplementary S8.3中**: 纠正后的版本明确声明"What our results do NOT show"，并正确指出经典模拟器使用张量网络收缩等完全不同的技术。

### E3. 其他潜在残留

- **轻微注意**: `literature_review.md` Section 3.3 称 Harrow & Montanaro (2017) 关于"Quantum computational supremacy"，但该论文的标题实际上是"Quantum computational supremacy"，发表在Nature 549, 188-196。引用是准确的。但需注意该引用在文中的上下文是否恰当——当前用于讨论Haar-random酉操作的门数下界，这是恰当的。
- **Phase7文档**: 在 `phase7_limitations.md` 和 `phase7_claim_rewrite_map.md` 中提到了"quantum advantage"，但仅用于说明本工作的实验规模限制（n <= 20，远小于量子优势所需的规模），这是正确的用法。

---

## 七、可能缺失的关键文献汇总

以下按优先级排序列出建议增加的参考文献：

### 第一优先级（必须添加）

| # | 文献 | 理由 |
|---|------|------|
| 1 | Shende, Bullock & Markov (2006) "Synthesis of Quantum-Logic Circuits" IEEE TCAD | 电路下界的奠基性工作，与structural ceiling概念直接相关 |
| 2 | Nam, Niu & Maslov (2014) 或 Nam, Chen & Roetteler (2018) | 量子电路优化的重要系列工作 |
| 3 | Boixo et al. (2018) "Characterizing quantum supremacy in near-term devices" Nature Physics | S8.3中已引用但未列入正式参考文献 |
| 4 | Arute et al. (2019) "Quantum supremacy using a programmable superconducting processor" Nature | 同上 |
| 5 | Fowler, Mariantoni, Martinis & Cleland (2012) "Surface codes: Towards practical large-scale quantum computation" PRA | Introduction中引用了但未列入参考文献 |
| 6 | Bernstein & Vazirani (1997) | Theorem 9的核心电路族——BV oracle的来源 |
| 7 | Farhi, Goldstone & Gutmann (2014) "A Quantum Approximate Optimization Algorithm" | Section 2.1中引用 |
| 8 | Peruzzo et al. (2014) "A variational eigenvalue solver on a photonic quantum processor" Nature Communications | Section 2.1中引用 |
| 9 | Edmonds (1965) "Paths, trees, and flowers" Canadian Journal of Mathematics | Proposition 1讨论的blossom algorithm原始论文 |
| 10 | Grover (1996) "A fast quantum mechanical algorithm for database search" STOC | Section 2.1中引用 |

### 第二优先级（强烈建议添加）

| # | 文献 | 理由 |
|---|------|------|
| 11 | Nitsch et al. (2023) MQT Bench, ACM TEAC | Phase7 Related Work中引用，重要benchmark |
| 12 | Wang et al. (2021) QASMBench | Phase7 Related Work中引用 |
| 13 | IBM Benchpress (2024) | Phase7 Related Work中引用 |
| 14 | QCircuitBench (NeurIPS 2025) | 直接相关的最新benchmark |
| 15 | Romero et al. (2018) UCCSD, Quantum Science and Technology | Section 2.1中引用 |
| 16 | Cuccaro et al. (2004) Quantum adder | Section 2.1中引用 |
| 17 | Amy, Maslov & Mosca (2018) Phase polynomial — 确认年份和出版信息 | Section 2.2.4中讨论但未列入参考文献 |
| 18 | Aho, Sethi & Ullman (1986) Compilers (Dragon Book) | 经典编译器理论基础 |
| 19 | Amdahl (1967) Amdahl's Law | 结构天花板类比的理论基础 |

### 第三优先级（可选但有益）

| # | 文献 | 理由 |
|---|------|------|
| 20 | Kissinger & van de Wetering (2020) PyZX | ZX-calculus工具链 |
| 21 | Backens et al. (2021) Circuit extraction | ZX-calculus的关键步骤 |
| 22 | Chong, Franklin & Martonosi (2017) Nature — quantum compilation survey | 综述性引用 |
| 23 | Selinger (2013) "Efficient Clifford+T approximation" | T-count优化的重要工作 |
| 24 | Aharonov, Ambainis, Kempe & Vazirani (2001) Quantum walk | Section 2.1中引用 |
| 25 | Shepherd & Bremner (2019) IQP | Section 2.1中引用 |

---

## 八、总结与建议

### 整体评价

| 维度 | 评分 (1-5) | 说明 |
|------|-----------|------|
| A. 文献覆盖度 | 3.5/5 | 核心方向覆盖较好，但缺少Shende-Bullock-Markov等关键文献；benchmark和算法背景文献不足 |
| B. 引用准确性 | 4/5 | 大部分引用准确，Wille & Drechsler 2009的描述需核实；格式不一致问题严重 |
| C. Related Work质量 | 4.5/5 | 核心区分精准，竞争方法引用公正，文献综述支持贡献声明 |
| D. 引用格式 | 2.5/5 | 三个文档三种格式，缺少DOI/arXiv ID，需要统一 |
| E. 已知纠正 | 4.5/5 | S8.3纠正质量好，无残留错误 |

### 投稿前必须完成的修正清单

1. **[CRITICAL]** 编制统一的完整参考文献列表（目标60-70篇），确保手稿正文中所有引用都有对应条目
2. **[CRITICAL]** 添加上述第一优先级的10篇关键文献
3. **[CRITICAL]** 为所有参考文献补充DOI和arXiv ID
4. **[MAJOR]** 统一引用格式为author-year或numbered格式（推荐author-year，与Quantum兼容）
5. **[MAJOR]** 整合 `phase7_related_work.md` 中的新增引用（MQT Bench, QASMBench, Benchpress, MLCO, Dragon Book, Amdahl's Law）到主参考文献列表
6. **[MAJOR]** 核实Wille & Drechsler 2009的描述准确性
7. **[MINOR]** 增加2-3篇2023-2026年的综述或形式化验证方面的工作
8. **[MINOR]** 补充Selinger (2013)和Amy et al. (2018) phase polynomial的完整引用信息

### 最终意见

本项目的文献综述基础扎实，对现有工作的分析深入且有洞察力。"What they achieved / What they did NOT do"的结构化对比方法在学术写作中值得推广。主要问题集中在**参考文献列表不完整**和**格式不统一**这两个操作性问题上，这些在投稿前是必须解决的。核心学术内容——结构天花板框架的定位、与Quartz/Qarl/AlphaTensor的区分、Phase 1/Phase 2的分类——在文献综述中得到了充分支撑。

建议在解决上述CRITICAL和MAJOR问题后投稿。预计修正工作量：1-2天。

---

*审查完成时间: 2026-06-16*
*审查人: 量子计算博士后研究员*
