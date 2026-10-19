---
name: galdre-code-review
description: Interactive, multi-agent review of a PR or commit in a Clojure codebase. Skims the change, agrees review perspectives with the user (security, a prose pass, and DRY and code bloat are always included), runs one reviewer subagent per perspective with its own nREPL, proves or disproves findings with failing tests, checks proven findings against the base commit, classifies findings as Required / Requested / Optional with the user, and builds a tabbed review page for humans plus a copy-as-Markdown export for agents. Use when the user asks for a code review of a PR, branch, or commit and wants the full process, or invokes this skill by name.
---

# Code review

This is an interactive process. Stop at every checkpoint (marked **Checkpoint**) and wait for the user. Never
treat your own proposal as the user's decision.

All files for one review live in a workspace folder at the repository root:
`scratch/review-<pr>-<short-sha>/`. Nothing in this process is committed or pushed. Nothing is posted to GitHub,
Slack, or any other service.

References, read when the step needs them:
- `references/reviewer-brief.md`: the prompt for a perspective reviewer.
- `references/test-writer-brief.md`: the prompt for a test-writer agent.
- `references/baseline-brief.md`: the prompt for the base-commit check.
- `references/report-format.md`: the report contract that the page build parses.
- `references/classification.md`: the labels, and how to ask the user about them.
- `references/repl.md`: how each agent gets an isolated nREPL and app DB, and tears it down.

Assets: `assets/build.py`, `assets/template.html`, `assets/diagrams_lib.py`, `assets/diagrams.example.py`,
`assets/review.example.json`.

## Authorization granted by invoking this skill

Invoking this skill authorizes `git worktree add` and `git worktree remove` for worktrees that this review creates
under `scratch/review-<pr>-<short-sha>/worktrees/`, and `git fetch` of the PR's refs. It authorizes no other
state-changing git command. Test code stays as unstaged changes in the review worktree; nothing is staged or
committed unless the user asks.

## Step 0: pin the code under review

1. Find the PR's head commit and base commit (`gh pr view <n> --json headRefOid,baseRefName,mergeCommit`).
2. Verify every relationship you rely on with git, never by inference: `git merge-base --is-ancestor`,
   `git rev-parse`. PR numbers say nothing about commit order.
3. Show `git diff --stat <base>...<head> | tail -5` and the file count.
4. Create a worktree at the reviewed commit: `scratch/review-<pr>-<short-sha>/worktrees/head`.

**Checkpoint:** state the reviewed SHA, the base SHA, the diff base, and the file count. The reviewed SHA is the
one the final page names and links. Proceed only after the user confirms.

## Step 0b: read Tulip's explanation

