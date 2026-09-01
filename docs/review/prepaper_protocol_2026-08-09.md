# Q-research 论文前确认性研究协议（冻结版）

**冻结日期：** 2026-08-09  
**阶段：** 论文撰写前；本文件冻结后，所有偏离均须追加记录，不能覆盖原规则。  
**研究定位：** 本项目研究固定局部量子线路优化规则集在不同平坦 gate listing / representation 下的可见动作空间、优化收益与经验 ceiling。它不预设普适相变、算法无关 ceiling 或复杂度下界。

## 1. 可证伪问题与主要结局

### RQ1：表示敏感性

在电路语义、局部规则集和优化预算固定时，改变合法线性化是否会系统改变可见可消除动作及最终门数？

- **主要结局：** 同一输入实例、同一优化器、不同 representation 的归一化门数下降百分比之配对差。
- **反证条件：** 95% 置信区间包含预注册的最小相关效应 `|Δ reduction| = 1 percentage point`，且等效性检验支持 `[-1, +1]` 区间。
- **次要结局：** 深度、双比特门数、动作空间大小、运行时间；均明确标为次要。

### RQ2：结构诊断的外部预测能力

仅用优化前结构特征训练/冻结的诊断器，能否在完全未参与规则设计的新生成器族上识别“存在可利用优化余量”的实例？

- **主要结局：** family/generator-clustered held-out MCC。
- **共同结局定义：** 在至少两个独立外部优化器中，共同基门集归一化后的门数下降均超过 1%，且等价性通过，定义为有外部优化余量。
- **成功门槛：** held-out MCC 的双层 bootstrap 95% CI 下界大于 0；accuracy、F1、AUROC 为次要结果。
- **禁止泄漏：** 阈值、特征选择、缺失值处理、标准化、模型选择只能使用训练 families；held-out generator 的任何优化结果不可用于调参。

### RQ3：工具比较与边界

在共享的 520 个输入上，custom、Qiskit、Cirq、t|ket> 的有效输出、失败率和资源指标如何不同？

- **主要结局：** 有效等价输出率（包含 timeout/error/unavailable 的意向性分母）。
- **次要结局：** 共同基门集下的门数、双比特门数、深度和运行时间。
- **解释边界：** 这是一组固定版本、固定配置的实现比较，不代表算法类别的普适排序。

## 2. 共享 SOTA 设计

- 输入由 `seed = 42 + 1000 * trial`, `trial = 0..9` 生成；目标 qubit 数为 `{4, 6, 8}`；预期 520 个实例。
- 输入在任何工具运行前物化为 OpenQASM 2 文件和 manifest。配对键为：
  `benchmark_manifest_sha256 + input_circuit_sha256 + circuit_id + trial + seed`。
- 所有工具仅读取同一 manifest；禁止在后端内部重新生成输入。
- **原生指标**用于描述各工具自己的输出；**跨工具资源比较**只使用统一的无优化 basis normalization：`['rz', 'sx', 'x', 'cx']`，不设置 coupling map，不做 routing。
- 优化时间只计工具本身；解析、共同基门归一化和 fidelity 验证分别计时。
- 每实例 timeout 为 120 s。版本、配置、CPU/OS、Python 和依赖版本写入 metadata。
- 旧 suite 的 `{4, 6, 8}` 是 family target size，不总等于实现后的寄存器宽度；实际输入为 4--10 qubit。全部使用精确 average gate fidelity；全局相位不影响判定。`fidelity >= 1 - 1e-10` 才视为等价。

## 3. 失败、缺失与意向性原则

- `timeout`、`error`、fidelity unavailable、fidelity 未达阈值均保留在主分析分母中，不能删除。
- 主分析中无有效等价输出的实例记为“无可证实改进”，资源下降记为 0，同时单独报告失败原因；不把未知 fidelity 写成 0。
- 完整案例分析只能作为敏感性分析，必须与意向性结果并列。
- 所有排除必须来自以下预注册规则：输入 QASM 无法被任一工具共同解析、manifest SHA 不匹配、重复配对键。排除数量和实例 ID 全量公开。

