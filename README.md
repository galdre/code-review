# metabase-code-review

A Claude Code skill for interactive, multi-agent review of a Metabase PR or commit.

The process: pin the reviewed commit, agree review perspectives with the user (security, a prose pass, and DRY and code
bloat are always included), run one reviewer per perspective with its own nREPL, prove or disprove findings with failing tests,
check proven findings against the base commit, classify findings as Required / Requested / Optional with the
user, and build a tabbed review page with a copy-as-Markdown export.

## Install

```bash
git clone git@github.com:galdre/metabase-code-review.git ~/.claude/skills/metabase-code-review
```

Invoke it by asking Claude Code for a code review of a PR, or with `/metabase-code-review`.

## Contents

- `SKILL.md`: the process, its checkpoints, and what invoking it authorizes.
- `references/`: briefs for the reviewer, test-writer, and base-commit agents; the report format; classification;
  nREPL isolation.
- `assets/`: the page template, the build script, the diagram library, and an example config.

Build a review page: `python3 assets/build.py <workspace>/review.json`.
