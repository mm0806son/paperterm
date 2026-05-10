## 任务：Phase 5 — 用户自带 LLM 的端到端工作流（无 API 依赖）

**背景**：Phase 4 demo (`d006739`) 验证了 `paperterm check` 能检出真实漂移。但目前用户要拿到 glossary.yaml 必须**手工**：(a) 把 example/prompt.md 抄出来 / (b) 在自己 LLM 里粘贴 prompt + 论文 / (c) 把回复存成 yaml / (d) 转成正式 glossary。Phase 5 的目标是把 (a) 自动化（`paperterm print-prompt`）并可选地把 (b) 也自动化（`paperterm bootstrap` 把 prompt + AST-清洗 corpus 拼成单文件给用户粘）。

**用户决策**：
- ❌ **不做 anthropic provider**（plan §6.2 / §8.2 整段在 v0.1 won't-fix）
- ✓ paperterm 只提供 prompt + base glossary 库，用户用自己 LLM 跑、自己 review，paperterm CLI 只负责 print-prompt + check
- ✓ 兼容 plan §6.2 「manual provider」路径（不调任何 API）

**Phase 5 deliverable**：

| Sub-stage | 内容 | commit message 草稿 |
|---|---|---|
| P5.A | `src/paperterm/prompts.py` 含 `BOOTSTRAP_PROMPT` 字符串常量（从现有 `example/prompt.md` 移植，paper-agnostic）；`tests/test_prompts.py` 仅测 `BOOTSTRAP_PROMPT` 内容（schema/skip-rules/example anchor + 反污染 grep） — `prompts/glossary_bootstrap.md` 一致性测试推到 P5.D | `feat(prompts): add BOOTSTRAP_PROMPT as single source of truth` |
| P5.B | `src/paperterm/bootstrap.py` 实现 manual mode：扫 .tex → 调 `latex.iter_spans` 提 prose → 按 plan §8.4 拼 corpus（行号 prefix）→ 与 BOOTSTRAP_PROMPT 拼成单文件；`tests/test_bootstrap.py` | `feat(bootstrap): manual mode for AST-cleaned prompt + corpus` |
| P5.C | `cli.py` 加 `print-prompt` 与 `bootstrap` 子命令；CLI 测试加到 `tests/test_linter.py` 或新建 `tests/test_cli_bootstrap.py` | `feat(cli): add print-prompt and bootstrap subcommands` |
| P5.D | 生成 `prompts/glossary_bootstrap.md`（checked-in，是 `paperterm print-prompt` 的 byte-equal 输出）；`tests/test_prompts.py` 加 `test_checked_in_prompt_matches_module()` 用 `Path("prompts/glossary_bootstrap.md").read_text() == BOOTSTRAP_PROMPT`；`docs/usage.md` 写英文用户工作流（plan §1.3 user-facing 英文）；删除 `example/prompt.md`（双源），同时 sed 更新 `example/README.md` / `example/findings.md` / `example/demo.md` 中所有指向 `example/prompt.md` 的引用为 `prompts/glossary_bootstrap.md`（grep 验证 0 残留） | `docs: ship standalone prompt file and end-to-end usage doc` |

**关键设计**：

1. **Prompt 单源**（plan §8.5）：
   - SoT = `src/paperterm/prompts.py` 的 `BOOTSTRAP_PROMPT` 字符串
   - `prompts/glossary_bootstrap.md` 由 `paperterm print-prompt` 生成；`tests/test_prompts.py` 加 `test_checked_in_prompt_matches_module()` 用 `Path("prompts/glossary_bootstrap.md").read_text() == BOOTSTRAP_PROMPT` 守住
   - 旧 `example/prompt.md` 删除，文件位置改为 `prompts/glossary_bootstrap.md`（plan §8.5 路径），避免「两份手写 prompt」

