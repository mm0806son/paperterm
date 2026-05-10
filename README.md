# paperterm

LaTeX 论文术语一致性检查工具（命令行）。通过 YAML glossary 检测 metric / dataset / model 等术语在 section / table / appendix 间的命名漂移。**不依赖任何 LLM API** —— 词汇表生成阶段你用自己的 Claude.ai / ChatGPT 订阅，paperterm 本地准备 prompt 和清洗后的语料，剩余流程全本地。

## 快速使用

```bash
git clone git@github.com:mm0806son/paperterm.git
cd paperterm
python3.11 -m venv .venv
.venv/bin/pip install -e ".[dev]"

# 1. 生成 prompt + 清洗后的语料（本地，无网络）
.venv/bin/paperterm bootstrap <paper_dir>

# 2. 把 <paper_dir>/.paperterm_prompt.txt 内容粘到 Claude.ai / ChatGPT，
#    把 YAML 回复保存为 <paper_dir>/glossary.draft.yaml

# 3. 人工 review draft → <paper_dir>/glossary.yaml（删 found_forms / 选 canonical）

# 4. 本地 lint
.venv/bin/paperterm check <paper_dir>
```

详细工作流：[`docs/usage.md`](docs/usage.md)。
完整设计：[`.planning/20260508_paperterm_v0.1_design.md`](.planning/20260508_paperterm_v0.1_design.md)。
真实样例（在 Raw2Event NeurIPS 论文上检出 18 个漂移）：[`example/demo.md`](example/demo.md)。

License: Apache-2.0。
