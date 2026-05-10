# paperterm dogfood — findings (Stage T5 evaluation)

> 主 agent 对 Stage T4 subagent 产物的人工评估。
> 输入：`example/output/glossary.draft.yaml`（51 concepts，1958 行）+
> `example/output/run_log.md`（subagent 自述）+ 抽样验证 raw paper。
> 评估视角：找 prompt + schema 的真实缺陷，为 plan §12 Phase 1 写
> `src/paperterm/prompts.py` 时减少试错。

## 执行偏差声明

规划 Stage T5 要求主 agent 在跑 subagent **之前**就手抽 3 条 ground truth
seeds 写入 findings.md 顶部，但实际执行时主 agent 直接进入 Stage T4 启动
subagent，待结果回来后才到 T5。所以下面「人工 ground truth seeds」节虽然
是从 raw paper（不是从 yaml）抽取的，但抽取人**已经看过 yaml 摘要**，
seeds 选择可能受先入观影响。

为了部分弥补，seeds 抽自 raw paper 中**最显著的核心术语**（abstract +
intro 头 30 行内 \textbf 加粗或 abstract 直接命名的概念），这类术语任
何阅读了 abstract 的 LLM 都不可能漏抓，污染面较小。

## 1. 人工 ground truth seeds（3 条）

事后从 raw paper 抽取，验证 yaml 命中：

| # | Seed | 来源（raw paper） | yaml 命中 |
|---|------|----------|--------|
| GT1 | **Raw2Event** (dataset) | abstract.tex:3 `\textbf{Raw2Event}`, intro.tex:20 `\textbf{Raw2Event}` | ✓ `id: raw2event_dataset`, `canonical: Raw2Event`, 35 occurrences |
| GT2 | **DAVIS346** (dataset/sensor) | abstract.tex:3,4,7,9,11; intro.tex:20-22 等多处 | ✓ `id: davis346`, `canonical: DAVIS346`, 61 occurrences |
| GT3 | **DVS-Voltmeter** (model) | abstract.tex:9,10; intro.tex:13 | ✓ `id: dvs_voltmeter`, `canonical: DVS-Voltmeter`, 22 occurrences |

**命中率：3 / 3 = 100%**。所有 3 条核心术语都被 subagent 正确归类、给出
权威 canonical、并采集到多 section 的 location 列表。

## 2. 覆盖矩阵（concept × category）

```
abbrev_pair : 12   (CI, EMD, HDR, IEI, ISP, NTP, PDAF, ROI, SDE, TV, AGC, auto_exposure)
dataset     :  8   (Raw2Event, DAVIS346, CIFAR-10, CIFAR10-DVS, DDD17, DSEC, MVSEC, N-ImageNet, 1Mpx)
model       : 11   (DVS-Voltmeter, ESIM, v2e, V2CE, vid2e, SuperSloMo, QKFormer, davis_simulator, dobot_arm, ...)
metric      :  9   (polarity_deviation, count_ratio, dt_emd, iei_tv, px_emd, spatial_entropy_ratio,
                    active_pixel_ratio, top1_accuracy, R@1)
pipeline    : 10   (per_pair_K_calibration, paired_bootstrap_CI, upstream_diagnostic,
                    isp_rgb_stream, raw_bayer_stream, sim_to_real_gap, aedat4_format,
                    april_tag, aps_frames, cifar10_dataset_protocol)
other       :  1   (rgb2event_stream — pipeline-ish but author treats as data product)

TOTAL       : 51
```

paperterm 「值得 lint」的核心场景是 **drift ≥ 3 forms 的 concept**，本
yaml 共 21 条满足（见下节），占 41%。

## 3. drift 分布（form count 直方图，top 10）