2. **`paperterm bootstrap <paper_dir>` 行为**（manual mode 唯一路径）：
   - `--include` / `--exclude` 与 `paperterm check` 一致
   - 默认 `--output <paper_dir>/.paperterm_prompt.txt`
   - 输出文件结构：`BOOTSTRAP_PROMPT\n\n=== BEGIN CORPUS ===\n<chunks>\n=== END CORPUS ===\n`
   - chunk 格式：`=== FILE: <relative-path> ===\n<L>: <line>\n<L+1>: <line>\n...\n`（每行带绝对行号 prefix，匹配 prompt 中 Corpus 节要求）
   - 退出码 0；stdout 打印**正确指引**（注意：`paperterm check` 拒绝 draft，必须先 review）：
     ```
     Prompt written to: <output>
     Next steps:
       1. Paste <output> into any LLM and capture its YAML reply.
       2. Save the reply as <paper_dir>/glossary.draft.yaml (this is a draft).
       3. Hand-promote the draft to <paper_dir>/glossary.yaml:
          - drop every found_forms / confidence field
          - choose a canonical (replace any "TBD")
          - move remaining forms into aliases / allowed_forms
       4. Run `paperterm check <paper_dir>`.
     ```

3. **`paperterm print-prompt`**：
   - 输出 BOOTSTRAP_PROMPT 到 stdout
   - 不带 `=== BEGIN CORPUS ===` 块（用户自己附论文）
   - `--output PATH` 选项写入文件

4. **`docs/usage.md`**（英文，plan §1.3）：
   - Quickstart：`pip install -e .` → `paperterm print-prompt > prompt.md` → 在 LLM 里粘 prompt + 自己论文 → 保存 yaml → `paperterm check`
   - 进阶：`paperterm bootstrap` 自动准备 prompt+corpus
   - Glossary 编辑指南（draft → production：删 found_forms / 选 canonical / 设 aliases）
   - extends 用法（继承 paperterm:base/event-camera.yaml）

**质量门禁**（每 sub-stage 强制满足）：
- `pytest tests/` 全绿
- `ruff check .` + `ruff format --check .` 全绿
- `mypy` 全绿
- 每 sub-stage commit 前过 codex 短审

**Per-sub-stage 工作流**（按 user 之前要求 sub-phase 也 commit）：
1. 实施 → 跑门禁 → codex 短审 → commit + push → 进下一 sub-stage

**完成判据**：
- `paperterm print-prompt` 能跑，输出与 `prompts/glossary_bootstrap.md` 一致
- `paperterm bootstrap raw2event/doc/paper` 能跑，输出文件可直接粘到 LLM
- 文档让全新用户 5 分钟能跑通端到端
- 全局 tests/ pass + 三类门禁绿

## 待确认事项

无（用户对 anthropic 砍除态度明确，sub-stage commit 节奏已定）。

---

## 完成记录

| Sub-stage | commit | 关键产物 |
|---|---|---|
| P5.A | `3a5edc4` | src/paperterm/data/bootstrap_prompt.md（357 行 SoT）+ src/paperterm/prompts.py（importlib.resources 加载）+ 24 anchor/反污染 tests |
| P5.B | `f0463f3` | src/paperterm/bootstrap.py（AST-cleaned 拼装；已修同行 inline math/cite/comment 不泄漏 + pathlib exclude dir 递归）+ 12 tests |
| P5.C | `dc8a20b` | cli.py 加 print-prompt + bootstrap 子命令；4 步 manual flow 指引；6 CLI tests |
| P5.D | `c412468` | prompts/glossary_bootstrap.md（byte-equal SoT）+ docs/usage.md（英文端到端文档）+ README 重写 + 删 anthropic extra + 删 example/prompt.md（git rename）+ 历史引用清理 |

**全程门禁**：100 tests pass / ruff check + format / mypy strict 全绿，每 commit 通过 codex 短审。

**用户验证入口**：
- `paperterm bootstrap <paper_dir>` — 本地准备 prompt+corpus 文件
- 粘到 Claude.ai / ChatGPT / 任意 LLM 订阅
- 保存 YAML 回复为 `glossary.draft.yaml`
- 人工 review → `glossary.yaml`
- `paperterm check <paper_dir>` — 本地 lint
- 端到端**零网络调用**；详见 docs/usage.md。

**plan §6.2 anthropic provider 永久 won't-fix（v0.1）**；plan 设计文档保留作未来重启的参考稿。
