# Q-research 全项目科研审计（2026-08-09）

> 性质：内部科研审计，不是论文草稿。
> 边界：未修改 `docs/manuscript/manuscript.md`；先修代码、统计、数据契约和理论状态。

## 1. 覆盖与验证

- 基线：`master`，审计开始时 HEAD 为 `d463d7a04ae22ec3ee9df9c97166ce5f007b36c0`，工作树干净。
- 逐字节读取全部 564 个跟踪文件（36,692,487 bytes）。
- 545 个 UTF-8 文本文件，共 221,416 行；19 个 PDF 均完成页面渲染检查。
- 215 个 CSV（152,789 行）和 79 个 JSON 全部可解析；数值列无无穷值。
- 发布清单 37 个条目全部通过 SHA-256 与行数核验；其中 35 个为 active canonical，共 96,205 行，另外 2 个为 superseded provenance。
- `compileall` 通过；335 个 pytest 测试全部通过。
- 规范数据校验通过，但多个旧实验记录的 source hash 与当前代码不同；这意味着“冻结数据完整”，不意味着“当前代码可原样复现旧数值”。

## 2. 总体判断

### 科研水平

**当前等级：强研究工程原型 / 中等科学结论可信度。**

优点：实验覆盖广、数据版本链和发布清单较完整、代码可测试、问题记录充分、表示敏感性是一个真实且有工程意义的现象。

限制：若干核心理论证明曾被错误标为成立；部分冻结实验使用了错误或不可解释的 fidelity/success 契约；多组统计忽略配对结构；SOTA 与预测实验尚不足以支持外推或优越性结论。

### 创新水平

**当前等级：中等、但必须窄化。**

不能再主张“首次发现搜索空间限制”“首次研究表示影响”或“通用 Phase-1 ceiling”。Quarl 已明确处理图表示与非统一动作空间；Quasar 同时使用图和序列 e-graph 并提供 step-limited optimality；Arora 等人的 cut-and-meld 工作提供局部最优保证。

仍可能具有辨识度的贡献是：在明确指定的平坦 gate listing、局部规则集和线路族上，对线性化敏感性、可见动作空间和经验 ceiling 进行系统消融，并将这些因素与优化器结果分解对应。该贡献目前是软件/表示条件下的经验框架，不是普适复杂度定律。

### 科研价值

**当前等级：中高潜力、尚未达到强外部结论阶段。**

若完成平衡 SOTA、持出预测、修复后重跑和更严格的表示理论，本项目可以成为有价值的量子编译诊断基准：回答“某个局部规则集为何在某种表示上失效”。当前最有价值的产出是方法学负结果和审计透明度，而不是“新物理规律”或“算法无关上限”。

## 3. 已确认的关键问题与处理

1. **Fidelity 失败时伪造结构相似度。** 删除 gate-multiset/Jaccard 回退；精确计算失败时转采样，采样也失败则返回 NaN 并 fail closed。
2. **Success 契约不一致。** 未来代码统一为 reduction 至少 5% 且 fidelity 达标；冻结 v2_fixed--v8 的旧标志不追溯改写，跨版本分析应从原始 reduction/fidelity 重算。
3. **全局相位造成 Phase-1/Phase-2 偏置。** Greedy 现在按项目的物理等价契约删除 `R(2kπ)`；与 Phase-2 行为一致。
4. **E10 和多组汇总统计误用独立样本检验。** 改为按生成实例严格一一配对，使用 Wilcoxon/Friedman、paired bootstrap、Cohen dz 和 matched rank-biserial；拒绝重复或未匹配行。
5. **有限尺寸缩放过拟合和伪 critical point。** 统一标准 Binder 定义，采用 leave-one-size-out collapse 和按 size 分层 bootstrap；不能识别时返回 NaN/不适用。
6. **功效分析 ARE 使用错误。** Mann--Whitney 的 0.955 ARE 作用于样本量/非中心参数关系，不再直接乘功效值。
7. **AG canonical 一般定理存在反例。** 旧生成器 `n=2, seed=35` 可出现相邻相同 CNOT，Greedy 从 7 门降到 5 门。生成器已保证每个名义 H stage 非空；原一般定理撤回，只保留修正生成器的窄命题，E23 必须重跑。
8. **Theorem 2d 证明无效。** 含双比特门的电路一般不能分解为每根 wire 的独立酉矩阵；原证明还把逆门对计数等同于可实现的 Phase-2 最优值。该结论已撤回；随机优化器 ceiling 仍是开放问题。
9. **Theorem 5 浓缩界不完整。** 随机 matching 端点依赖，原 McDiarmid 独立乘积空间不是实际生成器；需要 exposure martingale 或 matching concentration 证明。
10. **Theorem 8 前提矛盾。** 同时假设精确多项式尺寸实现和最小复杂度大于该尺寸；定理及推论撤回。
11. **QMA-hardness 草稿无效。** Non-Identity Check 的 promise 方向被反转；diamond norm 写在矩阵而非诱导信道上；SWAP test 不能验证所声称的 worst-case diamond closeness。整份草稿仅保留为失败路线记录。
12. **SOTA 比较不平衡。** Custom 仅 21 行 smoke，其他工具 440--520 行；大多数 family 没有 exact matched pair，仅少数 cell 为 `n=3`。规范描述聚合保持 SHA 不变，修正推断另存审计产物；禁止据此声称 custom/SOTA 优越。
13. **Predictive advantage 是循环验证。** 规则来自同一批 15 个 family，又在同一批 family 上计算 86.67% accuracy/MCC 0.7385。已标记为 in-sample resubstitution；7.6x 仅是反事实 runtime proxy，不是实测持出加速。
14. **规模优先权不成立。** 96,205 行主要是重复观测，不能与 Quartz/Quarl 的 unique benchmark 数直接比较；“最大研究”“高两个数量级”已从非论文研究说明中撤回。
15. **引用错误。** 伪造/错配的 Patel--Shapira--Markov `arXiv:2210.12035` 条目已移除并保留审计 tombstone。

