# paperterm dogfood run — Raw2Event NeurIPS 2026 paper

Run date: 2026-05-09. Sub-agent: Claude (claude-opus-4-7).
Inputs: `prompts/glossary_bootstrap.md` (then known as `example/prompt.md`,
moved to `prompts/glossary_bootstrap.md` in P5.D) + `example/inputs/corpus_manifest.txt`.

## Files read

All 26 manifest entries were read (in manifest order). Corpus is a single
LaTeX paper rooted at `/vol1/1007/projects/raw2event/doc/paper/`. Total
size processed: **~132 KB** across the 26 source files (≈ 33 K tokens
estimated).

| # | File (relative to paper root)                         | Lines |
|---|-------------------------------------------------------|-------|
|  1 | `neurips_2026.tex`                                   | 107   |
|  2 | `sections/00_abstract.tex`                           | 16    |
|  3 | `sections/01_introduction.tex`                       | 54    |
|  4 | `sections/02_related_work.tex`                       | 103   |
|  5 | `sections/03_dataset.tex`                            | 109   |
|  6 | `sections/04_benchmark.tex`                          | 46    |
|  7 | `sections/05_results.tex`                            | 69    |
|  8 | `sections/06_discussion.tex`                         | 34    |
|  9 | `sections/07_conclusion.tex`                         | 10    |
| 10 | `sections/99_appendix.tex`                           | 30    |
| 11 | `sections/appendix/A_datasheet.tex`                  | 357   |
| 12 | `sections/appendix/B_acquisition.tex`                | 222   |
| 13 | `sections/appendix/C_supplementary.tex`              | 105   |
| 14 | `sections/appendix/D_k_calibration.tex`              | 455   |
| 15 | `sections/appendix/E_compute.tex`                    | 66    |
| 16 | `sections/appendix/F_reproducibility.tex`            | 40    |
| 17 | `tables/cross_modal.tex`                             | 26    |
| 18 | `tables/k_health.tex`                                | 32    |
| 19 | `tables/paired_branch_delta.tex`                     | 17    |
| 20 | `tables/prior_datasets.tex`                          | 75    |
| 21 | `tables/prior_datasets_full.tex`                     | 108   |
| 22 | `tables/retrieval.tex`                               | 21    |
| 23 | `tables/self_retrieval.tex`                          | 18    |
| 24 | `tables/variant_matrix.tex`                          | 33    |
| 25 | `tables/within_prefix_rho.tex`                       | 23    |
| 26 | `tables/within_prefix_rho_dt.tex`                    | 24    |

No file was skipped. The orchestrator file `neurips_2026.tex` is
mostly preamble + `\input{}` plumbing and contributed almost no
concept locations (only the title used the form `Raw2Event` in
prose, but that occurrence is inside `\title{}` which I did not
record because the prompt does not list `\title` as an exempt
context — see "edge cases" below).

## Concept count by category

```
abbrev_pair : 12
dataset     :  8
metric      :  9
model       : 11
other       :  1
pipeline    : 10
TOTAL       : 51
```

## Concepts with confidence < 0.7

Only one: **`cifar10_dataset_protocol`** at `0.6`.

