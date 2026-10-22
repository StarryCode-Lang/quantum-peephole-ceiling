# Innovation Scan — Quantum Peephole Ceiling（2026-10-19）

**范围**：科研全流程体检（论文撰写除外）+ 创新方向扫描，目标是把项目提升到
Nature/Science 级别的科学水平。
**约束**：`data/`、`release/` 未修改；`docs/manuscript/` 只读；本轮新建的所有
证据性文件均带日期与来源；未删除任何冻结或哈希绑定的文件。

**本轮与前三轮（10-16 / 10-17 / 10-18）的差别**：前三轮主要是"读 + 提议"，本轮
**执行了一个决定性实验（E47）**，其结果是负面的——它推翻了 v15 头条数字的一部分。
因此本轮的结论不是"再加一个方向"，而是"先改口径，再改框架"。

---

## 0. 执行摘要

1. **v15 的"65 个精确局部最优"是三个数混在一起报的**：96 个真实源（E39）+ 32 个
   代价 1–2 的 oracle fixture（E44）。32 个 fixture 全部被分类为"局部最优"，
   因为任何 1 门电路都没有单步削减空间。真实局部最优是 **33/96**，真实逃逸率是
   **63/96 = 65.6%**，而不是头条的 63/128 = 49.2%。

2. **h=3 的"局部最优"对多数真实源是错的，不是"弱"**。在完全相同的资源契约下
   （200k 状态 / 30s / `e44_core_v1`），把视野抬到 h=4 就有 6/33 真实源出现逃逸；
   抬到 h≤7，**19/33（57.6%）** 存在严格更便宜、可重放、且**数值幺正等价**的电路。
   19/19 通过逐步重放与全局幺正比对（`escape_verification.csv`）。

3. **BV 族给出一个可证明的视野障碍**。6 个 BV 源的最短改进路径长度为 **4**，而库内
   单步最大削减是 **2 门**。因此任何 H≤3 的搜索**在原理上**都看不见该改进，与预算
   无关。这解释了为什么"再多算也算不出来"——不是算力问题，是视野阶数问题。

4. **"genuine structural ceiling" 只剩两个家族站得住**。SurfaceCode 8/8、GHZ 1/1
   在 h≤7 下没有改进；**QFT 失守**（34→33，h=5 首次改进）。

5. **文献侧出现一个正好命中项目软肋的新工作**：`2609.20873 The Refutation Gap`
   （2026-09-16）指出电路最小化的"最优性否证半部"至今没有可检验产物，并给出
   DRAT + 第三方 checker 的完整流水线。项目的 34 个 witness-bounded 与 65 个
   local optimum 正落在该缺口里。同批还有 3 篇零覆盖的关键论文（见 §5.3）。

**一句话判断**：项目现在最该做的不是"补 34 个单元"，也不是"上真机"，而是把
**horizon 从隐藏参数变成显式坐标**，并把"局部最优"从搜索结论改写成可检验的否证
证书。这两件事都能在本地完成，且都是主刊级方法学增量。

---

## 1. 事实基线（2026-10-19 复核）

### 1.1 逐项读过的证据链

| 层 | 文件 | 复核结论 |
|---|---|---|
| 总览 | `README.md` | 128/128 分类、94 精确 best cost、34 witness-bounded、E46 76,236 窗口 0 截断；自述 `NOT_READY_FOR_PAPER` |
| 状态 | `docs/PROJECT_STATUS.md`（2026-10-11 快照） | 12 项关闭、3 项外部开放、1 项 bounded |
| 论文 | `docs/manuscript/manuscript.md`（1477 行，只读） | §6.12 记录 v15；§7.5 列 20 条 limitation；§7.6 列 10 条 future work |
| 理论 | `docs/theory/framework.md` v5.4.2 | Thm 2(b)/2d/5/6/8 已撤回或收窄；现存仅初等结构结果 + Thm 7/9 构造 |
| 数据 | `data/DATA_CANONICAL.md` v2.4.0 | 37 数据集 / 96,289 行；35 活跃（96,205）；15 条 Known Issue |
| 文献 | `docs/references/unified_references.md` v2.2 | [1]–[94]；另有 10-17 的 [95]–[112] 增补（未合并，因路径绑定） |
| 判据 | `release/v15_readiness_verdict.json` | `NOT_READY_FOR_PAPER`；`external_cold_start` / `real_qpu` / `release_authority` = OPEN |

### 1.2 四个已知差距的逐条核验（直接读 JSON，不转述）

| 差距 | 声明 | 本轮核验 | 结论 |
|---|---|---|---|
| G1 | 34 个长 listing 逃逸单元只有 witness-bounded | `certificate_tiers` = {34, 1, 93}，合计 128；`exact_best_cost_count` = 94 | **确认**，但见 §3：问题不在"没算完" |
| G2 | 无真实 QPU | `scientific_gates.real_qpu` = `OPEN`；EHW 是 fake backend 噪声模型 | **确认** |
| G3 | 无独立冷启动 | `external_cold_start` = `OPEN`；`docs/verification/cold_start_protocol.md` 已在 10-18 改为 Git-pinned 传输 | **确认**，协议现已可执行 |
| G4 | 无 external execution gate | `release_authority` = `OPEN`；`scripts/verify_prepaper_release_manifest.py` **仍然失败**（`docs/review/metric_audit_ledger_2026-08-24.csv` 字节/哈希不匹配） | **确认且恶化**：连续第三次复现，见 §4.4 |
| G5 | 理论撤稿后仅剩初等结果 | framework.md 审计注释与 `formal_results.md` 一致；Thm 5 在 10-17 已给出修复方案（5-A/5-B 有效，5-C 待证） | **确认**，修复路径已存在 |

