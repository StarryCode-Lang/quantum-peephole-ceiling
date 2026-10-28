# science_boost — 科研体检与创新方向扫描索引

十八轮扫描（2026-10-16 → 2026-10-28）的记录索引。

**2026-10-24 清理**：第 1–9 轮的**叙述性主文件**（`*_innovation_scan.md`、
`2026-10-22_backlog_closure.md`）与 3 个原始 arXiv 转储目录已删除——它们的结论在后续轮次被
反复推翻，对当前判断不再有引用价值。**证据包全部保留**（下表末列），因为脚本与当前文档
按路径读取它们。

**2026-10-25 清理**：`2026-10-23_innovation_scan.md` 一并删除——它的头条结论
（闭包 −10.44% 具有容错价值）已被第 11 轮 E58 否证（98.2% 是单比特合并）；
仍然有效的定理 1 与 E56 分别落在 `docs/theory/exposability_criterion_2026-10-23.md`
与 `2026-10-23_closure_criterion/` 证据包中。删除内容可从 git 恢复：

```bash
git show d7fb16236:docs/review/science_boost/2026-10-23_innovation_scan.md
git show a8d68e370:docs/review/science_boost/2026-10-22_innovation_scan.md
```

## 轮次编年（一句话结论 + 证据去向）

| 轮次 | 关键结论 | 后续命运 | 保留的证据包 |
|---|---|---|---|
| 10-16 | 首轮基线；发现 `2609.29406`（pass order）为最大新颖性威胁 | 被修订；该文献仍是必引 | — |
| 10-17 | 认证下界（128 源 `best_cost ≥ baseline − 6`）；128 根状态位精确重建；`qrcert/v1` 验证器 | 方法有效，**结论已被闭包取代** | `2026-10-17_certified_lower_bounds/`、`2026-10-17_certificate_verification/`、`2026-10-17_thm5_tail_test/` |
| 10-18 | 规则库普查（1,474 规则，反向闭合 99.55%）；三条引理 L1–L3 | 有效 | `2026-10-18_rule_library_census/` |
| 10-19 | **E47 视野探针**：19/33 个 h=3 局部最优在 h≤7 被推翻 | 有效；被定理 1 精确解释 | `2026-10-19_horizon4_probe/` |
| 10-20 | **D1 基线通胀 8.3×**；**E48 外部证伪**：SurfaceCode 1/8、QFT 2/2 天花板被打破 | 有效 | `2026-10-20_external_falsifier/` |
| 10-21 | **E50 BV 视野标定**：h\*=2,4,4,6,6,6,7；**E49 双口径** | 有效；`e56` 按路径读取其 `summary.json` | `2026-10-21_horizon_scaling/`、`2026-10-21_source_relative/` |
| 10-22 | **D2 重基线**（逃逸 22/95）；**E52 机制普查**；**E53 BQSKit 证伪**；**E55** 把 Thm 10 修正为"有界视野 vs 闭包" | 有效 | `2026-10-22_d2_rebaseline/`、`2026-10-22_escape_mechanism/`、`2026-10-22_bqskit_tzap/`、`2026-10-22_commutation_gap/` |
| 10-23 | 定理 1 + E56 闭包：128/128 证书重放，70,293→62,952 | 主线；**收益口径被第 11 轮否证**，叙述文件已删 | `2026-10-23_closure_criterion/`、`2026-10-23_literature_scan/` |
| 10-24 | **两比特口径否掉 10-23 主线**（98.2% 单比特）；**E61 找到 Qiskit L3 非单调**；**E59 QCEC 128/128**；**E60 经验合流** | 有效 | `2026-10-24_cross_engine_closure/`、`2026-10-24_qcec_oracle/`、`2026-10-24_opt_level_monotonicity/`、`2026-10-24_closure_order/`、`2026-10-24_literature_scan/` |
| **10-25** | **E62 绝对参照点 + 三分解 + 湮灭墙**；**E63 证明 L3 缺陷在 Qiskit 2.6.1 已修复** | **当前** | `2026-10-25_rotation_gap/`、`2026-10-25_qiskit_261/`、`2026-10-25_literature_scan/` |
| **10-25（第 13 轮）** | **引擎 successor-generation 缺陷**（"last location wins"）修复 + v16 重钉（93 精确 / 34 bounded / 1 resource-bounded）；E64 逃逸几何；E65 精确化（5 单元 RAM 永久封死）；E66 关键对；⊥ 可靠性 ALL_PASS；WCL 窗口剖面**接近零效应** | 有效；v14/v15 冻结不再字节可再生 | `2026-10-25_engine_successor_fix/`、`2026-10-25_escape_geometry/`、`2026-10-25_bounded_exactification/`、`2026-10-25_kbc_critical_pairs/`、`2026-10-25_perp_reliability/`、`2026-10-25_wcl_window_profile/`、`2026-10-25_full_scope_pilot/`、`2026-10-25_bv_lower_bound/` |
| **10-26（第 15 轮）** | **E69 设计式推断**：有效 n 仅 122–144（deff 134–153），配对零反转，宽度 ≈ 6× 视野；**D3 分母口径错误**（96.8% 窗口在未优化根上，其逃逸 99.9% 是 depth-1） | **当前** | `2026-10-26_window_inference/`、`2026-10-26_literature_scan/` |
| **10-26（第 16 轮）** | **P5 外部效度 + 绝对间隙标度**：E70 fragment-bench 旋转间隙（240 实例，聚合 g_reorder/g_total=0.710，129 达绝对最优，**否定普适标度律**——家族结构主导：对照族 0.0、diagonal/random_phase 0.97–1.0、iqp 0.87–0.96、linear_rotation n=64 骤降 0.50）；E71 MQT Bench 外部集（14/14，平均削减 7.43%）；fragment bench 账目修复（形式演化=向量异或，转置错误已修）；E65 分级契约重启（授权的内存分块） | 有效 | `2026-10-26_fragment_rotation_gap/`、`2026-10-26_external_circuits/`、`2026-10-25_fragment_bench/`、`2026-10-25_bounded_exactification/` |
| **10-27（第 17 轮）** | **E72 跨度判据的可预测性**：76,236 窗口 **0 假阳性**、首次逃逸深度逐窗精确 99.995%，但覆盖率分层（raw 97.0% vs greedy 32.8%）；**E73 规则库完备性**：1,474 条规则中仅 14 条单比特、无 3 门单比特模式，2q Clifford 片段上 **30.25% 的可约 listing 达不到绝对最优**，`h·x·h·z` 合法动作数为 0；**主刊门改判**：完备性路线被 `2609.40106` 占住，改走「完备性价格」 | 主线延续；家族级残余表述被第 18 轮 E77 校正为家族特异 | `2026-10-27_span_law/`、`2026-10-27_library_completeness/`、`2026-10-27_literature_scan/` |
| **10-28（第 18 轮）** | **E75 完备性价格曲线（阈值而非斜坡）**：长度 2 规则贡献恰为 0.00（`pair_v1` 已饱和该类），2q Clifford 30.25% →（+全部 ≤3）9.12% →（+全部 ≤4）0.00%；1q Clifford 阈值 `L* = 4 ≪ m = 8`，阈值下两种 regime 无中间态（P(2) 随实例长度上升、P(3) 饱和、P(4) 恒 0）→ 定理 6；**E77 Holm 校正**：blanket「残余集中在结构化家族」**撤回**——greedy 不动点上 IQP/Oracle 显著更多、RandomClifford/UCCSD 显著更少（家族特异，非结构普适）；**E75 顺带修复 E73 的 unitary-key 缺陷**（argmax 枢轴并列时拆类；相位不变键 1q 片段 12→8 类；legacy 键下 30.25% 精确复现，回归门 PASS）；定理 5/6 判定边界成文（`docs/theory/decidability_frontier_2026-10-28.md`）；证书 M1–M9 失效模式映射（`docs/review/certificate_failure_mode_map_2026-10-28.md`） | **当前** | `2026-10-28_completeness_price/`、`2026-10-28_span_family_holm/`、`2026-10-28_literature_scan/` |

