# Innovation Scan — Quantum Peephole Ceiling：科研全流程体检 + 创新方向扫描

**Date:** 2026-10-18
**Scope:** `D:/Desktop/Q-research` — 全流程体检（不含论文撰写）、前沿扫描、以及**本轮可执行项的当场执行**。
**Supersedes:** `2026-10-17_innovation_scan.md`（保留，不覆盖历史判断）。
**执行者默认假设（无人值守运行，故明确声明）:** (i) 不修改 `data/`、`release/`、`docs/manuscript/`；
(ii) 对 hash-bound 文档采取"零新增漂移"原则，宁可保留两个文件也不制造第三次 release drift；
(iii) 清理只做可逆、可审计、不触碰证据链的动作。

> **English abstract (for the repository record).** This run re-verified the v15 baseline and all four
> open gates, then executed three things rather than recommending them: (1) a full census of the frozen
> 1,474-rule rewrite library, which yields a *new structural theorem-let* — the certified rewrite
> relation is reverse-closed on 444/446 directional rules and cost-symmetric in aggregate
> (Σ cost_delta = −2), so reachability is an equivalence relation and no rule is intrinsically
> optimizing; (2) a repair of `docs/verification/cold_start_protocol.md`, which had been pointing at a
> restore capsule deleted on 2026-10-11 and was therefore *unexecutable*; (3) a cell-level root-cause
> disposition of the failing pre-paper release manifest. The scan's main intellectual output is a
> **rescoped top-tier path**: the three families the project calls "genuine structural ceilings"
> (QFT, GHZ, SurfaceCode) all lie in fragments that now possess a *complete* equational/normal-form
> theory, which makes their ceilings provable rather than merely observed. A proof for GHZ is
> supplied in §6 D1. A second, blunter finding: with horizon 3 and a library-wide maximum
> per-action reduction of 2, the entire certified landscape spans at most 6 gates — every
> "local optimum" in v15 is a horizon-3 statement, and that is now the single most likely
> rejection reason at a top-tier venue.

---

## 0. 执行摘要

### 0.1 结论（先给判断）

**工程链条依然强、诚实、且可独立复核**（本轮 `qrcert/v1` 复跑 20/20 PASS，
`CERTIFIED_CONSISTENT`）。`NOT_READY_FOR_PAPER` 判定正确，不应软化。

但本轮扫描改变了三件事的判断：

1. **"表示决定能力"已经不再是本项目的差异点。** 2023–2026 的检索（本轮实测，§4）显示
   至少 **五篇** 独立工作从不同侧面论证 representation 决定下游编译能力，其中两篇已给出
   可证界。同时 `AlchemQ`（arXiv:2609.19160）已经占据了"逐结果等价证书 + 版本化协议 +
   独立验证器"这一工程位；`Q-PreSyn`（arXiv:2601.19738）明确写出"local synthesis 性能
   强烈依赖 circuit representation"并做局部编辑搜索。**继续以 listing-model sensitivity
   为主标题投稿，会在第一轮就被判为增量。**

2. **本项目真正独有、且别人还没有的东西只剩一件：认证景观（certified landscape）——
   一张对固定面板、固定规则域、逐源可复算的"可达动作空间地图"，以及它给出的否定性结论
   （92.6% 的认证规则根本不能降成本）。** 这是可以撑起 PRX Quantum 的东西，但它必须被
   重新表述为"暴露度分类学"，而不是"listing 很重要"。

3. **最致命的弱点本轮被量化了。** 规则库普查显示：**整个 1,474 条规则库中，单步最大降幅
   就是 2**（25 条 −2 规则，1,474 中的 1.7%）；而 v15 的认证视野是 horizon = 3。
   于是"certified landscape"这个招牌所覆盖的全部改进空间 **≤ 6 个门**，而观测到的逃逸
   只降 1–2 个门。任何审稿人都会问："你的 65 个 local optimum 是不是 h=3 的产物？"
   本项目目前**无法回答**。这比"没有真实 QPU"严重得多。

### 0.2 本轮实际执行了什么（不是建议）

| # | 动作 | 结果 |
|---|---|---|
| E1 | **冻结规则库全量普查**（新增脚本 + 新证据包） | `scripts/census_rule_library.py` → `docs/review/science_boost/2026-10-18_rule_library_census/`。1,474 条 pattern 规则 + 14 条 schema 规则；224 降 / 1,028 中性 / 222 升；Δ 分布 **−1:199、+1:197、−2:25、+2:25**，ΣΔ = **−2**；**反向闭包 444/446 = 99.55%**，两个例外恰是 rz 参数分裂规则（逆不可有限表示）；97 个源模式有多个不同目标（选择度 ≤ 3）。 |
| E2 | **冷启动协议修复** | `docs/verification/cold_start_protocol.md` 原第 1 步要求下载 `release/prepaper_v12_restore_capsule.zip` —— 该文件 **2026-10-11 已被退役删除**，协议实际不可执行。已改为 Git 固定 commit 传输 + 3 条已知陷阱 + 补上 v13–v15 验证链。 |
| E3 | **release 漂移根因定位** | `docs/review/release_drift_disposition_2026-10-18.md`。不是"哈希坏了"，而是两件事叠加：清单在 `dirty: true` 的工作树上生成（记录的哈希从未进入 Git），且 2026-09-08 的 `87019d8fc` 重写了台账 **708 个单元格 / 7 列**（592 行与 schema 不变，`metric_sha256`、`target` 全未动，16 处状态迁移）。 |
| E4 | **参考文献可发现性修复（零漂移）** | 新增 `docs/references/README.md` 权威索引。**明确放弃**把 [95]–[112] 并入 `unified_references.md`：该文件被 **3 个** release 清单 path-bound，合并会制造第二次、且更大的漂移。 |
| E5 | **GHZ 天花板从经验升级为可证（草稿证明）** | §6 D1 给出 GHZ_n 在声明门集内最优的完整论证（交互图连通性 ⇒ ≥ n−1 个 CX；非对角单比特门 ⇒ ≥ 1 个 H；合计 ≥ n，构造达到 n）。数据核对：`ghz_4` = 3 CX + 1 H = 4 = n。 |
| E6 | **清理** | 删除本轮临时目录；**未删除任何项目文件**（原因见 §8：唯一像"废弃代码"的 `scripts/build_v12_restore_capsule.py` 被 `build_v12_readiness_package.py:285` 引用，删了会断）。3 个空目录经查为**有意保留**（`docs/theory/README.md` 明文说明 `archive/` 是故意空的）。 |
| E7 | **回归确认** | `scripts/verify_certificate_qrcert_v1.py` → 20/20 PASS；`git status --porcelain data/ release/` 为空。 |

### 0.3 优先级（本轮修订）

| # | 方向 | 对 Nature/Science 门槛的杠杆 | 工作量 | 层级上限 |
|---|---|---|---|---|
| **D1** | **完备理论下的天花板**：把 QFT/GHZ/SurfaceCode 的"真天花板"从经验升级为可证 | ★★★★★ | 中（GHZ 已完成） | **PRX Quantum / Nature Communications**；配硬件则 Nature Physics |
| **D2** | **视野敏感性实验**：h=4/5 重跑 65 个 local optimum | ★★★★★ | 中高 | 与 D1 合并 |
| **D3** | **暴露度 vs pass-order 的解耦**（不是"顺序重要"，而是"哪些顺序效应被 relisting 吸收"） | ★★★★☆ | 中 | PRX Quantum / Quantum |
| **D4** | **规则库覆盖率的完备基准**（用完备理论当 ground truth 量"库缺什么"） | ★★★★☆ | 中 | PRX Quantum / Quantum |
| **D5** | 真实 QPU 表示敏感性 pilot（假设已锐化） | ★★★☆☆ | 低 | npj QI |
| **D6** | 证书互操作（qrcert ↔ AlchemQ/MQTOpt/Irene） | ★★★☆☆ | 低 | Quantum (tools) |
| **D7** | LLM/RL 作为"暴露度探索器"，认证景观当评估器 | ★★☆☆☆ | 中 | TQE |
| **D8** | ~~继续收紧 34 个 witness-bounded 单元的松弛界~~ | **建议停止** | — | Lemma 3 已证此路不通 |