### 1.3 本轮复核发现的口径问题（新）

v15 verdict 的 `classified_count: 128` 与 `local_optimum_count: 65` 都是**面板合并
后的数**，但面板本身是异质的：

| 来源 | 数量 | baseline cost | 分类结果 |
|---|---:|---|---|
| `e39`（真实电路开发网格） | 96 | 0 – 12,422（中位 86） | 63 escape / 33 local optimum |
| `e44`（certified-landscape oracle 夹具） | 32 | 1 – 2 | 32 local optimum / 0 escape |

e44 的 32 个源代价全部 ≤ 2，**没有任何单步可削减空间**，"局部最优"是构造使然，
不构成关于电路的科学陈述。把它计入 65 会系统性夸大"不可优化"的比例。
建议的报法（不改冻结数据，只改叙述）：

> 96 个真实源中 63 个（65.6%）在 h=3 存在认证逃逸；33 个在 h=3 为局部最优，
> 其中 14 个在 h≤7 仍无改进。32 个 oracle 夹具（cost ≤ 2）作为引擎正确性检查，
> 不计入景观统计。

---

## 2. 本轮新证据：E47 视野探针

### 2.1 设计

- **问题**：v15 的"精确局部最优"是 h=3 的陈述。h=3 是声明边界，不是电路性质。
  提高视野会不会改变分类？
- **契约**：与冻结的 v14 面板**完全一致**——`state_budget=200000`、
  `time_budget_seconds=30`（阶梯用 20）、`rule_scope=e44_core_v1`、
  `RULE_LIBRARY=data/v13/e43_quartz_rule_import/generation_a/rule_library.json`
  （sha256 `fe9876de…3295`）。
- **根状态**：复用 `experiments.e46_window_landscape.run.load_root_states()`，它对
  每个根做 `state_hash` 比对（对照 v14 冻结证书），因此**不触碰任何冻结包**。
- **产出**：`docs/review/science_boost/2026-10-19_horizon4_probe/`
  - `horizon4_probe_rows.csv`（65 行，h=4）
  - `horizon_ladder_rows.csv`（33 行真实源，h=3…8）
  - `escape_verification.csv`（19 行，重放 + 幺正校验）
  - 三个 `*_summary.json`

### 2.2 结果一：h=4 已经动摇分类

| 结果 | 计数 | 说明 |
|---|---:|---|
| `H4_CERTIFIED_LOCAL_OPTIMUM` | 58 | h=4 精确完成且无逃逸 |
| `H4_ESCAPE_FOUND` | **6** | 全部为 Oracle/BV，cost 10 → 8，逃逸深度 4 |
| `H4_RESOURCE_BOUNDED` | 1 | QFT cost 148，`time_budget` |

在 33 个真实源上：26 认证 / **6 逃逸** / 1 有界 → **18.2% 的 h=3 局部最优在 h=4 被推翻**。

### 2.3 结果二：h≤7 阶梯，57.6% 被推翻

| 首次改进的视野 | 源数 |
|---|---:|
| h=4 | 6 |
| h=5 | 3 |
| h=6 | 5 |
| h=7 | 5 |
| **合计** | **19 / 33** |

按家族：

| 家族 | 真实源（h=3 局部最优） | h≤7 出现改进 | 幅度 |
|---|---:|---:|---|
| Oracle (BV) | 16 | **14** | 10→6（Δ4）、13→11（Δ2）、16→14（Δ2） |
| RandomClifford | 3 | **3** | 20→18、23→21、45→44 |
| HardwareEfficient | 1 | **1** | 46→45（h=7） |
| QFT | 2 | **1** | 34→33（h=5） |
| SurfaceCode | 8 | 0 | — |
| GHZ | 1 | 0 | — |
| IQP | 1 | 0 | — |

**这是本轮最重要的一句**：`genuine structural ceiling`（QFT / GHZ / SurfaceCode）
在视野阶梯下**只剩 SurfaceCode 与 GHZ 站得住**；QFT 在 h=5 就被削掉 1 门。
注意 QFT 的 Δ=1 很小，但"小"不等于"没有"——对"结构性天花板"这一**绝对陈述**，
一个反例就足够。

### 2.4 结果三：19/19 逃逸可重放且幺正等价

对每个改进源，重跑到首个改进视野，取证书里的 escape witness：

1. `replay_actions()` 逐步重放（每步都做 `_action_semantically_equivalent` 校验）；
2. 再用公开的 `iter_legal_actions()` 独立走一遍，拿到终点状态；
3. 对终点与根做**稠密幺正比对**（`semantically_equivalent`，全局相位商，n ≤ 9 精确）。

