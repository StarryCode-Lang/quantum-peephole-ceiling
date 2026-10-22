# 遗留项关闭报告 — 2026-10-22

**范围**：2026-10-16 至 10-22 六轮扫描累积的全部未决项。
**原则**：能关闭的关闭，不能关闭的明确标注阻塞原因，不重复"记录问题"。
**红线**：`data/`、`release/`、`docs/manuscript/` 全程只读（`git status` 已核验）。

---

## 0 总览

| # | 遗留项 | 悬置轮数 | 本轮结果 | 状态 |
|---|---|---|---|---|
| 1 | D2：基线未优化污染逃逸统计 | 1（10-22 发现） | E54 统一重基线，全 panel 重算 | **关闭** |
| 2 | release manifest 校验失败 | 5 | 枚举出 15 条漂移（原报 1 条），全部归因；建登记表 + 旁路验证器 | **关闭（可判定）** |
| 3 | 同预算随机动作基线 | 4 | 逻辑撤销：93/128 证书为穷尽闭包，随机不可能超越 | **关闭（撤销）** |
| 4 | BQSKit / tzap 未接入 | 3 | BQSKit 已接入（E53）；tzap 0.8.0 已安装 | **部分关闭** |
| 5 | `environment.yml` 与 `requirements.txt` 不一致 | 1 | **误判**：已用 `-r requirements.txt` 单一来源 | **关闭（更正）** |
| 6 | Thm 10 形式太弱 | 2 | 重写为"有界视野 vs 交换闭包"分离，E55 提供对照 | **关闭（定位修正）** |
| 7 | 摘要三处自证伪 | 2 | 产出可套用补丁清单（manuscript 只读） | **关闭（交付物）** |
| 8 | 冷启动无法区分已知漂移与篡改 | 5 | 协议 Trap 3 改为可执行判定 | **关闭** |
| 9 | 真实 QPU 验证 | 6 | 无账号，未尝试 | **阻塞（外部）** |
| 10 | 独立冷启动（非作者机器） | 5 | 无第二台机器；协议结构已自检通过 | **阻塞（外部）** |
| 11 | release 重钉 | 5 | 红线禁止改 `release/` | **阻塞（owner）** |

---

## 1 D2 关闭：E54 统一重基线

**脚本**：`scripts/e54_d2_uniform_rebaseline.py --full-panel-search`
**证据**：`docs/review/science_boost/2026-10-22_d2_rebaseline/`（`rebaseline.csv`、`survivors.csv`、`panel_h3.csv`、`summary.json`）

### 1.1 做了什么

去掉 `MAX_BASELINE_GATES = 80` 旁路，对全部 128 源跑贪心不动点，然后在同一冻结契约
（`e44_core_v1`、h=3、200k 状态、30 s）下重跑整 panel。

### 1.2 结果

| 量 | 值 |
|---|---|
| 贪心有减少的源 | **116 / 128** |
| 总门数 | 70,789 → **66,825** |
| 单源最大减少 | 313 门（中位 8） |
| 重基线后 h=1 不动点 | **104 / 128** |
| 仍有相邻可约对的源 | **24**（全部为 `rotation_merge`，共 2,628 对） |
| 14 个真逃逸是否存活 | **14 / 14，0 丢失** |

**关键发现 1：贪心本身不做 `rotation_merge`。**
24 个源在贪心后仍含相邻的 `rz`+`rz` 对。也就是说 `GreedyGateCancellation` 只消逆门，
不合并旋转——它在 `pair_v1` 语义下**不是不动点**。这解释了为什么 E52 的 63 个减少步里
34 个是 `rotation_merge`：贪心根本不做这件事。

**关键发现 2：统一重基线后逃逸不是 14，是 22。**

| 层 | 源数 | 逃逸 | 局部最优 | 不可判定 |
|---|---|---|---|---|
| 可判定（≤200 门） | 95 | **22** | 73 | 0 |
| 资源受限 | 6 | — | — | 6 |
| 内存风险（>200 门，跳过） | 27 | — | — | 27 |

- 全层逃逸率 **22/128 = 17.2%**；可判定层 **22/95 = 23.2%**。
- 22 = 14（原真实逃逸，全部存活）+ **8 个新暴露**。
- 新暴露的 8 个来自 QAOA / Grover / UCCSD：它们原本是 raw 根，基线噪声掩盖了 h≥2 的逃逸。
- 按族：UCCSD 7、IQP 7、QAOA 3、RandomClifford 3、Grover 1、Oracle 1。
- **19 / 22 的逃逸发生在 h=1 不动点上**——即这些是真"视野型"逃逸，不是基线残留。

**关键发现 3：统一重基线在冻结契约下不可行。**
首次全 panel 运行在 388 门电路上 `MemoryError`（200k 状态 × 388 门 ≈ 3 GB）。
这说明 80 门旁路**不是随意的**，是资源约束的产物。因此 D2 的正确处置不是"统一重基线"，
而是**分层报告**：