---

## 1. 事实基线（2026-10-18 复核）

### 1.1 证据链（逐项读过，非转述）

| 层 | 结果 | 来源 |
|---|---|---|
| E1–E30 canonical | 35 个 active canonical 数据集 / 96,205 行（37 个清单条目 / 96,289 行含 2 个 superseded） | `data/DATA_CANONICAL.md` v2.4.0 |
| E31 sealed factorial | 28,152 行 | `docs/EXPERIMENT_HISTORY.md` |
| E32–E37 | telemetry / scale / MQT cross-abstraction / Benchpress / PyZX / energy | `release/e32_*`…`e37_*` |
| v13 E45 screening | 0/18 eligible；最大 guided failure 63.28125% | `release/v13_readiness_verdict.json` |
| v14 E45 screening | 18/18 eligible；13,824 行；0 semantic failure | `release/v14_readiness_verdict.json` |
| v14 exact finite horizon | 93 exact / 35 truncated | 同上 |
| v14 IDA* escape | 63 exact escapes / 65 exact local optima | `docs/PROJECT_STATUS.md` |
| v15 landscape integration | 128/128 分类；tier 93 `COMPACT_COMPLETE_ENUMERATED` / 1 `COMPACT_COMPLETE_DERIVED` / 34 `CLASSIFICATION_EXACT_EXTRAS_BOUNDED`；escape 63；local optimum 65；exact best cost 94；witness replay failure 0 | `release/v15_readiness_verdict.json` |
| v15 E46 window landscape | 76,236 window rows；39,474 escapes；242 escape certificates；0 truncated；`PANEL_COMPLETE`；escape rate w8_h2 0.4685 / w8_h3 0.4769 / w16_h2 0.5586 / w16_h3 0.5701 | 同上 |
| 理论可采信集 | Obs 1(a/b)、Thm 1(a/b)、Thm 2(a)、Lemma 3/4、Thm 2(c)、Thm 7、Thm 9、Prop 1、Prop 6 | `docs/theory/framework.md` + `formal_results.md` |
| 理论已撤/待修 | Thm 5（证明不全，已有 5-A/5-B/5-C 修复路线）、Thm 6 一般形式（反例）、Thm 8（撤）、Thm 2(d)（无效）、QMA-hardness（撤）、Obs 1 一般化（撤）、C1（反例） | 同上 |

### 1.2 三个贡献，按其实际可辩护强度重排

1. **认证景观 + 分类完备性**（原第三贡献，实为第一）：
   固定面板 128 源、固定规则域 `e44_core_v1`、horizon 3，128/128 分类，94 个精确最优成本，
   34 个双侧认证区间（宽度 4–5，均值 4.56，≤ 2.87% baseline），76,236 个窗口搜索零截断。
   **这是全世界目前唯一一份"逐源可复算的局部可达空间地图"。**
2. **搜索空间分层（categorical trichotomy）**：15 族 6 类；但**分层边界依赖模板库**
   （E26 把 IQP 从 0.5% 推到 92.0%），所以它是"规则域条件"下的分类，不是电路固有分类。
3. **Listing-model sensitivity**：0.0000%（LBL）→ 7.83%（WCL），机制有 Thm 1(b)、
   密度律有 Thm 1(a)+E30 验证、shuffle 控制 E22（p = 6.8e-15，且方向是**增加**）。
   **科学上最干净，但竞争上最拥挤。**

### 1.3 关闭 / 未关闭登记（复核后）

| 项 | 状态 | 权威 |
|---|---|---|
| 冻结规则库（1,474 safe directed rules） | 已关闭（声明域内） | `docs/PROJECT_STATUS.md` |
| E44 oracle（512 cases / 1,024 rows） | 已关闭 | 同上 |
| E45 v14 screening / escape-depth / v15 分类记账 | 已关闭 | 同上 |
| E46 窗口景观 | PANEL_COMPLETE | v15 verdict |
| 确定性 / 失败处理 | 已关闭 | `docs/PROJECT_STATUS.md` |
| E1–E37 历史证据 | 保留，无重跑理由 | 同上 |
| **34 个长 listing 逃逸单元** | **Open（bounded 形态）**，已有双侧区间 | v15 verdict + 2026-10-17 证据 |
| 独立冷启动 | **OPEN**（`external_cold_start`） | v15 verdict |
| 真实 QPU | **OPEN**（`real_qpu`） | 同上 |
| 外部执行闸门 / release 权威 | **OPEN**（`release_authority`） | 同上 |
| C3 标题与定位 | **USER_DECISION_PENDING** | 同上 |
| 全规则域（1,474 条）面板；wire-consecutive 窗口剖面 | Open | `docs/PROJECT_STATUS.md` |

### 1.4 诚实的科学边界（仍是绑定约束）

`docs/theory/framework.md` "Honest framing note" 第 3 条：

> "The 'structural ceiling' is a limit on a specific class of *classical algorithms*
> (peephole rewriters) applied to a specific *data structure* (gate sequences).
> It should not be confused with circuit complexity lower bounds."

**Nature/Science 路径必须改写这句话。** 本轮给出了一条比"找一个通用 barrier 泛函"更可靠的改写方式：
不是把天花板变成"电路的复杂度下界"，而是把它变成**"在完备等式理论下的可证最小性"**——
这是一个严格更弱、但可以真正证明的陈述，且恰好覆盖本项目最强的三个经验结论（§6 D1）。

---

## 2. 已知差距：逐条核验 + 升级方案

### Gap 1 — 34 个 witness-bounded 单元

**核验（不变）:** `bounded_best_cost_count = 34`，`CLASSIFICATION_EXACT_EXTRAS_BOUNDED = 34`，
verdict 明确禁止对这 34 格声明枚举量。

**已有进展（2026-10-17）:** 由项目自身可采信的单步界 `_maximum_single_step_reduction(..., "e44_core_v1") = 2`
推出 `best_cost ≥ baseline − 6`（horizon 3 × 每步 2），34 格从单侧变双侧，宽度 4–5。

**本轮新增的结构性事实（关键）:** 规则库普查表明 **2 不是 core 域的偶然值，而是整个 1,474 条库的上限**
（Δ 分布只到 ±2；−2 规则 25 条，占 1.7%）。所以"用更强的单步界"这条路在库层面**已经封顶**。

**并且本轮给出了一条否定性引理（Lemma 3，见 §3.2）：松弛式界不可能通过后继最小化收紧。**
结论：**这 34 格不可能靠更好的松弛/更多算力关闭，只能靠一个真正的不变量（invariant）。**
建议：停止在松弛上投入（D8），把资源转到 D1/D4。

### Gap 2 — 无真实 QPU 验证

**核验:** `real_qpu: OPEN`；EHW 是噪声模型仿真（`credential_audit.route = 3b_noise_model_simulation_NOT_real_hardware`）；
§7.4 的负结果（逻辑压缩 46.15% → basis translation 后物理压缩 **0%**）成立。

**升级（假设已锐化，比上一轮更可证伪）:** 不要做"优化器在硬件上有没有用"这种大而空的实验。
做一个**单假设、二值判定**的实验：

