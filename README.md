# metabase-code-review

A Claude Code skill for interactive, multi-agent review of a Metabase PR or commit.

The process: pin the reviewed commit, read Tulip's explanation of the change, agree review perspectives with the user (security, a prose pass, and DRY and code
bloat are always included), run one reviewer per perspective with its own nREPL, prove or disprove findings with failing tests,
check proven findings against the base commit, classify findings as Required / Requested / Optional with the
user, and build a tabbed review page with a copy-as-Markdown export.

## Install

```bash
git clone git@github.com:galdre/metabase-code-review.git ~/.claude/skills/metabase-code-review
```

Invoke it by asking Claude Code for a code review of a PR, or with `/metabase-code-review`.

### Tulip (step 0b, optional)

Step 0b runs [Tulip](https://github.com/VirtusLab/tulip), which explains a change before the review starts. It
needs Node.js 24 or later and a logged-in `claude` CLI.

- For PRs on GitHub: `npm install -g @virtuslab/tulip`.
- For a local branch or commit range: Tulip upstream takes only a GitHub PR URL. A local patch adds `--local`
  (options `--repo`, `--base`, `--head`, `--title`, `--body-file`; it refuses `--serve`). The patch is commit
  `72dbda5` on branch `local-mode` in `~/.local/share/tulip-local` on thalos. It is not in upstream Tulip and is not
  pushed anywhere. To use it on another machine, copy that clone (for example with `git bundle`), then run
  `pnpm install && pnpm build` in it, and make a command:
  `printf '#!/bin/sh\nexec node %s/dist/cli/index.js "$@"\n' ~/.local/share/tulip-local > ~/bin/tulip-local && chmod +x ~/bin/tulip-local`.

If Tulip is not installed, the review skips step 0b.

## Contents

- `SKILL.md`: the process, its checkpoints, and what invoking it authorizes.
- `references/`: briefs for the reviewer, test-writer, and base-commit agents; the report format; classification;
  nREPL isolation.
- `assets/`: the page template, the build script, the diagram library, an example diagrams module (reladraw first,
  `diagrams_lib` as the fallback), and an example config.

Build a review page: `python3 assets/build.py <workspace>/review.json`.
