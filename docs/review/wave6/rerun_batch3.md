# Wave-6 Report: Rerun reconciliation 批 3（E19 / E21）

> **Task**: 重跑对账批 3（最难的两个：E19 万行规模、E21 fidelity 昂贵）
> **Date**: 2026-07-21
> **Status**: COMPLETE（2/2 均**全量**重跑并对账；预算内提前完成，无延期项）
> **Files produced**:
> - `data/v9/e19/e19_wcl_listing_full_e19_full_20260721_071617.csv`（10,000 行，全量）
> - `data/v9/e19/metadata.json`
> - `data/v9/e21/ceiling_aware_comparison.csv`（1,140 行，全量）+ `ceiling_aware_summary.csv` + `metadata.json`
> - `data/v9/reconciliation_results.json`（已合并 E19/E21 两键，读-改-写原子写回）
> - `analysis/rerun_e19_checkpointed.py`（E19 断点续跑驱动）
> - `analysis/rerun_e21_checkpointed.py`（E21 断点续跑驱动）
> - `data/v9/e19_partial/`、`data/v9/e21_partial/`（断点现场，留作 provenance）

## 0. 结果总览

| 实验 | canonical 行 | 重跑行 | 完成度 | 判定 | 关键发现 |
|---|---|---|---|---|---|
| E19 | 10,000 | 10,000 | **全量** | **EQUIVALENT（实质 IDENTICAL）**：除 runtime_seconds 外全部列 10,000/10,000 逐值全等 | 生成器/greedy/wire_traversal 哈希虽变，行为逐位等价 |
| E21 | 1,140 | 1,140 | **全量** | **DIVERGED（40/1,140 行）** | 输入哈希 1,140/1,140 一致；40 行差异全部在 IQP 族，与 E14/E16 同一归因 |

两个实验均**未**动用"部分完成"授权：E19 全量约 6.5 分钟（~7 s/depth × 50），
E21 全量约 4 分钟（唯一昂贵配置 QuantumWalk n=6 精确 fidelity 83 s），
均在单机预算内。预估的"E19 万行不可全量 / E21 fidelity 跑不动"均未成真：
E19 电路为 n=5、depth≤50 的小电路，fidelity 走精确路径（32 维）极便宜；
E21 canonical 语义本身对 n>6 传 `target=None`（placeholder fidelity），
精确 AGF 只到 n=6（64 维），无需任何 fidelity 加速补丁。

## 1. 重跑方法（运行时适配声明）

两个实验均用**新写的断点续跑驱动**（仿照 `analysis/rerun_e17_checkpointed.py`）：
通过 `rerun_to_v9.load_patched_module` 加载实验 run.py（源码级把
`output_dir = ... / "v6" / "eYY"` 改写为 `data/v9/eYY`，**experiments/ 零改动**；
RUN_PY 条目在驱动内注入，未改共享的 `rerun_to_v9.py`，避免与批 2 冲突），
逐行复刻 run() 的循环结构与行 schema，每个 depth（E19）/ 每个 (family, n_qubits)
配置（E21）原子追加到 partial CSV，kill 后可断点续跑。

运行参数严格取自 canonical metadata：
- **E19**：seed=42、mode=full、n_qubits=5、depth 1–50、trials_per_depth=100、
  optimizer=both（LBL: `wire_traversal=False`；WCL: `wire_traversal=True`）。
  **无 fidelity 补丁**（n=5 精确路径便宜，且要对账 fidelity 列）。
- **E21**：mode=full（n_trials=10）、seed=42、window=10、
  `max_exact_fidelity_qubits=6`（wave-4 考证的 canonical **有效**阈值，
  而非 metadata 误记的模块常量 12）。trial_rng 消耗顺序与 run() 逐一对齐
  （含异常跳过路径），保证 trial_seed 序列一致。**无 fidelity 补丁**。

## 2. E19（WCL vs LBL）— 10,000/10,000 逐值全等

- 键（depth × trial × listing_model）10,000/10,000 全覆盖；trial_seed 10,000/10,000 一致。
- E19 schema 无 input_circuit_sha256 列，以 `original_size` 作输入同一性代理：
  10,000/10,000 一致（canonical 与重跑生成的电路门数逐行相同）。
- 科学列 `optimized_size`、`reduction`、`fidelity`：**10,000/10,000 逐值全等**
  （max diff = 0.0）。唯一差异列是 `runtime_seconds`（本征非确定）。
- 头条数字复现：LBL mean reduction = 0.0、WCL mean reduction = 0.07828503893953924，
  两端完全一致（canonical notes 的 "WCL 7.83% vs LBL 0%" 成立）。
- **归因**：canonical 之后 `generator_v2.py`（e0d5f541→75bb4876）、
  `greedy.py`（59d50643→3f50c48d）、`wire_traversal.py`（e4d22147→c78ce84f）、
  `base.py`（fa214f3d→9deebb58）、`structural_ceiling.py`（e57ef84b→c36dbb5e）
  均有改动，但对 UNIVERSAL n=5 套件的行为**逐位等价**——改动未触及该套件走过的
  代码路径的输出。E19 run.py 本身哈希未变（32f8a9a4 = canonical）。
- **采用建议**：保留 canonical。E19 是被当前代码**全量精确复现**的最强证据；
  重跑 CSV 仅作 provenance，无替换价值差异。

## 3. E21（ceiling-aware vs naive）— DIVERGED 40/1,140 行，全部可归因

