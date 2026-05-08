## 任务：Vibe Coding 工作流初始化（不开发，仅搭脚手架）

**背景**：用户从 vibe-coding-template fork 出 paperterm 仓库，模板里 `CLAUDE.md` / `AGENTS.md` / `README.md` 还含 `{{PLACEHOLDER}}`，且 README 引用的 `.agent-rules/` / `.planning/` / `.cursor/memory/` / `sync_agent_rules.py` 当前不存在。需要按 paperterm（CLI 库，非 ML 研究项目）特点裁剪模板并补齐缺失文件，让仓库具备一个能正常工作的 vibe coding 工作流（Claude Code + Codex 协作），最后推到 `https://github.com/mm0806son/paperterm`。本次任务**仅做工作流脚手架，不写任何 paperterm 源码**（源码是 plan §12 Phase 1 的工作）。

**影响范围**（创建/修改的文件）：

```
新建：
  .agent-rules/approval.md
  .agent-rules/core.md
  .agent-rules/style.md
  .agent-rules/sync_agent_rules.py        ← 仅依赖标准库
  .planning/README.md
  .planning/20260508_init_vibe_coding.md  ← 本文档
  .cursor/memory/MEMORY.md                ← 本地文件，不入 git（D9）
  .gitignore

移动：
  paperterm_plan.md  →  .planning/20260508_paperterm_v0.1_design.md

重写：
  CLAUDE.md   ← sync 脚本生成，paperterm 占位符填好，删 ML 节
  AGENTS.md   ← sync 脚本生成
  README.md   ← 重写为 paperterm 中文 stub（≤20 行）

不创建：
  LICENSE / pyproject.toml / src/ / tests/ / scripts/ / .venv/   ← 留给 plan §12 Phase 1
```

**前置条件**：
- 已读完 `paperterm_plan.md`，掌握项目定位（LaTeX 论文术语一致性 CLI）、技术栈（Python 3.10+ / pylatexenc / pydantic / click）、目录结构（plan §11）
- `git remote origin` 已指向 `https://github.com/mm0806son/paperterm`，远端为空，本地无 commits
- 用户确认了 9 项关键决策（已记在「决策记录」节 D1–D9）

**Per-Stage 工作流（用户额外要求）**：每个 Stage 内部的执行循环都是「实施 → codex 审查 → 修订到通过 → `git add` 白名单 → `git diff --cached --name-only` 审核 → commit → push 到 `origin/main` → 进入下一 Stage」。本规划文档（**Stage 0**）也走这个流程：第一次 push 因 `main` 远端为空，使用 `git push -u origin main`；后续 push 直接 `git push`。

**Stage 总览**：
- Stage 0：本规划文档（已 codex 二审，待第三审通过后 commit + push）
- Stage 1：`.agent-rules/` 三个 md + sync 脚本
- Stage 2：`.planning/README.md` + 移动设计文档 + `.cursor/memory/MEMORY.md` 占位
- Stage 3：`README.md` 中文 stub + `.gitignore`
- Stage 4：跑 sync 重新生成 `CLAUDE.md` / `AGENTS.md`
- Stage 5：在本规划文档末尾追加「完成记录」并最终 commit + push

---

### Stage 1：创建 `.agent-rules/` 与 sync 脚本
- **目标**：
  - `.agent-rules/approval.md`：从当前 `CLAUDE.md` / `AGENTS.md` 中抽出「任务审批规则（先规划后执行）」整节，原样保留（通用规则，无 paperterm 特定内容）
  - `.agent-rules/core.md`：项目核心规则。**裁剪**：删除「开发阶段分离」整节；目录规范中 `data/` / `experiments/` 改为 paperterm 实际结构（`src/paperterm/` / `prompts/` / `docs/`）；填入 paperterm 占位符（见「占位符值」节）。**保留**：Python 环境约定、Claude Code 记忆存储规范
  - `.agent-rules/style.md`：代码规范 + Git 工作流。**裁剪**：删除「实验管理」整节，`KEY_METRICS` 改为 paperterm 相关指标。**保留**：代码规范、Git 工作流、语言规范、卡住处理、实施流程、技术标准、Codex Review Gate、质量门禁、错误处理、权限约定
  - `.agent-rules/sync_agent_rules.py`：**仅允许标准库 import**（`pathlib` / `textwrap` / `sys` / `argparse` 等）。合并三个 source md 写入 `CLAUDE.md` 和 `AGENTS.md`；CLAUDE.md 顶部带 Claude Code 专用 Commands 区块 + Codex MCP 调用示例；AGENTS.md 顶部带通用 banner
