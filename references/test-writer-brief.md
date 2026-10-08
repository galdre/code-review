# Test-writer brief

Give this to one agent per group of test files. The coordinator groups findings by the test file each test belongs
in; each agent owns a set of files that no other agent edits.

---

**Goal.** For each assigned finding, write one test that asserts the correct behavior and fails on the reviewed
code for the reason the finding gives. Do not change production code.

**The code.** Work in the review worktree at `[path]`, checked out at the reviewed commit `[sha]`. You may edit only
these files: `[list]`. Other agents are editing other test files now. Leave your changes unstaged. No git commands
that change state.

**Findings.** [For each: the plain-language statement, the source report and finding number, the basis, and what
a failing test should show.] Read the cited report sections and the code they cite before you write a test.

**Basis.** Each finding is marked:
- **PR**: the correct behavior follows from what the PR states it does. If you find that the PR does the opposite on
  purpose (a docstring says so, or one of its own tests pins it), report it: the finding becomes a design decision.
- **target**: the correct behavior follows from an external design input ([path to the target]). Write the test
  anyway, with a `testing` string that states the target behavior plainly, and record "basis: target".

**Outcomes, all valid:**
- **FAILS-AS-EXPECTED**: the failure (assertion or exception) is the problem the finding describes.
- **DISPROVEN**: the test passes, so the finding is wrong. Keep the test text in
  `[workspace]/tests/disproven/<finding>.clj` (not in the repository file) with what you ran and observed. The
  final report puts it in its "Disproven findings" section.
- **FAILS-DIFFERENTLY**: investigate until the failure is the finding's, or say what the finding got wrong.
- **SKIPPED**: not testable deterministically, or the correct behavior is a product decision. Say which.

A failure caused by test setup proves nothing; read the failure output every time. For a race, force the order of
operations (redefinitions, promises) and run the test at least three times; all runs must agree. Where useful, show
the test is about the defect with a control: a temporary REPL-only fix that makes the test pass, removed afterwards.

**Standards.** Follow the conventions of the file you edit: reuse its helpers, fixtures, and naming. `testing`
strings state the behavior, tersely. No comments that narrate the review; a comment earns its place with a local
reason the code does not show. Helper docstrings are caller contracts. Use `clj-paren-repair` for delimiter
errors and the `:kondo` alias to lint each file you change. `clj-paren-repair` also reformats code you did not
touch: check `git diff` afterwards, and restore any hunk that is not yours. Name each test `<behavior>-test`, unique
in the file: the report links test names to code.

**REPL.** Use your own nREPL and app DB as `references/repl.md` describes: port `[port]`, database `[db]`, log
`[log]`. Tear them down when you finish, including on failure.

**Report.** Append to `[workspace]/tests/[agent]-report.md`, one section per finding: the finding, the basis, the
outcome, the test name and file:line, the exact failure output from a real run, the number of runs. Return a short summary.
