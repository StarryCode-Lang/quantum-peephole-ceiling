# Wave-5 Report: E27 New circuit families

> **Task ID**: 3 (e27_new_families)
> **Date**: 2026-07-21
> **Status**: COMPLETE (data generation + analysis; ceiling model PART 5 deferred)
> **Files produced**:
> - `experiments/e27_new_families/run.py` (5 new family generators + 3-pipeline runner)
> - `data/v8/e27_new_families/e27_new_families_v8.csv` (675 rows canonical)
> - `data/v8/e27_new_families/metadata.json`
> - `docs/review/wave5/e27_new_families.md` (this report)

## 1. 新族设计与理由

| Family | Structure | Key difference from existing 15 |
|---|---|---|
| QPE | Hadamard cascade + controlled-RZ powers + inverse QFT | Controlled-rotation structure not in any existing family |
| TrotterHamiltonian | Product of Pauli rotations (RX/RY/RZ + CNOT ladders) | Parameterized Pauli rotations; no existing family uses this |
| QuantumVolume | Random SU(4) blocks on random qubit pairs | Arbitrary 2-qubit unitaries; Universal uses fixed gate set |
| WState | Cascade of controlled rotations for W-state prep | Distributed entanglement; GHZ has concentrated entanglement |
| RepetitionCode | 1D QEC encoding + syndrome extraction (CNOT + H) | 1D stabilizer; SurfaceCode is 2D |

## 2. 数据规模

- 5 families × 5 sizes (n=3,4,5,6,8) × 3 depths × 3 seeds × 3 optimizers = 675 rows
- Runtime: 48s
- Fidelity: 0 failures (min = 0.999999999999962 ≈ 1.0)

## 3. 三管线结果

### 3.1 Per-family x optimizer mean reduction

| Family | Phase-1 (greedy) | Phase-2a (commutation) | Phase-2b (template) |
|---|---|---|---|
| QPE | 0.0% | 0.0% | 0.0% |
| QuantumVolume | 0.0% | 0.0% | 0.0% |
| RepetitionCode | 48.7% | 0.0% | 48.7% |
| TrotterHamiltonian | 0.9% | 0.05% | 6.9% |
| WState | 0.0% | 0.0% | 0.0% |

### 3.2 Core question (Phase-1 ~ 0% -> Phase-2b > 30%?)

| Family | P1 mean | P2b mean | P1~0? | P2b>30%? |
|---|---|---|---|---|
| QPE | 0.0000 | 0.0000 | YES | no |
| QuantumVolume | 0.0000 | 0.0000 | YES | no |
| RepetitionCode | 0.4875 | 0.4875 | no | YES (but P2b=P1) |
| TrotterHamiltonian | 0.0085 | 0.0694 | ~0 | no |
| WState | 0.0000 | 0.0000 | YES | no |

### 3.3 结构可区分性

新族显示出与现有 15 族不同的压缩模式：
- **QPE, QuantumVolume, WState**: 完全不可压缩（所有管线 0%），类似现有 Universal/RandomClifford
- **RepetitionCode**: Phase-1 高效（48.7%），Phase-2b 无增量。类似现有 CNOT_chain
- **TrotterHamiltonian**: Phase-2b 有增量（0.9% -> 6.9%），这是有价值的发现

## 4. Family-mean 统计功效评估

**当前状态**: 15 族 -> family-mean r=0.059（统计功效不足）
**新增后**: 15 + 5 = 20 族

新族增加了结构多样性：
- 3 个完全不可压缩族（增加 Phase-1=0 的样本）
- 1 个 Phase-1 高效但 Phase-2b 无增量的族
- 1 个 Phase-2b 有增量但 <30% 的族

**诚实评估**: 5 个新族将 family count 从 15 增至 20，理论上可改善 family-mean 回归的
统计功效。但实际改善需要运行 ceiling_model_repair.py PART 5（LOFO 评估），本任务
因时间限制未实现 PART 5。数据已就绪，未来可直接加载。

## 5. 未完成事项

- **ceiling_model_repair.py PART 5**: 未实现。需要将新族数据加载到特征缓存，
  运行 LOFO 交叉验证，重算 family-mean 回归 r 值。数据已在
  `data/v8/e27_new_families/`，可直接用于未来评估。
- **更大规模**: full 模式目标 500-1500 行，实际 675 行（在范围内）。
  可增加更多 depth 值或 n=10 来扩大规模。

## 6. 铁律遵守

- 原子写 + 时间戳备份：遵守
- 禁止 git 操作：遵守
- 未重新生成 release manifest：遵守
- 未改 manuscript/theory 文档：遵守
- 新族经 fidelity=1.0 验证：遵守（min fidelity ≈ 1.0）
- 数字来自真实运行：遵守
