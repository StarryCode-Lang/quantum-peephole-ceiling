# 第 24 轮：科研全流程体检 + 创新方向扫描（2026-11-06）

**性质**：review-grade。不在 `release/` 哈希链内。`data/`、`release/`、`docs/manuscript/`
零内容改动。本轮**执行**两项注册实验（E94 λ 稳定性、E95 源级两轴划分）与一次
冷启动替代验证（cold-start-lite），修复一个静默失败门控 bug，并把文献/生态扫描
（E96）升级为含全文精读的版本。

---

## 0 执行摘要

1. **两轴划分现在有两个独立的测量层，且逐源精确重合。** E95 对 69 个认证逃逸
   （35 枚举 + 34 witness-bounded）逐源分类第一步 `cost_delta`：
   **content-first 49/69（71.0%）、reorder-first 20/69（29.0%）**，且
   **RAW 层 49 个全部 content-first、greedy 层 20 个全部 reorder-first**——
   E90 的窗口级预测（19,303/699 与分层重合）在源级**精确成立**。
   与 E52 的 63 个共享源**零分歧**。round-23 清单 #1 关闭。
2. **λ 是按 L 稳定的量；线性读法被 L=6/7 证伪。** E94 把刚性衰减曲线延拓到
   m=20 并按窗口长度 L 分别拟合：panel_2q
   `λ(2..7) = 0.900 / 0.789 / 0.689 / 0.582 / 0.456 / 0.313`，
   panel_1q `λ(2,3) = 0.750 / 0.476`；每个 L 的尾部比值全部远在预注册判据
   ±0.02 之内（最大 spread 5.7e-3）。逐级差 −0.111 / −0.100 / −0.107 /
   −0.126 / −0.143：**线性只成立于 L=2..5，L≥5 后加速下降（凸递减）**。
   round-23 清单 #4 关闭，且带一个诚实的负结果。
3. **冷启动门在本地拿到了第一份可执行证据。** Docker 在本机**不存在**
   （round-23 P1-3 的"本地 Docker 可用"前提错误，与 2026-10-26 的核查一致）；
   替代方案 cold-start-lite：**零第三方依赖的全新 CPython 3.12 解释器**直接跑
   manifest 级字节审计——`release_manifest.json` **37/37 MATCH**、
   prepaper 链（35,042 条，含 19 条已登记漂移）**exit 0**。审计链是纯 stdlib
   的，这一点本身就是新证据。round-23 清单 #7 本地部分关闭；真正的第三方冷启动
   仍需第二台机器（owner）。
4. **顺带抓到并修复一个静默失败 bug**：`reproduce_all.py --audit-frozen`
   单独传入时只打印 help 并 exit 0（`any()` 门控漏了该旗标）——这正是 M1–M9
   映射警告的失效模式；已修复并验证（双链 PASS + verify PASS）。不影响任何
   已发布数字（历轮审计都是直接调用 `audit_frozen_bytes.py`）。
5. **`requirements-lock.txt` 不可 pip 安装（第一份直接执行证据）。** 干净 venv
   上 `pip install -r requirements-lock.txt` 报 `ResolutionImpossible`
   （pennylane 0.45.1 要求 numpy≥2.0 等冲突）。这是 owner 队列
   "requirements-lock 一致性 / 完整 pip-compile"项的实证材料。
6. **2608.27592 全文精读完成，划界成立且更牢固。** 它做的是**等代价平台内的
   选择**（best-of-24 + 跨路由种子排序迁移），全文无可达性判据、无局部刚性
   计数、无完备性价格。两个可借鉴点：(a) 其统计标准（配对 bootstrap CI 10k +
   精确 Wilcoxon + Holm 族 + 64 项全局敏感性）应作为本项目 P0-1 表格的
   对标线；(b) 其"基线口径改变报告幅度"（12.83% / 14.77% / 22.39% 三种）是
   P1-1 基准口径审计论点的**最好外部佐证**。
7. **QSymb 代码库确认存在**（`VeriGu/QSymb`，OOPSLA 2026，2026-08-16 更新；
   工具链 JDK 17 + Maven + `egglog-experimental` 1.0.0）。round-23 清单 #6 的
   Go 判定成立，1 天时间盒的执行步骤已具体化（§4 P1-2）。
8. **判定不变**：`NOT_READY_FOR_PAPER`。投稿层级不变：**PRX Quantum**
   （两轴划分 + 序轴判定边界 + 内容轴计数律 + 门集依赖阈值）、**Quantum**
   （证书方法学）。E95 的源级表补上了 P0-1 缺的最后一块测量。
9. **D11 修复落地（E70-v2）**：两个生成器消费种子，bench v2 去重
   170 → **230/240**（残余为 n=4 结构上限）；E70 重跑：四族份额**逐位复现**
   round-16（0.991/0.982/0.883/0.715，验证重跑链路），trotter_zz
   0.000 → **0.118**（旧 0 是层序固定的结构性伪象），合并份额
   **0.736**（0.710 坏测量 / 0.880 重加权 / **0.736 实测**）；gap 总量
   4,313 与绝对最优数 129 逐位不变。round-23 清单 #11 关闭；#12（λ 延拓）
   随 E94 复跑关闭。
