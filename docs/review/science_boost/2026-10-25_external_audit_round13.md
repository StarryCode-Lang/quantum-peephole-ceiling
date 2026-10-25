# Round 13 — 外部审计与优化执行记录（2026-10-25）

**性质**：review-grade（不在 release 哈希链内）。本轮由四路并行外部审计
（代码深审 / 数据证据链审计 / 顶刊文献侦察 / ScholarEval+GRADE 批判性评估）
驱动，随后当场执行了全部 P0 修复与高价值免费推导。`docs/manuscript/` 按
用户指示**未做任何改动**（论文撰写暂缓）；所有新证据均为 review-grade
包，冻结 `data/`、`release/` 未动。

---

## 0. 摘要（TL;DR）

1. **发现并修复一个真实的引擎正确性缺陷**（successor-generation bug）：
   `iter_legal_actions` 在规则匹配 ≥2 个 location 时丢弃先前 location 的
   后继（"last location wins"）。冻结 v14/v15 受影响面：**6/64 个
   EXACT_H_LOCAL_OPTIMUM 为假**（真值 best 8 vs 冻结 10）、5/14 个逃逸
   单元精确量错误、**1/1 派生单元失去重认证**。修正版 128 单元重认证：
   **94 → 93 个精确 best-cost**，8 个陈述值改变（合计 −14 门）。
2. **文献扫描（31 组查询 / 17 次原始抓取）：无撞车（NO SCOOP）**。五个最近
   邻各自认证不同对象；新增必引 15 条（AlchemQ / Q-PreSyn / TZAP / Quasar /
   GUOQ / POPQC 等），已登记 `docs/references/search_ledger.md` §12。
3. **三项引擎增强落地并通过 E44 oracle 5120/5120 字节级一致性验证**：
   `filter_rule_scope` 去重、可采纳逐门下界剪枝、`state_wcl` 转换器——
   分别解锁全规则库面板、bounded 单元精确化、WCL 窗口剖面。
4. **两个新 review-grade 证据包**：
   `2026-10-25_engine_successor_fix/`（修正版重认证）与
   `2026-10-25_escape_geometry/`（E64 冻结数据免费推导，含
   bounded 单元精确化追踪器与窗口→整列表完美分离 p=2.8e-36）。
5. **批判性评估**给出 5 个最薄弱点（WL-1..5）与 12 条 overclaim 的
   精确改写建议；**创新路线图 D1–D12**（ledger §12.4）映射为
   P0–P6 执行计划（§7）。

---

## 1. 引擎正确性缺陷：发现、修复、修正版重认证

### 1.1 缺陷

`src/optimisation/certified_landscape.py` `iter_legal_actions`：
对每个规则按 signature 匹配多个 location 时，内层循环用
`local_actions = list(local)` **覆盖**而非累积——只有最后一个 location
的动作被产出。完整引擎 `legal_actions`（逐状态物化）不受影响；冻结
v14/v15 的全部面板（compact / IDA* / E46 / v15 积分）经由 compact 引擎
使用了缺陷生成器。此前所有验证门为何全绿：E44 oracle 只在 4–9 门小实例
上验证完整引擎；compact-vs-reference 一致性测试只用了单一 4 门中性态；
E46 验证器用同一缺陷引擎复搜子样本；v15 积分只做派生不搜索；回执只钉
payload 哈希、不含引擎源哈希。

### 1.2 影响面（冻结 v14/v15）

| 变更类型 | 单元数 | 内容 |
|---|---|---|
| AGREE | 82 | 含全部 32 个 E44 oracle 单元与试点对照 |
| RESOURCE_BOUNDED_BOTH | 34 | 修正后 incumbent 与冻结**逐一致**（0 改进 0 退化） |
| FALSE_OPTIMUM_NOW_ESCAPE | 6 | 冻结 best 10 → 真值 8，逃逸深度 3 |
| ESCAPE_DEPTH_OVERSTATED | 3 | 深度 3 → 2，best 不变（高估=安全方向但量错） |
| ESCAPE_COST_STATED_WRONG | 2 | 21→20、52→51 |
| FROZEN_EXACT_NOW_TRUNCATED | 1 | 派生单元 `e39:b2f83603…`（QFT, baseline 148）：修正后引擎每状态后继更多，双引擎均触 200k 状态预算，H-local 结论在冻结预算下既未确认也未反驳 |

