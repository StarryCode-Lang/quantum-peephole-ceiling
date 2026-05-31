# 全面数据验证报告
生成时间: 2026-05-30

---

## 一、实验原始数据完整性

| 实验 | 主原始文件 | 行数 | 数据结构 | 状态 |
|------|-----------|------|---------|------|
| E1 | exp1_phase_transition_20260530_095003.csv | 5,000 | 50 depths × 100 trials, n=5 | ✅ OK |
| E1(熵) | exp1_entropy_vs_depth.csv | 6,300 | 6 n × 35 depths × 30 trials | ✅ OK |
| E2(密度) | exp2_entanglement_density_20260530_112304.csv | 1,260 | 21 densities × 2 opt × 30 trials | ✅ OK |
| E2(密度扩展) | exp2_entanglement_density_20260530_121027.csv | 4,200 | 21 densities × 2 opt × 100 trials | ✅ OK |
| E2(比例) | exp2_ratio_sweep.csv | 1,890 | ratio sweep数据 | ✅ OK |
| E3 | exp3_scaling_20260530_100830.csv | 1,138,335 | 完整数据集(8n×多depth×1500/n) | ✅ OK |
| E3(子集) | exp3_scaling.csv | 8,520 | 子集(8n×35d×30) | ✅ OK |
| E4 | exp4_algorithm_comparison_20260530_120454.csv | 400 | 4 optimizers × 100 trials | ✅ OK |
| E5 | exp5_landscape_20260530_102554.csv | 6,000 | 10 circuits × 100 samples × 6 depths | ✅ OK |

---

## 二、处理结果文件完整性

### JSON 文件

| 文件 | 大小 | 内容 | 状态 |
|------|------|------|------|
| e1_e3_analysis_results.json | 7,163 B | E1/E3完整分析(拟合+Bootstrap+FSS) | ✅ OK |
| e2_e4_analysis_results.json | 9,184 B | E2/E4完整分析(相关+Wilcoxon+Bootstrap) | ✅ OK |
| e1_e3_step1_results.json | 2,915 B | E1/E3 sigmoid fits + 统计摘要 | ✅ OK |
| comprehensive_analysis.json | 1,671 B | 旧版综合分析(含E5/E6) | ✅ OK (旧版) |

### CSV 文件

| 文件 | 大小 | 内容 | 状态 |
|------|------|------|------|
| e1_phase_transition_summary.csv | 2,624 B | 50 depths × 5列 | ✅ OK |
| e2_density_sweep_summary.csv | 4,643 B | 21 densities × 2 opt × 9列 | ✅ OK |
| e2_density_overall_stats.csv | 1,663 B | 21 densities × 6列 | ✅ OK |
| e3_n_scaling_summary.csv | 802 B | 8 n × 7列 | ✅ OK |
| e3_nd_scaling_summary.csv | 12,532 B | 241行 n×depth详细 | ✅ OK |
| e3_scaling_summary.csv | 24,606 B | 241行完整统计 | ✅ OK |
| e4_optimizer_comparison_summary.csv | 666 B | 4 optimizers × 9列 | ✅ OK |
| fss_results.csv | 315 B | E1 FSS(1行) | ⚠️ 可疑(R²=-0.008) |
| sigmoid_fit_results.csv | 2,340 B | E3 per-n sigmoid(8行) | ⚠️ 全部R²为负 |
| combined_aggregated_data.csv | 15,104 B | 290行聚合数据 | ✅ OK |

---

## 三、图表完整性

### figures/final/ (发表级)

| 图表 | 大小 | 格式 | 对应实验 | 状态 |
|------|------|------|---------|------|
| fig1_entropy_vs_depth.png | 321 KB | PNG | E1 | ✅ OK |
| fig1_phase_transition.png | 325 KB | PNG | E1 | ✅ OK |
| fig1_phase_transition.pdf | 48 KB | PDF | E1 | ✅ OK |
| fig2_fss.png | 435 KB | PNG | E3 FSS | ✅ OK |
| fig2_fss.pdf | 42 KB | PDF | E3 FSS | ✅ OK |
| fig2_ratio_sweep.png | 72 KB | PNG | E2(旧) | ✅ OK |
| fig3_density_sweep.png | 301 KB | PNG | E2 density | ✅ OK |
| fig3_scaling.png | 53 KB | PNG | E3(旧) | ✅ OK |
| fig4_algorithm_comparison.png | 207 KB | PNG | E4 | ✅ OK |
| fig4_optimization.png | 147 KB | PNG | E4(旧) | ✅ OK |
| fig5_landscape.png | 512 KB | PNG | E5 landscape | ✅ OK (已添加到final) |
| fig5_phase_diagram.png | 45 KB | PNG | E5(旧版) | ⚠️ 旧版/替代 |

