#!/usr/bin/env python3
"""Build the code-review page from a review workspace.

Usage: build.py <workspace>/review.json

The config names every input; paths in it are relative to the config file. See references/report-format.md for the
report conventions and assets/review.example.json for the config shape. The build fails, rather than guessing,
when an input is missing, a cited file is absent, or a document still refers to the reviewer's machine.
"""
import importlib.util
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ASSETS = Path(__file__).resolve().parent
sys.path.insert(0, str(ASSETS))

DEF_RE = re.compile(r"^\((deftest|defn-?|defmacro|def)\s+(?:\^:?[\w\-]+\s+)?([\w\-!?*<>]+)", re.M)
IT_RE = re.compile(r'^\s*(?:it|test)\("([^"]+)"', re.M)
REQUIRE_RE = re.compile(r"^\s*\[[\w.\-]+(\s+:as\s+[\w.\-]+)?(\s+:refer\s+.*)?\]\)?$")
LANG = {".clj": "clojure", ".cljc": "clojure", ".cljs": "clojure", ".ts": "typescript", ".tsx": "typescript",
        ".js": "javascript", ".jsx": "javascript", ".sql": "sql", ".json": "json", ".yaml": "yaml", ".yml": "yaml",
        ".patch": "diff", ".diff": "diff"}
DEFAULT_FORBIDDEN = ["/Users/", "/home/", "scratch/"]
# reladraw's syntax is not stable yet, so the build pins one version. Change it here, and check the example diagram.
RELADRAW_VERSION = "0.15.1"
SVG_ID_RE = re.compile(r'(\bid="|url\(#|href="#)([^")]+)')


def fail(msg):
    raise SystemExit(f"build: {msg}")


def lang_of(path):
    return LANG.get(Path(path).suffix, "plaintext")


def git(repo, *args):
    return subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True).stdout


def file_ns(repo, path):
    # a proposal patch can create a file that the worktree does not have yet
    if not path.endswith((".clj", ".cljc", ".cljs")) or not (Path(repo) / path).exists():
        return None
    head = (Path(repo) / path).read_text().split("\n", 4)
    m = re.search(r"\(ns\s+(?:\^[^\s]+\s+)?([\w.\-]+)", "\n".join(head))
    return m.group(1) if m else None


def test_names(code):
    return ([m.group(2) for m in DEF_RE.finditer(code) if m.group(1) == "deftest"] + IT_RE.findall(code))


def all_names(code):
    return [m.group(2) for m in DEF_RE.finditer(code)] + IT_RE.findall(code)