9b. **第二面板复制（E97）**：30/30 个 MQT Bench 电路（16 个新算法）等价
   认证后普查——可约动作最小源长度 **{2: 17}，100% = 2**、规则级长度 2
   饱和、8 个 greedy 不动点全部零可约（分层重合复制）、23 电路划分
   14/9；ghz5/ghz10 整条无动作 = `LF-1` 真实实例。一处真实差异
   （3 个电路 witness 策略依赖）确立写作规范：**源轴标签必须连同
   witness 策略声明**。round-23 清单 #3 关闭。
10. **deep-sweep 代理双返回**：L2（认证 gh 通道）生态基线整体刷新
    （Qiskit 2.6.2 / Quartz 规则面分叉 / PyZX PhaseGadget 表示 bug /
    Quasar+QSymb 新基线），多条信号直接佐证表示依赖；L1 完整前沿扫描
    （16 条 + 13/13 必引摘要）——新增标题级划界义务 `2609.29210`、
    逐实例类比 `2608.22801`、唯一真缺口 `2101.01332`；引文枢纽
    **[109]–[111] 已补**，审计保持 20 accepted / 35,022 MATCH / ok。
11. `pytest` 全量套件本轮复核 exit 0（§7）。

---

## 1 事实基线（相对第 23 轮的增量）

第 23 轮 §1 的事实基线本轮**逐条复核，无变化**：

- `release/v16_readiness_verdict.json`：`NOT_READY_FOR_PAPER`；93 exact +
  34 witness-bounded + 1 resource-bounded；三门 OPEN
  （`external_cold_start` / `real_qpu` / `release_authority`）+
  `C3_title_and_positioning: USER_DECISION_PENDING`。
- 本轮新确认的**前提修正**：`real_qpu` 与 `external_cold_start` 两门的"本地可做"
  部分已有结论——QPU 属 owner 决策（第 22 轮已论证 out-of-scope），冷启动的
  本地替代已执行（§2.3）；两门剩下的都是**第二台机器/账号**问题，不再是
  "可以本地做而没做"。
- 理论注册表（`THEOREM_REGISTRY.md`）未动：`PD-1/2/3`、`LF-1`、`PR-1`、
  `AX-1`、`RF-1`、`EX-1`、`DF-5/6`、`T-9`。本轮新增的是 `RF-1` 的
  **参数稳定性**（E94）与 `AX-1` 的**源级测量**（E95），都是测量不是新定理。
- `docs/theory/framework.md`（v5.4.2，2026-08-11）仍是"结构天花板"时代的
  枢纽文档：其不可证清单纪律良好，但天花板中心叙事已被两轴划分取代。
  它不在哈希链内，**建议**（owner 决策）在正文 patch（清单 #8）执行时同步
  加一节 "certified era" 指针，指向 `THEOREM_REGISTRY.md` 与本轮主线。

---

## 2 本轮新证据

### 2.1 E95：源级两轴划分（`scripts/e95_source_axis_partition.py`，19 项自检全绿）

**问题**：E90 的划分是**窗口级**的（38,118 个窗口切片）。P0-1 的叙事需要
**源级**版本：对每个"整条 listing 被认证可以逃逸"的源，它的逃逸路径第一步
是否降代价。窗口是切片，源级才是"逃逸"的本义单位。

**方法**：复用 E52 的全套机制（`load_root_states` 哈希校验重建、
`decompose_escape`、`rule_family_of`），对 69 个认证逃逸源（35 枚举 compact +
34 witness-bounded）读冻结 witness 的**第一个动作**，计算其 `cost_delta`；
另用 `iter_legal_actions` 在根状态上独立枚举做交叉验证（E90 的定义）。
1 个 resource-bounded 源（`e39:b2f83603…`）单独记录，不分类。

| 量 | 值 |
|---|---|
| 分类逃逸源 | **69**（未解决 0） |
| content-first（首步 `cost_delta < 0`） | **49（71.0%）** |
| reorder-first（首步 `cost_delta = 0`） | **20（29.0%）** |
| RAW 层逃逸 | 49 / 49 **全部 content-first** |
| GREEDY_FIXED_POINT 层逃逸 | 20 / 20 **全部 reorder-first** |
| 根动作枚举交叉验证 | 49 个 content-first 根全部存在 reducing 动作；20 个 reorder-first 根全部不存在 |
| 首个 reducing 步长 | **全部 69 条为 2**（E90 断言在源级成立） |
| compact 与 IDA\* witness 首步方向 | 69/69 一致（9 个源首规则不同但方向相同） |
| E52 对齐 | 63 个共享源 `neutral_prefix` 轴**零分歧**；v16 新增 6 源已列出 |

**三条读数**：

1. **分层重合在源级是精确的，不是趋势。** 窗口级（E90）与源级（E95）两个
   分母完全不同的测量给出同一个定性结构：内容轴是未优化基线的产物，
   序轴是 greedy 不动点的全部机制。`AX-1` 现在是"定义级划分 + 双层测量"。
2. **reorder-first 的首步可以是长 3/长 4 的零代价规则**（11 例长 3、1 例长 4）。
   E90 的"全部 reducing 动作源长 2"只约束 reducing 动作；零代价动作不受此限。
   这条已如实写进 summary——它也再次说明为什么报告价格必须带 cost-delta 剖面
   （第 23 轮第三条报告规则）。
