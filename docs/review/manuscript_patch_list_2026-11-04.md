# 正文修订清单（2026-11-04）

**性质**：review-grade 补丁清单。`docs/manuscript/` 只读，本文件**不修改正文**，
只逐条给出「原文位置 → 为什么错 → 替换文字 → 证据」。

**为什么需要它**：第 10–22 轮的执行证据已经推翻了正文中的若干表述，但正文自
2026-10-15 起未再更新。审稿人只要查三处（摘要的天花板分类、§7.1 的 IIIa 类、
§1.1 的"no prior study"）就会触发 desk reject。这份清单让 owner 可以在一次
编辑会话内完成修订，而不必重读 22 轮记录。

---

## P1 — 必改（不改会被一击即中）

### P1-1 摘要：三个"真实结构天花板"已被自家实验否证

- **位置**：`docs/manuscript/manuscript.md:43`（Abstract → Results），
  同句在 `:115`（§1.2 贡献列表）、`:1230`（§7.1 表 IIIa 行）重复。
- **原文**：「3 families at genuine structural ceiling (QFT, GHZ, SurfaceCode;
  no tested compiler reduces them)」。
- **为什么错**：
  - E48（2026-10-20）用 4 个外部优化器跑 96 个真实源：QFT **2/2 被击破**
    （34→31、148→127），SurfaceCode **1/8 被击破**（`surface_code_8` 10→8，
    pyzx `full_reduce`，酉等价已验证）。只有 GHZ 保持 0/1。
  - E53（2026-10-22）用 BQSKit 复核：SurfaceCode 8/8 与 QFT 2/2 **恰好等于**
    认证代价——即"没有人更低"在 BQSKit 上成立，但 E48 的 pyzx 反例仍在。
  - E50（2026-10-21）进一步给出 BV 的 h\* 随 n 增长，说明"天花板"是视野的函数。
- **替换文字（建议）**：
  > ... and ~0% on the remainder — **one family at a library-relative ceiling
  > (GHZ; no tested compiler or ZX reducer lowers it, and `GHZ_n >= n` in any
  > 1-/2-qubit gate set), one family with a partial counterexample
  > (SurfaceCode, 1 of 8 sources beaten by pyzx), and QFT reclassified as
  > reducer-dependent (2 of 2 sources beaten by pyzx, but matched by BQSKit)** ...
- **证据**：`docs/review/science_boost/2026-10-20_external_falsifier/`、
  `2026-10-22_bqskit_tzap/`；结论汇总见 `science_boost/README.md` 的 10-20、10-22 行。

### P1-2 §1.1 与摘要的"no prior study"不可辩护

- **位置**：`:57`（§1.1 第二段）。
- **原文**：「no prior study has, to our knowledge, systematically characterized
  *when* these passes succeed...」
- **为什么错**：2026 年至少有五篇同题论文，且 2013 年已有先例：
  `2609.29406`（pass order）、`2609.29210`（representation-dependent
  recoverability，含熵下界）、`2610.06142`（equivalent circuits lose synthesis
  choices，360/360 条件）、`2601.19738`（Q-PreSyn，local edits）、
  `1305.0810`（2013，已用 ≤4 输入最优 Clifford 电路做 peephole，削减约 50%）。
- **替换文字（建议）**：把"no prior study"改为一句划界：
  > Representation dependence itself is now documented
  > [2609.29406, 2609.29210, 2610.06142, 2601.19738]; what is not, is a
  > **decidable** criterion for the reorder axis and a **counted** price for the
  > content axis. This paper supplies both (`DF-5`, `EX-1`, `PR-1`, `E91`).
- **证据**：`docs/review/science_boost/2026-11-04_literature_scan/`；
  `docs/references/reference_additions_2026-10-17.md` §E。

### P1-3 摘要中的 v15 计数已被 v16 取代

- **位置**：`:43`（「94 exact best costs (93 enumerated certificates plus one
  IDA*-derived)」）、`:444`。
