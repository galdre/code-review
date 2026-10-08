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
  - `**Severity:** High. **Status:** Test fails. **Base:** NEW.` Status is one of: Test fails, Code reading,
    Disproven, Decision. Base is the base-commit class (NEW, WORSE, SAME, BETTER), for proven findings that the
    base check covered; define the classes in section 1.
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

A module in the workspace that defines `DIAGRAMS = {"<section>": [(diagram, "caption"), ...]}`. Start from
`assets/diagrams.example.py`. Draw one mechanism per diagram: endpoints, functions, and tables, with labeled
arrows. A caption is one or two ASD-STE100 sentences.

- **Use reladraw first.** A diagram is a string of reladraw source (https://github.com/reladraw/reladraw). You say
  where each box goes (`right of api`, `below check`), and reladraw calculates the distances. The build renders
  each string twice, in the light and the dark theme, and the page shows the one that matches its theme. The
  build needs `reladraw` on the PATH or `npx`; it pins reladraw to one version, because its syntax still changes.
  Problems are red: `style bad  border: #d1242f  text: (color: #d1242f)`, and `line: (color: #d1242f)` on an
  edge. Fixes are green (`#1a7f37`) only after the user approves them.
- **Use `diagrams_lib` only when reladraw cannot say the arrangement.** Then the entry is a function that returns
  a `D`, with explicit coordinates. Problems use `bad=True` (red). Fixes use `good=True` (green) only after the
  user approves them.

reladraw draws boxes and lines only. It does not draw sequence diagrams or charts of data, and it does not keep a
line away from a box that the line does not connect: use `between` or `below <node>` to route such a line.

## Other documents

Reviewer reports (`reviews/NN-*.md`) and check reports (`checks/*.md`) are shown verbatim. They follow the
briefs: a glossary first, then findings. Each document gets a one-paragraph ASD-STE100 summary in the config.

A document in any view can carry its own diagrams, for example a tab with an alternate design: give its item
`"diagrams": "<module>.py"`, a module in the `diagrams.py` format whose keys are names, not section numbers. The
Markdown places each key with a line that holds only `[[diagram:<key>]]`. The build fails unless every key has
exactly one such line and every line names a key. The page shows the figures there; the Markdown export shows the
caption and the reladraw source.

A view with `"placement": "before-report"` gets its tab before the Report tab (after Tulip's), for reference material
that the report cites, such as a specification. Link to one of its documents as `[text](#<view key>-<item id>)`; the
view key must be lowercase letters only.

## Tulip's walkthrough (`tulip` in the config)

Optional. `"tulip": {"html": "tulip/index.html", "tab": "Walkthrough", "label": "<text>"}` (or only the path). The
path is Tulip's `index.html`, with Tulip's `assets/` folder beside it: copy Tulip's whole output folder into the
workspace. The build converts it with `assets/tulip_import.py` into one document (styles, fonts, scripts inlined;
mermaid from cdn.jsdelivr.net at the version Tulip shipped) and shows it as the left-most tab, in an iframe, with
Tulip's own sidebar and themes. `label` replaces the pull-request link that Tulip's local mode writes. The build
checks the Tulip page for local paths, as it checks the other documents. With no `tulip` entry, the page has no
such tab.

## The config (`review.json`)

See `assets/review.example.json`. Paths are relative to the config file. `howto` holds the "How to use this
report" paragraphs, including this PR's label definitions; `copy_intro` opens the Markdown export.

A view with `"kind": "proposal"` shows source changes the review proposes but did not apply: each entry of
`proposals` names a patch file in the workspace, a summary, and the report findings it corrects (`"findings":
["3.2"]`). The build fails if a patch does not apply to the review worktree, and writes each patch next to the page
under the name its apply command shows. Use it for a verified correction that a test cannot prove (for example a
smaller form of new code); state the verification in the proposal's write-up.