## 4. 修复后重跑范围

- E3、E14、E18、E23、E26 均写入 `data/v10/prepaper/`，不得覆盖旧 canonical 证据。
- fidelity 来源必须是 `exact`、`sampled_global_haar`、`exact_clifford` 或 `unavailable`；同时记录样本数和 Monte Carlo 标准误（若适用）。
- E18 的主分析采用所有尝试实例的意向性分母；转换失败不允许静默丢弃。
- E23 使用修正后的 AG generator；旧 `n=2, seed=35` 作为固定反例回归测试，不混入修正生成器的确认性估计。
- E26 不再使用 product-state fidelity；能够 exact/tableau 验证者优先，否则使用全局 Haar 并报告不确定度。

## 5. 统计分析计划

- 所有确认性检验双侧 `alpha = 0.05`。
- 单一 RQ 内多个 optimizer/representation 对比使用 Holm family-wise 校正；不同 RQ 不合并为一个 p 值池。
- 配对设计使用配对检验；同时报告原始配对差、Hodges-Lehmann 型位置差、配对 rank-biserial effect 和 95% CI。
- 层级模型至少包含 instance/family(or generator)/seed 的随机截距，以及 optimizer、representation 及其交互的固定效应。若模型奇异或不收敛，预注册后备为 family-clustered bootstrap + cluster-robust permutation。
- bootstrap 以 family/generator 为外层、instance 为内层，固定 RNG seed `20260809`，10,000 次。
- 对零膨胀/边界分布，主分析不依赖正态假设；参数模型作为一致性检查。
- 所有效应量与 CI 必须报告；p 值不单独决定科学意义。

## 6. 外部基线与理论闸门

- 优先尝试作者发布的 Quasar、Quartz、Quarl、GUOQ、cut-and-meld 代码/artifact；仅在同一输入与指标契约下进入定量表。
- 无法复现的工具须记录仓库/版本、安装命令、输入、错误和阻断类别；不得用论文表格数字冒充本地复现。
- 一般 ceiling 定理只有在 dependency DAG / trace-monoid 定义下给出完整证明并通过反例搜索后才能恢复；否则最终结论明确限定为经验性、规则集和表示依赖。

## 7. 论文前通过标准

只有以下条件全部满足才允许进入论文撰写：

1. 520 输入 manifest 冻结，四工具键集合完全相同，主分析无未解释缺失。
2. E3/E14/E18/E23/E26 修复后全规模重跑完成，原始数据、metadata、代码 SHA 可追溯。
3. held-out generator 在封存预测后才运行优化器，且泄漏审计通过。
4. 层级/cluster-aware 统计、稳健性、功效和多重校正完成。
5. 至少两类强外部方法在同一协议下成功运行；其余方法有可复现阻断记录。
6. 理论主张要么完整证明，要么明确收缩，不存在“草稿证明被当成结果”。
7. 所有主图有源数据、PDF/SVG 和 600 dpi PNG，颜色无障碍且灰度可辨。
8. release manifest、全量测试、数据 schema、行数与 SHA 验证全部通过。
9. ScholarEval 八维加权分数至少 4.0/5，且 Methodology、Data、Analysis 均不低于 4。

## 8. 偏离日志

冻结后任何修改追加到本节，格式为：日期、原规则、修改、原因、是否在查看相应结果前决定、影响范围。不得回写删除历史。

