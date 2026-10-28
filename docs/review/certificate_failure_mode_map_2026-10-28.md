# 证书失效模式映射（2026-10-28）

**性质**：review-grade 方法学产物，不在 `release/` 哈希链内。
**用途**：给"逐动作 witness + replay + 引擎源哈希链"这套证书语义一个**外部动机**。
**上游**：`docs/theory/certified_claims_contract_2026-10-25.md`（"certified"的唯一定义）。

---

## 0. 这份文件回答什么

`2609.13839` 报告：酉等价 oracle 会漏掉约 **28%** 的 transpiler 修复（该论文的失效模式分类
**本轮未取回**，因此本文**不**引用其分类，只做机制侧映射）。
`2610.00255` 提出 "assurance contract + evidence"。

本项目的回答不是"我们的 oracle 更强"，而是：**每条会静默改变结论的机制，在证书里都有一个
对应字段，且该字段的缺失会 fail-closed**。下表把九条机制逐条钉到字段与证据上。

> **读法**：第 2 列是"如果没有这个字段，会静默发生什么"；第 4 列是"本项目实测到它的那次实验"。
> 前三条是**本项目自己踩过的坑**（bug 级：直接产生错误输出）；M4–M9 也各有第 4 列的
> 本项目实测反例，但属于评审中发现的方法学缺陷，不是假想的坑。

---

## 1. 九条机制

| # | 静默失效机制 | 无字段时的后果 | 证书字段 | 本项目证据 |
|---|---|---|---|---|
| M1 | **全局相位漂移** | 输出与输入"不等"，或反之被误判为不等 | `equivalence.phase_invariant_overlap`（`\|tr(U†V)\|/d = 1`，**不是** `Operator.__eq__`） | E59：128/128 输出等价，其中 **28/128 只到全局相位**；用 `==` 会报 28 个假失败 |
| M2 | **基/优化等级混行** | 同一 `level` 有两行（frozen / default basis），按 level 过滤会静默取错基，缺陷"消失" | `basis`（`frozen` / `default`）+ `contract_id` | E61：`level_sweep.csv` 每个源有两条 level-3 行；只按 level 过滤时 Qiskit L3 非单调性**看不见** |
| M3 | **隐式 wire swap 被丢弃** | 跨引擎转换后电路"等价"，但实际少了交换门 → 门数虚低 | `transport.implicit_swaps_replaced`（`tk_to_qiskit(..., replace_implicit_swaps=True)`）+ 逐量子比特标签的酉比较 | E58：修前 **13/96** 输出非等价；pyzx 相位以 π 为单位，同样 13/96 |
| M4 | **表示导致的基线通胀** | 削减率的分母被自己的规范化放大，收益虚高 | `baseline.scope`（`source_relative` / `panel_relative`）双口径必报 | D1/E49：Adder 8.30×、VQE 7.25×、QAOA 5.68×；59/96 源"优化后比输入还大" |
| M5 | **分母分层混用** | 用一个层的分母配另一个层的限定词，比率可虚高 3 倍 | `root_kind`（`RAW_*` / `GREEDY_FIXED_POINT`） | D3/E72：76,236 窗口中 73,780 在未优化根上，其逃逸 99.9% 是 depth-1；真不动点上 w16_h3 = 39.7%（23 源） |
| M6 | **资源截断被当作精确** | 截断值被当成最优值写进正文 | `certificate_tier`（`COMPLETE_ENUMERATED` / `EXTRAS_BOUNDED` / `RESOURCE_BOUNDED`），fail-closed | v16 verdict：93 exact / 34 bounded / 1 resource-bounded；E65 证 5 个单元永久封死 |
| M7 | **引擎版本漂移** | 同一输入不同引擎产出不同数，且无法判定谁对 | `engine_source_hashes()` 逐单元钉 + `engine_version` | round 13：successor-generation "last location wins" 缺陷；v14/v15 因此不再字节可再生 |
| M8 | **作用域混淆（窗口 vs 整表）** | 窗口局部结论被写成整表结论 | `scope: window_local \| whole_listing` + 窗口坐标 | v16 `claim_boundary` 明文禁止"whole-listing meaning for window-local profiles" |
| M9 | **规则库/字母表不在证书里** | "最优"相对什么无法复算 | `rule_library_sha256` + `rule_scope` + `alphabet` | 本轮 E75：同一片段的"价格"随 `(arity, L)` 从 30.25% 变到 0.00%，库不钉死则数字无意义 |

---

## 2. 这张表对投稿的用法

- **不要**主张"我们的 oracle 更准"。`2609.13839` 的 28% 是关于**第三方 oracle 的漏检率**，
  与本项目无关；本项目的主张是**字段完备性**：九条机制各有字段，缺字段则 fail-closed。
- **可以**主张：在一个我们自己踩过 M1–M9 全部九条的项目里，每条机制都有对应的实测反例。
  这是"证书设计来自事故，不来自想象"的证据。
- **必须**披露：M1 的 28/128、M3 的 13/96、M5 的 73,780 都是**本项目的**数字，
  不是对 `2609.13839` 的复现。

---

## 3. 仍缺的字段（诚实清单）

1. **无外部时间戳**：证书不带可信时间戳，"先于某工作"无法证明。
2. **无第三方签名**：`qrcert/v1` 是自研验证器，独立重实现仍缺（`external_cold_start` OPEN）。
3. **无硬件层证据**：全部证书止于酉等价，不含噪声模型下的保真度（`real_qpu` OPEN）。
4. **无 oracle 漏检率的自测**：本项目从未测过"若把 witness 换成纯酉 oracle，会漏掉多少"。
   这是 P2-1 唯一还缺的实验，成本约半天（把 E56 的 128 条 witness 换成纯 QCEC 判定，
   看结论是否仍成立）。**本轮未做**，列为 30 天清单第 4 项。
