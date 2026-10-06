---
name: metabase-self-review
description: Multi-agent self-review of Timothy's own Metabase branch or PR, before he shares it. The same review as metabase-code-review (perspective reviewers with their own nREPL, findings proven or disproven with tests, a base-commit check, a tabbed review page), trimmed for an audience of one - no checkpoints before the page, labels assigned without asking, Tulip in the background, no proposal patches by default. Use when the user asks for a self-review of his own work, or invokes this skill by name. For a review that someone else will read, use metabase-code-review.
---

# Metabase self-review

The same review as `metabase-code-review`, for Timothy's own work. He is the only reader. He will look through the
page and argue with it there, so do not stop to ask him during the process. Build the whole page, then give him the
link.

The other skill holds the shared parts. Read them from `~/.claude/skills/metabase-code-review/` when a step needs
them (`CR` below stands for that folder):
- `CR/references/reviewer-brief.md`, `CR/references/test-writer-brief.md`, `CR/references/baseline-brief.md`;
- `CR/references/report-format.md` (the page build parses it) and `CR/references/repl.md`;
- `CR/assets/build.py`, `CR/assets/template.html`, `CR/assets/diagrams_lib.py`, `CR/assets/diagrams.example.py`,
  `CR/assets/review.example.json`.

Everything goes in `scratch/review-<pr>-<short-sha>/` at the repository root, as in the other skill. Nothing is
committed, pushed, or posted to GitHub, Slack or any other service. This skill authorizes `git worktree add` and
`git worktree remove` for worktrees under `scratch/review-<pr>-<short-sha>/worktrees/`, and `git fetch` of the PR's
refs; no other state-changing git command.

## What differs from metabase-code-review

| Step | Here |
|---|---|
| Checkpoints | None before the page. State the pinned commits and the perspectives in one status line each and go on. Stop only when a fact blocks the review (for example, the base commit is ambiguous). |
| Tulip | Start it in the background at step 0, and do not wait for it. Put it on the page when it has finished; if it has not finished when the page builds, build without it and add it later with one rebuild. |
| Perspectives | Always security, the prose pass, and DRY and code bloat; add only the one or two that this change needs. |
| Proposals | No proposal patches by default. A finding with a clear fix gets a `**Possible correction:**` paragraph. Write a verified patch only when Timothy asks, or when the fix is not clear from a paragraph. |
| Base-commit check | Only for the findings whose label depends on "did this change make it worse". |
| Labels | Assign them yourself, with the criteria in `CR/references/classification.md`. A borderline finding goes in the higher label and gets the note `Borderline: <the other label> because <reason>.` No executive report and no questions. |
| Diagrams | Only where a diagram shows a mechanism that the text does not. Problems in red. No green fix diagrams and no checkpoint for them. |
| Report | The format of `CR/references/report-format.md`. Keep "Changes to the initial assessment" to what the review actually corrected. |

## Steps

### 0. Pin, and start Tulip

1. Find the head commit and the base commit (`gh pr view <n> --json headRefOid,baseRefName,mergeCommit`, or the
   branch the user names). Check each relationship you rely on with git (`git merge-base --is-ancestor`,
   `git rev-parse`). Use `git diff origin/<base>...<head>` with three dots, and print the file count first.
2. Create the review worktree at the reviewed commit: `scratch/review-<pr>-<short-sha>/worktrees/head`.
3. Start Tulip in the background, with its output in the workspace (`tulip-local`, as `CR/SKILL.md` step 0b says;
   never `--serve`). Record its process id. Go on at once. If it fails, tell the user the error line from its log.
4. One status line: reviewed SHA, base SHA, file count.

### 1. Perspectives

Read the PR description and skim the diff. Choose the perspectives: security, prose pass, DRY and code bloat, and
at most two more that this change needs. One status line with the list.

### 2. Reviewers

One subagent per perspective, in parallel, with `CR/references/reviewer-brief.md`, an nREPL and app DB each as
`CR/references/repl.md` assigns. Add to each brief:
- Run the tests that answer your question (a probe, one test, one namespace), in your own nREPL. Do not use
  `./bin/test-agent` unless a fresh JVM is the point of the test.
- A test result is pass, or the failures with their output. Do not report or confirm counts.
- Save your report to the workspace as you go.

Save every report in full. Tell Timothy nothing yet, except a failure that stops the review.

### 3. Prove or disprove

Group the testable findings by test file, so that no two agents edit one file, and run one test writer per group
with `CR/references/test-writer-brief.md` (no checkpoint for the grouping). A finding whose test passes is
disproven. A finding that no test can prove keeps the status `Code reading`.

### 4. Base-commit check

One agent with `CR/references/baseline-brief.md`, only for the proven findings whose label depends on it.

### 5. Labels

Assign every label yourself (see the table above). Record the criteria you used in report section 1.3.

### 6. The page

Write `report.md`, `summaries.json`, `diagrams.py` (if any) and `review.json`, and run
`python3 ~/.claude/skills/metabase-code-review/assets/build.py scratch/review-<pr>-<short-sha>/review.json`. Fix the
input when the build fails; do not weaken a check. Look at the page once, fix what the look shows, then publish it as
a private Artifact. When Tulip finishes later, add it to `review.json`, rebuild and publish to the same Artifact.

Give Timothy the link with: the counts per label, each Required finding in one line, and any security finding.
Then stop. He will argue with the labels on the page; when he does, change the report, rebuild, and publish again.

## Rules that apply throughout

- State the reviewed SHA as a checked fact in every subagent prompt. If a premise you gave subagents turns out to
  be wrong, send every affected agent a correction at once.
- Files go in the workspace, never in `/tmp`. No local paths in anything the page shows.
- Plain words. No metaphors, no undefined shorthand labels, no bare internal ids in messages to Timothy.
- Stop only processes that you or your agents started, by process id or port, never by name.
