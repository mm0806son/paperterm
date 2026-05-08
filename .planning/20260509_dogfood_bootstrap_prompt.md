## 任务：用 subagent dogfood paperterm bootstrap prompt（无源码端到端验证）

**背景**：paperterm 当前处于 init 之后、源码 Phase 1 之前的状态（`src/paperterm/` / `pyproject.toml` 都还不存在）。但 plan §8.1 已经设计好 standalone bootstrap prompt（即将进入未来 `src/paperterm/prompts.py` 的 `BOOTSTRAP_PROMPT` 常量），plan §5 也设计好了 `glossary.draft.yaml` 的 schema。

在写 Python 代码之前，可以**先用一个 subagent 把这套 prompt 跑一遍真实论文**，验证：
1. prompt 设计是否能产出**符合 schema** 的 yaml（不是泛泛文本）
2. yaml schema 在真实长论文上**是否够用**（哪些字段会缺、哪些字段从未填上）
3. LLM 在跳过 `\cite{}` / `\label{}` / equation / verbatim / `%` 注释时的**自觉性**（manual provider 下 LLM 没有 AST 辅助，要靠 prompt 自约束）
4. 在没有 AST 预处理的 manual provider 模式下，`found_forms.locations` **行号准确性**

**目标论文**：`/vol1/1007/projects/raw2event/doc/paper/`（Raw2Event NeurIPS 2026 D&B paper，~1400 行 .tex 跨 8 个 section + 7 张表 + appendix 子目录）— 是 plan §1.1 描述的「跨 section 多写法」的真实样本。

**为什么有价值**：
- 早 ROI 高：未来真写 `prompts.py` / `bootstrap.py` 时，这次发现的 prompt 缺陷直接 inline 修，省 1 轮迭代
- 真实 ground truth：抽出来的 yaml 可作为未来 `tests/fixtures/glossary/raw2event_bootstrap.yaml` 的种子（即使 schema 后续微调，concept 列表也能复用）
- 验证设计，不验证实现：本任务**不**写任何 paperterm 源码、不创建 `pyproject.toml`、不创建 `src/`

**影响范围**：

```
新建目录：
  example/                                ← 全部 dogfood 产物的根
  example/inputs/                         ← corpus manifest（不拷贝 .tex 主体）
  example/output/                         ← subagent 写出的 yaml + 日志

新建文件（全部 commit 入 git）：
  example/README.md                       ← 这次 dogfood 的目的、输入/输出说明、复现步骤
  example/prompt.md                       ← 实际给 subagent 用的 prompt（基于 plan §8.1 / §8.5）
  example/inputs/corpus_manifest.txt      ← 论文 .tex 文件清单（仅路径与行数，不含正文）
  example/output/glossary.draft.yaml      ← subagent 抽取的术语等价类
  example/output/run_log.md               ← subagent 自己记录的扫描过程
  example/findings.md                     ← 主 agent（我）人工评估 + prompt 缺陷清单

不新建：
  example/inputs/<拷贝的 .tex>            ← 决策：subagent 直接读 ../raw2event/doc/paper/，不拷贝
  src/ tests/ pyproject.toml              ← 留给 plan §12 Phase 1
```

**前置条件**：
- vibe coding init（Stage 0–5）已完成（commit `1d2dbe3`）
- raw2event paper 实际存在于 `/vol1/1007/projects/raw2event/doc/paper/`（已验证：`neurips_2026.tex` + `sections/0[0-7]_*.tex` + `99_appendix.tex` + `tables/*.tex` 总 ~1400 行）
- 用户决策已记录（D-T1–D-T4，见下方「测试决策记录」）

---

### Stage T1：撰写 standalone bootstrap prompt（`example/prompt.md`）

- **目标**：基于 plan §8.1 + §8.5 写一份**自包含**的 prompt，subagent 拿去就能跑：
  - 角色 / 任务说明（来自 `BOOTSTRAP_PROMPT` 设计）
  - YAML schema 完整描述（**严格遵循 plan §5**：顶层 `version`、`concepts` 列表；每个 concept 含 `id` / `category` / `canonical` / `allowed_forms` / `aliases`；bootstrap 阶段额外字段 `found_forms` / `confidence`，并允许 `canonical: TBD` 表示待人工确认）
  - 2–3 个 worked example（metric / dataset / model 各一个，**绝不**用 raw2event 出现过的概念；用合成例如 `mean_pixel_error` / `MNIST` / `ResNet-50` 等通用术语）
  - 显式跳过指令：`\cite{...}` / `\ref{...}` / `\label{...}` / `%` 注释 / `\begin{equation/align/eqnarray/...}` 内 / `\begin{verbatim/lstlisting/minted}` 内 / inline `$...$` 内的 math 变量
  - 占位区分隔符 `=== BEGIN CORPUS ===` ... `=== END CORPUS ===`
  - **输出约束**：合法 YAML；顶层只允许 `version: 1` + `concepts:`（**不**自创顶层字段 — codex 已确认 plan §5 没有 `bootstrap` 顶层字段，draft 识别走 `canonical: TBD` 或 `found_forms` 路径，见 plan §5.2 末尾）；用 `canonical` 字段（不用 `suggested_canonical`，统一到 plan §5 schema 命名）