- **成功标准**（每条都是可执行命令）：
  - `test -f .agent-rules/approval.md && test -f .agent-rules/core.md && test -f .agent-rules/style.md && test -f .agent-rules/sync_agent_rules.py`
  - sync 脚本无第三方 import（**ast 白名单硬校验**，比 grep 更可靠）：
    ```bash
    python3 -I - <<'PY'
    import ast, sys
    allowed = {'pathlib','textwrap','sys','os','argparse','datetime','re','typing','__future__','collections','io','json'}
    tree = ast.parse(open('.agent-rules/sync_agent_rules.py').read())
    bad = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            bad += [n.name.split('.')[0] for n in node.names if n.name.split('.')[0] not in allowed]
        elif isinstance(node, ast.ImportFrom) and node.module:
            root = node.module.split('.')[0]
            if root not in allowed:
                bad.append(root)
    sys.exit(0 if not bad else (print('non-stdlib imports:', bad) or 1))
    PY
    ```
    辅助 grep（仅作快速人眼审）：`grep -E '^(import|from) ' .agent-rules/sync_agent_rules.py`
  - 用 `python3 -I` 隔离环境跑通：`python3 -I .agent-rules/sync_agent_rules.py --check`（脚本支持 `--check` 仅做语法/参数自检，不写文件；若不实现该 flag 则用 `python3 -I -c "import ast; ast.parse(open('.agent-rules/sync_agent_rules.py').read())"`）
  - `core.md` 不含「开发阶段分离」：`! grep -q '开发阶段分离' .agent-rules/core.md`
  - `style.md` 不含「实验管理」：`! grep -q '实验管理' .agent-rules/style.md`
- **Stage 1 commit**：`git add .agent-rules/` → 审核 staged 清单 → commit message `init(rules): add modular agent rule sources and sync script` → push
- **状态**：Not Started

### Stage 2：搭 `.planning/` 与 `.cursor/memory/`
- **目标**：
  - `.planning/README.md`：1 段话说明本目录用途 + 文件命名规范（`{YYYYMMDD}_{task_name}.md`）+ 生命周期（追加，不删，归档）
  - 移动 `paperterm_plan.md` → `.planning/20260508_paperterm_v0.1_design.md`（仓库尚未 commit，用 `mv`；不用 `git mv`）
  - `.cursor/memory/MEMORY.md`：空索引文件（仅 `# Memory Index` 标题 + 一行说明）；**该文件本身不入 git**（D9），仅作为本地占位让 agent 启动后能直接写
- **成功标准**：
  - `test -f .planning/README.md`
  - `test -f .planning/20260508_paperterm_v0.1_design.md`
  - `test ! -e paperterm_plan.md`（旧位置已不存在）
  - `test -f .cursor/memory/MEMORY.md`
- **Stage 2 commit**：`git add .planning/README.md .planning/20260508_paperterm_v0.1_design.md` —— **不**添加 `.cursor/memory/MEMORY.md`（D9）；commit message `init(planning): move design doc and add planning README` → push
- **状态**：Not Started

### Stage 3：重写 `README.md` + 创建 `.gitignore`
- **目标**：
  - `README.md`（**中文**，≤20 行）：项目一句话定位 + 计划用法（`git clone` → `pip install -e .` → `paperterm bootstrap` / `paperterm check`）+ 指向 `.planning/20260508_paperterm_v0.1_design.md` 看完整设计 + License: TBD（本次不创建 LICENSE 文件，避免锁死许可证）
  - `.gitignore`：见「.gitignore 关键条目」节，**包含 `*.swp` 等编辑器 swap 文件**
