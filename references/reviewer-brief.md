# Reviewer brief

Fill in the bracketed parts and give this to one reviewer subagent per perspective.

---

You are reviewing [PR #<n> / commit] from one perspective: **[perspective]**. [One paragraph on what this
perspective examines in this PR, and the specific questions the coordinator wants answered.]

**Context.** Read `[workspace]/reviews/COMMON-CONTEXT.md` in full first: the checked facts, any target design,
the leads, the specification rules, and how to run code.

**The code.** The reviewed commit is `[sha]`; this is checked, not assumed. The base commit is `[base sha]`. The
review worktree at `[path]` is checked out at the reviewed commit. Read the PR description at `[path]` and the
diff (`git -C [worktree] diff [base]...[sha]`) before you start. Do not run state-changing git commands.

**Run code.** Use your own nREPL and app DB, as `references/repl.md` describes, with port `[port]`, database
`[db]`, log `[log]`. Reading code is how you find a lead; running code is how you confirm it. Label each finding
CONFIRMED (you ran it, or you traced it end to end and say which) or PLAUSIBLE (it needs a run or a fact you could
not check; say which). Tear down your REPL and database when you finish, including on failure.

**Evidence.** Save every probe you run and its raw output under `[workspace]/reviews/evidence/[NN]/`, and cite each
file by its bare name in backticks (`probe_flow.clj`, not `evidence/01/probe_flow.clj`): the page links a bare name
to the file. The report goes to people who cannot see this machine, so it names no folder, worktree, or workspace
file. To refer to repository code, give the repository-relative path and line at the reviewed commit; to refer to a
diff, give the git command that produces it.

**Report.** Write to `[workspace]/reviews/[NN]-[perspective].md`. Create it early and append as you go. Structure:

1. A title, then a one-paragraph scope: what you examined and how.
2. **Terms**: a short glossary of every term a reader needs (for example "ledger: the `remote_sync_object` table").
3. Findings, most severe first. For each:
   - a heading `### <n>. <Severity> (<CONFIRMED|PLAUSIBLE>): <statement>`;
   - **Statement** and **Summary** in ASD-STE100: short sentences, one idea each, active voice, approved words,
     technical names allowed;
   - details in plain technical prose: the code path with file:line citations, a concrete failure scenario, the
     evidence files, and whether the problem existed before this PR;
   - a fix direction when one is clear.
4. **Leads checked and ruled out**, each with the reason.

Prose rules: plain words, no metaphors, no undefined shorthand, no editorializing. A reader who starts at the top
must understand each finding without other documents. An empty findings section is a valid outcome; do not pad.

Return a short summary: counts by severity and one line per finding.
