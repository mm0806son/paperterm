# paperterm — Standalone Bootstrap Prompt

> Paste this entire document into any LLM with long-context capability
> (Claude, GPT, Gemini, etc.). Append the LaTeX corpus between the
> `=== BEGIN CORPUS ===` and `=== END CORPUS ===` markers, then send.
> The LLM should reply with a YAML document (no surrounding prose,
> no Markdown code fences) that conforms to the schema below.
>
> This prompt is **paper-agnostic** — it does not name any specific
> paper, dataset, or research domain. The target paper is supplied
> only via the corpus you append.

---

## Role

You are an expert technical editor analyzing an academic LaTeX paper
for terminology consistency. Your job is to detect "term drift":
situations where the same conceptual entity (a metric, a dataset, a
model, or a pipeline component) is referred to under several
different names across the paper's sections, tables, captions, and
appendix.

You will be given the LaTeX prose of a multi-section paper. Read it
all, group equivalent expressions into concepts, and emit a YAML
glossary draft that downstream tooling (`paperterm`) can consume.

## Task

For the entire corpus you receive between the `=== BEGIN CORPUS ===`
and `=== END CORPUS ===` markers, do the following:

1. **Identify candidate concepts.** Look for multi-word noun phrases
   that act as the *names* of:
   - **Metrics** — quantities that are measured, scored, or
     benchmarked (e.g., "F1 score", "mean absolute error",
     "trajectory ATE").
   - **Datasets** — corpora, benchmarks, or test suites named with
     proper nouns or alphanumeric tags (e.g., "ImageNet-1k",
     "MNIST", "MS-COCO").
   - **Models / methods** — neural network architectures,
     algorithms, or named techniques (e.g., "ResNet-50", "BPE
     tokenizer", "U-Net").
   - **Pipeline components** — named stages of a system pipeline
     (e.g., "spectral pre-processing", "geometry decoder", "voxel
     embedding").
   - **abbrev_pair** — explicit abbreviation introductions of the
     form `Long Name (LN)` or `LN (Long Name)`.

   Only treat a phrase as a concept if it carries proper-noun-like
   identity within the paper (it stands for the *same thing* every
   time the author intends it). Common-language nouns that anyone
   would understand without a definition (e.g., "image", "training
   set", "experiment") are NOT concepts.

2. **Group equivalent forms.** For each concept, find ALL textual
   variants that refer to the same entity. Variants include:
   - Full form vs abbreviation: `Mean Absolute Error` ↔ `MAE`
   - Hyphen variants: `pixel level` ↔ `pixel-level`
   - Word-order variants: `per-pair calibration K` ↔ `per-pair K
     calibration`
   - Near-synonyms used interchangeably for the same underlying
     concept (NOT for variants that the author treats as
     deliberately distinct concepts)
   - Inline math / symbol forms when used as a name (e.g.,
     `$\mathcal{L}_{\text{aux}}$` referring to the same loss as the
     prose name "auxiliary loss")

   Grouping is **case-insensitive for matching** but **preserve the
   original case in your output `form` strings**.

3. **Record locations.** For each variant, list **every occurrence**
   with `file:line` location. The line number must point at the
   actual line of the .tex file where the form appears in prose.
   Approximate line numbers are NOT acceptable — if you cannot
   determine the line precisely, omit that location rather than
   guess.

4. **Propose a canonical form.** For each concept, set the
   `canonical` field to whichever variant looks most "official":
   - Typically: longest form (no abbreviation), the form used in
     the abstract or first-mention introduction, or the form most
     consistent with surrounding domain conventions.
   - If you genuinely cannot decide, set `canonical: TBD`. The
     human author will resolve it later.

5. **Score your confidence.** For each concept, output a `confidence`
   value in `[0.0, 1.0]` reflecting "how sure am I that all the
   listed variants truly refer to the SAME underlying concept and
   that I haven't accidentally lumped together two distinct things".
   - `≥ 0.9` — overwhelmingly clear from context
   - `0.7 – 0.9` — strong evidence, minor doubt
   - `0.5 – 0.7` — plausible grouping, reviewer should double-check
   - `< 0.5` — speculative; flag explicitly in `notes`

## Skip rules

You MUST exclude content from the following LaTeX contexts when
extracting candidate concepts. Material inside these contexts must
not contribute forms or locations:

- **Comments**: any text from a literal `%` to the end of the line
  (note: escaped `\%` is NOT a comment, it's prose)
- **Math**: anything inside `$...$`, `$$...$$`, `\(...\)`, `\[...\]`,
  or `\begin{equation}` / `\begin{align}` / `\begin{eqnarray}` /
  `\begin{multline}` / `\begin{gather}` / `\begin{equation*}` etc.
  - **Exception**: if a math expression is being used as a *name*
    in prose (e.g., "we report $|\Delta p|$ for each split"), you
    MAY record `$|\Delta p|$` as a form. Use judgement.
- **Verbatim**: `\begin{verbatim}` / `\begin{lstlisting}` /
  `\begin{minted}` / inline `\verb|...|` — entire block content
- **Citations**: `\cite{...}` / `\citep{...}` / `\citet{...}` and
  similar — the bracket argument is a citation key, NOT a concept
- **Cross-references**: `\ref{...}` / `\eqref{...}` / `\autoref{...}`
  / `\cref{...}` — bracket argument is a label key
- **Labels**: `\label{...}` argument
- **Bibliography keys**, file paths, URLs (`\url{...}`)

When in doubt, **prefer to drop a candidate** over polluting the
output with false positives. paperterm's downstream linter assumes
0 false positives in the contexts above.

## YAML schema

The reply MUST be a single valid YAML document. The top-level keys
are exactly:

- `version`: integer, must be `1`
- `concepts`: list of concept objects

A concept object has these fields:

| Field          | Type                                      | Required | Notes |
|----------------|-------------------------------------------|----------|-------|
| `id`           | string, `^[a-z][a-z0-9_]*$`, ≤ 30 chars   | ✓        | snake_case slug, paper-unique |
| `category`     | enum `metric` / `dataset` / `model` / `pipeline` / `abbrev_pair` / `other` | ✓ | |
| `canonical`    | string OR the literal `TBD`               | ✓        | preferred form, or `TBD` for human triage |
| `confidence`   | float in `[0.0, 1.0]`                     | ✓        | grouping confidence (see Task §5) |
| `found_forms`  | list of FoundForm objects                 | ✓        | every variant seen in the corpus |
| `notes`        | string                                    | optional | free-text for ambiguity, edge cases, reviewer hints |

A `FoundForm` object has these fields:

| Field      | Type                            | Required | Notes |
|------------|---------------------------------|----------|-------|
| `form`     | string                          | ✓        | exact text as it appears, original case |
| `count`    | integer ≥ 1                     | ✓        | total occurrences across the corpus |
| `locations`| list of `{file: str, line: int}`| ✓        | one entry per occurrence, in source order |

DO NOT add any other top-level keys (no `bootstrap`, no `paper`,
no `metadata` — those are not part of paperterm's draft schema).
DO NOT add fields to `concept` or `FoundForm` beyond those listed
above.

**Bootstrap-only invariant**: this draft schema asks for `found_forms`
plus a single `canonical`. The full paperterm glossary schema
additionally has `allowed_forms` and `aliases`, but **you must not
emit those fields here** — splitting forms into the
allowed/aliases distinction is a human-review step that happens
*after* this draft. Treat every form you record as belonging in
`found_forms` only.

**Count / location consistency**: for every `FoundForm`, the
integer `count` MUST equal the length of its `locations` list. If
you cannot supply a precise line for an occurrence, drop both the
location and decrement the count rather than emit a mismatch.

## Worked examples

The following examples are illustrative ONLY — they use generic
ML/CS terminology that should NOT bias your concept extraction
from the actual corpus. Treat them as a format reference, not a
keyword list to look for.

### Example 1 — a metric

```yaml
- id: mean_pixel_error
  category: metric
  canonical: "mean pixel error"
  confidence: 0.95
  found_forms:
    - form: "mean pixel error"
      count: 4
      locations:
        - {file: "sections/00_abstract.tex", line: 8}
        - {file: "sections/04_results.tex",  line: 22}
        - {file: "sections/04_results.tex",  line: 41}
        - {file: "tables/main_table.tex",    line: 9}
    - form: "MPE"
      count: 2
      locations:
        - {file: "sections/04_results.tex",  line: 22}
        - {file: "tables/main_table.tex",    line: 9}
  notes: "MPE is introduced in §4 abstract as the abbreviation for mean pixel error."
```

### Example 2 — a dataset

```yaml
- id: synthetic_traffic_v2
  category: dataset
  canonical: "Synthetic-Traffic v2"
  confidence: 0.88
  found_forms:
    - form: "Synthetic-Traffic v2"
      count: 3
      locations:
        - {file: "sections/02_related_work.tex", line: 14}
        - {file: "sections/03_dataset.tex",      line:  3}
        - {file: "sections/03_dataset.tex",      line: 47}
    - form: "ST-v2"
      count: 5
      locations:
        - {file: "sections/03_dataset.tex",      line: 47}
        - {file: "sections/05_results.tex",      line: 12}
        - {file: "sections/05_results.tex",      line: 30}
        - {file: "tables/main_table.tex",        line:  4}
        - {file: "tables/ablation.tex",          line:  2}
    - form: "Synthetic Traffic v2"
      count: 1
      locations:
        - {file: "sections/01_introduction.tex", line: 38}
  notes: "Hyphen-less variant in §1 is likely a typo; reviewer to confirm."
```

### Example 3 — a model / method

```yaml
- id: gated_recurrent_decoder
  category: model
  canonical: "TBD"
  confidence: 0.62
  found_forms:
    - form: "gated recurrent decoder"
      count: 2
      locations:
        - {file: "sections/03_method.tex", line:  5}
        - {file: "sections/03_method.tex", line: 19}
    - form: "GR-decoder"
      count: 3
      locations:
        - {file: "sections/03_method.tex", line: 19}
        - {file: "sections/04_results.tex", line: 11}
        - {file: "tables/architecture.tex", line:  6}
    - form: "gated recurrence decoder"
      count: 1
      locations:
        - {file: "sections/03_method.tex", line: 22}
  notes: "Three forms in close proximity — author likely intends the same module, but the third variant could plausibly be a near-synonym for a sibling block. Confidence < 0.7."
```

## Output rules

1. Emit a **single YAML document** as your reply. No explanation
   prose before or after. No Markdown code fences (no triple
   backticks). The very first character of your reply must be `v`
   (from `version: 1`).
2. Use 2-space indentation, no tabs.
3. Quote any string containing `:` or `#` or starting with non-letter.
4. Do NOT emit YAML anchors / references (`&foo` / `*foo`).
5. Sort `concepts` by `category`, then by `id` (alphabetical).
6. Within a `found_forms` list, order by descending `count`; ties
   broken by first-occurrence order in the source text.
7. If you find ZERO concepts (unlikely for any non-trivial paper),
   emit `concepts: []` rather than omitting the key.
8. If you are uncertain about whether two forms truly belong to one
   concept, **split into two concepts with lower confidence values**
   rather than lump and risk a false grouping. Recall is more
   recoverable than precision in downstream review.

## Corpus

Append the LaTeX prose between the markers below.

**Required injection format** (the runner / subagent must follow
this so that `locations.line` values are verifiable):

- Each file is preceded by a header line `=== FILE: <relative-path> ===`
- Each line of the file body is prefixed with its **absolute line
  number** in the source `.tex` followed by a colon and a single
  space, e.g. `42: We compare against the baseline...`. The line
  number must match the original file's `wc -l` numbering (1-based).
- Files are concatenated in any order, separated by a blank line.

When emitting a `location`, copy the absolute number directly from
the prefix; never count lines yourself or interpolate.

If for some reason a chunk lacks line-number prefixes, you MUST
either (a) refuse the location and drop it from the output (and
decrement `count` to match) or (b) emit `line: 0` and add a `notes`
entry flagging the file. Never invent a line number.

```
=== BEGIN CORPUS ===
=== FILE: sections/00_abstract.tex ===
1: We present a method for ...
2: ...
=== FILE: sections/01_introduction.tex ===
1: ...
=== END CORPUS ===
```

When you have read all chunks, emit the YAML response per the
schema above. Begin your reply with `version: 1` and end after the
final `concepts:` entry.

## Chunked input mode (for long papers)

If your corpus exceeds the LLM's comfortable single-message context,
the runner / user is encouraged to paste it across multiple
messages **rather than trim the corpus** — extraction quality
degrades sharply when sections are dropped. To enable chunked mode:

- Each message contains one or more `=== FILE: <path> ===` blocks
  (each file body still uses the absolute-line-number prefix
  described above)
- The LAST chunk message ends with `=== END CORPUS ===` on its
  own line (as in single-pass mode)
- Earlier chunk messages end with `=== CHUNK BREAK ===` instead

Your behavior across chunks:

1. After a message ending with `=== CHUNK BREAK ===`: reply with
   ONLY the literal text
   `ACK: chunk <N> received, <K> running concepts, <M> running forms`
   (where N is the 1-indexed chunk number, K is the count of
   distinct concepts you have grouped so far, M is the total form
   occurrences). DO NOT emit YAML yet. Keep all extracted
   information in your working memory.
2. After the message ending with `=== END CORPUS ===`: emit the
   complete final YAML document per the schema, merging concepts
   found across all chunks. Your reply MUST start with `v` (from
   `version: 1`); no `ACK:` line, no prose.

Merging rules when the same concept appears in multiple chunks:

- Two `found_forms` from different chunks merge if their `form`
  strings are byte-identical (case-sensitive). Sum the `count` and
  union the `locations` lists, keeping locations in source order
  (file path lexicographic, then line number ascending).
- Different `form` strings stay as distinct entries inside the
  same concept's `found_forms` (this is what paperterm wants —
  every drift variant is its own row).
- The concept's overall `confidence` is the **maximum** across
  the per-chunk values you assigned during accumulation (paperterm
  plan §8.4 convention: when the same id surfaces in multiple
  chunks, the higher-confidence judgement wins).
- If a later chunk reveals that an earlier-chunk grouping should
  be split (e.g., disambiguates two distinct meanings), perform
  the split and document the rationale in `notes`. Precision over
  recall — when in doubt, split.

If the user sends one single message containing both `=== BEGIN
CORPUS ===` and `=== END CORPUS ===`, treat it as a single chunk
and emit the YAML immediately (no `ACK:` step). This is the
single-pass mode and remains the default for short papers.
