# paperterm — Usage

`paperterm` is a LaTeX-aware terminology consistency linter for
academic papers. It does **not** call any external API: it ships a
single prompt that you paste into your own LLM (Claude.ai, ChatGPT,
Gemini, …) to produce a draft glossary, then a fully local CLI to
lint your `.tex` against that glossary.

This page walks through the end-to-end workflow from a clean clone.

## Install

```bash
git clone git@github.com:mm0806son/paperterm.git
cd paperterm
python3.11 -m venv .venv
.venv/bin/pip install -e ".[dev]"
.venv/bin/paperterm version   # → "paperterm 0.1.0.dev0"
```

paperterm runs on Python ≥ 3.10.

## Workflow at a glance

```
+----------------+     +-------------+     +----------------+     +----------------+
| paperterm      | --> | your LLM    | --> | hand-promote   | --> | paperterm      |
| bootstrap or   |     | (Claude.ai, |     | draft to final |     | check          |
| print-prompt   |     | ChatGPT, …) |     | glossary.yaml  |     | (local lint)   |
+----------------+     +-------------+     +----------------+     +----------------+
```

The LLM step is the **only** stage that needs an LLM, and it is
manual — paperterm only assembles the prompt and the cleaned corpus.

## 1. Prepare the prompt and corpus

Two equivalent entry points:

### A. `paperterm bootstrap <paper_dir>` (recommended)

Walks every `.tex` under `<paper_dir>` through paperterm's LaTeX
parser, drops math / verbatim / comments / `\cite{…}` / `\ref{…}` /
`\label{…}` / URLs, and writes a single file containing the standalone
prompt followed by the AST-cleaned corpus:

```bash
.venv/bin/paperterm bootstrap path/to/your/paper
# → wrote path/to/your/paper/.paperterm_prompt.txt
```

Use `--include` / `--exclude` (repeatable globs) to scope which
files contribute. Use `--output` to write somewhere other than
`<paper_dir>/.paperterm_prompt.txt`.

### B. `paperterm print-prompt`

If you want to manage the corpus yourself, just emit the
paper-agnostic prompt:

```bash
.venv/bin/paperterm print-prompt > prompt.md
# then append your .tex contents between the
# === BEGIN CORPUS === / === END CORPUS === markers
```

## 2. Run your LLM

Open Claude.ai, ChatGPT, Gemini, or any chat UI you already pay
for, paste **the entire contents** of the file from step 1, and
send. The prompt instructs the model to reply with a single YAML
document (no Markdown fences, starts with `version: 1`).

Save the reply to `<paper_dir>/glossary.draft.yaml`.

> Tip: if your paper is very long, split the corpus across several
> messages — the prompt explains the *chunked input mode*
> (`=== CHUNK BREAK ===` between chunks, `=== END CORPUS ===`
> after the last). The model accumulates state across messages and
> emits one merged YAML at the end.

## 3. Hand-promote the draft

`paperterm check` deliberately refuses to run on a draft. The
review step is one of the highest-leverage parts of the workflow:
the human deciding which form is canonical and which forms are
true aliases is what makes the lint actionable later.

For each concept in `glossary.draft.yaml`:

1. Drop the `found_forms` list and the `confidence` value (those
   are bootstrap-only fields).
2. Pick a `canonical` (replace any `TBD`).
3. Move the remaining variants into either:
   - `aliases:` — names you do **not** want anywhere in the paper
     (or only want in specific contexts via `contexts: …`); or
   - `allowed_forms:` — abbreviations / symbols you accept, often
     restricted with `contexts: [table, figure, caption]`.
4. Save the result as `<paper_dir>/glossary.yaml`.

Optional: extend a paperterm-supplied base glossary so common
ML / event-camera terminology is covered for free:

```yaml
version: 1
extends:
  - paperterm:base/ml-common.yaml
  - paperterm:base/event-camera.yaml
concepts:
  - id: my_metric
    category: metric
    canonical: "my custom metric"
    aliases:
      - form: "my-metric"
```

The `paperterm:base/<file>` URI dispatches to the YAML files
shipped under `src/paperterm/data/base/`. See
`example/raw2event_glossary.yaml` for a complete real-world
example.

## 4. Lint

```bash
.venv/bin/paperterm check path/to/your/paper
```

Default exit codes (paperterm `check`):

| code | meaning |
|------|---------|
| 0 | no violation |
| 1 | at least one violation |
| 2 | hard error (missing/draft glossary, parse failure) |

`--include` / `--exclude` mirror the `bootstrap` flags;
`--glossary <file>` overrides the default
`<paper_dir>/glossary.yaml`.

Each reported line has the shape:

```
<file>:<line>:<col>  [<context>]  '<found>'  →  '<suggestion>'  (<concept_id>)
```

The `[context]` tag is the LaTeX context tag the walker assigned
(`prose` / `caption` / `table` / `figure`). Suggestions come from
the alias's `suggest:` field, falling back to the concept's
`canonical`.

## Reference

- Detailed design: `.planning/20260508_paperterm_v0.1_design.md`
- Worked dogfood example: `example/` (full prompt run on the
  Raw2Event NeurIPS paper, hand-curated glossary, captured
  `paperterm check` output, evaluation notes).