## 4. 当前仍可使用的证据

- 发布清单及 37 个冻结文件的字节完整性和行数。
- 在当前生成器/listing/Greedy predicate 下，LBL 暴露的相邻逆门对稀疏或为空这一软件行为。
- WCL/LBL、Phase-2a/2b 与线路族之间存在明显经验异质性，但应限定到具体实现与规则集。
- Theorem 7 的人工 Phase-2a 构造和 Theorem 9 的 BV Phase-2b 构造可作为窄存在性结果；不能外推为一般 ceiling 定律。
- E10 配对重算中，Universal 的 Phase-2a 优势显著；Structured 为全零；real-35 的样本和效应需按配对报告，不再使用独立样本解释。

## 5. 暂时不可用于强结论的证据

- E3/E14 的旧 fidelity=0 unchanged-circuit 行、E18 的失败/选择偏差、E26 的 product-state sampling fidelity。
- 旧 AG/E23 对一般 canonical Clifford ceiling 的验证。
- 不平衡 SOTA aggregate 的跨工具显著性和优越性。
- predictive advantage 的 accuracy、MCC 和 speedup 作为外部预测性能。
- QMA-hardness、Haar incompressibility、一般 stochastic Phase-1 ceiling。
- 任何“最大规模”“首次”“唯一框架”或算法无关的优先权结论。

## 6. 最小下一轮实验（写论文前）

### P0：恢复结论有效性

1. 在完全共享的 520-row 设计上重跑 custom、Qiskit、Cirq、t|ket>；按 input SHA/circuit id/seed 一一配对并统一 gate basis、routing、timeout 和 fidelity policy。
2. 用当前 fidelity/success 契约重跑 E3、E14、E18、E26；分别报告 exact、sampled、unavailable，禁止把 unavailable 当 0。
3. 用修正后的 AG generator 重跑 E23，并把旧 `n=2, seed=35` 作为固定反例回归测试。
4. 预注册持出预测：按未用于规则设计的新 family 或新 generator 留出测试集；所有阈值只在训练 family 上确定。

### P1：建立可发表的创新边界

1. 在相同 QASM/指标上加入 Quasar、Quartz、Quarl（可运行版本）及 cut-and-meld/GUOQ 类方法；比较“表示敏感性诊断”而不只比较 reduction。
2. 若保留一般 ceiling 理论，改用 dependency DAG/trace monoid，定义 conflict-aware 最大可消除集合，并证明 identity insertion 不改变该最优值；否则明确放弃普适定理。
3. 采用层级/混合效应模型区分 circuit instance、family、seed、optimizer 和 representation；多重比较方案预先固定。

## 7. 验收状态

- 代码编译：通过。
- 全测试：335/335 通过。
- CSV/JSON 解析：294/294 文件通过；无数值 infinity。
- Release manifest：37/37 SHA 与行数通过。
- 图表再生成：通过；FDR 主表改用设计匹配的配对检验与配对效应量。
- 论文正文：未修改。
- 科研结论：完成审计和第一轮基础修复；P0 重跑未执行，因此项目不应视为“论文结论已最终验证”。