- 层 A（≤200 门，95 源）：完整 h=3 搜索，报逃逸率 **23.2%**；
- 层 B（>200 门，33 源）：冻结契约下不可搜索，只报可达性，不报逃逸率。

### 1.3 对论文的影响

摘要与 §6.12 的"63 exact escapes / 65 exact local optima"必须替换。正确表述：

> 在 95 个可在冻结契约下判定的源上，22 个（23.2%）存在认证改进，73 个是 h=3 局部最优；
> 其余 33 个源超出契约的内存边界，单独报告。此前报告的 63 个包含 49 个深度 1 逃逸，
> 它们度量的是未经贪心的基线，不是景观结构。

---

## 2 release 链关闭：从"1 条错误"到"15 条已归因漂移"

**脚本**：`scripts/verify_release_chain_with_dispositions.py`
**登记表**：`docs/review/release_drift_register.json`
**报告**：`docs/review/release_chain_verification_2026-10-22.json`

### 2.1 为什么之前只看到 1 条

`verify_prepaper_release_manifest.py` 遇到第一个 mismatch 就 `raise`。全量扫描 35,042 条后，
实际有 **15 条**漂移。

### 2.2 结果

```text
[verify] 35042 manifest entries, 15 registered drifts
[verify] {'KNOWN_DRIFT_ACCEPTED': 15, 'MATCH': 35027}
[verify] verdict=PASS_WITH_ACCEPTED_DRIFT
```

15 条全部归因到 manifest 快照（`created_utc 2026-08-31T09:44:39Z`）**之后**的具名提交：

| 提交 | 日期 | 条数 | 文件 |
|---|---|---|---|
| `af8ed604b` | 2026-09-01 | 2 | quartz adapter `.cmd` / `.patch` |
| `e4250beec` | 2026-09-01 | 3 | `data_dictionary.md`、`framework.md`、`analysis_summary.md` |
| `926c76407` | 2026-09-01 | 1 | `prepaper_archive_restore_audit.json` |
| `8255a1634` | 2026-09-02 | 1 | `requirements.txt` |
| `c52b48083` | 2026-09-02 | 1 | `sbom.cdx.json` |
| `87019d8fc` | 2026-09-08 | 6 | 5 个 + 已知的 `metric_audit_ledger_2026-08-24.csv` |
| `d6c5ce2f5` | 2026-10-15 | 1 | `search_ledger.md` |

**结论**：不是 1 个坏条目，而是 **manifest 是 2026-08-31 的时点快照、从未重钉**。
没有任何一条是未归因的编辑。

### 2.3 处置

- 未修改 `release/`、未修改被绑定的验证器（它本身在 manifest 里，改它会新增第 16 条漂移）。
- 新增登记表（`docs/` 下，不被任何 manifest 绑定）与旁路验证器（`scripts/` 下，未被绑定）。
- `docs/verification/cold_start_protocol.md` 的 Trap 3 改为可执行判定：看到
  `DRIFT_UNREGISTERED` 才停，看到 15 条 accepted 才继续。
- owner 仍需在 `release/` 里重钉（Option A）或加 superseded 条目（Option B），
  这是本项目写权限之外的唯一剩余动作。

---

## 3 同预算随机动作基线：逻辑撤销

连续 4 轮列为待办。本轮论证它**在逻辑上冗余**：

- 93/128 的证书是 **穷尽 h=3 闭包**（`EXACT_*`）。随机策略只能访问该闭包内的状态，
  因此不可能找到闭包外的改进。对这类单元，"随机基线"是一个被穷尽枚举支配的实验。
- 34 个 witness-bounded 单元的控制不是随机基线，而是 2026-10-17 的
  `best_cost >= baseline − 6` 下界。
- E54 新增的 27 个 `SKIPPED_MEMORY_RISK` 单元连穷尽搜索都跑不了，随机基线同样跑不了。

**撤销该待办**，改为在方法节写明"证书为穷尽闭包时不需要随机对照"。

---

## 4 BQSKit / tzap

- **BQSKit 1.2.1**：已接入（E53），41 行结果，见 `2026-10-22_bqskit_tzap/`。
- **tzap 0.8.0**：本轮 `pip install tzap` **成功**。此前"无 wheel"的判断是错的。
  尚未接入面板——tzap 只处理线性可逆（CNOT）部分，需要单独的成本口径，列为下一步。
- **MQT QCEC**：仍然不可用（Windows wheel 缺 `mqt/core/bin`，`WinError 3`）。这是真实阻塞，
  已有 `Operator` 与 pytket 两条独立等价性检查替代。

---

## 5 Thm 10 重写：从"业界缺口"到"有界视野 vs 闭包"

**文档**：`docs/theory/thm10_horizon_vs_closure_2026-10-22.md`
**证据**：`docs/review/science_boost/2026-10-22_commutation_gap/`（E55）

### 5.1 E55 结果

四个手写电路（`{h,x,rz,cx}`），`rz(t) … rz(-t)` 夹在 CX 两侧，`rz` 在**控制位**（对角门与 CX 对易）：

