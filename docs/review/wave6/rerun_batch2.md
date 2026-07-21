# Wave-6 Report: Rerun reconciliation 批 2（E12 / E15 / E18 / E20）

> **Task**: 重跑对账批 2（接续 `docs/review/wave6/rerun_batch1.md`）
> **Date**: 2026-07-21
> **Status**: PARTIAL（E12、E15 完成重跑+对账；E18、E20 超出本轮预算，记为缺口并附续跑指引）
> **Files produced**:
> - `data/v9/e12/e12_compiler_baseline_e12_full_20260721_072841_nocoupling.csv`（560 行）+ `metadata.json`
> - `data/v9/e15/e15_multi_compiler_e15_full_20260721_075707.csv`（986 行）+ `metadata.json`
> - `data/v9/e12_partial/`、`data/v9/e15_partial/`（断点现场 + `deferred.json` 延期清单，留作 provenance）
> - `analysis/rerun_to_v9.py`（RUN_PY 扩展 e12/e15/e18/e20 条目）
> - `analysis/rerun_e12_checkpointed.py`、`analysis/rerun_e15_checkpointed.py`（断点续跑驱动）
> - `data/v9/reconciliation_results.json`（E12/E15 键已刷新；E18/E20 保持 NOT_RERUN）

## 0. 结果总览

| 实验 | canonical 行 | 重跑行 | 行数 | 重叠区判定 | 关键发现 |
|---|---|---|---|---|---|
| E12 | 568 | 560 | 分叉（-8 延期） | **OVERLAP_IDENTICAL**（560/560 键，全列逐值全等） | 跨 Python/numpy 环境仍逐位复现 |
| E15 | 994 | 986 | 分叉（-8 延期） | 978/986 全等；8 行 IQP 可归因 | 输入哈希 986/986 一致，零输入漂移 |
| E18 | 270 | — | 未重跑 | 缺口 | 分解爆炸+单条 250 s 预算不可行，见 §4 |
| E20 | 1070 | — | 未重跑 | 缺口 | 需分 10 个 trial 续跑，见 §4 |

**结论速读**：E12/E15 的 canonical 数据在相同输入下被当前代码**逐值精确复现**
（E12 全列含 fidelity；E15 除 8 行 IQP 外全列）。E15 的 8 行差异与批 1 的 E14/E16
完全同源（commutation_rewriter 增强，方向为当前代码移除更多门）。
两实验各有 qwalk_9、grover_10 共 8 行因精确保真度成本延期（见 §3），不影响重叠区结论。

## 1. 重跑方法（运行时适配声明）

沿用批 1 框架：`analysis/rerun_to_v9.py`（RUN_PY 新增 e12/e15/e18/e20，
experiments/ 零改动，参数严格取自 canonical metadata：E12 `no_coupling_map=True`、
E15 `skip_cirq=True, skip_tket=True`、E20 `skip_custom=True, per_circuit_timeout=60`）。

单条 bash ≤250 s 约束下新增两个断点续跑驱动（模式同批 1 `rerun_e17_checkpointed.py`，
逐 (circuit, level) / (circuit, block) 原子 flush，重跑即续跑）：
- `analysis/rerun_e12_checkpointed.py`：**无**保真度适配（transpile + 精确 fidelity n≤10，
  与 canonical 完全同路径）；含成本护栏（§3）。
- `analysis/rerun_e15_checkpointed.py`：custom 优化器路径启用批 1 的
  `--fast-fidelity` 适配（exact≤10q、32 采样、相等/Clifford 短路、记忆化；
  只影响 fidelity 列）；**qiskit 行不做任何适配**，与 canonical 同路径。

环境核对（与 canonical metadata 比对）：
- E15/E18/E20 canonical 环境 = 当前环境：python 3.12.12、qiskit 2.4.1、
  numpy 1.26.4、pandas 2.2.2、scipy 1.13.1、cirq 1.6.1、pytket 2.18.0 —— 全部一致。
- E12 canonical 环境为 python 3.10.20 / numpy 2.2.6（qiskit 同为 2.4.1）；
  重跑用仓库 python 3.12.12 / numpy 1.26.4，实测对结果**零影响**（§2.1）。

源码哈希归因基线（当前值 vs canonical source_hashes）：

| 文件 | E12 canon | E15 canon | E20 canon | 当前 |
|---|---|---|---|---|
| 各 run.py | 10f7595c | bd06667e | ebee5ff9 | e12:10f7595c / e15:abd412e4 / e18:0eb2abde / e20:cf4c43a1 |
| real_benchmarks.py | 5f137e8e | a113f1cf | 5f137e8e | 5f137e8e |
| generator_v2.py | 75bb4876 | 94ef14ad | 75bb4876 | 75bb4876 |
| base.py | ac66c717 | 85099cb4 | ac66c717 | 9deebb58 |
| greedy.py | 59d50643 | 29c52bc2 | 59d50643 | 3f50c48d |
| commutation_rewriter.py | bf301a58 | 10433151 | bf301a58 | a5376980 |

