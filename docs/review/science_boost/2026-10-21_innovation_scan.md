# 2026-10-21 科研全流程体检 + 创新方向扫描（第 6 轮）

**项目**：Quantum Peephole Ceiling（Q-research）
**本轮日期**：2026-10-21
**基线**：`release/v15_readiness_verdict.json`（`as_of` 2026-10-11，verdict `NOT_READY_FOR_PAPER`）
**前轮**：`2026-10-16` / `2026-10-17` / `2026-10-18` / `2026-10-19` / `2026-10-20`
**本轮性质**：执行型。除文献扫描外，产出两项新证据（E49、E50），其中 E50 改变主线叙事的落点。

---

## 0 执行摘要

1. **主线结论变了。** 项目一直用「structural ceiling（结构天花板）」描述优化器失效。E50 表明更准确的
   对象是**「天花板在哪个视野上溶解」**：在 Bernstein–Vazirani 族上，看到改进所需的视野随比特数增长
   （n=4…16 时首现改进视野 h\* = 2, 4, 4, 6, 6, 6, 7），而**改进量恒为 −2 门**。代价（视野）增长、
   收益（门数）不变——这是一条「分离」形状的结论，而不是一条「分类」形状的结论。
2. **E50 还给出了机制**：所有逃逸路径都是 **k 次代价中性的交换 + 1 次相邻逆对消**，减少步永远是同一条
   规则 `pair_v1.self_inverse`。即「优化器看不见一次免费的 Phase-1 抵消，因为它要先做 k 次交换」。
   7/7 条 witness 经 `replay_actions` 重放通过。
3. **E49 完成了 D1 处置**（上轮第一优先项）。双口径结果：128 源面板相对基线的中位改进 **0.224%**，
   相对源电路 **−11.31%**；**59/96 个真实源的认证输出比输入电路还大**。含义：任何把
   「7.83%」「0% 天花板」当作节流量来读的表述都会被审稿人一击命中；但「逃逸是否存在」这一结构陈述
   不受影响（它是同一 listing 内的比较）。
4. **主刊（Nature/Science）门槛的诚实判断**：当前证据链不构成主刊。三条可能路径中，P0-1（视野–增益
   分离定律）是唯一在 6–9 个月内可完成、且不需要新硬件的候选；P2-1（真实 QPU 表示消融）是唯一的
   实证型主刊路径，但受设备与跨平台复现约束。**现实目标仍是 PRX Quantum**，Quantum 为保底。
5. **文献侧**：18 条短语查询、168 条去重记录（≥2023，最新 2026-10-15）。与论文目录（94 条）和补遗
   （18 条）对照后，**6 条必引而目录中缺失**，其中 `2610.06768`（matchgate-Clifford 合成的门集
   依赖复杂度分离）是本轮最重要的方法论模板。

---

## 1 事实基线（本轮独立复核）

### 1.1 证据链现状

| 层 | 事实 | 来源 |
|---|---|---|
| 面板 | 128 源 = 96 真实（e39）+ 32 oracle 夹具（e44） | `classification_complete.csv`（128 行） |
| 分类 | 63 `EXACT_ESCAPE` / 65 `EXACT_H_LOCAL_OPTIMUM`，0 未分类 | 同上 |
| 量 | 94 精确 best cost（93 枚举 + 1 IDA\* 派生）+ 34 witness-bounded | `v15_readiness_verdict.json` |
| 窗口 | E46 76,236 次窗口搜索，0 截断，39,474 条窗口逃逸 | 同上 |
| 裁决 | `NOT_READY_FOR_PAPER` | 同上 |
| 开放门 | `external_cold_start` / `real_qpu` / `release_authority` = OPEN；`C3_title_and_positioning` = USER_DECISION_PENDING | 同上 |

### 1.2 已知差距逐条核验

| # | 上轮记录的差距 | 本轮核验 | 状态变化 |
|---|---|---|---|
| D1 | 34 个长 listing 逃逸单元只有 witness-bounded | 与 verdict `bounded_best_cost_count: 34` 一致；且 2026-10-19 已证这批单元不是「没算完」而是「算完了但不是 h=3 局部最优」 | **不再是绑定项**（见 §3.2） |
| D2 | 无真实 QPU 验证 | `real_qpu: OPEN`，无任何设备结果 | 未变 |
| D3 | 无独立冷启动复现 | `external_cold_start: OPEN`；协议已于 2026-10-18 改为 Git-pinned 传输 | 未变；本轮新增一条环境证据（§3.4） |
| D4 | 无 external execution gate | E48 已建（4 个外部优化器），但缺 BQSKit / tzap | 部分关闭 |
| D5 | 理论：Thm 5/6/8 有缺陷，仅剩初等结果 + Thm 7/9 | `framework.md` v5.4.2 的审计声明与此一致；Thm 5 必要条件已于 2026-10-17 实测（0/27 违反，但集中尺度比声称小 10–40×） | 未变 |

**新增的绑定项是 D1'（上轮发现）**：认证面板的 `baseline_cost` 是归一化电路（`{h,x,rz,cx}`）的贪心
不动点，而归一化本身是膨胀的。本轮 E49 给出该缺陷的完整量化与处置口径。

---

## 2 本轮新证据

### 2.1 E49：源相对重基线（D1 的处置）

**做法**：不重跑任何搜索，只对两份冻结 CSV 做算术。
`classification_complete.csv`（128 行）× `baseline_inflation.csv`（128 行，E48 产出）。
每个源同时计算两种分母：

- `reduction_vs_baseline_pct` = (baseline − best) / baseline —— 面板自己的分母（冻结契约）；
- `reduction_vs_source_pct` = (source_gates − best) / source_gates —— 交出原始电路的人看到的分母。

**脚本**：`scripts/e49_source_relative_rebaseline.py`
**证据**：`docs/review/science_boost/2026-10-21_source_relative/`（`source_relative.csv`、
`family_summary.csv`、`summary.json`）
**输入哈希**：见 `summary.json.inputs`（两文件 SHA-256）