3. **E52 → E95 的六个月演进是测量粒度的细化，不是结论翻转。** E52（2026-10-22）
   在 14 个 greedy 层逃逸上发现"零代价前缀必要"；E95 确认这 14 个今天仍是
   reorder-first，且全集 69 个上轴与分层重合。

### 2.2 E94：刚性衰减 λ 的稳定性（`scripts/e94_rigidity_lambda.py`，8 项自检全绿）

**问题**（round-23 清单 #4）：E91 的 `λ ≈ 0.58` 只有 7 个点（m=8..14）且只有
L=5 一条曲线。要写成"律"需要 (a) m→20，(b) 每个 L 自己的 λ。

**方法**：原样复用 E91 的两个精确 DP（`geodesic_counts` / `valid_counts`），
无搜索无采样。预注册判据：**λ 稳定 = 尾部比值 ρ(m+1)/ρ(m) 在 m=12..19 上
对均值的最大偏差 ≤ 0.02**。

| 片段 | L | λ（尾均值） | 最大偏差 |
|---|---|---|---|
| panel_2q（阶 11,520，D=9，A=10） | 2 | **0.900** | ~1e-16 |
| | 3 | **0.789** | 3.4e-8 |
| | 4 | **0.689** | 2.5e-5 |
| | 5 | **0.582** | 4.4e-4 |
| panel_1q（阶 24，D=4，A=4） | 2 | **0.750** | 0（精确） |
| | 3 | **0.476** | 4.6e-3 |

**三条读数**：

1. **判据满足，且是压倒性满足。** 所有 spread 比判据小 2 个数量级以上；
   曲线稳定延拓到 m=20（此前只到 m=14）。
2. **λ(L) 的经验形状（首轮读法，后被 §2.5 的 L=6/7 修正）**：panel_2q 上
   L=2..5 的逐级差 −0.111 / −0.100 / −0.107（均值 ≈ −0.106/级）。这是测量
   不是定理；L=6、7 的延拓在同一轮内完成（§2.5），证明线性只在 L=2..5
   成立，L≥5 后凸加速。
3. **跨实验对齐（准入门首日执行）**：E94 逐位复现冻结 E91 包的 ρ(m,5)
   （m=4..14 全部重叠格）与 E87 的两个分母（80,986 / 988,046）。
   `docs/reproducibility.md` 的准入门（本轮新增，见 §6）在成文当天即被
   一个新实验遵守。

### 2.3 Cold-start-lite：零依赖冷解释器的全链字节审计（`2026-11-06_cold_start_lite/`）

| 步骤 | 结果 |
|---|---|
| Docker 存在性 | **不存在**（`where docker` 为空）——round-23 P1-3 前提修正 |
| 全新 venv（无任何 pip 包）+ Python 3.12.12 | `audit_frozen_bytes.py --manifest release/release_manifest.json` → **37/37 MATCH，ok=true** |
| 同解释器 + drift register | prepaper 链（35,042 条）→ **exit 0**（`PASS_WITH_ACCEPTED_DRIFT`，19 条已登记） |
| `pip install -r requirements-lock.txt` | **`ResolutionImpossible`**（pennylane 0.45.1 `numpy>=2.0` 等冲突）——owner 队列项的实证 |
| `reproduce_all.py --audit-frozen` 单传 | **bug**：打印 help 后 exit 0，审计未执行（`any()` 门控漏 `args.audit_frozen`） |
| 修复后 `--audit-frozen --verify` | 双链 **PASS/PASS** + verify PASS，`ALL TASKS PASSED` |

**读数**：审计链是**纯 stdlib** 的——"冻结证据未被改动"这一命题可以在一个
没有任何第三方包的解释器上独立复核。这是外部验证路径（§3.6）从 1.5 → 2 分的
唯一原因：它仍是本机自检，不是第三方复现，但它把"可复现"从依赖环境声明
降到了"任何 Python 3.12 都能验"。

### 2.4 E70-v2：D11 修复版 fragment bench 的重生成与重跑（`2026-11-06_fragment_bench_v2/` + `..._v2_e70/`）

**修复**（按 E93 登记的方案，`generate_fragment_bench.py` 未钉扎）：
`gen_trotter_zz` 消费种子（每层边序 shuffle）；`gen_arithmetic_phase` 消费
种子（随机进位长度 k ∈ [max(2, n/2), n] + 随机链窗口起点）。冻结的
2026-10-25 包不动；新 bench 写入新日期目录。

| 量 | 旧 bench（D11） | v2 |
|---|---|---|
| 行数 / 去重后电路 | 240 / **170** | 240 / **230**（残余 10 个重复是 n=4 处结构上限：arithmetic_phase 只有 6 种 (k, start) 结构 < 8 实例） |
| 合并 `g_reorder/g_total` | 0.710（重复放大）→ 0.880（去重重加权） | **0.736（修复后真测量）** |
| 绝对最优实例 | 129 | **129（逐位不变）** |
| gap 总量 | 4,313 | **4,313（逐位不变）** |

