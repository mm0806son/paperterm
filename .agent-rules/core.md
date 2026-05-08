# 项目核心规则

## 项目定位

<!-- paperterm — LaTeX 论文术语一致性检查工具（命令行）。
     科研写作辅助工具，非 ML 训练项目。 -->

**项目名称**：paperterm

**一句话**：LaTeX 论文术语一致性检查工具（命令行），通过 YAML glossary 检测 metric / dataset / model 等术语在 section / table / appendix 间的命名漂移；支持跨论文继承，并提供 LLM bootstrap 自动提取候选概念。

**主要贡献 / 目标**：

| # | 方向 | 关键词 |
|---|------|--------|
| C1 | LaTeX-aware lint engine | `pylatexenc` AST、context-aware（math / verbatim / cite skip） |
| C2 | Glossary YAML schema with cross-paper extends | pydantic、`extends:` 继承、Vale-compatible 家族相似 |
| C3 | LLM bootstrap (manual + Anthropic) | standalone prompt、provider-agnostic、`glossary.draft.yaml` |

目标：`git clone` 后 `pip install -e .` 即用；不上 PyPI（库形式分发即可）。

## Python 环境

**始终使用项目虚拟环境 `.venv/`（Python 3.11）**，禁止使用系统 Python（少数例外：`.agent-rules/sync_agent_rules.py` 因仅依赖标准库，可用 `python3` 直接跑）。

所有 `python`、`pytest`、`pip` 命令必须使用 `.venv/bin/` 前缀，或在已激活虚拟环境的 shell 中执行：

```bash
source .venv/bin/activate   # 激活
.venv/bin/python ...        # 直接调用（推荐，确保隔离）
```

## 目录规范

```
src/paperterm/   # 主源码包
tests/           # 测试，镜像 src/paperterm/ 结构
docs/            # 用户/设计文档（英文）
prompts/         # standalone bootstrap prompt
scripts/         # 发布等 ops 脚本（按需）
.planning/       # 所有规划文件（按 {YYYYMMDD}_{task_name}.md 命名）
.cursor/         # IDE 与 Agent 会话状态（memory/、task_plan.md 等，不入 git）
.agent-rules/    # AI 协作规则源（CLAUDE.md / AGENTS.md 由 sync 脚本生成）
```

- 禁止在根目录创建 `.py` 文件
- 大二进制文件（论文 PDF、原始数据）不提交 Git
- 上游依赖通过 PyPI 引入，不直接复制源码

## Claude Code 记忆存储规范

Claude Code 的持久化记忆文件必须保存在项目目录下，不使用全局路径：

- **记忆根目录**：`.cursor/memory/`
- **索引文件**：`.cursor/memory/MEMORY.md`（仅包含指向各记忆文件的链接，不写记忆内容）
- **记忆文件命名**：`{type}_{topic}.md`，例如 `feedback_planning_location.md`
- **禁止**使用 `~/.claude/` 或任何项目目录之外的路径存储记忆
- `.cursor/memory/` 整目录在 `.gitignore` 中被排除（个人/会话级记忆，不入仓库）

每个记忆文件使用如下 frontmatter 格式：

```markdown
---
name: 记忆名称
description: 一句话描述（用于判断未来会话的相关性）
type: user | feedback | project | reference
---

内容
```