结果：`REPLAY_PASS` 19/19，`UNITARY_EQUIVALENT` 19/19，`CERTIFIED_ESCAPE` 19/19。
即这些不是规则库的语义事故，是真实的、可验证的削减。

### 2.5 结果四：BV 给出**可证明的视野障碍**

6 个 BV 源：根代价 10，h=4 首次逃逸到 8，h=7 到 6。最短改进路径长度 **L = 4**。
库内单步最大削减 **δ = 2**（10-18 规则库普查：149 条规则里只有 1 条 Δ=−2）。

> 因为 L=4 > H=3，任何 H≤3 的**完备**搜索都必然返回"局部最优"。
> 这与预算无关：把 state_budget 从 200k 提到 2M 也改变不了结论。

这是一个干净的、可写进论文的命题（见 §6 D1）：**视野下界 L ≥ ⌈Δ/δ⌉**，而实测
L=4 是该下界（⌈4/2⌉=2）的 2 倍——说明路径不是"两步大削减"，而是"先交换再削减"
的复合，正是 peephole 的经典盲区。

### 2.6 为什么这条结果对项目是**好事**

它同时做了三件事：

1. **把最可能的拒稿理由变成已发表的发现**。任何审稿人拿到 65 个"local optimum"
   都会问"h=3 够吗"。现在答案是有数据的：不够，19/33 不够，而且有定理式的解释。
2. **给"模板库 vs 搜索"一个可测的 trade-off**。E26 的 Phase-2b 一次匹配就到 k+2；
   通用规则 + 有界搜索 h=7 才到 6。**模板 = 长程重写复合的压缩表示**，等预算下
   不可被搜索替代——这直接回应 HOPPS 一类"SAT-最优分块可替代模板库"的挑战。
3. **重排了优先级**。继续收紧 34 个 witness-bounded 单元的松弛界（10-18 的 D8）
   已被证明是错的方向：这些单元的问题不是"算不完"，而是"算完了也不是局部最优"。

---

## 3. 已知差距：升级方案（逐条）

### G1 — 34 个 witness-bounded 单元 → **改口径，不要改预算**

- **现状**：34/128 只有上界（witness）+ 派生下界（10-17 给出 `baseline − 6` 的两侧区间）。
- **本轮判定**：真正的缺口不是这 34 个，而是**全部 65 个 local optimum 的视野合法性**。
- **升级**：(a) 把 34 个标为 `HORIZON_BOUNDED` 而非 `BOUNDED_QUANTITY`；(b) 把
  "65 local optima" 改报为"h=3 局部最优 33（真实）+ 32（夹具），其中 14 在 h≤7 存活"；
  (c) 停止继续收紧松弛界。
- **代价**：1 天（叙述层），0 行数据改动。

### G2 — 无真实 QPU → **降级为"表示敏感性的硬件 pilot"，不要当主证据**

- 现有 EHW 是 fake backend 噪声模型，288 行，已明确标注非真机。
- 真机能提供的科学增量有限：listing 是软件层概念，硬件只看到编译后的脉冲/门序列。
  唯一有价值的真机问题是"**同一幺正、不同 listing 编译出的电路，在噪声下保真度是否
  系统性不同**"——这是一个可做的 pilot（n=5，20 条电路，2 个 listing × 3 后端）。
- **判定**：★★★☆☆，排在 D1–D4 之后。它闭合的是一个 gate，不产生新科学。

### G3 — 无独立冷启动 → **已可执行，缺的是"第二台机器"**

- 10-18 已把 `cold_start_protocol.md` 从已删除的 capsule 改成 Git-pinned 传输
  （v15 = `5b08f60fc`）+ v13–v15 验证链 + 三个命名陷阱。
- **升级**：把"独立"操作化——不是"另一个人跑一遍"，而是"**一个不 import 生产者
  代码的验证器**"。`scripts/verify_certificate_qrcert_v1.py` 已是这个形状（20/20，
  不 import 生产者验证器）。把它扩到 E47 的 19 个逃逸证书，就是最小可用的外部闸门。
- **代价**：2 天。

### G4 — 无 external execution gate → **先修断掉的链，再谈外部**

- `verify_prepaper_release_manifest.py` 连续第三次失败在
  `docs/review/metric_audit_ledger_2026-08-24.csv`。10-18 已 root-cause（manifest 由
  `dirty: true` 树构建 + commit `87019d8fc` 重写 708 个单元）。
- **判定**：这是**所有者决策**（重钉哈希 or 声明漂移），不是技术问题。`release/`
  是红线，本轮不动。在决策前，任何"可复现发布"的说法都不成立。
- **升级**：在 verdict 里新增 `release_chain_status: BROKEN_BY_DRIFT`，让 fail-closed
  显式化，而不是让一个失败脚本静默存在。

### G5 — 理论撤稿后仅剩初等结果 → **两条可修的路**

1. **Thm 5-C**：10-17 已给出替换方案（Poisson/Bernstein，基于 Chen–Stein 在有界度
   线依赖图上）。本轮数据支持：27 个 E30 单元的离散指数中位 0.976，X 近似 Poisson，
   真实集中尺度是 E[X] 而非 n(d−1)。**这是唯一"补完即成立"的定理**。
