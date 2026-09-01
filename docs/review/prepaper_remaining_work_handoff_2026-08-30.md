# Q-research 论文前剩余工作交接计划

生成日期：2026-08-30（Asia/Shanghai）  
项目根目录：`D:\Desktop\Q-research`  
用途：将“论文撰写前的全部未完成工作”移交给另一个 agent。本文是执行合同，不是完成证明。

## 0. 可直接交给下一位 agent 的总任务

> 在 `D:\Desktop\Q-research` 中继续完成论文撰写前审计。先阅读根目录 `AGENTS.md`、本交接文档、`docs/review/metric_evidence_registry_2026-08-26.json`、`docs/review/metric_audit_ledger_2026-08-24.csv` 和 `docs/review/metric_audit_summary_2026-08-24.json`。不得撰写论文正文，不得删除或重置现有工作树，不得修改已封存 E31 的输入、结果、协议或结论。以 592 项逐指标台账为唯一完成口径：每项只能用直接、哈希固定、机器可检查的证据升级；不能把邻近指标、文件存在、结构相似或测试通过冒充该指标通过。先完成正在收尾的分层归档恢复测试，再稳定源代码，运行完整测试、工作区扫描、SBOM 和最终发布清单验证，最后逐项关闭所有可本地关闭的 PARTIAL/FAIL，并把确需用户、外部研究者、真实 QPU 或投稿平台的项目保留为 EXTERNAL/FAIL，附明确 actor/action。固定面板结论只作描述；15 家族层结果只作支持性推断；未见家族泛化在真正外部家族证据出现前保持 BLOCKED。完成后输出新的 592 项状态计数、每项证据链和“可进入论文写作/仍不可进入”的终审判定。

## 1. 当前权威状态

权威来源是当前逐指标台账，不是旧报告或聊天摘要：

| 状态 | 数量 | 含义 |
|---|---:|---|
| PASS | 173 | 已有逐指标、机器可检查的满足证据 |
| PARTIAL | 340 | 有部分证据或范围受限；其中大量仍缺逐指标 selector/predicate |
| FAIL | 45 | 当前未满足 |
| NA | 29 | 在已声明研究模型下不适用；不得无理由改成 PASS |
| EXTERNAL | 5 | 需要外部主体、外部平台或投稿前时点动作 |
| 合计 | 592 | 必须始终保持目录映射一一对应 |

当前文件指纹：

- 原始 592 项指标目录 SHA-256：`eb5f039ae5cfcd97e205afae9febb25f7b69bd52e57f4af4cdb8997d0393d36b`
- registry SHA-256：`4a137a72da55b122340ee86f36c4acfd0947dd37747cab5c97728ba8ad32b7a6`
- ledger SHA-256：`0acdc975a1bdb17a7bec44ebdb794fb2bf73783a50e9908d6f51935c8a911302`
- 当前 Git HEAD：`d463d7a04ae22ec3ee9df9c97166ce5f007b36c0`
- 当前工作树：约 281 个状态条目，包含用户和本轮已有工作；严禁 reset、clean、checkout 覆盖或未经授权提交。

重要：当前台账生成于归档恢复测试完成之前。若 15.41 真正通过并被正确登记，预期至少变为 PASS 174、FAIL 44；必须以重新生成后的结果为准，不能手工改计数。

## 2. 运行环境与恢复方法

### 2.1 已实测主机

- OS：Microsoft Windows 11 专业版，`10.0.26200`，64 位。
- CPU：11th Gen Intel Core i7-11370H @ 3.30 GHz，4 核 / 8 逻辑处理器。
- 可见内存：16,555,320 KB，约 15.79 GiB。大型并行任务需保守设置，避免内存交换影响计时。
- 时区：Asia/Shanghai。
- 当前可用终端：PowerShell。
- Git：`C:\Users\Administrator\scoop\shims\git.exe`。
- 根 `AGENTS.md` 留存的 `C:\Program Files\Git\bin\bash.exe` 在本机当前实测不存在；不要假设 Git Bash 可用。若另一个主机有 Git Bash，可使用 POSIX 路径，但命令语义必须保持一致。
- Docker：当前 PowerShell PATH 中未检测到 `docker`；不要把 Docker 当作现成依赖或把 Docker 缺失误报为研究失败。
- Node：`v24.16.0`，本项目主验证链不依赖 Node。
- 当前宿主 PowerShell Core：7.6.4；Git：2.55.0.windows.3。

