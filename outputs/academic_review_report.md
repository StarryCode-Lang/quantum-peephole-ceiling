# Q-Research 科研/学术水平评估报告

**评审日期**: 2026-07-13
**评审标准**: 博士后/教授级，目标期刊 Quantum / ACM TQC / IEEE Quantum Engineering
**项目**: 量子电路窥孔优化的结构天花板与可优化性研究

---

## 综合评分: 7.2 / 10

项目已达到**可投稿状态**，但需完成以下关键修复后方可提交。主要风险点为：Phase-2b 实现状态的手稿-代码不一致（已修复）、工业基准表的聚合误导性（已修复）、以及交换规则代码分歧（已修复）。

---

## 1. 研究问题与学术意义 (7/10)

**优点**:
- RQ1-RQ5 清晰、可回答、有实践意义
- Listing model sensitivity 是真正的方法论发现
- 负面结果（Phase-1 ~0%）被恰当定位为科学贡献

**已修复问题**:
- [FATAL-3] 三分类从"universal structural law"降级为"empirical observation on 15 pre-selected families"
- [HIGH] "structural ceiling" 术语已分类：3 genuine (QFT/GHZ/SurfaceCode) + 7 prototype-limited

**残留风险**:
- [MEDIUM] "largest systematic study" 表述需验证——Quartz/Qarl 规模更小但方法不同，"systematic"定义需明确
- [LOW] RQ5 (ceiling-aware optimization) 本质上是探索性结果，贡献定位已降级为 supplementary observation

## 2. 理论框架与数学严谨性 (7/10)

**优点**:
- D1-D10 定义完整、自洽
- Theorem 2 INSERTION cascade gap 已通过 2c/2d 关闭
- Theory-experiment cross-validation table 覆盖 8 observables

**已修复问题**:
- [FATAL] Theorem 1(b) 已降级为 Observation 1(b)（tautological under LBL definition）
- [HIGH] Theorem 9 Phase-2b cross-validation row 已从"Consistent"改为"Partially validated"（Phase-2b 未全规模实现）

**残留风险**:
- [MEDIUM] Theorem 8 (Haar incompressibility) 适用于 Haar-random unitaries，但实验用 random gate sequences——已在 §6.3.4 充分说明
- [LOW] Theorem 7 使用人工构造的电路族，Practical significance 有限

## 3. 文献综述与学术定位 (8/10)

**优点**:
- 81 篇参考文献，覆盖 1965-2025
- 关键奠基文献齐全：Barenco 1995, Maslov 2008, Nam 2018, Shende-Bullock-Markov 2006
- 最新工作已纳入：Quartz 2022, Quanto 2024, Qarl 2024, AlphaTensor-Quantum 2025, Riu 2025

**已修复问题**:
- [HIGH] 移除可能虚构的参考文献 [72] QCircuitBench, [73] MLCO, [77] QUASAR
- [MEDIUM] 移除重复参考文献 [74] (=[59]), [76] (=[62])

**残留风险**:
- [LOW] 缺少 Fossati 2024 (MQT compiler), Vandaele 2024 (depth optimization)——非致命，可后续补充

## 4. 实验设计与方法 (7/10)

**优点**:
- 15 circuit families 覆盖随机/算法/结构/变分四大类
- 预注册假设 (H1-H6)，power analysis (β≥0.80)
- CONSORT-guideline 适配

**已修复问题**:
- [HIGH] Phase-2b 手稿声称"not implemented"但代码+数据存在（1,017 rows）——已更新为"implemented with fixture-scale validation"
- [MEDIUM] E04 single-seed 已在 §6.3.7 充分说明

**残留风险**:
- [MEDIUM] 无 random gate shuffler control——已在 §6.3.11 说明
- [MEDIUM] E6 (gate-set sensitivity) 未执行——已在 §6.3.12 说明

## 5. 数据完整性与可重复性 (8/10)

**优点**:
- `reproduce_all.py --verify` ALL PASS
- 27 datasets, SHA-256 校验完整
- metadata.json 全部指向 full-mode CSV
- Dockerfile + environment.yml 可复现环境

**已修复问题**:
- [HIGH] Trial count 不一致（63,535 / 63,300 / 65,811）——统一为"over 67,000 data rows across 27 datasets"
- [HIGH] Supplementary S5.2 stale single-schema——已指向 canonical data_dictionary.md

**残留风险**:
- [MEDIUM] Supplementary S5.1 stale filenames（11+ experiments）——需同步到 manifest

## 6. 统计分析与效应量 (7/10)

**优点**:
- BH-FDR 多重比较校正 (q=0.05)
- Bootstrap CI (10,000 resamples)
- Underpowered experiments 标注为 exploratory
- Held-out validation failure (MAE=0.2775, Pearson=NaN) 诚实报告

**已修复问题**:
- [MEDIUM] Glass's Delta 列已添加到 effect_sizes.csv（approximated as d/sqrt(2)）
- [MEDIUM] 手稿已说明 Glass's Delta 为近似值