主文件只保留四份：`2026-10-24_innovation_scan.md`（口径复核）、
`2026-10-25_innovation_scan.md`（绝对参照点）、
`2026-10-26_innovation_scan.md`（D3 + E69 + 文献改道）、
`2026-10-27_innovation_scan.md`（判定边界 + 完备性价格首点）。
第 18 轮起的叙述性主文移出本目录：`docs/theory/decidability_frontier_2026-10-28.md`
（定理 5/6 定稿）与 `docs/review/certificate_failure_mode_map_2026-10-28.md`
（证书失效模式映射）。
round 13/14 的执行记录是 `2026-10-25_external_audit_round13.md`。

## 阅读顺序

1. 只读 `2026-10-27_innovation_scan.md` 与 `docs/theory/decidability_frontier_2026-10-28.md`。
   前者是判定边界与完备性价格的完整叙述，后者是定理 5/6 的定稿（含明确未证清单）。
2. 需要某条数字的原始 CSV 时，按上表末列回跳。
3. 需要 10-24 之前的推理链时，用 git 恢复被删的叙述文件（命令见上）。

## 当前主线（2026-10-26 起；10-28 增补）

**重写的代价住在跨度（span）里，不在视野（horizon）里；而"相对什么最优"的答案是规则集，不是片段。**