- **裁剪**：本次不写 anthropic provider 的 tool schema 部分（`BOOTSTRAP_TOOL_SCHEMA`），那是给 anthropic API 走 tool use 用的；本次走 manual provider 模式，subagent 直接以文本形式输出 yaml
- **成功标准**：
  - `test -f example/prompt.md`
  - 5 个关键 anchor 全在：`## YAML schema` / `## Worked examples` / `## Skip rules` / `=== BEGIN CORPUS ===` / `=== END CORPUS ===`（每个 `grep -q`）
  - 长度区间：`[ $(wc -l < example/prompt.md) -ge 150 ] && [ $(wc -l < example/prompt.md) -le 600 ]`
  - **paper-agnostic 硬校验**：`example/prompt.md` 必须是**完全通用**的 standalone prompt（plan §8.5 设计意图），**不含任何 raw2event 任务上下文**；目标论文路径仅通过 Stage T4 的 subagent brief + manifest 注入。校验：`! grep -iE 'polarity deviation|per-pixel emd|davis346|raw2event|dvs-voltmeter|qkformer' example/prompt.md`（这些是 raw2event 已知概念或 plan 内置示例，worked example 里也不许）
  - **schema 字段一致性硬校验**：`! grep -q 'suggested_canonical' example/prompt.md`（统一用 `canonical`）；`! grep -E '^bootstrap:' example/prompt.md`（不允许顶层 `bootstrap` 字段）
- **状态**：Not Started

### Stage T2：codex 审 prompt 设计（执行 subagent 前的硬卡点）