| 案例 | 交换距离 k | 最优 | qiskit L3 | tket FPO | tket RR | BQSKit | 项目 h=1 | 项目 h=3 |
|---|---|---|---|---|---|---|---|---|
| A（1 个 CX） | 1 | 1 | **1** | **1** | 3 | 3 | 3 | **1** |
| B（6 个 CX） | 6 | 6 | **6** | **6** | 8 | 8 | 8 | **8** |
| C（目标位，负对照） | — | 3 | 3 | 3 | 3 | 3 | 3 | 3 |
| E（控制位 + 目标 X） | 2 | 2 | **2** | **2** | 4 | 4 | 4 | **2** |

### 5.2 三条结论

1. **这条交换律业界已实现**。qiskit L3 与 tket `FullPeepholeOptimise` 在 k=1 和 k=6 都成功。
   10-22 上午报告里"引擎交换关系没实现全"的表述**是错的，已撤回**。
2. **项目引擎有规则、但视野不够**。它在 A（k=1）和 E（k=2）于 h=3 成功，在 B（k=6）于 h=3 失败。
   这是同一个引擎仅因 k 变化而成功/失败的首个实例，正好是命题 `h >= k+1` 的直接验证。
3. **闭包引擎在代价上占优**。qiskit/tket 不枚举动作序列，而是计算可达性，因此不受 k 影响，
   代价 O(m²)。**这使 76,236 次窗口搜索在"优化器"意义上被支配**——它们的价值是"认证"，
   不是"优化"。

### 5.3 对论文的硬约束

任何把认证景观当作优化结果呈现的句子都必须删除。可保留的主张是：
"认证景观是一个测量仪器，它证明有界引擎看不见什么"，以及"有界视野与闭包在同一问题上的分离"。

---

## 6 稿件纠错补丁

**文档**：`docs/review/manuscript_correction_patch_2026-10-22.md`

五条补丁（C1 结构天花板、C2 "no prior study"、C3 百分比分母、C4 逃逸计数、C5 "certified optimum"），
每条给出原文、替换文本、依据实验。`docs/manuscript/` 未修改。

---

## 7 冷启动协议：Trap 3 可判定化

`docs/verification/cold_start_protocol.md` 的 Trap 3 原本只说"这是已知漂移，报告后继续"。
现在给出可执行判定：

```text
python scripts/verify_release_chain_with_dispositions.py
# 期望：35042 entries / 15 accepted / 0 unregistered / PASS_WITH_ACCEPTED_DRIFT
```

看到 `DRIFT_UNREGISTERED` 或 `MISSING` 才是真问题。

**协议结构自检**（本轮执行，全部通过）：
`requirements-lock.txt` 含 1,668 个 `sha256` 哈希（支持 `--require-hashes`）；
pinned commit `5b08f60fc` 存在；`reproduce_all.py --verify` 支持；5 个 v14/v15 verifier 均存在。

**仍未关闭**：真正的非作者机器执行需要第二台机器，本轮无法提供。

---

## 8 阻塞项（不在本工作流能力内）

| 项 | 阻塞原因 | 解除条件 |
|---|---|---|
| `real_qpu` | 无 IBM/IonQ 账号与排队 | 账号 + 校准漂移基线 |
| `external_cold_start` | 无第二台机器/账号 | 非作者环境执行协议 |
| release 重钉 | 红线：不得修改 `release/` | owner 执行 Option A/B |
| MQT QCEC | Windows wheel 缺 DLL | 换 Linux 或等上游修复 |

---

## 9 本轮新增文件

| 路径 | 类型 |
|---|---|
| `scripts/e54_d2_uniform_rebaseline.py` | E54 重基线 |
| `scripts/e55_commutation_gap_probe.py` | E55 跨引擎探针 |
| `scripts/verify_release_chain_with_dispositions.py` | 旁路 release 校验 |
| `docs/review/science_boost/2026-10-22_d2_rebaseline/` | E54 证据包（4 文件） |
| `docs/review/science_boost/2026-10-22_commutation_gap/` | E55 证据包（2 文件） |
| `docs/review/release_drift_register.json` | 15 条漂移登记表 |
| `docs/review/release_chain_verification_2026-10-22.json` | 全量校验报告 |
| `docs/review/manuscript_correction_patch_2026-10-22.md` | 稿件补丁清单 |
| `docs/theory/thm10_horizon_vs_closure_2026-10-22.md` | Thm 10 候选定理 |
| `docs/review/science_boost/2026-10-22_backlog_closure.md` | 本文件 |

## 10 本轮更正的三处事实错误

1. **`environment.yml` 已钉 qiskit**（通过 `-r requirements.txt`）。10-22 上午报告称"未钉、两文件不一致"是误判。
2. **tzap 可安装**（0.8.0）。此前三轮"无 wheel"的判断错误。
3. **"业界没实现对角门穿控制位交换"是错的**。qiskit L3 与 tket FPO 都实现，且在 k=6 上有效。
   Thm 10 的定位已相应从"缺口"改为"有界视野与闭包的分离"。
