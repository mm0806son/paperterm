## 任务：paperterm v0.1 Phase 1 — 项目骨架（最小可装可跑）

**背景**：vibe coding init（commit `1d2dbe3`）+ dogfood (`98cdd8b`) 已封档，paperterm 当前是「设计完整、源码空缺」状态。Phase 1 是 plan §12 列出的第一阶段，目标是把仓库从「无源码」变成「`pip install -e .` 能装、`paperterm version` 能输出 `paperterm 0.1.0.dev0`」的最小可运行骨架。**不写**任何 lint engine / glossary loader / bootstrap 业务代码（那是 Phase 2–6）。

**plan §12 Phase 1 完整 deliverable**（user 已批准的简化版）：

| 项 | plan §12 原文 | 本任务实际做 | 说明 |
|---|---|---|---|
| repo + git init | ✓ | 已完成（init 阶段 commit `bde6b57`） | 跳过 |
| `pyproject.toml` | ✓ | ✓ | hatch backend，PEP 621 |
| `.gitignore` | ✓ | 已完成 + dogfood 期间扩到 `.cursor/` 整目录 | 跳过 |
| `LICENSE` | ✓ | ✓ | **Apache 2.0**（user 决策 D-P1.1） |
| `README.md` | ✓ | 已完成 | 跳过；Phase 1 不动 README |
| `src/paperterm/__init__.py` + `cli.py` | ✓ | ✓ | `paperterm version` 子命令；版本字符串 `0.1.0.dev0` |
| 配 `ruff` + `mypy` + `pytest` | ✓ | ✓（在 pyproject.toml 内） | tool 段配置 |
| 配 `.github/workflows/ci.yml` | ✓ | ✗ **不做**（user 决策 D-P1.2） | 留待真有 PR 协作时再加 |
| commit "init: project scaffold" | ✓ | 拆 4 个 sub-stage commit（user 决策 D-P1.3） | 见 Stage P1.A–P1.D |

**完成判据**（plan §12 Phase 1 原文）：
- `pip install -e .` 后 `paperterm version` 输出 `paperterm 0.1.0.dev0`
- pytest 在 dummy test 上通过

**影响范围**（创建/修改的文件）：

```
新建：
  LICENSE                                  ← Apache 2.0 完整文本（~200 行）
  pyproject.toml                           ← hatch backend (dynamic version), PEP 621, ruff/mypy/pytest tool configs
  src/paperterm/__init__.py                ← __version__ = "0.1.0.dev0"（仓库唯一版本字面 SoT）
  src/paperterm/__main__.py                ← `python -m paperterm` 入口
  src/paperterm/cli.py                     ← click-based; 仅 `version` 子命令；version 字符串从 __init__.py 读
  src/paperterm/py.typed                   ← PEP 561 marker（让下游识别本包带 type hints）
  tests/__init__.py                        ← 空（让 pytest 把 tests/ 视为包）
  tests/test_version.py                    ← `paperterm version` 输出断言 + `paperterm.__version__` 断言

不动：
  README.md / CLAUDE.md / AGENTS.md / .gitignore / .agent-rules/ / .cursor/ / example/

不创建（留 Phase 2–6）：
  src/paperterm/{latex,glossary,linter,bootstrap,prompts,report}.py
  tests/test_{latex,glossary,linter,bootstrap}.py
  prompts/ docs/ scripts/ data/ experiments/   ← 后两者本项目永远不会有
  .github/workflows/                            ← user 选不做 Phase 1 CI
```

**前置条件**：
- vibe coding init + dogfood 全部封档（远端 HEAD `98cdd8b`）
- `.venv/` **本任务必须创建**（首次执行 `python3.11 -m venv .venv`），否则 `pip install -e .` 没目标
- user 三项决策已记录：D-P1.1 Apache 2.0 / D-P1.2 不做 CI / D-P1.3 4 commits

---

### Stage P1.A: 创建 LICENSE（Apache 2.0）

- **目标**：仓库根目录 `LICENSE` 文件，内容是 Apache License 2.0 完整 boilerplate（标准文本，不修改任何条款）
- **不做**：不在 LICENSE 里写 paperterm 特定内容；版权年份用 2026，版权人用 `Zijie Ning`（来自 `git config user.name`）
- **成功标准**：
  - `test -f LICENSE`
  - 行数 ≥ 200（标准 Apache 2.0 全文 ~202 行）
  - 含「Apache License」字符串：`grep -q 'Apache License' LICENSE`
  - 含「Version 2.0」字符串：`grep -q 'Version 2.0' LICENSE`
  - 末尾的版权 placeholder 块已替换（不能含字面 `[yyyy] [name of copyright owner]`）：`! grep -E '\[yyyy\]|\[name of copyright owner\]' LICENSE`
- **commit**：`init: add Apache-2.0 LICENSE`
- **状态**：Complete

### Stage P1.B: 创建 `pyproject.toml`（含工具链配置）

