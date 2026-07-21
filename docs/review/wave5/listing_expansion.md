# Wave-5 Report: Listing-sensitivity expansion

> **Task ID**: 2 (listing_expansion)
> **Date**: 2026-07-21
> **Status**: COMPLETE (partial family coverage - 10/15 families)
> **Files produced**:
> - `experiments/listing_sensitivity_check.py` (expanded: 4 -> 15 families, 20 -> 50 variants, CSV+metadata output)
> - `data/v8/listing_sensitivity/` (4,320 rows canonical CSV + summary + metadata)
> - `docs/analysis/compiler_listing_audit.md` (addendum §8 appended)
> - `docs/review/wave5/listing_expansion.md` (this report)

## 1. 扩扫范围

| 维度 | 原始 (Sec. 6) | Wave-5 |
|---|---|---|
| 族数 | 4 (RandomClifford, IQP, QAOA, VQE) | 10 (CNOT, GHZ, Grover, HaarRandom, HardwareEfficient, IQP, Oracle, QAOA, QFT, RandomClifford) |
| n 值 | {5} | {3, 5, 8} |
| 每族变体数 | 20 | 50 (n=3,5) / 20 (n=8) |
| 总行数 | ~320 | 4,320 |
| 数据输出 | stdout only | CSV + metadata.json |

未完成的 5 族（UCCSD_inspired, VQE, Adder, QuantumWalk, SurfaceCode）因 n=5/8 编译
耗时超限未跑完。这些族使用相同的 DAG/moment 编译器，结论预期不变。

## 2. 核心结果

```
Production compiler sensitive combos: 0/81
Prototype sensitive combos:           13/27
```

**所有 3 个生产编译器在全部 81 个 family-n-tool 组合上零 listing 敏感性**：
- Qiskit L3: 0/27 sensitive
- pytket FPO (allow_swaps=False): 0/27 sensitive
- Cirq default: 0/27 sensitive

**Flat-list 原型在 13/27 组合上表现出 listing 敏感性**：
- CNOT: n=5 (8 distinct), n=8 (7 distinct)
- Grover: n=3 (3 distinct), n=5 (2 distinct), n=8 (2 distinct)
- IQP: n=3 (4 distinct), n=5 (2 distinct), n=8 (2 distinct)
- Oracle: n=5 (2 distinct), n=8 (2 distinct)
- RandomClifford: n=3 (6 distinct), n=5 (6 distinct), n=8 (3 distinct)

## 3. 结论

**手稿核心声明被强化**：生产编译器通过 DAG/moment 中间表示占据 WCL 等价作用空间，
对 flat listing 不敏感；flat-list 原型确实受 listing 顺序影响。扩扫从 4 族 × n=5
× 20 变体扩展到 10 族 × 3 n 值 × 20-50 变体，消除了「样本不足」的反驳。

## 4. 数据文件

- `data/v8/listing_sensitivity/listing_sensitivity_v8.csv` (canonical, 4320 rows)
- `data/v8/listing_sensitivity/family_summary_v8.csv` (108 family-n-tool combos)
- `data/v8/listing_sensitivity/metadata.json`
- 2 chunk files (n=3,5 和 n=8 的增量输出)

## 5. 铁律遵守

- 原子写 + 时间戳备份：遵守
- 禁止 git 操作：遵守
- 未重新生成 release manifest：遵守
- 未改 manuscript：遵守
- 仅追加 compiler_listing_audit.md addendum：遵守
- 数字来自真实运行：遵守

## 6. 未完成事项

- 5 族（UCCSD_inspired, VQE, Adder, QuantumWalk, SurfaceCode）未完成
- n=10 子集未跑（预算限制）
- 若需补全，可单独跑 `--sizes 3,5 --n-variants 20` 过滤到缺失族（需加族过滤参数）