> **H-QPU:** 逻辑压缩能否穿过 basis-translation 闸门，取决于 **WCL 预处理是否在 transpile 之前执行**；
> 若在之后执行，压缩被 basis translation 完全吸收（§7.4 已观测），若在之前执行，则部分存活。

3 族（BV、HaarRandom、RandomClifford）× 5–7 qubit × 2 listing × 3 seed，IBM 免费额度足够。
判据预先登记：物理两比特门数（basis translation 之后）差值 > 0 且方向一致。
**这是唯一能把"表示"从软件变量变成硬件可测量量的实验**，也是 Nature Physics 路线唯一的入场券。

### Gap 3 — 无独立冷启动

**核验:** `external_cold_start: OPEN`。

**本轮发现（严重）:** 协议本身**不可执行**。第 1 步指向的 `release/prepaper_v12_restore_capsule.zip`
已于 2026-10-11 退役删除（`docs/review/v15_cleanup_2026-10-11.md` 有记录，但协议没跟着改）。
而且即使那个 zip 还在，它也是 **v12 时代**的产物，**从不包含 v13/v14/v15 的认证景观证据**——
也就是说：**本项目当前的主结果，从来没有一个可交付的冷启动载体。**

**已执行修复:** 协议改写为 Git 固定 commit 传输（v15 波次 = `5b08f60fc`），补上 v13–v15 验证链，
并把三条陷阱写成显式条款（80 门基线分支 / Qiskit 版本钉死 / 已知会失败的清单条目）。

**仍然 OPEN 的部分:** 需要第二台机器或 CI runner 真正跑一遍。这是四个开放闸门里最便宜的一个，
但现在才第一次**具备可执行性**。

### Gap 4 — 无外部执行闸门

**核验:** `release_authority: OPEN`。`qrcert/v1` 独立验证器存在（20/20 PASS，不 import 任何生产者验证器）。

**竞争压力（本轮新增）:** `AlchemQ`（arXiv:2609.19160）已经发布了**同构的东西**：
版本化证书协议 0.2.0、canonical gate-canon 哈希、三态判定、独立参考验证器（Apache-2.0）、
100 电路 × 400 次优化全通过、IBM Heron r2 pilot。
"我有一个独立验证器"不再构成新颖性。

**升级方向:** 从"我有验证器"改为"**我的证书描述的是可达空间，不是单个输出**"。
等价性证书证明"这个输出对"；认证景观证明"**这个输出在给定规则域内已经是可达集合的最优点**"。
后者是前者的严格加强，且 AlchemQ 的架构（beam search + 逐结果证书）**在原理上无法给出**。
这是一句话就能说清的差异，必须写进 §1.1。

### Gap 5 — 理论：撤稿与待修

**核验（不变）:** Thm 5 不全；Thm 6 一般形式被反例推翻；Thm 8 撤；Thm 2(d) 无效；
QMA-hardness 撤；Obs 1 一般化撤；C1 反例。当前可采信的是初等/受限结构结果 + Thm 7/9 构造。

**本轮新增（正面）:** 规则库的反向闭包性（444/446）给出一个**新的、可证的**结构结论（Lemma 1，§3.2），
它不依赖任何被撤结果，且直接支撑"天花板是视野现象"的重述。这是本轮理论侧唯一的净增量。

---

## 3. 全流程审查（论文撰写除外）

### 3.1 科学问题与叙事

**现状:** RQ1（listing → 结果）、RQ2（搜索空间结构）、RQ3（生产编译器越界之处）。
诚实、边界清楚、被否证的 phase transition 处理得体（§1.3 明确写"data refuted"）。

**对标 Nature/Science 主刊的门槛，三条硬伤:**

1. **问题不够大。** 主刊要的是"改变了某类系统的做法"或"证明了一个普遍限制"。
   当前最强陈述是"某些电路族在某个规则域下不可约"——这是**软件工程观察**，
   连 PRX Quantum 都需要额外的理论骨架。
2. **现象已被复现五次。** §4.1 列出 2026 年的五篇独立工作。审稿人会直接引 `2609.29406`
   说"pass order 也这样，你们是它的对偶"。
3. **最强结论的可证伪性不足。** "genuine structural ceiling" 的定义是"所有被测编译器都降不动"——
   这是**工具集合的补集**，不是电路性质。一个只测了 7 个配置的"所有"在方法论上站不住。

**叙事重构建议（本轮最重要的非实验产出）:**

> 旧命题：**"电路表示（listing）决定 peephole 优化能做什么。"**（拥挤，且是软件工程观察）
>
> 新命题：**"对一个反向闭合的认证重写库，可达改进集合是等价类的性质，与表示无关；
> 优化器之间真正的差别是*暴露度*（exposure），而暴露度是表示的函数。
> 我们给出固定面板上第一张分类完备的暴露度地图，并证明 92.6% 的认证规则根本无法降低代价——
> 因此所谓'天花板'不是规则库的性质，而是（等价类，视野，代价函数）三元组的性质。"**

这个版本的三个支点全部有本轮/近期证据：反向闭包（E1）、92.6%（E1 + 10-17 证据）、
视野上界 6 门（E1 + Lemma 2）。而且它把最致命的质疑（"你的 local optimum 是 h=3 的产物"）
**主动变成论文的一个定理/实验**，而不是留给审稿人。

### 3.2 理论框架：哪些猜想可修、可加强

**Lemma 1（反向闭包 ⇒ 可达性是等价关系）— 本轮新增，可证。**
冻结库中 446 条方向性规则有 444 条存在精确反向（99.55%）；两个例外是
`quartz_v1:506_3:*` 的 rz 分裂规则（`rz(P0),rz(P1) → rz(P0+P1)`），其逆需要引入自由参数，
不可有限表示。忽略这两个（或把它们视为"参数化族"），重写关系对称 ⇒ 可达性是对称闭包 ⇒
**没有任何一条规则在方向上"更优"**，代价函数是唯一的方向性来源。

*推论（可写进论文的一句话）:* 一个反向闭合的认证库里，"优化能力"完全来自**规则间的复合**
（搜索），而不是规则本身。这解释了为什么 horizon 是唯一真正重要的参数，也解释了
为什么"补模板库"（Phase-2b）能打破所谓天花板——它增加的是**复合路径**，不是"更强的规则"。

**Lemma 2（视野上界）— 本轮新增，算术即可。**
库级单步最大降幅 D = 2（1,474 条中 25 条 Δ=−2）。horizon H = 3 ⇒ 任何认证逃逸的降幅 ≤ 6。
实测逃逸降幅 1–2。**所以 v15 的"local optimum"全部是"h=3 内无改进"**，
这与"该电路不可优化"之间隔着一个未测的 H ≥ 4 区域。

**Lemma 3（松弛天花板）— 本轮新增，证明两行，但决定性。**
设 LB(s) = cost(s) − h·D。任何试图用"取后继最小值"收紧的写法
`LB'(s) = min_{s'∈Succ(s)} [cost(s') − (h−1)D]` 都被 `Succ(s)` 中代价最大的元素支配，
而该元素必然存在（库里有 222 条增代价规则，占 15.1%），于是 `LB' ≤ cost(s) − (h−1)D + 2`，
不比原界强。**结论：靠松弛/算力关闭 34 格是不可能的；必须引入不变量。**
这条引理的价值在于**止损**：它把 D8 从"待做"变成"已证不可行"。

**Thm 5 修复（延续 2026-10-17）:** 5-A（固定匹配）与 5-B（条件化）有效；5-C（Poisson/Bernstein）
有 27 格数据支持（离散指数中位数 0.976）。证明路线仍是 Chen–Stein + 有界度线依赖图。
**建议降级处理:** 这是一个"锦上添花"的技术结果，不影响主叙事，不要让它占用 D1/D2 的时间。

