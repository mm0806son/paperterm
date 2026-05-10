# `.planning/`

[中文](#中文) · [English](#english)

---

## 中文

任务规划与阶段拆解文档。**只放规划性内容，不放代码**。

### 命名规范

```
.planning/{YYYYMMDD}_{task_name}.md
```

- `YYYYMMDD`：起草日期（八位数字）
- `task_name`：任务简短别名，避免与同日其它任务重名

### 任务规划文件格式

参见 [`../.agent-rules/approval.md`](../.agent-rules/approval.md)（先规划后执行规则）。**每个任务规划文件**应包含：

- `## 任务` 标题
- `**背景**` / `**影响范围**` / `**前置条件**`
- 若干 `### Stage N` 段（含 **目标** / **成功标准** / **状态**）
- `## 待确认事项`（执行前需用户决策的开放问题）

> 例外：纯设计文档不必套用以上模板。

### 生命周期

- **追加，不删**。规划文件视为只读历史。
- 每个 Stage 完成后即时更新 `**状态**`：`Not Started` → `In Progress` → `Complete`。
- 任务结束后在文件末尾追加 `## 完成记录`，写完成时间、与原计划的偏差、最终 commit hash。

### 与会话状态的边界

`.cursor/task_plan.md` / `progress.md` / `findings.md` 是**会话级临时**状态，记录当下正在跑的执行细节，不入 git；`.cursor/memory/` 是**本机持久记忆**，也不入 git。**本目录是任务级永久记录，入 git**。

---

## English

Task planning and stage breakdowns. **Planning content only, no
code.**

### Naming

```
.planning/{YYYYMMDD}_{task_name}.md
```

- `YYYYMMDD`: draft date.
- `task_name`: short alias, unique within the day.

### Format of a task plan

See [`../.agent-rules/approval.md`](../.agent-rules/approval.md)
(plan-before-execute rule). Every task plan should contain:

- `## 任务` (Task) heading
- `**背景**` / `**影响范围**` / `**前置条件**`
  (Context / Scope / Prerequisites)
- one or more `### Stage N` sections, each with **Goal**,
  **Success criteria**, **Status**
- `## 待确认事项` (Open questions) — anything needing the
  user's decision before execution

> Pure design documents may skip the template.

### Lifecycle

- **Append, never delete.** Plans are read-only history.
- Update each stage's `**状态**` (Status) as work progresses:
  `Not Started` → `In Progress` → `Complete`.
- When the task is done, append `## 完成记录` (Completion
  record) listing the actual finish time, deviations from the
  plan, and the final commit hash.

### Boundary with session state

`.cursor/task_plan.md` / `progress.md` / `findings.md` are
**session-level scratch** state for the live execution and stay
out of git; `.cursor/memory/` is **machine-local persistent
memory**, also out of git. **This directory is task-level
permanent record, committed to git.**