**面板级结果**

| 量 | 全体 128 | 真实 96 |
|---|---|---|
| 相对基线中位改进 | 0.000% | **0.224%** |
| 相对源中位改进 | 0.000% | **−11.31%** |
| 认证输出大于源电路的源数 | 59 | **59** |
| 归一化膨胀中位数 | 1.000× | 1.389× |
| 最大膨胀 | 9.4×（`adder_6`） | 9.4× |

**按族（中位数）**

| 族 | 源数 | 膨胀 | vs 基线 % | vs 源 % | 输出>源 | h=3 逃逸 |
|---|---|---|---|---|---|---|
| Adder | 3 | 8.00 | 4.17 | −666.7 | 3 | 3 |
| VQE | 10 | 7.26 | 0.30 | −623.9 | 10 | 10 |
| QAOA | 6 | 5.73 | 0.56 | −470.6 | 6 | 6 |
| HaarRandom | 3 | 3.85 | 0.09 | −284.7 | 3 | 3 |
| QFT | 2 | 3.76 | 0.00 | −275.6 | 2 | 0 |
| UCCSD_inspired | 8 | 2.84 | 3.03 | −172.7 | 8 | 8 |
| HardwareEfficient | 7 | 2.39 | 2.73 | −132.6 | 7 | 6 |
| IQP | 8 | 1.41 | 4.49 | −11.3 | 5 | 7 |
| QuantumWalk | 10 | 1.22 | 0.12 | −21.5 | 10 | 10 |
| Grover | 6 | 1.01 | 0.43 | −0.6 | 5 | 6 |
| CNOT | 1 | 1.00 | — | +100.0 | 0 | 0 |
| Oracle | 17 | 1.00 | 0.00 | +31.6 | 0 | 1 |
| RandomClifford | 6 | 1.00 | 1.56 | +35.7 | 0 | 3 |
| SurfaceCode | 8 | 1.00 | 0.00 | 0.0 | 0 | 0 |
| GHZ | 1 | 1.00 | 0.00 | 0.0 | 0 | 0 |
| E44 夹具 | 32 | 1.00 | 0.00 | +80.0 | 0 | 0 |

**读法（关键）**

1. 表里存在一个干净的二分：**膨胀 = 1.00 的族**（Oracle / SurfaceCode / GHZ / RandomClifford /
   E44 夹具）源电路本来就在 `{h,x,rz,cx}` 里，两个口径一致；**膨胀 > 1 的族**（其余 10 族）两口径
   完全不可互换。所有「0% 天花板」叙事都落在第二类里。
2. `reduction_vs_source` 为负不代表优化器变差，而是**门集不同**：源电路的 10 个 `ccx` 与归一化后的
   94 个 `{h,x,rz,cx}` 门不是同一把尺子。所以这一列是**编译层指标**，不能当 peephole 指标用。
   它的价值在于阻止把面板内的百分比当成节流量对外陈述。
3. 「逃逸」不受影响：它是同一 listing 内 `best < baseline` 的存在性陈述。63/128、真实 63/96 仍然成立。
   **变的是幅度叙事，不是存在性叙事。**

**处置建议（写入论文时必须做的三件事）**

- 主表同时给两列；`reduction_vs_baseline` 明确标注为「同一归一化 listing 内的贪心改进」。
- 删除或改写所有「7.83% 门数下降」式的对外表述，改为「在同一 listing 内，Phase-1 归约从 0.0000%
  变为 7.83%」——这正是原文的准确说法，风险来自摘要里的转述。
- 任何「0% 天花板」句子后必须紧跟「在 `{h,x,rz,cx}` 归一化 listing、`e44_core_v1` 规则域、视野 3 下」。

### 2.2 E50：视野标定与中性交换前缀（本轮核心）

**问题**：2026-10-19 的 E47 在固定面板上发现「h=3 局部最优在 h=4..7 被推翻」。那是固定面板的
固定视野陈述。决定这件事是**定律**还是**单面板假象**的问题只有一个：首现改进视野是否随电路规模增长。

**做法**：用项目自己的生成器 `make_bernstein_vazirani(seed=42)` 造 n=4…20，用项目自己的
`normalize_circuit` 归一化，复现面板的基线规则（贪心不动点；超 `MAX_BASELINE_GATES=80` 时取归一化
原文），每个规模跑一次到 h=8 的精确有限视野 BFS，契约与冻结面板一致（`e44_core_v1`、200k 状态、30 s）。
对每个规模记录：首现改进视野、该视野下的逃逸 witness、witness 的逐步 `cost_delta`、以及
`replay_actions` 重放结果。

**脚本**：`scripts/e50_horizon_scaling.py`
**证据**：`docs/review/science_boost/2026-10-21_horizon_scaling/`（`bv_horizon_scaling.csv`、`summary.json`）

**结果**

| n | 根代价 | 首现改进视野 h\* | 中性交换前缀 k | 逃逸深度 | 增益 | 重放 |
|---|---|---|---|---|---|---|
| 4 | 7 | 2 | 1 | 2 | −2 | PASS |
| 6 | 10 | 4 | 3 | 4 | −2 | PASS |
| 8 | 10 | 4 | 3 | 4 | −2 | PASS |
| 10 | 13 | 6 | 5 | 6 | −2 | PASS |
| 12 | 13 | 6 | 5 | 6 | −2 | PASS |
| 14 | 13 | 6 | 5 | 6 | −2 | PASS |
| 16 | 16 | 7 | 6 | 7 | −2 | PASS |
| 20 | 25 | —（30 s / 200k 预算内未认证） | — | — | — | 无声明 |

三条可直接写进论文的观察：

1. **h\*(n) 单调不减，且在 n≥6 时全部 > 3。** 也就是说，冻结面板采用的「视野 3」在 BV 族上从
   6 比特起就系统性漏检。这不是预算问题，是视野定义问题。
