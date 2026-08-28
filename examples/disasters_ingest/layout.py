#!/usr/bin/env python3
"""
Single source of truth for the restructured diagram geometry.

Design space is 1600x900 (16:9). The organising idea: STAC sits on the exact
canvas centre (800, 450), because it is the one box every other box touches.
Everything else is placed as a balanced pair around it:

    Data Integration  (left)   <-> Portal Content        (right)
    Earthdata GIS     (above)  <-> Data Processing       (below)
    Funded Projects   (bot-L)  <-> Community & Engagement (bot-R)
    Airflow SM2A      (feeds STAC from the left) <-> TinaCMS (draws from the right)

Everything downstream (frame generator, GIF builder) reads coordinates from
here, so the layout can be retuned in one place.
"""

import math
import os

import overrides as ov

WD = os.path.dirname(os.path.abspath(__file__))
ASSETS = WD + "/assets"              # canonical extraction target
FRAMES = WD + "/frames"
# librsvg refuses to load a resource outside the referencing document's own
# directory tree, so every frame points at a copy that lives *below* frames/.
FRAME_ASSETS = FRAMES + "/assets"

# ---------------------------------------------------------------- canvas ----
W, H = 1600, 900
CX, CY = W / 2, H / 2          # (800, 450) -- STAC's centre

FONT = "Helvetica Neue, Helvetica, Arial, sans-serif"

# ---------------------------------------------------------------- colours ---
INK = "#2b3138"
EDGE = "#3a414a"
BG = "#ffffff"

FILL_INTEGRATION = "#f7f4e4"
FILL_STAC = "#c3f7c8"
FILL_EGIS = "#fff0fb"
FILL_PROCESSING = "#edf5ff"
FILL_PORTAL = "#fff0f0"
FILL_FUNDED = "#f2f2ff"
FILL_COMMUNITY = "#fbf0ff"

FLOW = "#008a0e"               # the green used for flow arrows in the original
DOT = "#ff7a00"                # amber travelling packets -- reads on every fill
GLOW = "#1856ed"               # highlight ring on the active region
BUBBLE_BG = "#12243d"
BUBBLE_FG = "#ffffff"

CONTEXT_OPACITY = 0.40         # greyed-out boxes that are never animated

# ------------------------------------------------------------- containers ---
# (x, y, w, h)
BOX_INTEGRATION = ov.rect("box.integration", (40, 130, 550, 640), "Data Integration")
BOX_PORTAL = ov.rect("box.portal", (1010, 130, 550, 640), "Portal Content")
BOX_EGIS = ov.rect("box.egis", (680, 96, 240, 200), "Earthdata GIS")
BOX_PROCESSING = ov.rect("box.processing", (680, 604, 240, 200), "Data Processing")
BOX_STAC = ov.rect("box.stac", (660, 350, 280, 200), "STAC")
BOX_FUNDED = ov.rect("box.funded", (40, 800, 550, 80), "Funded Projects")
BOX_COMMUNITY = ov.rect("box.community", (1010, 800, 550, 80), "Community")

# Symmetry checks these satisfy:
#   left margin  40 == right margin  1600-1560
#   STAC centre  (800, 450) == canvas centre
#   gap DI->STAC 680-590 == 90 == gap STAC->Portal 1010-920
#   EGIS bottom 296 is 154 above centre; Processing top 604 is 154 below centre

# ------------------------------------------------- data integration innards --
SRC_ICON_W = 46
SRC_LABEL_DY = 46              # label baseline below the icon centre.
                               # The icon is 46 tall, so this clears its
                               # bottom edge by 23px instead of 9.
SRC_LABEL_CHARS = 15           # wrap width for a stacked label
SRC_LABEL_LH = 21              # line height for a wrapped label
HUB = ov.point("hub", (318, 450), "ingest hub")
BOX_INGEST = ov.rect("box.ingest", (338, 418, 162, 64), "VEDA Ingest UI")

PLUS_C = ov.point("node.plus", (516, 450), "+ glyph")
AIRFLOW_C = ov.point("node.airflow", (550, 450), "Airflow SM2A",
                     size_key="node.airflow.size")
AIRFLOW_SIZE = ov.scalar("node.airflow.size", 48, "Airflow SM2A size")
TINA_C = ov.point("node.tinacms", (975, 450), "TinaCMS",
                  size_key="node.tinacms.size")
TINA_SIZE = ov.scalar("node.tinacms.size", 58, "TinaCMS size")

# The six sources bow outward on an arc so they read as a semicircle wrapped
# around the VEDA Ingest UI, the way the original diagram did.
#
# y stays on an even pitch and only x is bowed. A true circular arc would
# compress the vertical gaps at its ends to ~70px, and an icon plus a stacked
# two-line label needs ~86px -- so a real arc collides with itself. Bowing x
# against an even y gives the radial look with none of the crowding.
SRC_PITCH = ov.scalar("src.pitch", 100, "vertical pitch")
SRC_BASE_X = ov.scalar("src.base_x", 196, "arc x at the ends")
SRC_BOW = ov.scalar("src.bow", 92, "how far the arc bulges left")