### 2.2 Python 与依赖

- Python：`D:\Downloads\miniforge3\python.exe`
- Python 版本：3.12.12
- uv：0.11.28
- 直接依赖：`requirements.txt`
- 哈希锁定依赖：`requirements-lock.txt`
- 关键当前版本包括 Qiskit 2.4.1、PyZX 0.10.5、Cirq 1.6.1、pytket 2.18.0、qiskit-aer 0.17.2、qiskit-ibm-runtime 0.47.0、pytest 8.2.2。

在新环境中优先创建隔离环境并严格按锁文件安装。不要原地升级当前环境来“修复”版本矩阵：

```powershell
cd D:\Desktop\Q-research
uv venv .venv-handoff --python 3.12
.\.venv-handoff\Scripts\python.exe -m pip install --require-hashes -r requirements-lock.txt
```

如果 `pip --require-hashes` 与 `uv` 的当前接口不兼容，可用 `uv pip install --python .\.venv-handoff\Scripts\python.exe --require-hashes -r requirements-lock.txt`；必须记录实际命令、解析版本和失败信息。

### 2.3 每次开始前的只读现场检查

```powershell
cd D:\Desktop\Q-research
git rev-parse HEAD
git status --short
& 'D:\Downloads\miniforge3\python.exe' --version
uv --version
Get-FileHash -Algorithm SHA256 docs\review\metric_evidence_registry_2026-08-26.json
Get-FileHash -Algorithm SHA256 docs\review\metric_audit_ledger_2026-08-24.csv
Get-Content -Raw docs\review\metric_audit_summary_2026-08-24.json
```

如果上述 SHA 或状态与本文不同，先确定是前一 agent 的合法进展还是意外漂移。不要回滚未知变化。

## 3. 不得破坏的科学边界

1. 固定实验面板只能支持该面板上的描述性结论。
2. 15 个 circuit-family cluster 的推断只属于支持性 family-level inference；小簇数意味着离散置换分辨率与较弱外推能力。
3. 对真正未见 generator/family 的泛化仍为 BLOCKED，除非新增严格外部家族并冻结协议。
4. structural gate multiset、Jaccard 或规范化结构一致不等于量子语义 fidelity。
5. 超过精确矩阵预算的验证必须 fail-closed，并明确标注 sampled/approximate/unavailable，不能默认 valid。
6. timeout、error、invalid 必须进入 ITT 分母。
7. 真实 QPU 的 duration、calibration、queue、drift、crosstalk、shots 和 pulse 结论在没有真实硬件运行记录前不得声称已完成。
8. 不得修改已封存 E31 的输入、28,152 行结果、随机种子、预算、主协议或事后美化结果。允许新增独立验证器和只读派生分析。
9. 不得开始论文正文；项目目标是先把证据链与边界做到最好。

## 4. 已完成且不应重跑的昂贵工作

除非验证发现哈希损坏，否则不要从头重跑：

- E31 全因子正式运行：28,152 行，已有封存检查点、环境和独立语义证书链。
- E12 跨环境面板：560 项。
- 编译器版本矩阵：7 个隔离环境、15 家族、105 项；105/105 QASM 独立语义回放通过。
- held-out v2：16 个家族；仍受“非真正未见生成器”边界约束。
- native semantic verification：6,858 个单元，含 20,314 个 row certificate 和 6,858 个 QPY 输出。
- PyZX 外部方法审计、共享外部比较、硬件代理 48 个单元。
- 编译器版本矩阵现有版本对：Qiskit 2.3.1/2.4.1、Cirq 1.6.0/1.6.1、pytket 2.17.0/2.18.0、custom-current。

如需验证这些工作，运行现有 verifier，不要重做正式实验。

## 5. 第一优先级：完成 15.41 分层归档恢复

### 5.1 当前现场

- 内层冻结清单：`release/prepaper_capsule_inner_manifest.json`
- 归档：`release/prepaper_restore_capsule.zip`
- 当前大小约 82.37 MB。
- 内层清单约 9.76 MB，包含 34,682 个成员条目及清单本身。
- 已纳入 6,858 cell JSON、20,314 row certificate、6,858 QPY、必要的冻结 verifier 与传递源依赖。
- `release/prepaper_archive_restore_audit.json` 在本文生成时仍不存在。
- 一个无输出的独立 restore-and-verify 进程仍在运行；“进程存在”不等于 PASS。

