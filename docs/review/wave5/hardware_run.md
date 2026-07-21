# Wave-5 Report: IBM Quantum real-hardware validation

> **Task ID**: 5 (hardware_run)
> **Date**: 2026-07-21
> **Status**: COMPLETE (no-credentials path - experiment NOT executed)
> **Files produced**:
> - `docs/review/wave5/hardware_run.md` (this report)

## 1. 前置凭据检查

| Check | Result |
|---|---|
| `QISKIT_IBM_TOKEN` environment variable | **absent** (empty) |
| `~/.qiskit/qiskitrc` saved account | **absent** (file does not exist) |

**Decision**: Per the task's前置检查铁律, with both credential sources absent,
the experiment portion is **NOT executed**. No real-hardware data is generated or
simulated.

## 2. 文档状态确认

`docs/results/hardware_validation.md` current state:
- §1–§6: Noise-model simulation results (fake backends, 288 rows in
  `data/v8/hardware_validation/`). These are properly labeled as simulations.
- §7: Real-hardware protocol (`experiments/hardware_validation/real_hardware_protocol.py`)
  - Ready to run, credential guard verified (exits code 2 without token)
  - Cost estimate: 3–8 min QPU time, within Open Plan free quota
  - Success criteria C1–C4 defined
- §8: Reproduction instructions for the noise-model run
- §9: Limitations (noise-model only, not hardware)

**No §8 real-hardware results section exists** - the current §8 is
"Reproduction" (noise-model), not real-hardware results. The task specified
appending a new §8 for real results; since no experiment was run, no §8
appendix is made. The document remains accurate as-is.

## 3. 真机实验未执行声明

**无凭据，真机实验未执行。** 本次 wave-5 未产生任何真机数据。所有定量结果
仍来自 `data/v8/hardware_validation/` 的噪声模型模拟（fake backends），与
wave-4 状态一致。

## 4. 对手稿的影响

无变化。手稿 EHW 节已正确标注为噪声模型模拟，非真机数据。真机验证仍为
future work（§7 协议就绪，待凭据）。

## 5. 铁律遵守

- 无凭据时严禁模拟数据冒充真机：遵守（未生成任何数据）。
- 禁止 git 操作：遵守。
- 未改 `docs/results/hardware_validation.md`：遵守（无真机结果可追加）。
- 未重新生成 release manifest：遵守。

## 6. 后续条件

当 IBM Quantum token 可用时，执行：
```
D:\Downloads\miniforge3\python.exe experiments\hardware_validation\real_hardware_protocol.py --dry-run
D:\Downloads\miniforge3\python.exe experiments\hardware_validation\real_hardware_protocol.py --shots 8192 --seed-reps 3
```
然后追加 §8 真机结果到 `docs/results/hardware_validation.md`。
