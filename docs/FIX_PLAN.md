# Q-Research 项目修复计划

## Phase 1: CRITICAL Bug 修复 (立即)

### 1.1 E10 analyze.py or True bug
文件: experiments/e10_phase1_vs_phase2/analyze.py:306
修改: 移除 or True

### 1.2 E10 analyze.py Binder cumulant 按族分组
文件: experiments/e10_phase1_vs_phase2/analyze.py:297-300
修改: 按 circuit_family 分组计算 Binder cumulant

### 1.3 PROJECT_ROOT 未定义
文件: analysis/phase2_threshold_sensitivity/run.py:118
修改: 添加 PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

### 1.4 Pearson NaN 不对齐
文件: analysis/generate_figures.py:666-668
修改: 使用 e2[[col1, col2]].dropna()

### 1.5 success=False 谓词修复
文件: src/optimisation/base.py (success 判断逻辑)
修改: 调查并修复 success 列计算

### 1.6 DATA_CANONICAL.md 更新
文件: data/DATA_CANONICAL.md
修改: 更新文件名以匹配磁盘实际文件

### 1.7 Manifest 修复
文件: release/release_manifest.json
修改: 删除重复 E10 条目，重新生成哈希

### 1.8 删除 core.py 重复统计
文件: analysis/phase1_statistics/core.py
修改: 删除文件，更新 generate_figures.py 和 phase2_threshold_sensitivity/run.py 导入

### 1.9 事后功效分析修复
文件: scripts/phase7_statistical_remediation.py:560-835
修改: 替换为前瞻性功效分析

### 1.10 特征泄漏修复
文件: scripts/phase7_statistical_remediation.py:1007-1077
修改: 仅使用结构特征

## Phase 2: 实验修复

### 2.1 E04 多种子评估
文件: experiments/e04_algorithm_comparison/run.py
修改: 每个优化器运行多个种子

### 2.2 E12 保真度计算
文件: experiments/e12_compiler_baseline/run.py
修改: 添加保真度验证

### 2.3 E20 数据生成
文件: experiments/e20_multi_compiler_full/run.py
修改: 运行实验生成 CSV

### 2.4 E19 WCL 实验
文件: experiments/e19_wcl_listing/run.py
修改: 完成实验运行

### 2.5 E17 零缩减调查
文件: experiments/e17_connectivity/run.py
修改: 调查并修复

### 2.6 E21 保真度计算
文件: experiments/e21_ceiling_aware/run.py:198
修改: 实际计算保真度而非硬编码 1.0

### 2.7 环境同步
文件: requirements.txt, environment.yml
修改: 同步 pytket, pytest 等依赖

## Phase 3: 手稿修复

### 3.1 Theorem 9 Phase-2a/2b 分离
文件: docs/06_manuscript/v5_full_manuscript_part1.md
修改: 明确分离理论(Phase-2b)和实验(Phase-2a)

### 3.2 Structural ceiling 重新框架
文件: docs/06_manuscript/v5_full_manuscript_part3.md
修改: 说明是 listing-model 产物

### 3.3 DAG 编译器讨论
文件: docs/06_manuscript/ (新章节)
修改: 添加 LBL/WCL vs DAG 比较

### 3.4 Theorem 2d 证明修复
文件: docs/01_theory/thm2_insertion_proof.md
修改: 限制 invariant 或证明安全性

### 3.5 Qiskit pass isolation 扩展
文件: experiments/ (新实验或扩展)
修改: 覆盖全部 15 族

## Phase 4: 代码质量

### 4.1 修复所有 HIGH 代码问题
- base.py _fitness 修复
- _gates_commute 扩展
- ceiling_aware.py 修复
- make_uccsd_ansatz 重命名
- E15 硬编码 seed
- E18 T-count 存储
- E19 死代码清理
- E11 fidelity 回退
- E12 coupling map
- E13 负 gap 处理
- E14 metadata
- E15 QASM round-trip
- E16 Phase-1-only 基线
- E20 自定义优化器
- compute_new_summary.py 数据伪造
- phase5_optimize_or_skip.py 样本内评估

### 4.2 清理死代码
- _apply_random_single_qubit
- circuit_sha256 重复
- 调试产物

### 4.3 CI 修复
- 使用 conda 环境
- 添加 test_commutation_bug_reproduction.py
- 添加 type checking
- 扩展 linting 范围

### 4.4 添加缺失测试
- random_local_search.py
- simulated_annealing.py
- structural_ceiling.py
- 实验运行器