### 5.2 执行步骤

1. 先查看是否已有活动中的 `archive_restore_audit.py`；不要并发启动第二个同目标写入进程。
2. 若现有进程已退出且没有 receipt，读取完整错误并修复闭包，不能降低检查标准。
3. 若需要重新运行：

```powershell
cd D:\Desktop\Q-research
& 'D:\Downloads\miniforge3\python.exe' scripts\archive_restore_audit.py `
  --manifest release\prepaper_capsule_inner_manifest.json `
  --archive release\prepaper_restore_capsule.zip `
  --audit release\prepaper_archive_restore_audit.json `
  --python 'D:\Downloads\miniforge3\python.exe'
```

4. receipt 必须实际包含 `PASS_LAYERED_ARCHIVE_RESTORE_TEST`，且恢复发生在新临时目录中，不能偷读原工作区。
5. 在 `scripts/merge_metric_registry_fragments.py` 中为 15.41 添加直接 overlay：receipt 的 SHA、JSON selector 和严格状态断言。
6. 重新生成 registry/ledger，并用独立 verifier 复核。
7. 保持两层模型：内层清单冻结 ZIP 内容；外层当前发布清单只固定内层清单、ZIP 和 restore receipt。不得制造清单自指循环。

### 5.3 验收标准

- receipt 存在、哈希稳定、状态严格 PASS。
- 解压目录可以完全离线验证清单、关键结果和语义证书。
- 15.41 在新 ledger 中从 FAIL 升为 PASS，且不是通过共享证据或手工改 CSV。
- `tests/test_archive_restore_audit.py` 通过。

## 6. 第二优先级：稳定源代码后的统一验证链

顺序很重要：源代码一旦再改，相关 source-bound receipt、SBOM 和发布清单都要重做。

### Phase A：目标化验证

```powershell
cd D:\Desktop\Q-research
& 'D:\Downloads\miniforge3\python.exe' analysis\compiler_version_sensitivity_audit.py --skip-execution
& 'D:\Downloads\miniforge3\python.exe' analysis\compiler_version_sensitivity_verifier.py
& 'D:\Downloads\miniforge3\python.exe' analysis\hardware_routing_overhead_audit.py
& 'D:\Downloads\miniforge3\python.exe' -m pytest `
  tests\test_compiler_version_sensitivity_audit.py `
  tests\test_compiler_version_sensitivity_verifier.py `
  tests\test_hardware_routing_overhead_audit.py `
  tests\test_archive_restore_audit.py -q
```

如脚本 CLI 与无参数调用不一致，先运行 `-h` 并使用脚本声明的参数；不得猜测输出路径。

### Phase B：完整测试

```powershell
& 'D:\Downloads\miniforge3\python.exe' -m compileall -q analysis experiments scripts src tests
& 'D:\Downloads\miniforge3\python.exe' -m pytest -q
```

旧的“341 passed”只是历史基线，不能作为当前完成证明。当前新增了多组测试，必须记录新的总数、用时、失败和 timeout 分类。

### Phase C：SBOM 与可能改变文件的其他审计

```powershell
& 'D:\Downloads\miniforge3\python.exe' scripts\generate_sbom.py
& 'D:\Downloads\miniforge3\python.exe' scripts\verify_sbom.py
```

SBOM 必须在源和依赖稳定后重建；当前 `release/sbom.cdx.json` 是早期产物，不能直接当最终证明。

如果引用或外部链接文件发生变化，再运行：

```powershell
& 'D:\Downloads\miniforge3\python.exe' scripts\audit_external_links.py --live --strict
```

网络不可达与证据本身失败要分别记录。不要用临时网络故障证明文献不可靠。

### Phase D：最终稳定工作区扫描

必须在完整测试、SBOM、外链检查及所有其他会写文件的审计之后运行，否则新生成的缓存、日志或审计文件会落在扫描边界之外：

```powershell
& 'D:\Downloads\miniforge3\python.exe' scripts\audit_workspace_coverage.py --workers 16
```

如果内存压力明显，降低 workers 并记录；不得为了速度缩小扫描目录。验收包括工作区文件清单、目录清单、不可读文件为零或有明确例外。