- 2026-08-09：协议首次冻结；尚未查看本轮新生成的 SOTA、修复重跑或 held-out 结果。
- 2026-08-10：在查看任何正式 SOTA 结果前发现首版隔离执行器把 Windows 子进程启动计入 `runtime_seconds`，且无 checkpoint；四个父任务在一小时外层上限停止时均未写出正式 CSV。执行器改为每工具一个持久隔离 worker，优化器内部记录 `optimizer_elapsed_seconds`，外部另记 `end_to_end_elapsed_seconds`，每 10 行原子 checkpoint；单实例 120 s 终止规则、输入、样本量、结局和阈值均未改变。首轮不构成科研结果。
- 2026-08-10：第二轮完整性审计（效应分析前）发现 checkpoint 键漏 `circuit_id`，导致两个不同 ID、相同语义哈希的合法实例被折叠；键修复后四工具均为 520 个唯一配对实例。又发现 legacy target size 会产生最多 10 个实际 qubit，因此精确 fidelity 上限由 8 修正为 10，以兑现“全实例 exact”的原意。
- 2026-08-10：兼容性/等价性闸门发现 QASM 中带定义的 `mcx`/`mcphase` 仍被 Qiskit 保留为高层指令，使 t|ket> 适配器拒绝 Grover/QuantumWalk；共享输入物化阶段现统一展开这两个定义，四工具均消费同一新 manifest。Cirq 现显式保留 idle qubit 索引；t|ket> 转回 Qiskit 时启用 implicit-swap replacement。以上修复发生在任何门数效应检验之前；旧 manifest 和旧 520 行输出转存为 preflight-invalid 证据，不进入统计。
- 2026-08-10：E18 冒烟在正式结果分析前暴露概念错误：旧设计试图将含任意连续旋转及 Haar 单元的扩展套件“精确”转换到离散 Clifford+T 门集；一般此类有限精确分解不存在，且该尝试在一个冒烟实例上持续消耗计算而无输出。明确识别的冒烟进程被终止且无结果进入证据链。E18 改为原生生成六类严格 Clifford+T（含可精确分解的 Toffoli block）线路，full 网格为 n=3..8、每族每 n 10 个独立 seed、三个优化器，全部使用 exact fidelity 与 ITT 失败分母。此修改发生在查看任何 E18 新结果之前；主要问题仍是 Clifford+T 表示下局部/交换优化的效果。
- 2026-08-10：在运行任何 held-out 优化结果前物化并封存 8 个新 generator（MirrorRandom、SeparatedInverse、PauliGadgetLadder、ClusterEcho、IsingBrickwork、FredkinChain、ControlledRotationFanout、DihedralAlternation），n={4,6,8}、每格 10 个 seed，共 240 个共享 QASM。Qiskit/Cirq/t|ket> 仅做解析兼容性检查，240/240 通过；未调用优化器。冻结分类器为训练 families 上的 L2 logistic regression（C=1、class_weight=balanced、阈值 0.5），训练集内中位数填补与标准化；特征固定为 n_qubits、log1p(n_gates)、inverse_pair_density、wire_inverse_density、commutation_density、gate_diversity、rotation_fraction、clifford_fraction、t_fraction、multi_q_fraction、has_multi_controlled、depth_to_gate_ratio。标签严格使用 Qiskit 与 t|ket> 在共同基门集上均有效且 reduction>1% 的交集；所有预处理参数只从训练 families 拟合。若训练标签单类，后备为按训练标签先验的常数预测并将确认性 MCC 记为不可识别，而不改阈值/特征。预测文件及模型参数 SHA 封存后才允许运行 held-out 优化器。
- 2026-08-10：Cirq 的 520 行文件完成后、任何效应比较前，等价性闸门发现 490 行 fidelity unavailable。根因是 Cirq QASM importer 使用 `NamedQubit('q_i')`，适配器为保留 idle wires 却追加了不同对象类型 `LineQubit(i)`；非空线路导出时因而形成两套寄存器，只有被完全消去的 CNOT 族偶然通过。该文件整体转存到 `preflight_invalid/cirq_linequbit_identity_20260810`，不得进入分析。修复须在 custom/Qiskit/t|ket> 当前进程结束后实施，以避免中途改变其动态记录的 source SHA；随后 Cirq 必须从同一 520 manifest 全量重跑并再次逐行 exact 验证。
- 2026-08-10：Quasar 正式外部基线的首轮调度在 51 条 checkpoint 后、任何跨方法效应分析前被判为资源混杂：4 个并发 artifact 子进程各自建立 BLAS 线程池，日志明确出现 `memory allocation ... failed` 与 `OpenBLAS ... Memory allocation ... failed`。该轮完整归档至 `shared_520/preflight_invalid/resource_contention_20260810_0954`，不进入科研统计。重跑固定为单 executor worker，并向未修改的官方 artifact 子进程设置 `OPENBLAS_NUM_THREADS=OMP_NUM_THREADS=MKL_NUM_THREADS=NUMEXPR_NUM_THREADS=1`；输入、Seq-EG step=8/iters=3/no-ILP/no-escalation、每实例 120 s 内部预算、结局和 ITT 规则均不变。此改动只消除调度层资源争用，且在查看任何跨方法结论前决定。
- 2026-08-10：单 worker Quasar 重跑仍与此前启动、尚在完成的 Cirq 精确验证重叠；Cirq 在 340/520 后因 multiprocessing queue 分配 741,376 bytes 失败而退出，Quasar 的 30 条 checkpoint 中亦有两条几十 KB 内存分配失败。该 Quasar 轮归档至 `shared_520/preflight_invalid/residual_overlap_20260810_1012`，不进入统计；Cirq 从原子 checkpoint 续跑。此后两项严格串行，先完成 Cirq，再独占运行 Quasar。算法配置、输入、超时和结局不变；真正达到时间预算的 timeout 与调度性 memory failure 分开处理。
- 2026-08-10：Cirq checkpoint 续跑的 Windows 隐藏进程约 30 秒后才出现在进程查询中；一次过早检查导致第二个父进程被启动。两进程均尚未新增 checkpoint 行，后启动的 PID 18984 及其子进程被立即精确终止，仅保留 PID 6464。最终仍须以 520 个唯一配对键、单一 manifest/source SHA 和逐行等价性审计为准；该调度事件不改变输入或结果规则。
- 2026-08-10：Quasar 单-worker 隔离轮在已确认 137 条后，与新发现的 stochastic-incumbent 回归测试重叠约 160 秒；测试虽仅涉及小线路，但 CPU 竞争可能影响 wall-time timeout。Quasar 父进程随后在 162 条 checkpoint 处无 traceback 退出。完整 162 条 checkpoint/log 归档至 `shared_520/preflight_invalid/test_overlap_after_row137_20260810`；正式 checkpoint 精确截回重叠前已确认的前 137 条，后 25 条全部重跑。算法、输入、时间预算和结果规则不变。
- 2026-08-10：理论反例搜索发现一般“初始 Greedy 动作集为空即所有 Phase-1 优化器零收益”命题为假：`H(q0), X(q1), H(q0)` 可先交换互不相交的前两门，再消去相邻 H 对，从 3 门精确降至 1 门。同期代码审计发现 SA/RLS/GA 把含 cancellation-potential 奖励的探索 fitness 当作返回 incumbent，可能在已经访问较小等价线路后仍返回膨胀线路。三实现已改为独立保存最小 fidelity-valid incumbent，并加入回归测试。此发现要求撤回一般算法无关 ceiling；Greedy、受限生成器和 E26 Phase-2b 结果不受该逻辑命题支持。旧 stochastic 数据不重写，须在修复代码下重跑后方可用于相关主张。
- 2026-08-10：复杂性理论交叉审计确认旧 `framework.md`/QMA 草稿错误地把本项目 CIT schema 直接标为 QMA-complete、把 `r=0` 当作 CODP hardness 特例，并由 Gottesman--Knill 推出一般最优 Clifford 优化在 P。原始 Non-Identity Check 定理依赖明确 promise gap、范数、全局相位与“远离 identity 为 YES”的方向；`r=0` 在当前 CODP 定义下由输入线路自身平凡满足，`r=1` 又反转该 promise。diamond norm 也必须作用于诱导信道而非矩阵差。上述复杂性结论全部收缩为 open/未分类；Clifford 仅保留等价性/模拟在 P。此为证明有效性修正，不改变任何实验输入、结局或统计计划。
- 2026-08-10：Quasar 独占续跑在 217 条原子 checkpoint 后再次无 traceback 消失。审计确认 Windows `.venv\\Scripts\\python.exe` 会再派生实际 Python；旧 `subprocess.run` 外层 timeout 只保证直接 wrapper 被终止，可能留下继续耗内存的孙进程，解释宽线路 timeout 后调度器被资源压力终止。前 217 条的 checkpoint SHA 与旧 driver SHA 已冻结在 `shared_520/execution_segments.json`，结果/输入/算法配置均保留。后续 driver 只改变执行控制：每个 pending 实例先删除同目录旧输出，使用 `Popen`，外层 timeout 后对精确 PID 调用 Windows 整棵进程树终止，并记录 return code；Seq-EG step=8/iters=3/no-ILP/no-escalation、内部 120 s 预算、输入、结局与 ITT 规则不变。新旧 driver SHA 分段公开，禁止用单一源码哈希掩盖该修正。
- 2026-08-10：进程树修正版从 217 行续跑后的首个宽线路超时（`ghz_8`, trial 4）提供了直接执行证据：外层 140 s 到期后 `taskkill /T` 返回成功，并分别记录实际 Miniforge 子进程和 `.venv` wrapper 被终止；随后检查点继续完成 `grover_4`，从 217 推进至 219。该证据证明新控制覆盖了观测到的两层进程，但不能证明旧父进程消失只有这一项原因。原先含省略号、不可重放的示意 `.patch` 已删除，改为 `driver_process_tree_cleanup_notes.md`；两个真实源码 SHA 和断点 SHA 仍以 `execution_segments.json` 为准。
- 2026-08-10：Quasar segment 2 到 226 行后，检查点时间戳停止变化，但单 worker 已派生到后续输入，表明 worker 仍执行而主线程不再落盘。可能原因是 Windows 原子替换与短暂只读监控发生 sharing violation，随后异常在 executor shutdown 等待中未打印；这是时序推断，因为终止前没有 traceback。为避免更多未落盘计算，精确终止 PID 4004 及子树，226 行文件以 SHA-256 `95f33a...14e` 保留；未 checkpoint 的尝试全部重跑。segment 3 仅为 `PermissionError` 的原子替换增加 8 次有界指数退避，并停止打开活动 CSV 监控；算法配置、输入、时间预算、结局和 ITT 不变。分段源码 SHA 继续记录在 `execution_segments.json`。
- 2026-08-11：指标审计发现首轮正式 SOTA CSV 只保存 `optimizer_elapsed_seconds` 与 worker-wrapper `end_to_end_elapsed_seconds`，没有兑现第 4.2 节所述的解析、共同基门归一化、fidelity 验证和序列化分段计时。历史 520 行证据保持不可变，所有新增字段对历史数据均显式为 unavailable，不允许用 0 回填。未来 schema 1.1 逐行记录 manifest QASM 解析、输入/输出归一化、优化、exact 验证、结果行序列化、完整 pipeline wall time、worker CPU time、50 ms 轮询得到的进程树 peak RSS，以及共同基门下的 2Q depth。旧 `end_to_end_elapsed_seconds` 保留原 worker-wrapper 语义以避免静默改写；完整端到端口径使用 `pipeline_elapsed_seconds`。质量--时间 Pareto 分析可以从历史 `optimizer_elapsed_seconds` 与 ITT reduction 派生，但 CPU/RSS/阶段计时和 2Q depth 只能由新运行产生。
