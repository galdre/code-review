# metabase-code-review

A Claude Code skill for interactive, multi-agent review of a PR or commit.

This is called `metabase-code-review` only because it instructs agents to use a Metabase-specific artifact-sharing tool. Nothing else in this repository is in any way Metabase-specific; if it is, that's a bug. :)

The process: pin the reviewed commit, read Tulip's explanation of the change, agree review perspectives with the user (security, a prose pass, and DRY and code
bloat are always included), run one reviewer per perspective with its own nREPL, prove or disprove findings with failing tests,
check proven findings against the base commit, classify findings as Required / Requested / Optional with the
user, and build a tabbed review page with a copy-as-Markdown export.

## Install

```bash
git clone git@github.com:galdre/metabase-code-review.git ~/.claude/skills/metabase-code-review
```

Invoke it by asking Claude Code for a code review of a PR, or with `/metabase-code-review`.

## The self-review skill (`self-review/`)

The same repository holds a second skill, `metabase-self-review`, for a review of your own branch before you share
it. It runs the same reviewers, tests and page build, trimmed for an audience of one: no checkpoints before the
page, labels assigned without asking (a borderline finding takes the higher label, with a note), Tulip in the
background, and no proposal patches by default. It reads the briefs, the report format and the page build from
`~/.claude/skills/metabase-code-review/`, so install that skill first. Install the second skill with a link:

```bash
ln -s ~/.claude/skills/metabase-code-review/self-review ~/.claude/skills/metabase-self-review
```

Invoke it by asking for a self-review of your own work, or with `/metabase-self-review`.

### Tulip (step 0b, optional)

Step 0b runs [Tulip](https://github.com/VirtusLab/tulip), which explains a change before the review starts. It
needs Node.js 24 or later and a logged-in `claude` CLI.

The skill runs a patched build, `tulip-local`. The file `assets/tulip-local-mode.patch` holds two commits on top
of upstream:

1. A local mode: the option `--local`, with `--repo`, `--base`, `--head`, `--title` and `--body-file`. It builds the
   PR record from `git diff` and a local worktree, so it contacts no GitHub service, and it refuses `--serve`, which
   posts comments to GitHub.
2. A runner fix. With `verbose: true` in the Claude settings, `claude --output-format json` prints its event stream
   as a JSON array, and upstream Tulip fails with `missing "result"/"session_id"`. The fix reads the array's
   `result` event.

Neither commit is in upstream Tulip. Install the build like this:

```bash
git clone https://github.com/VirtusLab/tulip.git ~/.local/share/tulip-local
cd ~/.local/share/tulip-local
git checkout -b local-mode 9c90092f8d8af4b9995acbe81105916d972fee7f   # the upstream commit the patch was made on
git am ~/.claude/skills/metabase-code-review/assets/tulip-local-mode.patch
npx pnpm install && npx pnpm build && npx pnpm test
printf '#!/bin/sh\nexec node %s/dist/cli/index.js "$@"\n' ~/.local/share/tulip-local > ~/bin/tulip-local
chmod +x ~/bin/tulip-local
```

To update an existing install, move its directory aside and run the same steps; the launcher keeps its path.
`tulip-local` also takes a PR URL, as upstream does. Run it on a commit range:
`tulip-local --local --repo <repo> --base <base sha> --head <head sha> --title "<title>" --body-file <description.md> --no-open`.
If `git am` fails on a newer upstream commit, apply it on the commit above, or rebase the patch by hand.

If Tulip is not installed, the review skips step 0b.

## Contents

- `SKILL.md`: the process, its checkpoints, and what invoking it authorizes.
- `references/`: briefs for the reviewer, test-writer, and base-commit agents; the report format; classification;
  nREPL isolation.
- `assets/`: the page template, the build script, the Tulip converter (`tulip_import.py`), the diagram library, an example diagrams module (reladraw first,
  `diagrams_lib` as the fallback), and an example config.

Build a review page: `python3 assets/build.py <workspace>/review.json`.