2. **Thm 9 的全局最优性**：现在有了新工具。`2610.01024` 用 F₂ 自正交子空间维数给出
   高斯消元可算的 T-count 下界，并 certify 了 193/311 个块（nullity 只 113）。同样的
   代数不变量思路可以用在 phase-polynomial 片段上，把"k+2 是最优"从构造上界升级为
   两侧闭合。

---

## 4. 全流程审查（论文撰写除外）

### 4.1 科学问题与叙事（对标主刊门槛）

| 维度 | 现状 | 主刊门槛 | 差距 |
|---|---|---|---|
| 现象新颖性 | 表示依赖（WCL 7.83% vs LBL 0%） | 需要"此前无人系统刻画" | **已被 5 篇 2026 论文部分占据**（§5.2），现象本身不再是卖点 |
| 机制深度 | Thm 1(b) 是索引算术；Thm 1(a) 是生日悖论式计算 | 需要"为什么必然如此"的结构性原因 | 有，但初等；framework.md 自认"combinatorial, not physics" |
| 定量律 | 无跨家族可检验的律 | 需要一个能预测未见家族的公式 | **本轮首次给出候选：L ≥ ⌈Δ/δ⌉** |
| 反例控制 | 有 E22 shuffle、E31 factorial、E46 窗口 | 需要"主动找反例"的机制 | 本轮 E47 是最强的一次自我反例 |
| 普适性 | 15 家族 + 20 家族稳健性检查 | 需要外部基准（MQT Bench / Benchpress 已做 E34/E35） | 已有，但都是 n ≤ 20 |

**判断**：以"listing-model sensitivity"为主标题冲主刊，现在不成立（现象已被占位）。
以"**horizon-indexed reachability**"为主标题，成立的概率显著更高——因为它是一个
**方法学命题**（"局部最优"这个词在重写系统里到底意味着什么），而不是一个现象报告。

### 4.2 理论框架：哪些可修、可加强

| 结果 | 状态 | 处置 |
|---|---|---|
| Thm 1(a) | 已修正 + E30 验证（27 单元，max\|z\|=2.86） | 保留，作为"密度律" |
| Thm 1(b) | 索引算术，正确但平凡 | 保留，但不要当核心定理 |
| Thm 2(a) | 正确（Greedy 无动作谓词） | 保留 |
| Thm 2(b)/2d | 已撤回 | 删除或明确标 withdrawn |
| Thm 5 | 5-A/5-B 有效，5-C 待证 | **补 Chen–Stein**（G5.1） |
| Thm 6 | 收窄到受限生成器（n=2, seed=35 反例） | 保留收窄版 |
| Thm 7 | 人工族，构造正确 | 保留 |
| Thm 8 | 撤回（前提不相容） | 删除 |
| Thm 9 | 构造上界 + 全局最优性未证 | **用代数下界补**（G5.2） |
| C1 | 已被三门 SWAP+REMOVAL 反例否证 | 删除 |
| C2 | 存在性已证（Thm 7/9） | 保留 |
| **新增候选 Thm 10** | `L ≥ ⌈Δ/δ⌉`（视野下界） | **本轮数据支持，可写成一行证明 + 一个实例族** |

### 4.3 实验设计：功效、对照、外部效度

- **功效**：E1–E5/E15–E17 功效 0.94–>0.999；E10/E11/E12/E14/E18 欠功效（0.15–0.68），
  论文已披露。本轮 E47 是**全枚举**（不是抽样），功效问题不存在，但**外部效度**
  问题存在：33 个真实源来自 96 源面板，不是随机抽样。
- **对照**：缺一个关键对照——**同预算随机动作基线**。10-18 提过，仍未做。现在有了
  E47，这个对照的价值下降（因为完备搜索已给出精确答案），但"随机基线在 h=7 能
  找到多少"仍是审稿人会问的（"你的搜索是不是只是运气"）。**建议：1 天，补上。**
- **外部效度**：面板的家族覆盖是 9 个家族（E39 侧），不是 15 个。QFT 只有 2 个源，
  GHZ 只有 1 个源——"GHZ 站得住"这句话的统计基础是 n=1。**必须在正文写清。**

### 4.4 数据与可复现性

- 冻结链完整：`release/release_manifest.json` + 35 个活跃数据集 + SHA-256。
- **断点**：`verify_prepaper_release_manifest.py` 失败（§G4），连续第三次。
- **新风险**：本轮新增的 E47 输出全部落在 `docs/review/science_boost/`，**不进**
  `data/`、**不进** `release/`——这是刻意的：避免制造第四个漂移。代价是它不是
  "发布级"证据，需要在正文引用时说明其为 review-grade。

### 4.5 代码工程质量

- 结构：`src/circuits/`、`src/optimisation/{phase1,phase2}/`、`experiments/E*/run.py`、
  `scripts/verify_*.py`——分层清晰，fail-closed 一致。
