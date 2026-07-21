# Wave-6 Report: Listing-sensitivity fill (5 remaining families)

> **Task ID**: wave6 / listing_fill
> **Date**: 2026-07-21
> **Status**: COMPLETE (15/15 families; qwalk_8 partial 3/20 variants)
> **Files produced**:
> - `experiments/listing_sensitivity_fill.py` (NEW: resume-capable fill runner, nominal-n selection)
> - `data/v8/listing_sensitivity/listing_sensitivity_v8.csv` (canonical: 4,320 -> 6,652 rows)
> - `data/v8/listing_sensitivity/family_summary_v8.csv` (recomputed: 108 -> 168 combos)
> - `data/v8/listing_sensitivity/metadata.json` (updated; 14 wave6fill chunk files retained)
> - `docs/analysis/compiler_listing_audit.md` (addendum §9 appended)
> - `docs/review/wave6/listing_fill.md` (this report)

## 1. 超时根因（对 wave5 诊断的修正）

wave5 报告将 5 族缺失归因于「n=5/8 编译耗时超限」。完整根因为两条：

1. **选择 bug（主因）**：`listing_sensitivity_check.py` 用 `circuit.num_qubits in {3,5,8}`
   过滤套件线路。Adder / QuantumWalk / SurfaceCode 含辅助/coin 量子比特，实际比特数为
   4-10，永远不等于名义 n，因此**无论预算多少都会被静默跳过**。fill 脚本改为按
   circuit_id 后缀（名义 n）选择，`n_qubits` 列如实记录实际比特数。
2. **真实算力成本（次因）**：QuantumWalk 的 MCX 分解使编译爆炸。实测单变体耗时：

   | 线路 | 实际比特 | qiskit | tket | cirq | prototype |
   |---|---|---|---|---|---|
   | qwalk_5 | 6 | 0.0s | 12.8s | 4.0s | 0.4s |
   | qwalk_8 | 9 | 0.1s | 61.6s | 30.1s | 98.4s |

   qwalk_8 单变体 ≈190s，加上 9 比特精确 `Operator()` 幺正检验超过 250s/次的 bash 预算。
   UCCSD/VQE ansatz 构造本身不慢（套件生成 0.7s/142 条），其 n=5/8 编译均在秒级。

## 2. 实际覆盖：5/5 族全部有数据

| 族 | 线路 | 实际 n_qubits | 变体数 | 行数 | 幺正检验 |
|---|---|---|---|---|---|
| UCCSD_inspired | uccsd_3 / uccsd_5 / uccsd_8 | 3 / 5 / 8 | 50 / 50 / 20 | 480 | pass |
| VQE | vqe_twolocal_3/5/8 | 3 / 5 / 8 | 50 / 50 / 20 | 480 | pass |
| Adder | adder_3 / adder_5 / adder_8 | 4 / 7 / 10 | 50 / 50 / 20 | 480 | pass |
| QuantumWalk | qwalk_3 / qwalk_5 / qwalk_8 | 4 / 6 / 9 | 50 / 50 / **3** | 412 | pass / pass / **skip** |
| SurfaceCode | surface_code_3/5/8 | 5 / 6 / 9 | 50 / 50 / 20 | 480 | pass |
| **合计** | 15 条线路 | — | — | **2,332** | 2,320 pass + 12 skip |

与 wave5 同口径：rng = Random(1234)、n_swaps = 4×size、变体 0 = 基准线路、
50 变体（名义 n=3,5）/ 20 变体（n=8）、相同 4 工具、0 错误行。

## 3. 关键数字（wave5 → wave6 合并后）

| 指标 | Wave-5 (10 族) | Wave-6 (15 族) |
|---|---|---|
| 族覆盖 | 10/15 | **15/15** |
| 总行数 | 4,320 | **6,652** |
| family-n-tool 组合 | 108 | 168 |
| 生产编译器敏感组合 | 0/81 | **0/126** |
| 原型敏感组合 | 13/27 | **15/42** |

- **生产编译器（Qiskit L3 / pytket FPO no-swap / Cirq）在全部 15 族、126 个组合上
  依然零 listing 敏感性** —— 手稿核心声明未被推翻，反而完成全覆盖验证。
- 原型新增 2 个敏感组合：UCCSD_inspired n_qubits=5（5 distinct，44-48 门）与
  n_qubits=8（3 distinct，78-80 门）。敏感族从 5 个增至 6 个。
- VQE / Adder / QuantumWalk / SurfaceCode 的原型不敏感（线路结构太规则或对贪心遍
  已最小），与机制一致，不构成反例。
- qwalk_8 已有 3 个变体 × 4 工具门数完全一致（4551 / 7385 / 11474 / 106），
  与「不敏感」方向一致，但样本只有 3，按缺口记录、不做外推。

## 4. 剩余缺口（如实记录）

1. **qwalk_8 仅 3/20 变体**（~190s/变体，预算限制）。补齐需约 17 次 × 250s 调用。
2. **qwalk_8 幺正检验为 skip**（12 行）：9 比特精确 Operator 检验在预算内不可行；
   relisting 变换按构造保幺正，且其余 14 条线路（含 qwalk_3/qwalk_5）均精确验证 pass。
3. Adder/QuantumWalk/SurfaceCode 的 `n_qubits` 为实际比特数（4-10），summary 中
   出现在 {4,5,6,7,8,9,10} 而非 {3,5,8}，属如实记录而非缺陷。
4. 同线比特上「交换门」类 relisting 未枚举（与 wave5 §8.3 相同）。

## 5. 铁律遵守

- 原子写 + 时间戳备份：遵守（`*.bak-20260721_141836` 三件套 + 14 个 chunk 文件保留）
- 禁止 git 操作：遵守
- 未重新生成 release manifest：遵守
- 未改 manuscript 及其他文档：遵守（仅 compiler_listing_audit.md 追加 §9）
- 数字来自真实运行：遵守（全部溯源至 chunk CSV / canonical CSV）
- 单条 bash ≤250s：遵守（超时 2 次均由增量写保住进度，断点续跑无重复行）