Tulip (https://github.com/VirtusLab/tulip) splits a change into categories, marks each one `Read closely` or `Read
through`, and explains each with prose, a diagram, and the diff. Use it to find the parts that are confusing, that
can have problems, or that need extra review. Install it as the README says. If Tulip is not installed, say so and
go to step 1.

1. Run `tulip-local`, the patched build (see the README), on the pinned commits:
   - for a local branch or commit range, and for a PR when the pinned commits matter:
     `tulip-local --local --repo <worktree> --base <base sha> --head <reviewed sha> --title "<title>" --body-file
     <description file> --no-open`;
   - for a PR on GitHub at its current head: `tulip-local <PR URL> --no-open`.
   Use upstream `tulip` only when `tulip-local` is not installed: it fails when the user's Claude settings have
   `verbose: true`. Never use `--serve`: it posts comments to GitHub, and this process posts nothing.
   If Tulip fails, tell the user the error line from its log before you go on. `missing "result"/"session_id"` means
   the build lacks the runner fix in `assets/tulip-local-mode.patch`: reinstall as the README says.
2. Tulip runs the `claude` CLI on the user's account, with Opus, Sonnet, and Haiku: about 6 minutes on a small PR,
   about 27 minutes on a 63-file PR. Run it in the background and say how long it may take.
   It writes the page to a temporary directory. Copy that whole output folder (`index.html` and `assets/`) to
   `scratch/review-<pr>-<short-sha>/tulip/`. In step 6, the `tulip` entry in `review.json` puts it into the review
   page as the left-most tab (`references/report-format.md`).
3. Read its `Read closely` categories and its explanations. They are input to step 1 (which perspectives, and where
   each reviewer starts) and to the prose pass (text that Tulip found hard to explain, and places where its
   summary repeats the PR description without a check against the code).

Tulip reads code; it does not run code. On one PR it missed every finding that needed a run. Never cite Tulip as
evidence for a finding: a reviewer must confirm the finding in its own nREPL. Its diagrams are mermaid; diagrams on
the review page stay reladraw first.

## Step 1: skim and propose perspectives

Read the PR description, Tulip's `Read closely` categories (step 0b), and skim the diff. For a large PR, read the file list and the central files only, and say
which parts you did not read. Propose a list of review perspectives, each with one line on what it examines.
**Always include `security`, `prose pass`, and `DRY and code bloat`** (duplicated logic, code that repeats what an existing helper does, and code larger than the change needs). Scale to the PR: a small PR needs few perspectives.

For each perspective, name the Tulip categories it covers. Give the prose pass the path of the Tulip page.

Candidate perspectives beyond the three required ones, when the PR calls for them:
- **Against a target design**, when the user brings someone else's statement of how the change should work. Save the
  statement verbatim in the workspace (`<topic>-target.md`) and give it to reviewers as input, not as settled fact.
- **Architectural simplicity** ("Simple Made Easy": concepts intertwined that could be separate, concepts defined in
  more than one place, state stored that could be derived). The reviewer writes the PR's model formally, with its
  inputs and case counts.
- **Upgrade, downgrade, and rolling deploy**, when the PR has a migration or changes stored data or a protocol.

**Specifications.** When the PR implements a protocol or standard (OAuth, MCP, an RFC), fetch the specification
yourself before step 2, list the normative rules (MUST, SHOULD) that the change touches, and give them to the
reviewers. Reviewers checked the PR "against the spec" and still missed a server MUST on audience validation that
decided the design question. In step 6 the quoted rules become a reference tab.

**Checkpoint:** the user edits the list. Do not start reviewers until the user approves it. Publish the Tulip page
as a private Artifact at once, and give the user the link with the list. Publish it as one file: convert it first
(`python3 <skill>/assets/tulip_import.py tulip/index.html --label "<text>" > tulip/tulip.html`) and publish
`tulip.html` with no `files`. An artifact with more than one file downloads as a zip, not as an HTML file.

## Step 2: one reviewer per perspective

Spawn one subagent per perspective, in parallel, with `references/reviewer-brief.md`. Put what every reviewer needs
in one file, `reviews/COMMON-CONTEXT.md`: the checked commit facts, the paths, any target design, the leads from Tulip
and from your skim, how to run code, and the report format. Each prompt then holds only the perspective's questions
and its resources. Each reviewer:
- works in the review worktree and runs code in its own nREPL (`references/repl.md`); reading code alone does not
  confirm a finding;
- writes its report to `reviews/<NN>-<perspective>.md` as it goes, and saves probe code and output under
  `reviews/evidence/<NN>/`;
- writes each finding's statement and summary in ASD-STE100, and the details in plain technical prose, with a
  glossary at the top of the report.

Keep each report in full. When a reviewer finishes, tell the user its counts and its most serious findings. When a
reviewer finds something outside its perspective, send it to the reviewer that owns that perspective, if it is still
running.

## Step 3: prove or disprove with tests

List the findings that a test can prove or disprove. Group them by the test file each test belongs in, so that no
two agents edit one file. Give each finding a basis, the source of its "correct behavior":
- **PR**: what the PR itself says it does. Check the claim against the PR's description, its docstrings, and its own
  tests before you write "PR". A PR that does a thing on purpose (a docstring says so, a test pins it) gives a
  Decision, not a bug.
- **target**: an external design input, such as the target design from step 1. The test is still written; the
  report presents it under a design decision (status Decision).

**Checkpoint:** show the grouping, the file ownership, and the basis of each finding.

Spawn one test writer per group with `references/test-writer-brief.md` (write it once to `tests/TEST-WRITER-BRIEF.md`
with the paths filled in; each prompt then names the file, the resources, and the findings). Each test asserts the correct behavior and
must fail on the reviewed code for the reason the finding gives. A finding whose test passes is disproven: keep the
test text and the evidence, and move the finding to the report's "Disproven findings" section.

A finding that no test can prove, but whose correction is clear (for example a smaller form of new code), can get a
proposal instead: an agent writes the correction as a patch in `proposals/`, does not apply it to the worktree, and
verifies it in its own nREPL (the PR's tests still pass, results unchanged). The page shows it in a Proposals tab
(`references/report-format.md`).

## Step 3b (optional): an alternate design

When several findings come from one design choice, and the user wants the alternative worked out, it becomes an
"Alternate design" tab: a proposal for discussion, not a finding.

1. A rough sketch early, while reviewers or test writers still run: a short design note, a small prototype of pure
   functions in its own nREPL, and checks of the prototype against the rule it implements.
2. The full version after the reviews (start it with the test writers if the user asks): a design document with
   diagrams placed in it, a prototype with checks, what the design closes and what it costs, open questions, and a
   path from the PR as it stands. It must answer the specification rules from step 1.
3. After `report.md` is numbered, the design document cites report sections ("closes Section 3.2") only where it bears
   on a finding.

The prototype and its checks live outside the worktree (`proposals/alt-design/`). They are the design document's
evidence files on the page.

## Step 4: check proven findings against the base commit

After the tests are done, run one subagent with `references/baseline-brief.md`. It creates a second worktree at the
base commit, uses one nREPL, and for each proven finding answers: did this behavior exist before the PR, and is it
worse now? Run it once, for proven findings only.

## Step 5: classify

Apply `references/classification.md`. Propose criteria for this PR (the question is always "does this PR make
something worse than it was before?", but what "worse" means depends on the PR). Label each finding Required,
Requested, or Optional.

**Checkpoint:** present the criteria and every label in one executive report, with the evidence for each
borderline case. Ask once, not finding by finding. When unsure whether a finding is Required or Requested, ask.

## Step 6: the report and the page

1. Write `report.md` following `references/report-format.md` exactly: section 1 is scope and method with terms
   and labels; then numbered sections with findings; then "Disproven findings"; then "Changes to the initial
   assessment".
2. Write a pattern summary for each section (`summaries.json`), in ASD-STE100.
3. Propose diagrams where they show a mechanism that the text does not: call paths, architecture, namespace
   relationships. Write them in reladraw; use `diagrams_lib` only when reladraw cannot say the arrangement
   (`references/report-format.md`). Problems are red. **Checkpoint:** list the findings whose fix is clear enough to draw in green;
   draw green only for the ones the user approves.
4. Write the tabs beyond the standard ones, when the review has them. The tab order is Walkthrough (Tulip), any
   `before-report` views, Report, then the other views in the order `views` lists them.
   - Before Report: a reference tab (for example "MCP spec") with `"placement": "before-report"`: one document per
     rule, each quoting the rule with its link and listing the report sections that cite it. Findings link to a rule
     as `[resource parameter](#spec-resource)`.
   - After Report: the "Alternate design" tab (step 3b), an ordinary document view listed after Reviews and Tests. Its
     document carries its own diagrams module, its evidence is the prototype's files, and its summary says it is a
     proposal, not a finding.
5. Write `review.json` from `assets/review.example.json` and run
   `python3 <skill>/assets/build.py scratch/review-<pr>-<short-sha>/review.json`. The build fails on a local path
   in any document, a missing evidence file, or a test that the report names but the test code lacks. Fix the
   input; do not weaken the check. The build does not check evidence files: copy each cited one to
   `page/evidence/<same path>` with local paths replaced (`<workspace>/`, `~/`, `<tmp>/`), and point `evidence_dir`
   there. For a large review, one agent can do this assembly with a script (`page/make_config.py`) that writes the
   staging copies and `review.json`, so a rebuild is two commands.
6. Look at the page once, fix what the look shows, then stop. Headless Chrome (`--headless=new --screenshot=...`)
   writes the screenshot and then does not exit: run it in the background and stop the task.
7. Publish the page as a private Artifact as soon as it builds, before any question to the user. After each change,
   rebuild and publish again to the same Artifact, so the link stays the same and shows the newest version.
   Publish `review.html` alone, with no `files`: the page already contains the patches the build writes beside it,
   and an artifact with more than one file downloads as a zip, not as an HTML file.

**Checkpoint:** give the user the link and tell the user what the page contains, including any security findings.
Ask the open questions (labels, green diagrams) with the link. Findings outside the PR's scope are held for a
separate PR and stay out of the page unless the user asks.

## Rules that apply throughout

- Every subagent prompt states the reviewed SHA as a checked fact. If you find that a premise you gave subagents
  was wrong, say so to the user at once and send every affected agent a correction.
- Save every subagent report to a file before you summarize it. A summary never replaces the report.
- Files go in the workspace, never in `/tmp`.
- Do not expose local paths in anything the page shows. Evidence that a document cites is included in the page;
  a cited file that only copies repository content, or third-party source extracted from a jar, is replaced by the
  command that shows it.
- No document points at the reviewer's machine: no folder names (`evidence/03/`, `prototype/`), no worktree names,
  no workspace files that are not on the page. A document cites an evidence file by its bare name (`12-old-site-url.out`),
  which the page links to the file; it cites repository code by repository-relative path and line; and it replaces a
  workspace file such as a saved diff with the git command that produces it.
- Plain words. No metaphors, no undefined shorthand labels, no bare internal ids in messages to the user.