- **目标**：codex 复审 `example/prompt.md` 是否：
  1. 与 plan §8.1 / §5 schema 一致（字段名 `canonical`、不引入未批准的顶层字段）
  2. skip 规则覆盖 plan §3.4 列出的所有 LaTeX context
  3. worked example 不污染 raw2event 的术语判断
  4. 输出格式约束清楚（避免 LLM 输出散文 + yaml 混合；明确「直接输出合法 YAML，不带任何 ```yaml fence」或反之，二选一并明示）
  5. subagent 能否在没有 AST 的情况下按 prompt 自律
- **成功标准**：codex 给出明确「批准 / 不批准」结论；**若不批准则修订后重审，循环直到批准再进 T3**（每轮 codex 反馈在本规划文档「修订记录」节追加一行）
- **状态**：Not Started

### Stage T3：准备 corpus manifest（`example/inputs/corpus_manifest.txt`）

- **目标**：列出 subagent 应扫描的具体 .tex 文件清单，明确**包含**和**排除**：
  - **包含**：
    - `/vol1/1007/projects/raw2event/doc/paper/neurips_2026.tex`
    - `/vol1/1007/projects/raw2event/doc/paper/sections/00_abstract.tex` … `99_appendix.tex`
    - `/vol1/1007/projects/raw2event/doc/paper/tables/*.tex`
    - `/vol1/1007/projects/raw2event/doc/paper/sections/appendix/*.tex`（如有）
  - **排除**：
    - `raw2event.tex`（旧 IEEE arXiv 版，**内容重复**且会双重计数 forms）
    - `checklist.tex`（NeurIPS D&B checklist 模板，与论文术语无关）
    - `neurips_2026.sty` / `neurips_2026_template_demo.tex.bak`（样式 / demo 备份）
- **格式**：每行一条 `<path> <line_count>`，开头注释说明取舍依据
- **成功标准**：
  - `test -f example/inputs/corpus_manifest.txt`
  - 每条路径用 `test -f` 校验存在
  - 总行数估算（manifest 中文件 wc -l 加和）≤ 2000 行（plan §8.4 corpus 长度估算 3000-token cap × 多 chunk OK，但单一 chunk 模式宁可一次过）
- **状态**：Not Started

### Stage T4：subagent 跑（dogfood 主体）

- **跑 subagent 前的 baseline 记录**（必做，否则越权校验不可验）：放在 `.cursor/`（已 ignored，不入 git）下，避免污染 example/：
  - `git -C /vol1/1007/projects/raw2event rev-parse HEAD` 与 `git -C /vol1/1007/projects/raw2event status --short` → `.cursor/dogfood_baseline_raw2event.txt`
  - `git -C /vol1/1007/projects/paperterm rev-parse HEAD` 与 `git status --short` → `.cursor/dogfood_baseline_paperterm.txt`
- **目标**：用 `Agent` 工具启动 `general-purpose` subagent，model = Opus，按以下 brief 执行：
  - 输入：`example/prompt.md` 全文（paper-agnostic，由 brief 显式说明本次目标论文是 raw2event NeurIPS）+ `example/inputs/corpus_manifest.txt` 路径
  - 工作流：subagent 用 Read 把 manifest 列出的 .tex 一一读取，**自己**应用 prompt 中的 skip 规则提取 prose，跨文件聚合 candidate concepts，形成 yaml 输出
  - 写出：
    - `example/output/glossary.draft.yaml`：**严格遵循 plan §5 schema**（顶层只 `version: 1` + `concepts:`；每个 concept 含 `id` / `category` / `canonical` / `found_forms` / `confidence`；`canonical` 可填具体 form 或 `TBD`；**绝不**自创 `bootstrap` 顶层字段或 `suggested_canonical` 字段）
    - `example/output/run_log.md`：subagent 自述「我扫了哪些文件 / 抽到了多少 candidate / 哪些低置信度 / 用了多长上下文 / 哪里不确定」；**若 yaml 第一次输出不合 schema，记录失败原因并重试 1 次（同一 subagent 线程）；第二次仍失败则保留失败 yaml 并标注「prompt/schema 缺陷待 T5 评估」**
- **限制**：subagent **只能写 `example/output/` 下的文件**，绝不修改 paperterm 仓库其它内容；不修改 raw2event；不创建 `src/` `tests/` 等
- **成功标准**：
  - `test -f example/output/glossary.draft.yaml`
  - `test -f example/output/run_log.md`
  - yaml 结构 grep 校验（**不依赖 PyYAML**）：
    - `head -5 example/output/glossary.draft.yaml | grep -q '^version: *1$'`
    - `grep -q '^concepts:' example/output/glossary.draft.yaml`
    - `grep -cE '^- id:' example/output/glossary.draft.yaml`（concept 计数）≥ 5
    - **schema 反污染**：`! grep -E '^bootstrap:' example/output/glossary.draft.yaml`；`! grep -q 'suggested_canonical' example/output/glossary.draft.yaml`
  - 后验校验 — subagent 无越权写入：
    - `git status --short --untracked-files=all` 输出排序后与 `.cursor/dogfood_baseline_paperterm.txt` 对比，新增项**全部**在 `example/` 内
    - `git -C /vol1/1007/projects/raw2event status --short` 输出必须与 `.cursor/dogfood_baseline_raw2event.txt` 完全一致（diff 0）；若 raw2event 不是 git 仓库则 fallback `find /vol1/1007/projects/raw2event -newer .cursor/dogfood_baseline_raw2event.txt -type f` 无输出
- **状态**：Not Started

### Stage T5：人工评估（`example/findings.md`）

- **目标**：主 agent（我）从 yaml + 抽样 .tex 检查结果，写一份评估报告：
  - **覆盖矩阵**：concept 数量按 category 分组（metric / dataset / model / pipeline / abbrev_pair / other）
  - **drift 分布**：每个 concept 的 found_forms 数量直方图（≥3 的概念是 paperterm 真实价值所在）
  - **行号抽样**：随机抽 3 个 concept × 1 个 form，去对应 .tex 的行号验证是否真实
  - **跳过规则评估**：在 yaml 中搜是否有疑似 cite key（形如 `Yang2024`）/ math 变量（形如 `\Delta p`）残留——若有，prompt skip 规则不充分
  - **known concepts sanity check**（codex 强烈建议加）：在跑 subagent **之前**主 agent 自己读一遍 raw2event abstract + introduction 的前 30 行，手抽 3 个**显然**会出现的核心术语（写到 `example/findings.md` 顶部「人工 ground truth seeds」节，时间戳标记），跑完 subagent 后对照 yaml 看是否全部命中；若漏抓任何一个 → 直接列入 prompt 缺陷清单
  - **prompt 缺陷清单**：列出至少 3 条「下次写 prompts.py 时要改 / 要补充的点」
  - **schema 缺陷清单**：列出 plan §5 schema 中可能不实用 / 缺的字段
- **成功标准**：
  - `test -f example/findings.md`
  - 包含六节：人工 ground truth seeds / 覆盖矩阵 / drift 分布 / 行号抽样 / 跳过规则评估 / prompt+schema 缺陷
  - 「人工 ground truth seeds」节含 3 条手抽术语 + 命中状态（每条 ✓ / ✗ + 备注）
  - 至少给出 3 条 prompt 缺陷与 1 条 schema 缺陷（如果都没有缺陷，说明评估太松，prompt 可能漏抓）
- **状态**：Not Started

### Stage T6：写 `example/README.md` + codex 终审 + commit + push

- **目标**：
  - `example/README.md`：解释 example/ 目录用途、本次 dogfood 设置、复现步骤、产物清单
  - codex 终审（审 README + findings + glossary 整体是否一致）
  - 单一 commit `dogfood(example): bootstrap prompt vs raw2event NeurIPS paper`，body 引用 `.planning/20260509_dogfood_bootstrap_prompt.md`
  - push 到 origin/main
- **成功标准（多重防泄漏校验）**：
  - `test -f example/README.md`
  - **白名单精确匹配**：`git diff --cached --name-only` 输出排序后必须**正好**等于：
    ```
    .planning/20260509_dogfood_bootstrap_prompt.md
    example/README.md
    example/findings.md
    example/inputs/corpus_manifest.txt
    example/output/glossary.draft.yaml
    example/output/run_log.md
    example/prompt.md
    ```
    （命令：`git diff --cached --name-only | sort > /tmp/staged.txt && diff /tmp/staged.txt <(echo "<7 paths>" | sort)` 应无差异）
  - **物理 .tex/.bib 防泄漏**：`find example -type f \( -name '*.tex' -o -name '*.bib' \)` 无输出
  - **正文长引用人工抽查**：`run_log.md` / `findings.md` / `glossary.draft.yaml`（含 `notes` 与 `locations` 字段）三者都不允许有 ≥10 行的连续 raw2event .tex 原文引用（人工 grep + 视觉检查）
  - push 后远端 HEAD == 本地 HEAD
- **状态**：Not Started

---

## 测试决策记录（用户已确认）

| # | 决策 | 选项 |
|---|---|---|
| D-T1 | corpus 怎么给 subagent | subagent 直接读 `../raw2event/doc/paper/`，不拷贝 .tex 到 paperterm 仓库 |
| D-T2 | example/ 是否入 git | 入 git（作为 dogfood 存档）；前提是不拷贝 corpus 主体（D-T1） |
| D-T3 | subagent 类型 | `general-purpose`（全工具，能 Read .tex + Write example/output/） |
| D-T4 | model | Opus（plan 设计要求 LLM 跨 section 语义一致） |

## 待确认事项

无（codex 一审反馈已 inline 修订；主 ground truth 对比已升级为 Stage T5 必做项）。

## 修订记录

- 2026-05-09 codex 一审反馈 → 8 处修订：
  1. 删除 Stage T1 中错误的「`bootstrap` 顶层字段」；明确 plan §5 顶层只有 `version` / `concepts:`，draft 识别走 `canonical: TBD` 或 `found_forms`（plan §5.2 末尾）
  2. 统一字段名 `canonical`（不用 `suggested_canonical`，与 plan §5 schema 一致）
  3. Stage T1 加反污染硬校验（worked example 不许含 raw2event 已知概念）
  4. Stage T1 加字段一致性校验（不许出现 `suggested_canonical` 或顶层 `bootstrap`）
  5. Stage T2 明确「不批准则修订到批准为止」循环
  6. Stage T4 yaml 校验改为 grep 结构（不依赖 PyYAML）；加 subagent 越权写入后验校验（git status + raw2event 比对）
  7. Stage T5 升级 ground truth sanity check 为必做（顶部新增「人工 ground truth seeds」节，3 条手抽术语 + ✓/✗）
  8. Stage T6 防泄漏多重校验：白名单精确匹配 7 文件、`find -name '*.tex' -o -name '*.bib'` 无输出、长引用人工抽查
- 2026-05-09 codex 二审反馈 → 3 处微调：
  1. 「7 处修订」笔误 → 「8 处修订」
  2. Stage T1 反污染硬校验：明确 `example/prompt.md` 是**完全通用**的 paper-agnostic standalone prompt，不含 raw2event 任务上下文，目标路径仅通过 subagent brief + manifest 注入（避免反污染 grep 误杀合法任务说明）
  3. Stage T6 长引用抽查范围：在 `run_log.md` / `findings.md` 之外加入 `glossary.draft.yaml`（locations / notes 字段也可能塞原文）

## 执行批准

写完本规划后，先送 codex 审本任务方案；通过后开始 Stage T1。