Reason for low confidence: the paper uses at least three distinct
"CIFAR-10 ... protocol" surface forms that lump together what are
actually **two different** procedural concepts — the *acquisition
protocol* (how the rig captured data, see §3 / Appendix B) and the
*sim-to-real classification protocol* (how trained classifiers are
evaluated, see §4.4 / §5.2). The abstract puts both flavours in a
single sentence ("an open benchmark for evaluating frame-to-event
simulators against real DAVIS346 events under a controlled CIFAR-10
acquisition protocol [...] a downstream CIFAR-10 sim-to-real transfer
protocol"), and this draft followed the prompt's recall-over-precision
rule: I lumped, marked low confidence, and flagged in `notes` that a
human reviewer should split. This is the single most important
human-review action item from this draft.

The other entries that hover near the 0.7 floor (raw_bayer_stream
0.75, isp_rgb_stream 0.7, metric_px_emd 0.75, per_pair_k_calibration
0.7, upstream_diagnostic 0.7, one_mpx_automotive 0.7) are documented
inline in their respective `notes` fields; they reflect either
predicate-vs-noun ambiguity (post-ISP vs ISP-RGB), a possible
factual error in the paper (one_mpx_automotive table cites
`perotLearningDetectObjects2020` which is GEN1 304×240, not 1 Mpx),
or terminology overload (per-pair K has at least 10 surface variants
in 4 sections).

## Locations dropped during validation

Three location-drop incidents are documented:

1. **`pi_camera_module_3` / form `Module~3` on `sections/03_dataset.tex` line 46.**
   That line is inside a multi-line commented-out figure block (each
   line is `% ...`), so per the prompt's "Comments" skip rule it
   cannot contribute a location. I dropped the location and the form
   `Module~3` (its only candidate occurrence) was therefore removed
   from the FoundForm list rather than emitting `count: 0`.

2. **`abbrev_isp` / form `ISP` on `sections/01_introduction.tex` line 16.**
   I initially included this location based on a paraphrase
   ("image-processing pipeline") that does not contain the literal
   substring "ISP". Dropped during the count-vs-locations
   self-validation pass.

3. **`abbrev_isp` / form `ISP` on `sections/01_introduction.tex` line 35.**
   That line contains `ISP-RGB` (a compound), not bare `ISP`. The
   compound is recorded under the sibling concept `isp_rgb_stream`,
   so this `ISP` location was dropped from `abbrev_isp` to avoid
   double-counting.

Counts in the YAML have been decremented to match each drop.

## Self-validation outcome

After writing `glossary.draft.yaml`, I re-parsed it with PyYAML and
checked:

- ✓ first line is `version: 1`
- ✓ top-level keys are exactly `{version, concepts}`
- ✓ no `bootstrap` field, no `suggested_canonical` substring
- ✓ every FoundForm satisfies `count == len(locations)` and `count ≥ 1`
- ✓ every `category` ∈ {metric, dataset, model, pipeline, abbrev_pair, other}
- ✓ every `id` matches `^[a-z][a-z0-9_]*$` and is ≤ 30 chars
- ✓ no duplicate ids
- ✓ concepts are sorted by `(category, id)` ascending
- ✓ within each `found_forms`, sorted by descending `count`
- ✓ 51 concepts ≥ the 5-concept floor

The first attempt **failed** validation in three ways, which I fixed
in-session before final emission rather than triggering the "save and
flag" retry path:

1. Concepts were not sorted by `(category, id)` because I authored
   them in topical order. Fixed with a programmatic `sort_keys` pass.
2. Found-form lists were not sorted by descending `count`. Same pass
   fixed it.
3. One `id` (`aprilTag`) violated the snake_case regex. Renamed to
   `april_tag`.
4. One FoundForm (`davis346 / DAVIS346`) had `count: 60` but 61
   locations. Off-by-one accounting error from manual counting.
   Adjusted count to 61.
5. One concept (`paired_bootstrap_ci`) had a placeholder FoundForm
   with `count: 0` and empty locations, violating the `count ≥ 1`
   rule. Removed the empty form before final dump.

After these fixes, the second self-validation pass returned 0
errors. **No retry of the full YAML emission was needed**; the
fixes were targeted edits / a programmatic re-sort.

## Honest dogfood assessment of paperterm's prompt + schema

The prompt and schema worked surprisingly well as a forcing function
for surfacing **terminology drift** in this paper — Raw2Event has
many real drift cases (per-pair K calibration with 10+ surface
forms, per-pixel EMD with 6 forms, the upstream diagnostic with at
least 5 names, ISP-RGB / post-ISP / ISP-processed). These are exactly
the cases paperterm exists to find, and the FoundForm list naturally
expressed them.

That said, several genuine pain points showed up:

- **The prompt's worked examples bias the model toward simple cases.**
  All three examples are clean concepts with 1-2 abbreviations.
  Real papers have *concept overloading*: in this paper, "Raw2Event"
  is the dataset name, the simulated-event-stream name, and a
  simulator-variant name (V01/V02). The schema has no native way
  to express "this concept's variants belong to two related-but-
  distinct senses"; I had to either lump (with a confidence cut and
  a long `notes` apology) or split into sibling concepts with no
  link between them. A `senses:` sub-list or a `related_to:` link
  field would help a lot.