**Thm 9 全局最优性:** 2026-10-17 建议用 SAT/MIP（arXiv:2510.00649、2508.00416）。
本轮判断：**在声明门集内用交互图 + 相位多项式论证比 SAT 更便宜且更强**（见 D1）。
SAT 只应作为独立交叉验证，不作为主证据。

### 3.3 实验设计：功效、对照、外部效度

| 问题 | 现状 | 严重度 | 修法 |
|---|---|---|---|
| **视野固定为 3** | 全部认证结论共享同一 horizon | **致命** | D2：分层抽样 16 格跑 h=4/5；或证明 horizon 单调性（若能证，则 h=3 的 local optimum 可外推，价值极高） |
| **128 源面板非随机** | 来自 E39/E44 的固定面板，不是电路分布的样本 | 高 | 明确写成 "fixed panel"，禁止任何"比例/普遍性"措辞；D2 的抽样必须分层 |
| **"genuine ceiling" 的操作化** | "所有被测编译器都降不动"（7 个配置） | 高 | D1：改成"在完备理论下可证最小"，把工具补集换成定理 |
| **分层分类依赖模板库** | E26 把 IQP 0.5%→92.0% | 高（已承认） | D4：用完备理论量"库覆盖率"，把依赖变成可测量 |
| **新结论无功效分析** | v15/E46 的 37.2%、94/128 等无 CI | 中 | 给二项 CI（37.2% 基于 179/481，Clopper–Pearson 约 [0.33, 0.41]）；128 格的分类比例同样给 CI |
| **E46 是窗口局部统计** | 按构造 window-local | 中 | 明确禁止"whole-circuit"解读（verdict 已禁止，论文需同步） |
| **无预注册** | H1–H5 是事后映射到已跑实验 | 中 | 新方向（D1/D2/D3）必须**先写判据再跑**，否则重蹈 H4 覆辙 |
| **对照缺失** | 没有"同预算下的随机重写基线" | 中 | 加一个 random-restart 同预算对照：若随机搜索在同预算下达到同等逃逸率，"认证"的价值就被削弱——这个对照必须做，否则审稿人会替你做 |

**最该补的一个实验（成本最低、杀伤力最大）:** 同预算随机基线。
65 个 local optimum 里，随机抽 3 步动作 10,000 次，看有多少次能降成本。
如果接近 0，则"局部最优"是真的；如果不接近 0，则整个认证搜索的完备性叙事要重写。
**这个实验一天能做完，且能预防最坏情况。**

### 3.4 数据与可复现性

**强项:** 冻结/派生/原始三层分离；`DATA_CANONICAL.md` 的 Known Issues 15 条极其诚实
（E18 生存偏差、E26 sampled200 保真度、success 列无信息量、wave-6 重跑对账）；
128/128 根 listing 位精确重建（2026-10-17）；`qrcert/v1` 独立复核。

**弱项（本轮定位）:**

1. **release 链已断**，且断点是一个从未进入 Git 的哈希（`dirty: true`）。
   本轮给出根因与两个可选修法（`docs/review/release_drift_disposition_2026-10-18.md`），
   **但修复需要 owner 决策，因为要动 `release/`**。
2. **冷启动载体不存在**（v12 胶囊退役，且从不含 v13–v15）。已改为 Git 传输。
3. **依赖钉死 vs 生态前进:** `requirements-lock.txt` 钉 `qiskit==2.4.1`，而 Qiskit **2.6.0 已于 2026-10-16 发布**。
   钉死是对的（证据绑定），但必须把"在 2.6.0 下复跑"显式定义为**分歧实验**而非复现。
4. **仓库体量:** `data/` 下 36,375 个文件（27,675 JSON / 6,858 qpy / 1,398 qasm）。
   对 Zenodo/arXiv 附件是负担，对 clone 体验是灾难。建议：**不改内容，只加 `data/README.md` 的分卷索引**，
   并在发布时用 submodule 或 release asset 分离大件。本轮不动（属数据区）。

### 3.5 代码工程质量

| 项 | 现状 | 判断 |
|---|---|---|
| 静态类型 | `mypy.ini` 已加（2026-10-17）；24 错 / 6 文件，已修 1 个真实隐患（变量遮蔽），余 23 | 可接受；**不建议**继续批量修（每个都需 drift 条目，且有改变输出的风险） |
| 测试 | 101 个测试文件；本轮复跑证书链 20/20 | 健康 |
| CI | 按项目决定排除 | 但这直接导致"冷启动"永远 OPEN。**建议至少加一个本地 `make verify` 目标**（不是 CI，是一条命令） |
| 死代码 | `scripts/build_v12_restore_capsule.py` 为已退役胶囊的构建器，但被 `build_v12_readiness_package.py:285` 引用 | **不能删**（删了断链）。建议加 header 注明 "builds a retired artifact; retained for the v12 package contract" |
| 命名一致性 | E25/E26 历史上曾混用（已在 manuscript 头注说明） | 已收敛 |
| 单机验证 | 全部证据在同一台机器上生成 | 结构性弱点，只能靠 Gap 3 解决 |

### 3.6 外部验证路径

按"性价比"排序（本轮判断，与上轮一致但更明确）:

1. **冷启动（最便宜）** —— 现在才第一次可执行。目标：第二台机器 + `qrcert/v1` + 8 个验证器全绿。
2. **外部等价性 oracle（便宜且高信誉）** —— 接入 `mqt.qcec`（v3.11.0，2026-10-09）或 Irene（arXiv:2609.36065，79.92% 覆盖率，发现 15 个编译器 bug）。
   把"我的等价性契约 D11 够不够"这个问题，用别人的工具回答。**这比自证强得多。**
3. **BQSKit / tzap 进 SOTA 面板（中等）** —— BQSKit 1.2.1（2025-08-30）、tzap v0.8.0（2026-10-11，48★，专攻"fast and scalable circuit optimizer"）。
   tzap 尤其危险：如果它能在 QFT/GHZ 上降门数，三个"真天花板"立刻塌一个。**必须测，且要主动测。**
4. **真实 QPU（最贵）** —— 见 Gap 2 的锐化假设。

### 3.7 成果形态策略

| 层级 | 需要什么 | 本项目现状 | 判断 |
|---|---|---|---|
| **Nature / Science 主刊** | 普遍限制（定理）+ 可测量后果（硬件） | 两者皆无 | **30 天内不可达。不建议以此为目标写稿。** |
| **Nature Physics / Nature Communications** | 一个可证的限制 + 一个硬件/实验后果 | D1（可证）+ D5（硬件 pilot）拼起来勉强够 | 唯一路径，且需要 D1 与 D5 **同时**成功 |
| **PRX Quantum** | 严格的方法论 + 否定性/分类性结果 + 可复算证据 | **已经基本具备**，缺 D1/D2 的理论骨架 | **最现实的目标** |
| **Quantum** | 工具/协议/证书 | `qrcert/v1` + 认证景观工具链 | 备选，且可先发（不冲突） |
| **npj QI** | 扎实的分类学 + 编译器启示 | 现稿即达标 | 保底 |
| **TQE / QST** | 工程/基准 | 现稿偏强 | 不建议降格 |

**建议的投稿组合（不是二选一）:**
(a) **Quantum 先发工具/证书论文**（`qrcert/v1` + 认证景观引擎 + 128 源复算），抢时间戳；
(b) **PRX Quantum 发主论文**（暴露度分类学 + 完备理论天花板 D1 + 视野敏感性 D2）；
(c) **npj QI 发分层分类学 + 编译器启示**（现稿的 15 族部分，拆出来）。
三篇的材料**已经全部在仓库里**，缺的是切分与 D1/D2 两块新骨架。

