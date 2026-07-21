# Wave-6 Report: E27 PART 5 — 新族加入 LOFO 评估（15 → 20 族）

> **Task**: ceiling_model_repair PART 5（wave-5 遗留项）
> **Date**: 2026-07-21
> **Status**: COMPLETE
> **Files produced**:
> - `experiments/ceiling_model_repair.py`（新增 `--part5` 子命令；PART 1–4 逻辑未动）
> - `data/v6/ceiling_repair/part5_e27_features.csv`（122 条唯一新族线路：特征 + naive 管线标签）
> - `data/v6/ceiling_repair/part5_lofo_results.csv`（3 个配置 × 逐 fold 指标）
> - `data/v6/ceiling_repair/part5_summary.json`（汇总、新旧对照、门行为、判定）
> - `docs/theory/universal_law_assessment.md`（追加 wave-6 addendum；备份 `…bak-20260721-132800`）
> - `docs/review/wave6/e27_part5.md`（本报告）

## 1. 标签问题与方法（必须先说清）

E27 数据（675 行）只独立跑了三个优化器，**从未运行** E21 定义模型目标的
naive 管线（Phase1 → Phase2 → Phase1）。因此 PART 5 不能用 CSV 里任何一列
直接当 `gate_reduction` 标签。采取的做法：

1. 按 `(circuit_family, param_n, depth, seed)` 取 225 个唯一线路规格，用
   `experiments/e27_new_families/run.py` 的原生成器确定性重建线路；
2. **双重验证**（全部 225/225 通过，任一失败即 raise）：
   - `circuit.size()` == CSV `original_size`；
   - 重跑 Phase-1 的 reduction 与 CSV `greedy_phase1` 列**逐位一致**；
3. 内容级去重（sha256，族内）：WState 不依赖 depth/seed（每尺寸 9 份相同）、
   QPE 不依赖 depth、RepetitionCode param_n=3 被提升为 n=4 与 param_n=4 相同
   —— 共丢弃 103 条重复，保留 **122 条唯一线路**
   （QPE 15 / QuantumVolume 45 / RepetitionCode 12 / TrotterHamiltonian 45 / WState 5）；
4. 用与 E21 完全相同的 naive 管线（Greedy(100) → Commutation(window=10) →
   Greedy(100)）重算标签；机制特征定义与 PART 2 逐字段一致。

合并数据集：570（E21 naive）+ 122 = **692 行 / 20 族**。

**协议保真**：在任何 20 族数字之前，先在原 15 族上复现 wave-4 V4 ——
MAE 0.017240047 / r 0.976939886 / ρ 0.852745940，与
`regime_intervention_summary.json` **全位一致**（`matches_wave4: true`）。

## 2. 20 族 LOFO 主结果（V4 混合模型，seed 42，mechanism 特征）

| 指标 | 15 族（wave-4 V4） | 20 族（PART 5 V4） | 20 族 V0（纯 RF，对照） |
|---|---|---|---|
| Pooled MAE [CI95] | 0.0172 [0.0129, 0.0218] | **0.0188 [0.0144, 0.0236]** | 0.0424 [0.0345, 0.0506] |
| Pooled Pearson r [CI95] | 0.977 [0.963, 0.987] | **0.967 [0.948, 0.979]** | 0.940 [0.909, 0.965] |
| Pooled Spearman ρ | 0.853 | **0.654** | 0.654 |
| Pooled R² | 0.954 | 0.934 | 0.776 |
| CNOT fold MAE | 0.000 | 0.000（不变） | 0.409 |
| 最差 fold MAE | 0.146（RandomClifford） | **0.303（RepetitionCode）** | 0.409（CNOT） |
| NaN-Pearson folds | 11/15 | 14/20 | 14/20 |

- ρ 下降是**并列值伪影**：三个不可压缩新族贡献约 65 条 actual=0 且预测≈0
  的行，秩统计无法排序；Pearson/R² 基本维持 wave-4 水平。
- V4 相对 V0 在 20 族上仍然全面占优（MAE −0.024，r +0.027），机制门在
  新族上**零误触发**。

## 3. Family-mean 回归：n = 15 → 20（新旧对照）

协议与 PART 3b(a) 完全一致（族均值 combined 特征 + RF，LOO）：

| 配置 | n | MAE | Pearson r | Spearman ρ |
|---|---|---|---|---|
| 旧（发布值 / 本次复现） | 15 | 0.114 | **0.059** | — |
| 新（纯 RF） | 20 | 0.085 | **0.780** | 0.510 |
| 新（RF + V4 门作用于族均值） | 20 | 0.050 | **0.887** | — |