### Phase E：registry、ledger 与最终外层发布清单

先查看脚本 `-h`，然后按现有默认路径运行：

```powershell
& 'D:\Downloads\miniforge3\python.exe' scripts\merge_metric_registry_fragments.py
& 'D:\Downloads\miniforge3\python.exe' scripts\generate_metric_audit_ledger.py
& 'D:\Downloads\miniforge3\python.exe' scripts\verify_metric_audit_ledger.py
& 'D:\Downloads\miniforge3\python.exe' scripts\generate_prepaper_release_manifest.py
& 'D:\Downloads\miniforge3\python.exe' scripts\verify_prepaper_release_manifest.py
```

若实际 ledger 脚本名称不同，以 `scripts` 目录和现有测试中的真实调用为准，并把最终命令补回本文。验收要求：592 行、无重复/遗漏 metric_id、目录 SHA 匹配、所有 selector/predicate 成功、嵌套审计哈希成功、外层清单不自指。

## 7. 全部 45 个当前 FAIL：处置计划

### 7.1 可由本地 agent 继续建设或审计

| 指标 | 缺口 | 最小合格交付物 |
|---|---|---|
| 4.30 | 参数化门、部分初始化、observational equivalence 理论边界 | 明确定义范围；反例或定理/命题；可执行测试；不得从 unitary-only 直接外推 |
| 5.28 | MQT Bench 跨抽象层对齐 | 冻结版本、许可证、输入哈希、抽象层映射、ITT 结果和语义验证 |
| 5.29 | Benchpress 风格大型软件压力测试 | 预先冻结规模层、超时/内存上限、失败分类、time-to-solution；不得用 smoke test 代替 |
| 13.12 | 跨 qubit 范围外推 | 严格在训练 4–10 之外的面板，例如 >10 qubits；预先声明无法精确验证时的 fail-closed 路径 |
| 13.13 | 跨 topology 泛化 | 至少两个冻结耦合图族，配对输入与相同 routing 预算，报告 native 2Q/depth/失败率 |
| 13.14 | 跨 compiler version | 现有 7 环境/105 项应能把 FAIL 至少更新为有界 PARTIAL；建立直接逐指标 overlay，不能声称广泛泛化 |
| 13.17 | 真实世界电路 | 引入可追溯真实应用来源、许可证和 provenance；与自定义生成器分层报告 |
| 16.15 | parameterized circuits | 参数绑定前后语义、符号或多点采样协议、反例门、可复现结果 |
| 16.16 | 硬件感知目标 | 现有代理硬件结果可支持有限 PARTIAL；若追求 PASS，需冻结硬件目标与公平对照 |
| 16.18 | fault-tolerant T 资源 | 明确 Clifford+T 转换、近似精度、T-count/T-depth/logical qubits 与有效性 |
| 16.23 | 所有工具版本更新后的机制结论 | 现有版本矩阵只能支持所测版本；增加覆盖或保持 PARTIAL 边界 |
| 17.29 | 删除自定义 benchmark | 用外部/真实面板重跑核心对比并保持同一 estimand |
| 17.30 | 只看真实线路 | 真实线路子集的独立估计、区间、最坏家族和 ITT |
| 18.04 | 第三个可执行独立强工件 | 选择与现有两套方法不同且可执行的外部方法，固定版本/配置并审计语义 |
| 18.06 | 大型线路层级 | 预注册规模、资源预算、验证层级和 failure accounting；不能缩成小样本 smoke test |
| 18.07 | 参数化线路等价 | 与 4.30/16.15 联合建设，但必须有独立逐指标证据 |

### 7.2 需要新增 telemetry，不能从封存总耗时倒推

- 9.52 time-to-first-valid。
- 9.53 time-to-best。
- 10.07 energy consumption。
- 10.08 monetary cost。

这些指标不能从现有总 runtime、CPU time 或云价目表伪造。若做新实验，先冻结事件级 trace schema、采样时钟、能耗/成本口径和失败处理；封存 E31 不得补写事后不存在的时间点。

### 7.3 真实 QPU / 外部硬件平台缺口