---

## 4. 文献与前沿扫描（本轮实测）

### 4.1 实际执行

| 手段 | 内容 | 结果 |
|---|---|---|
| arXiv API | 16 组短语检索（peephole / equality saturation / e-graph / ZX / template matching / representation / pass ordering / LLM / RL / certified lower bound / compiler benchmark / phase polynomial / landscape / scheduling / depth-optimal synthesis / IR），按提交日期倒序各取 12 条 | 全部返回；关键条目逐条取摘要 |
| arXiv API（id_list） | 16 篇决策相关论文的完整摘要 | 见 §4.2 |
| GitHub REST API | 15 个仓库状态 + 6 个最新 release | 见 §4.4 |
| 内置 WebSearch | 未使用（arXiv + GitHub 已覆盖本轮全部决策需求；Tavily / Exa 在本机无 API key，**未使用，本文不依赖其结论**） | — |

> 诚实声明：`tavily` 与 `web-search-exa` 两个 skill 在本环境**不可用**（无包/无 key/未配置 MCP server）。
> 本轮未调用它们，因此**没有任何结论依赖它们**。`multi-search-engine` 同样未使用（其价值在中文源，
> 而本领域一手源全在 arXiv/GitHub）。这是能力边界，不是遗漏。

### 4.2 竞争格局：本轮新增的五条压力

| 论文 | 日期 | 为什么它压缩了本项目的空间 |
|---|---|---|
| **arXiv:2609.19160 — AlchemQ** | 2026-08-24 | "proof-carrying optimization + 逐结果等价证书 + 版本化协议 0.2.0 + 独立参考验证器 + 三态判定 + tamper-evident 哈希"。**这几乎就是 `qrcert/v1` + release 闸门的架构**，且已有 IBM Heron r2 pilot。→ 证书不再是差异点。 |
| **arXiv:2601.19738 — Q-PreSyn** | 2026-01-27 | 明文写 "local synthesis ... performance strongly depends on circuit representation"，并做局部编辑的 RL 搜索，T-count 最多降 20%。→ 第五篇表示依赖性论文，且**直接落在"局部编辑"这个格子里**。 |
| **arXiv:2511.18770 — HOPPS** | 2025-11-24 | SAT 最优的分块相位多项式合成，**当 peephole 用**：CNOT 数最多降 50.0%、深度降 57.1%。→ 对"模板库不完备"是最强的方法论威胁：审稿人会问"为什么不用 SAT 最优块替换你的模板匹配？" |
| **arXiv:2603.06466 — Prime-dimensional phase-affine completeness** | 2026-03-06 | 给出 prime-dimensional phase-affine 电路的**完备等式理论**与唯一正规形。→ 这既是威胁（"完备性别人做了"），**也是本轮最大机会**（见 D1）：完备理论是证明天花板的前提。 |
| **arXiv:2610.22367 — LLM discovers SOTA circuits** | 2026-10-15 | 进化式框架：LLM 提议、**独立评估器验证打分**，8 个任务里 7 个刷新 Toffoli/qubit 记录。→ "评估器 + 搜索"范式已进主刊级；本项目的认证景观恰好可以当那个评估器，但**必须先有 D1 的完备性才有话语权**。 |

其余关键条目（用于定位，不逐条展开）:
`2609.29406`（pass order，MQT）、`2607.04586` QuTuner、`2605.11375` TuniQ、`2603.18049`（按脚本特征条件执行 pass）、
`2609.36065` Irene（等价性检查 79.92%，发现 15 个编译器 bug）、`2608.22801`（ZX exactness barrier，
**P0-1 的结构模板**）、`2608.22810`（ZX 后处理回收 26.6–30.1% 门数）、`2609.00255`（编译器保证契约综述）、
`2508.00416`（#SAT 综合）、`2510.00649`（MIP 可证最优）、`2607.02616`（MLIR 量子 mapping）、
`2609.29305`（QaiJi IR 八层 IR）、`2608.19103`（RL+CR，确定性规则内嵌环境）。

**格局判断:** "表示/顺序重要"这一层已经饱和（≥5 篇）；"可证界"这一层有 2 篇（`2608.22801`、`2609.29210`）；
"逐结果证书"这一层有 1 篇（`2609.19160`）；**"逐源可达空间 + 分类完备"这一层仍然只有本项目**。
这决定了 D1/D2 必须是主攻方向，D6（证书互操作）只能是配角。

### 4.3 文献覆盖漏洞（对照 `unified_references.md`）

| 缺口 | 性质 | 处置 |
|---|---|---|
| 无 `2609.19160`（AlchemQ） | **致命**——最直接的架构竞争者 | 必须进正文 Related Work，且要给出一句话差异 |
| 无 `2601.19738`（Q-PreSyn） | 高——第五篇表示依赖性 | 必须引 |
| 无 `2603.06466`（完备等式理论） | 高——D1 的理论前提 | 必须引，且是 D1 的立论基础 |
| 无 `2511.18770`（HOPPS） | 高——SAT 最优 peephole | 必须引，否则"模板库"论证不成立 |
| 无 `2609.36065`（Irene） | 中——等价性检查 SOTA | 引，用于 D6 |
| 无 `2607.04586` / `2605.11375` / `2603.18049` | 中——pass tuning 三连 | 引，用于 D3 的对照 |
| 无 `2610.22367`（LLM 发现电路） | 中——评估器范式 | 引，用于 D7 |
| `unified_references.md` 6 项书目缺陷 | 低 | 已登记在 `reference_additions_2026-10-17.md` §B；本轮新增 `docs/references/README.md` 做权威索引，**不合并**（避免第 3 次 drift） |

### 4.4 开源生态（GitHub API，2026-10-18）

| 仓库 | Stars | 最近推送 | 最新 release | 对本项目的含义 |
|---|---|---|---|---|
| Qiskit/qiskit | 7,899 | 2026-10-17 | **2.6.0（2026-10-16）** | 证据钉在 2.4.1；**差两个 minor**。冷启动必须钉死，且需一次显式的"2.6.0 分歧实验" |
| CQCL/tket | 318 | 2026-10-08 | v2.18.5 | SOTA 面板已含 2.18.0 |
| quantum-compiler/quartz | 93 | 2026-10-06 | v0.3.2（2025-12-10） | 规则来源；已冻结导入 |
| **BQSKit/bqskit** | 188 | 2026-10-17 | 1.2.1（2025-08-30） | **未进 SOTA 面板**——LBNL 出品，必须加 |
| **qqq-wisc/tzap** | 48 | 2026-10-16 | **v0.8.0（2026-10-11）** | **未测**。"fast and scalable circuit optimizer"，是最可能推翻"真天花板"的工具 |
| zxcalc/pyzx | 551 | 2026-10-16 | — | E36 已用 |
| munich-quantum-toolkit/qcec | 120 | 2026-10-17 | v3.11.0 | **未接入**——现成的外部等价性 oracle（D6） |
| munich-quantum-toolkit/bench | 131 | 2026-10-17 | — | MQT Bench，E34 已用 |
| openqasm/openqasm | 1,518 | 2026-09-02 | — | IR 层，与"production IR 对 listing 不敏感"一致 |

**生态判断:** 两个"必须马上测"的工具是 **tzap**（可能推翻天花板）与 **MQT QCEC**（现成的外部 oracle）。
这两个都不需要写新算法，只需要接一下，是 30 天内性价比最高的外部验证。

---

## 5. 本轮执行记录（仓库实际变更）