**族级份额（v2 vs round-16 去重口径）**：random_phase 0.991（=0.991）、
diagonal_structured 0.982（=0.982）、iqp_core 0.883（=0.883）、
linear_rotation 0.715（=0.715）——四个未动过的生成器在种子不变下**逐位
复现**，这同时验证了重跑链路本身。**trotter_zz 0.000 → 0.118**：旧 bench
的 0 是"两层边序完全相同 ⇒ 结构上不存在重排机会"的伪象；修复后露出
真实的 0.118（仍然内容主导）。arithmetic_phase 保持零 gap（闭包直达绝对
最优）。**三个数字的正确读法**：0.710 是坏 bench 的聚合、0.880 是坏 bench
的去重重加权（不是测量）、**0.736 才是修复后 bench 的实测聚合**；
"reorder 主导"结论在非退化实例上成立。

### 2.5 E94 延拓：λ 的 L=6/7 点与线性读法被证伪

E94 复跑（L 延拓到 6/7，8/8 自检再次全绿）：λ(6) = **0.456**（spread
2.8e-3）、λ(7) = **0.313**（spread 5.7e-3）。**每级稳定性结论不变**
（全部 ≪ 0.02），但**线性读法只在 L=2..5 成立**：逐级差
−0.111 / −0.100 / −0.107 / **−0.126 / −0.143**，λ(L) 在 L≥5 后加速下降
（凸递减）。这是本轮第二个诚实的负结果：λ 随 L 严格递减、凸，但
"−0.106/级"不是律。曲线族（6 个 L × m≤20）已入 E94 包。

### 2.6 E96：文献与生态扫描（真实执行，`2026-11-06_literature_scan/`）

**执行方式**：arXiv API 最新优先扫描（peephole / equality saturation /
circuit rewriting / rewrite rules，quant-ph，25 条，2026-11-02 → 2024-09）；
5 个新 ID 的摘要精读；`2608.27592` 的 abs + HTML v2 全文精读；docs/ 全库
覆盖核查；unified_references.md 枢纽核查；`VeriGu/QSymb` 浅克隆查验
（只读，未执行）。GitHub REST 在扫描时被限流（未认证配额耗尽），生态
快照以 E92（2026-11-04，已认证）为准——两天内无相关变化证据。

**scoop 判定**：**2026-11-06 无撞车。** 25 条扫描结果中没有任何一条触碰
四个重叠轴（表示依赖 / 逃逸可达性 / 局部刚性计数 / 完备性价格）。
7 个未预先钉扎的新 ID 里 6 个已被 docs/ 覆盖（12–16 个文件），唯一零覆盖是
`2611.02345`（MBUndo，测量式反计算）——"none of the four"，列为方法论
线的可选引文。

**2608.27592 精读（全文）**：设定是固定 placement + maintained-parity
lowering 下的可交换相位项两阶段编译；Stage 1 达到 support 最优（OR-Tools，
`2n+2` 经 support 线图的 Hamiltonian 路径直接证明最优），Stage 2 在
**K=24 个等代价顺序**里选最小路由深度。证据标准：配对 bootstrap CI
（10,000 重采样）+ 精确 Wilcoxon + Holm 族 + 64 项全局敏感性；跨 SABRE
种子 Spearman 0.910。关键数字：support 代价 74 的三个顺序路由深度
228.6 / 233.8 / 256.7；同一实验**三种 Stage-1 基线口径给出 12.83% /
14.77% / 22.39%** 三种幅度；BasicSwap 下增益反转（rank corr 0.093）；
Heron 误差改善的 CI 含 0。它自己的限制清单明确承认：不保证全局最小深度、
20 项以内才精确计数、只采样 24 个顺序、饱和未确立、协议宁可停止也不
静默放宽最优。

**两条可借鉴（已写进 §4）**：(a) 其统计标准成为 P0-1 跨源对比表的
报告标准；(b) 其三基线幅度差是 P1-1 基准口径审计论点的**直接外部证据**。

**划界句（进论文）**：他们优化 plateau 内部的**选择**，我们判定 plateau
是否是**唯一通路**。

**引文覆盖缺口（已修复）**：17 个已跟踪必引 ID 在 docs/ 全覆盖
（2–20 个文件），但 `unified_references.md`（写作时引用枢纽，v2.2，
2026-08-24 后未更）只收了 16 个 certified-era 关键 ID 中的 **1 个**。
本轮以**纯增量 Section Q**（[95]–[108]，每条注明显现轮次与核实状态）
修复，并按 house 规程登记 prepaper 链第 20 条漂移
（`release_drift_register.json`，POST_MANIFEST_EDIT）；审计复跑
**20 accepted / 35,022 MATCH / ok**。