2. **k = h\* − 1，且 k 严格增长（1, 3, 3, 5, 5, 5, 6）。** 逃逸路径的形状在所有规模上完全一致：
   `k` 步 `cost_delta = 0` 的交换（规则 `exchange.disjoint` / `pair_v1.self_inverse` 的组合），
   最后一步 `cost_delta = −2`。
3. **减少步永远是 `pair_v1.self_inverse`** —— 一条普通的相邻逆对消。**整个现象可以一句话说清：
   优化器看不见一次免费的 Phase-1 抵消，因为它要先做 k 次交换才能让这一对相邻；k 随 n 增长，
   而抵消的收益恒为 2 门。**

**为什么这是本轮最重要的东西**

- 它把「结构天花板」从**名词**变成**函数**：天花板不是电路族的属性，是 (电路族, 视野) 对的属性，
  而视野需求随规模发散。
- 它给出了**代价/收益不对称**：搜索代价随 k 指数增长（观测墙钟 0.69 s → 15.3 s，n=4→16，同一机器），
  收益恒为 2 门。这就是一条分离（separation），而不是一条分类（taxonomy）。
- 它解释了上一轮 E48 的矛盾：为什么外部工具（qiskit L3 / pytket / pyzx）能打败面板基线？因为它们
  不在这个 listing 里做局部搜索，它们重建表示——即**换掉了坐标系而不是加深了视野**。E50 说明在固定
  listing 内加深视野的代价是超线性的，所以「换表示」在渐近意义上更优。

**边界（必须同时写）**

- 单一生成器（BV，seed 42）、单一归一化器、单一规则域 `e44_core_v1`。n=20 是**右删失**，不是「无逃逸」。
- k 的增长形状不是线性的（1,3,3,5,5,5,6），存在平台。拟合 `k ≈ n/2 − c` 会过拟合；正确说法是
  「单调不减且观测到 6」，并把「k(n) 的闭式或下界」列为待证。
- 生成器对 n 的依赖使根代价非单调（n=10,12,14 都是 13），说明 BV 电路的 CNOT 阶梯长度在某区间饱和。
  这本身需要在定理陈述里处理，否则「k 随 n 增长」会被质疑为生成器伪影。

### 2.3 文献与生态（真实执行记录）

| 通道 | 状态 | 结果 |
|---|---|---|
| arXiv API（本项目脚本 `e51_literature_harvest.py`） | 可用 | 18 条短语查询，168 条去重记录（≥2023，2026-10-15 最新） |
| arxiv-watcher skill | 可用（同一 API） | 与上同一批次，未重复调用 |
| arxiv-reader skill | **不可用**：需要 `.env` 中的 `LLM_API_KEY`/`LLM_BASE_URL`，本机未配置 | 以 arXiv abs + 摘要精读替代，见 §2.3.2 |
| tavily skill | **不可用**：需 `TAVILY_API_KEY`，环境无 | 未使用；无任何结论依赖它 |
| web-search-exa skill | **不可用**：需 Exa MCP（`mcp.json` 未配置） | 未使用 |
| multi-search-engine skill | 可用（无需密钥，走 HTML 抓取） | 以 WebSearch + 单引擎抓取替代，覆盖非 arXiv 新闻面 |
| github-trending-cn skill | **部分不可用**：GitHub REST 未认证配额耗尽（403，`remaining: 0`） | 改用 release 页面抓取，见 §2.3.3 |
| citation-manager | 可用（本地对照） | 目录 94 条 + 补遗 18 条 vs 本轮 168 条，缺口见 §2.3.4 |

#### 2.3.1 检索覆盖（18 条查询）

`peephole` / `equality saturation` / `e-graph` / `ZX-calculus` / `template matching` /
`RL + compilation` / `LLM + circuit` / `local optimum + landscape` / `CNOT + lower bound + Clifford` /
`T-count + lower bound` / `phase polynomial` / `exact synthesis` / `quantum compiler + hardware co-design` /
`circuit representation + compiler` / `pass order` / `average-case + circuit` /
`certificate + optimization` / `benchmark + reproducib`

命中结构：ZX 36 条、LLM 51 条、T-count 17 条、average-case 18 条，而 **`peephole` 仅 3 条、
`template matching` 0 条、`equality saturation` 2 条**。这是一个有用的负面信号：**「peephole」这个词
在 2023–2026 的量子编译文献里几乎不用**，社区用「local rewriting / template / ZX simplification /
pass ordering」。论文标题里的 peephole 会降低可检索性，这是标题策略（C3 门）的一个实证输入。

#### 2.3.2 精读的三篇（方法层）

| arXiv | 标题 | 对本项目的意义 |
|---|---|---|
| `2609.16208` | Link-middle-cut lower bounds for Clifford circuit synthesis | **唯一现成的「把经验天花板变成定理」工具**。把 LMC 框架从线性可逆电路扩到 binary symplectic tableau，引入 block-support 连通图 + 行列式不变量，得到可高效计算的**无辅助位 CNOT 下界**；对置换类证明紧（n 比特 k 个环 ⟺ 恰好 3(n−k) 个 CNOT，即使允许任意单比特 Clifford）。可直接用于 SurfaceCode / QFT 源的 CNOT 下界认证。 |
| `2610.06768` | Complexity separations for optimal matchgate-Clifford synthesis | **本轮最重要的模板**。同一个最优合成问题，门集连通图为 path/complete 时 O(n²) 可解，为 tree 时判定版 NP-完全。即「复杂度取决于门集/连通性参数」。把本项目的经验三分法升级为**表示参数化复杂度二分**，就是这条路线。 |
| `2608.22801` | An Exactness Barrier for ZX-Calculus Optimization of Synthesized Clifford+T Circuits | 逐实例可计算的精确性壁垒（分母指数），把「几乎优化不动」解释为壁垒距离地板远近，并给出 101× 的认证因子。是「零改进要有下界解释」的范本。 |