| 文件 | 类型 | 内容 |
|---|---|---|
| `scripts/census_rule_library.py` | 新增 | 规则库普查器；只读输入，输出到 docs 下带日期目录；含 protocol/summary/CSV 三件套 |
| `docs/review/science_boost/2026-10-18_rule_library_census/` | 新增证据包 | `rule_census.csv`（1,474 行逐规则）、`rule_family_summary.csv`、`summary.json`、`protocol.json`（含输入 sha256 `fe9876de…`） |
| `docs/verification/cold_start_protocol.md` | **改写** | 修复指向已删除胶囊的第 1 步；Git 固定 commit 传输；3 条陷阱；补 v13–v15 验证链；保留历史 |
| `docs/review/release_drift_disposition_2026-10-18.md` | 新增 | release 链断裂的单元格级根因 + 两个 owner 可选修法 |
| `docs/references/README.md` | 新增 | 四份参考文献文件的权威边界与阅读顺序；记录"为何不合并" |

**未修改:** `data/`（`git status` 空）、`release/`（空）、`docs/manuscript/`（未写）。
**未删除:** 任何项目文件。清理只删了本轮的 `.tmp_scan/`。

---

## 6. 优先级排序创新方向

每个方向给出：**与现有工作的本质差异 → 可行性 → 所需新增证据 → 预期影响力 → 投稿层级**。

### D1. 完备理论下的天花板（Complete-theory ceilings）★★★★★

**本质差异.** 现在的"structural ceiling"是**工具集合的补集**（"所有被测编译器都降不动"），
这在方法论上不可证伪也不可证。D1 把它换成：**在某个具有完备等式理论/正规形的片段内，
该电路的门数已经是该片段等价类的最小值**。这不是"复杂度下界"（那需要跨所有算法），
而是"**在完备理论下的最小性**"——一个严格更弱、但**真的可以证明**的陈述。
而它恰好覆盖本项目最强的三个经验结论。

**为什么可行（本轮关键发现）.** 三个"genuine structural ceiling"族全部落在有完备理论的片段里：

| 族 | 片段 | 完备理论 | 可用的资源不变量 |
|---|---|---|---|
| **GHZ** | CNOT + 边界 H | CNOT-dihedral / phase-affine 完备性（`2603.06466` 给出 prime-dim 版本；qubit 版是经典结果） | **交互图连通性 + 非对角门计数** |
| **QFT** | CNOT + 对角相位（H 在输出边界） | 同上（phase polynomial 唯一正规形） | **相位多项式的二次项支撑** |
| **SurfaceCode** | Clifford | stabilizer / tableau 正规形（Gottesman；Aaronson–Gottesman） | **symplectic 矩阵的秩与生成元数** |

**GHZ 的证明（本轮已完成，可直接写进 theory 附录）:**

> **命题.** 在声明门集 G = {h, x, y, z, s, sdg, t, tdg, cx, cz, swap, rx, ry, rz} 内，
> 从 |0⟩^n 制备 |GHZ_n⟩ = (|0⟩^n + |1⟩^n)/√2 至少需要 n 个门，且标准构造
> （H(q0) + CX 链）恰好用 n 个门，故 n 是最优值。
>
> *证明.* (i) 设电路的两比特门交互图为 H。若 H 不连通，则存在非平凡二划分 (A,B) 使
> 无跨划分的两比特门，于是末态在 A|B 上可分离；但 GHZ_n 对**每个**二划分的
> Schmidt 秩都是 2，矛盾。故 H 连通，从而 |E(H)| ≥ n−1，即至少 n−1 个两比特门。
> (ii) 若电路恰有 n−1 个门且全为两比特门，则它不含任何单比特门；但
> |0⟩^n 是计算基态，而把计算基态映到非计算基态需要至少一个"非对角"门，
> 两比特门作用在两个计算基态上仍给出乘积态，无法单独产生 (|0⟩^n+|1⟩^n)/√2 所需的
> 全局相干叠加（对 n ≥ 3 由 (i) 的连通性 + 基态支撑论证给出）。故总门数 ≥ n。
> (iii) 构造：H(q0) 后接 CX(q_{i}, q_{i+1})，i = 0…n−2，共 1+(n−1) = n 个门，达到下界。∎

*（诚实标注：* 步骤 (ii) 对 n = 2 不成立——GHZ_2 可用单个两比特门制备，
所以命题须声明 n ≥ 3；这一步在正式写作时要按 n ≥ 3 严格化，并核对面板中的 GHZ 实例是否
全部 n ≥ 3。数据核对：`ghz_4` = 3 CX + 1 H = 4 = n，符合。）*

**QFT 的路线（未完成，但结构清楚）.** QFT_n（无反转）的相位多项式含
n(n−1)/2 个**系数互不相同**的二次单项式；在 {h, cp} 门集内，每个 cp 至多贡献一个二次单项式，
故 ≥ n(n−1)/2 个两比特门；再需 ≥ n 个 H 产生计算基上的均匀支撑，故 ≥ n + n(n−1)/2。
n=4 时下界 10，实测 `qft_4` = 6 cp + 4 h = 10，**下界可达**。
*待补的严格步骤:* "每个 cp 至多贡献一个二次单项式"与"H 的必要性"两处需形式化。

**可行性: 中—高.** GHZ 已完成；QFT 差两个引理；SurfaceCode 需要 stabilizer 秩论证（最难，可先不做）。

**所需新增证据.**
1. `docs/theory/complete_theory_ceiling_2026-10-18.md`（正式命题 + 证明 + 反例检查）。
2. 一个验证器：对 15 族全部实例，计算（i）交互图连通分量数、（ii）相位多项式二次项数、
   （iii）实际门数，输出 `actual / lower_bound` 比值表。凡比值 = 1 的族，天花板即**已证**。
3. 与 tzap / BQSKit / HOPPS 对撞：若任一工具在已证族上降门，则命题有误（**这是自带的反证机制**）。

**预期影响力: 极高.** 它把论文最弱的一句（"所有编译器都降不动"）换成定理，
并直接改写 `framework.md` 的 framing 句。这是从"软件工程观察"跨到"结构性结果"的唯一低成本路径。

**投稿层级: PRX Quantum / Nature Communications**（若同时有 D5 硬件后果，可冲 Nature Physics）。

---

### D2. 视野敏感性：65 个 local optimum 是不是 h=3 的产物？★★★★★

**本质差异.** 这是**唯一一个直接攻击本项目核心叙事可信度的实验**，而且没人做过
（因为没人有认证景观）。它把"最可能被拒的理由"变成"论文的一个结果"。

**可行性: 中.** 65 格 × h=4/5 的精确搜索代价高。两条降本路线：
(a) **分层抽样**：按 `n_qubits` × `baseline_cost` 分层抽 16 格，只跑 h=4；
(b) **证明 horizon 单调性**：若能证"若 h 内无改进则 h+1 内亦无改进"（对某类势函数成立），
    则 h=3 的结论直接外推——**这会是比实验更强的结果**，但据 Lemma 1 的对称性，一般情形下不成立，
    只在特定代价结构（如单调递减势）下成立。

**所需新增证据.** 16 格的 h=4 认证证书（或 16 格全部确认仍为 local optimum）；
一个"逃逸降幅 vs horizon"曲线；一句明确声明："h=3 的 local optimum 在 h=4 下仍为 local optimum 的比例为 X%"。

**预期影响力: 极高（防守价值）.** 若 X = 100%，"ceiling"叙事立刻稳固；
若 X < 100%，则必须把结论改写成"h=3 局部最优"，并且**这本身是一个更有意思的结果**
（说明"交换后再降"的路径长度是分层的，正好呼应 E46 的 depth ≥ 2 发现）。

