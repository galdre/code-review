# Base-commit check brief

Run once, after the tests are done, for the proven findings only. One agent, one nREPL.

---

**Question.** For each proven finding below, did the same behavior exist at the base commit `[base sha]`, before
this PR? If it did, is it worse now (more frequent, more severe, or reachable in more ways)?

**Setup.** Create a worktree at the base commit: `git worktree add [workspace]/worktrees/base [base sha]` (the
skill authorizes this). Start one nREPL there as `references/repl.md` describes: port `[port]`, database `[db]`.

**Method.** For each finding, run the equivalent scenario at the base commit. The PR's own tests usually cannot run
there, because the PR added the code they call; write the closest scenario the base code supports, and for
behavior the PR introduced, say "not present before the PR". Also check whether other types or code paths have the
same defect at the reviewed commit when the coordinator asks (for example "does the same bug affect cards, not only
actions?").

**Evidence.** Save each probe and its output under `[workspace]/checks/evidence/[id]/` and cite the file names.

**Classes, one per finding:**
- **NEW**: the PR introduced the behavior.
- **WORSE**: the behavior existed before, and the PR makes it more frequent or more severe. Say how.
- **SAME**: the behavior existed before and the PR does not change it.
- **UNDETERMINED**: say what is missing.

**Report.** Write `[workspace]/checks/[id].md`: a glossary of terms, then one section per finding with the class,
the scenario run at each commit, the actual output, and the evidence files. Remove the base worktree
(`git worktree remove`) and tear down the REPL when you finish.