三篇共同的范式：**不报告「优化器做到了多少」，而是报告「任何此类优化器都不可能超过多少」，且该界
逐实例可算。** 本项目目前是前者的极致（76,236 次窗口搜索），后者的储备只有一条
`best_cost ≥ baseline − 6`（2026-10-17 派生）。这是最大的方法论落差。

#### 2.3.3 生态（2026-10-21 快照）

| 项目 | 版本/状态 | 影响 |
|---|---|---|
| Qiskit | **2.6.0（2026-10-16）** | 证据钉在 2.4.1；2.6.0 把多个合成算法迁到 Rust 并升级 QPY 到 v18，`normalize_circuit` 的字节输出可能变，**冻结面板的可复现性依赖 2.4.1**，需在 `requirements` 里显式钉死并在论文写「qiskit 2.4.1」 |
| tket / pytket | 仓库已迁 `CQCL/tket` → `Quantinuum/tket`（上轮记录） | 引用 URL 需更新 |
| PyZX | 仓库已迁 `zxcalc/pyzx`（上轮记录），v0.10.7 | 同上 |
| BQSKit / tzap | **本机未安装**（`bqskit`/`tzap` import 失败） | P1-3 外部门的直接阻塞项，`uv pip install bqskit tzap` 即可，属 1 小时工作量 |
| GitHub REST | 未认证配额 60/h 已耗尽（403） | 生态监控需要 `GITHUB_TOKEN`，否则每轮都会被限流 |

#### 2.3.4 文献覆盖缺口（对照 `unified_references.md` 94 条 + 补遗 18 条）

必引而两处皆无的 6 条：

| arXiv | 为什么必引 |
|---|---|
| `2610.06768` | 门集依赖的复杂度分离；不引则「表示决定可解性」的新颖性被稀释 |
| `2609.16208` | 唯一现成 CNOT 下界工具；不引则「天花板无下界支撑」的批评成立 |
| `2609.17465` | Quantum Compiler Design for FTQC（综述）；定位段必须挂上 |
| `2607.23672` | 算子词汇表本身是瓶颈（logic synthesis 侧的同一论点）；支撑「动作空间由库定义」 |
| `2605.02389` | Action-Space Engineering（RL 路由）；「动作空间」框架的最近邻 |
| `2607.24195` | 并行精确合成（semi-tensor product）；精确合成的对照基线 |

另：`2609.29406`（pass order）、`2610.06142`（等价电路丢失合成选择）、`2609.29210`（表示依赖可恢复性）、
`2601.19738`（Q-PreSyn）已在补遗或目录内，但**摘要正文仍按「no prior study」口径写**（见 §3.1），
这是比缺引更危险的问题：已有五篇 2026 年论文在同一命题上，而摘要声称首次系统刻画。

---

## 3 全流程审查（逐环节，除撰写论文外全覆盖）

### 3.1 科学问题与叙事（对标主刊门槛）

**当前叙事**：表示决定可达动作空间 → 经验三分法 → 若干族存在结构天花板。

**三个问题**：

1. **「首次」失效。** 2026 年已有至少五篇独立论文论证表示/门集/通道顺序门控编译能力
   （`2609.29406` pass order、`2609.29210` 表示依赖可恢复性、`2610.06142` 等价电路丢失合成选择、
   `2601.19738` 局部编辑、`2609.35239` Clifford 模板编译复杂度）。摘要的
   "no prior study has, to our knowledge, systematically characterized when..." 现在不可辩护。
   **必须改成**「我们把该现象从定性观察推进到可认证的有限视野景观」。
2. **「结构天花板」在数据上已被自己推翻。** E48：QFT 2/2、SurfaceCode 1/8 被外部工具打破；
   E50：BV 在 h≥4 全部有改进。摘要仍写「3 families at genuine structural ceiling (QFT, GHZ,
   SurfaceCode; no tested compiler reduces them)」。**这是当前稿件最严重的事实性缺陷**，且是
   自证伪（本项目自己的证据包推翻自己的摘要）。
3. **量级叙事与结构叙事混用。** E49：中位改进 0.224%，59/96 输出比输入大。凡以百分比呈现收益的
   句子都会被要求给出分母。

**升级后的叙事（建议）**：

> 局部优化的可达性不是电路的性质，是 (电路, listing, 视野) 三元组的性质。我们在固定 listing 与
> 固定规则域上给出**可认证的有限视野景观**，并证明该景观的视野需求随规模增长而收益不增长
> （BV 族：h\* 从 2 增到 7，增益恒为 −2 门）。因此「结构天花板」应被理解为「在给定视野下不可见」，
> 而非「不存在」。

这个叙事有四个好处：与已有五篇的差异是**认证 + 视野标定**而非现象；不需要否认外部工具更强；
把「0%」变成「视野不足」；并且天然指向一条可证的分离。

### 3.2 理论框架：哪些可修复、哪些该放弃

| 结果 | 现状 | 处置 |
|---|---|---|
| Thm 1(a)(b) | 已修正并有 E30 直接验证（13,500 trials，27 单元，max \|z\|=2.86） | **保留**，是 LBL 侧最硬的一块 |
| Thm 2(a) | 仅证 Greedy 无动作谓词 | 保留为引理，不要当定理 |
| Thm 5 | 集中性证明不完整；2026-10-17 实测 X 近似 Poisson（离散指数中位 0.976），真实集中尺度约为 `E[X]`，比声称的 `N=n(d−1)` 小 10–40× | **修复方向明确**：改成 Chen–Stein 在有界度线依赖图上的版本（Thm 5-C）。这是 1–2 周的写作量，不是新实验 |
| Thm 6 | 有具体生成器反例 | **放弃**，不要试图修 |
| Thm 7 | 构造性但族人工 | 保留为存在性，不承重 |
| Thm 8 | 前提不相容，已撤回 | **放弃** |
| Thm 9 | BV 上 Ω(1) Phase-2b 优势，自然族 | **保留并加强**：用 SAT 证全局最优（而非仅 k+2 构造），这是最可引的一条 |
| 新 Thm 10（候选） | 2026-10-19 提出 `L ≥ ⌈Δcost/Δ_max⌉` | **这个形式太弱**（BV 上给 L≥1，实际 L=4）。正确的陈述是**中性前缀**：若最便宜改进路径有 k 步零代价前缀，则任何 h≤k 的搜索都不可能认证改进。E50 把 k 从「定义」变成「可测且随 n 增长」 |

