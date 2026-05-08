# paperterm — 设计与实施方案 v0.1

> 文件位置：`/vol1/1007/projects/paperterm_plan.md`
> 起草日期：2026-05-08
> 目标读者：**没有任何上下文的 agent**（Claude / Codex / GPT 任意），读完此文档应能从零开始独立实现 v0.1
> 项目目录（拟）：`/vol1/1007/projects/paperterm/`（实施第一步创建）
> 开发语言：英文代码、英文 commit、英文 user-facing docs（README / CLI help / 错误信息）；中文设计 / 内部规划文档

---

## 0. 一分钟摘要

`paperterm` 是一个**用于学术 LaTeX 论文的术语一致性工具**，要解决的具体问题是：

- 论文跨 section / table / appendix 写作时，**同一个概念在不同位置使用不同名字**（例如 metric "polarity deviation" 又叫 "polarity bias" 又叫 "polarity-balance deviation"）
- 这在 vibe coding / LLM 协作写作下尤其常见，肉眼很难发现，reviewer 一翻就抓
- 现有工具（Vale / textidote / LaTeX `glossaries` 包）没有一个能在学术 LaTeX 论文上做好这件事（详见 §2 调研）

`paperterm` 提供两个 CLI 命令：

- `paperterm bootstrap <paper_dir>` — 用 LLM（或人工 paste-back）自动扫描论文，提取术语等价类，生成 `glossary.draft.yaml` 草稿
- `paperterm check <paper_dir>` — 基于 `glossary.yaml` 检查所有 .tex，报告非 canonical 别名的位置

工具是 **LaTeX-aware** 的（基于 `pylatexenc` AST，正确跳过注释 / 数学 / verbatim / `\cite{}`），**跨论文复用**（YAML 支持 `extends:` 继承），**LLM-agnostic**（支持 Anthropic API + manual paste-back 两种模式）。

---

## 1. 项目背景与目标

### 1.1 真实问题（一个具体例子）

某 NeurIPS 论文中，一个名为 $|\Delta p|$ 的度量在不同位置被写成：

| 位置 | 出现的名字 |
|------|------|
| Abstract | `polarity deviation` |
| Introduction | `polarity bias`（部分版本） / `polarity deviation`（部分版本） |
| §4 Benchmark | `polarity-balance deviation` |
| §5 Results / Table 3 | $|\Delta p|$（仅符号） |
| Appendix C | `polarity deviation` |

至少 3–4 个写法。同一篇论文里另一个度量（per-pixel EMD）有 6 种写法：`per-pixel count EMD` / `per-pixel EMD` / `pixel-level EMD` / `px-EMD` / `spatial per-pixel EMD` / `spatial px-EMD`。

这是术语漂移（term drift）的典型表现。

### 1.2 v0.1 目标

| # | 目标 | 衡量 |
|---|------|------|
| G1 | 在真实 LaTeX 论文上**精确**检出术语别名 | 0 false positive 在注释 / 数学 / verbatim / cite / label / ref 内 |
| G2 | 提供 **YAML schema** 让作者声明 canonical 名 + allowed forms + aliases | 一个 `glossary.yaml` 即可表达完整规则 |
| G3 | **LLM bootstrap** 让作者无需手写 glossary | `bootstrap` 命令产出可直接编辑的 draft yaml |
| G4 | **跨论文复用**：共享 base glossary + 论文级 override | 通过 YAML `extends:` 字段实现 |
| G5 | **可 pip 安装**，命令行优先，零运行时配置 | `pip install paperterm` 后立即可用 |

### 1.3 v0.1 非目标（明确不做）

- ❌ IDE / LSP 集成（v0.2+ 考虑）
- ❌ 自动修复（`--fix`，v0.2+ 考虑；现阶段只报告）
- ❌ Markdown / RST 等其它格式（只支持 .tex）
- ❌ 复杂的"first mention 必须先定义全称"规则（v0.2+；现阶段允许全称和缩写都登记为合法 form）
- ❌ Web UI / GUI
- ❌ Vale 兼容性输出（schema 灵感来自 Vale，但不保证可直接转 Vale rules——见 §2.4）
- ❌ Multi-language paper 支持（中文论文术语漂移规则不同；v0.1 仅英文 LaTeX）

---

## 2. 既有方案调研与拒绝理由

实施前必读，避免重复发明。

### 2.1 Vale (https://vale.sh)

**地位**：工业级 prose linter，被 GitLab、Microsoft Docs、Mozilla 等用于文档一致性。

**为何不直接用**：
1. **LaTeX 支持是词法级的，不是语法级的**：Vale 的 `.tex` parser 只做基本 token 切分，不识别 `\begin{equation}` / `\begin{verbatim}` 等环境边界
2. **配置 `BlockIgnores` 在 .tex 上不生效**（实测于 Vale 3.14.1）：试图通过正则跳过数学块和 verbatim 块均失败
3. **`%` 注释不会被自动跳过**——学术论文经常在注释里放 author notes（`% TODO: 这里 polarity bias 措辞要改`），Vale 会全部误报
4. **Go 正则不支持 lookbehind**，自定义 `TokenIgnores` 写起来受限
5. **官方 workaround 是 pandoc 转 markdown**——会丢失 `\text{}` 等语义信息，对学术论文不可接受

**实测验证**：在一篇真实 NeurIPS 论文（10 个 section）上跑 Vale，主体匹配率 100%（8/8 命中），但在一个 stress test 文件上 6 处误报（注释 1、`\cite{}` 0（这个能跳过！）、equation block 1、verbatim 1、prose 3 真阳）。**真阳信号好，但假阳率不可控**。

**保留的设计借鉴**：YAML rule schema（`extends: existence / substitution`）、`tokens:` 列表风格、styles 目录跨项目共享思路——`paperterm` schema 应保持**可机械转换为 Vale rules**（未来 Vale LaTeX 支持改善后，可一键迁移）。

### 2.2 textidote (https://github.com/sylvainhalle/textidote)

**地位**：LaTeX 专用 linter，学术圈最常被推荐。

**为何不用**：聚焦语法 / 排版问题（缺空格、引号风格、句子过长），**没有术语一致性检查**。可作为补充工具，不是替代。

### 2.3 LaTeX `glossaries` / `acronyms` 宏包

**地位**：LaTeX 原生方案，作者可定义 `\newacronym` 然后用 `\gls{key}` 替代裸文本。

**为何不用**：
1. **侵入式**：要求作者把 prose 里所有术语写成宏调用，行文僵硬
2. **不可回溯**：现有论文已有大量 prose，全部改宏成本高
3. **不解决 LLM-bootstrap 需求**：仍需作者手工列宏

可作为**未来导出格式**：v0.3+ 可以让 `paperterm` 自动导出一份 `glossary` 包配置供作者贴入 preamble。

### 2.4 LanguageTool / Grammarly / DeepL Write

**地位**：通用 prose 工具。