**修正后头条**：94 → **93** 个精确 best-cost（58 精确 H-local + 35 精确
枚举逃逸 + 0 派生）；94 中 8 个陈述值改变、合计 **−14 门**。69/69 修正
见证重放 REPLAY_PASS；确定性子样本 10/10 字节级一致；生产运行 20.6 分钟
（compact 1206 s / 32 单元触 30 s 上限；IDA* 32.4 s / 0 截断）。

E46 窗口面板：抽样复检（80 深度-1 探针 + 50 完整引擎复搜）0 不匹配——
数值上稳健（16 门窗口由辅助规则主导、在 755–772 行完整收集），但
**原则上需在 v16 用修正引擎重跑**方能恢复其"exact"用语。

### 1.3 修复与防复发

- 修复：跨 location 累积后单次排序（保持文档规定的 rule-by-rule、
  规则内 sort_key 顺序）；4 行 diff。
- 新测试（tests/test_v13_certified_landscape.py）：多 location 回归测试
  （先红后绿验证）、60 例固定种子随机重复模式属性测试（0.05 s）、
  引擎哈希测试。
- 溯源补洞：`src/provenance.py` 新增 `ENGINE_SOURCE_FILES` +
  `engine_source_hashes()`（不动旧 `DEFAULT_SOURCE_FILES`，验证
  `reproduce_all.py --verify` 前后字节一致绿色）；重认证包内
  每单元钉引擎源哈希。
- **推论**：冻结 v14/v15 包在修正引擎下不再字节可再生 → 需要 **v16
  重钉周期**（重跑 compact + IDA* + E46；34 个 bounded 的两侧区间中
  下界为引擎无关推导、见证重放不受影响，全部存活）。

---

## 2. 引擎增强（全部通过验证）

1. **`filter_rule_scope` 统一规则域过滤**：三处重复（`_quartz_index`、
   `_maximum_single_step_reduction`、`derive_v15_certified_lower_bounds.py`）
   收敛为一个导出助手；pinned 库上 149 核心规则 id/顺序字节一致。
   全规则库（1,474 条）面板由此变成配置项。
2. **可采纳逐门下界进入引擎**：`admissible_remaining_cost_lower_bound`
   （= max(Σ_g max(0, n_g − H·r_g), max(0, cost − H·D))，文档字符串给出
   可采纳性论证）；接入 IDA* `lower_bound`（取 max）与 compact 的
   branch-and-bound 剪枝（不触碰 BFS 状态枚举，state set 字节不变）。
   验证：E44 oracle 1024 实例 × horizon 0–4 **5120/5120 结论与
   certificate_sha256/state_set_sha256 字节一致**；46 个 e39 试点单元
   A/B 全一致；compact 8.204→7.423 s（−9.5%，最大单元 −34%），
   IDA* +3.9%（认证开销的诚实代价）。在 e44_core_v1 域内下界很少超过
   粗界；**其真正收益在 full 规则域集中名称实例上**（v15 CSV 证实该
   面板上 lb_class ≤ lb_aggregate）。
3. **`state_wcl`**：LandscapeState 上的 WCL 排序纯函数（主导线 =
   最小 qubit、逐 qubit 依赖边去重、Kahn 最小堆按
   `(primary_wire, original_index)`），与 Qiskit
   `WireTraversalPreprocessor` 在 12 个清单上顺序全等；24 个随机清单
   语义等价 + 代价不变 + 字节稳定。E46 runner 的 `root_kind` 管道
   已有插入点，WCL 窗口剖面由此解锁。

全套 pytest：**631 通过**；唯一失败为先前已存在的
`test_direct_dependencies.py`（已提交脚本 e53/e55/e58 引入未声明依赖
bqskit/tzap），与本轮无关，待 `scripts/README.md` 索引清理时一并处理。

---

## 3. 数据与证据链审计（发现→行动项登记，未改 manuscript）

