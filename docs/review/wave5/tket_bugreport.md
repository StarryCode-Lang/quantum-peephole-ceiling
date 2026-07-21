# Wave-5 Report: t|ket> bug report finalization

> **Task ID**: 6 (tket_bugreport)
> **Date**: 2026-07-21
> **Status**: COMPLETE
> **Files produced**:
> - `docs/results/tket_bug_report_final.md` (final bug report, English, ready for GitHub issue)
> - `docs/review/wave5/tket_bugreport.md` (this report)

## 1. Reproduction复核

Reran `experiments/reproduce_tket_clifford_unitarity.py` with the current
environment:

| Package | Version |
|---|---|
| pytket | 2.18.0 |
| pytket-qiskit | 0.77.0 |
| qiskit | 2.4.1 |
| Python | 3.12 (miniforge3) |

**Result: 3/3 recorded failures reproduced, 3/3 controls pass.**

```
 n trial      gates      F_avg     |Tr|    d/2            verdict
-----------------------------------------------------------------
 3     2   30->10     0.333333   4.0000      4         REPRODUCED
 4     4   30->6      0.294118   8.0000     16         REPRODUCED
 5     4   40->10     0.272727  16.0000     16         REPRODUCED
 3     0   25->5      1.000000   8.0000      4       ok (control)
 4     0   28->11     1.000000  16.0000      8       ok (control)
 5     0   44->12     1.000000  32.0000     16       ok (control)
```

The theoretical fidelity `F_avg = (d/4 + 1)/(d + 1)` for a single transposition
matches the observed values exactly at n = 3, 4, 5. Both fix paths confirmed:
`replace_implicit_wire_swaps()` -> 3/3 F = 1.0;
`allow_swaps=False` -> 5/5 F = 1.0 (from the original sweep).

## 2. 终稿路径

`docs/results/tket_bug_report_final.md` - 完整英文 bug report，包含：
- Title / Environment / Summary
- Minimal reproducer（可直接粘贴运行）
- Expected vs Actual behavior
- Reproduction sweep 数据表
- Root cause analysis（隐式置换 -> U·P 而非 U，|Tr(P_σ)| = d/2 推导）
- Fix / workaround（两条已验证路径 + 建议上游默认改为 replace_implicit_swaps=True）
- Related upstream issues 检索结论
- Impact on Q-research（手稿不受影响，已用 allow_swaps=False）

## 3. 上游检索结论

Searched [CQCL/tket issues](https://github.com/CQCL/tket/issues?q=implicit+permutation+tk_to_qiskit)
with query "implicit permutation tk_to_qiskit" (2026-07-21). Found 3 closed
issues, none an exact duplicate:

- **#1747** "Optimisation Pass Failing to Preserve Circuit Equivalence" (closed
  Jan 2025) - general equivalence concern, not `tk_to_qiskit` specific.
- **#1020** "CliffordSimp produces circuit inequivalent to input" (closed Sep
  2023) - different pass.
- **#1573** serialization-related, not relevant.

**No open or closed issue** specifically reports the `tk_to_qiskit` default
dropping implicit permutations. The bug report is therefore filed as a **new
report**, not a "confirmation of existing issue". If the maintainers identify a
duplicate, the root-cause analysis and reproduction data in our report can serve
as supporting evidence.

## 4. 未执行的动作

- **未提交 GitHub issue** - 按铁律，提交动作由 owner 手动执行。
- 终稿面向 CQCL/tket 或 CQCL/pytket-qiskit 仓库（两者均可，owner 判断最佳目标）。

## 5. 对手稿的影响

无。手稿 §12 已用 `allow_swaps=False`，不受此 bug 影响。终稿中的 Impact
section 已声明这一点。

## 6. 铁律遵守

- 禁止 git 操作：遵守。
- 不改其他文件：遵守（仅新建 `docs/results/tket_bug_report_final.md` 和本报告）。
- 数字来自真实复现运行：遵守（脚本输出已嵌入报告）。