def blocks_for(diff_text):
    """The added code of one file's diff: pure additions as plain code, hunks that change lines as diffs."""
    blocks = []
    for h in re.finditer(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@.*?\n(.*?)(?=^@@ |\Z)", diff_text, re.M | re.S):
        start, body = int(h.group(1)), h.group(2).rstrip("\n").split("\n")
        if any(l.startswith("-") for l in body):
            blocks.append({"kind": "diff", "line": start, "code": "\n".join(body), "names": []})
            continue
        line, run, run_start = start, [], None
        for l in body + [" "]:
            if l.startswith("+"):
                if run_start is None:
                    run_start = line
                run.append(l[1:])
            else:
                if run:
                    code = "\n".join(run).strip("\n")
                    kind = "requires" if all(REQUIRE_RE.match(x) for x in run if x.strip()) else "add"
                    blocks.append({"kind": kind, "line": run_start, "code": code, "names": all_names(code)})
                run, run_start = [], None
            line += 1
    return blocks


def check_text(name, text, forbidden):
    for f in forbidden:
        if f in text:
            fail(f"{name} contains {f!r}; replace it with a commit reference, a link, or an included evidence file")


def load_doc_view(base, view, forbidden):
    items = []
    for it in view["items"]:
        text = (base / it["file"]).read_text()
        check_text(it["file"], text, forbidden)
        doc = {"id": it["id"], "nav": it["nav"], "summary": it["summary"], "md": text, "evidence": [], "excluded": []}
        if "short" in it:
            doc["short"] = it["short"]
        if it.get("diagrams"):
            doc["diagrams"] = load_doc_diagrams(base / it["diagrams"], f"{view['key']}-{it['id']}", it["id"], text)
        ev_dir = base / it.get("evidence_dir", "")
        for f in it.get("evidence", []):
            p = ev_dir / f
            if not p.exists():
                fail(f"{it['id']}: evidence file {p} is missing")
            doc["evidence"].append({"name": f, "lang": lang_of(f), "code": p.read_text().rstrip()})
        for name, cmd in it.get("excluded", {}).items():
            if f"`{name}`" not in text:
                fail(f"{it['id']}: excluded file {name} is never cited")
            doc["excluded"].append({"name": name, "cmd": cmd})
        items.append(doc)
    out = {"key": view["key"], "tab": view["tab"], "title": view["title"], "intro": view["intro"], "items": items}
    if view.get("placement"):
        out["placement"] = view["placement"]
    return out


def load_code_view(base, view, repo, against):
    items, names, patch_parts = [], [], []
    for f in view["files"]:
        path = f["path"]
        diff = git(repo, "diff", against, "--", path)
        if not diff.strip():
            fail(f"no changes in {path} against {against}")
        patch_parts.append(diff)
        is_new = "\nnew file mode" in diff[:400]
        blocks = blocks_for(diff)
        items.append({"id": f["id"], "nav": f["nav"], "path": path, "ns": file_ns(repo, path), "lang": lang_of(path),
                      "isNew": is_new, "blocks": blocks})
        for b in blocks:
            for n in test_names(b["code"]):
                names.append({"name": n, "doc": f["id"]})
    # The whole patch belongs to the view, not to a page of it: a button in the view's header copies it.
    return {"key": view["key"], "tab": view["tab"], "title": view["title"], "intro": view["intro"], "kind": "code",
            "items": items, "patch": "".join(patch_parts), "applyCmd": "git apply review-tests.patch"}, names


def load_proposal_view(base, view, repo, forbidden):
    """A view of source changes the review proposes but did not apply. Each proposal is a patch file, which must apply
    to the review worktree; the page shows each changed file as code and the whole patch with an apply command."""
    items = []
    for p in view["proposals"]:
        patch_path = base / p["patch"]
        if not patch_path.exists():
            fail(f"proposal {p['id']}: patch {patch_path} is missing")
        patch = patch_path.read_text()
        check_text(p["patch"], patch, forbidden)
        r = subprocess.run(["git", "-C", str(repo), "apply", "--check", str(patch_path)], capture_output=True, text=True)
        if r.returncode != 0:
            fail(f"proposal {p['id']}: patch does not apply to the review worktree: {r.stderr.strip()}")
        out_name = p.get("patch_out", Path(p["patch"]).name)
        for m in re.finditer(r"^diff --git a/(\S+) b/\S+\n.*?(?=^diff --git |\Z)", patch, re.M | re.S):
            path = m.group(1)
            items.append({"id": f"{p['id']}-{len(items) + 1}", "short": "file", "nav": f"{p['nav']}: {Path(path).name}", "path": path,
                          "ns": file_ns(repo, path), "lang": lang_of(path), "isNew": False,
                          "blocks": blocks_for(m.group(0)), "findings": p.get("findings", [])})
        items.append({"id": p["id"], "short": "patch", "nav": f"{p['nav']}: the patch", "patch": patch,
                      "tag": "PROPOSED CHANGE AS ONE PATCH", "applyCmd": f"git apply {out_name}",
                      "summary": p["summary"], "findings": p.get("findings", []), "out": out_name})
    return {"key": view["key"], "tab": view["tab"], "title": view["title"], "intro": view["intro"], "kind": "proposal",
            "items": items}


def reladraw_cmd():
    if shutil.which("reladraw"):
        return ["reladraw"]
    if shutil.which("npx"):
        return ["npx", "--yes", f"reladraw@{RELADRAW_VERSION}"]
    fail("a diagram is in reladraw, but neither reladraw nor npx is installed (npm install -g reladraw)")


def render_reladraw(source, key):
    """One reladraw source as two inline SVGs, light and dark; the page shows the one that matches its theme.

    Each SVG's ids get a unique prefix, because the page holds many SVGs and an arrow marker must not resolve to
    another diagram's marker."""
    cmd = reladraw_cmd()
    out = []
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / f"{key}.reladraw"
        src.write_text(source)
        for theme in ("light", "dark"):
            p = subprocess.run([*cmd, str(src), "-o", "-", "--theme", theme], capture_output=True, text=True)
            if p.returncode != 0:
                fail(f"diagram {key}: reladraw failed: {(p.stderr or p.stdout).strip().replace(tmp + '/', '')}")
            svg = SVG_ID_RE.sub(lambda m: f"{m.group(1)}{key}-{theme}-{m.group(2)}", p.stdout.strip())
            svg = svg.replace("<svg ", f'<svg class="rd-svg rd-{theme}" ', 1)
            out.append(svg)
    return "".join(out)


def render_diagram_module(path, prefix):
    """`{key: [{svg, caption, source}]}` from the module at `path`, which defines `DIAGRAMS = {key: [(fig, caption)]}`.
    A fig is reladraw source text or a function that returns a diagrams_lib D; `source` is the reladraw text or None.
    `prefix` keeps SVG ids unique across modules."""
    spec = importlib.util.spec_from_file_location(f"review_diagrams_{prefix}".replace("-", "_"), path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    out = {}
    for key, figs in mod.DIAGRAMS.items():
        out[str(key)] = [{"svg": render_reladraw(fig, f"rd{prefix}{key}-{i}".replace(".", "-")) if isinstance(fig, str)
                          else fig().svg(), "caption": caption, "source": fig if isinstance(fig, str) else None}
                         for i, (fig, caption) in enumerate(figs)]
    return out


def load_diagrams(base, cfg):
    """The final report's diagrams, keyed by section number. Prefer reladraw; use D when reladraw cannot say the
    arrangement."""
    if not cfg.get("diagrams"):
        return {}
    return render_diagram_module(base / cfg["diagrams"], "")


DIAGRAM_SLOT_RE = re.compile(r"^\[\[diagram:([\w.\-]+)\]\]$", re.M)


def load_doc_diagrams(path, prefix, doc_id, md):
    """A document's own diagrams. Its Markdown places each with a line `[[diagram:<key>]]`; every key needs exactly
    one such line, and every line a key."""
    if not path.exists():
        fail(f"{doc_id}: diagrams module {path.name} is missing")
    figs = render_diagram_module(path, prefix)
    slots = DIAGRAM_SLOT_RE.findall(md)
    for k in figs:
        if slots.count(k) != 1:
            fail(f"{doc_id}: diagram {k} needs exactly one [[diagram:{k}]] line, found {slots.count(k)}")
    for k in slots:
        if k not in figs:
            fail(f"{doc_id}: [[diagram:{k}]] names no diagram in {path.name}")
    return figs


def main(config_path):
    cfg_path = Path(config_path).resolve()
    base = cfg_path.parent
    cfg = json.loads(cfg_path.read_text())
    repo = Path(cfg["repo_dir"]) if cfg.get("repo_dir") else Path(git(base, "rev-parse", "--show-toplevel").strip())
    if not repo.is_absolute():
        repo = base / repo
    forbidden = cfg.get("forbidden", DEFAULT_FORBIDDEN)
    gh = f"https://github.com/{cfg['repo']}"

    report = (base / cfg["report"]).read_text()
    check_text(cfg["report"], report, forbidden)
    summaries = cfg.get("summaries") or {}
    if isinstance(summaries, str):
        summaries = json.loads((base / summaries).read_text())

    reviewed = cfg["reviewed_sha"]
    views, names = [], []
    for v in cfg["views"]:
        if v.get("kind") == "code":
            cv, names = load_code_view(base, v, repo, cfg.get("tests_diff_against", "HEAD"))
            views.append(cv)
        elif v.get("kind") == "proposal":
            views.append(load_proposal_view(base, v, repo, forbidden))
        else:
            views.append(load_doc_view(base, v, forbidden))
        # whether "Copy as text" includes the view by default; without it, test code and proposals only
        if "copy" in v:
            views[-1]["copy"] = bool(v["copy"])

    # every test the report names must exist in the test code
    known = {n["name"] for n in names}
    for m in re.finditer(r"`(?:[\w.\-]+/)?([a-z0-9\-]+-test)`", report):
        if m.group(1) not in known and m.group(1) not in cfg.get("existing_tests", []):
            fail(f"the report names test {m.group(1)}, which is not in the test code (list pre-existing tests in "
                 f"existing_tests)")

    meta = {
        "title": cfg["title"], "subtitle": cfg.get("subtitle", ""), "storageKey": f"cr-{cfg.get('pr', reviewed[:8])}",
        "pr": {"number": cfg["pr"], "url": f"{gh}/pull/{cfg['pr']}"} if cfg.get("pr") else None,
        "ticket": cfg.get("ticket"),
        "reviewed": {"sha": reviewed, "url": f"{gh}/commit/{reviewed}", "label": cfg.get("reviewed_label", "reviewed commit")},
    }
    tulip = None
    if cfg.get("tulip"):
        # Tulip's walkthrough becomes the left-most tab: tulip_import makes it one document, shown in an iframe.
        import tulip_import
        t = cfg["tulip"] if isinstance(cfg["tulip"], dict) else {"html": cfg["tulip"]}
        path = base / t["html"]
        if not path.exists():
            fail(f"tulip: {path.name} is missing")
        label = t.get("label") or f"Local commits, ending at {reviewed[:12]}"
        html_t = tulip_import.convert(path, label=label, inline_mermaid=t.get("inline_mermaid", False))
        check_text("the Tulip page", html_t, forbidden)
        tulip = {"tab": t.get("tab", "Walkthrough"), "html": html_t}
    payload = {
        "meta": meta, "report": report, "summaries": summaries, "diagrams": load_diagrams(base, cfg), "tulip": tulip,
        "views": views, "testNames": names, "howto": cfg["howto"],
        "copyIntro": cfg.get("copy_intro", ""),
    }
    # Escape every "<" as \u003c, a valid JSON escape: then no "</script" or "<!--" in the data can end or change the
    # <script> element that holds it. ("<\!--" was the old escape, and JSON.parse rejects it.)
    blob = json.dumps(payload, ensure_ascii=False).replace("<", "\\u003c")
    template = (ASSETS / "template.html").read_text()
    html = template.replace("{{PAGE_TITLE}}", cfg["page_title"]).replace("/*DOCS*/", blob)
    out = base / cfg.get("out", "review.html")
    out.write_text(html)
    patches = [v["patch"] for v in views if v.get("kind") == "code" and v.get("patch")]
    if patches:
        (base / "review-tests.patch").write_text(patches[0])
    for i in (i for v in views if v.get("kind") == "proposal" for i in v["items"] if i.get("patch")):
        (base / i["out"]).write_text(i["patch"])
    n_files = sum(len(v["items"]) for v in views if v.get("kind") == "code")
    print(f"wrote {out} ({len(html):,} bytes); {len(names)} tests in {n_files} files")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        fail("usage: build.py <workspace>/review.json")
    main(sys.argv[1])