1. **§6.12 数字块与冻结面板矛盾**（最高优先级修正项）：正文
   "123 greedy fixed-point roots / five raw-listing roots" vs 冻结数据
   **78 greedy / 50 raw**（44/50 携带窗口；34 个源根 <8 门无窗口）；
   37.2% = 179/481 是 **h3-only 切片**（h2 = 229/1228 = 18.6%）；
   "五个原始列表根出现深度-1 逃逸" 实为 **49/50 raw 根、38,606 个
   深度-1 逃逸**。179/481 本身精确； surrounding 计数错。
   `docs/EXPERIMENT_HISTORY.md` 80–83 行同病。
2. **claim_evidence_table.csv 停在 v10 时代**：E30–E37、E38–E46、
   v13–v15、science_boost E47–E63 全部为"孤儿证据"（无 claim 行引用）；
   C3 引用不存在的 `data/v5/e12/`（canonical 为 `data/v4/e12/...`）；
   C12 缺 E26 `sampled200` 估计量 201 行 caveat（修正版在
   `data/v10/prepaper/e26/`，仅 C13 引用）；C4 的 power=0.126 靠
   caveat 列兜底；"Cirq/t|ket> 需独立验证" 的 caveat 相对
   `data/v11/e20_corrected` 已过时。
3. **断链指针**：§6.11 引用的 `docs/manuscript/evidence_integration_map.md`
   不存在（哈希实际在 `release/v14_readiness_verdict.json` 与各回执）。
4. **统计合同缺失**（WL-4 对应）：76,236 窗口为同源相邻重叠样本，
   需按 source 聚类（n=128 簇）做设计式推断；37.2% 与 verdict 的
   46.85/47.69/55.86/57.01% 需一张分母对账表（E64 包已给雏形）。
5. **薄层**：32 个 E44 夹具单元 cost 1–2（退化层）；E13 n=56、
   E25 n=66、E35 n=5、E36 n=3；E16 power=0.126；E31 广义估计量
   power 0.07055（new-family 主张被正确 BLOCK）。
6. **34 个 bounded 单元精确化路径**（E64 追踪器）：26 便宜（b≤250，
   其中 5 个 state_budget 族只需把 200k 预算提到 1–2M）、3 中等
   （HaarRandom nq4, b≈528）、尾部 QuantumWalk nq=8/9（7,514/12,422
   门，b=1682/2677）大概率永久预算界。同构组（QAOA nq4、VQE nq4/6/8）
   搜索统计字节相同——**一次枚举可清最多 4 个单元**。

---

## 4. 文献扫描结论（详见 ledger §12）

- **无撞车**。最近邻表：AlchemQ（等价性证书，非最优性）、
  POPQC/2502.19526（oracle-相对、by-construction 达成）、
  TZAP（预计算 MURM 内极小性）、Fischbach（穷举无证书）、
  Quasar（e-graph 闭包内步数限最优）。本项目独占：
  **对任意贪婪不动点的绝对语义逐实例分类 + 分类完全景观**。
- 词汇碰撞两个需在正文划界："phase transition"（2608.00189 的 SA
  热力学相变 vs 本项目被驳斥的结构敏感性假设）；"landscape"
  （2505.05380 的变分参数景观 vs 重写景观）。
- 基线机会（按可执行度）：TZAP（映射式极小 vs 认证逃逸深度的
  覆盖对比）、QALM（其逃逸点应集中在被分类为非最优的单元）、
  GUOQ（resynthesis-as-oracle 的 oracle 敏感性研究 D12）、
  Quasar（闭包最优 vs 认证最优差距）、Fischbach（同窗口
  search-vs-certify 对照）。
- 工具链新鲜度：Qiskit 2.4.1 → 2.5.0（peephole 双门 pass）→
  2.6.1（L3 非单调缺陷已修，E61/E63 闭环）；mqt-core 4.0.0 移除
  ZX 库；Quartz 自 v0.3.2（2024-12）休眠。

---

## 5. 批判性评估摘要（完整版见本节末登记的评分与清单）

