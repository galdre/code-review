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
        ".js": "javascript", ".jsx": "javascript", ".sql": "sql", ".json": "json", ".yaml": "yaml", ".yml": "yaml"}
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
    if not path.endswith((".clj", ".cljc", ".cljs")):
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
    return {"key": view["key"], "tab": view["tab"], "title": view["title"], "intro": view["intro"], "items": items}


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
    patch = "".join(patch_parts)
    items.append({"id": "patch", "short": "all", "nav": "All tests as one patch", "patch": patch,
                  "summary": view.get("patch_summary", "This patch contains every test that this review added. It "
                                                       "applies to the reviewed commit.")})
    return {"key": view["key"], "tab": view["tab"], "title": view["title"], "intro": view["intro"], "kind": "code",
            "items": items}, names


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


def load_diagrams(base, cfg):
    """A diagram entry is (function, caption), where the function returns a diagrams_lib D, or
    (reladraw source text, caption). Prefer reladraw; use D when reladraw cannot say the arrangement."""
    if not cfg.get("diagrams"):
        return {}
    spec = importlib.util.spec_from_file_location("review_diagrams", base / cfg["diagrams"])
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    out = {}
    for section, figs in mod.DIAGRAMS.items():
        out[str(section)] = [{"svg": render_reladraw(fig, f"rd{section}-{i}".replace(".", "-")) if isinstance(fig, str)
                              else fig().svg(), "caption": caption}
                             for i, (fig, caption) in enumerate(figs)]
    return out


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

    views, names = [], []
    for v in cfg["views"]:
        if v.get("kind") == "code":
            cv, names = load_code_view(base, v, repo, cfg.get("tests_diff_against", "HEAD"))
            views.append(cv)
        else:
            views.append(load_doc_view(base, v, forbidden))

    # every test the report names must exist in the test code
    known = {n["name"] for n in names}
    for m in re.finditer(r"`(?:[\w.\-]+/)?([a-z0-9\-]+-test)`", report):
        if m.group(1) not in known and m.group(1) not in cfg.get("existing_tests", []):
            fail(f"the report names test {m.group(1)}, which is not in the test code (list pre-existing tests in "
                 f"existing_tests)")

    reviewed = cfg["reviewed_sha"]
    meta = {
        "title": cfg["title"], "subtitle": cfg.get("subtitle", ""), "storageKey": f"cr-{cfg.get('pr', reviewed[:8])}",
        "pr": {"number": cfg["pr"], "url": f"{gh}/pull/{cfg['pr']}"} if cfg.get("pr") else None,
        "ticket": cfg.get("ticket"),
        "reviewed": {"sha": reviewed, "url": f"{gh}/commit/{reviewed}", "label": cfg.get("reviewed_label", "reviewed commit")},
    }
    payload = {
        "meta": meta, "report": report, "summaries": summaries, "diagrams": load_diagrams(base, cfg),
        "views": views, "testNames": names, "howto": cfg["howto"],
        "copyIntro": cfg.get("copy_intro", ""),
    }
    blob = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/").replace("<!--", "<\\!--")
    template = (ASSETS / "template.html").read_text()
    html = template.replace("{{PAGE_TITLE}}", cfg["page_title"]).replace("/*DOCS*/", blob)
    out = base / cfg.get("out", "review.html")
    out.write_text(html)
    patches = [i["patch"] for v in views if v.get("kind") == "code" for i in v["items"] if i.get("patch")]
    if patches:
        (base / "review-tests.patch").write_text(patches[0])
    n_files = sum(1 for v in views if v.get("kind") == "code" for i in v["items"] if not i.get("patch"))
    print(f"wrote {out} ({len(html):,} bytes); {len(names)} tests in {n_files} files")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        fail("usage: build.py <workspace>/review.json")
    main(sys.argv[1])
