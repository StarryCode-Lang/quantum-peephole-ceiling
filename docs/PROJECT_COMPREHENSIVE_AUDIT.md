# Q-Research 项目全面审查报告

**项目**: Quantum Circuit Peephole Optimization
**审查日期**: 2026-06-17
**审查标准**: 博士后水准 / 顶会顶刊
**审查范围**: 全部 ~175 个文件

---

## 总体评估

项目有真正的科学价值。但当前状态存在 **5 个致命问题** 和 **14 个严重问题**。

**当前就绪度**: 5.5/10 (顶刊), 7/10 (Quantum)

## 问题总览

| 严重程度 | 数量 |
|----------|------|
| FATAL | 5 |
| CRITICAL | 14 |
| HIGH | 18 |
| MEDIUM | 20 |
| LOW | 10 |

---

## FATAL 致命问题

### F-1. Theorem 9 Phase-2b vs 实验 Phase-2a 不匹配
Theorem 9 需要 Phase-2b template matching，但所有实验使用 Phase-2a commutation。
代码库中没有 template matching 实现。

### F-2. structural ceiling 是 listing-model 产物
45,500 次试验的 0% Phase-1 是 LBL 的构造性结果(Theorem 1(b))，不是电路性质。

### F-3. LBL/WCL 框架与 DAG 编译器脱节
生产编译器使用 DAG 表示，不是顺序 gate listing。

### F-4. Theorem 2d wire-order invariant 对同线 COMMUTATION 不成立
证明自身承认反例但继续假设 invariant 成立。

### F-5. Qiskit pass isolation 仅覆盖 5/15 族
10 个族的机制归因是纯推测。

---

## CRITICAL 严重问题

### C-1. E04 单种子随机优化器评估
SA/GA/RLS 各一个固定种子，排名可能完全随机。

### C-2. E10 Binder cumulant 跨混合族计算
必须按族分组计算。

### C-3. E10 analyze.py or True bug
第 306 行 or True 使过滤器成为 no-op。

### C-4. 重复统计实现 (core.py vs 模块)
core.py 718 行复制所有模块，不同签名和返回类型。模块版本是死代码。

### C-5. 事后功效分析统计谬误
observed power 是 p 值的 1:1 函数，零额外信息。

### C-6. Held-out 验证循环特征泄漏
使用 actual_reduction 作为特征预测 reduction。

### C-7. PROJECT_ROOT 未定义
phase2_threshold_sensitivity/run.py:118 会崩溃。

### C-8. Pearson 相关 NaN 不对齐
generate_figures.py:666 独立 dropna() 导致长度不匹配。

### C-9. success=False 系统性问题
E01: 100%, E04: 100%, E05: 99.98%, E10: 94.8%, E11: 83.8%

### C-10. DATA_CANONICAL.md 引用不存在文件
E01-E05 文件名与实际磁盘文件不匹配。

### C-11. E10 在 manifest 中重复
两个不同 CSV 共享同一 experiment_id。

### C-12. Manifest 源哈希不匹配
release_manifest.json 与实验 metadata.json 哈希不同。

### C-13. E12 零保真度数据
568/568 行 fidelity=NULL。

### C-14. E20 无 CSV 数据
仅 metadata.json，无实验结果。

---

## HIGH 高优先级问题

H-1. requirements.txt vs environment.yml 分歧 (pytket/pytest)
H-2. CI 用 pip，项目设计为 conda
H-3. E15 元数据误导 (Qiskit-only 声称 multi-compiler)
H-4. E17 所有行 reduction=0.0
H-5. base.py _fitness 分母和奖励项问题
H-6. _gates_commute 不完整交换规则
H-7. ceiling_aware.py count_phase2_actions 低计 + 容差不一致
H-8. make_uccsd_ansatz 不是真正的 UCCSD
H-9. E15 硬编码 transpiler seed
H-10. E18 T-count 数据未存储
H-11. E21 硬编码 fidelity=1.0
H-12. E19 死代码 + 任意阈值
H-13. E17 混杂测量 (optimization_level=1)
H-14. E11 fidelity 回退逻辑
H-15. E12 固定 coupling map
H-16. E13 负 ceiling_gap 未处理
H-17. E14 build_optimizers() 无参数
H-18. E15 QASM round-trip 弃用
H-19. E16 缺少 Phase-1-only 基线
H-20. E20 缺少自定义优化器
H-21. compute_new_summary.py 数据伪造 (fidelity=1.0)
H-22. phase5_optimize_or_skip.py 样本内评估

---

## MEDIUM 中等问题

M-1. 硬编码时间戳 (phase5 脚本)
M-2. std 代替 SEM (qiskit_pass_analysis.py)
M-3. log scale 零值 (generate_figures.py Fig 5)
M-4. 比较脚本缺少统计检验
M-5. 相关分析无多重比较校正
M-6. 因果分析无因果框架
M-7. 死代码和调试产物
M-8. 函数内 import
M-9. convert_png_to_pdf.py 栅格嵌入 PDF
M-10. COLUMN_MAP 未使用 + KeyError (phase5_feature_extraction.py)
M-11. 手稿过长且重复
M-12. .docx 交付物与 markdown 不同步
M-13. E03 fidelity=0.0 行未标记
M-14. E05 纠缠熵接近零
M-15. E18 数据不一致 (decompose_error 行)
M-16. ISOLATION 数据 50% 缺失 fidelity
M-17. Dockerfile 无法验证数据
M-18. 无锁文件
M-19. 缺少消融研究数据
M-20. E10 run_expanded.py n_qubits 对 BV 错误
M-21. E10 run_expanded.py QAOA/VQE 硬编码角度
M-22. E15 QASM round-trip 非酉保持
M-23. E17 make_heavy_hex 非真正 heavy-hex
M-24. E18 缺少 Clifford 特定优化器比较
M-25. E19 缺少 WCL 后 Phase 2
M-26. E20 _extract_n_param 脆弱解析
M-27. E20 _generate_filtered_suite 浪费计算

---

## LOW 低优先级

L-1. 死代码 _apply_random_single_qubit
L-2. circuit_sha256 重复
L-3. simulated_annealing.py 缺少 Optional import
L-4. iteration 变量遮蔽
L-5. 各种小代码质量问题

---

## 修复计划

### Phase 1: 立即修复 (CRITICAL bugs)
1. 修复 E10 analyze.py or True bug 和 Binder cumulant
2. 修复 PROJECT_ROOT 未定义
3. 修复 Pearson NaN 不对齐
4. 修复 success=False 谓词
5. 更新 DATA_CANONICAL.md
6. 修复 manifest 重复和哈希
7. 删除 core.py 重复统计
8. 修复事后功效分析
9. 修复特征泄漏

### Phase 2: 实验修复 (HIGH)
1. 重新运行 E04 多种子
2. 重新运行 E12 带保真度
3. 运行 E20 生成数据
4. 运行 E19 WCL 实验
5. 修复 E17 零缩减
6. 修复 E21 保真度计算
7. 同步 requirements.txt 和 environment.yml

### Phase 3: 手稿修复 (FATAL)
1. 解决 Theorem 9 Phase-2a/2b 不匹配
2. 重新框架 structural ceiling 为 listing-model 产物
3. 添加 DAG 编译器讨论
4. 修复 Theorem 2d 证明
5. 完成 Qiskit pass isolation 全部 15 族

### Phase 4: 代码质量 (MEDIUM/LOW)
1. 修复所有 HIGH 代码问题
2. 清理死代码
3. 添加缺失测试
4. 统一 CI 环境