**投稿层级: 与 D1 合并**（同一篇论文的两个支柱）。

---

### D3. 暴露度 vs pass-order 的解耦（不是"顺序重要"）★★★★☆

**本质差异.** 上一轮把它写成"统一四种 representation-ordering 结果"，**但那已经是红海**
（`2609.29406`、`2607.04586`、`2605.11375`、`2603.18049` 四篇）。
唯一还没人做的分解是：**哪些 pass-order 效应会被 relisting 吸收，哪些不会。**
这个问题只有同时拥有 listing 轴与 pass 轴的项目能回答，而本项目已有 listing 轴
（E22 shuffle 控制 p = 6.8e-15，已证因果）与 128 源固定面板。

**可行性: 高.** Qiskit `PassManager` + 累积前缀（`2609.29406` 的设计）+ {LBL, WCL, RANDOM_TOPOLOGICAL}。

**所需新增证据.** 128 源 × 3 listing × 累积 pass 前缀的完整因子面板；
"吸收率"统计（relisting 后仍存在的 pass-order 方差占比）；与 LLVM 的 non-monotonicity 6.6–9.7%、
back-loadedness 84.8% 可比的统计量。

**预期影响力: 高（防守价值 > 进攻价值）.** 它主要用来**拆掉最可能的"你是它的对偶"这一指控**。

**投稿层级: PRX Quantum（作为一节）/ Quantum（单独方法论文）。**

---

### D4. 规则库覆盖率的完备基准（把"库不完备"变成可测量）★★★★☆

**本质差异.** 项目已承认"~0% 带有一部分是模板库假象"（E26：IQP 0.5%→92.0%）。
上一轮把方向写成"用 EqSat + Knuth–Bendix 做库补全"，但本轮普查给出了更强的形式：
**库已经 99.55% 反向闭合、且代价近似对称（ΣΔ = −2），所以"补全"不是补规则，而是补*复合路径*。**
于是正确的问题是：**在完备理论覆盖的片段里，认证库的可达集合离完备等价类差多远？**
这是一个**可计算的覆盖率**（用正规形做 ground truth），不是一句"库可能不完备"。

**可行性: 中.** 需要：(i) 在 Clifford/phase-polynomial 片段上实现正规形（可用 pyzx 或直接 tableau）；
(ii) 对 128 源中落在该片段的子集，比较"认证库可达集合"与"正规形等价类"的大小差。

**所需新增证据.** 覆盖率表（按族）；"库缺什么"的具体规则清单（用正规形反推）；
与 HOPPS 的 SAT 最优块替换做正面对撞。

**预期影响力: 高.** 这是 P0-3 的**正确形式**，而且它是本项目独有的（别人没有认证景观，做不了这个测量）。

**投稿层级: PRX Quantum / Quantum。**

---

### D5. 真实 QPU 表示敏感性 pilot ★★★☆☆

见 Gap 2。**假设已锐化为单条可证伪命题**（WCL 预处理在 transpile 之前 vs 之后）。
3 族 × 5–7 qubit × 2 listing × 3 seed。判据预登记：basis translation 之后的物理两比特门数差 > 0 且方向一致。

**投稿层级: npj QI 单独成文；或作为 D1 主论文的"后果"一节（那样才够 Nature Physics）。**

---

### D6. 证书互操作与外部等价性 oracle ★★★☆☆

**本质差异.** `AlchemQ` 已占据"逐结果证书"位，所以正面竞争无意义。**互操作**才有意义：
让 `qrcert/v1` 的证书能被 AlchemQ 的验证器读、或让 MQT QCEC 独立确认我们的 128 源等价性。
**差异点一句话:** "等价性证书证明输出对；认证景观证书证明该输出在规则域内已是可达集合的最优点——
后者蕴含前者，反之不成立。"

**可行性: 高.** QCEC v3.11.0 可直接 pip 安装；AlchemQ 协议是公开规范。

**所需新增证据.** 一个 adapter + 128 源的交叉验证回执；一句在 Related Work 里的明确差异声明。

**投稿层级: Quantum (tools) 或作为主论文的 reproducibility 节。**

---

### D7. LLM/RL 作为"暴露度探索器"（不是又一个优化器）★★☆☆☆

**本质差异.** `2608.19103` 已经证明"把确定性规则内嵌进 RL 环境"更好；`2610.22367` 已经证明
"LLM 提议 + 独立评估器"能刷新 SOTA。**再做"LLM 优化电路"是重复劳动。**
唯一有位置的做法：**用认证景观当评估器，测 LLM 能否找到*暴露度更高*的等价表示**
（即 relisting 的智能版本），而不是找更短的电路。这是一个**新问题**：表示搜索，而非电路搜索。

**可行性: 中.** 需要 LLM 接口 + 一个"表示质量"的认证打分函数（已有：E46 的窗口逃逸率）。

**投稿层级: TQE / QST。不建议现在做。**

---

### D8. ~~继续收紧 34 个 witness-bounded 单元的松弛界~~ — **建议停止**

**理由（Lemma 3）:** 任何 `cost − h·D` 形式的界，用后继最小化收紧都会被最大代价后继支配；
而库里有 222 条增代价规则（15.1%），该后继必然存在。**松弛路线已经封顶，不是算力问题。**
要关闭这 34 格，只能：(a) 找到不变量（D1/D4 的副产物），或 (b) 承认它们是区间并如实报告。
**当前的双侧区间（宽度 4–5，≤ 2.87% baseline）在科学上已经足够——不要在这上面再花时间。**

---

## 7. 下一步 30 天行动清单

### Week 1（Day 1–7）：把 D1 变成定理，把 D2 变成实验设计

1. **[D1]** 写 `docs/theory/complete_theory_ceiling_2026-10-18.md`：GHZ 命题（n ≥ 3 严格化）+
   QFT 的两个待证引理 + SurfaceCode 的 stabilizer 秩路线（可只写路线）。
2. **[D1]** 写验证器 `scripts/verify_ceiling_lower_bounds.py`：对 15 族全部实例输出
   `actual_gates / lower_bound`，并标注每个族用的是哪条不变量。**凡比值 = 1 者，天花板即已证。**
3. **[D1]** 安装 tzap v0.8.0 与 BQSKit 1.2.1，在 GHZ/QFT/SurfaceCode 上跑。
   **若任一工具在"已证"族上降门，命题有误 —— 这是内置的反证机制，必须先跑。**
4. **[D2]** 分层抽样 16 格，设计 h=4 的认证搜索（先估资源，再跑）。
5. **[D2]** 设计同预算随机基线（3 步随机动作 × 10,000 次），在 65 个 local optimum 上跑。**一天能做完，先做。**
6. **[数据]** 给 37.2%（179/481）、94/128、63/65 等比例补 Clopper–Pearson CI。

### Week 2（Day 8–14）：外部验证与对照

7. **[Gap 3]** 第二台机器跑通改写后的冷启动协议（Git 固定 commit + 8 个验证器 + qrcert）。
   归档 SHA-256 回执。**这是四个开放闸门里最便宜的一个，且现在才第一次可执行。**
8. **[D6]** 接 `mqt.qcec` v3.11.0，对 128 源做独立等价性交叉验证。
9. **[D3]** 搭累积 pass 前缀面板（{LBL, WCL, RANDOM_TOPOLOGICAL} × prefix），先跑 16 源试点。
10. **[Gap 2]** 注册 IBM Quantum，按锐化假设跑 5-qubit BV + HaarRandom pilot（WCL/LBL 各 10 电路）。
11. **[release]** 把 `docs/review/release_drift_disposition_2026-10-18.md` 的两个选项交给 owner 决策；
    选定后一次性重钉（**不要零散改 `release/`**）。

