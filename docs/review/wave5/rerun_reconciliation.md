# Wave-5 Report: Rerun reconciliation (E12–E21, E25)

> **Task ID**: 4 (rerun_reconciliation)
> **Date**: 2026-07-21
> **Status**: PARTIAL (1/11 rerun: E25 EQUIVALENT; 10/11 not rerun within budget)
> **Files produced**:
> - `data/v9/e25/e25_industry_benchmarks_e25_industry_proxies_20260721_033411.csv` (rerun)
> - `data/v9/reconciliation_results.json` (automated comparison)
> - `analysis/rerun_reconciliation.py` (reusable reconciliation framework)
> - `docs/review/wave5/rerun_reconciliation.md` (this report)

## 1. 重跑结果

| Experiment | Canonical rows | Rerun? | Status | Note |
|---|---|---|---|---|
| E12 | 568 | No | NOT_RERUN | Compute budget |
| E13 | 56 | No | NOT_RERUN | Timed out (structural ceiling analysis) |
| E14 | 2130 | No | NOT_RERUN | Compute budget |
| E15 | 994 | No | NOT_RERUN | Compute budget |
| E16 | 696 | No | NOT_RERUN | Compute budget |
| E17 | 755 | No | NOT_RERUN | Compute budget |
| E18 | 270 | No | NOT_RERUN | Compute budget |
| E19 | ~10000 | No | NOT_RERUN | Compute budget (largest) |
| E20 | — | No | NOT_RERUN | Compute budget |
| E21 | 1140 | No | NOT_RERUN | Compute budget |
| **E25** | **66** | **Yes** | **EQUIVALENT** | **All scientific columns 66/66 identical** |

## 2. E25 详细对账

E25 (industry benchmarks) 是唯一完成重跑的实验。

### 2.1 逐字段对比

| Column | Max diff | Match | Total |
|---|---|---|---|
| reduction | 0.000000 | 66 | 66 |
| fidelity | 0.000000 | 66 | 66 |
| original_size | 0.000000 | 66 | 66 |
| optimized_size | 0.000000 | 66 | 66 |
| runtime_seconds | 0.135442 | 0 | 66 |

### 2.2 判定: EQUIVALENT

- 所有科学字段（reduction, fidelity, original_size, optimized_size）66/66 完全一致
- runtime_seconds 差异（max=0.135s）是预期的非确定性差异（硬件负载、系统调度）
- **采用建议**: E25 canonical 数据可安全保留。重跑确认了数据的可复现性。
  无需替换 canonical，因为科学字段已完全一致。

## 3. E13 重跑尝试

E13 (structural ceiling, 56 rows) 被尝试重跑但超时（>5min）。E13 的 run.py 涉及
结构上限分析，可能包含昂贵的 exact fidelity 计算。建议未来以更长超时或分块方式重跑。

## 4. 未完成实验清单

以下 10 个实验因计算预算未重跑，'source modified since run' 警告保持不变
（已在 docs/reproducibility.md 记录为已接受状态）：

E12, E13, E14, E15, E16, E17, E18, E19, E20, E21

### 建议优先级（未来重跑）

1. E13 (56 rows) - 最小，但需要更长超时
2. E18 (270 rows) - 较小
3. E16 (696 rows), E17 (755 rows) - 中等
4. E12 (568 rows), E15 (994 rows), E21 (1140 rows) - 中等
5. E14 (2130 rows) - 较大
6. E19 (~10000 rows), E20 - 最大，需要分块

## 5. 对账框架

`analysis/rerun_reconciliation.py` 是可复用的对账工具：
- 自动查找 data/v9/<eXX>/ 下的重跑 CSV
- 逐字段比较 reduction/fidelity/original_size/optimized_size（确定性字段）
- runtime_seconds 单独报告（非确定性）
- 三级判定：IDENTICAL / EQUIVALENT / DIVERGED
- 输出 JSON 结果到 data/v9/reconciliation_results.json

未来重跑更多实验时，只需将重跑 CSV 放入 data/v9/<eXX>/ 并重新运行此脚本。

## 6. 铁律遵守

- 原子写 + 时间戳备份：遵守
- 禁止 git 操作：遵守
- 未重新生成 release manifest：遵守
- 未修改 canonical 数据（data/v2_fixed..v8）：遵守
- 重跑输出仅在 data/v9/：遵守
- 未改 manuscript 及其他文档：遵守
- E25 重跑结果与 canonical 一致，未擅自「修正」：遵守

## 7. 采用建议总结

| 实验 | 建议 | 理由 |
|---|---|---|
| E25 | 保留 canonical | 科学字段 100% 一致，无需替换 |
| E12-E21 | 保留 canonical | 未重跑，警告已记录为已接受 |
| 全部 | 保留 canonical | 无证据表明 canonical 数据有误 |

**本报告仅为建议，替换决策由 owner 做。**