**生态（2026-11-06 认证通道刷新，覆盖 E92 快照）**：Qiskit **2.6.2**
（11-05）；2.6.0 集中修 peephole 正确性 bug（`CommutativeCancellation`
全局相位 #16402、负角 `sx` 再合成 #16599、`Optimize1qGatesDecomposition`
死锁 #16592、小角近似 #17321），open #17057 two-CX 边界错误——
**同一条规则在相位/符号/容差三种表示维度上都出过正确性问题**，是表示
依赖的直接上游证据。pytket 已迁 `Quantinuum/tket`：#2232（2026-09 修复）
自消门对被 `FullPeepholeOptimise` 漏掉——规则不完备的活案例；open #1150
符号电路下 peephole 反增 2q 门数。Quartz 迁至 `quantum-compiler/quartz`，
2026-04 重激活时**新增 Nam (5,3)-complete ECC 集——上游规则面已与本项目
冻结的 1,474 条分叉**（引用须用 commit hash）；open #230/#232 输出非等价
电路（规则源头自己承认验证缺口）。QUanto 404 无后继；VOQC→SQIR 休眠；
BQSKit 实质停更（2026-08-11 后仅维护提交）。PyZX 0.10.7/0.10.8 修
PhaseGadget **同一电路两种内部表示结果不同**的 bug（本机 pin 0.10.5 落后
3 版，升级决策维持 round-23 结论）。MQT core 3.11→4.1 大版本跳
（MLIR/LLVM 重构），引用其电路表示需注明断层。**新基线**：`VeriGu/Quasar`
（PLDI 2026，e-graph/egglog 路线，step-limited 最优保证）与
`VeriGu/QSymb`（OOPSLA 2026，P1-2 输入）。

### 2.7 E97：MQT Bench 第二面板普查（`2026-11-06_mqt_second_panel/`，round-23 清单 #3 关闭）

**方法**：`scripts/e97_mqt_second_panel.py`（importlib 复用 e71 归一化 +
e90 普查 + e95/e52 划分机制，无逻辑复制）。**30/30** 个 MQT Bench 电路
（≤10 比特，E71 的 14 个 + 16 个新算法）加载并逐个通过精确等价认证；
根状态整条 listing 上跑声明 scope `e44_core_v1` 普查。10/10 自检，36.2 s。

| 量 | E90/E95（原面板） | E97（第二面板） |
|---|---|---|
| 可约动作最小源长度 | 19,303 窗全 2；69 源首步全 2 | **{2: 17}，100% = 2**（17/30 根有可约动作） |
| 规则级长度 2 饱和 | 2 条可约触发、全长 2 | 53/149 触发、**5 条可约全为长 2**（3×pair_v1 + 2×quartz 变体） |
| greedy 不动点 | 1,228 窗 / 20 源全零可约 | **8 个 greedy 不动点全部零可约动作**（分层重合复制） |
| 两轴划分 | 49/69 content-first | 23 个有认证闭包约减的电路：**14 content-first / 9 reorder-first** |
| 完全无动作 | 49 窗（0.13%） | **ghz5 / ghz10 整条 listing 无任何动作**——`LF-1` 的真实电路实例 |
| E71 对齐 | — | 14 个共享电路门数与闭包输出**逐字段精确相等** |

**一处真实差异（如实记录）**：qpeexact8、qpeinexact4、randomcircuit8 三个
电路根上有可约动作，但其闭包 witness 首步是零代价 exchange（20/23 轴
一致）。原因是闭包使用"最近对优先"的确定性策略，而 E95 的 witness 由
搜索自由选首步——**同一个根的不同逃逸路径可以落在不同的轴上**；
逐路径划分（`AX-1` 的本义）是良定义的，逐源单一标签不是。这把 E90 的
窗口级定义（"根上有无可约动作"——策略无关）确认为正确的报告口径，
并给 P0-1 增加一条写作规范：**源的轴标签必须连同其 witness 策略声明**。

**判定**：round-23 清单 #3 关闭——内容轴在自家基准饱和于长度 2、
greedy 层序优先，两个头条都在独立流水线的 30 个电路上复制。

**方法学精读池**：本轮全文精读 1 篇（2608.27592，最高优先级竞争者）+
deep-sweep 代理的 13/13 必引摘要（Section B）+ 16 条前沿表（Section A）。
**L1 补充的新发现**：(a) **`2609.29210`（Representation-Dependent
Recoverability in Quantum Compilation，2026-09-24）是唯一的标题级重叠**
——它形式化"FT 编译输出的表示如何改变下游相位恢复代价"，带定理与
**预注册协议**；但无 listing model、无窗口 landscape、无完备性价格。
划界句升级为：**他们研究编译输出的表示依赖，我们研究优化器输入表示的
可达性依赖**；其预注册协议标准采纳进 P0-1。(b) **`2608.22801`
（Exactness Barrier）**：逐实例 T-count 可达下界 + rigidity 证书
（99.4–99.9% 实例不可压缩）——本项目群体级计数律的**逐实例类比**，
方法学收割的最高价值单点（给认证窗口配发"规则库已达闭包"证书）。
(c) `2101.01332`（张量图 EqSat 先例）是唯一真覆盖缺口 → 引文枢纽
**[109]–[111] 已补**（漂移条目 20 的观察哈希同步更新，审计保持
20 accepted / 35,022 MATCH / ok）。(d) 零命中声明（EqSat×量子 2023–26
无新条目；"wire-consecutive"/"listing model" 编译语境零命中；
"认证+最优性+peephole"三者兼有的论文不存在）——scoop 判定维持
**无撞车**，附带 2609.29210 的显式划界义务。

---

## 3 全流程审查（撰写除外，7 个环节；相对第 23 轮的增量）

### 3.1 科学问题与叙事 —— 4/5（上升 0.5）