| concept id | forms | 备注 |
|---|---|---|
| `per_pair_k_calibration` | **10** | 漂移最严重；abstract / §4 / §6 / appendix D 各种「per-pair K」「per-camera-pair K」「Stage-1.5 K」「polarity-refined K」混用 |
| `upstream_diagnostic` | 6 | "diagnostic" / "scorecard" / "table" / "suite" / "k_health" 等多个名字指同一上游评估表 |
| `pi_camera_module_3` | 6 | "Raspberry Pi Camera Module 3" / "Pi Camera Module 3" / "RPi Cam V3" 等 |
| `metric_px_emd` | 6 | abstract §1 真实例子（plan §1.1 引用）：per-pixel EMD / px-EMD / pixel-level EMD / spatial per-pixel EMD 等 |
| `metric_iei_tv` | 6 | IEI total variation 的多种描述 |
| `metric_dt_emd` | 6 | dt-EMD / Δt-EMD / IEI Sinkhorn EMD |
| `cifar10_dataset_protocol` | 6 | **subagent 标低信心（0.6）** — 应该是两个不同概念（acquisition protocol vs sim-to-real protocol）被错误 lump |
| `raw_bayer_stream` | 5 | raw Bayer / 10-bit raw / pre-ISP raw / ... |
| `metric_count_ratio` | 5 | event-count ratio / count ratio / N̂ / ... |
| `abbrev_tv` | 5 | TV 的多次重复定义 |

**关键观察**：plan §1.1 列举的 paperterm 真实 motivating example
（`per-pixel EMD` 6 种写法）在本 yaml 里**精确复现**：subagent 抓到
了 6 个 form。这强烈支持 paperterm v0.1 的设计假设。

## 4. 行号准确性抽样（12 抽样，10 PASS / 2 FAIL）

抽样方法：从 yaml 抽 3 个高频 concept × 3-5 个 location，去 raw paper
对应行验证是否真的包含该 form。

| concept | 抽样数 | PASS | FAIL | 备注 |
|---|---|---|---|---|
| Raw2Event | 4 | 2 | **2** | (1) `abstract.tex:2` 应为 line 3（off-by-one；line 2 是 "Frame-to-event simulators"，line 3 才是 \textbf{Raw2Event}）；(2) `dataset.tex:12` 实为 `\section{Dataset Description}`（完全错位） |
| DAVIS346 | 5 | 5 | 0 | 全 PASS |
| DVS-Voltmeter | 3 | 3 | 0 | 全 PASS |
| **总** | **12** | **10** | **2** | **错误率 ~17%** |

**关键观察**：错误**集中在 Raw2Event**（35 个 location 中至少 2 个错位），
而 DAVIS346 / DVS-Voltmeter 全对。猜测：

- 短而独特的 token（`DAVIS346` / `DVS-Voltmeter`）容易被 LLM 准确锚定
- 出现在多种语境（`\textbf{}` / 普通 prose / `\section{}` 标题 / appendix）的 token（`Raw2Event`）容易让 LLM 数行错位
- 这正好印证 plan §8.5 比较表里 「Standalone prompt 输出准确度：中（LLM 可能未严格遵循跳过规则）」

paperterm v0.1 真实实现的 ~~anthropic provider~~ (dropped in v0.1; equivalent benefit applies to any future AST-injection path)（plan §6.2）应该用 AST 提取
prose + 在 prompt 注入时**强制**带 absolute line prefix，把行号准确性
从「LLM 自律」变成「机械可验」。

## 5. 跳过规则评估

### 5.1 subagent 主动 drop 的 3 处（已在 run_log.md 记录）

1. `pi_camera_module_3` form `Module~3` @ `dataset.tex:46` — 多行
   commented `\begin{figure}` 内，被识别为 comment，drop
2. `abbrev_isp` form `ISP` @ `intro.tex:16` — 实际是 paraphrase
   "image-processing pipeline"，无字面 ISP，drop
3. `abbrev_isp` form `ISP` @ `intro.tex:35` — 实际是 `ISP-RGB`
   compound，归到 `isp_rgb_stream` concept 避免双计

