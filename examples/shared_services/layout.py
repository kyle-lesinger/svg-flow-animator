"""
Every coordinate in the diagram, each one a handle in the editor.

The shared-capabilities variant of examples/managed_services. A third, purple
box sits between the managed (blue) and externally managed (red) accounts and
holds the capabilities both use: ONE Algorithm Catalog, ONE Data Catalog and
ONE set of Visualization Tools. Anything in the purple box exists nowhere
else -- the point of the figure is that nothing is duplicated.

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
DIAGRAM_H = 960
BAND = 210
H = DIAGRAM_H + BAND

# ------------------------------------------------------------------ boxes ---
MANAGED = ov.rect("box.managed", (30, 30, 1190, 420), "Managed Services Account")
SHARED = ov.rect("box.shared", (30, 475, 1190, 180), "Shared Data System Capabilities")
EXTERNAL = ov.rect("box.external", (30, 680, 1190, 260), "Externally Managed Accounts")
DASHBOARD = ov.rect("box.dashboard", (420, 85, 400, 180), "User Dashboard")
BOXES = {"box.managed": MANAGED, "box.shared": SHARED, "box.external": EXTERNAL,
         "box.dashboard": DASHBOARD}

# Two caption slots in the band: centred on its own, or to the left of a
# screenshot when the beat has one.
CAPTION = ov.rect("box.caption", (250, 985, 1100, 165), "caption")
CAPTION_BESIDE_SHOT = ov.rect("box.caption_shot", (30, 985, 540, 165),
                              "caption beside a screenshot")

# Titles ride on their box: an offset from its top-left corner. Each sits in
# the one stretch of its box's edge no line crosses: External at the
# bottom-left, Shared at the bottom-RIGHT (right-aligned on its offset), since
# lines run into and out of the purple box along most of both edges.
TITLE_MANAGED = ov.offset("label.box.managed", (22, 36), "box.managed", MANAGED,
                          "Managed title")
TITLE_SHARED = ov.offset("label.box.shared", (1182, 162), "box.shared", SHARED,
                         "Shared title (right-aligned)")
TITLE_EXTERNAL = ov.offset("label.box.external", (22, 237), "box.external",
                           EXTERNAL, "External title")
TITLE_DASHBOARD = ov.offset("label.box.dashboard", (12, 22), "box.dashboard",
                            DASHBOARD, "User Dashboard title")

# Which account a node lives in decides its ownership colour; a flow whose two
# ends are in different accounts is a boundary crossing and is drawn dashed.
# Personas belong to neither.
#   key: (default centre, icon, label, account)
_NODES = {
    "operator":     ((1420, 150), "user-check",
                     "Data Production Operator\n/ Algorithm Developer", None),
    "auth":         ((110, 165), "shield-check",
                     "Authentication &\nAuthorization", "managed"),
    "ade":          ((525, 170), "notebook-pen",
                     "Algorithm Development\nEnvironment", "managed"),
    "jmd":          ((715, 170), "monitor-dot",
                     "Job Monitoring\nDashboard", "managed"),
    "dps":          ((525, 365), "server", "Data Processing\nSystem", "managed"),
    "api":          ((880, 365), "arrow-left-right", "Data Service APIs", "managed"),
    # The shared capabilities: one of each, and nowhere else.
    "algcat":       ((400, 555), "package", "Algorithm Catalog", "shared"),
    "catalog":      ((880, 555), "library", "Data Catalog", "shared"),
    "viz":          ((1080, 555), "map-pinned", "Visualization Tools", "shared"),
    "users":        ((110, 790), "users", "User Management", "external"),
    "orgade":       ((620, 790), "notebook-pen",
                     "Algorithm Development\nEnvironment", "external"),
    "files":        ((860, 790), "hard-drive", "File Storage", "external"),
    # The users column. Everyone but the operator appears only when the story
    # reaches them; see LATE_PERSONAS.
    "investigator": ((1420, 360), "user-check",
                     "Science Investigator\n/ Algorithm Developer", None),
    "developer":    ((1420, 570), "user-cog", "Applications\nDeveloper", None),
    "analyst":      ((1420, 780), "user-search", "Decision Maker\n/ Analyst", None),
}
PERSONAS = ("operator", "investigator", "developer", "analyst")
# Hidden until their first beat, then they stay: the closing frame shows every
# kind of user the architecture serves.
LATE_PERSONAS = ("investigator", "developer", "analyst")

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
                      [(145, 165), (418, 165)]),
    "auth_users":    ("auth", "users", "Reads",
                      [(110, 240), (110, 753)]),
    "dps_algcat":    ("dps", "algcat", "Accesses",
                      [(490, 380), (400, 430), (400, 518)]),
    "ade_dps":       ("ade", "dps", "Triggers",
                      [(525, 245), (525, 328)]),
    "jmd_dps":       ("jmd", "dps", "Reads",
                      [(700, 245), (640, 300), (560, 335)]),
    "dps_files":     ("dps", "files", "Writes outputs",
                      [(525, 430), (525, 667), (845, 667), (845, 753)]),
    "dps_catalog":   ("dps", "catalog", "Updates STAC collections",
                      [(556, 370), (620, 370), (720, 555), (843, 555)]),
    "api_viz":       ("api", "viz", "Serves",
                      [(912, 385), (1055, 522)]),
    "api_cat":       ("api", "catalog", "Queries",
                      [(880, 410), (880, 518)]),
    "cat_files":     ("catalog", "files", "Indexes",
                      [(880, 612), (880, 753)]),
    # Users' lines. TEMPORARY (see TRANSIENT): each user's set draws in, then
    # fades once the next user's lines are in. Routed down the lane between the
    # boxes and the users column, so they never cross a user's label.
    "op_viz":        ("operator", "viz", "Views",
                      [(1386, 185), (1240, 300), (1240, 470), (1117, 550)]),
    "inv_viz":       ("investigator", "viz", "Views",
                      [(1385, 365), (1250, 420), (1117, 545)]),
    "inv_orgade":    ("investigator", "orgade", "Accesses",
                      [(1388, 385), (1262, 440), (1262, 905), (620, 905),
                       (620, 862)]),
    "dev_api":       ("developer", "api", "Calls",
                      [(1385, 560), (1200, 470), (917, 385)]),
    "ana_viz":       ("analyst", "viz", "Views",
                      [(1385, 770), (1250, 680), (1117, 565)]),
    "orgade_algcat": ("orgade", "algcat", "Publishes",
                      [(590, 762), (438, 585)]),
    "orgade_files":  ("orgade", "files", "Reads",
                      [(655, 790), (824, 790)]),
}
FLOWS = {k: dict(src=s, dst=d, label=lab, default=pts)
         for k, (s, d, lab, pts) in _FLOWS.items()}

# Every line a user draws, except the operator's way in at the start of the
# story, which stays: it is how the whole journey begins.
TRANSIENT = frozenset(k for k, f in FLOWS.items()
                      if f["src"] in PERSONAS and k != "op_dash")


def account_of(name):
    if name in NODES:
        return NODES[name]["account"]
    return {"dashboard": "managed", "managed": "managed", "shared": "shared",
            "external": "external"}.get(name)


# Crossing flows are dashed, except these, which are drawn solid by choice:
# the run chapter's two outputs read as one pair, so they look alike.
SOLID = frozenset(("dps_files", "dps_catalog"))


def crosses(key):
    """Does this flow cross between two boxes (managed, shared, external)?
    Personas belong to none, so a persona's own flows never count."""
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
# The ones crossing the gap between purple and red slide into the red box, so
# two labels never share that narrow strip.
_LABEL_T = {"dps_catalog": 0.72, "orgade_algcat": 0.3, "cat_files": 0.72}


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

_SHOT_DEFAULT = (590, 980, 980, 140)


def shot_rect(key):
    return ov.rect(f"shot.{key}", _SHOT_DEFAULT, f"screenshot: {key}")