**为何不用**：定制术语规则需要付费 API 或企业版；不感知 LaTeX；不解决跨论文复用。

### 2.5 结论

`paperterm` 没有合适的现成替代。值得自研，但 **schema 应保持 Vale-compatible 的家族相似性**，让用户和未来工具能互通。

---

## 3. 核心概念

实施前必须理解这五个概念。

### 3.1 Concept（概念）

一个语义实体，例如"极性偏差度量"。每个 concept 有：
- **唯一 ID**（slug，如 `polarity_deviation`，机器可读）
- **Category**（`metric` / `dataset` / `model` / `pipeline` / `abbrev_pair`）
- **Canonical name**（最权威写法，例如 `polarity deviation`）
- 0+ **Allowed forms**（合法变体，例如 `|\Delta p|` 数学符号形式）
- 0+ **Aliases**（禁用的别名，linter 会报警）

### 3.2 Form（形式）

一个文本 pattern，可以是：
- 字面字符串（最常见）
- 简单正则（用 `regex:` 前缀显式声明，避免误用）
- 数学表达式（包在 `math:` 前缀下，仅在数学模式 token 比较时启用）

每个 form 可标注 **case_sensitive** 和 **contexts**（见 §3.4）。

### 3.3 Alias（别名）

一个 forbidden form。匹配到 alias 后 linter 输出报告，含 `suggest`（默认指向 canonical，可单独覆盖）。

### 3.4 Context（上下文）

linter 在某段文本上判断时所处的 LaTeX 环境标签。可能取值：

| Context | 含义 | 用途 |
|---|---|---|
| `prose` | 普通段落文字（不在任何特殊环境内） | 默认，最严格 |
| `table` | 在 `\begin{table}` ... `\end{table}` 内（含 caption） | 允许使用缩写形式（如 `px-EMD`） |
| `figure` | 在 `\begin{figure}` 内（含 caption） | 同上 |
| `caption` | 在 `\caption{}` 内（不在 table/figure 时也可单独触发） | 通常等同 prose 但可单独配 |
| `math` | 数学模式内（`$..$`、`$$..$$`、`equation` 等） | 通常 SKIP（不 lint） |
| `verbatim` | `verbatim` / `lstlisting` / `listing` / `minted` 环境内 | SKIP |
| `comment` | `%` 注释 | SKIP |
| `cite_arg` | `\cite{...}` / `\ref{...}` / `\label{...}` 内部 | SKIP |

v0.1 实现时，`contexts` 字段在 `allowed_forms` 上**起作用**（限定该 form 只在某些 context 合法），在 `aliases` 上**不起作用**（别名永远是别名，无论上下文）。

### 3.5 Cross-Paper Reuse（跨论文复用）

通过 YAML `extends:` 字段实现继承：

```yaml
# paper-A/glossary.yaml
extends: ../base/event-camera.yaml
concepts:
  - id: polarity_deviation
    canonical: "polarity deviation"
    aliases: [...]
```

`base/event-camera.yaml` 提供事件相机领域共享术语；论文级 yaml 可以**覆盖**（同 id 时，paper-level 完全替换 base）或**追加**（不同 id 时，并集）。

---

## 4. 架构总览

```
┌─────────────────────────────────────────────────────────────────┐
│  Input: paper directory (多个 .tex + main.tex)                   │
└─────────────────────────────────────────────────────────────────┘
                           │
                ┌──────────┴──────────┐
                │                     │
                ▼                     ▼
   ┌──────────────────────┐   ┌──────────────────────┐
   │  paperterm bootstrap │   │   paperterm check     │
   │                      │   │                       │
   │  1. parse .tex AST   │   │   1. parse .tex AST  │
   │  2. extract prose    │   │   2. load glossary    │
   │  3. send to LLM      │   │      (with extends)   │
   │     (anthropic|      │   │   3. walk AST,        │
   │      manual)         │   │      match rules per  │
   │  4. parse YAML reply │   │      context          │
   │  5. write draft.yaml │   │   4. emit report      │
   └──────────┬───────────┘   └──────────┬────────────┘
              │                          │
              ▼                          ▼
   glossary.draft.yaml            stdout / JSON / SARIF
   (作者手动编辑 → glossary.yaml)   exit 1 if violations
```

### 4.1 核心模块（src/paperterm/ 目录下）

| 模块 | 责任 | 估行数 |
|---|---|---|
| `latex.py` | LaTeX AST 解析 + context-aware text iterator | ~250 |
| `glossary.py` | YAML schema (pydantic) + extends 解析 | ~150 |
| `linter.py` | rule 匹配引擎 + 报告格式化 | ~200 |
| `bootstrap.py` | LLM bootstrap（manual + anthropic provider） | ~250 |
| `cli.py` | click-based 命令行 | ~100 |
| `report.py` | 输出格式化（line / JSON / SARIF） | ~80 |
| `__init__.py` | 公共 API export | ~20 |
| **合计** | | **~1050** |

外加 tests / docs / packaging 约 +400–600 行。

---

## 5. Glossary YAML Schema

这是工具的核心。schema 用 pydantic 强校验。

### 5.1 完整示例

```yaml
# glossary.yaml
version: 1                       # schema 版本，v0.1 固定为 1

extends:                         # （可选）继承的 base glossary 路径
  - ../base/event-camera.yaml
  - ../base/ml-common.yaml

defaults:                        # （可选）所有 concept 的默认值
  case_sensitive: false
  whole_word: true               # 词边界匹配，避免 polarity 撞 polarity-targeted

concepts:
  # ─── Metric 例 ─────────────────────────────────────
  - id: polarity_deviation
    category: metric
    canonical: "polarity deviation"
    allowed_forms:
      - form: "|\\Delta p|"      # 数学符号形式
        contexts: [math, table]  # 仅在这些上下文允许
      - form: "$|\\Delta p|$"    # inline math
        contexts: any
    aliases:
      - form: "polarity bias"
        suggest: canonical       # 默认值，可省略
      - form: "polarity-balance deviation"
      - form: "polarity-balance"
        suggest: "polarity deviation"
    notes: |
      "Polarity-targeted K calibration" 是另一概念（calibration 变体），
      不混入此 concept。

  - id: per_pixel_emd
    category: metric
    canonical: "per-pixel EMD"
    allowed_forms:
      - form: "px-EMD"
        contexts: [table, figure, caption]
      - form: "px-EMD$_{\\text{med}}$"
        contexts: [table]
    aliases:
      - form: "per-pixel count EMD"
      - form: "pixel-level EMD"
      - form: "spatial per-pixel EMD"
      - form: "spatial px-EMD"
        suggest: "px-EMD"        # 单独指定建议，不指向 canonical
    notes: ""

  # ─── Dataset 例 ───────────────────────────────────
  - id: davis346
    category: dataset
    canonical: "DAVIS346"
    case_sensitive: true         # 覆盖 defaults
    aliases:
      - form: "DAVIS-346"
      - form: "Davis346"
      - form: "davis346"

  # ─── Model 例 ─────────────────────────────────────
  - id: dvs_voltmeter
    category: model
    canonical: "DVS-Voltmeter"
    case_sensitive: true
    allowed_forms:
      - form: "DVS-V"
        contexts: [table, figure, caption]
    aliases:
      - form: "DVS Voltmeter"    # 缺连字符
      - form: "DVSVoltmeter"

  # ─── Pipeline term 例 ─────────────────────────────
  - id: per_pair_k
    category: pipeline
    canonical: "per-pair K calibration"
    aliases:
      - form: "pair-specific K"
      - form: "per-device-pair K"
      - form: "polarity-targeted K calibration"  # 论文里偶发的另一种表达
        suggest: "per-pair K calibration"
```