`count` 都同步 decrement，`count == len(locations)` 一致性 OK。

### 5.2 yaml 噪音 grep

| 检查 | 命令 | 结果 |
|---|---|---|
| 顶层 `bootstrap` 字段 | `! grep -E '^bootstrap:' yaml` | 通过（无） |
| `suggested_canonical` 字段 | `! grep -q 'suggested_canonical' yaml` | 通过（无） |
| 疑似 cite key（如 `Yang2024`） 作为 form | `grep -E 'form:.*[A-Z][a-z]+[0-9]{4}' yaml` | 0 命中 |
| 疑似 LaTeX label / ref 残留 | `grep -E 'form:.*\\\\label\|\\\\ref\|sec:' yaml` | 0 命中 |
| 注释残留（`%` 前缀） | `grep -E "form:.*['\"]%" yaml` | 0 命中 |

跳过规则在抽查范围内**无明显违反**。

### 5.3 chunked input mode 实测

本次 corpus 2200 行 single-pass 走通，**chunked input mode 未实测**。
`prompts/glossary_bootstrap.md`（dogfood 时还在 `example/prompt.md`，P5.D 后已搬到 SoT 位置）后期新增的 chunked 协议（每轮 ACK + 终轮合并 + 跨轮
merge 规则）目前**没有真实运行验证**，留给未来更长论文（如完整 thesis）
的 dogfood 时再压测。

## 6. prompt + schema 缺陷清单

主 agent 综合 subagent run_log.md 与本节抽样发现的**可执行**改进点：

### prompt 缺陷（≥ 3 条）

P1. **manual provider 行号准确性 17% 错误率**（本节 §4 实测）。
    Standalone prompt 模式下，LLM 在 `Read` 工具自带行号 + prompt 文本
    要求 "absolute line prefix" 的双重约束下，仍会在高频 token 上数错。
    **修复方向**：plan §6.2 ~~anthropic provider~~ (dropped in v0.1; equivalent benefit applies to any future AST-injection path) 改用 AST 注入 prose 时
    一定要在每行 prefix 绝对行号；plan §8.5 standalone prompt 必须更
    硬地警告「行号是验收硬指标，宁缺勿错」。

P2. **multi-line `\begin{figure}...\end{figure}` 注释块易遗漏**（subagent
    自评）。「any text from `%` to end of line」是 per-line 规则，但论文
    里整段被注释掉的 figure 环境跨数十行，LLM 容易在第 N 行忘记前 N-3
    行已是 comment。**修复方向**：runner 预处理时按多行块整体剥离 comment
    更稳，比让 LLM 每行自律可靠。

P3. **subscript markup 重复（`\mathrm` vs `\text`）**（subagent 自评）。
    `cnt$_{\mathrm{med}}$` 与 `cnt$_{\text{med}}$` 视觉等同，但 prompt
    "preserve original case" 被解读为也 preserve 原 LaTeX 源，导致同一
    metric 拆成两个 form。**修复方向**：在 prompt skip rules 里追加
    「常见 subscript markup variants 视为同义」一条，或保留分裂但加
    `equivalent_to:` 字段（schema 改动）。

P4. **`\title{}` 是否 prose 不明确**（subagent 自评）。`\title{Raw2Event:
    ...}` 既像 label 又像 prose 的开篇。当前 prompt 没列 `\title` 为
    exempt，但 `\title{}` 内重复出现 paper 名字会让 form count 虚高。
    **修复方向**：prompt 显式列 `\title{}` `\author{}` `\affiliation{}`
    为 exempt（这些位置是元数据不是 prose）。

P5. **「math 用作 prose 名」例外不可机械判别**（subagent 自评）。
    `$|\Delta p|$` 在 abstract 是 metric 名，在 equation 是公式中的项；
    当前 prompt 让 LLM 「judgement」，结果不稳定。**修复方向**：要求
    AST 处理时把 math 块整体 skip，**不**给 prompt 这个例外，由 prose
    文本里的 LaTeX 还原（`$|\Delta p|$` 在 prose 中保留为字面）来覆盖。