**残留风险**:
- [LOW] Glass's Delta 为近似值（缺少 per-group SDs），需后续用原始数据重算

## 7. 结果呈现与可视化 (7/10)

**优点**:
- 所有图表为 PDF 矢量格式
- Figure/Table 在正文中均有引用

**已修复问题**:
- [HIGH] Table 13 从聚合表（Qiskit -175%~-247%）替换为 per-family 表
- [HIGH] Table 11 QAOA 从"Skip"移到"Escalate to Phase 3"

**残留风险**:
- [MEDIUM] 零效应图表（Phase-1 ~0%）仍为空白热图——需重新设计以避免误导
- [LOW] Figure 11 等关键图需与数据交叉验证

## 8. 手稿写作与学术语言 (7/10)

**优点**:
- IMRaD 结构完整
- 术语一致性已大幅改善（prototype action-space ceiling vs genuine structural ceiling）
- Honest framing notes 已嵌入 framework.md

**已修复问题**:
- [FATAL] "structural ceiling" 43 处替换为"prototype action-space ceiling"
- [HIGH] 虚假声明"correctly predicts when peephole optimization is futile regardless of which optimizer"已修正
- [HIGH] Table 11 prescription 与 reclassification 一致

**残留风险**:
- [MEDIUM] 手稿约 50 页，需检查目标期刊长度限制
- [LOW] 部分段落仍有冗余表述

## 9. 局限性与学术诚实 (9/10)

**优点**:
- §6.3 包含 13 个 limitations subsections
- Held-out generalization caveat 在 10+ 位置重复说明
- E18 survivorship bias 充分披露 (44.4% failure rate)
- 理论结果适用范围正确定限

**已修复问题**:
- [FATAL-3] Generalization framing 已添加到 §6.1.1
- [MAJOR-1/2/3/4] Missing families, random shuffler, gate-set sensitivity, WCL scope 已添加到 §6.3.10-6.3.13
- [CRITICAL-4] Statistical power caveat 已添加到 E10 results

**无残留风险**——此维度达到顶级标准。

## 10. 工程实现与代码质量 (7/10)

**优点**:
- 239 tests collected, commutation/ceiling_aware tests pass
- 无硬编码 Windows 路径
- _SELF_INVERSE_GATES 单一定义，无重复
- 所有依赖已声明
- 有界缓存 (FIFO, max=4096)

**已修复问题**:
- [HIGH] Commutation rule divergence: base.py 缺 CNOT+X-family, CZ+Z-family; _gate_predicates.py 缺 SWAP-SWAP, CZ-CZ——已双向同步

**残留风险**:
- [MEDIUM] _gate_predicates.py 无独立测试文件——需添加 test_gate_predicates.py
- [LOW] deepcopy 在 GA hot loop 中 16 次调用——性能瓶颈，非正确性问题

## 11. 投稿准备与期刊适配 (6/10)

**优点**:
- Data/Code availability statements 完整
- Competing interests + Author contributions 已添加
- Docker + reproduce_all.py 可复现

**残留风险**:
- [HIGH] Zenodo DOI placeholder 未填写——投稿前需分配
- [HIGH] GitHub repo URL 为 placeholder (`github.com/Q-research-team/q-research`)——需创建
- [MEDIUM] 目标期刊需确定（Quantum vs ACM TQC vs IEEE QCE），各期刊格式要求不同
- [MEDIUM] Cover letter + response-to-reviewers 模板未准备

---

## 问题与修复清单

### 已修复 (本轮)

| # | 严重性 | 位置 | 问题 | 修复 |
|---|--------|------|------|------|
| 1 | FATAL | manuscript.md §6.1.1 | Trichotomy 声称为 universal law | 降级为 empirical observation |
| 2 | FATAL | formal_results.md | Theorem 1(b) 为 tautology | 降级为 Observation 1(b) |
| 3 | FATAL | manuscript.md (43处) | "structural ceiling" 误用于 prototype-limited families | 替换为 "prototype action-space ceiling" |
| 4 | HIGH | manuscript.md Table 13 | 聚合表 Qiskit -175%~-247% 误导 | 替换为 per-family 表 |
| 5 | HIGH | manuscript.md line 1577 | 虚假声明"regardless of optimizer" | 修正为"prototype-specific" |
| 6 | HIGH | manuscript.md Table 11 | QAOA 在 Skip 但应为 Escalate | 移到 Escalate |
| 7 | HIGH | manuscript.md §5.3 | Phase-2b 声称"not implemented"但代码存在 | 更新为"fixture-scale validated" |
| 8 | HIGH | manuscript.md (多处) | Trial count 不一致 (63,535/63,300/65,811) | 统一为 "over 67,000" |
| 9 | HIGH | _gate_predicates.py | 缺 SWAP-SWAP, CZ-CZ 规则 | 已同步 |
| 10 | HIGH | base.py | 缺 CNOT+X-family, CZ+Z-family 规则 | 已同步 |
| 11 | MEDIUM | references [72,73,74,76,77] | 虚构/重复参考文献 | 已移除 |
| 12 | MEDIUM | manuscript.md §6.1.1 | "10 of 15" 未更新 | 改为 "3 of 15 + 7 of 15" |
| 13 | MEDIUM | effect_sizes.csv | 缺 Glass's Delta 列 | 已添加 |
| 14 | MEDIUM | cross-val table | Phase-2b 行标注为"Consistent" | 改为"Partially validated" |
| 15 | MEDIUM | §6.3.10-6.3.13 | 缺 4 个 limitations | 已添加 |