要点：E12 的 run.py 与生成器**完全未变**且不使用自研优化器 → 预期精确复现（证实）。
E15 的生成器哈希虽变（a113f1cf→5f137e8e），但 extended suite 全部 142 电路
**逐位一致**（输入哈希 986/986）；优化器改动只显现在 IQP 8 行。

## 2. 分实验对账

### 2.1 E12（Qiskit transpiler 基线，no-coupling 公平模式）— OVERLAP_IDENTICAL

- canonical 568 行（142 电路 × opt_level 0-3）；重跑 560 行（缺 qwalk_9、grover_10 各 4 行，§3）。
- 560/560 键（circuit_id × level）全覆盖；**输入电路哈希 560/560、输出电路哈希 560/560 一致**。
- 逐值对比（max diff 全为 0.0）：baseline_gate_count、optimized_gate_count、reduction、
  depth、compiled_depth 均 560/560 全等；fidelity 的 432 个 exact 值 **432/432 逐位全等**，
  128 个 unavailable 两端一致（fidelity_source 交叉表完全吻合）。
- 注意：canonical 运行在 python 3.10 / numpy 2.2.6，重跑在 python 3.12 / numpy 1.26.4，
  qiskit 2.4.1 + seed_transpiler=42 的 transpile 与精确保真度**跨环境逐位复现**。
- **归因**：无差异可归因——run.py/real_benchmarks/generator_v2 哈希均未变；
  自研优化器虽有改动但 E12 不调用。
- **采用建议**：保留 canonical。140/142 电路被当前代码逐值精确复现；
  qwalk_9/grover_10 两行（8 行数据）补跑后预期同样一致（同属无差异代码路径）。

### 2.2 E15（multi-compiler 基线：custom + qiskit）— 978/986 全等，8 行可归因

- canonical 994 行（142 电路 × 7 行：3 custom + 4 qiskit）；重跑 986 行
  （缺 qwalk_9、grover_10 的 qiskit 行各 4 行；两电路的 custom 行已完成，§3）。
- 986/986 键（circuit_id × compiler × backend × opt_level）全覆盖，rerun 无多余键。
- **输入电路哈希 986/986 一致**——尽管生成器哈希 a113f1cf→5f137e8e，
  extended suite（full, seed=42）全部 142 电路逐位复现，零输入漂移。
- 差异恰为 8 行：`iqp_5/6/7/8 × {commutation_phase2, hybrid_phase1_2}`，
  方向全部为当前代码移除更多门（如 iqp_6：canonical 0.0 → 重跑 0.1176；
  iqp_7：0.0556 → 0.1111）。greedy_phase1 与全部 4 级 qiskit 行**零差异**。
- 其余列：baseline_gate_count 986/986、cnot_reduction 986/986、
  fidelity 858/858（max 2.8e-12，采样噪声级）、depth/two_qubit reduction 978+/986。
- **归因**：与批 1 E14/E16 完全同源——`commutation_rewriter.py`（10433151→a5376980）
  与 `base.py`（85099cb4→9deebb58）改动。IQP 为全对角电路，门门可对易；
  当前对易谓词能找到更多可消除逆对（review FATAL-1 系列修复方向），
  属**优化器能力增强**，非 canonical 算错、非重跑出错。
- **采用建议**：保留 canonical + 标注（与批 1 E14 同一建议）：
  手稿凡引用 E15 中 IQP 族 phase-2/hybrid 压缩率的数字，在当前代码下系统性偏高；
  其余 978 行（含全部 qiskit 基线行，这是 E15 的审稿人关注点）逐值复现。

## 3. 延期清单（E12/E15 共同）

| 电路 | 位置 | 原因 | 估计补跑成本 |
|---|---|---|---|
| qwalk_9（n=10） | E12 缺 4 行；E15 缺 4 行 qiskit（custom 行已完成） | transpile 后门数爆炸（L0: 118→6916 门），n=10 精确平均门保真度需将编译后线路组合为 1024 维稠密 Operator，单层 >250 s | 4 层 × ~4 min ≈ 15-25 min（分层断点已支持，删掉 `deferred.json` 中对应条目并在驱动中放宽护栏即可续跑） |
| grover_10（n=10） | 同上 | 同上（L0: 68→1772 门） | ≈ 5-10 min |

与批 1 E17 qwalk_8 延期同根因（qwalk 族 transpile 门数爆炸 × 精确保真度），
均为 canonical 内行，状态记为"未验证"，**不影响**其余行的对账结论。
延期明细落盘于 `data/v9/e12_partial/deferred.json`、`data/v9/e15_partial/deferred.json`，
并写入 v9 两实验 metadata.json 的 `deferred_circuits` 字段。

## 4. 缺口与续跑指引（E18 / E20 未启动）

### 4.1 E18（Clifford+T）— 超出本轮预算

