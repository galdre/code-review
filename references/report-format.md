# Report format

`assets/build.py` parses these conventions. Follow them exactly; the page's folding, labels, links, and copy
export depend on them.

## The final report (`report.md`)

- One `#` title.
- **Section 1** is `## 1. Scope and method`. It stays open on the page. It contains the method, the status values,
  `### 1.1 Terms` (a glossary table), `### 1.2 Summary` (counts), and `### 1.3 Labels` (the label definitions and
  a table with a header cell `Label` whose rows are `[Required]`, `[Requested]`, `[Optional]`, `No label`, and
  whose second column lists section numbers).
- **Sections 2 and later** are `## N. Topic`. A section whose next heading is `### N.M ...` is a group: the page
  shows its pattern summary and folds its findings. A section with no subsections is standalone: a finding if its
  heading carries a label, otherwise information.
- **A finding** is `### N.M [Label] Title`, where the label is `[Required]`, `[Requested]`, or `[Optional]`, or no
  label for findings that are not requests (disproven, or explanation only). The title is one ASD-STE100 sentence.
- **Finding bullets**, in this order, each starting with a bold key:
  - `**Severity:** High. **Status:** Test fails.` Status is one of: Test fails, Code reading, Disproven, Decision.
  - `**Problem:**` the statement and summary, in ASD-STE100.
  - optional `**Result:**`, `**Cause:**`, `**Scenario:**`, `**Note:**`, `**Possible correction:**`.
  - `**Test:**` or `**Tests:**` with each test as `` `namespace/test-name` `` (the build links each to its code
    and fails if the test code lacks it; list pre-existing tests in `existing_tests` in the config).
  - `**File:**` the test file the first time a file appears.
  - `**Source:**` or `**Sources:**` with `report NN` references to the reviewer reports.
- **Disproven findings** form their own section near the end, `## N. Disproven findings`, with unlabeled findings
  whose status is Disproven and whose bullets say which test disproved them.
- **The last section** is `## N. Changes to the initial assessment`: statements from the first skim or from the
  coordinator that the review showed to be wrong.
- In-report references: write `Section 2.3` (linked automatically) and `report 04` (linked to that reviewer
  report). Never cite a local path.

## Section summaries (`summaries.json`)

`{"<section number>": "<markdown>"}`. ASD-STE100. Name the patterns that the section's findings share, and link
each finding as `[2.1](#s2.1)`. Every group section should have one.

## Diagrams (`diagrams.py`)

A module in the workspace that imports `diagrams_lib` and defines
`DIAGRAMS = {"<section>": [(function, "caption"), ...]}`. Each function returns a `D`. Draw one mechanism per
diagram: endpoints, functions, and tables, with labeled arrows. Problems use `bad=True` (red). Fixes use
`good=True` (green) only after the user approves them. A caption is one or two ASD-STE100 sentences.

## Other documents

Reviewer reports (`reviews/NN-*.md`) and check reports (`checks/*.md`) are shown verbatim. They follow the
briefs: a glossary first, then findings. Each document gets a one-paragraph ASD-STE100 summary in the config.

## The config (`review.json`)

See `assets/review.example.json`. Paths are relative to the config file. `howto` holds the "How to use this
report" paragraphs, including this PR's label definitions; `copy_intro` opens the Markdown export.
