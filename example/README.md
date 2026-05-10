# `example/` — paperterm 工作样例

[中文](#中文) · [English](#english)

---

## 中文

一份合成的 CV 论文片段，配套小型 glossary，演示 `paperterm check` 的全部行为。

### 文件清单

| 文件 | 用途 |
|---|---|
| `glossary.yaml` | 5 条 production-shape 的 concept（mAP / IoU / ResNet-50 / MS-COCO / batch normalization） |
| `section.tex` | 手写 46 行 LaTeX，覆盖每一类常见漂移 |
| `lint_output.txt` | `paperterm check` 的捕获输出（14 violations / exit 1） |

### 复现

```bash
.venv/bin/paperterm check example \
    --glossary example/glossary.yaml \
    --include 'section.tex'
```

### 覆盖的漂移类型（共 14 处 violation）

- **大小写漂移**：`ResNet50` / `Resnet-50` / `Res-Net50` → `ResNet-50`
- **连字符 / 空格漂移**：`MSCOCO` / `MS COCO` / `ms-coco` → `MS-COCO`
- **复合写法**：`batch-normalization` / `batch norm` / `BatchNorm` → `batch normalization`
- **同义词漂移**：`Mean Avg. Precision` / `mean avg precision` / `average precision` → `mean Average Precision`
- **连字符别名**：`intersection-over-union` → `Intersection over Union`
- **大小写敏感别名**：`IOU` → `IoU`

paperterm 正确**不**触发的位置：

- 顶部 `%` 注释
- canonical 的正常使用（`ResNet-50` / `MS-COCO` / `batch normalization` / `IoU` …）
- 行内数学（`$\mathrm{IoU} = \cdots$`）
- `\cite{…}` / `\ref{…}` 参数
- `\begin{verbatim}` 块
- `mAP@50` 与 `BN` 在 table / figure / caption 内（`contexts: [table, figure, caption]` 已允许）

### 替换为自己的论文

`glossary.yaml` 是你要替换的入口。完整流程见 [`../docs/usage.md`](../docs/usage.md)：用 `paperterm bootstrap` 生成 prompt，粘到 LLM，保存回复，人工 review 成正式 glossary，再跑 `paperterm check`。

---

## English

A small synthetic CV-domain fixture demonstrating the end-to-end
behaviour of `paperterm check`.

### Files

| File | Purpose |
|---|---|
| `glossary.yaml` | 5 production-shape concepts (mAP / IoU / ResNet-50 / MS-COCO / batch normalization) |
| `section.tex` | hand-written 46-line LaTeX section with intentional drift |
| `lint_output.txt` | captured `paperterm check` output (14 violations, exit 1) |

### Reproduce

```bash
.venv/bin/paperterm check example \
    --glossary example/glossary.yaml \
    --include 'section.tex'
```

### Drift categories exercised (14 violations)

- **Capitalisation drift** — `ResNet50` / `Resnet-50` / `Res-Net50` → `ResNet-50`
- **Hyphen / spacing drift** — `MSCOCO` / `MS COCO` / `ms-coco` → `MS-COCO`
- **Compound spelling** — `batch-normalization` / `batch norm` / `BatchNorm` → `batch normalization`
- **Synonym drift** — `Mean Avg. Precision` / `mean avg precision` / `average precision` → `mean Average Precision`
- **Hyphenated alias** — `intersection-over-union` → `Intersection over Union`
- **Case-sensitive alias** — `IOU` → `IoU`

`paperterm check` correctly stays silent on:

- Top-level `%` comment lines
- Canonical mentions (`ResNet-50`, `MS-COCO`, `batch normalization`, `IoU`, …)
- Inline math (`$\mathrm{IoU} = \cdots$`)
- `\cite{…}` and `\ref{…}` arguments
- `\begin{verbatim}` blocks
- `mAP@50` and `BN` inside tables, figures, captions
  (`contexts: [table, figure, caption]` allows them there)

### Adapting for your own paper

`glossary.yaml` is the file you would replace with your own. The
full workflow is in [`../docs/usage.md`](../docs/usage.md):
prepare a prompt with `paperterm bootstrap`, paste it into your
LLM, save the YAML reply, hand-promote it to a production
glossary, then run `paperterm check`.
