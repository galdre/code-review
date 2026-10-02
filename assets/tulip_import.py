#!/usr/bin/env python3
"""Turn Tulip's output (index.html and its assets/ folder) into one self-contained HTML document.

Usage: tulip_import.py <tulip output>/index.html [--label TEXT] > tulip.html
build.py imports convert() when review.json has a "tulip" entry, and shows the result as the page's left-most tab,
inside an iframe. The iframe keeps Tulip's styles, ids and script apart from the review page, so nothing can clash,
and Tulip's own sidebar navigation and light and dark themes work as Tulip made them.

What the conversion does:
- inlines assets/style.css, and the fonts it names as data: URLs;
- inlines assets/app.js and Tulip's highlight.js bundle;
- loads mermaid from cdn.jsdelivr.net at the version Tulip shipped (Tulip's copy is 3.5 MB), unless inline_mermaid;
- replaces the link that Tulip's local mode writes for a pull request that does not exist with plain text (label);
- fails if a <script>, <link> or url() names an asset it cannot find.
"""
import argparse
import base64
import re
import sys
from pathlib import Path

LOCAL_PR_LINK = re.compile(r'<p class="pr-link"><a href="https://local/[^"]*">[^<]*</a></p>')
MIME = {".woff2": "font/woff2", ".woff": "font/woff", ".ttf": "font/ttf", ".svg": "image/svg+xml", ".png": "image/png"}


def fail(msg):
    raise SystemExit(f"tulip_import: {msg}")


def mermaid_version(js):
    # The bundle holds the version strings of mermaid and of the libraries inside it; mermaid's is the highest.
    found = {tuple(map(int, v.split("."))) for v in re.findall(r'version:"(\d+\.\d+\.\d+)"', js)}
    found.discard((0, 0, 0))
    return ".".join(map(str, max(found))) if found else None


def inline_css(css, css_dir):
    def data_url(m):
        ref = m.group(2)
        if ref.startswith(("data:", "#")):
            return m.group(0)
        p = (css_dir / ref).resolve()
        if not p.exists():
            fail(f"style.css names {ref}, which is not in Tulip's output")
        b64 = base64.b64encode(p.read_bytes()).decode()
        return f'url("data:{MIME.get(p.suffix, "application/octet-stream")};base64,{b64}")'
    return re.sub(r'url\((["\']?)([^)"\']+)\1\)', data_url, css)


def script_text(js):
    # A script inside an HTML document ends at the first "</script"; escape it inside the code.
    return js.replace("</script", "<\\/script")


def convert(index_html, label=None, inline_mermaid=False):
    index_html = Path(index_html)
    base = index_html.parent
    html = index_html.read_text()

    def link(m):
        p = base / m.group(1)
        if not p.exists():
            fail(f"index.html links {m.group(1)}, which is not in Tulip's output")
        return f"<style>\n{inline_css(p.read_text(), p.parent)}\n</style>"
    html = re.sub(r'<link rel="stylesheet" href="([^"]+)">', link, html)

    def script(m):
        src, rest = m.group(1), m.group(2)
        p = base / src
        if not p.exists():
            fail(f"index.html loads {src}, which is not in Tulip's output")
        js = p.read_text()
        if p.name == "mermaid.min.js" and not inline_mermaid:
            version = mermaid_version(js)
            if not version:
                fail("cannot read the mermaid version from Tulip's mermaid.min.js; use inline_mermaid")
            return f'<script src="https://cdn.jsdelivr.net/npm/mermaid@{version}/dist/mermaid.min.js"></script>'
        # Tulip loads its scripts at the end of <body>, so an inline copy runs before DOMContentLoaded, as a deferred
        # script does; app.js starts on DOMContentLoaded.
        return f"<script>\n{script_text(js)}\n</script>"
    html = re.sub(r'<script src="([^"]+)"([^>]*)></script>', script, html)

    text = label or "A local commit range (no pull request)"
    html = LOCAL_PR_LINK.sub(f'<p class="pr-link">{text}</p>', html)
    left = re.findall(r'(?:src|href)="(assets/[^"]+)"', html)
    if left:
        fail(f"assets still linked after the conversion: {left[:3]}")
    return html


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("index_html")
    ap.add_argument("--label", help="text in place of a local-mode pull request link")
    ap.add_argument("--inline-mermaid", action="store_true", help="inline Tulip's mermaid (3.5 MB) instead of a CDN")
    a = ap.parse_args()
    sys.stdout.write(convert(a.index_html, a.label, a.inline_mermaid))
