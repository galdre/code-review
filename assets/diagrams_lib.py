"""A small library for hand-placed inline SVG diagrams in the review page.

This is the fallback. Write a diagram in reladraw first (see diagrams.example.py); use this library only when
reladraw cannot say the arrangement.

A diagram is a set of boxes at explicit coordinates and edges between box sides. Colors come from CSS classes in
the page template, so diagrams follow the light and dark themes. Mark the failing parts with bad=True (red); mark
the corrected path with good=True (green) only after the user approves the fix it shows.
"""
from html import escape

BH = 44  # box height


class D:
    def __init__(self, key, w, h, label):
        self.key, self.w, self.h, self.label = key, w, h, label
        self.boxes, self.parts = {}, []

    def box(self, bid, x, y, title, sub="", bad=False, good=False, w=200):
        self.boxes[bid] = (x, y, w)
        cls = "dg-box" + (" bad" if bad else "") + (" good" if good else "")
        self.parts.append(
            f'<g class="{cls}"><rect x="{x}" y="{y}" width="{w}" height="{BH}" rx="6"/>'
            f'<text class="dg-t" x="{x + 10}" y="{y + 18}">{escape(title)}</text>'
            + (f'<text class="dg-s" x="{x + 10}" y="{y + 34}">{escape(sub)}</text>' if sub else "")
            + "</g>")
        return self

    def anchor(self, bid, side):
        x, y, w = self.boxes[bid]
        return {"t": (x + w / 2, y), "b": (x + w / 2, y + BH), "l": (x, y + BH / 2), "r": (x + w, y + BH / 2)}[side]

    def edge(self, a, sa, b, sb, label=None, bad=False, good=False, dashed=False, via=(), lab=None, anchor="start"):
        pts = [self.anchor(a, sa), *via, self.anchor(b, sb)]
        d = "M " + " L ".join(f"{px:.0f} {py:.0f}" for px, py in pts)
        tone = "bad" if bad else "good" if good else ""
        cls = "dg-e" + (f" {tone}" if tone else "") + (" dashed" if dashed else "")
        marker = f"url(#{self.key}-{tone or 'arr'})"
        self.parts.append(f'<path class="{cls}" d="{d}" marker-end="{marker}"/>')
        if label:
            lx, ly = lab if lab else ((pts[0][0] + pts[1][0]) / 2 + 6, (pts[0][1] + pts[1][1]) / 2 + 4)
            self.note(lx, ly, label, bad=bad, good=good, anchor=anchor)
        return self

    def note(self, x, y, text, bad=False, good=False, anchor="start"):
        tone = " bad" if bad else " good" if good else ""
        self.parts.append(f'<text class="dg-l{tone}" x="{x:.0f}" y="{y:.0f}" '
                          f'text-anchor="{anchor}">{escape(text)}</text>')
        return self

    def frame(self, x, y, w, h, text):
        self.parts.append(f'<rect class="dg-frame" x="{x}" y="{y}" width="{w}" height="{h}" rx="8"/>'
                          f'<text class="dg-l" x="{x + 10}" y="{y + 16}">{escape(text)}</text>')
        return self

    def hline(self, x1, x2, y, text):
        self.parts.append(f'<line class="dg-e dashed" x1="{x1}" y1="{y}" x2="{x2}" y2="{y}"/>'
                          f'<text class="dg-l" x="{x2}" y="{y - 5}" text-anchor="end">{escape(text)}</text>')
        return self

    def svg(self):
        defs = (f'<defs>'
                f'<marker id="{self.key}-arr" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path class="dg-head" d="M0 0 L10 5 L0 10 z"/></marker>'
                f'<marker id="{self.key}-bad" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path class="dg-head bad" d="M0 0 L10 5 L0 10 z"/></marker>'
                f'<marker id="{self.key}-good" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path class="dg-head good" d="M0 0 L10 5 L0 10 z"/></marker>'
                f'</defs>')
        return (f'<svg class="dg-svg" viewBox="0 0 {self.w} {self.h}" role="img" aria-label="{escape(self.label)}">'
                + defs + "".join(self.parts) + "</svg>")



# Column x positions for a three-column layout in a 760-wide viewBox with 200-wide boxes.
C0, C1, C2 = 20, 280, 540