**理论侧的判断**：现有理论骨架（初等结构结果 + 两个构造）**不足以支撑主刊**，但足够支撑一篇
PRX Quantum 的理论-实验混合论文，前提是补上 Thm 5-C 与 Thm 10（中性前缀版）。

### 3.3 实验设计（功效、对照、外部效度）

| 问题 | 现状 | 改进项 |
|---|---|---|
| 功效 | 面板 128 源固定，无功效分析；34 个 witness-bounded 单元的区间宽度 4–5（2026-10-17） | 报告每个结论的最小可检测效应；对「0% 天花板」类结论给等价检验（TOST）而非仅不显著 |
| 对照 | 已有 4 个外部优化器（E48）、贪心基线、SOTA 面板 | **缺同预算随机动作基线**（2026-10-18 已列为第二优先，仍未做）。没有它，「逃逸率 65.6%」无法排除「随机也能碰到」 |
| 外部效度 | 96 真实源 + 32 夹具；15 族 | 夹具占 25%，且夹具的「局部最优」是构造必然（成本 1–2），拉低了「65 个局部最优」的信息量。**应把夹具与真实源分开报**（2026-10-19 已指出，仍未落地到论文表） |
| 视野 | 冻结面板 h=3；E47 探到 7；E50 探到 8 | **视野必须成为显式自变量**，不是超参。建议主表改成 h∈{1,2,3,4,6,8} 的曲线 |
| 外部执行 | 无真实硬件 | 见 §3.6 |

### 3.4 数据与可复现性

**优点**（本轮复核确认）：冻结包带 SHA-256 链、每源 `initial_state_sha256` 可重建、
`replay_actions` 对 witness 做语义重放、fail-closed 的 verdict。

**缺陷**：

1. **环境漂移已是现实风险**：Qiskit 2.6.0（2026-10-16）已发布，证据钉在 2.4.1。`normalize_circuit`
   走 `transpile(optimization_level=0)`，其输出字节受版本影响。**必须在 `requirements.txt` 里把
   `qiskit==2.4.1` 钉死**（当前 `requirements.txt` 只有 489 字节，需核验是否已钉）。
2. **conda 环境路径不可直接调用**：本轮实测，`envs/q-research/python -m pytest` 在收集阶段
   21 个 `WinError 193`；同一测试集在 base env（`/d/Downloads/miniforge3/python`）18 项全绿。
   原因是未 `conda activate` 时原生扩展的 DLL 搜索路径缺失。**这直接影响冷启动协议**：
   `docs/verification/cold_start_protocol.md` 必须写明「必须 activate，不能直接调解释器」。
3. **release manifest 仍失败**：`verify_prepaper_release_manifest.py` 因
   `metric_audit_ledger_2026-08-24.csv` 字节不符而失败，已连续四轮。处置建议见 §6。

### 3.5 代码工程质量

| 项 | 状态 |
|---|---|
| 类型检查 | `mypy.ini` 已加（2026-10-17），24 个错误中 1 个真实隐患已修，23 个已记录 |
| 测试 | 本轮选中 18 项全绿（`-k "certified or landscape or horizon"`，base env） |
| 缓存/垃圾 | 0 个 `__pycache__`、0 个 `.pyc`、0 个 `.bak`、`.pytest_cache` 已删 |
| 新增脚本 | 本轮 4 个脚本均带 `EXPERIMENT_ID`、契约块、输出路径、只读声明 |
| 可改进 | `scripts/` 已有 70+ 文件，命名不统一（`e47_*`、`derive_v15_*`、`audit_*`、`verify_*` 混用）。建议按 `<动作>_<对象>_<版本>` 收敛，并在 `scripts/README.md` 建索引 |

### 3.6 外部验证路径

| 路径 | 成本 | 能关闭哪道门 | 判断 |
|---|---|---|---|
| BQSKit + tzap 进天花板面板 | 1 小时（`uv pip install`） | D4 补强 | **立刻做**。GHZ 天花板目前只经 4 个工具检验，是最脆的一条定理 |
| 第二台机器冷启动 | 半天 | `external_cold_start` | 已连续四轮列为高优先，仍未做。这是**唯一不需要任何外部授权的门** |
| MQT QCEC 交叉验证 128 源 | 1 天 | 语义侧独立证据 | 现成工具（`mqt/qcec`），价值高 |
| 真实 QPU | 需账号 + 排队 | `real_qpu` | 见 P2-1；没有它就没有主刊实证路径 |
| 独立第三方复现（非作者） | 需人 | `release_authority` | 只有在前四项完成后才有意义 |

### 3.7 成果形态策略

| 形态 | 可行性 | 依据 |
|---|---|---|
| Nature / Science 主刊 | **当前不可行** | 缺 (i) 有外推力的定律，或 (ii) 硬件实测效应，或 (iii) 广泛意义的复杂度分离。三者皆无 |
| Nature Computational Science / Communications Physics | 有条件 | 需要 P0-1 的 k(n) 定理 + 跨族外推，或 P0-2 的二分 |
| **PRX Quantum** | **现实首选** | 认证景观 + 视野标定 + 一条分离，体量与新颖度匹配 |
| Quantum | 保底，可发表 | 工程严谨度足够；理论贡献偏薄但可接受 |
| npj QI | 保底 | 同上 |
| 纯工具论文（Quantum 的 "software" 轨道） | 可行 | `qrcert/v1` 验证器 + 冻结包 + 重放协议已具备 |

---

## 4 创新方向清单（按优先级）

每条含：与现有工作的本质差异 / 可行性 / 所需新增证据 / 预期影响力 / 投稿层级。