- 静态检查：10-17 引入 `mypy.ini`，24 个错误（1 个真实隐患已修，23 个记录在案）。
- 测试：`tests/` 101 个 py 文件。本轮跑全量（`pytest tests/ -q -x`），**391 秒完成、
  无提前中止、无 `lastfailed` 记录 → 全绿**；输出只有 pandas `FutureWarning` 与
  Qiskit 2.3+ 的 `Gate.control(annotated=)` `DeprecationWarning`。前者是测试代码
  自身往 bool 列写字符串（`tests/test_e31_*.py:205/1014`），后者来自上游 API 演进，
  两者都不影响断言，但都应在下一次接触这两处时顺手清掉。
- **可改进**：`scripts/` 65 个文件里有一批一次性 census/probe 脚本（含本轮 2 个）。
  建议在 `scripts/README.md` 里分"发布链 / 诊断 / 一次性"三档，而不是删除——
  删了会破坏可追溯性。

### 4.6 外部验证路径

| 路径 | 现状 | 最短可行版本 | 成本 |
|---|---|---|---|
| 独立冷启动 | 协议可执行，无第二台机器 | Docker + Git-pinned + `qrcert/v1` 验证器 | 2 天 |
| 等价性 oracle | MQT QCEC v3.11.0 可用，未接入 | 对 128 源做交叉等价检查 | 2 天 |
| 第三方编译器 | Qiskit 2.6.0 / tket v2.18.5 / BQSKit 1.2.1 / tzap v0.8.0 | 对 GHZ/QFT/SurfaceCode 做 falsifier | 3 天 |
| 真机 | 无凭证 | n=5 表示敏感性 pilot | 需硬件 |

### 4.7 成果形态策略

| 形态 | 内容 | 判断 |
|---|---|---|
| **主刊（Nature/Science）** | 只有当"horizon-indexed reachability"成为一条**跨领域**命题（重写系统的局部最优定义）时才成立 | 现在不成立；需要 D1+D2 都完成 |
| **Nature Communications / npj QI** | 表示依赖 + 分层 + 认证景观的完整实证 | 可行，但现象已被占位，新颖性打折 |
| **PRX Quantum** | "认证景观 + 视野下界 + 模板/搜索 trade-off" 三件套 | **最匹配**。方法学强、实证扎实、有定理 |
| **Quantum** | 同上，若理论部分更重（Thm 5-C + Thm 10） | 次优但稳 |
| **TQC / QPL** | 只投 Thm 10 + 视野障碍的纯理论短文 | 可作为"占位"先发 |

**建议**：把当前稿件拆成两篇。一篇方法学（PRX Quantum / Quantum）：视野坐标 +
认证 + 模板 trade-off；一篇实证（npj QI）：15 家族分层 + 生产编译器对比。硬塞成
一篇主刊，会在"现象已被占位"和"理论太初等"两处同时被打。

---

## 5. 文献与前沿扫描（本轮实测）

### 5.1 实际执行

| 工具 | 状态 | 产出 |
|---|---|---|
| arXiv API | ✅ 可用 | 12 条短语查询，194 条记录，全部按提交日期倒序 |
| arXiv 摘要精读 | ✅ | 10 篇（含 4 篇零覆盖新文） |
| GitHub API | ✅ | 9 个仓库状态 + 4 次仓库搜索 |
| WebSearch | ✅ | 2 次（增量有限，见下） |
| Tavily | ❌ | 无 `tavily` 包、无 `TAVILY_API_KEY` |
| Exa | ❌ | 无 `exa_py`、无 key、无 MCP server |
| multi-search-engine | ❌ | 依赖外部引擎，本机不可用 |

Tavily / Exa / multi-search-engine 连续第四轮不可用，本文档**没有任何结论依赖它们**。

### 5.2 竞争格局：本轮新增的压力（按威胁程度）

1. **`2609.20873` The Refutation Gap（2026-09-16）** — 不是竞争者，是**判据**。
   它说：最优性claim 的否证半部"没有 witness，只能跑 solver 到 UNSAT"，而"这门
   纪律还没到达电路最小化"。项目的 34+65 个"没找到改进"正好是这个缺口的样本。
   **它同时是最强的威胁和最清晰的升级路径。**
2. **`2610.02029` (A Variant of) Clifford Circuit Synthesis is NP-Complete（2026-10-01）**
   — 补上了 manuscript §2.4 里"Clifford 优化复杂度未定"的空缺。这会削弱论文
   "我们指出了 simulability ≠ optimizability"的贡献度（别人已经证了）。
3. **`2609.04160` Vanilla Exact Synthesis of CNOT Circuits is NP-hard（2026-09-03）**
   — 同上，CNOT 片段的最优合成已 NP-hard。
4. **`2610.01024` Exact T-counts of CCZ layers from an isotropy bound（2026-10-01）**
   — **方法学模板**。F₂ 自正交维数 → 高斯消元可算下界 → certify 193/311 块。
   这是"把 ceiling 变成定理"的正确姿势，比 10-16 提的 `2608.22801` 更可操作。