SOURCES = [
    {"label": "GIBS Catalog",         "kind": "cyl"},
    # The globe PNG has whitespace padding baked in, so it reads smaller than
    # the drawn icons at the same nominal size. Give it a larger default.
    {"label": "EGIS", "kind": "cyl", "logo": "bJ.png", "size": 66},
    {"label": "DAAC S3 Bucket",       "kind": "bucket"},
    {"label": "External AWS Bucket",  "kind": "bucket"},
    {"label": "CSDA AWS bucket",      "kind": "bucket"},
    {"label": "External GIS Catalog", "kind": "bucket"},
]


def _arc_default(i):
    """Even y, x bowed by (1 - t^2) where t is the distance from the middle."""
    n = len(SOURCES)
    cy = 450 + (i - (n - 1) / 2.0) * SRC_PITCH
    t = (cy - 450) / ((n - 1) / 2.0 * SRC_PITCH)
    return (SRC_BASE_X - SRC_BOW * (1 - t * t), cy)


for _i, _s in enumerate(SOURCES):
    # Size first: the point declares it so the editor can offer a resize grip.
    _s["size"] = ov.scalar("src.size.%d" % _i, _s.get("size", SRC_ICON_W),
                           _s["label"] + " size")
    _s["c"] = ov.point("src.%d" % _i, _arc_default(_i), _s["label"],
                       size_key="src.size.%d" % _i)
    # Stored as an OFFSET from the icon, so the label always travels with its
    # node and what you tune is the gap, not an absolute position.
    _s["label_c"] = ov.offset("label.src.%d" % _i, (0, SRC_LABEL_DY),
                              "src.%d" % _i, _s["c"],
                              _s["label"] + " (label)")

# The Disasters AWS Bucket sits ON the hub's vertical (x = HUB[0]) rather than
# in the source rank. That is what makes stage 4->5 a single uninterrupted
# straight run instead of a dogleg.
DISASTERS_ICON = ov.scalar("node.disasters_bucket.size", 48,
                           "Disasters AWS Bucket size")
DISASTERS_C = ov.point("node.disasters_bucket", (HUB[0], 712),
                       "Disasters AWS Bucket",
                       size_key="node.disasters_bucket.size")
LABEL_DISASTERS = ov.offset("label.disasters", (34, 4.5),
                            "node.disasters_bucket", DISASTERS_C,
                            "Disasters AWS Bucket (label)")
LABEL_PUSH = ov.offset("label.push", (30, 50), "node.disasters_bucket",
                       DISASTERS_C, "Push data (label)")
LABEL_AIRFLOW = ov.offset("label.airflow", (0, 40), "node.airflow", AIRFLOW_C,
                          "Airflow SM2A (label)")
LABEL_TINA = ov.offset("label.tinacms", (0, 45), "node.tinacms", TINA_C,
                       "TinaCMS (label)")
LABEL_TITLE_DI = ov.offset("label.title.integration", (18, 30),
                           "box.integration", BOX_INTEGRATION,
                           "\"Data Integration\" title")
LABEL_TITLE_FUNDED = ov.offset("label.title.funded", (18, 34),
                               "box.funded", BOX_FUNDED,
                               "\"Funded Projects\" title")

DISASTERS_TOP = DISASTERS_C[1] - DISASTERS_ICON / 2 + 1
DISASTERS_BOT = DISASTERS_C[1] + DISASTERS_ICON / 2 + 1

# The "Push data" riser from Funded Projects up into the Disasters bucket.
PUSH_X = DISASTERS_C[0]
PUSH_FROM_Y = 800
PUSH_TO_Y = DISASTERS_BOT + 2

