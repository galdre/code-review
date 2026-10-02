"""Example diagrams module for a review workspace (copy it to diagrams.py and replace the diagrams).

Prefer reladraw: write the diagram as reladraw source text, and the build renders it in the page's light and dark
themes. Use a diagrams_lib function only when reladraw cannot say the arrangement.
"""
from diagrams_lib import D, C0, C1, C2

# reladraw: say where each box goes; the tool works out the distances. Red marks the problem, green an approved fix.
CALL_PATH = """
style bad   border: #d1242f  text: (color: #d1242f)
style good  border: #1a7f37  text: (color: #1a7f37)

node api     "POST /api/card"
node check   "check-permissions"  right of api
node db      "app DB: report_card"  right of check  style: bad

edge api -> check  "calls"
edge check -> db   "writes before the check ends"  line: (color: #d1242f)
"""


def fix_path():
    # The fallback: explicit coordinates. Labels go under the boxes, because a 60-pixel gap has no room for them.
    return (D("fix", 760, 110, "The write happens after the check")
            .box("api", C0, 20, "POST /api/card")
            .box("check", C1, 20, "check-permissions", good=True)
            .box("db", C2, 20, "app DB: report_card")
            .edge("api", "r", "check", "l", "calls", lab=(250, 90), anchor="middle")
            .edge("check", "r", "db", "l", "writes after the check", good=True, lab=(510, 90), anchor="middle"))


DIAGRAMS = {
    "2": [(CALL_PATH, "The endpoint writes the card before the permission check ends."),
          (fix_path, "The approved fix: the write happens after the check.")],
}