- **目标**：单文件包含
  1. `[build-system]` — hatchling
  2. `[project]` — name=paperterm, **version 走 dynamic（Hatch 从 `__init__.py` 读取，单 SoT）**, requires-python=">=3.10", license="Apache-2.0", authors, keywords, classifiers
     - `dynamic = ["version"]`
     - `[tool.hatch.version] path = "src/paperterm/__init__.py"` 配套设定
  3. `[project.dependencies]` — **Phase 1 仅最小**：`click>=8.1`（CLI 必需）。pylatexenc / pydantic / pyyaml / rich 留 Phase 2–4 增量加（plan §10 列表完整版本）
  4. `[project.optional-dependencies]` — `dev = [pytest>=7.4, pytest-cov>=4.1, ruff>=0.1.6, mypy>=1.7]`；`anthropic = [anthropic>=0.34]`（Phase 1 不用，先 hook 着）
  5. `[project.scripts]` — `paperterm = "paperterm.cli:main"`
  6. `[tool.ruff]` — line-length=100, **target-version="py310"**（与 `requires-python>=3.10` 公共承诺一致；本地开发用 3.11 .venv 跑无冲突），select 主流规则（E/F/I/UP/B 等）
  7. `[tool.mypy]` — strict=true（小项目可负担），**python_version="3.10"**（同上）
  8. `[tool.pytest.ini_options]` — testpaths=["tests"]，addopts="-q --strict-markers"
  9. `[tool.hatch.build.targets.wheel]` — packages=["src/paperterm"]
- **关于 `__version__` SoT（codex 反馈）**：用 Hatch `dynamic = ["version"]` 让 pyproject 从 `src/paperterm/__init__.py` 的 `__version__ = "..."` 字面读取，避免两份字符串漂移。`cli.py` 也只引用 `paperterm.__version__`。结果：**整个仓库版本号 single source of truth = `src/paperterm/__init__.py`**。
- **成功标准**：
  - `test -f pyproject.toml`
  - 用 `python3 -c 'import tomllib; tomllib.load(open("pyproject.toml","rb"))'`（py3.11 内置 tomllib）解析 0 错误
  - 含 `name = "paperterm"`：`grep -q '^name = "paperterm"$' pyproject.toml`
  - 含 `dynamic = ["version"]`：`grep -q 'dynamic = \["version"\]' pyproject.toml`
  - **不**含 `^version = ` 字面行：`! grep -E '^version = ' pyproject.toml`（避免 SoT 漂移）
  - `target-version = "py310"`：`grep -q 'target-version = "py310"' pyproject.toml`
  - `python_version = "3.10"`：`grep -q 'python_version = "3.10"' pyproject.toml`
- **commit**：`init: add pyproject.toml with hatch backend and tool configs`
- **状态**：Complete

### Stage P1.C: 创建 `src/paperterm/` 包 + CLI 骨架

- **目标**：
  1. 创建虚拟环境：`python3.11 -m venv .venv`（**先做**，否则后续无法验证）
  2. `src/paperterm/__init__.py`：`__version__ = "0.1.0.dev0"`（**整个仓库唯一版本字面常量**） + module docstring
  3. `src/paperterm/__main__.py`：`from .cli import main; main()`，让 `python -m paperterm` 可跑
  4. `src/paperterm/cli.py`：click group + `version` 子命令，输出 `paperterm <__version__>`（**必须**从 `from . import __version__` 读，不准硬编码二次）
  5. **`src/paperterm/py.typed`**：空文件（PEP 561 marker，让下游知道本包带 type hints；codex 反馈第 9 项）
  6. 安装 + 自检：`.venv/bin/pip install -e .` 然后 `.venv/bin/paperterm version`
- **关键设计**：
  - CLI 用 click（plan §10 选定），不用 argparse / typer
  - `version` 是子命令而非 `--version` flag（plan §6.1 明示）
  - `__version__` single source of truth；`cli.py` 用 `from paperterm import __version__` 显式引用，不复制
  - mypy strict 下 click decorator 可能要求 main 函数返回类型；用 `def main() -> None:` 明示
- **成功标准**：
  - `test -f .venv/bin/paperterm`（pip install 后 entry script 存在）
  - `test -f src/paperterm/py.typed`
  - `.venv/bin/paperterm version` 输出**正好** `paperterm 0.1.0.dev0`（`diff <(.venv/bin/paperterm version) <(echo 'paperterm 0.1.0.dev0')` 为空）
  - `.venv/bin/python -m paperterm version` 输出同上
  - `.venv/bin/python -c 'import paperterm; print(paperterm.__version__)'` 输出 `0.1.0.dev0`
  - `.venv/bin/python -c 'from importlib.metadata import version; print(version("paperterm"))'` 输出 `0.1.0.dev0`（验证 Hatch dynamic 把 `__version__` 正确挂到了 distribution metadata）
  - **`cli.py` 不含字面 `0.1.0`**：`! grep -F '0.1.0' src/paperterm/cli.py`（验证 SoT 没漂移）
- **commit**：`feat(cli): scaffold paperterm package with version subcommand`
- **状态**：Complete

### Stage P1.D: 创建 `tests/` 包 + 一个 dummy 测试