- **为什么错**：`release/v16_readiness_verdict.json`（as_of 2026-10-25）为
  **93 exact + 34 witness-bounded + 1 resource-bounded**，分类 127/128；
  引擎 successor-generation 修复后 v14/v15 不再字节可再生。
- **替换文字**：按 v16 三个 tier 重写，并注明 producing engine version
  （verdict 的 `paper_status` 已要求这一点）。

---

## P2 — 应改（决定论文能否过方法学审稿）

### P2-1 摘要的方法/结果顺序

- **位置**：`:41`（Methods）在 `:43`（Results）之前，但 Results 里先给结论再给
  方法学描述。第 10 轮已记录。**处置**：把 Methods 段压到两句（语料 + 引擎版本），
  把 engine version 与 rule scope 提到 Results 首句。

### P2-2 价格数字必须带三个限定词

- **位置**：全文任何引用"完备性价格"的句子（当前正文尚未引入该概念，
  但 §7.6 的未来工作会引用）。
- **规则**（已写入 `docs/reproducibility.md` 的「Rule-library reporting rule」）：
  每个价格数字必须同时报告 **(generator set, maximal source length in the scope
  actually used, cost-delta profile)**。
- **本条新增的两个事实**（2026-11-04）：
  - 认证景观跑在 `e44_core_v1` 上，该 scope 的**最大源长度是 4**（长度 2/3/4 分别
    12/32/105 条，长度 5 为 0），而"库预算 5"说的是 1,474 条全库。混用会把
    "差 5 级"变成"差 6 级"或反之。证据：E90 `summary.json` `firing_by_source_length`。
  - 价格的对照量"局部不可约比例"与价格**无序**：E87 在 (m=6, L=5) 的价格是
    4.03%，而 E91 的局部不可约比例是 5.26%——只有当搜索契约允许零代价动作时
    才可能（E75 `actions_for(strictly_reducing=False)`）。

### P2-3 §7.5 Limitations 需补四条

- **位置**：`:1263`（§7.5 Limitations）。
- **补 1（real_qpu 重新分类）**：全部结论都是门数陈述；门数与保真度在 4–20 比特、
  10²–10³ 门规模上不单调（E48 已量）。一次 QPU 运行能验证的只有等价性，
  而等价性已由 MQT QCEC 128/128 外部验证（E59）。建议写
  "`real_qpu` is out of scope for this paper's claims, not pending"。
- **补 2（视野 vs 库）**：`best_cost_at_h3` 是 horizon-relative **且**
  library-relative；库相对性现在有定理（`T-9`）与数字（E87 56.07% @ L=5）。
- **补 3（内容轴在真实面板上饱和）**：E90 —— 38,118 个冻结窗口中，
  19,303 个有可约动作，**其最小源长度 100% 为 2**；149 条声明 scope 规则中
  只有 37 条曾经触发，其中 2 条以可约方式触发。所以"长度预算"在**本项目的
  基准上**不是约束。
- **补 4（3.5% 的逃逸是零代价优先）**：699/20,002 个 EXACT_ESCAPE 窗口在根状态
  上**没有任何可约动作**——它们必须先走一步零代价动作。这是 `EX-1` 的跨度律
  在动作层的直接签名，也是"horizon 是自变量"的最干净证据。

### P2-4 §7.1 的 IIIa/IIIb 分类表需要重新标注口径

- **位置**：`:1230`（表 7/10/12 的 IIIa 行）。
- **处置**：IIIa 从 3 个族缩到 1 个（GHZ）+ 1 个部分（SurfaceCode）；
  QFT 移出。并在表注写明"ceiling 是 (gate set, reducer set) 的函数"——
  `2510.20730` 已证明在可编程全连接多比特纠缠门下任何 Clifford 序列代价 ≤4，
  所以 `GHZ_n >= n` 是 **(circuit, 1-/2-qubit gate set)** 的陈述，不是电路的陈述。