- 13.15 跨硬件平台泛化。
- 14.06 calibration 时间。
- 14.10 idle time。
- 14.11 crosstalk-sensitive concurrency。
- 14.16 至少一个真实 QPU。
- 14.17 多日期重复硬件实验。
- 14.18 随机化执行顺序抵御 drift。
- 14.20 shots 数由精度目标决定。
- 14.27 depth 更短但 crosstalk 更强。
- 14.28 queue time 与纯执行时间。
- 14.29 end-to-end time-to-solution。
- 14.33 pulse-aware 编译。

没有用户提供的 QPU 账户、预算、目标设备和授权时，这些保持 FAIL/EXTERNAL，并准备一份可直接执行的冻结协议即可；不要索取、记录或提交密钥。

### 7.4 需要人类/外部主体或用户授权

- 1.19：非开发者或新机器完成独立冷启动复现。
- 3.30：匿名同行 novelty red-team。
- 13.16：独立研究组数据。
- 16.19：真实用户或外部研究组需求。
- 16.20：外部复用证据。
- 17.19：独立研究者攻击 theorem。
- 17.21：外部工具作者检查配置。
- 15.28：干净机器验证。
- 15.29：非作者验证。

本地 agent 可以准备归档、说明、复现表单和验证命令，但不能冒充独立主体。

### 7.5 需要用户决策或发布权限

- 15.09 数据许可证：需要权利人选择兼容许可证；agent 不得替用户作法律/授权决定。
- 15.10 DOI/Zenodo：需要用户账户和公开发布授权；上传前必须确认发布边界。
- 15.40 固定 commit 重建 release：当前工作树约 281 个状态条目；在用户明确授权提交并给出候选 SHA 前不能完成。
- 15.41 archive restore：本地正在收尾，按第 5 节处理。

## 8. 全部 5 个 EXTERNAL：处置计划

| 指标 | 必需 actor/action |
|---|---|
| 1.20 新颖性碰撞风险 | 投稿前由独立审阅者按冻结检索协议做 novelty red-team；记录日期、库、检索式和判断 |
| 3.12 listing/order sensitivity 直接实验 | 当前 E31 很可能已有直接证据；先审计为什么 registry 仍标 EXTERNAL。若是分类/绑定错误，添加逐指标 selector；若问题指外部文献，则保持外部文献审查边界 |
| 8.35 外部作者核查运行配置 | 向被比较工具作者提供版本、commit、CLI、预算和输入哈希，归档其确认或异议 |
| 18.09 独立冷启动复现 | 把分层归档交给非作者/新机器，完整记录从空环境到主要表图/验证 receipt |
| 18.12 预投稿最新文献刷新 | 只能在真正投稿前执行；冻结检索日期、数据库、查询、纳入排除和最近 6–12 个月结果 |

## 9. 340 个 PARTIAL 的闭环方法

不能逐批“共享证据”升级。当前按 section 的 PARTIAL 数为：

| Section | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 | 13 | 14 | 15 | 16 | 17 | 18 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| PARTIAL | 11 | 7 | 27 | 25 | 30 | 32 | 12 | 28 | 9 | 11 | 24 | 15 | 3 | 14 | 38 | 24 | 24 | 6 |

其中当前 residual 粗分：211 项缺 item-specific satisfaction evidence；32 项缺能证明完整问题的语义 selector/assertion；16 项已有明确 claim boundary 但残余工作未完成；另有一批台账仍写着“E31 未封存”，这与当前事实可能已经过时，必须刷新而不是直接升级。

对每一项 PARTIAL 依次执行：

1. 读取该行 `metric`、`criterion`、`observed_value`、`scope`、`residual` 和 `evidence_refs_json`。
2. 判断属于：科学实验缺口、理论缺口、报告/统计缺口、证据绑定缺口、外部动作或确实 NA。
3. 若现有证据已直接回答该指标，添加唯一 metric_id、文件 SHA、稳定 selector 和可执行 predicate。
4. 若证据只回答一部分，保持 PARTIAL，并把 residual 改成具体可执行动作，禁止通用模板句。
5. 若需要新实验，先冻结 protocol、estimand、分母、失败口径、随机种子和停止规则，再运行。
6. 每批最多处理一个逻辑主题；增加回归测试，重新 merge/generate/verify 592 台账。
7. 每批记录状态净变化和为何升级/不升级。

推荐处理顺序：

