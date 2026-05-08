# paperterm

LaTeX 论文术语一致性检查工具（命令行）。通过 YAML glossary 检测 metric / dataset / model 等术语在 section / table / appendix 间的命名漂移；支持跨论文继承，并提供 LLM bootstrap 自动提取候选概念。

## 快速使用

```bash
git clone git@github.com:mm0806son/paperterm.git
cd paperterm
python3.11 -m venv .venv
.venv/bin/pip install -e ".[anthropic,dev]"
.venv/bin/paperterm bootstrap <paper_dir>   # LLM 提取候选概念，产出 glossary.draft.yaml
.venv/bin/paperterm check    <paper_dir>    # 按 glossary.yaml 检查 .tex 中的术语漂移
```

完整设计与实施方案：[`.planning/20260508_paperterm_v0.1_design.md`](.planning/20260508_paperterm_v0.1_design.md)

License: TBD