### P0-1 视野–增益分离定律（Horizon–gain separation）

- **本质差异**：现有工作（含本项目前五轮）回答「优化器做到多少」；本方向回答「看到改进的代价如何
  随规模增长，而收益是否随之增长」。E50 已给出反直觉答案：代价增长、收益恒定。
  与 `2610.06768` 同类（门集参数化复杂度分离），但对象是**视野**而非门集。
- **可行性**：高。证据已在手（7 个规模、7/7 重放通过）。剩余工作是定理化与跨族验证。
- **所需新增证据**：
  1. k(n) 的下界证明（BV 的 CNOT 阶梯上，把一对逆门拉到相邻至少需要 ⌈(n−2)/2⌉ 次交换）或反例；
  2. 至少 3 个非 BV 族的同一测量（GHZ / QFT / RandomClifford），证明 k 增长不是 BV 生成器伪影；
  3. n=20 的右删失要么解除（更大预算）要么在文中显式标为删失；
  4. 一条匹配上界：构造性优化器在 k+1 步内达到该增益（证明界是紧的）。
- **预期影响力**：高。给出「局部搜索在量子编译中的渐近不可能性」的第一条具体分离，可被 ZX /
  equality saturation / RL 三条线共同引用。
- **投稿层级**：PRX Quantum（首选）；若 (1)(2)(4) 全部完成且 k(n) 有闭式，可试 Nature
  Computational Science；主刊仍需硬件（见 P2-1）。

### P0-2 表示参数化复杂度二分（Representation-parameterized dichotomy）

- **本质差异**：把项目的经验三分法（3 结构 / 5 原型受限 / 2 实用 / 1 边界）替换为**定理**：
  判定「C 是否为 L-局部最优」在 LBL 下多项式可解（Thm 1(b) 使其退化），在 WCL 下 NP-难。
  没有文献做过「以 listing 为参数」的复杂度分类。
- **可行性**：中高。归约的支点是**最小交换距离 ≈ token swapping**（图上 token swapping 的
  NP-难性是已知结果），E50 的 k 正是这个量。
- **所需新增证据**：
  1. 形式归约：token swapping → WCL 局部最优判定；
  2. 小规模穷举验证（n≤6）「交换距离 = 依赖图上的 token swapping 距离」；
  3. 一个反方向的 poly 算法（LBL 或树状依赖图），构成真正的二分而非单边难度。
- **预期影响力**：高（理论向）。若成立，是 QIP/STOC 级结果，同时给 PRX Quantum 论文提供理论脊柱。
- **投稿层级**：QIP / STOC / FOCS（理论）；Quantum（期刊版）。不进主刊。

### P0-3 双口径报告（D1 处置，本轮已完成）

- **本质差异**：不再把面板内百分比当节流量。这是**口径修正**，不是新发现，但它决定论文是否会被
  一句「你的分母是什么」击倒。
- **可行性**：已完成（E49）。
- **所需新增证据**：无。需在正文/补充材料同时给两列，并在方法节解释门集不可比。
- **预期影响力**：防守型，但必要。
- **投稿层级**：不单独发表，作为 §5 与补充材料。

### P1-1 用 LMC 下界认证天花板（把经验变成定理）

- **本质差异**：当前「SurfaceCode 8/8 无逃逸」是搜索结论（h=3，`e44_core_v1`）；
  用 `2609.16208` 的 LMC + 行列式不变量可给出**与规则库无关**的 CNOT 下界。两者相等即为
  「该电路在 CNOT 计数上已最优」的定理级陈述。
- **可行性**：中。需要 (a) 从 Qiskit 电路抽 binary symplectic tableau；(b) 实现 block-support
  连通图 + 行列式不变量；(c) 处理含 H/S 的情形（该文已覆盖任意单比特 Clifford）。
- **所需新增证据**：8 个 SurfaceCode 源 + 1 个 GHZ 源的 LMC 下界，与冻结 `baseline_cost` 比对；
  若下界 < 基线，则「天花板」被降级为「视野内天花板」，必须如实报告。
- **预期影响力**：中高。这是唯一能把「ceiling」写进定理而不是写进摘要形容词的路径。
- **投稿层级**：PRX Quantum / Quantum 的一节。

### P1-2 GHZ 定理前提重述 + 全局相互作用反例

- **本质差异**：`GHZ_n ≥ n` 只在 1-/2-比特门集下成立。`2510.20730` 表明任意 Clifford 序列在
  可编程全连接多比特纠缠门下只需 ≤ 4 次应用。不写清前提，审稿人第一轮就会给出反例。
- **可行性**：高（写作 + 一个门集探测实验，E48 已有 gate_set_probe）。
- **所需新增证据**：把定理陈述改成「(circuit, 1-/2-qubit gate set) 上的陈述」，并加一句
  全局门集反例；E48 Part A 的 n=4…20 数据可直接复用（0 违反）。
- **预期影响力**：防守型；不做则整条定理作废。
- **投稿层级**：定理修订，不单独。

### P1-3 外部执行门补强（BQSKit + tzap + 第二台机器）

- **本质差异**：目前 GHZ 天花板只经 4 个工具检验（qiskit L3 / pytket FPO / pytket RR / pyzx）。
  BQSKit（QSearch/LEAP）与 tzap 是唯二未测的主流工具，且都可能打破它。
- **可行性**：高。`uv pip install bqskit tzap`；接口已由 E48 的 4-tool 框架铺好。
- **所需新增证据**：GHZ_n n=4…20 上两工具的 CNOT/总门数；SurfaceCode 8 源 + QFT 2 源同跑。
- **预期影响力**：防守型，但**决定 P1-2 定理能否存活**。
- **投稿层级**：补充材料。

### P1-4 理论修复两件（Thm 5-C、Thm 9 全局最优）

- **本质差异**：Thm 5 从「错误证明」改为「正确但更弱的 Chen–Stein 版本」；Thm 9 从「构造 + 数值」
  改为「SAT 证全局最优」。两者都是把可被攻击的点变成可引用的点。
