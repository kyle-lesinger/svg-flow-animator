"""
Every coordinate in the diagram, each one a handle in the editor.

Transcribed from page 2 of the Lucid source ("Managed Services Account" /
"External"), with Compute Instances dropped as redundant: the Data Processing
System produces into File Storage directly.

Nothing here is hardcoded past its default. A node is an `ov.point`, its label
an `ov.offset` from it (so it follows the node however far it is dragged), its
icon size an `ov.scalar`, a box an `ov.rect`, a connector an `ov.path`, and an
edge label's position along its line an `ov.scalar` in 0..1. Change a default
here, or drag it in the editor and Save -- overrides.json wins either way.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "..")))
sys.path.insert(0, HERE)

from svg_flow_animator import overrides as ov  # noqa: E402

# The live-preview server hands candidate overrides in through the environment
# (svg_flow_animator.serve). Otherwise, the project's own file.
ov.use(os.environ.get("FLOWGIF_OVERRIDES") or os.path.join(HERE, "overrides.json"))

# The figure, and a band beneath it that belongs to the words. Captions and
# screenshots live ONLY in the band, so nothing ever lands on top of a line or
# a label -- floating bubbles had to be placed around the figure and kept
# covering parts of it.
W = 1600
DIAGRAM_H = 900
BAND = 210
H = DIAGRAM_H + BAND

# ------------------------------------------------------------------ boxes ---
MANAGED = ov.rect("box.managed", (30, 40, 1190, 560), "Managed Services Account")
EXTERNAL = ov.rect("box.external", (30, 640, 1190, 235), "Externally Managed Accounts")
DASHBOARD = ov.rect("box.dashboard", (420, 95, 400, 180), "User Dashboard")
BOXES = {"box.managed": MANAGED, "box.external": EXTERNAL, "box.dashboard": DASHBOARD}

# Two caption slots in the band: centred on its own, or to the left of a
# screenshot when the beat has one.
CAPTION = ov.rect("box.caption", (250, 925, 1100, 165), "caption")
CAPTION_BESIDE_SHOT = ov.rect("box.caption_shot", (30, 925, 540, 165),
                              "caption beside a screenshot")

# Titles ride on their box: an offset from its top-left corner. The External
# title sits at the BOTTOM-left -- every boundary-crossing line enters that box
# through its top edge, and a top-left title had two of them cutting through it.
TITLE_MANAGED = ov.offset("label.box.managed", (22, 36), "box.managed", MANAGED,
                          "Managed title")
BADGE_MANAGED = ov.offset("label.box.managed.badge", (22, 60), "box.managed",
                          MANAGED, "Managed badge")
TITLE_EXTERNAL = ov.offset("label.box.external", (22, 193), "box.external",
                           EXTERNAL, "External title")
BADGE_EXTERNAL = ov.offset("label.box.external.badge", (22, 219), "box.external",
                           EXTERNAL, "External badge")
TITLE_DASHBOARD = ov.offset("label.box.dashboard", (12, 22), "box.dashboard",
                            DASHBOARD, "User Dashboard title")

# Which account a node lives in decides its ownership colour; a flow whose two
# ends are in different accounts is a boundary crossing and is drawn dashed.
# Personas belong to neither.
#   key: (default centre, icon, label, account)
_NODES = {
    "operator":     ((1420, 150), "user-check",
                     "Data Production Operator\n/ Algorithm Developer", None),
    "auth":         ((170, 165), "shield-check",
                     "Authentication &\nAuthorization", "managed"),
    "ade":          ((525, 170), "notebook-pen",
                     "Algorithm Development\nEnvironment", "managed"),
    "jmd":          ((715, 170), "monitor-dot",
                     "Job Monitoring\nDashboard", "managed"),
    "dps":          ((525, 365), "server", "Data Processing\nSystem", "managed"),
    "api":          ((880, 365), "arrow-left-right", "Data Service APIs", "managed"),
    "viz":          ((1080, 365), "map-pinned", "Visualization Tools", "managed"),
    "catalog":      ((880, 520), "library", "Data Catalog", "managed"),
    "users":        ((170, 745), "users", "User Management", "external"),
    "algcat":       ((400, 745), "package", "Algorithm Catalog", "external"),
    "orgade":       ((620, 745), "notebook-pen",
                     "Algorithm Development\nEnvironment", "external"),
    "files":        ((860, 745), "hard-drive", "File Storage", "external"),
    "orgviz":       ((1080, 745), "map-pinned", "Visualization Tools", "external"),
    "investigator": ((1420, 745), "user-check",
                     "Science Investigator\n/ Algorithm Developer", None),
}
PERSONAS = ("operator", "investigator")

ICON_DEFAULT = 54
NODES = {}
for _k, (_c, _icon, _label, _acct) in _NODES.items():
    _size = ov.scalar(f"node.{_k}.size", 62 if _k in PERSONAS else ICON_DEFAULT,
                      f"{_label.splitlines()[0]} (icon size)")
    _pos = ov.point(f"node.{_k}", _c, _label.replace("\n", " "),
                    size_key=f"node.{_k}.size")
    NODES[_k] = dict(
        c=_pos, size=_size, icon=_icon, label=_label, account=_acct,
        label_c=ov.offset(f"label.{_k}", (0, _size / 2 + 20), f"node.{_k}",
                          _pos, _label.replace("\n", " ") + " (label)"),
    )

# ------------------------------------------------------------- connectors ---
# key: (src, dst, edge label, default polyline)
# The direction is a CLAIM about the architecture, transcribed from the Lucid
# arrows and then corrected where README.md says so -- not a visual choice. See README "What the diagram asserts".
_FLOWS = {
    "op_dash":       ("operator", "dashboard", "Accesses",
                      [(1385, 160), (822, 160)]),
    "auth_dash":     ("auth", "dashboard", "Authenticates",
                      [(205, 165), (418, 165)]),
    "auth_users":    ("auth", "users", "Reads",
                      [(170, 240), (170, 708)]),
    "dps_algcat":    ("dps", "algcat", "Accesses",
                      [(490, 380), (400, 430), (400, 708)]),
    "ade_dps":       ("ade", "dps", "Triggers",
                      [(525, 245), (525, 328)]),
    "dps_jmd":       ("dps", "jmd", "Writes",
                      [(560, 335), (640, 300), (700, 245)]),
    "dps_files":     ("dps", "files", "Writes outputs",
                      [(525, 430), (525, 618), (845, 618), (845, 708)]),
    "dps_catalog":   ("dps", "catalog", "Updates STAC collections",
                      [(556, 370), (620, 370), (720, 520), (843, 520)]),
    "api_viz":       ("api", "viz", "Serves",
                      [(915, 365), (1045, 365)]),
    "api_cat":       ("api", "catalog", "Queries",
                      [(880, 410), (880, 483)]),
    "cat_files":     ("catalog", "files", "Indexes",
                      [(880, 568), (880, 708)]),
    "op_viz":        ("operator", "viz", "Views",
                      [(1365, 232), (1250, 290), (1115, 350)]),
    "op_orgviz":     ("operator", "orgviz", "Views",
                      [(1475, 232), (1500, 420), (1300, 640), (1115, 735)]),
    "inv_orgade":    ("investigator", "orgade", "Accesses",
                      [(1420, 828), (1380, 848), (620, 848), (620, 812)]),
    "orgade_algcat": ("orgade", "algcat", "Publishes",
                      [(585, 745), (436, 745)]),
    "orgade_files":  ("orgade", "files", "Reads",
                      [(655, 745), (824, 745)]),
    "inv_orgviz":    ("investigator", "orgviz", "Views",
                      [(1383, 745), (1115, 745)]),
    "inv_viz":       ("investigator", "viz", "Views",
                      [(1385, 712), (1290, 520), (1115, 385)]),
}
FLOWS = {k: dict(src=s, dst=d, label=lab, default=pts)
         for k, (s, d, lab, pts) in _FLOWS.items()}


def account_of(name):
    if name in NODES:
        return NODES[name]["account"]
    return {"dashboard": "managed"}.get(name)


# Crossing flows are dashed, except these, which are drawn solid by choice:
# the run chapter's two outputs read as one pair, so they look alike.
SOLID = frozenset(("dps_files",))


def crosses(key):
    """Does this flow cross between the two accounts? Personas belong to
    neither, so a persona's own flows never count as a crossing."""
    f = FLOWS[key]
    a, b = account_of(f["src"]), account_of(f["dst"])
    return a is not None and b is not None and a != b


def flow_path(key):
    """
    The resolved polyline. Registration is lazy -- an `ov.path` only becomes a
    handle when this is called -- so `warm_up()` calls it for every flow.
    """
    f = FLOWS[key]
    return ov.path(f"flow.{key}", f["default"], f"{f['src']} -> {f['dst']}")


# Edge labels sit mid-line unless a longer one needs a straighter stretch.
_LABEL_T = {"dps_catalog": 0.72}


def flow_label_t(key):
    """Where the edge label sits along its line, 0 (source) .. 1 (target)."""
    return ov.scalar(f"flowlabel.{key}.t", _LABEL_T.get(key, 0.5),
                     f"'{FLOWS[key]['label']}' position on {key}")


def warm_up():
    for k in FLOWS:
        flow_path(k)
        flow_label_t(k)
    for k in SHOTS:
        shot_rect(k)


# ------------------------------------------------------------ screenshots ---
from story import SHOTS  # noqa: E402

_SHOT_DEFAULT = (590, 920, 980, 140)


def shot_rect(key):
    return ov.rect(f"shot.{key}", _SHOT_DEFAULT, f"screenshot: {key}")