---

## P3 — 可选（提升可读性，不改结论）

| # | 位置 | 处置 |
|---|---|---|
| P3-1 | `:545` 图 1 说明 | "phase transition is absent" 保留，但加一句"the figure is retained as the record of a refuted hypothesis" |
| P3-2 | `:1237` 术语历史注 | 保留；它已经写得比大多数论文的 negative result 更诚实 |
| P3-3 | `:1185` | "94 exact" → v16 三 tier |
| P3-4 | 全文 | 删除一切"首次/首个"；`LF-C1` 的 `Θ(n²/log n)` 是文献（`2607.22248`），不是本项目结果 |

---

## 执行顺序建议

1. P1-1 → P1-3（同一段，一次改完）。
2. P2-3 补 1/补 3（都在 Limitations，一次改完）。
3. P2-2 规则段（新增一段，位置在 §5.4 之后）。
4. P2-4 表注。
5. P3 扫尾。

**不要**在完成 P1 之前提交任何版本：P1-1 是自家数据否证自家摘要，
这一条被审稿人发现的性质与"数据不支持结论"相同。

---

## 执行记录（2026-11-07，owner 授权执行）

全部补丁已应用到 `docs/manuscript/manuscript.md`（diff：+49/−33 行，其后
追加执行中的补充）：

| 补丁 | 状态 | 备注 |
|---|---|---|
| P1-1 | ✅ 已应用 | 摘要 `:43` 与 §1.2 `:115` 两处；§7.1 IIIa 段与表 9b 行同步重写（P2-4 一并完成） |
| P1-2 | ✅ 已应用 | `:57` 改为划界句；引用按项目惯例列 arXiv id，另加 `2608.27592`（round-23 新必引） |
| P1-3 | ✅ 已应用 | 摘要与 §6.12 前段（`:440-445`）都改为 v16 三层计数（93/34/1；127+1），注明引擎修复与重钉 |
| P2-1 | ✅ 已应用 | Methods 压缩为语料句；引擎版本与冻结 scope 在 v16 句中给出 |
| P2-2 | ✅ 已应用 | 新增「Reporting rule」段（§5.4 开头），含三条限定词 + 两个 2026-11-04 事实 |
| P2-3 | ✅ 已应用 | Limitations 新增 6–10 条（real_qpu 重分类、视野 vs 库、内容轴饱和、3.5% 序优先、review-grade 边界） |
| P2-4 | ✅ 已应用 | IIIa → GHZ（1）+ SurfaceCode 部分 + QFT 改判；表注给出 (gate set, reducer set) 依赖与 `2510.20730` |
| P3-1 | ✅ 已应用 | 图 1 说明加 "retained as the record of a refuted hypothesis" |
| P3-2 | ✅ 保留原样 | 术语历史注按清单建议不动 |
| P3-3 | ✅ 已应用 | `:1185` 段改为 v16 三层（69/58、127+1、93/34/1） |
| P3-4 | ✅ 已应用 | "first systematic" → "a systematic"；全文无"首次/首个"声明残留 |
| 清单外修正 | ✅ 已应用 | E46 单率表述（"123 greedy roots 37.2%"）→ v16 双分层口径（23 roots 39.71% 零 depth-1 / 50 raw roots 57.81%、97.9% depth-1）；39,474 → 39,572——这是 round-16 D3 撤回的表述，按 PROJECT_STATUS 的报告义务修正 |
| 清单外新增 | ✅ 已应用 | 状态横幅 `:27` 更新为 2026-11-07 执行记录 + v16 现行计数 |

**未做（登记为后续写作任务，不属于补丁清单范围）**：certified-era 主线
（两轴划分、完备性价格、窗口分层、E95/E97/E98/E99）尚未整合进正文章节；
这是新的写作会话，不是补丁。摘要的 v16 句之后未再加 round-24 内容，
保持补丁的手术式边界。