- **目标**：
  1. `tests/__init__.py` — 空文件（让 pytest 把 tests/ 视为 namespace）
  2. `tests/test_version.py`：用 click `CliRunner` 测 `version` 子命令的 stdout 与 exit code
  3. 验证 `.venv/bin/pytest tests/ -q` 至少 1 测试通过
  4. 验证 `.venv/bin/ruff check .` 0 violations（仅自己写的代码）
  5. 验证 `.venv/bin/mypy src/paperterm/` 0 errors
- **测试代码风格**：
  - 用 `from click.testing import CliRunner` 而不是 `subprocess.run`（更快、更确定）
  - 测 stdout 字面内容 + exit code 0
  - 测 `paperterm.__version__ == "0.1.0.dev0"`
- **成功标准**：
  - `.venv/bin/pytest tests/ -q` 至少 1 passed, 0 failed
  - `.venv/bin/ruff check .` exit 0
  - `.venv/bin/mypy src/paperterm/` exit 0
  - `tests/test_version.py` 至少 2 个 test function（CLI test + module-level `__version__` test）
- **commit**：`test: scaffold tests/ with version smoke tests`
- **状态**：Complete

---

## 决策记录

| # | 决策 | 用户选择 | 落地 |
|---|---|---|---|
| D-P1.1 | LICENSE 类型 | Apache 2.0 | Stage P1.A |
| D-P1.2 | GitHub Actions CI | **不做 Phase 1**，需时再加 | Stage 列表删除 ci.yml |
| D-P1.3 | commit 粒度 | 4 个 sub-stage commit | Stage P1.A–P1.D 各一 |

## 中间 commit 不可用的代价

由于 4 个 sub-stage commit 串行：
- commit P1.A 后：仓库有 LICENSE 但还没 pyproject，**`pip install -e .` 失败**
- commit P1.B 后：有 pyproject，但 src/paperterm/ 不存在，**`pip install -e .` 因找不到 package 失败**
- commit P1.C 后：能装能跑 `paperterm version`，但**没 tests**，质量门禁不全
- commit P1.D 后：完整可用

`git bisect` 在 P1.A / P1.B 区间会遇到「无法构建」的临时态。这是 user 选 4-commit 粒度的已知代价；如果未来 bisect 撞上 Phase 1 范围，需要 skip 中间 commit。本规划文档作为 audit 备查。

## 修订记录

- 2026-05-10 codex 一审反馈 → 3 处修订：
  1. **版本 SoT**：pyproject 改用 Hatch `dynamic = ["version"]` + `[tool.hatch.version] path = "src/paperterm/__init__.py"`；`cli.py` 通过 `from . import __version__` 引用；增加 `! grep -F '0.1.0' src/paperterm/cli.py` 反向校验
  2. **ruff/mypy target = py310**：与 `requires-python = ">=3.10"` 公共承诺一致；本地 `.venv` 仍 3.11，不冲突
  3. **`src/paperterm/py.typed` 入 Phase 1**：PEP 561 marker，零成本，让下游识别 paperterm 是 typed package

## 待确认事项

无（D-P1.1–D-P1.3 已敲定，3 处修订已 inline；所有 Stage 成功标准均为可执行命令）。

## Per-Stage 工作流

按 vibe-coding-init 期间的 codex review gate 节奏：

```
Stage P1.A 实施 → codex 审 LICENSE（确认 Apache 2.0 标准文本未被篡改）
              → git add LICENSE → diff --cached --name-only 单文件
              → commit → push
Stage P1.B 实施 → codex 审 pyproject.toml
              → git add pyproject.toml → commit → push
Stage P1.C 实施（含创建 .venv/ + pip install -e .）
              → codex 审 src/paperterm/{__init__,__main__,cli}.py
              → 跑 paperterm version 验证
              → git add src/ → commit → push
Stage P1.D 实施 → codex 审 tests/test_version.py
              → 跑 pytest + ruff + mypy 验证
              → git add tests/ → commit → push
```

## 执行批准

写完本规划后，先送 codex 审本任务方案；通过后开始 Stage P1.A。

---

## 完成记录

| Stage | 内容 | Commit |
|---|---|---|
| Stage 0 | 规划 codex 二审通过 + commit + push | `572de71` |
| Stage P1.A | LICENSE (Apache 2.0, 201 行) | `39371de` |
| Stage P1.B | pyproject.toml (hatchling≥1.27, dynamic version, click only) | `41a5120` |
| Stage P1.C | src/paperterm/{__init__,__main__,cli,py.typed} + .venv + editable install 自检 | `3cea4be` |
| Stage P1.D | tests/ + ruff extend-exclude；pytest/ruff/mypy 全绿 | `51895ea` |

**Phase 1 完成判据 (plan §12)**：✓ `pip install -e .` works；✓ `paperterm version` 输出 `paperterm 0.1.0.dev0`；✓ pytest 2 passed。

**偏差备注**：
- P1.D 顺手改了 P1.B 的 pyproject.toml（加 ruff `extend-exclude`），跨 Stage 修订；理由：lint 排除是 quality gate 配置，发现需求是在跑 ruff 时才暴露的，归 P1.D 范畴
- P1.A 之后 / P1.C 之前的中间 commit 处于「不可装」状态（已在规划「中间 commit 不可用的代价」节预告，user 已接受）