1. 清理已完成但 registry 未绑定的 E31、编译器版本、held-out、硬件代理与 archive 指标。
2. 统计与 verifier 类缺口（sections 7、9、11、12）。
3. 基线公平性和外部比较（sections 5、8、17、18）。
4. 泛化和规模层（sections 13、16、18）。
5. 开放科学、发布与独立复现（section 15）。
6. 真实 QPU 与外部 actor 项最后保留为明确外部门。

## 10. 证据登记的最低格式

任何状态升级至少包含：

- 唯一 `metric_id`；
- criterion source 与目录文本 SHA；
- 一个或多个具体 evidence 文件 SHA-256；
- 稳定 selector（JSON pointer、CSV required columns + row predicate、文本锚点或独立脚本断言）；
- predicate 的实际结果；
- observed value；
- scope/claim boundary；
- residual（若非 PASS）；
- 对应回归测试。

以下均不足以单独升级为 PASS：文件存在、脚本退出 0、测试总数增加、相邻指标通过、共享 section 报告、结构相似、平均值改善、单个 smoke test。

## 11. 预期执行批次与验收门

### Batch 0：恢复现场

- 确认归档进程状态、保存完整 stdout/stderr、不得重复启动。
- 验收：明确 PASS 或具体闭包错误。

### Batch 1：15.41 与外层发布链

- 完成 restore receipt、15.41 overlay、两层清单。
- 验收：恢复目录完全独立；预计 PASS +1 / FAIL -1。

### Batch 2：已完成工作的 registry 追认

- 审计所有仍写“E31 未封存”或忽略版本矩阵/硬件代理的 PARTIAL/FAIL。
- 特别审计 13.14：105 项版本矩阵已存在但当前仍为 FAIL；这首先是 evidence overlay/ledger 未吸收问题，不是重新跑版本实验的理由。
- 验收：每个升级都有 item-specific predicate；不越过 claim boundary。

### Batch 3：本地可补科学缺口

- 4.30、5.28、5.29、13.12、13.13、13.17、16.15、16.16、16.18、16.23、17.29、17.30、18.04、18.06、18.07。
- 验收：正式实验而非 smoke test；预注册式协议；ITT、语义和资源门完整。

### Batch 4：全套验证与发布候选

- compileall/完整 pytest → SBOM/其他生成型审计 → 最终工作区扫描 → ledger → 外层 manifest → 独立 verifier。
- 验收：所有命令零失败；所有 artifact 哈希闭合；新台账仍严格 592 项。

### Batch 5：外部阻塞清单

- 生成 actor/action/required-input/acceptance-evidence 四列表。
- 验收：没有本地 agent 冒充独立复现、真实硬件或用户发布授权。

### Batch 6：论文前终审

- 输出最终 PASS/PARTIAL/FAIL/NA/EXTERNAL 数量、全部剩余项、核心主张到证据映射和边界。
- 只有核心主张无越界、所有关键 verifier 通过、发布链可恢复，才可建议进入论文写作；不要求把本质上外部或投稿时点的指标虚构成 PASS。

## 12. 停止与升级规则

立即停止并向用户请求授权的情况：

- 需要提交、创建 release commit、推送、公开上传、选择许可证或发布 DOI；
- 需要真实 QPU 账户、付费额度或第三方凭据；
- 需要删除/覆盖用户现有改动；
- 新实验会改变已封存主协议或主要结论；
- 两个合理研究设计会导致实质不同结论且无法由现有目标决定。

可以自主继续的情况：只读审计、增加独立 verifier、添加回归测试、生成派生证据、修复清单闭包、刷新 registry/ledger，以及执行已有冻结协议。

## 13. 最终交付物

接手 agent 完成后至少交付：

1. `release/prepaper_archive_restore_audit.json` 与独立恢复日志。
2. 更新后的 registry、592 行 ledger、summary 及独立 verifier receipt。
3. 当前完整 pytest 结果。
4. 最终 workspace file/directory inventory。
5. 更新并通过验证的 CycloneDX SBOM。
6. 分层归档：inner manifest、ZIP、outer manifest，哈希无循环且可恢复。
7. 每个剩余非 PASS 指标的精确 blocker、actor、action 和所需证据。
8. 一份不含论文正文的 pre-paper readiness verdict。

最终报告必须明确区分：工程验证已完成、科学证据范围、外部/真实硬件门、发布授权门。任何未完成项都必须诚实保留，不能通过改名或降格测试来“清零”。