**ScholarEval 记分卡**：问题表述 4/5；新颖性（按现稿）3/5、（按
repo 前沿理论）4/5；方法与可复现性 4/5（全库最强维度）；证据–主张
对齐 3/5；理论可靠性 3/5；写作呈现 2/5（1478 行千层稿）；文献覆盖
3/5。**论文的新颖性目前活在正文没有引用的文件里**（定理 1–4、
旋转间隙分解、湮灭墙）。

**五个最薄弱点（WL）**：
- WL-1 **"provable/exact k+2 BV optimum" 与自家 C13 回执矛盾**
  （manuscript.md:43/772/1333 vs claim_evidence_table.csv:13：
  "achieved reduction … not that n+2 is a global gate-count optimum"）。
  首选解法：证明 BV 下界引理（{H,X,CNOT} 上 U_f 需 ≥k CNOT、
  ≥k+2 门；估计数日内可证）——一句话由虚变实，全稿最高价值单点。
- WL-2 **"certified" 无单一定义**、等价校验多为内部引擎（QCEC 只盖
  closure 输出层）。需一段定义（scope/horizon/window/等价契约/
  QCEC 覆盖范围）+ 见证集归档或把确定性再生 runner 入证据包。
- WL-3 **128 单元便利面板**（32 个夹具退化；绝对锚点片段内面板
  平凡：45 个 rz 全在下界上）。解法：fragment-native 基准
  （6 族 × ≥8 实例 × n=4..64，解析 s）+ E62 重跑 + 2 个外部
  电路集（MQT Bench/RevLib 子集）。
- WL-4 **窗口统计的相依性/分母/多重性**（见 §3.4）。
- WL-5 **旋转间隙理论的四层相对性**（⊥ 实现-引擎一致≠引擎-物理
  一致；closure 最优性 ⊥-重排相对；绝对下界限 {x,rz,cx} 片段；
  Prop 2 充分非必要）。解法：⊥ 公理化 + 逐规则矩阵证明（数日）、
  Prop 2 升级为片段内 iff、Lemma 1 标注文献来源并对照
  2610.01024、每个收益数旁印双门列。

**Overclaim 扫描**：12 处（BV×3、Thm1(b) 缺生成器限定词、"generalizes
strongly" 领先于 hedge、"14 match" vs 表 19 的 13/1/3、"2.20×" 缺
72 对称控制子集限定、"No production compiler" 全称量词越权、
76,236 exact 缺 scope/horizon 限定、"closed the classification
bookkeeping" 缺 34-bounded 后缀、"single most citable result" 删除、
"8–9×" 缺非对称计时限定）。逐条改写文案已存 round-13 评审底稿
（本轮未动 manuscript，撰写恢复时直接取用）。

**缺失理论清单**：BV 下界引理（数日）、⊥ 物理交换可靠性（数日）、
closure 不动点代价不变性 Conjecture 1（数日至数周）、Prop 2 iff
化（数日）、content-class 复杂度分离（数周，锚点：CNOT-distance
NP-完全 2608.03825 / token swapping 2601.09681）、窗口景观抽样理论
（数日，调查统计标准）、可选 Thm 5-C Chen–Stein Poisson 近似（数周）。

---

## 6. E64 逃逸几何包关键结果（冻结数据免费推导）

- 逃逸率图集（显式分母，含对账表）：全源逐配置 0.4685/0.4769/0.5586/
  0.5701；greedy-only w8 15.9% / w16 32.1%（h3 切片 37.2% / h2 18.6%）；
  raw w8 48.5% / w16 57.1%。
- **窗口→整列表逃逸完美分离**：2×2 = [[62,1],[0,65]]（Fisher
  p=2.8e-36；stdlib 精确实现与 scipy 1.13.1 机器精度互核）；唯一
  不一致是 Oracle-nq4（贪婪根塌缩到 8 门窗口最小值以下）。
  "正确性信号"从描述性统计升级为可检验的预测律。
- 分支律：states_seen 均值 16.38/39.71/53.21/220.65（max 819），
  拟合 states ≈ c·b^h，b≈2.42（w8）/4.15（w16）。
- 增益分布（39,474 逃逸）{1:2423, 2:14999, 3:12080, 4:4824, 5:4946,
  6:202}；barrier {0:39407, 1:67}；深度≥2 机制×族：IQP 448 /
  QuantumWalk 182 / UCCSD 87 / Grover 86 / RandomClifford 65
  （IQP 与 RandomClifford 深度-1 逃逸为零）。