# ------------------------------------------------------------------ assets --
A_INGEST = FRAME_ASSETS + "/bA.jpg"        # VEDA Ingest UI lockup
A_STAC = FRAME_ASSETS + "/bD.png"          # STAC wordmark
A_VEDA = FRAME_ASSETS + "/cy.png"          # NASA EARTHDATA VEDA wordmark
A_NASA = FRAME_ASSETS + "/cx.png"          # NASA meatball (ROSES)
A_ESRI = FRAME_ASSETS + "/cw.png"
A_EGIS = FRAME_ASSETS + "/bJ.png"
A_TINA = FRAME_ASSETS + "/cc.png"          # TinaCMS llama
A_AIRFLOW = ASSETS + "/airflow.svg"        # inlined, not href'd -- read from source dir
A_JUPYTER = FRAME_ASSETS + "/jupyter.png"
A_GITHUB = FRAME_ASSETS + "/github.png"
A_FEMA = FRAME_ASSETS + "/cu.png"
A_NOAA = FRAME_ASSETS + "/ct.png"
A_CENSUS = FRAME_ASSETS + "/cv.png"
A_ARCGIS_ONLINE = FRAME_ASSETS + "/cq.png"
A_ARCGIS_DESKTOP = FRAME_ASSETS + "/cr.png"
A_GRAFANA = FRAME_ASSETS + "/cn.png"
A_NEWSLETTER = FRAME_ASSETS + "/cG.png"
A_LISTSERV = FRAME_ASSETS + "/listserv.png"
A_MYST = FRAME_ASSETS + "/myst.png"
A_NOTEBOOK = FRAME_ASSETS + "/notebook.png"
A_SHOT_HOME = FRAME_ASSETS + "/home.png"   # live capture of science-dev.data.nasa.gov/disasters
A_SHOT_STORY = FRAME_ASSETS + "/aZ.jpg"
A_SHOT_TRAINING = FRAME_ASSETS + "/ce.jpg"
A_SHOT_VIZ = FRAME_ASSETS + "/aY.jpg"

# The Airflow blades were authored around this centre in source-SVG units;
# gen_frames re-origins them, but the spin needs the centre.
AIRFLOW_SRC_VIEWBOX = (1359.00, 1397.75, 126.75, 126.75)


# ------------------------------------------------------------- flow paths ---
def label_width(s, size=16.5):
    """Rough Helvetica advance width -- good enough to place a line after text."""
    return len(s) * size * 0.52


def spoke_start(idx):
    """Leave the icon's edge along the line toward the hub, so every spoke
    radiates out of its own node rather than starting in blank space."""
    cx, cy = SOURCES[idx]["c"]
    dx, dy = HUB[0] - cx, HUB[1] - cy
    d = math.hypot(dx, dy) or 1.0
    r = SRC_ICON_W / 2 + 8
    return (cx + dx / d * r, cy + dy / d * r)


def spoke(idx):
    """Polyline for source `idx` converging on the hub. Bendable."""
    return ov.path("flow.spoke.%d" % idx, [spoke_start(idx), HUB],
                   "spoke: " + SOURCES[idx]["label"])


def hub_to_ingest():
    return ov.path("flow.hub_to_ingest", [HUB, (BOX_INGEST[0], HUB[1])],
                   "hub -> Ingest UI")


def ingest_to_stac():
    """Ingest UI -> through the Airflow pinwheel -> STAC's left edge."""
    return ov.path("flow.ingest_to_stac",
                   [(BOX_INGEST[0] + BOX_INGEST[2], 450), (BOX_STAC[0], 450)],
                   "Ingest UI -> STAC")


def stac_return():
    """STAC -> Data Integration: the return half of the two-way link."""
    return ov.path("flow.stac_return",
                   [(BOX_STAC[0], 486),
                    (BOX_INTEGRATION[0] + BOX_INTEGRATION[2], 486)],
                   "STAC -> Data Integration")


def push_path():
    return ov.path("flow.push", [(PUSH_X, PUSH_FROM_Y), (PUSH_X, PUSH_TO_Y)],
                   "Push data")


def disasters_riser():
    """
    The Disasters AWS Bucket's own line up into the ingest hub.

    This is part of the OPENING picture: the bucket is already an ingest source
    alongside the six catalogs. The partner connection feeding *into* it is what
    gets added later.
    """
    return ov.path("flow.disasters_riser",
                   [(DISASTERS_C[0], DISASTERS_TOP - 2), HUB], "bucket -> hub")


def disasters_to_stac():
    """The full second story: green bucket -> hub -> ingest -> Airflow -> STAC."""
    # Compose from the real connectors rather than re-hardcoding their
    # endpoints: literal coordinates here would ignore any waypoint the editor
    # inserted, so a bent connector would animate along TWO different routes --
    # bent in stage 3, straight in stage 5.
    return (disasters_riser()[:-1] + hub_to_ingest()
            + ingest_to_stac())


# ---------------------------------------------------------------- bubbles ---
# Bubbles are AUTO-PLACED: rather than pinning each one to a hand-picked slot,
# the generator searches the canvas for the position closest to that stage's
# subject that collides with nothing. These are the regions it must avoid.
def occupied():
    return [BOX_INTEGRATION, BOX_PORTAL, BOX_EGIS, BOX_PROCESSING,
            BOX_STAC, BOX_FUNDED, BOX_COMMUNITY]


# Tried widest-first: a wide bubble wraps to fewer lines and fits the short
# top strip; a narrow one is the only thing that fits the bottom corridor.
BUBBLE_WIDTHS = (560, 460, 380)
BUBBLE_CLEARANCE = 14   # keep this much air between a bubble and any box