### 不足:
- fig3 和 fig4 各有两个版本(旧+新), 需明确使用哪个作为发表版
- fig3_scaling.png 和 fig4_optimization.png 来自01:01(旧), 缺少PDF版本
- fig3_density_sweep.png 和 fig4_algorithm_comparison.png 来自11:27(新), 缺少PDF版本

---

## 四、关键参数交叉验证

### E1: 指数衰减拟合 P(d) = 0.297·exp(-d/19)

| 参数 | JSON值 | 预期值 | 差异 | 状态 |
|------|--------|--------|------|------|
| P0 | 0.297354 | 0.297 | 0.0004 | ✅ 匹配 |
| d0 | 18.98 | 19 | 0.02 | ✅ 匹配 |
| R² | 0.8563 | 0.86 | 0.004 | ✅ 匹配 |
| P0_err | 0.019 | — | — | ✅ 合理 |
| d0_err | 3.99 | — | — | ✅ 合理 |
| P_bg | 2.80e-20 | — | ~0 | ✅ 背景趋零 |

**Bootstrap CI (E1):**
- success_rate: mean=0.1005, CI=[0.0922, 0.1090] ✅
- mean_reduction: mean=0.140203, CI=[0.138391, 0.142067] ✅
- CSV↔JSON一致性: 
  - CSV avg success_rate = 0.1004 vs bootstrap mean = 0.1005 ✅ (差0.0001)
  - CSV avg reduction = 0.140207 vs bootstrap mean = 0.140203 ✅ (差0.000004)
  - Step1 mean_reduction = 0.140207 vs bootstrap = 0.140203 ✅ (差0.000004)

### E2: Density sweep

| 参数 | JSON值 | 预期值 | 差异 | 状态 |
|------|--------|--------|------|------|
| GREEDY Pearson r | 0.962185 | 0.962 | 0.0002 | ✅ 匹配 |
| SA Pearson r | 0.345838 | 0.346 | 0.0002 | ✅ 匹配 |
| GREEDY Spearman | 0.966302 | — | — | ✅ |
| SA Spearman | 0.355305 | — | — | ✅ |

**Bootstrap CI (E2):**
- GREEDY reduction: mean=0.3050, CI=[0.2893, 0.3208] ✅
- SA reduction: mean=0.0147, CI=[0.0098, 0.0201] ✅
- CSV↔JSON: GREEDY avg=0.3050 vs bootstrap=0.3050 ✅ (完全一致)
- CSV↔JSON: SA avg=0.014683 vs bootstrap=0.014683 ✅ (完全一致)
- 原始↔JSON: 原始数据(112304版本)GREEDY=0.3050 vs bootstrap=0.3050 ✅

**注意:** 最新原始数据(121027)GREEDY mean=0.3082, 与bootstrap(0.3050)略有差异, 
因为bootstrap基于早期30-trials版本, 最新数据为100-trials版本。

### E3: Power law reduction(n) = 0.083·n^0.28

| 参数 | JSON值 | 预期值 | 差异 | 状态 |
|------|--------|--------|------|------|
| a | 0.082829 | 0.083 | 0.0002 | ✅ 匹配 |
| b | 0.281072 | 0.28 | 0.0011 | ✅ 匹配 |
| c | 8.88e-17 | ~0 | — | ✅ 基本为零 |
| R² | 0.916732 | 0.92 | 0.0033 | ✅ 匹配 |

**Bootstrap CI (E3 per-n):**
- n=3-10 全部有 success_rate 和 mean_reduction 的 CI ✅
- CSV↔JSON per-n 一致性:
  - 所有8个n的差异 < 0.00009 ✅ (完全一致)

**⚠️ 参数不确定性警告:**
- a_err=0.345 >> a=0.083 (相对误差 415%) ⚠️ 严重
- b_err=0.785 >> b=0.281 (相对误差 280%) ⚠️ 严重
- Power law 参数缺乏 Bootstrap CI ⚠️ 缺失

### E4: 4-optimizer comparison

| 指标 | GREEDY | RANDOM_LOCAL | SIMULATED_ANNEALING | GENETIC_ALGORITHM |
|------|--------|-------------|--------------------|--------------------|
| mean_reduction | 0.1436 | 0.1016 | 0.0020 | 0.0100 |
| success_rate | 0.20 | 0.04 | 0.00 | 0.00 |
| mean_fidelity | 1.000 | 0.9967 | 0.9999 | 0.9996 |