- **可行性**：Thm 5-C 是纯写作（1–2 周）；Thm 9 的 SAT 需编码（BV n≤10 规模可行，2–3 周）。
- **所需新增证据**：Thm 5-C 的定理陈述 + 依赖图有界度条件；Thm 9 的 UNSAT 证书（DRAT 可参考
  `2609.20873` 的 refutation certificate 范式）。
- **预期影响力**：中。决定理论节是否被整段删除。
- **投稿层级**：理论附录。

### P2-1 真实 QPU 表示消融（唯一的主刊实证路径）

- **本质差异**：现有全部证据都是经典模拟的门数计数。主刊需要**物理效应**：同一算法、两种 listing、
  固定 shot 预算，测保真度/分布距离差异，且效应量大于校准漂移。
- **可行性**：低-中。需 IBM Quantum 或 IonQ 账号；需先做校准漂移基线（同日重复同一电路 3 次）。
- **所需新增证据**：≥2 个平台、≥5 个电路、效应量 > 3σ 校准漂移；外加一个「表示选择改变编译后
  深度 → 改变退相干」的因果链。
- **预期影响力**：高（若成立）。这是唯一能把「表示很重要」从门数论证升级为物理论证的路径。
- **投稿层级**：Nature / Science（需跨平台）；单平台则 Nature Communications / PRX Quantum。

### P2-2 跨族预测律（原 P2-1 的收敛版）

- **本质差异**：从「族级三分法」到「给定 (n, 深度, 规则域) 预测 h\*」。2026-10-20 记录该模型
  out-of-family 失败；E50 提供了新的自变量（k 与 n 的关系），值得重试一次。
- **可行性**：中。需 ≥6 族的 h\* 测量（E50 框架可直接复用，每族 1 小时）。
- **所需新增证据**：6 族的 h\*(n) 曲线；留一族外推的预测误差。
- **预期影响力**：中高（若 MAE 可控）。
- **投稿层级**：PRX Quantum；若外推成功可支撑主刊的「定律」要求。

---

## 5 投稿层级判断（汇总）

| 目标 | 需要什么 | 现状差距 |
|---|---|---|
| Nature / Science | 定律 + 外推 / 硬件实测 / 广泛复杂度分离 | 三者皆无；P0-1+P2-1 同时完成才有讨论空间 |
| Nature Comput. Sci. / Commun. Phys. | P0-1 完整（k(n) 定理 + 3 族验证） | 缺定理与跨族 |
| **PRX Quantum** | 认证景观 + 视野标定 + 一条分离 | **缺 P0-1 的定理化 + P1-1 的下界** |
| Quantum | 工程严谨 + 有限视野景观 | 基本具备，缺 P1-2/P1-3 的防守 |
| npj QI | 同上 | 具备 |
| 工具轨道（Quantum software） | 验证器 + 冻结包 + 重放协议 | 具备 |

**一句话**：当前证据链的**科学含量**够 PRX Quantum，**叙事**还停在「我们测了很多」，
**理论**只有两个构造 + 一个待修的集中性结果。把 E50 定理化，是把三者同时抬一级的最短路径。

---

## 6 下一步 30 天行动清单

按「先防守、再定理、后扩张」排序。每项标注产出物与验收条件。

**第 1 周（防守，全部不需要外部资源）**

1. **BQSKit + tzap 进天花板面板**（P1-3）。产出：`scripts/e52_bqskit_tzap_falsifier.py` +
   证据包。验收：GHZ n=4…20、SurfaceCode 8 源、QFT 2 源全部跑完，等价性经幺正/tableau 校验。
2. **修 GHZ 定理陈述**（P1-2）。产出：`docs/theory/ghz_premise_note_2026-10-2x.md`。
   验收：定理含「1-/2-比特门集」前提 + 全局门集反例一句 + E48 Part A 引用。
3. **处置 release drift**（连续四轮未决）。产出：`docs/review/release_drift_disposition_2026-10-2x.md`
   的**决策**（建议：声明 drift、重钉 hash、在 manifest 里加 `drift_disposition` 字段，不重写历史）。
   验收：`verify_prepaper_release_manifest.py` 退出 0 或明确 FAIL 且带 owner 签字的豁免。
4. **钉死 qiskit==2.4.1**。验收：`requirements.txt` 与 `environment.yml` 一致，`pip check` 通过。

**第 2 周（定理化 P0-1，最高杠杆）**

5. **k(n) 下界证明或反例**。产出：`docs/theory/horizon_obstruction_2026-11.md`。
   验收：给出 BV 上 k ≥ ⌈(n−2)/2⌉ 的证明（或指出构造性反例并下调主张）。
6. **跨族 k 测量**（GHZ / QFT / RandomClifford / HardwareEfficient）。产出：扩展 `e50` 的
   `--family` 参数 + 证据包。验收：4 族 × n∈{4,8,12,16} 的 h\* 与 k 表。
7. **匹配上界**：构造性优化器在 k+1 步内达到 −2 增益。验收：算法 + 在全部测点上验证最优。

**第 3 周（下界与复杂度）**

8. **LMC 下界移植**（P1-1）。产出：`scripts/e53_lmc_cnot_bound.py`。验收：8 个 SurfaceCode 源的
   CNOT 下界，与 `baseline_cost` 同表；下界低于基线的源如实标出。
9. **同预算随机动作基线**（2026-10-18 起连续三轮未做）。验收：65 个局部最优 × 200k 随机动作，
   报告随机碰到改进的比例——这是「65 个局部最优」是否信息量的直接检验。
10. **P0-2 归约草稿**。验收：一页纸的 token-swapping → WCL 局部最优判定归约，含 n≤6 穷举校验脚本。

**第 4 周（外部与整理）**

11. **第二台机器冷启动**（`external_cold_start`）。验收：非作者机器上按 `cold_start_protocol.md`
    跑通 verifier 链，产出 receipt。**协议需先加一句「必须 conda activate」**。