- **成功标准**：
  - `test $(wc -l < README.md) -le 20`
  - README 不含模板痕迹：`! grep -E 'vibe-coding-template|\{\{' README.md`（CLAUDE.md / AGENTS.md 的同类检查留到 Stage 4，因为它们此时仍是含 `{{}}` 的模板原貌）
  - `.gitignore` 至少包含：`__pycache__/`、`.venv/`、`*.swp`、`.cursor/memory/`、`.cursor/task_plan.md`、`.claude/settings.local.json`
  - 验证 swap 文件被忽略：若 `.planning/.20260508_init_vibe_coding.md.swp` 存在，则 `git check-ignore -q .planning/.20260508_init_vibe_coding.md.swp` 退出码 0
  - 验证本地 Claude 配置被忽略：`git check-ignore -q .claude/settings.local.json` 退出码 0
- **Stage 3 commit**：`git add .gitignore README.md` → 审核 staged 清单（不应含 `.claude/settings.local.json`、`*.swp`、`.cursor/memory/`） → commit message `init: add .gitignore and paperterm README stub` → push
- **状态**：Not Started

### Stage 4：跑 sync + 验证
- **目标**：
  - 用 `python3` 跑 `.agent-rules/sync_agent_rules.py`（脚本仅依赖标准库，与 `.venv` 是否存在无关）；若 `.venv/bin/python` 已存在，优先使用，否则 fallback 到 `python3`
  - 重新生成 `CLAUDE.md` / `AGENTS.md`，确保 placeholder 全部替换
  - **幂等性验证**：连续跑两次 sync，`git diff -- CLAUDE.md AGENTS.md` 在第二次后应无新增变化
- **成功标准**：
  - `! grep -F '{{' CLAUDE.md AGENTS.md`
  - `! grep -E '开发阶段分离|实验管理' CLAUDE.md AGENTS.md`
  - `! grep -E 'data/|experiments/' CLAUDE.md AGENTS.md`（目录规范已按 paperterm 实际结构裁剪）
  - 幂等性：先 `python3 .agent-rules/sync_agent_rules.py` 跑一次，`md5sum CLAUDE.md AGENTS.md` 记录哈希；再跑一次，`md5sum` 完全相同
- **Stage 4 commit**：`git add CLAUDE.md AGENTS.md` → 审核 staged 清单（不应再含 `{{` 字串） → commit message `init: regenerate CLAUDE.md and AGENTS.md from agent-rules` → push
- **状态**：Not Started

### Stage 5：追加完成记录 + 最终 commit/push（封档）
- **目标**：本规划文档末尾追加 `## 完成记录`，逐条列出 5 个 Stage 的实际完成时间、是否有偏差、对应 commit hash；至此整个初始化任务封档。
- **执行顺序**：
  1. 用 Edit 工具在本规划文档末尾追加 `## 完成记录` 章节（含每个 Stage 的状态 → Complete、UTC 时间戳、commit short hash、偏差备注）
  2. **审核全仓 staged + working tree**：`git status --short` 应只剩本规划文件这一行 modified
  3. `git add .planning/20260508_init_vibe_coding.md`
  4. `git diff --cached --name-only` 应正好等于 `.planning/20260508_init_vibe_coding.md`
  5. commit message：`docs(planning): record completion of vibe coding init`
  6. `git push`（远端已通过 Stage 0 设置 upstream，无需 `-u`）
  7. 验证：`git rev-parse HEAD` 与 `git ls-remote --heads origin main` 一致
- **成功标准**：
  - `git status --short` 输出为空（工作树干净，且非 ignored 内容已全部 commit）
  - `git status --short --ignored` 仅显示 `.cursor/memory/` / `.venv/` 等预期 ignored 项（用于人工 sanity check）
  - `git rev-parse HEAD` == `git ls-remote --heads origin main | awk '{print $1}'`
  - 远端 GitHub 网页刷新可见 6 个 commit（Stage 0 + Stage 1–5）
- **状态**：Not Started

---

## 决策记录（用户已确认）

| # | 决策 | 用户选择 |
|---|---|---|
| D1 | 规则文件架构 | 完整 `.agent-rules/` + `sync_agent_rules.py` |
| D2 | 模板裁剪 | 删除「开发阶段分离」「实验管理」整节，KEY_METRICS 改为 paperterm 相关 |
| D3 | `paperterm_plan.md` 位置 | 移到 `.planning/20260508_paperterm_v0.1_design.md` |
| D4 | `README.md` 处理 | 替换为 paperterm 极简 stub |
| D5 | `TARGET_GOAL` | **不上 PyPI**，只需 `git clone` 后 `pip install -e .` 即用 |
| D6 | README 语言 | **中文** stub |
| D7 | `.venv/` 与依赖 | 允许创建/安装；本次初始化**不强制**做（sync 脚本仅用标准库，可用 `python3` 直接跑） |
| D8 | `scripts/release.sh` 等 stub | **不预创建**（YAGNI） |
| D9 | `.cursor/memory/` git 策略 | **不入 git**（连同 `.cursor/task_plan.md` / `progress.md` / `findings.md` 一并 `.gitignore`） |