5. **`2610.22367` Discovering SOTA quantum circuits with LLMs（2026-10-15）** — LLM
   进化框架在 8 个任务中的 7 个降低 Toffoli/量子比特数。它绕开了"局部重写"，
   是另一个层面的压力：如果 LLM 能直接搜出更好的电路，"peephole ceiling"这个
   问题的实践价值会被稀释。
6. **`2610.00669` Quantum Circuit Pruning（2026-09-30）** — 用保真度下界决定是否
   删门，最高 48.6% 削减。它的"每门一个可计算下界"结构与本项目互补，可引用。

### 5.3 文献覆盖漏洞（对照 `unified_references.md`，逐 ID 检索全库）

| arXiv ID | 标题 | 全库命中 | 影响 |
|---|---|---|---|
| `2609.20873` | The Refutation Gap | **0** | 直接命中项目软肋，必须引 |
| `2610.02029` | Clifford Synthesis NP-Complete | **0** | 使 §2.4 复杂度表过时 |
| `2609.04160` | Exact CNOT Synthesis NP-hard | **0** | 同上 |
| `2610.01024` | Isotropy T-count bound | **0** | 方法学模板，应引 |

其余 14 个候选 ID 已在 `reference_additions_2026-10-17.md` 或前几轮扫描中出现过。
**这 4 篇是真正的零覆盖**，且全部落在理论/复杂度章节——恰好是审稿人最会查的地方。

### 5.4 开源生态（GitHub API，2026-10-19）

| 仓库 | Stars | 最近推送 | 最新 release | 备注 |
|---|---:|---|---|---|
| Qiskit/qiskit | 7,903 | 2026-10-18 | **2.6.0** | 证据钉在 2.4.1，已落后两个 minor |
| CQCL/tket | 318 | 2026-10-08 | v2.18.5 | 论文钉 2.18.0 |
| quantum-compiler/quartz | 93 | 2026-10-06 | **v0.3.2** | 规则来源；版本变化需重跑 E43 导入 |
| BQSKit/bqskit | 188 | 2026-10-17 | 1.2.1 | 未进 SOTA 面板 |
| qqq-wisc/tzap | 48 | 2026-10-16 | v0.8.0 | 未进 SOTA 面板 |
| cda-tum/mqt-qcec | 120 | 2026-10-18 | v3.11.0 | 现成的外部等价 oracle |
| zxcalc/pyzx | 552 | 2026-10-16 | — | **仓库已迁移**（原路径 404），文献与脚本里的旧 URL 需更新 |
| inQWIRE/pyvoqc | 8 | 2022-04-19 | — | VOQC 已停更（Python 绑定） |

两个可执行结论：(a) Quartz 到 v0.3.2，`e43` 规则导入的 pin 需要一次显式确认；
(b) PyZX 仓库迁移会让任何按旧 URL 抓取的复现脚本失败——这是一个潜在的冷启动陷阱。

---

## 6. 优先级排序创新方向

> 排序依据：**科学增量 / 本地可行性 / 拒稿风险削减** 三者的乘积，而非工作量。
> 每个方向都写清"与现有工作的本质差异"，因为这是主刊与子刊的分界线。

### D1 — 视野作为显式坐标：horizon-indexed reachability ★★★★★

- **本质差异**：不是"我们搜得更深"，而是**证明"局部最优"这个词在重写系统里必须
  带下标**。给出 `L ≥ ⌈Δ/δ⌉`（最短改进路径长度 vs 单步最大削减），并证明当
  H < L 时**任何**完备搜索都返回局部最优——预算无关。现有全部工作（含本项目
  v13–v15）都把 H 当实现细节；把它变成坐标，等于重定义了问题。
- **可行性**：**已跑通**。E47 给出 19/33 的实测 + 6 个 BV 的 L=4 实例。
- **所需新增证据**：
  1. 全 96 个真实源的 h∈{3..8} 阶梯（本轮只做了 33 个局部最优）；
  2. L 的家族分布（现在只有 BV 有干净值）；
  3. Thm 10 的形式陈述与证明（一行 + 构造性实例族）。
- **预期影响力**：高。这是一个**可被其他重写系统引用**的命题（equality saturation、
  ZX、LLVM peephole 都适用）。
- **投稿层级**：PRX Quantum 主文；若 L 的分布呈现普适标度，可冲主刊 Perspective。

### D2 — 反驳缺口：把"局部最优"做成 DRAT 可检验的否证证书 ★★★★★

- **本质差异**：现有 34+65 个"没找到改进"是**搜索结论**；DRAT 证书是**可被第三方
  checker 独立验证的否证产物**。`2609.20873` 明确指出电路最小化领域没人做过这件事。
  差异不是"更严格"，而是"否证第一次有了 artifact"。
- **可行性**：中。需要把 h=3 的"无改进"编码为伪布尔/SAT 的 UNSAT，并导出 DRAT。
  规则库已是有限有向系统（149 条），状态空间有限，编码可行。
- **所需新增证据**：≥20 个 h=3 局部最优的 DRAT 证书；独立 checker 通过率；
  证明体积与校验耗时（对标 1.1 MB / 1.9× 求解时间）。
- **预期影响力**：极高。这是"certified"一词唯一站得住的用法，且天然对接
  `2609.20873` 的议程——可以直接引用它作为动机。