- **单次直跑已证不可行**：`rerun_to_v9.py e18 --fast-fidelity` 在 240 s 被杀、零产出。
  根因是**输入漂移的连锁反应**：canonical 时代（生成器 a113f1cf）含参族
  （qft/qaoa/vqe/hardware_eff/qwalk/uccsd…）在 Clifford+T 分解时抛
  BasisTranslator 错误（canonical 270 行中 78 行是 decompose_error，ok 行
  baseline ≤152 门）；当前生成器（5f137e8e）改变了这些族的门类型，分解**成功**，
  产出最高 29,760 门（qwalk_3）的巨线，优化器单次远超预算。qwalk_8/9/10 更大。
- **续跑方案**：写 `analysis/rerun_e18_checkpointed.py`（复制 e15 驱动模式），
  逐电路 flush + 延期护栏：`decompose_to_clifford_t` 后门数 >2500 的电路记为
  deferred（canonical ok 集最大 152 门，护栏不影响重叠区）；原线路 >600 门的
  直接跳过分解。预计工程量：驱动 ~30 行适配 + 3-6 个 250 s 分片（~15-25 min），
  覆盖全部 64 个 canonical-ok 电路与新增可分解小电路。
- 起跑命令（驱动写好后）：
  `/d/Downloads/miniforge3/python -u analysis/rerun_e18_checkpointed.py`（重复至 COMPLETE）

### 4.2 E20（MC-E20：qiskit/cirq/tket 全编译器）— 超出本轮预算

- 规模：10 trials × 43 电路/trial = 430 个电路运行（qiskit 全部 + cirq n≤8 + tket n≤6，
  单电路超时 60 s），单次 250 s 无法完成；run.py 只在结尾写 CSV，必须分片。
- 有利条件：生成器/real_benchmarks 哈希**未变**（输入应零漂移）；
  qiskit 2.4.1 / cirq 1.6.1 / tket 2.18.0 与 canonical **版本完全一致**；
  run.py 哈希有变（ebee5ff9→cf4c43a1），需在对账时确认其行为差异（若逐值复现则
  证明改动不影响该路径）。`skip_custom=True`，自研优化器改动无关。
- **续跑方案**：按 trial 分片——`seed=42+i, n_trials=1`（i=0..9）逐片调用
  （每片 trial_seed 与 canonical 第 i 个 trial 一致），每片完成后把
  `data/v9/e20/multi_compiler_full.csv` 移存为 `parts/part_i.csv` 再跑下一片；
  10 片合并后 trial 列按 `trial = seed - 42` 重映射，手工写 metadata.json。
  对账需自定义键（circuit_id × trial × compiler_name），通用对账脚本不覆盖 E20 的
  多 trial 键结构。预计 10-15 片 × 1-3 min ≈ 15-30 min。
- 起跑命令：`/d/Downloads/miniforge3/python analysis/rerun_to_v9.py e20 --extra seed=43 n_trials=1`
  （seed 依次取 42..51；wrapper 默认已带 `skip_custom=True, per_circuit_timeout=60`）

## 5. 对账框架状态

`data/v9/reconciliation_results.json` 已刷新：E12/E15 由 NOT_RERUN 更新为
DIVERGED(行数分叉) + overlap 明细（行数差全部为 §3 延期行）。
注意：通用脚本的 overlap 键（circuit_id × optimizer）对 E12/E15 的多行/电路结构
只取首行，**本文 §2 的按键精确对比（E12: circuit_id×level；E15: circuit_id×compiler×
backend×level）才是完整证据**，两者结论一致。

## 6. 铁律遵守

- 原子写 + 备份：遵守（分片先写 tmp 再追加；最终 CSV 先 tmp 再 os.replace；
  断点现场与 deferred.json 全部保留）
- 禁止 git 操作：遵守（归因全部基于 metadata source_hashes 对比）
- 未重生成 manifest；未改 manuscript/appendix/README；未改 canonical（v2_fixed–v8）：遵守
- experiments/ 零改动：遵守（wrapper 源码级重定向 + 独立 ckpt 驱动，原文件哈希不变）
- 数字真实：遵守（E18/E20 如实记缺口；延期行如实记"未验证"）
- 全程 `/d/Downloads/miniforge3/python`：遵守

## 7. 采用建议汇总（仅建议，替换决策归 owner）

| 实验 | 建议 | 理由 |
|---|---|---|
| E12 | 保留 canonical | 560/560 行（含 fidelity 逐位）被当前代码精确复现；缺 8 行为算力延期非差异 |
| E15 | 保留 canonical + 标注 | 978/986 逐值一致（含全部 qiskit 基线行与 fidelity）；8 行 IQP 同批 1 E14/E16 归因，方向为当前代码更优 |
| E18 | 保留 canonical | 未重跑（§4.1 缺口，警告维持已接受） |
| E20 | 保留 canonical | 未重跑（§4.2 缺口，警告维持已接受） |
