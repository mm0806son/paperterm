# paperterm

[中文](#中文) · [English](#english)

---

## 中文

LaTeX 论文术语一致性 lint 工具。检测同一概念在论文不同章节用不同名字（`MS-COCO` vs `MSCOCO`、`ResNet-50` vs `ResNet50`、`mean Average Precision` vs `Mean Avg. Precision` 等）。

本地运行，**不调用任何 LLM API**。词汇表生成阶段你用自己的 Claude.ai / ChatGPT 订阅，paperterm 只负责本地准备 prompt、清洗语料、人工 review 后做静态检查。

### 安装

```bash
git clone git@github.com:mm0806son/paperterm.git
cd paperterm
python3.11 -m venv .venv
.venv/bin/pip install -e .
```

### 用法

```bash
# 1. 在论文目录下生成 prompt + 清洗后的语料
.venv/bin/paperterm bootstrap path/to/paper

# 2. 把生成的 .paperterm_prompt.txt 内容粘到 Claude.ai / ChatGPT，
#    把 YAML 回复保存为 path/to/paper/glossary.draft.yaml

# 3. 人工 review draft → path/to/paper/glossary.yaml
#    （删 found_forms / 选 canonical / 把变体设为 aliases）

# 4. 本地 lint
.venv/bin/paperterm check path/to/paper
```

退出码：`0` 无 violation，`1` 有 violation，`2` 程序错误（缺 glossary、解析失败等）。

### 工作示例

`example/` 含一份合成的 CV 论文片段 + 配套 glossary，可直接复现 14 处 violation：

```bash
.venv/bin/paperterm check example \
    --glossary example/glossary.yaml \
    --include 'section.tex'
```

详见 [`example/README.md`](example/README.md)。

### 文档

- [`docs/usage.md`](docs/usage.md) — 完整工作流（含 `paperterm:base/...` 继承、context-aware 规则、glossary 字段说明）
- [`prompts/glossary_bootstrap.md`](prompts/glossary_bootstrap.md) — 喂给 LLM 的 prompt 全文

### License

Apache-2.0

---

## English

A LaTeX-aware terminology linter for academic papers. It catches
cases where the same concept is referred to under several names
across sections (`MS-COCO` vs `MSCOCO`, `ResNet-50` vs `ResNet50`,
`mean Average Precision` vs `Mean Avg. Precision`, …).

paperterm runs entirely locally and **never calls any LLM API**.
The glossary-generation step uses your own Claude.ai / ChatGPT
subscription; paperterm only prepares the prompt, cleans the
corpus, and lints against the glossary you hand-promote.

### Install

```bash
git clone git@github.com:mm0806son/paperterm.git
cd paperterm
python3.11 -m venv .venv
.venv/bin/pip install -e .
```

### Workflow

```bash
# 1. Prepare a prompt + AST-cleaned corpus from your paper
.venv/bin/paperterm bootstrap path/to/paper

# 2. Paste path/to/paper/.paperterm_prompt.txt into Claude.ai /
#    ChatGPT and save the YAML reply as
#    path/to/paper/glossary.draft.yaml

# 3. Hand-promote the draft to path/to/paper/glossary.yaml
#    (drop found_forms, pick a canonical, move the rest into
#    aliases / allowed_forms)

# 4. Lint
.venv/bin/paperterm check path/to/paper
```

Exit codes: `0` clean, `1` at least one violation, `2` hard
error (missing or draft glossary, parse failure).

### Worked example

`example/` ships a synthetic CV-domain `.tex` plus glossary; the
expected `paperterm check` output (14 violations, exit 1) is
captured for comparison:

```bash
.venv/bin/paperterm check example \
    --glossary example/glossary.yaml \
    --include 'section.tex'
```

See [`example/README.md`](example/README.md).

### Documentation

- [`docs/usage.md`](docs/usage.md) — full workflow including the
  `paperterm:base/...` extends URI, context-aware rules, and
  glossary field reference.
- [`prompts/glossary_bootstrap.md`](prompts/glossary_bootstrap.md)
  — the standalone prompt you paste into your LLM.

### License

Apache-2.0
