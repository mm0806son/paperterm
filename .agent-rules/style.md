# 代码规范、Git 工作流与质量门禁

## 代码规范

- **Python 3.10+**，type hints 必须，行长 100，PEP 8
- **Docstring**：所有公共类和函数使用 Google style docstring
- **命名**：`snake_case`（变量/函数）、`CamelCase`（类）
- 不使用 `import *`，不使用裸 `except`
- 捕获具体异常类型，有不确定性时先验证，不基于猜测改动
- 测试文件与源文件目录结构镜像，新功能必须附带测试
- 工具链：`ruff`（lint + format）、`mypy`（类型检查）、`pytest` + `pytest-cov`

## 关键质量指标

paperterm 的核心质量指标（区别于 ML 项目的 mAP / FPS 等）：

- **False positive rate**：在注释 / 数学 / verbatim / `\cite{}` / `\label{}` / `\ref{}` 内 0 误报
- **Detection coverage**：在真实论文上能检出已知的术语漂移（手写 ground truth 验证）
- **Runtime per paper**：单篇 NeurIPS 量级（10–20 个 .tex 文件）≤ 5s
- **Schema 校验错误友好度**：YAML 解析失败时给出具体行号 + 字段 + 建议

测试 fixture 应覆盖每条质量指标对应的边界情况（见 `tests/fixtures/`）。

## Git 工作流

- **分支命名**：`feat/<描述>`、`fix/<描述>`、`docs/<描述>`、`refactor/<描述>`
- **Commit 格式**：`<type>(<scope>): <简短描述>`
  - type ∈ `feat` / `fix` / `docs` / `refactor` / `test` / `chore` / `init`
  - scope 可省略，但跨模块时建议加（`feat(linter):` / `fix(glossary):`）
- **不提交**：`.venv/`、`__pycache__/`、`*.swp`、`.cursor/memory/`、本地 `.claude/settings.local.json`、大型二进制（> 10MB）
- 禁止跳过 hooks（`--no-verify`）
- `git add` 优先用具体路径，避免 `git add .` / `git add -A` 误带文件

## 语言规范

| 场景 | 语言 |
|------|------|
| Agent 与用户交互 | 中文 |
| 内部规划文档（`.planning/` 下） | 中文 |
| 当前阶段 README（项目尚处脚手架/设计期） | 中文 |
| 代码注释 | 英文 |
| Commit message | 英文 |
| **正式 user-facing 输出**：CLI `--help`、错误信息、`docs/` 用户手册、release 版 README | 英文（与 paperterm v0.1 设计目标一致，便于开源传播） |
| LaTeX fixture / 测试输入 | 英文（与目标场景一致） |

> 切换节点：`docs/usage.md` 写就时同步改写 README 为英文；CLI 输出从一开始就是英文。
> 注意 README 当前可中文不等于以后还是中文 — 见 `paperterm_plan.md` §0 中的语言策略。

## Prompt 单源规则

`prompts/glossary_bootstrap.md` 必须由 `paperterm print-prompt` 生成，**不允许手工编辑**。

- 修改 prompt 内容只编辑 `src/paperterm/prompts.py`
- CI 校验：`paperterm print-prompt | diff - prompts/glossary_bootstrap.md` 必须无差异
- 这是 plan §6.4 / §8.5 的关键 invariant：「standalone prompt 与代码内 prompt 永不漂移」

## 卡住处理

同一问题最多尝试 3 次，超过后停止硬改：
1. 记录已尝试方案 + 报错 + 失败原因判断
2. 对比 2-3 个相似实现，提炼替代路径
3. 优先选择更小、更可验证的拆解方案，等待用户选择

## 实施流程

1. **Understand**：先读现有实现与相邻功能，至少找 1 处相似实现
2. **Test**：优先先写测试（如适用）
3. **Implement**：最小改动通过验证
4. **Refactor**：在测试通过前提下清理结构
5. **Review**：非 trivial 改动提交前须经 Codex 代码审查（见下方「代码审查」节）
6. **Commit**：提交信息说明 why，并引用规划文档

## 技术标准与决策

- 优先组合而非继承，优先显式依赖与清晰数据流
- 评估顺序：可测试性、可读性、一致性、简洁性、可逆性

## 代码审查（Codex Review Gate）

项目已集成 OpenAI Codex 作为代码审查工具。Review Gate 已启用。

**何时触发**：
- 完成一个功能分支或逻辑完整的代码块后（对应实施流程第 5 步）
- 修改核心代码（lint engine、glossary loader、LLM provider 等）后
- 用户额外要求时（例如阶段性发布前，每个 sub-stage 完成都过审）

**审查重点**：
- 代码正确性与潜在 bug
- 与项目规范的一致性（PEP 8、type hints、命名规范）
- 测试覆盖是否充分
- 安全性与性能问题
- LaTeX 边界情况是否考虑（注释 / 数学 / verbatim / cite）

**豁免**：单行 bug fix、注释修改、配置调整、文档更新无需 Codex 审查。

> **各 Agent 的具体调用方式**：参见各自的指令文件（CLAUDE.md / .cursor/rules/ 等）中的工具特定说明。

## 质量门禁

完成前需满足：
- 代码可运行（`paperterm check <fixture> ` 不抛异常）
- 相关测试通过（`pytest tests/ -q`）
- 格式化与 lint 通过（`ruff check .` 与 `ruff format --check .`）
- 类型检查通过（`mypy src/paperterm/`）
- **Codex 代码审查通过**（适用于非 trivial 改动）

## 错误处理

- 快速失败并提供可定位上下文（YAML 错误指明行号 + 字段；LaTeX 解析失败指明文件 + 大致位置）
- 在合适层级处理错误，不吞异常
- 有不确定性时先验证，不基于猜测改动
- CLI 错误码语义：0 = 成功且无 violation；1 = 检出 violation；2 = 程序错误（YAML 加载失败、LaTeX 解析失败等）

## 权限约定

- 读操作默认允许
- 高影响命令（安装依赖、批量改写、潜在破坏性操作）需先征得用户确认
- `git push --force`、`git reset --hard`、删除分支等操作必须由用户明确批准
