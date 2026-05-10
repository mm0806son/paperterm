# paperterm demo — `paperterm check` against the Raw2Event paper

Status: **first end-to-end demo** delivered after Phase 1–4 of plan §12.

## What this shows

Plan §1.1 motivated paperterm with two real drift cases from the
Raw2Event NeurIPS paper:

| Concept | # surface forms in the paper |
|---|---|
| `per-pixel EMD` (a metric) | 6 |
| `per-pair K calibration` (a pipeline component) | 10+ |

The `paperterm check` subcommand now finds those drifts on its own,
together with several others (e.g. four different names for the
"upstream event-statistics diagnostic" table).

## Inputs

- **Glossary**: [`example/raw2event_glossary.yaml`](raw2event_glossary.yaml)
  — hand-curated from the dogfood draft (`example/output/glossary.draft.yaml`)
  by promoting six high-confidence concepts into the production schema.
  See the file header for the exact promotion procedure (drop
  `found_forms`, pick a canonical, move the rest into `aliases` /
  `allowed_forms`).
- **Paper source**: `/vol1/1007/projects/raw2event/doc/paper/`
  (sections + tables; appendices included). Not vendored into the
  paperterm repo.

## How to reproduce

From the paperterm repo root:

```bash
.venv/bin/paperterm check /vol1/1007/projects/raw2event/doc/paper \
    --glossary example/raw2event_glossary.yaml \
    --include 'sections/**/*.tex' \
    --include 'tables/*.tex'
```

## What the output should look like

Captured run is checked in at
[`example/dogfood_check_output.txt`](dogfood_check_output.txt) — 18
violations, exit code 1.

Each line is `<file>:<line>:<col>  [<context>]  '<found>'  →
'<suggestion>'  (<concept_id>)`. Highlights:

- `sections/00_abstract.tex:7  'per-pixel count EMD'  →  'per-pixel EMD'`
- `sections/01_introduction.tex:51  'pixel-level EMD'  →  'per-pixel EMD'`
- `sections/04_benchmark.tex:38  'spatial per-pixel EMD'  →  'per-pixel EMD'`
- `sections/appendix/A_datasheet.tex:151  'upstream event-statistics table'  →  'upstream event-statistics diagnostic'`
- `tables/within_prefix_rho.tex:5  [caption]  'spatial px-EMD'  →  'px-EMD'`

The `[caption]` tag on the last line is the LaTeX context tag
(plan §3.4): the walker correctly parsed `\caption{}` so paperterm
knows it is *not* prose.

## Exit codes (plan §6.3)

| code | meaning | demo behaviour |
|---|---|---|
| 0 | no violation | will switch to this once we accept all suggestions |
| 1 | at least one violation | what you see here |
| 2 | hard error (missing/draft glossary, parse failure) | tested separately, see `tests/test_linter.py` |

## Known v0.1 limitations exposed by this demo

1. **Forms containing `$...$` math symbols are not yet matchable**
   (the LaTeX walker peels math out of the prose stream before the
   matcher sees it). This is why the `per-pair K calibration`
   concept in the glossary intentionally drops the `$K$` variants
   and only ships `per-pair calibration` / `per-camera-pair K
   calibration` aliases. dogfood findings.md §6 P5 already flagged
   this; a future phase can add a `math:` form prefix.
2. **No auto-fix**: paperterm reports, the human edits. This is
   plan §1.3 v0.1 non-goal #2.
3. **No multi-file `\input{}` expansion**: `paperterm check` walks
   the files matched by `--include` directly. The Raw2Event main
   shell (`neurips_2026.tex`) is mostly `\input{}` plumbing and
   would have produced almost no concept hits even if included; we
   exclude it here for clarity.

## Where to go next

- Phase 5 (delivered): `paperterm bootstrap` + `paperterm
  print-prompt` make the dogfood loop a single CLI call. See
  `docs/usage.md` for the end-to-end recipe.
- ~~Phase 6: Anthropic-API provider for `bootstrap`.~~ **Dropped
  in v0.1.** paperterm intentionally ships no API integration —
  users run their own LLM (Claude.ai / ChatGPT / …) and paste the
  YAML reply back. A future major version may revisit.
- Phase 7 candidates: tighter docs, JSON / SARIF report formats,
  `math:` form prefix (so glossary entries can match `$K$`-style
  symbolic forms — see findings.md §6 P5).