- 键（family × n_qubits × trial_seed × trial_idx × strategy_name）1,140/1,140 全覆盖；
  `input_circuit_sha256` **1,140/1,140 逐位一致**
  （real_benchmarks 5f137e8e 与 generator_v2 75bb4876 自 canonical 以来未变，
  输入层完全冻结）。
- 逐值全等列：`original_size`、`cnot_reduction`、`fidelity`、
  `ceiling_proxy_value` 均 1,140/1,140。
- **差异 1 — gate_reduction 40 行**：全部 IQP 族（naive ×20 + ceiling_aware ×20；
  n=4×14、n=6×14、n=8×10、n=10×2）。方向全部为 canonical 0.0 → 重跑非零
  （IQP 均值 0.0000 → 0.0495）。optimized_size 差异同步（max Δ=4 门）；
  depth_reduction 差异 32 行是这 40 行的子集。
  **归因与 E14/E16 的 IQP 差异完全相同**：`commutation_rewriter.py`
  （033c4ebf→a5376980）+ `_gate_predicates.py`（259956dd→c7c0c6a7）的
  对易/逆对谓词增强，对全对角 IQP 电路能找到更多可消除逆对——
  优化器能力增强，非 canonical 算错，非重跑出错。
- **差异 2 — phase2_skipped 20 行**：全部 IQP × ceiling_aware。canonical 跳过
  phase 2（proxy 判无可消除动作），重跑不跳过并获得 reduction。
  `ceiling_proxy_value` 两端一致（O(m) phase-1 proxy 未变），变化的是
  ceiling-aware 内部 phase-2 动作计数（`ceiling_aware.py` 37c4fd77→53a29f2a
  依赖同一套增强后的对易谓词）。注意这不削弱 E21 结论方向：
  ceiling-aware 在重跑中 reduction 与 naive **逐行相同**（40 行差异两策略同步），
  "不损失压缩率"的主张在新代码下依然成立。
- **差异 3 — fidelity_source 标签 560 行（非数据差异）**：全部 n≥8 行，
  canonical 标 `exact_average_gate_fidelity`、重跑标
  `base_optimizer_large_circuit_estimate`。这正是 wave-4 已考证的误标
  （canonical 用模块常量 12 做阈值）在当前 run.py（8fbd5ed9→2b8771a0，
  含 wave-4 修复）下被纠正；**fidelity 值本身 1,140/1,140 全等**
  （两端同为 1.0 placeholder）。
- **采用建议**：保留 canonical + 标注。手稿若引用 E21 的 IQP 族绝对压缩率
  （canonical 为 0），需注明当前代码下 IQP 不再是零压缩（均值 ~5%）；
  E21 的核心主张（ceiling-aware 省时且不损 reduction）在重跑中方向不变。
  fidelity_source 标签以重跑值为准（wave-4 已背书）。

## 4. 与批 1 的对照

| 项 | 批 1（E13/E14/E16/E17） | 批 3（E19/E21） |
|---|---|---|
| 输入层漂移 | E13 扩族、E17 大面积漂移 | **零漂移**（E19 以 original_size 代理验证；E21 哈希级验证） |
| IQP reduction 增强 | E14 38 行、E16 16 行 | E21 40 行（同归因，第三次独立复现） |
| fidelity 伪迹 | E14 20 行 0.0→1.0 | 无（E21 fidelity 全一致；E19 全一致） |

IQP 归因链（commutation 谓词增强 → IQP 压缩率系统性升高）现已在
E14、E16、E21 三个独立实验上一致复现，可作为对手稿 IQP 相关数字的
统一敏感性说明依据。

## 5. 缺口与遗留

无。两个实验均全量完成、全量对账。断点现场（`data/v9/e19_partial/`、
`data/v9/e21_partial/`）按惯例保留作 provenance，无续跑需求。
批 1 遗留的 E17 qwalk_8 延期项不在本批范围，维持批 1 报告 §5 状态。

## 6. 铁律遵守

- 原子写 + 时间戳备份：遵守（chunk 先 tmp 再追加；最终 CSV tmp + os.replace；
  reconciliation_results.json tmp + os.replace，读-改-写冲突重试，一次成功，
  合并后文件含 E12–E21、E25 全部 11 键，未覆盖批 2 成果）
- 禁止 git 操作：遵守（归因全部基于 metadata source_hashes 对比）
- 未重新生成 manifest；未改 manuscript/appendix/README；未改 canonical
  （data/v2_fixed–v8）；未改批 1/批 2 的 data/v9 子目录：遵守
  （输出仅 data/v9/e19、data/v9/e21、data/v9/e19_partial、data/v9/e21_partial
  与 reconciliation_results.json 的 E19/E21 两键）
- experiments/ 脚本零改动：遵守（驱动内注入 RUN_PY，共享 rerun_to_v9.py 未改）
- 数字真实：遵守（E19/E21 均全量跑出，无编造、无缺口）
- 仓库 Python 全程 /d/Downloads/miniforge3/python：遵守

## 7. 采用建议汇总（仅建议，替换决策归 owner）

| 实验 | 建议 | 理由 |
|---|---|---|
| E19 | 保留 canonical | 10,000/10,000 行被当前代码逐值精确复现（仅 runtime 本征差异） |
| E21 | 保留 canonical + 标注 | 输入 1,140/1,140 一致；40 行 IQP reduction 差异=E14/E16 同归因（优化器增强）；fidelity_source 标签以重跑为准（wave-4 修复）；核心结论方向不变 |