划分主线未变，但 P0-1 的证据结构补齐：**双层测量（窗口 E90 + 源 E95）+
双轴独立量（序轴可判定 `EX-1`，内容轴可计数 `RF-1`）**。叙事第一句的
"划分"版本（round-23 §3.1）现在有源级表格可引。

### 3.2 理论框架 —— 4/5（持平）

新增两条经验规律（λ 的 L-依赖、λ 数值稳定），都**不是定理**，按 house
纪律写成 measurement。`framework.md` 的时代错位记为文档升级项（§1）。

### 3.3 实验设计 —— 4.5/5（上升 0.5）

- 本轮两个实验都有**预注册判据**（E94 的 ±0.02、E95 的 E90 方向预测），
  且判据都可能失败而实际通过。
- 对标升级：2608.27592 的统计标准（bootstrap CI 10k + Wilcoxon + Holm +
  64 项敏感性）写入 P0-1 的证据要求（§4）。
- 仍弱：**只有一个面板**（96 源来自同一 pipeline）——清单 #3 不变。

### 3.4 数据与可复现性 —— 4.5/5（持平，证据变硬）

冷启动从"协议存在"变成"本机已执行 + 审计链零依赖可验"；lock 文件问题
从"登记在案"变成"可直接复现的 ResolutionImpossible"。

### 3.5 代码工程质量 —— 4/5（上升 0.5 后回落持平）

修复一个静默失败门控（`reproduce_all.py`，已验证）；scripts/README 索引
补齐（119→130，e75/76/77/94 入表）。已知债不变：mypy 24 条（未扩大）；
`load_rule_library()` 暴露仍与释放重钉捆绑（#9/#10）。

### 3.6 外部验证路径 —— 2/5（上升 0.5）

cold-start-lite 是**内部**外部效度：零依赖冷解释器可独立复核冻结链。
第二台机器冷启动、真实 QPU 仍为 owner 外部门。

### 3.7 成果形态策略 —— 不变

| 形态 | 内容 | 判断 |
|---|---|---|
| **PRX Quantum（主线）** | 两轴划分（`AX-1`，现双层测量）+ 序轴判定边界（`EX-1`/`DF-5`）+ 内容轴计数律（`RF-1`/`LF-1`/E91/E94）+ 门集依赖阈值（`PD-1/2/3`） | **可投**；缺 #2 bypass 校验与第二面板 |
| **Quantum（次线）** | 证书方法学 + M1–M9 + 本轮新增的"审计链零依赖"事实 | **可投**，更厚了 |
| **npj QI（保底）** | 库工程指南（E87 边际价值 + E90 利用普查） | 不变 |
| **主刊（唯一形状）** | P1-1 基准口径审计；2608.27592 的三口径句子是新论据 | 预注册待执行 |
| **不建议** | "表示决定可达空间"（≥5 篇 2026）、"plateau 有后果"（2608.27592） | 撞车 |

---

## 4 创新方向清单（按优先级；Δ = 相对第 23 轮的变化）

### P0-1 两轴划分：机制分类与分层重合（**主线**）—— Δ 证据近齐

- **现状**：定义级划分（`AX-1`）+ 窗口级测量（E90：19,303/699）+
  **源级测量（E95：49/20，与分层精确重合）** + E52 零分歧对齐。
- **与现有工作的本质差异**：2608.27592 在平台内**选择**；我们**判定平台是否
  是唯一通路**，且给出双层可复算的二分。全文精读确认对方无可达性判据。
  deep-sweep 补充的 **`2609.29210`** 是唯一标题级重叠（representation-
  dependent × quantum compilation × 定理 + 预注册协议），其对象是 **FT
  编译输出的相位恢复代价**——划界句：**他们研究编译输出的表示依赖，
  我们研究优化器输入表示的可达性依赖**；其预注册协议采纳为本项目的
  证据标准之一。
- **剩余缺口（按 30 天清单）**：#2 bypass 校验（23 greedy 源关掉 80 门 bypass，
  用 E54 均匀基线）；#3 第二面板（MQT Bench 30 电路同一张表）。
- **证据标准升级**：主表采用 2608.27592 级统计（配对 bootstrap CI、精确
  Wilcoxon、Holm 族）——虽然本项目多为普查/精确计数（无抽样误差），
  跨源对比表（家族残余、分层对比）应按此标准报告。
- **投稿层级**：PRX Quantum。

### P0-2 内容轴计数律（`RF-1`）—— Δ λ 稳定性完成

- E94 关闭 round-23 #4。新增可写点：λ 的 L-依赖（经验）；
  曲线到 m=20。剩余：L=6/7 延拓（便宜，DP 状态 10⁵/10⁶）；
  `D_3` 精确值仍 open（[11,12]）；3 比特极端点不可算（写 open）。
- **投稿层级**：并入 P0-1。

### P1-1 基准口径审计（唯一主刊形状）—— Δ 外部佐证加强

- 2608.27592 自己量出**同一实验三种基线口径给 12.83% / 14.77% / 22.39%**
  三个幅度——这正是"报告口径系统性影响社区认知"的活例子，写进 P1-1 的
  动机段可直接引用。
- 其余不变：协议已预注册 v1.0，首轮（Qiskit L0–L3 × MQT Bench 30）= 清单 #5。
- **投稿层级**：Nature Physics（Comment/Perspective）或 Nature Communications；
  退路 PRX Quantum Perspective。