**诚实判定：r 实质改善（+0.72），但改善的性质要说清**——增益主要来自
低端方差：QPE / QuantumVolume / WState 实际值严格为 0 且预测接近 0。
两个难点依然难：纯 RF 下 CNOT（实际 1.0）预测 0.30（n=15 时为 0.056，
RepetitionCode 进入训练池后部分改善），RepetitionCode（实际 0.486）预测
0.04。V4 门作用于族均值后 CNOT 精确闭合（r→0.887），但 RepetitionCode
不受影响。**结论：n=15 的统计功效局限被缓解而非消除；对未见过的
高压缩机制的逐族外推仍是 binding failure。**

## 4. 新族逐族门规则行为（V4 gate: 2·phase1_density ≥ 1）

| 族 | 行数 | 实际均值 | density max | 门触发率 | fold MAE | fold r |
|---|---|---|---|---|---|---|
| QPE | 15 | 0.000 | 0.000 | 0.00 | 0.000007 | NaN（零方差） |
| QuantumVolume | 45 | 0.000 | 0.000 | 0.00 | 0.000007 | NaN |
| WState | 5 | 0.000 | 0.000 | 0.00 | 0.000000 | NaN |
| TrotterHamiltonian | 45 | 0.009 | 0.020 | 0.00 | 0.0059 | 0.835 |
| **RepetitionCode** | 12 | **0.486** | **0.248** | 0.00 | **0.3034** | **−0.826** |

- 门在新族上**零误触发**（无任何 false positive 候选）。
- 三个不可压缩族被模型（RF 部分）正确预测为 ≈0。
- TrotterHamiltonian 预测良好。

## 5. 新失败模式：RepetitionCode fold（如实报告 + 归因）

**现象**：RepetitionCode fold MAE 0.303（V0 与 V4 相同——门不触发），
fold 内 Pearson 为**负**（−0.826）。这是新族暴露的模型失效，不粉饰。

**归因（全部为计算事实）**：

1. RepCode 的压缩（0.466–0.496）完全来自相邻 H–H / CX 逆对抵消——12/12 行
   Phase-1-only reduction == naive 全管线 reduction；
2. 其 phase1_action_density（0.233–0.248）位于普通族（≤0.0345）与 CNOT
   （0.5）之间：V4 饱和规则（2d ≥ 1）**正确地**不触发，但训练池中没有任何
   族占据这个中间密度区，树回归无法把叶均值插值到 y≈0.49（预测≈0.18）；
3. 静态结构上限（structural_upper_bound）在 12/12 行上与实际压缩**逐行精确
   相等**（差 < 1e-12）——oracle-bound 预测器在该 fold 上 MAE=0。**失效在
   学习映射，不在机制特征**。

这与 wave-4 对 CNOT 的诊断是同一局限：树模型的外推失效不限于饱和端点，
而是覆盖整个中间密度 regime。

**附带观察**：纯 RF（V0）下，RepCode 进入训练池使 CNOT fold MAE 从 0.745
降至 0.409——进一步证实"机制相似的族"是树模型插值的必要条件。

## 6. 对手稿的影响（§6.6 / §7.6 对照表）

手稿未改。完整对照表已写入 `docs/theory/universal_law_assessment.md` 的
wave-6 addendum，要点：

- §6.6 Table 18 best row：MAE 0.0172→0.0188、r 0.977→0.967、ρ 0.853→0.654、
  R² 0.954→0.934（若采用 20 族为规范数字）；
- §7.6 family-mean 局限：r=0.059 (n=15) → r=0.780/0.887 (n=20)，局限措辞应
  从"功效不足"软化为"逐族外推失效"；
- §7.6 新增局限条目：RepetitionCode fold MAE 0.303（中间密度 Phase-1 regime
  的学习组件外推失效）；
- NaN-Pearson folds：11/15 → 14/20；CNOT fold 维持 0.000。

## 7. 铁律遵守

- 原子写 + 时间戳备份：遵守（part5_* 均为 .tmp→replace；assessment 备份
  `universal_law_assessment.md.bak-20260721-132800`）；
- 禁止 git 操作：遵守；
- 未重新生成 release manifest：遵守；
- 未改 manuscript：遵守（仅 assessment 追加 addendum）；
- PART 1–4 逻辑未改：遵守（仅新增 `--part5` 分支与 PART 5 函数；15 族复现
  全位一致可证）；
- 数字来自真实运行：遵守（225/225 线路双验证通过；复现检查
  `matches_wave4: true`）。

## 8. 复现

```bash
/d/Downloads/miniforge3/python experiments/ceiling_model_repair.py --part5
```
