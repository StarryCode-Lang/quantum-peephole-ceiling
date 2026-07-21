# Wave-6 Report: Phase-2b cross-product grid completion (depth_fill2)

> **Task**: Phase-2b 交叉积补全（wave5 finalize.md §5 第 7 条缺口）
> **Date**: 2026-07-21
> **Status**: COMPLETE — 无剩余缺口
> **Files produced**:
> - `experiments/phase2b_full_validation.py`（新增 `depth_fill2` chunk +
>   `--plan-start/--plan-limit` 切片参数；metadata 覆盖率声明改为从合并数据自动推导）
> - `data/v8/phase2b_full/phase2b_v8_depth_fill2_20260721_13{1807,1914,2233,2353,2425,2827,2843,3014}.csv`
>   （8 个切片，共 720 新行）
> - `data/v8/phase2b_full/phase2b_full_validation_v8.csv`（合并 canonical，2427 行）
> - `data/v8/phase2b_full/family_summary_v8.csv`、`core_question_v8.csv`、
>   `bv_theory_v8.csv`、`bootstrap_ci_v8.csv`（重新生成）
> - `data/v8/phase2b_full/metadata.json`（重新生成，覆盖率声明更新为 56/56 全因子）
> - `docs/review/wave6/phase2b_crossfill.md`（本报告）

## 1. 缺口确认（数据驱动）

合并表 1707 行核实：depth 族（Universal / RandomClifford / Structured / IQP）
在 n=3..10 × depth={20..50 step 5} 的 56 个 (n, depth) 组合中已覆盖 36 个，
缺失恰好为 finalize §5 第 7 条所述 20 个交叉组合：
n={4,6,7,9,10} × depth={25,30,40,45}。

## 2. 执行方式

- 新增 chunk `depth_fill2`：4 族 × 5 n × 4 depth × 3 seeds = 240 网格点
  × 3 optimizers = **720 计划行**。seed 公式与 wave5 一致
  （`BASE_SEED + seed*100 + n*10 + d`，seed∈{1,2,3}）。
- 为适配单条命令 ≤250s 的时间约束，新增 `--plan-start/--plan-limit` 切片参数，
  分 8 次调用跑完；每片写独立时间戳 chunk CSV，merge 按网格键去重（keep=last）。
- 各片墙钟耗时：47s / 178s / 72s / 24s / 234s / 9s / 83s / 82s，合计 **729s**。
  （720 行的 optimizer `runtime_seconds` 合计仅 49.1s；墙钟主要由 fidelity
  计算主导——n=9 exact Operator 与 n=10 sampled200 最慢。）
- 每片完成后数据落盘；全部完成后一次 `--merge-only` 合并分析。

## 3. Fidelity 合规

- **0 行 fidelity < 1-1e-9**（新 720 行及合并 2427 行均为 0），无需剔除记录。
- 新行 fidelity_method 分布：exact=576, clifford_tableau=36, sampled200=108。
  - n=10 RandomClifford 走 Clifford-tableau 精确相等（12 网格点 × 3 opt = 36）✓
  - n=10 Universal/Structured/IQP 走 sampled200（3 族 × 12 × 3 = 108）✓；
    优化器未改变这些线路时采样估计经结构相等快速路径返回精确 1.0。
  - 其余 n≤9 全部 exact ✓
- 合并后全表分布：exact=2103, clifford_tableau=123, sampled200=201。

## 4. 结果

### 4.1 覆盖率（最终）

- depth 族 **56/56 (n, depth) 组合全覆盖**，每组合 3 seeds × 3 optimizers。
- metadata.coverage.depth_parameterized_families 自动推导更新为：
  "FULL factor grid n=3..10 x depth={20,25,30,35,40,45,50} (56/56 combos)
  x 3 seeds per depth family"。

### 4.2 族均值稳定性（template_phase2b）

| Family | wave5 (1707行) | wave6 (2427行) | Δ | 稳定? |
|---|---|---|---|---|
| BV | 0.692 | 0.6922 | +0.0002 | YES |
| IQP | 0.920 | 0.9202 | +0.0002 | YES |
| Structured | 0.409 | 0.4019 | -0.0071 | YES |
| RandomClifford | 0.509 | 0.5163 | +0.0073 | YES |

新 20 组合 vs 旧 36 组合（各族 template_phase2b 均值）：

| Family | 旧 36 组合 | 新 20 组合 | 全 56 组合 |
|---|---|---|---|
| Universal | 0.1411 | 0.1396 | 0.1406 |
| RandomClifford | 0.5092 | 0.5290 | 0.5163 |
| Structured | 0.4087 | 0.3898 | 0.4019 |
| IQP | 0.9195 | 0.9214 | 0.9202 |

**结论：补全交叉积后族均值变化 < 0.8pp，wave5 的分层抽样结论
（stratified 均值是全因子均值的无偏估计）进一步成立。**

### 4.3 核心判据（2427 行）

- Core question：BV (P2b=0.6922) 与 Structured (P2b=0.4019) 仍 >30%，其余族否。判定不变。
- BV vs Theorem 9：n=3..10 全部 PASS（mean/min 均超 rigorous lower bound），与 wave5 一致。
- Bootstrap 95% CI (pooled)：P1 0.0047 [0.0010, 0.0095]；
  P2a 0.0896 [0.0819, 0.0973]；P2b 0.4849 [0.4647, 0.5051]（wave5: 0.4807，稳定）。

### 4.4 行数变化

| 指标 | wave5 | wave6 |
|---|---|---|
| 总行数 | 1707 | 2427 (+720, +42.2%) |
| depth 族 (n,depth) 覆盖 | 36/56 | **56/56** |
| Fidelity 失败行 | 0 | 0 |

## 5. 剩余缺口

**无。** depth 族 n=3..10 × depth={20..50 step 5} 全因子网格已闭合。

## 6. 铁律遵守

- 原子写 + 时间戳备份：遵守（merge_and_analyze 用 `_atomic_write_csv`；
  metadata.json 写前生成 .bak- 时间戳备份）。
- 禁止 git 操作：遵守。
- 未重新生成 release manifest：遵守。
- 未改任何 docs（除本报告）：遵守。
- 数字真实可溯源：遵守（全部来自上述 chunk CSV 与合并表）。