### P1-2 QSymb 第二库 Go/No-Go —— Δ 判定升级为"GO，步骤已具体化"

- `VeriGu/QSymb`（OOPSLA 2026）存在；工具链 JDK 17 + Maven≥3.6 +
  `egglog-experimental` 1.0.0 + Python 3.10。1 天时间盒的执行序：
  ① `build_qsymb.sh` 构建；② 对面板门集 `{h,x,rz,cx}` 合成规则集
  （重点拿**长度 2** 规则——E90 已证明真实基准只用长度 2）；③ 规则集塞进
  E87 价格表，对照"覆盖问题 vs 长度问题"判据（56.07% → 接近 47.72%？）。
- 失败处置不变：E75 合成库当第二库（只给上界，正文写明）。
- **投稿层级**：P0-1 的一节。

### P1-3 证书外部执行门 —— Δ 本地部分完成

- cold-start-lite 已执行（§2.3）；审计链零依赖可验是 Quantum 投稿的
  方法学卖点。剩余：第二台机器（owner）。
- **投稿层级**：支撑材料 / Quantum 方法学。

### P2（不变项，摘要）

- P2-1 三比特可及边界（定理陈述，不测量）。
- P2-2 `rz` 片段离散化锚（优先级维持下调）。

---

## 5 下一步 30 天行动清单（round-24 版；✅ = 本轮关闭）

| # | 动作 | 状态 | 产出 / 判据 |
|---|---|---|---|
| 1 | 源级两轴划分 | ✅ E95 | 49/20，分层精确重合，19/19 自检 |
| 2 | **分层重合的 bypass 检验**（23 greedy 源，关 80 门 bypass，E54 基线） | 待做 | 结论不变或记录差异 |
| 3 | **E90/E95 扩到 MQT Bench 30 电路**（第二面板） | ✅ E97 | 30/30 认证；{2:17}=100%、greedy 层零可约、划分 14/9；witness 策略差异记录 |
| 4 | `RF-1` λ 稳定性 | ✅ E94 | 全部 λ 稳定（≪±0.02）；λ(L) 线性下降为新经验规律 |
| 5 | 基准口径审计首轮（Qiskit L0–L3 × MQT Bench 30） | 待做 | 120 行双口径表，0 失败 |
| 6 | QSymb 1 天时间盒执行 | 待做（GO 已确认，构建步骤 §4 P1-2） | 第二库价格表或明确失败 |
| 7 | 冷启动 | ✅ 本地部分（cold-start-lite） | 双链 PASS；第二台机器仍 owner |
| 8 | 正文 patch list 执行（P1-1/P1-2/P1-3 + framework.md 指针） | owner | 三条各有证据引用 |
| 9 | `src/` 暴露 `load_rule_library()` / `rule_source_length()` | 待做（与 #10 捆绑） | E90 不再 import 私有名 |
| 10 | 释放重钉决策（19 条已登记漂移 + **新增 lock 文件证据**） | owner | 重钉或声明 drift |
| 11 | （新）D11 修复版 fragment bench 重生成 + E70 重跑 | ✅ E70-v2 | 230/240 去重；四族份额逐位复现；trotter 0→0.118；合并 0.736 |
| 12 | （新）L=6/7 的 λ 延拓（检验 −0.106/级 线性） | ✅ E94 复跑 | λ(6)=0.456、λ(7)=0.313；线性被证伪（凸递减） |

> 依赖关系：#3 与 #5 共用 MQT Bench 面板，先 #3 后 #5；#11 与 #3 无依赖可并行；
> #9/#10 必须同一次 release 操作里完成（动绑定路径）。

---

## 6 遗留清偿与清理（本轮）

| # | 遗留 | 来源 | 处置 |
|---|---|---|---|
| 1 | 清单 #1 源级两轴划分 | round-23 | **E95 关闭**（§2.1） |
| 2 | 清单 #4 λ 稳定性 | round-23 | **E94 关闭**（§2.2） |
| 3 | 清单 #7 Docker 冷启动 | round-23 | **cold-start-lite 本地关闭**；Docker 前提修正；第二台机器 owner |
| 4 | 清单 #6 QSymb Go/No-Go 输入 | round-22/23 | 代码库确认 `VeriGu/QSymb`；GO 维持，执行步骤具体化 |
| 5 | `reproduce_all.py --audit-frozen` 静默失效 | 本轮冷启动发现 | **修复并验证**（M1–M9 家族；不影响已发布数字） |
| 6 | `scripts/README.md` 索引过时（119 vs 实际 130；e75/76/77 缺行） | 历轮累积 | 刷新计数、前缀表、补 4 行（含 e94） |
| 7 | `docs/review/README.md` 过时（"共 65 项""十八轮"） | round-17 后未更 | 更新为 67 项 + 指向编年表 |
| 8 | round-23 改进项"跨实验对齐写成准入门" | round-23 §3.4 | **已写入** `docs/reproducibility.md`（admission gate），E94 当天遵守 |
| 9 | `.pytest_cache` | 本轮 | 已删 |
| 10 | lock 文件一致性（owner 队列）缺实证 | round-19 起 | **cold-start-lite 提供第一份直接执行证据**（ResolutionImpossible） |
| 11 | round-23 清单 #11：D11 修复 bench 重生成 + E70 重跑 | round-23 D11 | **E70-v2 关闭**（§2.4）：修复方案按 E93 登记执行 + 链窗口起点扩展；四族逐位复现，trotter 伪象消除 |
| 12 | round-23 清单 #12：λ 的 L=6/7 延拓 | round-24 §4 P0-2 | **E94 复跑关闭**（§2.5）：稳定性结论不变，线性读法证伪 |
| 13 | L1/L2 deep-sweep 未返回 | 本轮启动 | **限时收尾后双双返回**：L2 生态认证刷新（并入 E96 §5），L1 完整前沿 + 2609.29210 划界义务 + [109]–[111] 入枢纽（并入 E96 §6） |
| 14 | round-23 清单 #3：第二面板 | round-23 | **E97 关闭**（§2.7）：30/30 MQT 电路，长度 2 饱和与分层重合双复制；witness 策略差异 → 新写作规范 |
| 15 | `AX-1` 的逐源标签 vs 逐路径定义 | E97 发现 | **写作规范确立**：同一根的不同逃逸路径可落不同轴；逐路径划分良定义，逐源标签必须连同 witness 策略 |

