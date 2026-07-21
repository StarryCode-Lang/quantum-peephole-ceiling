# Wave-6 Report: Rerun reconciliation 批 1（E13 / E16 / E17 / E14）

> **Task**: 重跑对账批 1（接续 wave5 `docs/review/wave5/rerun_reconciliation.md`）
> **Date**: 2026-07-21
> **Status**: COMPLETE（4/4 均已重跑并对账；E17 有 21 个 (circuit, topology) 对因单条预算限制延期，均不影响 canonical 重叠区——除 qwalk_8）
> **Files produced**:
> - `data/v9/e13/e13_structural_ceiling_e13_full_20260721_052604.csv`（142 行）
> - `data/v9/e14/e14_extended_benchmark_e14_full_20260721_*.csv`（2130 行）
> - `data/v9/e16/e16_window_scaling_e16_full_20260721_053236.csv`（2130 行）
> - `data/v9/e17/e17_connectivity_e17_full_20260721_054304.csv`（1189 行，405/426 对）
> - `data/v9/reconciliation_results.json`（已刷新，含 overlap 分析）
> - `analysis/rerun_to_v9.py`（通用重跑 wrapper，输出重定向 v9）
> - `analysis/rerun_e17_checkpointed.py`（E17 断点续跑驱动）
> - `analysis/rerun_reconciliation.py`（扩展：行数分叉时的 overlap 对账）
> - `data/v9/e17_partial/`（E17 断点现场 + 损坏版备份，留作 provenance）

## 0. 结果总览

| 实验 | canonical 行 | 重跑行 | 行数 | 重叠区判定 | 关键发现 |
|---|---|---|---|---|---|
| E13 | 56 | 142 | 分叉 | **OVERLAP_IDENTICAL**（56/56 键、输入哈希 56/56、12 个科学列全等） | 仅生成器扩族（7→15 族） |
| E14 | 2130 | 2130 | **一致** | 逐行对比：2072/2130 全等 | 38 行 IQP reduction 变化 + 20 行 fidelity 0.0→1.0 |
| E16 | 696 | 2130 | 分叉 | 696/696 键全覆盖；680/696 reduction 一致 | 16 行 IQP reduction 变化；fidelity 全一致 |
| E17 | 755 | 1189 | 分叉 | 726/741 ok 键可比；输入一致行 54/54 全等 | 拓扑/生成器变化致大面积输入漂移；qwalk_8 延期 |

**结论速读**：四个实验的 canonical 数据在"相同输入"下均可被当前代码**精确复现**
（E13 全列、E14/E16 除 IQP 与 fidelity 异常行外、E17 输入一致行 54/54）。
观察到的差异全部可归因到 canonical 运行之后的源码改动，无任何随机或不可解释成分。
' **source modified since run**' 警告对 E13/E14/E16/E17 现在有完整证据链；
其余 7 个实验（E12/E15/E18/E19/E20/E21）警告维持 wave5 的"已接受"状态。

## 1. E13 超时根因（wave5 遗留问题）

根因**不是** structural ceiling 分析本身，而是优化器收尾的保真度计算：

1. `GreedyGateCancellation.optimize` / `HybridCommuteRewrite.optimize` 在 `target=circuit`
   调用时各做一次 `calculate_fidelity`。
2. n=12 时走精确路径：构造两个 4096×4096 `Operator` 做矩阵乘，**实测单次 ~70 秒**。
   E13 full 有 9 个 n=12 电路 ≈ 10.5 分钟，仅此一项就超过 wave5 的 5 分钟预算。
3. n=15/20 走采样估计：review H4 修复把 `DEFAULT_FIDELITY_SAMPLES` 从 100 提到 1000，
   且改为 Haar 乘积态方案；1000 样本 × 2 条电路 × 2^20 维态矢量演化，大电路单次数十分钟。

E13 的输出 schema **完全不含 fidelity/success 列**（只有结构上限与门数指标），
因此重跑时对 `calculate_fidelity` 做了整体旁路（对任何记录列零影响）。
旁路后 E13 full（142 电路）仅 2.8 秒。

## 2. 重跑方法（运行时适配声明）

所有重跑用 `analysis/rerun_to_v9.py`：读入实验 run.py 源码，仅改写
`output_dir = ... / "vX" / "eYY"` 一行为 `data/v9/<eYY>` 后 exec，
**experiments/ 下脚本零改动**（源码哈希不变，metadata 中记录的是原文件哈希）。
运行参数严格取自各实验 canonical `metadata.json`
（mode=full、seed=42、window=10、max_qubits_fidelity=10、window_sizes=[2,5,10,20,50]、
topologies=[linear,grid,heavy_hex]）。

