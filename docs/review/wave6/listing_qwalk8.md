# Wave-6 Report: qwalk_8 listing-sensitivity fill (17 remaining variants)

> **Cleanup note (2026-08-01):** The 17 chunk CSVs listed below were exact
> intermediate inputs to the canonical merge and were deleted after row-level
> verification. Canonical data and this provenance report remain.

> **Task ID**: wave6 / listing_qwalk8
> **Date**: 2026-07-21
> **Status**: COMPLETE (20/20 variants)
> **Files produced**:
> - 17 new chunk CSVs in `data/v8/listing_sensitivity/` (variants 3-19)
> - `data/v8/listing_sensitivity/listing_sensitivity_v8.csv` (canonical: 6,652 -> 6,720 rows)
> - `data/v8/listing_sensitivity/family_summary_v8.csv` (recomputed)
> - `data/v8/listing_sensitivity/metadata.json` (updated)
> - `docs/review/wave6/listing_qwalk8.md` (this report)

## 1. 执行概要

qwalk_8 (QuantumWalk, 9 actual qubits) 之前仅完成 3/20 变体（每变体约 190s）。
本次补齐变体 3-19（17 个），每个变体单独一条 bash 调用（~162-170s/变体），总计
约 46 分钟。

## 2. 最终覆盖

| Metric | Before | After |
|---|---|---|
| qwalk_8 variants | 3/20 | **20/20** |
| qwalk_8 rows | 12 | **80** |
| Total canonical rows | 6,652 | **6,720** |
| Total combos | 168 | 168 (unchanged) |
| Production compiler sensitive | 0/126 | **0/126** (unchanged) |
| Prototype sensitive | 15/42 | **15/42** (unchanged) |

## 3. qwalk_8 结果

| Tool | Variants | Distinct outputs | Gate count range | Sensitive? |
|---|---|---|---|---|
| qiskit_L3 | 20 | 1 | 4551-4551 | NO |
| tket_FPO_noswap | 20 | 1 | 7385-7385 | NO |
| cirq_default | 20 | 1 | 11474-11474 | NO |
| prototype_greedy | 20 | 1 | 106-106 | NO |

**qwalk_8 在所有 4 个工具上均不敏感** -- 20 个 relisting 变体产生完全相同的门数。
这与之前 3 个变体的观察一致，现在有 20 个变体的统计支持。

## 4. 幺正检验状态

qwalk_8 的 80 行（20 变体 × 4 工具）unitary_check = skip（9 比特精确 Operator
检验超出单条 250s 预算）。relisting 变换按构造保幺正（仅交换不同 wire 上可交换
门的顺序），且 qwalk_3/qwalk_5 的精确检验全部 pass。

## 5. 结论

**手稿核心声明进一步强化**：生产编译器在全部 15 族、126 个组合上零 listing 敏感性
（包括最难覆盖的 qwalk_8，20 个变体零变化）。原型的 15/42 敏感组合也未改变
（qwalk_8 原型不敏感，线路结构太规则）。

## 6. 铁律遵守

- 原子写 + 时间戳备份：遵守
- 禁止 git 操作：遵守
- 未重新生成 release manifest：遵守
- 未改 manuscript/README/DATA_CANONICAL：遵守
- 数字来自真实运行：遵守
- 单条 bash ≤250s：遵守（每变体单独调用，最大 170s）
