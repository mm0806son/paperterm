# `example/lint_demo/` — synthetic drift fixture for paperterm

A small hand-written `.tex` (51 lines) showing every category of drift
that `paperterm check` is meant to catch — and every category of
"looks-like-drift but should be silently skipped" content. Pair with
the production glossary `example/raw2event_glossary.yaml` (see
`example/demo.md` for how that file was prepared from a real paper).

## Files

| File | Purpose |
|---|---|
| `section.tex` | hand-written 51-line LaTeX section with intentional drift |
| `lint_output.txt` | captured output of `paperterm check` against this fixture |
| `README.md` | this page — line-by-line expectations |

## Reproduce

From the repo root:

```bash
.venv/bin/paperterm check example/lint_demo \
    --glossary example/raw2event_glossary.yaml \
    --include 'section.tex'
```

Should print 16 violations and exit 1. Captured run:
[`lint_output.txt`](lint_output.txt).

## Expectation table

`✓` = paperterm reported the line we expected;
`(skipped)` = paperterm correctly stayed silent here.

| Line | Original text | Concept | Expected | Actual |
|---|---|---|---|---|
| 4 | `% Top-level comment with DAVIS-346 inside` | davis346 | (skipped: comment) | (skipped) |
| 6 | `DAVIS346 reference sensor` | davis346 | (skipped: canonical) | (skipped) |
| 7 | `DAVIS-346` | davis346 | hyphen variant → `DAVIS346` | ✓ |
| 7 | `Davis346` | davis346 | wrong case → `DAVIS346` | ✓ |
| 7 | `davis346` | davis346 | wrong case → `DAVIS346` | ✓ |
| 11 | `DVS-Voltmeter` | dvs_voltmeter | (skipped: canonical) | (skipped) |
| 11 | `DVS Voltmeter` | dvs_voltmeter | space variant → `DVS-Voltmeter` | ✓ |
| 12 | `DVSVoltmeter` | dvs_voltmeter | run-together → `DVS-Voltmeter` | ✓ |
| 14 | `upstream event-statistics diagnostic` | upstream_diagnostic | (skipped: canonical) | (skipped) |
| 16 | `upstream diagnostic` | upstream_diagnostic | shortened → canonical | ✓ |
| 16 | `upstream event-statistics scorecard` | upstream_diagnostic | synonym → canonical | ✓ |
| 17 | `upstream event-statistics table` | upstream_diagnostic | synonym → canonical | ✓ |
| 20 | `per-pixel EMD` | per_pixel_emd | (skipped: canonical) | (skipped) |
| 21 | `spatial per-pixel EMD` | per_pixel_emd | drift → canonical | ✓ |
| 21 | `per-pixel count EMD` | per_pixel_emd | word-order → canonical | ✓ |
| 22 | `pixel-level EMD` | per_pixel_emd | synonym → canonical | ✓ |
| 23 | `spatial px-EMD` (in prose) | per_pixel_emd | alias even though `px-EMD` is allowed in tables → `px-EMD` | ✓ |
| 25 | `Per-pair K calibration` | per_pair_k_calibration | (skipped: canonical, case-insensitive) | (skipped) |
| 26 | `per-pair calibration` | per_pair_k_calibration | dropped 'K' → canonical | ✓ |
| 27 | `per-camera-pair K calibration` | per_pair_k_calibration | over-specified → canonical | ✓ |
| 29 | `DAVIS-346-shaped tokens` | davis346 | the `DAVIS-346` substring is still drift in prose | ✓ |
| 29 | `$|\Delta p|$` | – | (skipped: math) | (skipped) |
| 30 | `\cite{DAVIS-346:2014, davis346-extended}` | – | (skipped: cite arg) | (skipped) |
| 30 | `\ref{tab:DAVIS-346-summary}` | – | (skipped: ref arg) | (skipped) |
| 33 | `DAVIS-346 in a verbatim block` | – | (skipped: verbatim) | (skipped) |
| 39 | `px-EMD` in table `\caption{}` | per_pixel_emd | (skipped: allowed in captions) | (skipped) |
| 42 | table cell `px-EMD` | per_pixel_emd | (skipped: allowed in `[table,figure,caption]`) | (skipped) |
| 43 | table cell `DVS-V` | dvs_voltmeter | (skipped: allowed in tables/figures/captions) | (skipped) |
| 49 | `spatial px-EMD` in figure `\caption{}` | per_pixel_emd | alias is forbidden in any context → `px-EMD` | ✓ |

## Categories of error this fixture exercises

1. **Capitalisation drift** (case-sensitive concept) —
   `Davis346` / `davis346` / `DAVIS-346` vs `DAVIS346`.
2. **Hyphen / spacing drift** —
   `DVS Voltmeter` / `DVSVoltmeter` vs `DVS-Voltmeter`.
3. **Word-order / verbose drift** —
   `per-pixel count EMD` / `spatial per-pixel EMD` vs `per-pixel EMD`;
   `per-camera-pair K calibration` vs `per-pair K calibration`.
4. **Synonym drift across sections** —
   `upstream event-statistics scorecard` / `… table` /
   `upstream diagnostic` vs `upstream event-statistics diagnostic`.
5. **Allowed-form-in-prose violation** —
   `spatial px-EMD` in prose; `px-EMD` is fine inside tables /
   figures / captions but the longer alias is still flagged.
6. **Substring inside compound** —
   `DAVIS-346-shaped` still flags the inner `DAVIS-346` because
   alias matching uses word-boundary regex, and the alias is the
   whole drift signal even when used as a modifier.
7. **Things paperterm must NOT flag** — comments, math
   (`$...$`), `\cite{}` / `\ref{}` / `\label{}` arguments,
   `\begin{verbatim}` blocks, and forms explicitly allowed in
   their actual context.

## Summary

Counts:
- **16 expected violations**, all reported with correct concept_id
  and canonical suggestion.
- **13 expected non-violations** (counted from the table above:
  one comment, three canonical mentions, one math span, one cite
  arg, one ref arg, one verbatim block, three table-cell or
  caption-allowed forms, and two extra canonical forms). None of
  these appear in `lint_output.txt`.
- **0 false positives**, **0 false negatives**.

This fixture lives next to the production glossary so anyone
reading the repo can re-run it locally in seconds without needing
the upstream Raw2Event paper checked out.