### schema 缺陷（≥ 1 条）

S1. **缺 concept overloading 表达**（subagent 强烈反映）。Raw2Event 是
    数据集名 + 模拟事件流名 + 模拟器变体（V01/V02）名三义同体，schema
    没有 `senses:` 子列表或 `related_concepts:` link 字段，subagent
    被迫 lump-or-split。**修复方向**：plan §5 schema 增加可选
    `related_to: [list of concept ids]` 字段，或定义 concept family
    通过 id 前缀约定（`raw2event_dataset` / `raw2event_stream` /
    `raw2event_variant`）。

S2. **缺 `first_mention_idx` 锚定 canonical 来源**（subagent 提议）。
    paperterm linter 想要「全文首次出现的 form 应为定义点」，需要 schema
    给出哪个 location 是 first mention；当前要从 `locations` 列表的第
    0 项推断，跨文件时不严格对齐。**修复方向**：schema 增加
    `first_mention: {file, line}` 可选字段，bootstrap LLM 直接填入。

S3. **`canonical: TBD` 几乎用不到**（subagent 自评）。subagent 处理
    51 个 concept 没用一次 TBD —— abstract 总能给出权威长形式。**修复
    方向**：保留 TBD 作 escape hatch，但 prompt 减少对它的强调。

## 7. 总结

dogfood 验证了 paperterm v0.1 的核心设计假设：

- **schema 整体 fit-for-purpose**：51 concepts 全部装得下；plan §1.1
  motivating example（per-pixel EMD 6 forms）在 yaml 里精确复现。
- **prompt paper-agnostic 真的成立**：worked example 用合成概念，反污染
  grep 严格通过，subagent 没被 example 内的 `mean_pixel_error` /
  `Synthetic-Traffic v2` / `gated_recurrent_decoder` 误导。
- **手抽 ground truth 3/3 命中**：核心术语 LLM 在 200K 上下文 single-pass
  下能准确归类。
- **行号准确性是 manual provider 的真实瓶颈**（~17% 错误率），佐证
  plan §6.2 ~~anthropic provider~~ (dropped in v0.1; equivalent benefit applies to any future AST-injection path) + AST 路径的必要性。

paperterm v0.1 写代码时的具体调整（按 ROI 排序）：

1. **AST 化的 line prefix 注入**（解决 P1，最高影响） — `bootstrap.py`
   走 ~~anthropic provider~~ (dropped in v0.1; equivalent benefit applies to any future AST-injection path) 时强制把每行 prose prefix 成 `<file>:<line>:`，
   消除 LLM 自数行的失误来源。
2. **prompt skip rules 加 `\title{}` `\author{}` exempt**（解决 P4）。
3. **schema 加 `related_to` 字段**（解决 S1）。
4. **多行 `%` 注释块按 AST block-level 剥除**（解决 P2）—— `latex.py`
   walker 实现注意。
5. **subscript markup normalization**（解决 P3）—— 可放在 `linter.py`
   matcher 而非 schema。
6. **schema 加 `first_mention` 字段**（解决 S2，可选；当前 `locations[0]`
   也能用，只是不严格）。
7. 保留 chunked input mode 在 `prompts.py` 的 standalone 版本里（plan
   §8.4 的人工镜像），但 ~~anthropic provider~~ (dropped in v0.1; equivalent benefit applies to any future AST-injection path) 走 AST + 内部 chunking，不
   依赖 LLM 跨轮状态。

本 dogfood 的 yaml 可直接作为 `tests/fixtures/glossary/raw2event_bootstrap.yaml`
的种子（去除 line:0 类残留后），让 v0.1 `paperterm check` 单测有真实
glossary 输入。