- **投稿层级**：主刊方法学亮点（Nature 的 "methods" 类），或 Quantum 的
  certification 专题。

### D3 — 模板库 vs 搜索深度不可互换 ★★★★☆

- **本质差异**：E26 的 Phase-2b 一次匹配到 k+2；通用规则 + 有界搜索 h=3 看不见、
  h=4 到 8、h=7 才到 6。**模板是长程重写复合的压缩表示**，等预算下不可被搜索替代。
  这给出可测命题：存在 `H*(T)`（模板库 T 的等价视野），且 `H*(T) ≪ H_search`。
- **可行性**：高。两侧引擎都已存在（`Phase2bTemplateMatcher` + `search_landscape_horizons_compact`）。
- **所需新增证据**：(模板库, H) 二维表；`H*` 的定义与在 3 个家族上的测量；
  与 HOPPS 类方法的对照。
- **预期影响力**：高。直接回应"SAT-最优分块可以替代模板库"的挑战。
- **投稿层级**：PRX Quantum / Quantum。

### D4 — 可计算代数下界替代搜索式 barrier ★★★★☆

- **本质差异**：把 ceiling 从"h=3 枚举没找到"变成**每个实例可用高斯消元算出的
  下界**（`2610.01024` 的 isotropy 范式）。差异是"经验观察"→"定理"。
- **可行性**：中高。QFT/GHZ/SurfaceCode 都在 phase-affine 片段，`2603.06466` 已给
  该片段的完备等式理论；GHZ_n ≥ n 已在 10-18 证明。
- **所需新增证据**：一个不变量（候选：phase polynomial 的二次型秩 / F₂ 自正交维数）
  + 在 3 个家族上达到 baseline（紧性）；QFT 需要两个引理（每个 cp 贡献 ≤1 个二次
  单项式；H 的必要性）。
- **预期影响力**：这是唯一能让"structural ceiling"从经验变成定理的路径。
- **投稿层级**：主刊（若紧）；PRX Quantum（若不紧）。

### D5 — 面板构成重述与外部效度 ★★★★☆（防守性，必做）

- **本质差异**：不是新科学，是纠正一个会误导审稿人的统计口径（32 个 cost≤2 的
  夹具被计入"局部最优"）。
- **可行性**：**已完成**（本轮 §1.3）。
- **所需新增证据**：分层报表（96 真实 / 32 夹具）+ 修正后的 headline。
- **预期影响力**：防守性但必要。不做会在审稿第一轮被一击致命。
- **投稿层级**：所有层级的前置修正。

### D6 — 真实 QPU 表示敏感性 pilot ★★★☆☆

- **本质差异**：不问"优化器在硬件上好不好"，而问"**同一幺正的两种 listing 编译
  结果，在噪声下的保真度是否系统性不同**"。这是 listing 概念唯一有硬件意义的问法。
- **可行性**：需硬件凭证。
- **所需证据**：n=5、20 条电路、2 listing × 3 后端；预注册噪声模型预测。
- **影响力**：中。闭合一个 gate，不产生新科学。
- **投稿层级**：作为主文的补充实验，不单独成篇。

### D7 — 外部冷启动 + 等价性 oracle ★★★☆☆

- 工程闸门，不是科学增量。`qrcert/v1` 验证器 + MQT QCEC 交叉检查，2–4 天。

### D8 — ~~继续收紧 34 个 witness-bounded 单元的松弛界~~ → **明确停止**

10-18 已证（L3）：形如 `cost − h·D` 的松弛界无法通过后继最小化收紧。本轮进一步
确认：这些单元的真正问题不是"算不完"，而是"**算完了也不是局部最优**"（19/33 反例）。
继续投入预算只会增加运行历史，不增加证据。

---

## 7. 下一步 30 天行动清单

### Week 1（Day 1–7）：改口径 + 把 D1 变成定理

- [ ] **D1-a** 写 `docs/theory/thm10_horizon_lower_bound.md`：`L ≥ ⌈Δ/δ⌉`，
      证明 3 行；用 6 个 BV 实例（L=4, δ=2）做首个实例族。
- [ ] **D5** 在 `docs/PROJECT_STATUS.md` 与 v16 叙述里把"65 local optima"改为
      "33 真实 + 32 夹具"，并给出 63/96 = 65.6% 的真实逃逸率。
- [ ] **D1-b** 把 E47 扩到全部 96 个真实源（h=3..8），产出 `L` 的家族分布表。
- [ ] 补 10-18 遗留的**同预算随机动作基线**（1 天，防"你只是运气好"）。

### Week 2（Day 8–14）：把否证做成 artifact

- [ ] **D2-a** 选 20 个 h=3 局部最优，编码为伪布尔 UNSAT，导出 DRAT。
- [ ] **D2-b** 接第三方 checker，记录通过率 / 体积 / 校验耗时。
- [ ] **D7** 用 `qrcert/v1` 验证器覆盖 E47 的 19 个逃逸证书（不 import 生产者代码）。

### Week 3（Day 15–21）：理论补完 + 文献修补

