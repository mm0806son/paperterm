# `example/` — paperterm bootstrap prompt dogfood

本目录是一次**端到端 dogfood**：在 paperterm CLI 实现之前，用一个
subagent 模拟未来 `paperterm bootstrap --provider manual` 命令的执行
路径，验证 plan §8.1 设计的 **standalone bootstrap prompt** 与
plan §5 的 **glossary YAML schema** 在真实 NeurIPS 论文上是否能产出
可用结果。

**目标论文**：Raw2Event NeurIPS 2026 D&B paper，仓库位于
`/vol1/1007/projects/raw2event/doc/paper/`（不在本仓库内；见
`inputs/corpus_manifest.txt`）。

**这是测试存档，不是 paperterm 的对外样例。** v0.1 真正发版时本目录会被
迁移为 `tests/fixtures/glossary/raw2event_bootstrap.yaml` 的来源。

## 目录

```
example/
├── README.md                    ← 本文件
├── prompt.md                    ← paper-agnostic standalone bootstrap prompt
├── inputs/
│   └── corpus_manifest.txt      ← 待扫描的 .tex 路径清单（不含正文，仅路径 + 行数）
├── output/
│   ├── glossary.draft.yaml      ← subagent 产出的术语 yaml（51 concepts）
│   └── run_log.md               ← subagent 自述运行过程 + 自评 prompt 缺陷
└── findings.md                  ← 主 agent 人工评估 + ROI 排序的改进清单
```

## 运行设置

| 维度 | 取值 |
|---|---|
| Subagent 类型 | `general-purpose`（Claude Code Agent 工具） |
| Model | Opus（`claude-opus-4-7`） |
| 输入 | `prompt.md`（paper-agnostic）+ `inputs/corpus_manifest.txt`（26 paths）|
| Corpus 大小 | 2200 行 / ~33K tokens（single-pass，未触发 chunked mode） |
| Subagent 限制 | 只读 `paper/` + `example/`，只写 `example/output/`，禁 git mutating |
| 跑前 baseline | `.cursor/dogfood_baseline_{paperterm,raw2event}.txt`（不入 git） |
| 后验校验 | raw2event 仓库 HEAD/status 与跑前完全一致 ✓；paperterm 仓库无越权写入 ✓ |

## 关键结果

- **51 concepts** 抽出（12 abbrev_pair / 8 dataset / 11 model / 9 metric / 10 pipeline / 1 other）
- **3 / 3 ground truth seeds 命中**（Raw2Event / DAVIS346 / DVS-Voltmeter）
- **drift ≥ 5 forms 的 concept 共 10 条**，最严重的 `per_pair_k_calibration`
  10 forms — paperterm v0.1 motivating example（plan §1.1 列举的
  per-pixel EMD 6 forms）在本论文精确复现
- **行号准确性抽样 10/12 PASS**（错误率 17%，集中在高频 token Raw2Event 上）
- **subagent + 主 agent 联合识别 8 个 paperterm 改进点**，按 ROI 排序后
  写入 `findings.md` 第 7 节

## 复现步骤（说明性，未来 paperterm CLI 可用时会被取代）

```bash
# 1. baseline 记录（防 subagent 越权写入）
git -C /vol1/1007/projects/raw2event status --short \
    > .cursor/dogfood_baseline_raw2event.txt

# 2. 启动 general-purpose subagent，model = opus，brief 见 .planning/...
#    输入：prompt.md + corpus_manifest.txt
#    输出限制：只能写 example/output/ 下两个文件
#    （Claude Code: Agent tool with subagent_type=general-purpose, model=opus）

# 3. 后验校验
diff <(git -C /vol1/1007/projects/raw2event status --short) \
     <(grep -A1000 '=== status ===' .cursor/dogfood_baseline_raw2event.txt | tail -n +2)
# diff 应为空：subagent 没碰过 raw2event

# 4. yaml 结构 grep 校验（不依赖 PyYAML）
head -1 example/output/glossary.draft.yaml | grep -q '^version: 1$'
grep -q '^concepts:' example/output/glossary.draft.yaml
test $(grep -cE '^- id:' example/output/glossary.draft.yaml) -ge 5
```

## 与 paperterm v0.1 的关系

本 dogfood 验证了 plan §8.5 描述的「**Standalone prompt（无安装路径）**」
工作流的可行性，并提前暴露 8 处 prompt + schema 缺陷。这些缺陷**会**驱动
plan §12 Phase 1 真正写 `src/paperterm/prompts.py` / `bootstrap.py` 时的
具体实现选择 —— 详见 `findings.md` 第 7 节的 ROI 排序清单。

设计文档完整版：[`.planning/20260508_paperterm_v0.1_design.md`](../.planning/20260508_paperterm_v0.1_design.md)
本次任务规划：[`.planning/20260509_dogfood_bootstrap_prompt.md`](../.planning/20260509_dogfood_bootstrap_prompt.md)