---

## 占位符值

| 字段 | 值 |
|---|---|
| `PROJECT_NAME` | `paperterm` |
| `PROJECT_DESCRIPTION` | LaTeX 论文术语一致性检查工具（命令行），通过 YAML glossary 检测 metric / dataset / model 等术语在 section / table / appendix 间的命名漂移；支持跨论文继承，并提供 LLM bootstrap 自动提取候选概念 |
| `PYTHON_VERSION` | `3.11`（plan §10 要求 ≥3.10，钉到具体版本与 `.venv` 一致） |
| `TARGET_GOAL` | `git clone` 后 `pip install -e .` 即用；不上 PyPI |
| `KEY_METRICS` | False positive rate（注释/数学/verbatim/cite 内 0 误报）/ 真实论文 detection coverage / runtime per paper / schema 校验错误友好度 |
| C1 | LaTeX-aware lint engine — `pylatexenc` AST、context-aware（math/verbatim/cite skip） |
| C2 | Glossary YAML schema with cross-paper extends — pydantic、`extends:` 继承、Vale-compatible 家族相似 |
| C3 | LLM bootstrap (manual + Anthropic) — standalone prompt、provider-agnostic、`glossary.draft.yaml` |

---

## `.gitignore` 关键条目

```
# Python
__pycache__/
*.pyc
*.pyo
*.pyd
*.egg
*.egg-info/
.eggs/
build/
dist/
pip-wheel-metadata/
.pytest_cache/
.mypy_cache/
.ruff_cache/
.tox/
.nox/
.hypothesis/
.coverage
.coverage.*
coverage.xml
htmlcov/
.pyre/
.pytype/

# 虚拟环境
.venv/
venv/

# 编辑器 swap / 临时文件
*.swp
*.swo
.*.swp
.*.swo
*~

# Cursor / Agent 会话状态（个人，不入 git）
.cursor/task_plan.md
.cursor/progress.md
.cursor/findings.md
.cursor/memory/

# Claude Code 本地配置（每机不同）
.claude/settings.local.json
.claude/*.local.*

# 本地配置
.env
.env.*
!.env.example

# OS / IDE 噪音
.DS_Store
.idea/
.vscode/
```

> 注意：**不**在 `.gitignore` 加 `*.yaml` / `*.yml`，否则会伤到将来的 glossary fixtures。

---

## README 风格

- 中文，≤20 行
- 包含：项目一句话、当前状态、计划用法（`git clone` → `pip install -e .` → `paperterm bootstrap` / `paperterm check`）、设计文档指引（`.planning/20260508_paperterm_v0.1_design.md`）、`License: TBD`

---

## 待确认事项

无（D1–D9 已敲定，所有 Stage 成功标准均为可执行命令）。

## 执行批准

用户已通过「开始吧」表态批准。规划文档（Stage 0）在 codex 三审通过后，按 Stage 0 commit 流程提交 + push（首次 push 用 `git push -u origin main`），随后进入 Stage 1。

**Stage 0 commit 步骤**：
1. `git add .planning/20260508_init_vibe_coding.md`
2. **硬门禁**：`git diff --cached --name-only` 输出必须**正好**等于 `.planning/20260508_init_vibe_coding.md`（不多不少一行）。这是 Stage 0 的唯一刚性 staged 检查
3. （sanity）`git status --short` 此时会显示 staged 的本规划文件 + 其他 untracked（`AGENTS.md` / `CLAUDE.md` / `README.md` / `paperterm_plan.md` / `.planning/.swp` 等）。这些 untracked 是预期的，将在后续 Stage 处理；不属于 Stage 0 commit
4. commit message：`docs(planning): add init plan for vibe coding scaffold`
5. `git push -u origin main`（首次 push，设置 upstream）