### 5.2 字段规范

#### 顶层

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `version` | int | ✅ | schema 版本，v0.1 固定 `1` |
| `extends` | list[str] | ❌ | 相对路径或绝对路径，按顺序合并；后出现者覆盖先出现者 |
| `defaults` | object | ❌ | 应用到所有 concept 的默认字段 |
| `concepts` | list | ✅ | concept 列表 |

#### Concept

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `id` | str (slug) | ✅ | 全文档唯一；正则 `^[a-z][a-z0-9_]*$` |
| `category` | enum | ✅ | `metric` / `dataset` / `model` / `pipeline` / `abbrev_pair` / `other` |
| `canonical` | str | ✅ | 唯一首选写法；bootstrap 阶段允许暂为 `TBD` |
| `case_sensitive` | bool | ❌ | 默认继承自 `defaults` |
| `whole_word` | bool | ❌ | 默认继承自 `defaults`，true 时使用词边界匹配 |
| `allowed_forms` | list[Form] | ❌ | 合法变体 |
| `aliases` | list[Form] | ❌ | 禁用别名 |
| `notes` | str | ❌ | 自由文本 |

#### Form（用于 allowed_forms / aliases）

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `form` | str | ✅ | 字面字符串；以 `regex:` 前缀声明正则 |
| `contexts` | list[Context] 或 `any` | ❌ | 限定上下文；仅对 `allowed_forms` 起作用 |
| `case_sensitive` | bool | ❌ | 覆盖 concept 级别 |
| `suggest` | str | ❌ | 仅 alias；默认 `canonical`（特殊值）；可写显式字符串 |

#### Bootstrap-only 临时字段

`bootstrap` 命令产出的 `glossary.draft.yaml` 中，每个 concept 额外有：

| 字段 | 类型 | 说明 |
|---|---|---|
| `found_forms` | list[FoundForm] | 实际扫描到的所有写法 + 位置 + 出现次数 |
| `confidence` | float | LLM 给出的"这是同一 concept"的置信度，0–1 |

`FoundForm`:
```yaml
- form: "spatial per-pixel EMD"
  count: 2
  locations:
    - file: "sections/04_benchmark.tex"
      line: 38
    - file: "sections/appendix/C_supplementary.tex"
      line: 12
```

`paperterm check` 见到 `canonical: TBD` 或 `found_forms` 字段会**拒绝运行**并提示用户先编辑 draft → 提升为正式 glossary。

### 5.3 Extends 合并算法

```
load_glossary(path):
    raw = yaml.load(path)
    if "extends" in raw:
        merged = empty_glossary()
        for ext_path in raw["extends"]:
            ext = load_glossary(resolve(ext_path, base=path))
            merged = merge(merged, ext)
        merged = merge(merged, raw_without_extends)
        return merged
    return raw

merge(base, override):
    # defaults: override wins on conflict
    # concepts: same id → override wins (full replacement, not deep merge)
    #           different id → union
```

实施提示：`extends` 解析必须**检测循环引用**并报错。

---

## 6. CLI 设计

### 6.1 命令总览

```
paperterm bootstrap <paper_dir> [options]
paperterm check <paper_dir> [options]
paperterm print-prompt                 # 输出 standalone bootstrap prompt 到 stdout
paperterm validate <glossary.yaml>     # v0.1 末期可加，校验 schema
paperterm version
```

### 6.2 `paperterm bootstrap`

**用途**：扫描论文 .tex，用 LLM 提取候选概念等价类，产出 `glossary.draft.yaml`。

**参数**：

| 参数 | 默认 | 说明 |
|---|---|---|
| `<paper_dir>` | required | 论文根目录，递归找所有 `.tex` |
| `--main <file>` | `main.tex` 或自动探测 | 主文件，决定 `\input` 顺序（影响"首次出现"判断） |
| `--output <path>` | `<paper_dir>/glossary.draft.yaml` | 输出路径 |
| `--provider <name>` | `manual` | `manual` / `anthropic` |
| `--model <id>` | `claude-opus-4-7` | 仅当 provider=anthropic |
| `--api-key <key>` | env `ANTHROPIC_API_KEY` | 仅当 provider=anthropic |
| `--max-tokens <n>` | `8000` | LLM 输出上限 |
| `--include-glob <pat>` | `**/*.tex` | 多次指定 |
| `--exclude-glob <pat>` | `**/build/**` | 多次指定 |
| `--confidence-threshold <f>` | `0.5` | 仅保留置信度 ≥ 此值的 concept |
| `--dry-run` | false | manual 模式下打印 prompt 但不写文件 |

**行为（provider=manual）**：

1. 解析所有 .tex，提取 prose（去 math / cite / comment / verbatim）
2. 生成一份**完整 prompt + corpus**（自包含，含 schema 说明、示例、待分析文本）
3. 写入 `<paper_dir>/.paperterm_prompt.txt`，并在 stdout 打印路径
4. 提示用户："请把此文件内容粘贴到任意 LLM（Claude.ai / ChatGPT / Codex），把回复保存为 `<output>` 后再运行 `paperterm check`。"
5. 退出 0

**行为（provider=anthropic）**：

1. 同上 1
2. 调用 Claude API（**启用 prompt cache** 节省成本，corpus 部分缓存）
3. 让 Claude 通过 **tool use** 返回结构化 YAML（避免解析自由文本）
4. 把返回的 YAML 写入 `<output>`
5. 报告：发现 N 个 concept，其中 M 个 confidence ≥ threshold，最终写入 K 个

### 6.3 `paperterm check`

**用途**：用 `glossary.yaml` 检查论文，报告所有别名命中。

**参数**：

| 参数 | 默认 | 说明 |
|---|---|---|
| `<paper_dir>` | required | |
| `--glossary <path>` | `<paper_dir>/glossary.yaml` | |
| `--output <fmt>` | `line` | `line` / `json` / `sarif` |
| `--include-glob <pat>` | `**/*.tex` | |
| `--exclude-glob <pat>` | `**/build/**` | |
| `--minlevel <lvl>` | `warning` | `error` / `warning` / `info` |
| `--no-color` | false | 关闭 ANSI |

**输出格式 `line`**（默认）：