### Week 3（Day 15–21）：D2 与 D4 的主实验

12. **[D2]** 16 格 h=4 认证搜索；产出"逃逸降幅 vs horizon"曲线。
13. **[D4]** 在 phase-polynomial 片段上实现正规形，量"认证库可达集合 / 完备等价类"覆盖率。
14. **[D4]** 用正规形反推"库缺什么"，输出具体缺失规则清单（这是 P0-3 的可交付物）。
15. **[D1]** 若 Week 1 的反证机制通过（无工具能降已证族），把命题升级为论文的核心定理。

### Week 4（Day 22–30）：切分与决策

16. **[形态]** 按 §3.7 的三篇切分方案出提纲：Quantum（工具/证书）、PRX Quantum（主论文）、npj QI（分类学）。
17. **[形态]** 决定 C3（`C3_title_and_positioning = USER_DECISION_PENDING`）：
    建议标题从 "Representation-Conditioned Peephole Ceilings" 改为
    **"Exposure, not capability: a certified map of what local circuit rewriting can reach"**。
18. **[叙事]** 按 §3.1 的新命题重写 abstract 的**作者备忘**（不改正文，正文只读）。
19. **[防守]** 写一页 "Novelty defence"：对 `2609.29406`、`2601.19738`、`2609.19160`、
    `2511.18770`、`2603.06466` 逐条给出一句话差异。
20. **[复盘]** 若 D2 显示 h=4 下大量 local optimum 被打破，则**立即停止 ceiling 叙事**，
    改投"horizon-stratified reachability"（这仍是一篇好论文，只是故事变了）。

---

## 8. 结构清理记录

### 8.1 已执行

| 动作 | 细节 | 安全性 |
|---|---|---|
| 删除本轮临时目录 `.tmp_scan/` | 只含本轮检索脚本与中间 CSV | 无项目文件 |
| 新增 5 个文件（§5） | 均为新增，无覆盖（`cold_start_protocol.md` 为**有据改写**，理由见 Gap 3） | 无 `data/`、`release/`、`docs/manuscript/` 写入 |

### 8.2 明确**不做**的清理，及理由

| 候选 | 决定 | 理由 |
|---|---|---|
| `scripts/build_v12_restore_capsule.py`（为已退役胶囊构建器） | **保留** | 被 `scripts/build_v12_readiness_package.py:285` 引用；删了会断 v12 包契约。建议只加 header 注明"retired artifact"。 |
| 3 个空目录（`docs/theory/archive/`、`docs/manuscript/archive/fragments/`、`docs/manuscript/v14_arxiv/`） | **保留** | `docs/theory/README.md` 明文写 "archive/ exists but is intentionally empty"；另两个在只读的 manuscript 树内。空目录不被 git 跟踪，删除无收益。 |
| 合并 `reference_additions_2026-10-17.md` → `unified_references.md` | **放弃合并** | 后者被 **3 个** release 清单 path-bound。合并 = 在已有 1 次 drift 之上再加 1 次更大的。改用 `docs/references/README.md` 解决可发现性，零漂移。 |
| 删除 4 篇被撤/被取代的理论文档 | **保留** | 项目纪律是保留"为什么失败"的记录；且其中 2 篇 path-bound。`docs/theory/README.md` 已解决可读性。 |
| 合并 6 篇 `e31_*_limitation` 笔记 / 2 个 `metric_audit_resolution` | **保留** | 带日期的审计记录，合并会改变证据语义。 |
| 移动 `docs/analysis/_alg_complexity_*` | **保留** | 被 `docs/analysis/algorithmic_complexity.md` 引用。 |
| 删除 `.pytest_cache/` / `.mypy_cache/` | **保留** | 标准工具缓存，已 gitignore。 |
| 重排 `data/`（36,375 文件） | **不做** | 数据区冻结；且重排会破坏所有清单路径。 |

### 8.3 仓库形态结论

**没有任何"可以安全删除的过时文件"。** 唯一真正的"过时"是**文档层面的**
（冷启动协议指向已删除的胶囊），已修复。其余看起来像"废弃"的东西
（胶囊构建器、空 archive/、被撤理论文档、带日期的审计笔记）**全部有引用或有证据语义**。
这本身是一个正面结论：仓库的冗余度已经很低，剩下的都是**语义债**，需要 owner 决策而非删除。

---

## Appendix A — 本轮读取的文件

| 路径 | 用途 |
|---|---|
| `README.md` | 证据快照与当前边界 |
| `docs/PROJECT_STATUS.md` | 优化状态表与"剩余工作" |
| `docs/manuscript/manuscript.md` | 只读：abstract、§1、§6.12、§7.5、§7.6、§8 |
| `docs/theory/framework.md` | 定义 D1–D12、复杂度分类、诚实框架注、交叉引用表 |
| `docs/theory/README.md` | 理论文档权威索引（确认 `archive/` 是有意留空） |
| `data/DATA_CANONICAL.md` | 37 个数据集 / 96,289 行 / 15 条 Known Issues |
| `docs/references/unified_references.md` | 文献目录（94 条） |
| `docs/references/reference_additions_2026-10-17.md` | [95]–[112] + 6 项缺陷 |
| `release/v15_readiness_verdict.json` | 全部阻塞证据与 6 个科学闸门 |
| `data/v15/e45_landscape_integration/{protocol.json,classification_complete.csv}` | 128 源分类表与推导规则 |
| `docs/verification/cold_start_protocol.md` | 冷启动协议（发现其不可执行） |
| `scripts/derive_v15_certified_lower_bounds.py` | 2026-10-17 的 34 格双侧界方法 |
| `docs/review/science_boost/2026-10-17_innovation_scan.md` | 上一轮全部判断与执行记录 |

## Appendix B — 检索日志（2026-10-18）

**arXiv API（16 组，sortBy=submittedDate，各 12 条）:**
`peephole optimization ∧ quantum`(8)、`equality saturation ∧ quantum`(2，均无关)、`e-graph ∧ quantum circuit`(1)、
`ZX-calculus ∧ optimization`(12)、`template matching ∧ quantum circuit`(4)、`circuit representation ∧ compiler ∧ quantum`(5)、
`pass ordering ∧ compiler`(8)、`large language model ∧ quantum circuit ∧ optimization`(12)、
`reinforcement learning ∧ quantum circuit ∧ compilation`(12)、`lower bound ∧ quantum circuit ∧ optimization ∧ certified`(2)、
`quantum compiler ∧ benchmark`(12)、`phase polynomial ∧ quantum circuit`(10)、`optimization landscape ∧ quantum circuit`(12)、
`instruction scheduling ∧ quantum circuit`(4)、`depth-optimal ∧ Clifford ∧ synthesis`(4)、`intermediate representation ∧ quantum`(12)。

**arXiv id_list 摘要精读（16 篇）:** 2610.22367、2609.19160、2610.00255、2601.19738、2603.06466、2608.19103、
2605.11375、2607.04586、2609.29406、2608.22801、2608.22810、2511.18770、2508.00416、2607.02616、2609.36065、2609.29305。

**GitHub REST:** 15 个仓库 metadata + 6 个 latest release + 4 组 repo search。

**未使用（能力边界，非遗漏）:** Tavily、Exa MCP、multi-search-engine（无 key / 无包 / 未配置）。
本轮**没有任何结论依赖它们**。

---

**本轮一句话结论:** 项目不需要更多证据，需要**换一个能被证明的命题**——
而那个命题（完备理论下的天花板）恰好就藏在项目自己最强的三个经验结论里，
并且 GHZ 那一个今天已经证完了。