**Wilcoxon tests:** 18对比较, 全部显著(p<0.05) ✅
**Bootstrap CI (E4):** 4 optimizers × 4 metrics (reduction/fidelity/runtime/success) 全部有CI ✅
**CSV↔JSON:** 4 optimizers reduction 完全一致(差=0.000000) ✅

### E5: Landscape analysis

| 区域 | ruggedness | local_minima | 趋势 |
|------|-----------|-------------|------|
| Pre-critical | 0.01082 | 100.6 | — |
| Critical | 0.00512 | 132.2 | 中间 |
| Post-critical | 0.00434 | 147.2 | — |

- Ruggedness 递减趋势 ✅ (0.01082 > 0.00512 > 0.00434)
- Local minima 递增趋势 ✅ (100.6 < 132.2 < 147.2)

---

## 五、问题清单

### 🔴 严重问题 (数据质量)

1. **E1/E3 Sigmoid fits 全部失败**
   - E1 sigmoid: R² = -0.000006 (拟合失败)
   - E3 per-n sigmoid: 全部 R² 为负值 (从 -0.000006 到 -0.4524)
   - d_c 参数接近零且误差巨大(38百万级)
   - **影响**: Phase transition 的 sigmoid 模型不适用, 应改用 exp_decay 模型

2. **E3 FSS (Finite-Size Scaling) 不显著**
   - R² = 0.085 (极低)
   - p_value = 0.525 (不显著)
   - b_err = 0.423 >> b = -0.289 (不确定性大)
   - **影响**: 无法可靠提取 critical exponent ν

3. **E3 Power law 参数不确定性极高**
   - a_err/a = 415%, b_err/b = 280%
   - 缺乏 power law 参数的 Bootstrap CI
   - **影响**: 拟合公式 reduction(n)=0.083·n^0.28 的参数不可靠
   - **建议**: 增加 power law 参数的 Bootstrap CI 或使用更稳健的拟合方法

### 🟡 中等问题

4. **E2 GREEDY fidelity correlation 为 NaN**
   - GREEDY fidelity 恒为 1.0, 导致相关系数无法计算
   - **影响**: 论文中应注明此情况而非报告 NaN

5. **E2 Bootstrap 数据来源不一致**
   - Bootstrap 基于30-trials版本(112304)
   - 最新原始数据为100-trials版本(121027)
   - **影响**: 如使用最新数据重新分析, Bootstrap CI 会变化

6. **E3 原始数据来源不明确**
   - Processed total_trials=12000, 但 exp3_scaling.csv 仅8,520行
   - 完整数据在 exp3_scaling_20260530_100830.csv (1.1M行)
   - **影响**: 需确认处理结果基于哪个原始数据集

### 🟢 轻微问题

7. **图表版本混乱**
   - fig3 和 fig4 各有两个版本(旧+新)
   - fig5 有 fig5_landscape.png(新,512KB) 和 fig5_phase_diagram.png(旧,45KB)
   - **影响**: 需明确发表使用哪个版本, 建议为新版本统一生成PDF

8. **fig3 和 fig4 新版缺少 PDF 格式**
   - fig3_density_sweep.png 和 fig4_algorithm_comparison.png 缺 PDF
   - **影响**: 发表级图表应同时有 PNG 和 PDF

9. **figures/ 父目录有未分类文件**
   - fig5_landscape.png, fig6_entropy_comparison.png 在父目录而非 final/
   - **影响**: 需整理到 final/ 目录

---

## 六、总结

| 维度 | 状态 |
|------|------|
| 原始数据文件 | ✅ 5个实验全部有完整原始CSV |
| 处理结果JSON | ✅ 关键参数与预期值完全匹配 |
| 处理结果CSV | ✅ 汇总数据完整 |
| Bootstrap CI | ✅ E1/E2/E3/E4 全部有CI (⚠️ E3 power law参数CI缺失) |
| 图表PNG | ✅ 5个实验图表全部存在 |
| 图表PDF | ⚠️ 仅 fig1 和 fig2 有PDF版本 |
| JSON↔CSV一致性 | ✅ 所有交叉验证差异<0.0001 |
| 拟合质量 | ⚠️ sigmoid/FSS失败, power law参数误差大 |
| 原始↔处理一致性 | ⚠️ E2/E3 原始数据版本不一致 |

**整体评估**: 数据和结果文件结构完整, 关键数值参数与预期高度一致, Bootstrap CI 覆盖全面。主要问题集中在拟合质量(sigmoid失败、FSS不显著、power law参数误差大), 需在论文中妥善讨论这些局限。