```
sections/00_abstract.tex:7:185  warning  [polarity_deviation]
  found:   "polarity bias"
  suggest: "polarity deviation"
  rule:    glossary.yaml:23

sections/04_benchmark.tex:38:174  warning  [per_pixel_emd]
  found:   "spatial per-pixel EMD"
  suggest: "per-pixel EMD"
  rule:    glossary.yaml:41

Found 8 violations across 5 files.
Run with --output=json for machine-readable report.
```

**输出格式 `json`**：

```json
{
  "version": 1,
  "violations": [
    {
      "file": "sections/00_abstract.tex",
      "line": 7,
      "column": 185,
      "concept_id": "polarity_deviation",
      "category": "metric",
      "found": "polarity bias",
      "suggest": "polarity deviation",
      "level": "warning",
      "rule_path": "glossary.yaml",
      "rule_line": 23
    }
  ],
  "summary": {
    "total": 8,
    "files_scanned": 12,
    "files_with_violations": 5
  }
}
```

**Exit code**：

- `0` — 无违规
- `1` — 发现违规（任何 level）
- `2` — schema / 文件错误（grossary 解析失败、.tex 解析失败等）

`--minlevel info` 时所有结果都纳入；`--minlevel error` 时只有 error 级会让 exit 1。

### 6.4 `paperterm print-prompt`

**用途**：输出 standalone bootstrap prompt 到 stdout，供"无安装路径"使用（详见 §8.5）。

**参数**：

| 参数 | 默认 | 说明 |
|---|---|---|
| `--no-instructions` | false | 仅输出 prompt 主体，省略 user-facing 使用说明 |

**用法**：

```bash
# 直接复制到剪贴板
paperterm print-prompt | xclip -selection clipboard

# 同步到 repo 内 checked-in 文件（release 流程用）
paperterm print-prompt > prompts/glossary_bootstrap.md
```

**单源 invariant**：CI 必须检查 `paperterm print-prompt --no-instructions` 与 `prompts/glossary_bootstrap.md` 一致，否则阻断 PR。

---

## 7. LaTeX-Aware Linter 实现

### 7.1 选型

