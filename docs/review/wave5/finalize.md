# Wave-5 Finalize Report

> **Task ID**: 7 (finalize)
> **Date**: 2026-07-21
> **Commit**: cf315dd
> **Release**: q-research-9.0.0-wave5
> **Status**: COMPLETE

## 1. Wave-5 任务完成情况

| Task | Agent | Status | Key output |
|---|---|---|---|
| 1. Phase2b grid expansion | phase2b_fullgrid | COMPLETE | 735 -> 1,707 rows; depth families n=3..10 x depth=20..50 |
| 2. Listing sensitivity | listing_expansion | PARTIAL (10/15 families) | 4,320 rows; 0/81 production compiler sensitive |
| 3. E27 new families | e27_new_families | COMPLETE (PART 5 deferred) | 675 rows; 5 new families (QPE, TrotterHam, QV, WState, RepCode) |
| 4. Rerun reconciliation | rerun_reconciliation | PARTIAL (1/11 rerun) | E25 EQUIVALENT; reconciliation framework built |
| 5. Hardware validation | hardware_run | COMPLETE (no credentials) | No IBM token; status report only |
| 6. t|ket> bug report | tket_bugreport | COMPLETE | 3/3 reproduced; final bug report ready for GitHub issue |

## 2. 改动清单

### 2.1 新增数据

| Dataset | Path | Rows | New? |
|---|---|---|---|
| E_listing_sensitivity_v8 | data/v8/listing_sensitivity/ | 4,320 | NEW |
| E27_new_families | data/v8/e27_new_families/ | 675 | NEW |
| E26_phase2b_full_v8 | data/v8/phase2b_full/ | 1,707 | EXPANDED (was 735) |
| E25 rerun | data/v9/e25/ | 66 | NEW (rerun, not canonical) |

### 2.2 新增脚本

| File | Purpose |
|---|---|
| experiments/e27_new_families/run.py | 5 new circuit family generators + 3-pipeline runner |
| analysis/rerun_reconciliation.py | Reusable rerun-vs-canonical comparison framework |

### 2.3 修改的脚本

| File | Change |
|---|---|
| experiments/phase2b_full_validation.py | Added `depth_fill` chunk + incremental write |
| experiments/listing_sensitivity_check.py | Expanded to all families, CSV+metadata output, --sizes param |

### 2.4 新增报告 (docs/review/wave5/)

| File | Content |
|---|---|
| phase2b_fullgrid.md | Grid expansion report (735->1707 rows, means stable) |
| listing_expansion.md | Listing sensitivity expansion (0/81 production sensitive) |
| e27_new_families.md | New families report (5 families, diverse reduction patterns) |
| rerun_reconciliation.md | Rerun report (E25 EQUIVALENT, 10/11 not rerun) |
| hardware_run.md | Hardware status (no credentials, not executed) |
| tket_bugreport.md | t|ket> bug report finalization (3/3 reproduced) |
| finalize.md | This report |

### 2.5 新增文档

| File | Content |
|---|---|
| docs/results/tket_bug_report_final.md | Final English bug report for CQCL/tket |

### 2.6 修改的文档

| File | Change |
|---|---|
| README.md | 34->36 datasets, 73,702->79,669 rows, 735->1,707 phase2b rows, version 9.0.0 |
| data/DATA_CANONICAL.md | 34->36 datasets, 73,702->79,669 rows, new dataset entries |
| docs/supplementary/supplementary_materials.md | 34->36 datasets, 73,702->79,669 rows, new entries |
| docs/analysis/compiler_listing_audit.md | Addendum Section 8 (wave-5 listing expansion) |
| release/release_manifest.json | Regenerated: 36 datasets, 79,669 rows |

## 3. 验证结果

| Check | Result |
|---|---|
| reproduce_all.py --verify | PASS (36/36 datasets, all SHA-256 OK) |
| pytest tests/ -q --timeout=600 | PASS (298 passed, 0 failed, 261s) |
| .bak file cleanup | DONE |
| git commit | cf315dd |
| git push origin master | OK (0e3d10e..cf315dd) |

## 4. 关键数字变化

| Metric | Before (wave4) | After (wave5) | Change |
|---|---|---|---|
| Datasets | 34 | 36 | +2 |
| Total rows | 73,702 | 79,669 | +5,967 |
| Phase2b rows | 735 | 1,707 | +972 |
| Phase2b depth families n-values | {3,5,8} | {3..10} | +5 values |
| Phase2b depth families depth-values | {20,35,50} | {20..50 step 5} | +4 values |
| Listing sensitivity families | 4 | 10 | +6 |
| Listing sensitivity variants | 20 | 20-50 | +30 |
| New circuit families | 0 | 5 | +5 |
| Release version | 8.0.0-wave4 | 9.0.0-wave5 | - |

## 5. 仍未完成事项

1. **Listing sensitivity**: 5/15 families not completed (UCCSD_inspired, VQE, Adder, QuantumWalk, SurfaceCode) due to compute-time constraints at n=5/8
2. **E27 ceiling model PART 5**: LOFO evaluation with new families not implemented; data is ready in data/v8/e27_new_families/
3. **Rerun reconciliation**: 10/11 experiments not rerun (E12-E21); E13 timed out; framework is reusable
4. **IBM Quantum real-hardware**: No credentials available; protocol ready in experiments/hardware_validation/real_hardware_protocol.py
5. **t|ket> GitHub issue**: Not submitted (owner to post manually)
6. **Manuscript updates**: Only phase2b row count synced in README; manuscript.md/appendix.md not modified per task rules ("其他一律不动")
7. **Phase2b grid**: n={4,6,7,9,10} x depth={25,30,40,45} cross-product (20 combos per family) not completed

## 6. 铁律遵守

- 原子写 + 时间戳备份: 遵守
- 禁止 git 操作 (tasks 1-6): 遵守 (commit 仅在 task 7)
- 未重新生成 release manifest (tasks 1-6): 遵守 (regen 仅在 task 7)
- 未改 manuscript (tasks 1-6): 遵守
- 数字可溯源: 遵守 (每个数字溯源到 wave5 报告或数据文件)
- 英文文档、中文返回: 遵守