E14/E16/E17 启用 `--fast-fidelity` 运行时适配（**只影响 fidelity 列与速度，
不触碰 reduction/门数/结构列**）：
1. 相同电路短路返回 1.0（精确语义，canonical 时代同值 1±1e-15）；
2. 双 Clifford 且表相等短路返回 1.0（精确语义）；
3. 按 (输出哈希, 目标哈希) 记忆化（实验循环对同一输出重复算 fidelity）；
4. 精确路径上限 n≤12→n≤10（n=12 的 70 秒/次是预算杀手；n=11/12 改走采样）；
5. 采样样本数 1000→32。对功能保持型优化器每个样本重叠恰为 1.0，与精确值一致；
   且采样器使用 `RandomState(None)`，canonical 时代本来就不可逐值复现。

E17 另用断点续跑驱动（见 §5）。

## 3. 分实验对账

### 3.1 E13（structural ceiling）— DIVERGED(行数) / 重叠区 IDENTICAL

- canonical 56 行（7 族 × 8 尺寸），重跑 142 行（15 族，生成器 v4→v5 扩族）。
- 56 个 canonical circuit_id **全部**在重跑中；`input_circuit_sha256` 56/56 一致。
- 12 个科学列（gate_count_total、depth、structural_upper_bound_reduction、
  observed_best_reduction/gate_count、ceiling_gap、structural_lower_bound、
  cancellable/mergeable/commuting 各计数）56/56 **逐值全等**（max diff = 0.0）。
- **归因**：唯一差异来源是 `src/circuits/real_benchmarks.py` 扩族
  （canonical 哈希 a113f1cf → 当前 5f137e8e）。optimizer/ceiling 逻辑虽有改动
  （structural_ceiling.py、greedy.py、commutation_rewriter.py、base.py 哈希均变），
  但对这 56 个电路的行为逐值等价。
- **采用建议**：保留 canonical。E13 canonical 的每一行都被当前代码精确复现；
  重跑 CSV 可另作 v5 扩展族的新数据使用（新数据，非替换）。

### 3.2 E14（extended benchmark）— DIVERGED（行数一致，58/2130 行有差异）

- 行数 2130 = 2130；**全部 2130 行输入电路哈希一致**（生成器对 full 套件逐位复现）。
- reduction 差异 38 行：**全部在 IQP 族**（iqp_5…iqp_20），只涉及
  commutation_phase2（19 行）与 hybrid_phase1_2（19 行），window ∈ {10,20,50}；
  当前代码移除更多门（如 iqp_6/w20：canonical 34→34，重跑 34→28，Δ=+0.176）。
  greedy_phase1 零差异。
- fidelity 差异 20 行：canonical 的 0.0 全部变为 1.0（qwalk_10×13、iqp_10×2、
  clifford_10×5，均为 reduction=0 的未变更电路）。canonical 的 0.0 是当时
  保真度计算失败留下的伪迹；当前代码（含短路）返回正确的 1.0。
- 其余 2072 行（含全部门数、depth/2q/cnot 指标）逐值全等。
- **归因**：`commutation_rewriter.py`（10433159→a537698）与 `base.py`
  （85099cb4→9deebb58）改动。IQP 为全对角电路，门门可对易；当前 commutation
  谓词能在窗口内找到更多可消除逆对——与 structural_ceiling.py 注释中记录的
  review FATAL-1 系列修复（对易/逆对语义统一）方向一致，属**优化器能力增强**，
  不是 canonical 算错，也不是重跑出错。
- **采用建议**：倾向保留 canonical，但必须标注：手稿中凡引用 IQP 族
  phase-2/hybrid reduction 的数字，在当前代码下会系统性偏高（更大压缩）。
  若手稿结论依赖 IQP 的绝对压缩率，建议 owner 决策是否以 v9 重跑值做敏感性附注。
  20 行 fidelity=0.0 是 canonical 已知伪迹，v9 值为正确值。

### 3.3 E16（window scaling）— DIVERGED(行数) / 重叠区 680/696 一致

- canonical 696 行（87 电路 × 2 优化器 × 4 窗口）；重跑 2130 行
  （142 电路 × 3 优化器 × 5 窗口，run.py 结构已变：新增 phase1_only、window=50）。
- canonical 696 个键**全覆盖**；输入电路哈希 648/696 一致，
  变化的 48 行 = adder_3…adder_8（生成器 adder 量子比特数改变），
  但这 48 行 reduction 仍全部一致。
- reduction 差异 16 行：全部 IQP（iqp_5/6/7/8 × commutation/hybrid × window 10/20），
  与 E14 同一归因（commutation_rewriter 增强）。
- fidelity 696/696 全一致（canonical n≤9，双端均为精确路径）。
- **采用建议**：保留 canonical。手稿的 window-scaling 结论（Conjecture 2 支撑数据）
  涉及的窗口 {2,5,10,20} 与优化器对均在重叠区内且除 IQP 外逐值一致；
  IQP 各行差异方向为"当前代码更优"，不改变"窗口增大收益饱和"型结论的方向。

### 3.4 E17（connectivity）— DIVERGED(行数) / 重叠区大面积输入漂移