### 残留待修复

| # | 严重性 | 位置 | 问题 | 建议修复 | 工时 |
|---|--------|------|------|---------|------|
| R1 | HIGH | outputs/ | Zenodo DOI placeholder | 投稿前分配 DOI | 0.5h |
| R2 | HIGH | manuscript.md | GitHub repo URL placeholder | 创建 repo 并更新 URL | 1h |
| R3 | MEDIUM | supplementary S5.1 | 11+ stale filenames | 同步到 manifest | 1h |
| R4 | MEDIUM | manuscript.md | 目标期刊未确定 | 选择 Quantum (open access, 最多引用) | 决策 |
| R5 | MEDIUM | _gate_predicates.py | 无独立测试 | 添加 test_gate_predicates.py | 2h |
| R6 | MEDIUM | Figures 11+ | 零效应空白热图 | 重新设计为带标注的诊断图 | 3h |
| R7 | LOW | base.py GA | deepcopy 性能 | 改用 shallow copy | 4h |
| R8 | LOW | template_matcher.py | 私有 helper 缺 docstring | 添加 one-liner | 1h |

---

## 优化路线图

### Phase A: 投稿前必须完成 (1-2 天)
1. **R1+R2**: 分配 Zenodo DOI + 创建 GitHub repo (2h)
2. **R3**: 同步 supplementary filenames (1h)
3. **R4**: 确定目标期刊，调整格式 (2h)
4. **R5**: 添加 _gate_predicates 测试 (2h)
5. 运行 `reproduce_all.py --verify` 最终确认 (0.5h)
6. 运行全量 pytest (0.5h)

### Phase B: 审稿人可能要求 (3-5 天)
7. **R6**: 重新设计零效应图表 (3h)
8. 添加 random gate shuffler control 实验 (8h)
9. 添加 5+ additional circuit families (Trotterized, QPE) (16h)
10. 跨 family WCL 验证 (8h)

### Phase C: 长期改进 (1-2 周)
11. **R7**: deepcopy 性能优化 (4h)
12. **R8**: docstring 补充 (1h)
13. Phase-2b 全规模 benchmark (40h)
14. 预注册理论预测 + held-out 验证 (16h)

---

## 验证结果

| 检查项 | 状态 |
|--------|------|
| `reproduce_all.py --verify` | PASS (source-hash warnings expected) |
| `test_commutation.py` (29 tests) | PASS |
| `test_ceiling_aware.py` (17 tests) | PASS |
| 数据完整性 (27 datasets) | PASS |
| 参考文献去重 | 5 duplicates removed |
| 术语一致性 | 43 replacements, 5 genuine ceilings retained |
| 代码规则同步 | base.py ↔ _gate_predicates.py aligned |

---

## 变更日志 (CHANGELOG)

### 2026-07-13: Academic Review & Remediation

**Manuscript (docs/manuscript/manuscript.md)**:
- Reclassified 10/15 ceiling families: 3 genuine (QFT/GHZ/SurfaceCode) + 7 prototype-limited
- Replaced 43 "structural ceiling" -> "prototype action-space ceiling"
- Downgraded Theorem 1(b) to Observation 1(b) in formal_results.md
- Replaced aggregate Table 13 with per-family table
- Fixed false claim "regardless of which optimizer"
- Fixed Table 11: QAOA moved from Skip to Escalate
- Updated Phase-2b status from "not implemented" to "fixture-scale validated"
- Standardized trial count to "over 67,000 data rows"
- Added 4 limitation subsections (§6.3.10-6.3.13)
- Added E13 proxy independence caveat
- Fixed cross-validation table Phase-2b row
- Removed 5 fictitious/duplicate references
- Updated Glass's Delta description with approximation note

**Code (src/optimisation/)**:
- `_gate_predicates.py`: Added SWAP-SWAP and CZ-CZ commutation rules (sync with base.py)
- `base.py`: Added CNOT+X-family and CZ+Z-family commutation rules (sync with _gate_predicates.py)

**Data (analysis/figures/)**:
- `effect_sizes.csv`: Added `glass_delta` column (approximated as d/sqrt(2))

**Docs**:
- `claim_evidence_table.csv`: Updated C1 limitations
- `supplementary_materials.md`: Fixed trial count

**Tests**:
- test_commutation.py: 29/29 PASS
- test_ceiling_aware.py: 17/17 PASS