使用 [`pylatexenc`](https://pylatexenc.readthedocs.io/) v2.x，理由：
- 纯 Python，无外部依赖
- 提供 `LatexWalker` 给出 AST
- 区分 `LatexCharsNode` / `LatexMacroNode` / `LatexEnvironmentNode` / `LatexMathNode` / `LatexCommentNode`
- 比正则状态机更稳

### 7.2 算法

```python
from pylatexenc.latexwalker import (
    LatexWalker, LatexCharsNode, LatexMacroNode,
    LatexEnvironmentNode, LatexMathNode, LatexCommentNode,
)

SKIP_ENVS = {"verbatim", "lstlisting", "listing", "minted",
             "equation", "equation*", "align", "align*",
             "gather", "gather*", "multline", "multline*",
             "displaymath"}
TABLE_ENVS = {"table", "table*", "tabular", "tabularx", "longtable"}
FIG_ENVS   = {"figure", "figure*", "subfigure"}
SKIP_MACROS_WITH_ARGS = {"cite", "citep", "citet", "citeauthor",
                         "ref", "eqref", "autoref", "label",
                         "includegraphics", "input", "include",
                         "url", "href", "bibitem"}

def walk(node, ctx_stack: list[Context], on_text):
    if isinstance(node, LatexCommentNode):
        return  # skip comment
    if isinstance(node, LatexMathNode):
        return  # skip math
    if isinstance(node, LatexEnvironmentNode):
        env = node.environmentname
        if env in SKIP_ENVS:
            return
        new_ctx = ctx_stack[:]
        if env in TABLE_ENVS:
            new_ctx.append("table")
        elif env in FIG_ENVS:
            new_ctx.append("figure")
        for child in node.nodelist:
            walk(child, new_ctx, on_text)
        return
    if isinstance(node, LatexMacroNode):
        macro = node.macroname
        if macro in SKIP_MACROS_WITH_ARGS:
            return
        if macro == "caption":
            new_ctx = ctx_stack + ["caption"]
            for arg in node.nodeargd.argnlist or []:
                if arg: walk(arg, new_ctx, on_text)
            return
        # other macros: recurse into args
        for arg in (node.nodeargd.argnlist if node.nodeargd else []):
            if arg: walk(arg, ctx_stack, on_text)
        return
    if isinstance(node, LatexCharsNode):
        on_text(node.chars, ctx_stack, node.pos)
        return
```

### 7.3 Context 计算

每个 char node 携带一个 `ctx_stack`，linter 判断时取**最具体**的 context：

```python
def effective_context(stack: list[str]) -> str:
    # 优先级（最具体优先）
    for c in ["caption", "table", "figure", "equation", "verbatim"]:
        if c in stack: return c
    return "prose"
```

### 7.4 匹配引擎

```python
def match_text(text: str, ctx: Context, glossary: Glossary) -> list[Match]:
    matches = []
    for concept in glossary.concepts:
        # 跳过 allowed_forms（不报警），但要从 alias matching 中排除
        # 因为 alias 可能是 allowed form 的子串，需要先 mask
        masked = mask_allowed_forms(text, concept, ctx)
        for alias in concept.aliases:
            for span in find_spans(masked, alias.form,
                                   case_sensitive=alias.case_sensitive
                                                  or concept.case_sensitive,
                                   whole_word=concept.whole_word):
                matches.append(Match(
                    concept_id=concept.id,
                    found=text[span.start:span.end],
                    suggest=alias.suggest or concept.canonical,
                    span=span,
                ))
    return matches
```

**关键细节**：

- 匹配时先 mask 该 concept 的所有 allowed_forms，避免 `px-EMD` 在 `spatial px-EMD` 的别名匹配中被两次命中
- 词边界 `whole_word=True` 时使用 `(?<![\w-])PATTERN(?![\w-])` 避免 `EMD` 撞 `EMD-related`
- `regex:` 前缀声明的 form 直接编译为 regex，其它字面字符串在编译时 `re.escape`

### 7.5 已知边界情况

实施时务必处理：

| 边界 | 处理 |
|---|---|
| `\input{file.tex}` | v0.1 不展开，扫每个 .tex 独立处理 |
| `\newcommand` 定义的 alias | v0.1 不识别（v0.2+ 可解析定义） |
| 跨段落 / 跨节的同一概念 | 不做"首次出现"特殊处理（v0.2） |
| `\text{}` 内部（数学环境内的文本） | 当前算法在 `LatexMathNode` 整体跳过——**这是有意的**，避免误报；v0.2 可考虑递归到 `\text{}` 内部 |
| Unicode 在 .tex 中 | `pylatexenc` 默认处理；测试用例需覆盖 |
| 中文混排（如双语论文） | v0.1 仅英文 prose；中文 token 不报警也不计 form 匹配 |

---

## 8. LLM Bootstrap

### 8.1 共享 Prompt 模板

```
You are an expert technical editor analyzing an academic paper for terminology consistency.

I'll give you the prose extracted from a multi-section LaTeX paper. Your job:

1. Identify all multi-word noun phrases that look like NAMES of:
   - Metrics (e.g., "per-pixel EMD", "ATE", "F1 score")
   - Datasets (e.g., "DAVIS346", "ImageNet")
   - Models or methods (e.g., "QKFormer", "DVS-Voltmeter")
   - Pipeline components (e.g., "K calibration", "polarity decoder")

2. For each concept, find ALL textual variations across the corpus
   (case-insensitive grouping, but preserve case in output).
   A "variation" includes: full form, abbreviation, hyphen variants,
   word-order variants, near-synonyms used interchangeably.

3. For each concept group, propose:
   - id: lowercase_snake_case slug (≤30 chars)
   - category: one of [metric, dataset, model, pipeline, abbrev_pair, other]
   - found_forms: list of {form, count, locations}
   - suggested_canonical: the form that appears most "official"
     (typically: longest, used in abstract or introduction, no abbreviation
     in prose context). Mark as "TBD" if uncertain.
   - confidence: 0–1 score for "these forms truly refer to the same concept"

4. EXCLUDE:
   - Common English words ("event", "image", "model")
   - Standalone math symbols ($K$, $|\Delta p|$)
   - Citation keys
   - Single-word concepts unless clearly a proper noun

Output as YAML following this schema:
[insert schema example]

Corpus follows below, with each chunk labeled by file and line range.
[corpus]
```

### 8.2 Provider: anthropic

实施：

```python
import anthropic

def bootstrap_with_anthropic(corpus, model, api_key) -> Glossary:
    client = anthropic.Anthropic(api_key=api_key)
    response = client.messages.create(
        model=model,
        max_tokens=8000,
        system=[{
            "type": "text",
            "text": SYSTEM_PROMPT,
            "cache_control": {"type": "ephemeral"},
        }],
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": SCHEMA_DESCRIPTION,
                    "cache_control": {"type": "ephemeral"},
                },
                {
                    "type": "text",
                    "text": f"Corpus:\n{corpus}",
                },
            ],
        }],
        # 用 tool use 拿到结构化输出
        tools=[BOOTSTRAP_TOOL_SCHEMA],
        tool_choice={"type": "tool", "name": "register_concepts"},
    )
    # 从 tool_use block 解析 concepts
    concepts = extract_tool_input(response, "register_concepts")
    return Glossary.from_bootstrap(concepts)
```

**Prompt cache**：corpus 较大时，把 SCHEMA + SYSTEM 设为 `ephemeral` cache，省 90% input cost on retry。

**Tool schema**（部分）：

```python
BOOTSTRAP_TOOL_SCHEMA = {
    "name": "register_concepts",
    "description": "Register all detected concept equivalence classes.",
    "input_schema": {
        "type": "object",
        "properties": {
            "concepts": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "category": {"enum": ["metric","dataset","model","pipeline","abbrev_pair","other"]},
                        "found_forms": {...},
                        "suggested_canonical": {"type": "string"},
                        "confidence": {"type": "number"},
                    },
                    "required": ["id","category","found_forms","confidence"],
                },
            },
        },
        "required": ["concepts"],
    },
}
```

### 8.3 Provider: manual

不调任何 API，把 prompt + corpus 拼成单文件输出，让用户手贴到任意 LLM。

实现极简：

```python
def bootstrap_manual(corpus, output_dir):
    prompt_path = output_dir / ".paperterm_prompt.txt"
    text = SYSTEM_PROMPT + "\n\n" + SCHEMA_DESCRIPTION + "\n\n" + \
           f"Corpus:\n{corpus}\n\n" + \
           "Output the concepts as YAML below this line:\n---"
    prompt_path.write_text(text)
    print(f"Prompt written to: {prompt_path}")
    print(f"Paste it into any LLM, save the YAML reply as: ")
    print(f"  {output_dir / 'glossary.draft.yaml'}")
    print(f"Then run: paperterm check {output_dir}")
```

### 8.4 Corpus 准备

输入 LLM 之前，prose 要清洗：

1. 用 §7 的 walker 提取所有 `prose` / `caption` context 下的 `LatexCharsNode` 文本
2. 按文件 + 行号块标注：

```
=== FILE: sections/00_abstract.tex (lines 1–14) ===
The Raw2Event dataset provides...
[文本]

=== FILE: sections/01_introduction.tex (lines 30–50) ===
[文本]
```

3. 总长度估算：3000-token cap per chunk，超长则切块多次调用，最后 merge concepts（id 冲突时保留 confidence 高者）

### 8.5 Standalone Prompt（README 无安装路径）

为降低首次使用门槛，repo 内 checked-in 一份**自包含的 prompt 文件**：

```
prompts/glossary_bootstrap.md
```

#### 用户工作流（无需安装 paperterm）

1. 在 GitHub 上访问 `prompts/glossary_bootstrap.md`，整段复制
2. 粘贴到任意 LLM 对话窗口（Claude.ai / ChatGPT / Codex / Cursor / 任意支持长上下文的工具）
3. 在 LLM 对话里附上自己论文的 .tex 内容（多个 section 一次贴或分多次）
4. LLM 按 prompt 要求返回 YAML
5. 把 YAML 保存为 `glossary.draft.yaml`，手编 canonical 字段
6. 改名 `glossary.yaml`
7. （可选）`pip install paperterm && paperterm check ./paper` 走 lint

#### 单源同步机制

避免 standalone prompt 与代码内 prompt 漂移：

| 角色 | 路径 | 关系 |
|---|---|---|
| **Source of truth** | `src/paperterm/prompts.py` | 字符串常量 `BOOTSTRAP_PROMPT` |
| **派生 1** | `paperterm bootstrap --provider manual` 输出的 `.paperterm_prompt.txt` | 在 prompt 末尾自动注入已 AST-清洗的 corpus |
| **派生 2** | `prompts/glossary_bootstrap.md` (checked-in) | 由 `paperterm print-prompt` 生成；末尾留空白占位让用户自己附 .tex |
| **CI 守护** | `.github/workflows/ci.yml` | `paperterm print-prompt --no-instructions \| diff - prompts/glossary_bootstrap.md` 必须为空 |

#### 与 `bootstrap --provider manual` 的对比

| 维度 | Standalone prompt | `bootstrap --provider manual` |
|---|---|---|
| 安装 paperterm | ❌ 不需要 | ✅ 需要 |
| .tex 预处理 | 由 LLM 自己跳过 math/cite/comment（prompt 里告知） | paperterm 用 AST 提取好 prose，LLM 看到的是干净文本 |
| 输出准确度 | 中（LLM 可能未严格遵循跳过规则） | 高 |
| 典型场景 | 第一次试用、demo、单篇论文一次性 | 反复迭代、长期工作流 |

#### Standalone prompt 文件结构

`prompts/glossary_bootstrap.md` 必须包含：

1. **角色 / 任务说明**（system 部分）—— 来自 `BOOTSTRAP_PROMPT`
2. **YAML schema 完整描述** —— 来自 `prompts.py` 中的 `SCHEMA_DESCRIPTION`
3. **2–3 个 worked example**（一个 metric、一个 dataset、一个 model） —— 让 LLM 知道目标格式
4. **预处理指令** —— 显式告知 LLM 跳过 math `$..$` / `\begin{equation}` / `\begin{verbatim}` / `\cite{}` / `\ref{}` / `%` 注释
5. **占位区**（用户在此下面贴 .tex） —— 用清晰分隔符如 `=== BEGIN PAPER CONTENT ===` 标注

#### README 中的呈现（Option A）

README quickstart 必须有两条并列路径：

```markdown
## Quickstart

### Option A — Use any LLM (no install)

1. Open [prompts/glossary_bootstrap.md](./prompts/glossary_bootstrap.md)
2. Copy the whole file → paste into Claude/ChatGPT/Codex
3. Append your paper's .tex content below the marker
4. Save the LLM's YAML reply as `glossary.draft.yaml`
5. Edit `canonical:` fields → rename to `glossary.yaml`
6. (Optional) `pip install paperterm && paperterm check ./paper`

### Option B — Use the CLI (with API)

```bash
pip install paperterm[anthropic]
export ANTHROPIC_API_KEY=...
paperterm bootstrap ./paper
paperterm check ./paper
```
```

---

## 9. 跨论文复用机制

### 9.1 Base Glossary 设计

提供一个 `paperterm/data/base/` 目录，含若干 community-curated yaml：

```
data/base/
  ml-common.yaml         # ML 通用：F1 score, accuracy, AUC, t-SNE, ...
  cv-common.yaml         # CV：mAP, IoU, ROI, ...
  event-camera.yaml      # 事件相机：DAVIS346, polarity, contrast threshold, ...
  neuromorphic.yaml      # 神经形态：QKFormer, ANN-to-SNN, spike rate, ...
```

v0.1 仅提供 `ml-common.yaml` 和 `event-camera.yaml`（论文目标领域），其它 v0.2+。

### 9.2 论文级 yaml

每篇论文有自己的 `glossary.yaml`：

```yaml
version: 1
extends:
  - paperterm:base/event-camera.yaml   # 特殊前缀 paperterm:base/ 指向包内 data/
  - ../shared/group-style.yaml         # 文件路径
concepts:
  - id: my_unique_concept
    canonical: "MyConcept-v2"
    aliases: [...]
```

`paperterm:base/<file>` 是 URI 风格的快捷方式，由 `paperterm` 包内置。

### 9.3 冲突处理

合并时同 id 视为**完全替换**（论文级覆盖 base）。这避免了"我修改了 base 一个 alias，但论文级也有"导致难调试。

---

## 10. 技术栈

```
Python: >= 3.10  （类型提示 + match-case 友好）

核心运行时依赖:
  pylatexenc        >= 2.10        # LaTeX AST
  pydantic          >= 2.5         # YAML schema 校验
  click             >= 8.1         # CLI
  pyyaml            >= 6.0         # YAML 解析
  rich              >= 13.0        # 终端着色 / 进度

可选依赖（[anthropic] extra）:
  anthropic         >= 0.34        # LLM provider

开发依赖:
  pytest            >= 7.4
  pytest-cov        >= 4.1
  ruff              >= 0.1.6       # lint + format
  mypy              >= 1.7         # 类型检查
  hatch             >= 1.9         # 打包
```

`pyproject.toml` 用 hatch 后端，PEP 621 标准。

---

## 11. 文件结构

```
paperterm/                                # repo root
├── pyproject.toml
├── README.md                             # 英文，面向用户
├── LICENSE                               # MIT 推荐
├── CHANGELOG.md
├── .gitignore
├── .github/
│   └── workflows/
│       └── ci.yml                        # pytest + ruff + mypy on PR
├── docs/
│   ├── design.md                         # 本文档的英文翻译版
│   ├── usage.md                          # 用户指南
│   └── examples/
│       └── neurips_event_camera/         # 真实例子（去身份化的论文片段）
│           ├── glossary.yaml
│           └── sections/*.tex
├── prompts/
│   └── glossary_bootstrap.md             # Standalone prompt for any LLM
│                                         # 由 `paperterm print-prompt` 生成；
│                                         # CI 检查与 src/paperterm/prompts.py 一致
├── src/
│   └── paperterm/
│       ├── __init__.py
│       ├── __main__.py                   # python -m paperterm
│       ├── cli.py
│       ├── latex.py
│       ├── glossary.py
│       ├── linter.py
│       ├── bootstrap.py
│       ├── report.py
│       ├── prompts.py                    # bootstrap prompt 模板
│       └── data/
│           └── base/
│               ├── ml-common.yaml
│               └── event-camera.yaml
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── fixtures/
│   │   ├── tex/                          # 测试用 .tex 片段
│   │   │   ├── basic_prose.tex
│   │   │   ├── math_skip.tex
│   │   │   ├── verbatim_skip.tex
│   │   │   ├── cite_skip.tex
│   │   │   └── multi_section/
│   │   └── glossary/
│   │       ├── minimal.yaml
│   │       └── with_extends.yaml
│   ├── test_latex.py
│   ├── test_glossary.py
│   ├── test_linter.py
│   ├── test_bootstrap_manual.py
│   ├── test_bootstrap_anthropic.py       # 用 mock，不打真 API
│   ├── test_cli.py
│   └── test_extends.py
└── scripts/
    └── release.sh                        # 打 tag + 发布到 PyPI
```

---

## 12. 实施阶段（v0.1）

每个阶段必须**有可演示输出**才进下一个。

### Phase 1 — 项目骨架（0.5 天）

**目标**：可 `pip install -e .` 安装，`paperterm version` 能跑。

- [ ] 创建 repo `/vol1/1007/projects/paperterm/`，`git init`
- [ ] 写 `pyproject.toml`、`.gitignore`、`LICENSE`、`README.md`（极简 stub）
- [ ] 创建 `src/paperterm/__init__.py`、`cli.py`（仅 version 子命令）
- [ ] 配置 `ruff` + `mypy` + `pytest`
- [ ] 配置 `.github/workflows/ci.yml`
- [ ] commit："init: project scaffold"

**完成判据**：`pip install -e .` 后 `paperterm version` 输出 `paperterm 0.1.0.dev0`，CI 在 dummy test 上通过。

### Phase 2 — Glossary schema（1 天）

**目标**：能加载并合并 yaml。

- [ ] `glossary.py`：用 pydantic 定义 `Concept` / `Form` / `Glossary`
- [ ] 实现 `Glossary.from_yaml(path)` 含 extends 解析（带循环检测）
- [ ] `data/base/ml-common.yaml` 和 `event-camera.yaml` 初始版本（每个 5–10 个 concept）
- [ ] tests:
  - [ ] 加载最小 yaml 成功
  - [ ] extends 单层 / 多层 / 循环检测
  - [ ] schema 校验失败给清晰错误
- [ ] commit："feat(glossary): yaml schema with extends"

**完成判据**：`pytest tests/test_glossary.py tests/test_extends.py -q` 全绿。

### Phase 3 — LaTeX-aware walker（1.5 天）

**目标**：能从 .tex 文件中正确提取 prose / caption / table 等 context 标注的文本流。

- [ ] `latex.py`：实现 §7 算法，输出 `Iterator[(text, ctx_stack, position)]`
- [ ] tests:
  - [ ] 注释 / 数学 / verbatim / cite / label 内的关键词不出现在输出中
  - [ ] table caption 正确标注 `[caption, table]`
  - [ ] 嵌套环境（figure 内 subfigure）正确传递 context
  - [ ] Unicode 文本通过
  - [ ] 行号 / 列号正确
- [ ] commit："feat(latex): pylatexenc-based prose iterator"

**完成判据**：在一个真实论文 section 上跑，输出的文本流和肉眼判断一致。

### Phase 4 — Linter 引擎（1 天）

**目标**：`paperterm check` 在测试 fixture 上正确报告。

- [ ] `linter.py`：rule 匹配 + 上下文判断 + 报告组装
- [ ] `report.py`：`line` 和 `json` 格式
- [ ] `cli.py`：实现 `check` 命令（含所有 §6.3 参数）
- [ ] tests:
  - [ ] minimal glossary + minimal tex → 0 violations
  - [ ] 单 concept 单 alias → 1 violation，位置正确
  - [ ] alias 在数学/注释/cite 内 → 0 violations
  - [ ] allowed_form 在 contexts 限定外 → 不报警（因为不是 alias）
  - [ ] case_sensitive / whole_word 行为正确
  - [ ] extends 合并后冲突 concept 行为正确
  - [ ] exit code 在违规 / 无违规 / schema 错时分别 1 / 0 / 2
- [ ] commit："feat(linter): rule matching engine + CLI check"

**完成判据**：在 `docs/examples/neurips_event_camera/` 上跑出预期违规数。

### Phase 5 — Bootstrap manual + Standalone prompt（1 天）

**目标**：
- `paperterm bootstrap --provider manual` 输出可用 prompt 文件
- `paperterm print-prompt` 命令输出 standalone prompt
- `prompts/glossary_bootstrap.md` checked-in 并与代码常量同步

- [ ] `prompts.py`：模板常量
  - `BOOTSTRAP_PROMPT`（任务说明）
  - `SCHEMA_DESCRIPTION`（schema 文档）
  - `WORKED_EXAMPLES`（2–3 个示例）
  - `STANDALONE_INSTRUCTIONS`（README Option A 用户使用步骤）
  - `STANDALONE_PLACEHOLDER`（=== BEGIN PAPER CONTENT === 分隔符）
- [ ] `bootstrap.py`：corpus 提取 + prompt 渲染 + manual 输出
- [ ] `cli.py`：
  - `bootstrap` 命令（manual 分支）
  - `print-prompt` 命令（默认含使用说明，`--no-instructions` 仅 prompt 主体）
- [ ] 生成 `prompts/glossary_bootstrap.md`（运行 `paperterm print-prompt > prompts/glossary_bootstrap.md`）
- [ ] tests:
  - [ ] manual provider：prompt 文件包含所有 .tex 的 prose，math/cite 不在 corpus 中
  - [ ] `print-prompt` 输出包含 schema、示例、占位符分隔符
  - [ ] 同步检查：`print-prompt --no-instructions` 与 `prompts/glossary_bootstrap.md` 一致
- [ ] commit："feat(bootstrap): manual provider + standalone prompt"

**完成判据**：
- 对真实论文跑 `bootstrap --provider manual`，生成的 prompt 拷给 Claude.ai 能返回合法 yaml
- `prompts/glossary_bootstrap.md` 直接复制到 Claude.ai + 贴 .tex 也能返回合法 yaml

### Phase 6 — Bootstrap anthropic（1 天）

**目标**：`paperterm bootstrap --provider anthropic` 端到端工作。

- [ ] `bootstrap.py`：anthropic provider 实现，含 prompt cache 与 tool use
- [ ] tests:
  - [ ] mock anthropic client，验证请求结构（cache_control 设置正确、tool 注册正确）
  - [ ] mock 返回 → 正确解析为 Glossary
- [ ] 真实 API 集成测试（gated by `ANTHROPIC_API_KEY`，CI 上跳过）
- [ ] commit："feat(bootstrap): anthropic provider with prompt cache"

**完成判据**：在真实论文 + 真实 API 上跑通，生成的 yaml 正确。

### Phase 7 — 文档与发布准备（0.5 天）

- [ ] 完整 README（英文），必须含：
  - 安装
  - **Option A quickstart**：链接 `prompts/glossary_bootstrap.md` 的"无安装"路径
  - **Option B quickstart**：`paperterm bootstrap` + `check` CLI 路径
  - schema 简介
  - 贡献指南链接
- [ ] `docs/usage.md`（详细 CLI / yaml 字段 / 例子）
- [ ] `docs/design.md`（本文档英译版）
- [ ] `CHANGELOG.md` 1.0 entry
- [ ] CI 增加同步检查：`paperterm print-prompt --no-instructions | diff - prompts/glossary_bootstrap.md` 必须为空
- [ ] 双路径 e2e 验证：
  - 路径 A：直接把 `prompts/glossary_bootstrap.md` 喂给 Claude.ai + 真实 .tex，验证返回的 yaml 通过 `paperterm check`
  - 路径 B：`paperterm bootstrap --provider anthropic` → `check`
- [ ] commit："docs: v0.1 release docs + standalone prompt sync"
- [ ] tag `v0.1.0`

**完成判据**：一个完全没接触过的人按 README **任一**路径操作都能跑通。

### 总工时估计

| Phase | 工时 |
|---|---|
| 1 项目骨架 | 0.5 天 |
| 2 Glossary schema | 1 天 |
| 3 LaTeX walker | 1.5 天 |
| 4 Linter | 1 天 |
| 5 Bootstrap manual + Standalone prompt | 1 天 |
| 6 Bootstrap anthropic | 1 天 |
| 7 文档发布 | 0.5 天 |
| **合计** | **~6.5 天** |

---

## 13. 测试策略

### 13.1 单元测试

每个模块独立测试，覆盖率目标 **≥ 85%**。重点：

- `latex.py` — 各种 LaTeX 边界（math / verbatim / cite / nested envs）
- `glossary.py` — extends 链、循环检测、字段校验
- `linter.py` — context 判断、case_sensitive、whole_word
- `bootstrap.py` — corpus 提取（mock LLM）

### 13.2 集成测试

`tests/test_e2e.py`：从一个真实 .tex 集合开始，bootstrap → manual edit (fixture 提供已编辑版) → check → 比对预期 violation 列表。

### 13.3 真实论文回归

`docs/examples/neurips_event_camera/` 是一个**去身份化**的真实论文片段（包含已知的 8+ violations）。每次 release 前必须跑：

```bash
paperterm check docs/examples/neurips_event_camera/ \
    --glossary docs/examples/neurips_event_camera/glossary.yaml \
    --output json > /tmp/result.json
diff <(jq -S . /tmp/result.json) <(jq -S . docs/examples/neurips_event_camera/expected.json)
```

---

## 14. 版本与发布

### 14.1 SemVer

- v0.1.x — alpha；schema 可能 breaking 变化
- v0.2.x — beta；schema 稳定，增加功能（first-mention、auto-fix）
- v1.0 — schema 锁定，长期支持承诺

### 14.2 发布 checklist

每次 tag：

1. `ruff check src/ tests/` 通过
2. `mypy src/paperterm` 通过
3. `pytest --cov=paperterm --cov-fail-under=85` 通过
4. CHANGELOG 更新
5. `hatch build` 产出 wheel + sdist
6. `hatch publish` 到 PyPI（首发可先发 TestPyPI）
7. GitHub release 含 changelog 摘要

### 14.3 PyPI 包名

首选 `paperterm`；若被占用退而求其次 `paperterm-lint`。

---

## 15. 开放问题 / v0.2 路线图

### 15.1 v0.1 后期可能要回答的问题

1. **`\input` 展开是否支持？** v0.1 不展开，但用户可能希望 `bootstrap` 看到完整 prose 上下文。可加 `--follow-input`。
2. **多语言支持？** 中文论文有自己的术语漂移问题（"事件相机" vs "事件摄像头"）。设计上 schema 是 language-agnostic，但 LaTeX walker 需要测试。
3. **`\newcommand` 自定义宏识别？** 例如 `\newcommand{\PD}{polarity deviation}` 之后 `\PD` 应等价于 canonical。
4. **`bibtex` 内的 entry title 是否纳入 lint？** 一般否（不是作者写的 prose）。

### 15.2 v0.2 计划功能

- `--fix`：自动改写为 canonical（基于 LaTeX AST 重新序列化）
- First-mention 规则（`contexts: [first_mention]` 真正生效）
- VS Code 扩展（基于 LSP）
- Vale rules 导出（`paperterm export --to vale`）
- `glossaries` 包导出（`paperterm export --to latex-glossaries`）

---

## 附录 A：真实验证案例

测试集来自一个真实 NeurIPS 投稿的 LaTeX 源（事件相机领域，已去除作者身份信息）。

### A.1 已知违规列表

| 文件 | 行 | 别名 | 应建议 |
|------|---|------|--------|
| sections/00_abstract.tex | 7 | "per-pixel count EMD" | "per-pixel EMD" |
| sections/01_introduction.tex | 39 | "polarity bias" *（部分版本）* | "polarity deviation" |
| sections/01_introduction.tex | 39 | "pixel-level EMD" | "per-pixel EMD" |
| sections/04_benchmark.tex | 38 | "polarity-balance deviation" | "polarity deviation" |
| sections/04_benchmark.tex | 38 | "spatial per-pixel EMD" | "per-pixel EMD" |
| sections/appendix/C_supplementary.tex | 12 | "spatial per-pixel EMD" | "per-pixel EMD" |
| sections/appendix/C_supplementary.tex | 32 | "spatial px-EMD" | "px-EMD" |
| sections/appendix/C_supplementary.tex | 68 | "spatial px-EMD" | "px-EMD" |

共 8 处。

### A.2 应跳过的位置（不该被报警）

| 位置 | 内容 | 原因 |
|---|---|---|
| `\cite{polarity_bias_2024}` | "polarity bias" 在 cite key 中 | cite_arg context |
| `% TODO: polarity bias 措辞` | 注释 | comment |
| `\begin{equation} \text{polarity bias} \end{equation}` | 数学环境内 | math |
| `\begin{verbatim} polarity bias = compute_pb() \end{verbatim}` | verbatim | verbatim |

`paperterm check` 必须 0 false positive on this stress test。

---

## 附录 B：Vale 实测对照

为说明为何不直接用 Vale，记录 Vale 3.14.1 在 stress test 上的表现：

| 测试位置 | Vale 行为 | paperterm 期望行为 |
|---|---|---|
| 普通 prose 中的 `polarity bias` | ✅ 命中 | ✅ 命中 |
| `\cite{}` 内的 `polarity bias` | ✅ 跳过（TokenIgnores 配后） | ✅ 跳过 |
| `%` 注释内的 `polarity bias` | ❌ 误报 | ✅ 跳过 |
| `\begin{equation}` 内的 `\text{polarity bias}` | ❌ 误报（BlockIgnores 不生效） | ✅ 跳过 |
| `\begin{verbatim}` 内的 `polarity bias` | ❌ 误报（BlockIgnores 不生效） | ✅ 跳过 |
| inline `$|\Delta p|$` 的数学符号 form | ❌ 无法表达 contexts 限定 | ✅ 通过 contexts |

Vale 在真实论文 prose 上 100% 正确，但在 stress test 上 4/6 假阳。**学术论文实际写作中注释和 verbatim 出现术语 token 的概率不可忽略**，因此 Vale 不达标。

---

## 附录 C：术语表（本文档自身用）

为避免本文档自身陷入术语漂移：

- **concept** — 一个语义实体；YAML 中的 `id` 唯一
- **form** — 一段文本 pattern；可以是 canonical / allowed / alias
- **canonical** — concept 的唯一首选写法；每个 concept 必有 1 个
- **allowed form** — concept 的合法变体（不报警）
- **alias** — concept 的禁用变体（报警）
- **context** — LaTeX 上下文标签（prose / table / math / ...）
- **glossary** — 一个 yaml 文件，含 0+ concept
- **bootstrap** — 用 LLM 从论文自动产出 draft glossary 的过程
- **lint / check** — 用 glossary 检查论文的过程

---

## 附录 D：给 agent 的执行指引

如果你（agent）正在读这份文档准备开始实施，按以下顺序：

1. **创建项目目录** `/vol1/1007/projects/paperterm/`，`git init`
2. **按 §11 文件结构**搭骨架，写 `pyproject.toml`
3. **按 §12 Phase 1–7 顺序**逐阶段实施，每个 Phase commit 一次
4. 每个 Phase 的"完成判据"必须跑通才进下一阶段
5. **不要预先优化**：先跑通 happy path，再处理边界
6. **不要扩范围**：v0.1 严格按本文档列的目标实施；新需求记到 §15
7. 不确定时，**优先选择更简单的实现** + 在 PR 描述中标记"待讨论"
8. 测试用例参照 §13 和附录 A

完成后向用户汇报：
- 实际工时
- 偏离本文档的地方（必须列出）
- v0.2 候选项

---

**文档结束。版本：v0.1（2026-05-08）。后续修改请追加日期 + 修改摘要在本节之上。**