- **Math vs prose ambiguity is awkward.** The prompt's exception for
  "math used as a name in prose" sounds reasonable, but in practice
  symbols like `$|\Delta p|$`, `$R@1$`, `$\Delta t$-EMD`,
  `cnt$_{\text{med}}$` blur the line between equation labels and
  prose names. I recorded LaTeX-escaped strings as `form` values
  including the `$...$` delimiters, but downstream tooling will need
  a normalisation step to match `$R@1$` against the bare-text
  `R@1` from a table cell. The schema does not say which side of
  the math/prose line the `form` should sit on.

- **Subscript markup variants generate spurious form duplication.**
  `cnt$_{\mathrm{med}}$` and `cnt$_{\text{med}}$` are typeset
  identically and obviously the same metric, but the prompt says
  "preserve original case", which I read as also preserving the
  exact LaTeX source. I therefore emit them as separate forms, even
  though a paperterm reviewer would clearly merge them. A
  `normalize_latex` rule (or an explicit instruction to canonicalise
  `\text` ↔ `\mathrm` in subscripts) would prevent this noise.

- **Skip-rule edge case: comments inside multi-line figure blocks.**
  Section 3's commented-out figure environment is dozens of lines
  of `%`-prefixed material. Each line individually is a comment, but
  it's easy to forget that line N might be a comment because line
  N-3 is. The prompt's "any text from a literal `%` to end of line"
  is per-line and unambiguous, but a runner that pre-strips comments
  before injection would be more robust than relying on the LLM to
  remember this on every line.

- **Tables don't have prose context, so abbreviation-only forms have
  no introduction site.** The forms `slomo`, `DVS-V`, `R@1` only
  appear in tables; the only way to know they are abbreviations of
  prose names is to cross-reference. The schema handles this
  correctly (forms get listed regardless of where they appear), but
  the prompt could call out "prefer to lump table-only short forms
  with the prose long form even when the table doesn't introduce
  the abbreviation".

- **`canonical: TBD` is rarely the right call.** The prompt suggests
  TBD for genuine ambiguity, but in practice every concept I
  encountered had at least one defensible canonical (typically the
  abstract form). I did not emit any `TBD` values; reviewing later,
  none should have been TBD. This may indicate the TBD escape hatch
  is over-marketed in the prompt.

- **The abstract doubles as the canonical-introduction site for
  almost every metric.** §1.20 / §1.39 / §0_abstract.tex
  contains the canonical long forms of all seven upstream metrics.
  This is great for paperterm, but the schema doesn't reward it —
  there is no "first_mention" field, so the linter has to figure
  out which `form` is the introduction by re-reading the locations.
  Adding `first_mention_idx: int` (index into `locations`) would
  make downstream linting trivial.

- **The prompt does not address `\title`, `\author`, or BibTeX-key
  contexts.** I treated `\title{Raw2Event: ...}` as exempt
  (close to a label/identifier rather than prose), but the prompt
  explicitly lists only labels, refs, citations, comments, math,
  verbatim, URLs as exempt. Strict-reading it, `\title{}` content
  IS prose. A future version should make this explicit.

- **Recall-over-precision works but produces long `notes` fields.**
  Several of my low-confidence concepts have notes longer than
  their FoundForm payload. Downstream tooling consuming this YAML
  should expect notes to be a major component of the document size.

Bottom line: schema is fit-for-purpose for the dogfood goal, and
the prompt is paper-agnostic in practice (no Raw2Event-specific
keywords leaked through despite reading the entire paper). The
biggest paperterm-side improvement would be a structured way to
express **concept families** (a Raw2Event dataset/stream/variant
trio is a real linguistic phenomenon, not a measurement error),
followed by clearer math/prose handling and a `first_mention_idx`
helper.