- [ ] **G5.1** Thm 5-C 的 Chen–Stein 证明（有界度线依赖图）。
- [ ] **D4-a** 定义 phase-polynomial 不变量，先在 GHZ 上验证紧性。
- [ ] **文献** 把 4 篇零覆盖论文写入 `reference_additions_2026-10-19.md`
      （**不合并**进 `unified_references.md`——它是三份 manifest 的路径绑定文件）。
- [ ] **G4** 给 `v15_readiness_verdict.json` 的继任者加
      `release_chain_status: BROKEN_BY_DRIFT`（不改旧 verdict，新开一份）。

### Week 4（Day 22–30）：切分与决策

- [ ] **D3** (模板库, H) 二维表，产出 `H*(T)`。
- [ ] **切分决策**：方法学篇（PRX Quantum）+ 实证篇（npj QI），或单篇 PRX Quantum。
- [ ] **D6** 真机 pilot 的预注册文档（不执行，等凭证）。
- [ ] 生态：确认 Quartz v0.3.2 是否需要重跑 E43 导入；修 PyZX 迁移后的旧 URL。

---

## 8. 本轮执行记录（仓库实际变更）

### 8.1 新增

| 文件 | 说明 |
|---|---|
| `docs/review/science_boost/2026-10-19_innovation_scan.md` | 本文件 |
| `docs/review/science_boost/2026-10-19_horizon4_probe/` | E47 证据包（6 个文件：3 CSV + 3 JSON） |
| `scripts/e47_horizon4_probe.py` | h=4 探针 + 视野阶梯，两个子命令 |
| `scripts/e47_verify_escapes.py` | 19 个逃逸的重放 + 幺正校验 |
| `docs/review/science_boost/README.md` | 四轮扫描的索引（新增，见 §8.3） |

### 8.2 未修改（红线遵守）

- `data/`：`git status -- data release` 为 **0 行**，逐项确认无变化。
- `release/`：无变化（`verify_prepaper_release_manifest.py` 的失败是既有状态，未修）。
- `docs/manuscript/`：只读。
- 未删除任何冻结或哈希绑定的文件。
- 工作树里有两处 **10-17/10-18 遗留**的改动，不是本轮产生的，为免误判在此登记：
  `src/optimisation/certified_landscape.py`（变量重命名的行为中性改动，17 行）、
  `docs/verification/cold_start_protocol.md`（冷启动协议重写，135 行）。

### 8.3 清理

- 删除 `.mypy_cache/`（20 MB）、`.pytest_cache/`（64 KB）、`.tmp_scan/`（本轮临时）。
  三者均在 `.gitignore` 内，可再生。
- 新增 `docs/review/science_boost/README.md`：四轮扫描 + 三个证据包的索引，
  解决 `docs/review/science_boost/` 下 7 个条目无索引的问题。
- **明确不做**：`data/` 下 **28,335** 个空目录（分块原始结构，全在冻结包内，删除会
  破坏哈希绑定与目录契约）；`docs/manuscript/` 与 `docs/theory/archive/` 下的 3 个
  空目录（前者在只读区，后者是 10-17/10-18 已记录的"有意保留"）；
  `docs/theory/` 下两份路径绑定文档（`QMA_hardness_draft.md`、
  `universal_law_assessment.md` 在 `release/prepaper_release_manifest.json` 里，
  移动即制造第四个漂移）；`reference_additions_*.md` 不合并进
  `unified_references.md`（同上原因）。

---

## Appendix A — 本轮读取的文件

`README.md`、`docs/PROJECT_STATUS.md`、`docs/manuscript/manuscript.md`（§1、§2、§3、
§4、§5、§6.12、§7.1–§7.6、§8）、`docs/theory/framework.md`、`data/DATA_CANONICAL.md`、
`docs/references/unified_references.md`（§A–§E）、`release/v15_readiness_verdict.json`、
`data/v15/e45_landscape_integration/classification_complete.csv`、
`data/v14/e45_full_development/protocol.json`、`data/v14/e45_idastar_escape/protocol.json`、
`experiments/e46_window_landscape/run.py`、`src/optimisation/certified_landscape.py`（接口
与 `search_landscape_horizons_compact`/`replay_actions` 语义）、
`docs/review/science_boost/2026-10-18_innovation_scan.md`（结构与去重）。

## Appendix B — 检索日志（2026-10-19）

- arXiv API：12 条查询（peephole / equality saturation / ZX / RL / template /
  phase polynomial / representation / LLM / certified / gate-count lower bound /
  pass order / synthesis choice），194 条记录，`sortBy=submittedDate`。
- arXiv 精读：`2609.20873`、`2610.01024`（全文摘要）、`2609.04160`、`2610.02029`、
  `2610.00669`、`2610.22367`、`2601.15934`、`2602.12831`。
- GitHub API：9 个仓库元数据 + 最新 release；4 次仓库搜索（pyzx / voqc / quanto /
  qsearch）。
- WebSearch：2 次（"quantum circuit peephole optimization representation 2026"、
  "PRX Quantum 2026 compiler optimization lower bound"）。增量有限，未用于任何结论。
- 不可用：Tavily（无包/无 key）、Exa（无包/无 key）、multi-search-engine（无引擎）。