- 128 单元簇 bootstrap（10k 重采样，seed 20261025）：整体平均增益
  1.156，95% CI [0.88, 1.46]。
- ">80 门 ⇒ 深度-1"信号：与 80 门预算边界处阈值一致但与 root_kind
  定义混杂（支撑隙 67–81 门、1 个反例 148 门 QFT 零逃逸）；逃逸率
  沿清单近平坦（三分位 0.380/0.357/0.340）——**相变在根，不在位置**。

---

## 7. 创新路线图（D1–D12 × 开放扩展 → 执行计划）

方向登记见 ledger §12.4；按 新颖性 × 可行性 × 论文价值 排序：

- **P0（本轮已完成）**：引擎缺陷修复 + 修正版重认证 + 引擎增强 +
  E64 推导包 + 台账 §12。
- **P1 v16 重钉**：修正引擎下重跑 compact/IDA*（方法与预算已在
  `2026-10-25_engine_successor_fix/`，20.6 分钟量级）+ E46 全量重跑
  （76,236 窗口 ≈ 26 h·8 进程，过夜）+ 派生单元 `b2f83603` 单独
  处理（预算提高或专用无逃逸证明）。收益：头条恢复 "exact" 用语。
- **P2 bounded 精确化战役**（E64 追踪器驱动）：26 个便宜单元
  （预算 1–2M + 同构组共享证明）→ 头条从 "93 exact" 走向
  "105+/128 exact"。
- **P3 全规则库面板**：`rule_scope="full"`（1,474 条）— 引擎已就绪，
  逐门下界在此域发挥真实剪枝力；先 32 单元试点。
- **P4 WCL 窗口剖面**：`state_wcl` 已就绪，接入 E46 runner 的
  `root_kind` 管道 → 开放扩展 (2) 落地；跨表示证书迁移（D2）
  随之可测。
- **P5 fragment-native 基准 + 外部电路集**（WL-3 解法，
  round-12 P0-1 同项）：6 族 × ≥8 实例 × n=4..64 解析 s +
  MQT Bench/RevLib 子集；顺带修 SA/RLS/GA incumbent bug
  （DATA_CANONICAL Known Issue 15）解锁算法无关性语言。
- **P6 理论攻坚**（数日级先行）：BV 下界引理、⊥ 可靠性矩阵证明、
  Prop 2 iff、窗口聚类推断；数周级：content-class 复杂度分离（D1）、
  证书协议基础设施（D4，TACAS-2026 WMC 为独立语义验证器）。
- **投稿管线**（round-12 §5 并获外部评审背书）：短文 C（Qiskit L3
  非单调 → 2.6.1 修复 + 证书作回归测试，~4 页，数日）→ 工具轨 B
  （证书方法学 + QCEC 三方验证）→ 理论主文 A（定理 1–4 + 旋转
  间隙 + 湮灭墙，待 P1–P6 就绪）。

---

## 8. 本轮产物清单

修改：`src/optimisation/certified_landscape.py`（bug 修复 + 三项增强）、
`src/provenance.py`（engine_source_hashes）、
`scripts/derive_v15_certified_lower_bounds.py`（走统一过滤器）、
`tests/test_v13_certified_landscape.py`（6 个新测试）、
`docs/references/search_ledger.md`（§12）。

新增：`scripts/e64_escape_geometry_atlas.py`、
`docs/review/science_boost/2026-10-25_engine_successor_fix/`
（17 个工件，receipt 钉引擎+输入哈希）、
`docs/review/science_boost/2026-10-25_escape_geometry/`
（15 个工件，输入/输出/脚本全 SHA-256，双跑字节一致）、本文件。

明确未做（按用户指示或范围外）：`docs/manuscript/` 全部编辑（§3/§5
的修正项已登记待用）；`data/`、`release/` 零改动（git 确认）；
E46 全量重跑与 v16 重钉（P1，建议过夜窗口）；
`test_direct_dependencies` 的 e53/e55/e58 依赖声明（先前已存在）。