12. **MQT QCEC 交叉验证 128 源**。验收：128/128 语义一致或差异逐条定位。
13. **文献合并**：把 §2.3.4 的 6 条并入目录。注意：`unified_references.md` 被三个 manifest 绑定，
    合并会产生第三次 drift——**必须先做第 3 项的 drift 决策**，否则只追加到补遗文件。
14. **重写摘要的三处事实性问题**（不是"撰写论文"，是纠错）：删除「3 families at genuine
    structural ceiling」、删除「no prior study」、给所有百分比加分母说明。这三处是自证伪风险。

**验收口径**：第 2 周的 5–7 项全部完成，则具备把主线从「有限视野景观」升级为「视野–增益分离定律」
的条件，可开始 PRX Quantum 投稿包；否则退回 Quantum 轨道。

---

## 7 约束遵守与清理记录

**红线**

- `data/`、`release/`：**未修改**。本轮所有读取为只读；`git status -- data release` 为空。
- `docs/manuscript/`：**只读**。本轮仅阅读摘要与状态注记，未写入。
- 新建证据文件全部带日期与来源：`docs/review/science_boost/2026-10-21_*`、脚本头部含
  `EXPERIMENT_ID` 与契约块。
- 未删除任何项目文件。

**清理**

| 动作 | 对象 | 理由 |
|---|---|---|
| 已删除 | `.pytest_cache/`（11 KB） | 生成物，可重建 |
| 未删除 | `data/` 下 9 个空目录 | 属冻结数据区，删除即改动哈希链覆盖范围 |
| 未删除 | `docs/` 下 340+ 个未被 manifest 绑定的文件 | `prepaper_release_manifest.json` 绑定 248 条路径；在 drift 决策（第 1 周第 3 项）完成前删除任何一条都会新增一条 drift 记录 |
| 未删除 | `docs/review/science_boost/2026-10-16..20` 各轮 | 科研留痕优先于整洁；索引见 `science_boost/README.md` |

**合并候选（待 drift 决策后执行）**

1. `docs/review/science_boost/2026-10-16_innovation_scan.md` 已被 10-17 修订，可在索引中标注
   「已被取代」，但**不删**（它记录了当日 08:19 草稿的错误，是有价值的负面留痕）。
2. `docs/review/e31_*_2026-08-2x.md` 共 8 份，主题相邻（对照扩张、因子帕累托、族推断、宿主环境、
   帕累托聚合、预分析勘误、语义重放、传递源溯源）。建议合并为一份 `e31_review_register_2026-08.md`
   并保留原文为附录——**但它们在 manifest 内，需先处置 drift**。
3. `docs/theory/` 10 份文档已有 `README.md` 索引（2026-10-16 建），无需再合并。

**本轮新增文件清单**

| 路径 | 类型 |
|---|---|
| `scripts/e49_source_relative_rebaseline.py` | 新证据脚本（E49） |
| `scripts/e50_horizon_scaling.py` | 新证据脚本（E50） |
| `scripts/e51_literature_harvest.py` | 文献抓取（arXiv API） |
| `scripts/e51b_github_ecosystem.py` | 生态探测（受 403 限流，结果已如实记录） |
| `docs/review/science_boost/2026-10-21_source_relative/` | E49 证据包（3 文件） |
| `docs/review/science_boost/2026-10-21_horizon_scaling/` | E50 证据包（2 文件） |
| `docs/review/science_boost/2026-10-21_literature_scan/` | 文献包（`arxiv_records.json`、`uncovered_ids.json`、`query_log.json`、`github_ecosystem.json`） |
| `docs/review/science_boost/2026-10-21_innovation_scan.md` | 本文件 |

---

## 附录 A 检索与执行日志

**文献**
- 18 条 arXiv 短语查询，2026-10-21 执行，`sortBy=submittedDate`，每条上限 100。
- 168 条去重记录，最早 2023-01-01 起，最新 2026-10-15。
- 覆盖判定：`docs/references/unified_references.md`（94 条）+ `reference_additions_2026-10-17.md`
  （18 条，[95]–[112]）。
- 精读 3 篇（abs 全文 + 摘要 + 方法段）：`2609.16208`、`2610.06768`、`2608.22801`。
- 未使用通道及原因：`arxiv-reader`（缺 LLM key）、`tavily`（缺 key）、`web-search-exa`（缺 MCP）、
  `github-trending-cn`（GitHub 未认证配额 403）。**无任何结论依赖未使用的通道。**

**执行**
- E49：纯算术，输入为两份冻结 CSV，秒级。
- E50：8 个规模 × 单次 BFS 到 h=8，总墙钟约 63 s（n=20 触发 30 s 上限）。
- 测试：`pytest -k "certified or landscape or horizon"` → 18 passed（base env）。
- 类型：未重跑 mypy（本轮未改 `src/`，2026-10-17 结论仍适用）。

**环境**
- 证据环境：qiskit 2.4.1（`/d/Downloads/miniforge3`，base）。
- `envs/q-research` 直接调用解释器时收集失败（21 × `WinError 193`），需 `conda activate`；
  这是冷启动协议的一处必要补充，不是代码缺陷。

## 附录 B 本轮数值摘要

**E49**

- 128 源；相对基线中位 0.000%（全体）/ 0.224%（真实 96）；相对源中位 0.000% / −11.31%。
- 59 个源（全部为真实源）认证输出 > 源门数。
- 膨胀中位 1.000×（全体）/ 1.389×（真实）；最大 9.4×（`adder_6`）。
- 逃逸率不变：49.22%（全体）/ 65.63%（真实）。

**E50**

- h\*：2, 4, 4, 6, 6, 6, 7（n=4,6,8,10,12,14,16）；n=20 右删失。
- k = h\* − 1：1, 3, 3, 5, 5, 5, 6。
- 增益恒为 −2；减少步恒为 `pair_v1.self_inverse`；7/7 `REPLAY_PASS`。
- 墙钟：0.69 → 15.25 s（n=4→16，同机），约 22×。