1. **判据**：可约对可被交换律带到相邻 ⟺ 中间每个门与两端都独立；所需视野 `h* = D+1`，
   D = 中间的间隔（定理 1）。→ h 是推论，D 才是自变量。
2. **终止与不动点证书**：定理 2/3/4（`closure_termination_and_optimality_2026-10-24.md`）。
3. **三份独立证据指向同一量**：E50（BV 上 h* 随 n 增长 = 跨度增长）、
   E52（逃逸 100% 由 `pair_v1` 触发，即最短跨度规则）、
   **E69（宽度效应 +11.8pp ≈ 6 × 视野效应 +2.0pp，且四组对比零反转）**。
4. **绝对参照点只在相位多项式片段内成立**；跨出片段被湮灭墙挡住（`rotation_gap_2026-10-25.md`）。
5. **完备性价格是阈值，不是斜坡**（E75 → 定理 6）：长度 2 规则贡献恰为 0.00；
   2q Clifford 30.25% → 9.12%（+全部 ≤3）→ 0.00%（+全部 ≤4）；1q Clifford `L* = 4 ≪ m = 8`。
   阈值以下两种 regime 无中间态：P(2) 随实例长度上升、P(3) 饱和、P(4) 恒 0。
6. **E72 的家族级残余经 Holm 校正后是家族特异的**（E77）：greedy 不动点上
   IQP/Oracle 显著更多、RandomClifford/UCCSD 显著更少；"结构普适"表述撤回。

**六条必须同时记住的否定性 / 限定性结果**：

- 闭包的 −10.44% 里 **98.2% 是单比特门合并**，两比特口径只有 −0.53%。
- **闭包不比生产编译器强**：Qiskit L3 输出在 95/101 源上已是闭包不动点。
- tket/BQSKit 的"闭包增益"是**规范化假象**（扩张 5.75×/6.40×），不得引用。
- **窗口结论的分母是错的**（D3）：76,236 窗口中 73,780 个来自从未被优化的 raw 根，
  其逃逸 99.9% 是 depth-1；真正的 greedy 不动点只有 2,456 窗口 / 44 源，
  且 **depth-1 逃逸恒为 0**。修正后 w16_h3 = 39.7%（23 源 / 481 窗口）。
- **WCL 与 greedy 的窗口剖面几乎相同**（平均 Δ = −0.004，仅 7 源变化），
  "表示敏感性"在窗口层基本消失。
- **家族级残余不随"结构化"普适集中**（E77，Holm 校正后）：greedy 不动点上
  IQP/Oracle 更多、RandomClifford/UCCSD 更少；引用残余表必须点名家族。

**投稿层级**：PRX Quantum（跨度定律，需先修 D3）；Quantum（证书方法学，证据已齐）；
主刊的活门本轮**改判**：不再走"造完备规则集"（`2609.40106` 已占），
改走 **「完备性价格」**——固定长度规则库必然不完备，且代价可精确测量
（E73 首点 + E75 曲线：阈值形式，1q Clifford 为 `L* = 4`）。

## 约束（十八轮一致）

- `data/` 与 `release/` 不修改；`docs/manuscript/` 只读。
- 本目录下的证据包是 **review-grade**，不在 `release/release_manifest.json` 的哈希链里。
  论文正文引用时须说明这一点，或另建版本化证据包后再引用。
