# Q-research 项目结构 v2.1.0

> 最后更新：2026-05-30

## 项目概述

本项目研究量子电路优化中的纠缠密度、相位转变和缩放行为。包含5个核心实验的完整数据、分析脚本和发表级图表。

---

## 目录结构

```
Q-research/
├── README.md                          # 项目说明文档
├── PROJECT_STRUCTURE.md               # 本文档
│
├── src/                               # 核心源代码模块
│   ├── circuits/                      # 电路生成模块
│   │   ├── __init__.py                # 导出 generator_v2
│   │   └── generator_v2.py            # v2.1.0 电路生成器
│   ├── optimisation/                  # 优化算法模块
│   │   ├── __init__.py                # 导出 optimizers_v2
│   │   └── optimizers_v2.py           # v2.1.0 优化器（4种算法）
│   └── analysis/                      # 分析工具模块
│       ├── __init__.py                # 导出 analysis_v2
│       └── analysis_v2.py             # v2.1.0 分析工具
│
├── experiments/                       # 实验运行脚本
│   ├── run_all_experiments_v3.py      # 生产级实验运行器（核心）
│   ├── run_e1.py                      # E1: 相位转变检测
│   ├── run_e2.py                      # E2: 纠缠密度研究
│   ├── run_e3.py                      # E3: 缩放行为
│   ├── run_e4.py                      # E4: 算法比较
│   └── run_e5.py                      # E5: 地貌表征
│
├── scripts/                           # 分析和图表生成脚本
│   ├── phase_transition_analysis.py   # E1+E3 指数衰减/功率律分析
│   ├── e2_e4_analysis.py              # E2+E4 纠缠密度分析
│   ├── e5_landscape_analysis.py       # E5 地貌分析
│   ├── gen_fig1.py                    # 生成 Fig.1（3面板）
│   ├── gen_fig2.py                    # 生成 Fig.2（3面板）
│   ├── gen_pdfs.py                    # PNG转PDF工具
│   ├── generate_figures.py            # 综合图表生成器
│   └── reproducibility/               # 可重复性工具包
│       ├── Dockerfile
│       ├── environment.yml
│       ├── requirements.txt
│       ├── setup_reproducibility.py
│       └── README_REPRODUCIBILITY.md
│
├── data/                              # 实验数据
│   ├── raw/                           # 原始实验数据（5个CSV + 1个JSON）
│   │   ├── exp1_phase_transition_20260530_095003.csv
│   │   ├── exp2_entanglement_density_20260530_112304.csv
│   │   ├── exp3_scaling_20260530_100830.csv
│   │   ├── exp4_algorithm_comparison_20260530_111458.csv
│   │   ├── exp5_landscape_20260530_102615.csv
│   │   └── page_values.json
│   └── processed/                     # 处理后的数据（10个文件）
│       ├── e1_e3_analysis_results.json
│       ├── e2_e4_analysis_results.json
│       ├── e5_landscape_analysis_results.json
│       ├── e1_phase_transition_summary.csv
│       ├── e2_density_overall_stats.csv
│       ├── e2_density_sweep_summary.csv
│       ├── e3_n_scaling_summary.csv
│       ├── e3_nd_scaling_summary.csv
│       ├── e4_optimizer_comparison_summary.csv
│       └── fss_results.csv
│
├── figures/                           # 发表级图表
│   └── final/                         # 最终图表（5图×PNG+PDF）
│       ├── fig1_phase_transition.png/pdf   # E1: 指数衰减+reduction+熵阈值
│       ├── fig2_fss.png/pdf                # E3: 功率律+per-n曲线+Bootstrap CI
│       ├── fig3_density_sweep.png/pdf      # E2: 纠缠密度扫描
│       ├── fig4_algorithm_comparison.png/pdf # E4: 优化器比较
│       └── fig5_landscape.png/pdf          # E5: 地貌表征
│
├── docs/                              # 项目文档
│   ├── 00_research_outline.md         # 研究大纲
│   ├── 01_quick_reference.md          # 快速参考
│   ├── 02_execution_checklist.md      # 执行清单
│   ├── EXPERIMENTAL_PROTOCOL.md       # 实验协议
│   └── comprehensive_analysis_report_v2.md  # 综合分析报告（最终版）
│
├── reports/                           # 技术报告
│   └── VERIFICATION_REPORT.md         # 数据验证报告
│
├── logs/                              # 实验日志（空）
├── literature/                        # 参考文献
├── theory/                            # 理论推导
├── paper/                             # 论文草稿
│
└── archive/                           # 归档内容（旧版本/调试/一次性）
    ├── old_code/                      # v1核心代码（6个）
    ├── old_scripts/                   # 旧版分析/图表脚本（11个）
    ├── old_data/                      # 旧版实验数据（50+个）
    ├── old_figures/                   # 旧版图表（12个）
    ├── old_docs/                      # 旧版文档（5个）
    ├── debug_scripts/                 # 调试脚本（6个）
    └── one_shot/                      # 一次性运行脚本（4个）
```

---

## 核心模块说明

### src/circuits/generator_v2.py
- **功能**：生成随机量子电路（CNOT + 单量子比特门）
- **核心函数**：`generate_random_circuit(n_qubits, depth, seed)`
- **输出**：Qiskit QuantumCircuit 对象
- **性能**：O(n × d) 时间复杂度，内存效率优化