- canonical 755 行（87 电路，含 14 个 transpile_error 行）；重跑 1189 行
  （142 电路 × 3 拓扑，405/426 对完成，21 对延期见 §5）。
- 741 个 canonical ok 键中 726 个可比；缺失 16 键：
  qwalk_8×9（延期）+ adder_5/6 heavy_hex×6 与 adder_7 heavy_hex×1
  （生成器把 adder 从 n=5/6/7 改为 n=7/7/10，heavy_hex(n=7) 报错——与 canonical
  时代 adder_7/heavy_hex 报错行为一致，属输入漂移而非回归）。
- **输入一致的 54 行：reduction、fidelity 54/54 逐值全等**（max 3.6e-15）。
- 672 行输入漂移：transpile 后门数大幅变化（如 qwalk_8/linear 基线
  canonical 23082 vs 重跑 41468），reduction 随之不同（总体 594/726 一致）。
  qiskit 版本两端相同（2.4.1），漂移来源是 **run.py 拓扑函数与生成器改动**
  （e17 run.py 哈希 9b8f1e5a→e09a832a；real_benchmarks a113f1cf→5f137e8e；
  heavy_hex 规模从 max 6 qubits 变为 max 20 qubits）。
- **归因**：输入层（电路生成 + 拓扑约束）变更，非优化器回归。
  在相同输入上当前代码精确复现 canonical。
- **采用建议**：保留 canonical。E17 canonical 的绝对门数锚定旧拓扑/旧生成器，
  重跑值不可直接替换；若手稿引用 E17 绝对门数或 heavy_hex 结果，
  建议注明其对应 v5 时代拓扑定义。qwalk_8（canonical n≤9 内）未能重跑，
  其 9 行维持"未验证"状态。

## 4. 对账框架更新

`analysis/rerun_reconciliation.py` 新增 `reconcile_overlap()`：行数分叉时按键
（circuit_id × optimizer × window_size × topology）求交集，报告
输入/输出电路哈希一致率与科学列逐值对比，判定
OVERLAP_IDENTICAL / OVERLAP_EQUIVALENT / OVERLAP_DIVERGED。
`data/v9/reconciliation_results.json` 已用新框架刷新（E13/E14/E16/E17 含 overlap 细节）。

## 5. 缺口与遗留

| 项 | 状态 | 说明 |
|---|---|---|
| E17 qwalk_8×3 拓扑（9 对） | **延期** | 在 canonical 范围内（n=9）。transpile 后 41,468 门，忠实优化单次 >250 s；canonical 当年该行三优化器耗时 145/145/581 s。估计需 ~1-2 小时（分对断点可续）。 |
| E17 qwalk_9/10、grover_10、adder_10、cnot_chain_20(grid/hh)、surface_code_20（12 对） | 延期 | 均不在 canonical（n≥10 新行），不影响重叠对账；补跑只为 v9 数据完整。 |
| E12, E15, E18, E19, E20, E21 | 未重跑 | 批 2/3 处理；警告维持已接受状态。 |
| e17_partial/ | 保留 | 断点现场 partial.csv（已修复为统一 29 列 schema：修复前有 3 种列布局，备份 `partial_backup_20260721_broken.csv`）；如需续跑延期对可直接复用。 |

## 6. 铁律遵守

- 原子写 + 时间戳备份：遵守（断点 chunk 先写 tmp 再追加；最终 CSV 先 tmp 再 os.replace；损坏现场已备份）
- 禁止 git 操作：遵守（归因全部基于 metadata.json source_hashes 对比与源码注释，未调用 git）
- 未重新生成 release manifest：遵守
- 未修改 canonical（data/v2_fixed–v8）与 manuscript：遵守（重跑输出仅在 data/v9/）
- experiments/ 脚本零改动：遵守（wrapper 源码级重定向，文件哈希不变）
- 重跑与 canonical 实质不一致处（E14 IQP 38 行、E16 IQP 16 行、E17 输入漂移行）均已如实记录，未擅自"修正"canonical：遵守
- 仓库 Python 全程使用 /d/Downloads/miniforge3/python：遵守

## 7. 采用建议汇总（仅建议，替换决策归 owner）

| 实验 | 建议 | 理由 |
|---|---|---|
| E13 | 保留 canonical | 56/56 行被当前代码逐值精确复现 |
| E14 | 保留 canonical + 标注 | IQP 38 行 reduction 在当前代码下系统性更高；20 行 fidelity=0.0 为已知伪迹。若手稿引用 IQP 压缩率需敏感性说明 |
| E16 | 保留 canonical | 696 键全覆盖，除 16 行 IQP（同 E14 归因）外逐值一致；fidelity 全一致 |
| E17 | 保留 canonical + 标注 | 差异全部来自输入层（生成器+拓扑）变更；相同输入 54/54 精确复现；绝对门数锚定旧拓扑定义 |
| E12/E15/E18/E19/E20/E21 | 保留 canonical | 未重跑，警告维持已接受（待批 2/3） |
