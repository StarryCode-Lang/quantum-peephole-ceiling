可以继续检查的指标非常多，而且不存在一个对所有量子科研项目都封闭完备的“指标全集”——指标必须由你的核心主张、优化目标、计算模型和目标期刊反向决定。下面给你的是一套适用于“量子电路表示敏感性、局部优化、编译器比较、结构 ceiling 分析”的尽可能完整的顶级科研审计框架。

评价标准不是“代码能运行、结果显著、图好看”，而是：

> 每一个重要结论是否可证伪、是否有直接证据、是否经受替代解释、是否在公平条件下优于强基线、是否能被独立复现，以及它是否真正改变领域已有认知。

PRX Quantum要求达到 exceptional advance、connection、capability 或 insight；npj Quantum Information要求显著推进并且结论有强而技术可靠的证据。[PRX Quantum 标准](https://journals.aps.org/prxquantum/about)、[npj Quantum Information 审稿标准](https://www.nature.com/npjqi/for-authors-and-referees/guideforreviewers)

# 一、最重要的总仪表盘

这些是我建议以后每次审计都首先查看的 20 个总指标。

| 指标 | 顶级标准 |
|---|---|
| 核心主张证据覆盖率 | 100%；每项核心主张都有直接数据、定理或反例证据 |
| 主张越界率 | 0；经验结果不得升级成算法无关或普适结论 |
| 语义有效率 | 所有被计为“成功”的输出必须通过约定等价标准 |
| 未知有效性比例 | 单独报告；不得把 unavailable/unchecked 当成 valid |
| ITT 完整性 | timeout、error、invalid 全部进入分母 |
| 输入配对完整率 | 比较工具必须使用完全相同且哈希一致的输入 |
| 未记录排除数量 | 0 |
| 未记录协议偏离数量 | 0 |
| 主要效应及区间 | 效应量、95% CI、科学最小重要差异同时报告 |
| 外层独立单位数量 | 以家族、问题类、硬件或独立数据源计算，不能用重复 seed 冒充 |
| 最坏家族表现 | 必须报告，而不仅是总体均值 |
| LOFO/LOCO 稳定性 | 去掉任一家族后结论方向和数量级是否稳定 |
| 跨家族泛化 | 使用真正未见过的 generator/family 和嵌套区间 |
| Pareto 前沿 | 质量、时间、内存、失败率、保真度联合比较 |
| 规模规律 | 时间、内存、质量随 qubit/gate/depth 增长的经验指数及区间 |
| 强基线覆盖 | 学术 SOTA、工业编译器、独立工件、简单基线均包含 |
| 硬件相关性 | native 2Q count/depth、duration、noise-aware fidelity、success probability |
| 可复现实验率 | 从干净环境一条命令重建主要表图 |
| 独立复现率 | 至少一次由非开发者或新机器完成冷启动复现 |
| 新颖性碰撞风险 | 最近文献中是否已有同问题、同表示、同诊断、同实验设计 |

# 二、问题定义与科学主张

1. 研究问题是否能用一句可证伪的话表达？
2. 所谓“表示敏感性”具体是 gate listing、DAG、ZX 图、phase polynomial，还是搜索动作编码？
3. 研究对象是算法、搜索过程、规则库还是输入表示？
4. “ceiling”是规则集条件下、预算条件下、算法条件下，还是全算法意义上的？
5. “优化能力”指找到更短电路、找到任何改进、达到局部最优，还是接近已知全局最优？
6. 每个术语是否有数学定义和可执行判定器？
7. 结论的总体是什么：所有量子线路、某基门集，还是所采样的家族？
8. 主要结局是否在观察数据前冻结？
9. 科学最小重要差异是否预先定义？
10. 什么结果会推翻主要假设？
11. 什么结果只会缩小主张而不会完全推翻？
12. 是否区分探索性、支持性和确认性问题？
13. 是否存在结果出来后改变 RQ、阈值或评价指标的情况？
14. 是否记录了每次主张缩窄的原因？
15. 是否有最强的竞争性解释？
16. 观察到的差异是否可能只来自基门转换？
17. 是否可能只是某个 compiler 默认配置的特例？
18. 是否可能只是时间预算差异？
19. 是否可能只是 circuit family composition 造成的 Simpson 悖论？
20. 是否可能只是搜索空间大小变化，而不是“结构”变化？
21. “显著”是否同时具有统计意义和科学意义？
22. 如果效应只有 0.1%，是否仍有领域价值？
23. 如果平均效应为正但某些家族灾难性退化，结论如何变化？
24. 项目究竟发现了规律、构建了方法，还是主要发现了评价陷阱？
25. 这个结果改变了领域中哪一个具体判断？

# 三、创新性与文献完整性

1. 是否检索了相同任务，而不只是相同关键词？
2. 是否检索了 compiler、synthesis、peephole、rewrite、equivalence、superoptimization、routing、representation learning、ZX-calculus 等不同术语体系？
3. 是否逐篇核对最接近工作的输入表示？
4. 是否逐篇核对它们的优化规则和动作空间？
5. 是否比较了目标函数，而不只是方法名称？
6. 是否区分 gate count、T-count、2Q count、depth 和 hardware fidelity？
7. 是否已有论文研究 representation-changing edits？
8. 是否已有 relaxed/non-contiguous peephole？
9. 是否已有局部最优性或 cut-and-meld 证明？
10. 是否已有 rewrite discovery、e-graph、RL、GNN 或神经搜索？
11. 是否已有跨家族泛化实验？
12. 是否已有 listing/order sensitivity 的直接实验？
13. 是否已有相同 counterexample？
14. “首次”主张是否有可复查的检索协议？
15. 是否记录检索日期、数据库、检索式和排除理由？
16. 是否阅读论文正文而不是只看摘要？
17. 是否检查附录、代码和 artifact？
18. 是否检查 arXiv 最新版本和正式发表版本差异？
19. 是否查看引用该工作的后续论文？
20. 是否查看被该工作引用的更早来源？
21. 负面引用和复现实验是否纳入？
22. 是否存在同一方法换名字的重复发现？
23. 新颖性来自问题、理论、方法、数据、实验设计还是证据强度？
24. 如果去掉“普适”“首次”“硬上界”等词，贡献是否仍成立？
25. 是否能写出逐特征 novelty matrix？
26. 与最接近工作相比，至少有一个无法被“工程实现不同”解释的增量吗？
27. 该增量是否足以形成独立论文，而不只是 ablation？
28. 最新 6–12 个月是否重新搜索？
29. 是否包含 Q-PreSyn、Quartz、Quarl、Quanto、GUOQ、OAC/cut-and-meld 等直接比较对象？
30. 是否有匿名同行进行一次 novelty red-team？

# 四、理论与形式化

1. 每个 theorem 的量词是否明确？
2. 是对所有线路、某生成器，还是存在性构造？
3. 门集是否固定？
4. 是否允许 ancilla、measurement、reset 和 classical control？
5. 是否忽略全局相位？
6. 是否允许重排可交换门？
7. 局部窗口大小是否固定？
8. 算法预算是否属于定理前提？
9. 所谓最优是局部最优、规则最优还是全局最优？
10. 上界或下界是否依赖输入 listing？
11. 必要条件是否被误写成充分条件？
12. 经验相关性是否被误写成定律？
13. 是否存在极小反例搜索？
14. 是否对 n=1、2、空线路和退化线路检查？
15. 是否对不连续窗口检查？
16. 是否检查规则冲突和非合流性？
17. 是否证明算法终止？
18. 是否证明每步语义保持？
19. 是否证明代价单调，还是允许先扩张后缩减？
20. 是否存在循环 rewrite？
21. 复杂度结论是 worst-case、average-case 还是 observed scaling？
22. 是否把搜索问题与验证问题的复杂性混淆？
23. QMA-hardness/NP-hardness 是否对应准确的决策问题？
24. reduction 是否完整、双向且 polynomial？
25. 引用的复杂性结果是否真的适用于当前门集和误差模型？
26. 理论指标能否由代码直接计算？
27. 定理前提能否由测试自动验证？
28. 每项理论结论是否有至少一个正例和反例测试？
29. 是否用 property-based testing 搜索破坏定理的线路？
30. 定理在参数化门、部分初始化和 observational equivalence 下是否仍成立？

参数化电路需要专门的等价合同，因为有限参数实例测试不能证明参数化等价。[参数化量子线路等价检查](https://arxiv.org/abs/2404.18456)

# 五、基准数据与采样设计

1. benchmark 是否覆盖随机、结构化、算法型、变分型和真实来源线路？
2. 是否包含 QFT、Grover、BV、QAOA、VQE、Hamiltonian simulation、arithmetic、oracle、QEC 子电路？
3. 是否覆盖 Clifford、Clifford+T、任意旋转和多控制门？
4. qubit 数范围是否足够宽？
5. gate count 和 depth 是否独立变化？
6. 是否覆盖稀疏和稠密交互图？
7. 是否覆盖线性、网格、重六边形、全连接等拓扑？
8. 是否覆盖不同 gate diversity？
9. family 是否由真正不同的生成机制定义？
10. 同一家族的不同 seed 是否被错误地当成独立 family？
11. 是否存在大量重复或同构线路？
12. 是否计算电路哈希和规范化哈希？
13. train、validation、held-out 是否在 family 层隔离？
14. benchmark 是否被调参过程间接看过？
15. 是否有数据泄漏到特征标准化或缺失值填充？
16. 是否有 benchmark selection bias？
17. 是否只选择自定义方法擅长的家族？
18. 是否保留难例、失败例和零收益例？
19. 是否有 known-optimum 或 known-near-optimum 实例？
20. 是否包含 identity/mirror circuits 作为正确性 oracle？
21. 是否包含不可优化的负对照？
22. 是否包含人为插入可约简结构的正对照？
23. 是否包含 adversarial listings？
24. 是否包含相同 unitary 的多种 syntactic representation？
25. 是否包含相同结构但不同参数的线路？
26. 是否包含参数接近数值奇异点的线路？
27. 是否包含边界角度，如 0、π/2、π、2π？
28. 是否与 MQT Bench 之类跨抽象层数据对齐？
29. 是否运行 Benchpress 风格的大型软件压力测试？
30. 每个 family×size 单元是否有足够独立实例？
31. 样本量是否由 MDE/power 决定，而不是方便程度？
32. 是否报告 benchmark 全体和被运行子集的差异？
33. 是否有数据版本、生成器版本、seed 和生成时间？
34. 是否可以从生成器重建每个输入？
35. 是否将真实线路和合成线路分层报告？

MQT Bench强调跨抽象层、广泛 benchmark 与可扩展性；Benchpress则覆盖超过 1,000 项软件任务、多个 SDK、最高数百 qubit 和百万量级双比特门，这说明“小规模精确验证集”和“大规模软件压力集”应同时存在。[MQT Bench](https://quantum-journal.org/papers/q-2023-07-20-1062/)、[Benchpress](https://arxiv.org/abs/2409.08844)

# 六、算法与实现正确性

1. 算法伪代码和实现是否逐步骤一致？
2. 当前解与历史最佳有效解是否分开保存？
3. 无效候选是否可能覆盖有效 incumbent？
4. timeout 前找到的最佳有效解是否保留？
5. exception 是否可能被吞掉并记为成功？
6. 多进程终止时子进程是否全部结束？
7. checkpoint 是否原子写入？
8. resume 是否重复或跳过实例？
9. seed 是否控制所有随机源？
10. NumPy、Python、编译器、外部工具的随机种子是否都冻结？
11. 多线程 BLAS 是否破坏可重复性？
12. 数据顺序是否影响结果？
13. 并行调度是否影响随机序列？
14. 浮点比较是否使用合理公差？
15. 角度规范化是否一致？
16. gate inverse 判定是否处理参数周期？
17. qubit 顺序和 endian 是否一致？
18. QASM 解析/导出是否丢失 phase、parameter 或 register mapping？
19. 自定义 gate 分解前后语义是否一致？
20. barrier、measurement、reset 的处理是否明确？
21. 是否对每条 rewrite 做 unit test？
22. 是否对 rewrite 组合做 property test？
23. 是否进行 differential testing？
24. 是否使用 mutation testing 检查测试是否能抓住错误？
25. 是否对 parser、serializer 做 round-trip test？
26. 是否对 checkpoint/resume 做故障注入？
27. 是否对 timeout、OOM、子进程崩溃做故障注入？
28. 是否检查 resource leak、僵尸进程和临时文件？
29. 是否测试空输入、单门、超大输入和损坏输入？
30. 是否测试所有公开配置组合？
31. 是否有静态类型、lint、compile 和 API drift 检查？
32. 是否记录每个实验调用的真实源码 SHA？
33. 是否能证明运行时加载的代码就是被发布的代码？
34. 是否保存外部可执行文件哈希和动态库版本？
35. 是否有独立实现用于交叉验证关键统计量？

# 七、语义正确性与等价验证

1. 等价定义是 unitary、up-to-global-phase、partial、observational 还是 distributional？
2. 是否正确处理全局相位？
3. 是否允许 ancilla 初始化和释放？
4. 是否处理 measurement 和 classical control？
5. 是否处理部分初始化？
6. 参数化电路是符号验证还是有限点抽样？
7. exact average gate fidelity 的公式是否正确？
8. fidelity 阈值由什么数值误差分析支持？
9. 是否报告阈值附近结果的距离？
10. 是否区分 exact、numerical、sampled、heuristic 和 unavailable？
11. 大 qubit 线路超出精确矩阵预算后怎么办？
12. 是否错误地把结构相似度叫作 fidelity？
13. sampled-state 检查的采样分布是否覆盖完整 Hilbert 空间？
14. 是否有 adversarial unitary 使近似检查误判？
15. 是否使用第二种独立 verifier？
16. 是否用 inverse composition `U†V` 检查 identity？
17. 是否测试 I 与 X、I 与 Z 等已知非等价对？
18. 是否测试只差全局相位的等价对？
19. 是否测试不同 qubit permutation？
20. 是否测试 parameter wrap-around？
21. 输出 QASM 哈希是否在验证后固定？
22. 验证失败能否定位到哪条 transformation？
23. 是否报告每个工具的 invalid rate 及家族分布？
24. 是否把未发出输出、解析失败和非等价分开？
25. 是否对 large-scale circuits 使用符号、决策图、ZX 或 path-sum 验证？
26. 大规模无法验证时，主张是否自动降级？
27. 是否报告 verifier 自身的超时和覆盖边界？
28. verifier 是否接受所有被测工具输出的门集？
29. 转换到 verifier 门集是否本身通过验证？
30. 是否有 verifier-versus-verifier disagreement audit？

# 八、基线选择与公平性

1. 是否包含最简单的 identity/no-op 基线？
2. 是否包含原始线路不优化基线？
3. 是否包含 greedy/local 简单基线？
4. 是否包含主流工业编译器？
5. 是否包含至少两个独立研究工件？
6. 是否遗漏最接近的方法？
7. 遗漏理由是技术不可执行还是结果不利？
8. 是否使用官方版本或 commit？
9. 是否只修改 I/O，而未改变核心算法？
10. 修改是否有 patch 和哈希？
11. 所有工具是否使用同一输入 unitary？
12. 输入 basis 是否对某工具更有利？
13. 是否在共同基门集上评价输出？
14. 是否把工具自身 gate count 与共同 basis gate count 混用？
15. 是否采用相同 topology？
16. 是否采用相同 ancilla allowance？
17. 是否采用相同 approximation tolerance？
18. 是否采用相同超时？
19. 相同 outer timeout 是否意味着相同内部计算预算？
20. 是否同时比较官方默认配置和等预算配置？
21. 是否构建 quality–time Pareto 曲线？
22. 是否构建 quality–memory Pareto 曲线？
23. 预处理和后处理时间是否计入？
24. 启动/JIT/模型加载是否计入？
25. GPU 与 CPU 的资源成本是否可比？
26. 是否记录线程数、核心数、内存和加速器？
27. 是否区分算法失败、artifact 失败和环境失败？
28. 是否报告每个工具的版本敏感性？
29. 工具参数是否在独立 validation set 上选择？
30. 是否避免在正式 test set 上调参？
31. 工具名称是否与真实配置绑定？
32. 是否报告 unavailable 工具，而不是静默删除？
33. 是否使用论文数字冒充本地复现数字？
34. 是否对外部方法给出最有利且合理的配置？
35. 是否邀请外部作者核查运行配置？

# 九、优化质量指标

不能只看 total gate count。至少检查：

### 逻辑电路资源

1. 总门数。
2. 单比特门数。
3. 双比特门数。
4. 多比特门数。
5. CX/CZ/ECR 等原生纠缠门数。
6. 总 depth。
7. 双比特 depth。
8. critical-path duration。
9. circuit width。
10. ancilla 数。
11. measurement/reset 数。
12. gate diversity。
13. interaction graph density。
14. communication/nonlocal operation 数。
15. SWAP 数。
16. routing overhead。
17. basis translation overhead。
18. peak live qubits。
19. classical feed-forward latency。
20. dynamic-circuit 分支代价。

### 容错资源

21. T-count。
22. T-depth。
23. CCZ/Toffoli count。
24. magic-state consumption。
25. magic-state factory 数量。
26. logical qubits。
27. logical depth。
28. spacetime volume。
29. physical qubits。
30. physical runtime。
31. target logical error probability。
32. code distance。
33. distillation rounds。
34. synthesis approximation error。
35. logical failure probability。

T-count/T-depth的重要性来自非 Clifford 资源在许多容错体系中的高成本，但不能把它当成所有硬件架构的唯一成本。[T-count/T-depth 研究](https://arxiv.org/abs/2110.10292)

### 优化结果表达

36. absolute reduction。
37. relative reduction。
38. ITT reduction。
39. valid-only reduction。
40. median reduction。
41. worst-family reduction。
42. lower-tail quantile。
43. improvement probability。
44. regression probability。
45. catastrophic expansion probability。
46. known-optimum gap。
47. approximation ratio。
48. regret。
49. Pareto dominance rate。
50. hypervolume。
51. anytime performance/AUC。
52. time-to-first-valid。
53. time-to-best。
54. budget exhaustion rate。
55. solution diversity。

# 十、运行效率与可扩展性

1. wall-clock time。
2. CPU time。
3. peak RSS。
4. GPU memory。
5. disk I/O。
6. temporary storage。
7. energy consumption。
8. monetary cost。
9. initialization time。
10. parsing time。
11. basis conversion time。
12. optimization time。
13. verification time。
14. serialization time。
15. time-to-solution。
16. throughput circuits/hour。
17. timeout rate。
18. OOM rate。
19. crash rate。
20. budget-exhausted-but-valid rate。
21. runtime median、p90、p95、p99。
22. runtime随 qubits 的 scaling exponent。
23. runtime随 gate count 的 scaling exponent。
24. memory随规模的 scaling exponent。
25. 是否存在性能相变或只是资源阈值？
26. scaling fit 是否有 CI？
27. 是否比较 polynomial、exponential 和 piecewise 模型？
28. 是否做 out-of-range extrapolation 检验？
29. 是否报告最大可处理规模？
30. 最大规模是否仍保持语义验证？
31. 是否绘制 quality–runtime frontier？
32. 是否绘制 validity–runtime frontier？
33. 是否进行线程数/worker 数敏感性分析？
34. 是否测试冷缓存和热缓存？
35. 是否报告硬件与操作系统环境？

# 十一、统计推断

npj Quantum Information明确要求说明检验名称、每项分析的 n、比较对象、检验理由、α、单/双侧和实际 p 值，并同时给出描述统计。[统计报告要求](https://www.nature.com/npjqi/for-authors-and-referees/submission-guidelines)

1. 真正的实验单位是什么？
2. seed 是独立单位还是重复测量？
3. circuit instance 是否嵌套于 family？
4. tool 输出是否配对？
5. 是否错误使用独立样本检验？
6. 是否存在 pseudo-replication？
7. point estimand 是 instance-weighted 还是 family-weighted？
8. bootstrap 是否与 estimand 一致？
9. cluster permutation 是否保持 cluster 内结构？
10. 外层 cluster 数是否足以支持渐近近似？
11. 是否使用 exact/randomization inference？
12. 是否报告效应量？
13. 是否报告 95% CI？
14. 是否报告 median/quantile 等稳健统计量？
15. 是否预先定义 MCID？
16. 是否进行 equivalence/non-inferiority test？
17. 非显著结果是否被误写成“相等”？
18. p 值是否被误写成假设为真的概率？
19. 是否使用 Holm/Hochberg/FDR 等多重校正？
20. 多重校正 family 是如何定义的？
21. 是否同时报告校正前后结果？
22. 是否存在结果导向的 endpoint 选择？
23. 是否进行功效/MDE 分析？
24. 功效计算是否与实际统计模型一致？
25. 是否有 optional stopping？
26. 是否有 seed hunting？
27. 是否有 benchmark hunting？
28. 是否有 multiple-analysis-pipeline 问题？
29. 是否运行 specification curve 或 multiverse analysis？
30. 是否检查分布的偏斜、零膨胀和重尾？
31. 是否检查 boundary/separation？
32. mixed model 是否收敛？
33. Hessian、梯度和奇异随机效应是否正常？
34. 模型不收敛时是否使用预定义 fallback？
35. fallback 是否在看结果前规定？
36. 是否进行 cluster-level sensitivity？
37. 是否进行 leave-one-family-out？
38. 是否进行 worst-case family analysis？
39. 是否报告家族间异质性？
40. 是否估计 random-slope，而不只是 random-intercept？
41. 是否检查 Simpson 悖论？
42. 是否进行 influence diagnostics？
43. 是否报告 missingness/failure mechanism？
44. 缺失是否可能 MNAR？
45. 是否进行 worst-case bounds？
46. 是否区分 fixed-benchmark performance 与对潜在新实例的 generalized performance？
47. 泛化区间是否对 benchmark sampling 和运行随机性都建模？
48. 是否进行校准分析，而不只看 AUROC/MCC？
49. 分类器阈值是否预先冻结？
50. 置信区间是否覆盖外层家族不确定性？

ASA明确指出 p 值不衡量效应大小或科学重要性；NIST也区分“固定 benchmark 上的准确率”和“对潜在新样本的泛化准确率”。[ASA p-value 声明](https://www.amstat.org/asa/files/pdfs/p-valuestatement.pdf)、[NIST benchmark 泛化分析](https://www.nist.gov/publications/expanding-ai-evaluation-toolbox-statistical-models)

# 十二、稳健性、消融和因果归因

1. 是否单独改变 listing 而保持 unitary 不变？
2. 是否单独改变规则集？
3. 是否单独改变 window size？
4. 是否单独改变搜索预算？
5. 是否单独改变优化器？
6. 是否单独改变 gate basis？
7. 是否单独改变 family composition？
8. 是否单独改变 qubit size？
9. 是否存在完全交叉的 factorial design？
10. interaction 是否有统计估计？
11. representation effect 是否依赖 phase？
12. representation effect 是否依赖 family？
13. 是否比较随机 shuffle 与结构化 listing？
14. 是否比较最优、最坏和随机 listing？
15. 是否估计 listing variance？
16. 是否估计 seed variance？
17. 是否估计 instance variance？
18. 是否估计 family variance？
19. 是否进行 hyperparameter sensitivity？
20. 是否改变 fidelity threshold？
21. 是否改变 timeout？
22. 是否改变 equivalence verifier？
23. 是否改变共同基门集？
24. 是否改变 gate weight？
25. 是否用加权成本而不仅是等权 gate count？
26. 结论是否在不同软件版本下保持？
27. 结论是否在不同硬件架构假设下保持？
28. 是否有 placebo representation？
29. 是否有无信息特征基线？
30. 是否有标签置换检验？
31. 是否有负对照 family？
32. 是否有机制级 trace 证明为什么发生差异？
33. 消融是否真正隔离变量，而不是同时改多个组件？
34. 是否把相关性误当成机制因果？
35. 是否有 mediation/path analysis 的必要性？

# 十三、跨家族和外部有效性

1. held-out 是否在 generator 层彻底隔离？
2. 是否冻结模型、特征、阈值和预处理？
3. held-out 数量是否足以得到窄区间？
4. 是否覆盖与训练分布相近和远离的家族？
5. 是否报告 domain distance？
6. 是否报告每个 held-out family 的结果？
7. 是否有 family-level calibration？
8. 是否出现某个家族完全失败？
9. 是否有 leave-one-generator-out？
10. 是否有 leave-one-algorithm-class-out？
11. 是否有 leave-one-gate-set-out？
12. 是否有跨 qubit 范围外推？
13. 是否有跨 topology 泛化？
14. 是否有跨 compiler version 泛化？
15. 是否有跨硬件平台泛化？
16. 是否有跨研究组独立数据？
17. 是否有真正真实世界电路？
18. 是否把合成 generator 的多样性误当成真实分布代表性？
19. 是否报告 covariate shift？
20. 是否报告 prediction interval，而不只是均值 CI？
21. 模型是否只学到 gate count 或 family ID？
22. 是否检查 shortcut learning？
23. 是否进行 feature ablation？
24. 是否进行 out-of-distribution detection？
25. 当 OOD 时是否允许模型拒绝预测？

# 十四、硬件意义与量子价值

QED-C强调结果质量、宽度–深度体积和 time-to-solution，因此硬件价值不能仅由逻辑门数推断。[QED-C application-oriented benchmarks](https://arxiv.org/abs/2110.03137)

1. 优化后的逻辑电路是否映射到真实 native gate set？
2. 是否使用真实 coupling map？
3. 是否使用同一 initial layout？
4. 是否使用同一 routing policy？
5. 是否使用固定 calibration snapshot？
6. 是否记录 calibration 时间？
7. 是否报告 native 2Q count？
8. 是否报告 native 2Q depth？
9. 是否报告 scheduled duration？
10. 是否报告 idle time？
11. 是否报告 crosstalk-sensitive concurrency？
12. 是否报告 estimated success probability？
13. 是否报告 noise-aware cost？
14. 是否运行 noisy simulator？
15. noise model 是否来自真实校准？
16. 是否在至少一个真实 QPU 上执行？
17. 是否有多个日期的重复硬件实验？
18. 是否随机化执行顺序以减小 drift？
19. 是否记录 shots？
20. shots 数是否由精度目标决定？
21. 是否报告 measurement uncertainty？
22. 是否报告 Hellinger fidelity、TVD、cross entropy 或应用特定质量？
23. 是否比较 error mitigation 前后？
24. mitigation 收益是否包含额外时间和 shots 成本？
25. gate count 下降是否真正改善硬件输出？
26. 是否出现门更少但 fidelity 更差？
27. 是否出现 depth 更短但 crosstalk 更强？
28. 是否报告 queue time 和纯执行时间？
29. 是否报告 end-to-end time-to-solution？
30. 是否比较多个硬件拓扑？
31. 是否有平台特定结论被误写成通用结论？
32. 是否考虑 dynamic circuits？
33. 是否考虑 pulse-aware 编译？
34. 是否考虑容错时代成本模型？
35. 当前成果的“量子价值”是硬件收益、编译诊断，还是理论认识？

# 十五、可复现性、数据和软件工件

ACM将优秀工件评价为 documented、consistent、complete、exercisable，并区分 Artifacts Evaluated、Available 和 Results Validated；Nature要求支撑结论的最小数据集、代码和协议可获得。[ACM Artifact Review](https://www.acm.org/publications/policies/artifact-review-and-badging-current)、[Nature 数据与代码标准](https://www.nature.com/nbt/editorial-policies/reporting-standards)

1. 是否有从零开始的 README？
2. 是否列出支持的 OS？
3. 是否固定 Python/编译器/SDK 版本？
4. 是否有 lockfile？
5. 是否有 container 或可重建环境？
6. 是否有 SBOM？
7. 是否记录外部二进制哈希？
8. 是否有许可证？
9. 数据是否有许可证？
10. 是否有 DOI/Zenodo 归档？
11. 是否有持久版本号？
12. 是否有 data dictionary？
13. 是否有 schema？
14. 是否有 provenance chain？
15. 是否有 raw、derived、figure-source 分层？
16. 是否保留原始失败输出？
17. 是否保留日志？
18. 是否有数据 checksum？
19. 是否能检测数据被修改？
20. 是否有 release manifest？
21. 是否有一条命令重建每张表？
22. 是否有一条命令重建每张图？
23. 是否有一条命令运行主要实验？
24. 是否有 quick/smoke 和 full reproduction 两种路径？
25. 是否声明预计时间、CPU、内存、GPU 和磁盘？
26. 是否有 deterministic mode？
27. 非确定性是否给出允许误差？
28. 是否在干净机器验证？
29. 是否由非作者验证？
30. 是否保留失败复现记录？
31. 是否有 CI？
32. CI 是否只跑单元测试，还是也做数据/清单验证？
33. 是否对关键结果做 hash assertion？
34. 是否检查 CSV 行数、列名和无限值？
35. 是否检查 figure 与 source-data 对应？
36. 是否检查文档引用的数值与数据一致？
37. 是否区分 canonical data 与 exploratory rerun？
38. 是否禁止半成品 checkpoint 进入正式清单？
39. 是否记录 dirty worktree？
40. 是否能从固定 commit 重建 release？
41. 是否有 archive restore test？
42. 链接是否会腐烂？
43. 元数据是否机器可读？
44. 数据是否符合 Findable、Accessible、Interoperable、Reusable？
45. 是否存在无法公开的限制？是否明确说明？

FAIR原则要求持久标识、丰富元数据、标准协议、互操作词汇、许可证和详细 provenance。[FAIR 原则](https://www.nature.com/articles/sdata201618)

# 十六、科研价值与影响力

1. 谁会因为这个结果改变研究方法？
2. 它解决的是领域核心瓶颈还是局部实现问题？
3. 是否能避免错误的 optimizer ranking？
4. 是否能减少无效搜索预算？
5. 是否能指导表示选择？
6. 是否能指导 rewrite library 设计？
7. 是否能指导 benchmark construction？
8. 是否能指导编译器自动选择策略？
9. 是否能预测哪些线路有优化 headroom？
10. 是否能产生新理论问题？
11. 是否能形成公开 benchmark？
12. 是否能形成独立软件工具？
13. 是否能被其他编译器直接集成？
14. 是否能扩展到 routing/synthesis/error correction？
15. 是否能扩展到 parameterized circuits？
16. 是否能扩展到硬件感知目标？
17. 是否能减少物理双比特门或执行时间？
18. 是否能减少容错 T 资源？
19. 是否有真实用户或外部研究组需求？
20. 是否有外部复用证据？
21. 是否有 benchmark 被第三方采用的可能？
22. 结果是否在五年后仍有意义？
23. 如果所有具体工具版本更新，机制结论是否仍成立？
24. 贡献是暂时性能数字还是可迁移知识？
25. 是否有明确的“不应该如何评价量子优化器”的方法学价值？
26. 是否能形成社区标准或 checklist？
27. 是否能发现已有文献的系统性评价偏差？
28. 是否有负面结果同样值得发表？
29. 是否能降低其他研究者复现实验的成本？
30. 是否能推动从平均性能转向 family-aware/Pareto-aware 评价？

# 十七、负面结果与红队审查

1. 最强反例是什么？
2. 哪个 family 最不支持核心结论？
3. 哪项结论对单个数据点最敏感？
4. 哪项结论对阈值最敏感？
5. 哪项结论依赖某个工具版本？
6. 哪项结论依赖某个 basis？
7. 哪项结论依赖某个 timeout？
8. 哪项结论在 equal-budget 下可能反转？
9. 哪项结论可能由数据泄漏产生？
10. 哪项结论可能由 benchmark selection 产生？
11. 哪项结论可能由 survivorship bias 产生？
12. 哪项结论可能由非等价输出产生？
13. 哪项结论可能由重复样本夸大显著性？
14. 哪项结论无法在大规模线路验证？
15. 哪项结论没有独立工件支持？
16. 哪项结论没有硬件证据？
17. 是否尝试主动构造失败 family？
18. 是否尝试搜索最小反例？
19. 是否让独立研究者攻击 theorem？
20. 是否让独立研究者攻击统计方案？
21. 是否让外部工具作者检查配置？
22. 是否进行 blinded analysis？
23. 是否保留被推翻的假设？
24. 是否把 null result 完整发布？
25. 是否明确什么证据会改变最终判断？
26. 如果审稿人只允许保留一个贡献，哪一个仍成立？
27. 如果删除所有 p 值，证据是否仍有说服力？
28. 如果删除总体均值，家族结果是否仍支持结论？
29. 如果删除自定义 benchmark，结果是否仍成立？
30. 如果只看真实线路，结果是否仍成立？

# 十八、对你当前项目最值得继续补的指标

你目前已经较强地覆盖了：冻结协议、精确等价、ITT、家族聚类统计、LOFO、密封 held-out、两个外部工件、失败保留、理论撤回、发布清单和全工作区审计。

如果目标是继续向 PRX Quantum/npj Quantum Information 一类标准逼近，边际价值最高的是：

1. **真实硬件或高保真 noise-aware 验证**  
   检查逻辑缩减是否真的改善 native 2Q depth、duration 和输出质量。

2. **等算力 Pareto 实验**  
   除官方配置外，再比较固定 1、10、30、120 秒及固定内存预算下的质量–时间曲线。

3. **扩大真正独立的 held-out family 数**  
   当前八个外层家族的 MCC 区间仍宽；优先增加外层家族，而不是增加同一家族 seed。

4. **第三个可执行独立强工件**  
   条件允许时加入 GUOQ、Quarl 或其他可扩展工具，检验 Quasar/Quartz 结论是否稳定。

5. **扩大评价成本向量**  
   增加 2Q depth、native gate count、scheduled duration、T-count/T-depth、peak memory、energy/cost。

6. **大型线路层级**  
   建立数十至数百 qubit 的压力集；因为不能构造完整 unitary，需要预先冻结符号验证、decision diagram、ZX/path-sum 或“有效性不可确认”的降级规则。

7. **参数化线路等价**  
   不再只依赖有限参数实例，增加符号参数等价或明确的概率性覆盖合同。

8. **机制因果实验**  
   用 listing×rule-set×window×budget 的完整 factorial design，分离表示、规则覆盖和搜索预算效应。

9. **独立冷启动复现**  
   由另一台机器或另一位研究者从归档 DOI 开始，完全重建主要表图和一组正式实验。

10. **版本与平台稳健性**  
    在至少两个 Qiskit/tket/Cirq 版本、Windows/Linux 或不同 CPU 上检查结论漂移。

11. **测试强度指标**  
    增加 mutation score、property-based counterexample discovery、故障注入和 parser/QASM round-trip coverage。

12. **预投稿最新文献刷新**  
    重点监控 2025–2026 年表示变换、e-graph、参数化等价、AI 编译器和局部最优组合方法。

最重要的认知更新是：你下一阶段不应简单追求“更多行数、更多 seed、更多显著 p 值”。最高价值来自增加真正独立的外层证据、建立硬件或容错成本联系、实现等算力公平比较，以及让第三方在干净环境中复现整个证据链。