**新增缺陷**：0 个数据/口径缺陷。1 个工程 bug（已修复，#5）。
**未删除任何绑定文件**（本轮删除仅 `.pytest_cache`，gitignored 缓存）。

---

## 7 约束遵守

| 约束 | 验证方式 | 结果 |
|---|---|---|
| 不改 `data/` / `release/` | cold-start-lite 双链字节审计（零依赖冷解释器）+ git status | **37/37 MATCH**；prepaper 链 exit 0（**20 条已登记漂移**，含 [109]–[111] 追加后的条目 20 哈希更新） |
| 不改 `docs/manuscript/` | `git status --porcelain -- docs/manuscript` | 空 |
| 不删冻结文件 | 删除清单 = `.pytest_cache`（gitignored） | ✓ |
| 新证据文件带日期与来源 | E94/E95/cold-start-lite 三个包各带 `MANIFEST.json`（逐产物 sha256） | ✓ |
| 不破坏测试 | `pytest -q` 全量 | （运行结果见附录 B） |

---

## 附录 A：本轮产物

| 路径 | 内容 |
|---|---|
| `docs/review/science_boost/2026-11-06_innovation_scan.md` | 本文 |
| `docs/review/science_boost/2026-11-06_source_axis_partition/` | E95：`source_axis_partition.csv`、`summary.json`、`MANIFEST.json` |
| `docs/review/science_boost/2026-11-06_rigidity_lambda/` | E94：`rigidity_lambda.csv`、`summary.json`、`MANIFEST.json` |
| `docs/review/science_boost/2026-11-06_cold_start_lite/` | 冷启动替代：`summary.json`、两份日志、`MANIFEST.json` |
| `docs/review/science_boost/2026-11-06_literature_scan/` | E96：文献与生态扫描包（含 L1 deep-sweep §6 与 L2 生态 §5） |
| `docs/review/science_boost/2026-11-06_fragment_bench_v2/` | D11 修复版 fragment bench（240 行 / 230 去重） |
| `docs/review/science_boost/2026-11-06_fragment_bench_v2_e70/` | E70-v2 重跑（合并 0.736；四族逐位复现） |
| `docs/review/science_boost/2026-11-06_mqt_second_panel/` | E97：MQT 第二面板（30 电路普查 + 划分 + E71 对齐） |
| `scripts/e94_rigidity_lambda.py` | λ 稳定性实验（L=2..7 延拓后复跑） |
| `scripts/e95_source_axis_partition.py` | 源级两轴划分实验 |
| `scripts/e97_mqt_second_panel.py` | MQT 第二面板实验 |
| `scripts/generate_fragment_bench.py`（修改） | 两个生成器消费种子（D11 修复；文件未钉扎） |
| `docs/references/unified_references.md`（修改） | v2.4：Section Q [95]–[111]（纯增量；漂移条目 20） |
| （文档刷新）`scripts/README.md`、`docs/review/README.md`、`docs/reproducibility.md`、`science_boost/README.md` | 索引与准入门 |

## 附录 B：自检状态

- **E94**：**8/8**（双片段群阶/直径、ρ(L,L)=0、E91 ρ(m,5) 逐位复现、
  E87 两分母复现）。
- **E95**：**19/19**（计数 69+1、δ-轴一致、双包 witness 哈希、长度 2、
  E90 贪心预测、E52 对齐、根普查一致等）。
- **cold-start-lite**：审计双链 PASS（37/37 + exit 0）；门控修复验证
  `ALL TASKS PASSED`。
- **pytest**：全量套件 **exit 0**（2026-11-06 本轮复核；计数行被 `-qq`
  静默抑制，收集规模 632 沿用 round-23 记录）。
- **prepaper 链审计（含第 20 条漂移）**：**20 KNOWN_DRIFT_ACCEPTED /
  35,022 MATCH / ok**（unified_references.md Section Q 登记）。
- **E96**：采集型，无自检；scoop 判定基于 §1–§3 的主源检查。