### src/optimisation/optimizers_v2.py
- **功能**：4种优化算法实现
- **算法**：
  - `GREEDY`: 贪心搜索（最快，0.00s）
  - `RANDOM_LOCAL_SEARCH`: 随机局部搜索（7.88s）
  - `SIMULATED_ANNEALING`: 模拟退火（1.31s）
  - `GENETIC_ALGORITHM`: 遗传算法（1.75s）
- **接口**：`optimize(circuit, algorithm, seed)` → 优化后电路

### src/analysis/analysis_v2.py
- **功能**：电路分析和统计工具
- **核心函数**：
  - `analyze_circuit(circuit)`: 分析门计数、两量子比特门比例
  - `compute_entanglement_entropy(circuit)`: 计算纠缠熵
  - `statistical_summary(results)`: 统计汇总
- **输出**：字典格式的分析结果

---

## 数据文件说明

### data/raw/ — 原始实验数据

| 文件名 | 大小 | 行数 | 内容 |
|--------|------|------|------|
| exp1_phase_transition_*.csv | 481KB | 5000 | E1: n=5, d=1-50, 100trials |
| exp2_entanglement_density_*.csv | 159KB | 1260 | E2: n=6, d=20, density=0-1 |
| exp3_scaling_*.csv | 1112KB | 12000 | E3: n=3-10, d=1-30, 50trials |
| exp4_algorithm_comparison_*.csv | 49KB | 400 | E4: 4优化器×100trials |
| exp5_landscape_*.csv | 414KB | 6000 | E5: n=5, d=3-20 |
| page_values.json | 小 | - | 理论Page值参考 |

### data/processed/ — 处理后的数据

| 文件名 | 内容 |
|--------|------|
| e1_e3_analysis_results.json | E1+E3分析结果（指数衰减+功率律拟合） |
| e2_e4_analysis_results.json | E2+E4分析结果 |
| e5_landscape_analysis_results.json | E5地貌分析结果 |
| e1_phase_transition_summary.csv | E1按深度汇总 |
| e2_density_*.csv | E2纠缠密度统计 |
| e3_*_scaling_summary.csv | E3按n和d汇总 |
| e4_optimizer_comparison_summary.csv | E4优化器性能比较 |
| fss_results.csv | 有限尺寸标度分析结果 |

---

## 脚本-数据依赖关系

```
gen_fig1.py ─────┬─→ data/raw/exp1_phase_transition_*.csv
                 └─→ data/raw/exp3_scaling_*.csv

gen_fig2.py ─────┬─→ data/raw/exp1_phase_transition_*.csv
                 └─→ data/raw/exp3_scaling_*.csv

phase_transition_analysis.py ─→ data/raw/exp1_phase_transition_*.csv
                              └→ data/raw/exp3_scaling_*.csv

e2_e4_analysis.py ─┬─→ data/raw/exp2_entanglement_density_*.csv
                   └─→ data/raw/exp4_algorithm_comparison_*.csv

e5_landscape_analysis.py ─→ data/raw/exp5_landscape_*.csv
```

---

## 核心科学发现

### E1: 相位转变
- **模型**：指数衰减 P(d) = P₀ · exp(-d/d₀)
- **参数**：P₀ = 0.297 ± 0.015, d₀ = 19.0 ± 4.0
- **拟合质量**：R² = 0.86

### E3: 缩放行为
- **模型**：功率律 reduction(n) = a · n^b
- **参数**：a = 0.0828 [0.0786, 0.0873], b = 0.2813 [0.2542, 0.3075]
- **拟合质量**：R² = 0.92

### E4: 算法比较
- **成功率**：6.00%（整体）
- **运行时间**：GREEDY(0.00s) < SA(1.31s) < GA(1.75s) < RLS(7.88s)

---

## 快速开始

### 运行单个实验
```bash
cd D:/Desktop/Q-research
python experiments/run_e1.py
```

### 生成所有图表
```bash
python scripts/gen_fig1.py
python scripts/gen_fig2.py
python scripts/gen_pdfs.py
```

### 重新运行分析
```bash
python scripts/phase_transition_analysis.py
python scripts/e2_e4_analysis.py
python scripts/e5_landscape_analysis.py
```

---

## 清理日志

**清理前**：73个Python文件 + 25个原始CSV + 18个处理数据 + 大量旧图表

**清理后**：
- **保留**：17个Python脚本（核心+分析+图表）
- **归档**：50+个旧版本/临时文件（移至 archive/）
- **数据**：6个原始CSV + 10个处理文件
- **图表**：5图 × (PNG + PDF)

**归档位置**：
- `archive/old_code/` — v1核心代码
- `archive/old_scripts/` — 旧版分析脚本
- `archive/old_data/` — 旧版实验数据
- `archive/old_figures/` — 旧版图表
- `archive/old_docs/` — 旧版文档
- `archive/debug_scripts/` — 调试脚本
- `archive/one_shot/` — 一次性运行脚本

---

## 版本历史

| 版本 | 日期 | 变更 |
|------|------|------|
| v2.1.0 | 2026-05-30 | 项目结构重组，清理完成，Bootstrap CI添加 |
| v2.0.0 | 2026-05-29 | 核心模块v2重写，sigmoid→指数衰减模型 |
| v1.0.0 | 2026-05-28 | 初始实验运行（归档于 archive/old_code/） |
