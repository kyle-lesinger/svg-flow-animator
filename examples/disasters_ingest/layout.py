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

# ------------------------------------------------- earthdata GIS innards ----
# Three agency seals converge on one junction; the junction fans out over a
# short horizontal bus into the three ArcGIS tools. That is what the export
# draws, and the seals are pure SOURCES -- no connector from STAC may ever
# terminate on one.
#
# The two rows are handles rather than literals because the connectors have to
# live in the strip between them. At the original row positions that strip was
# 26 units tall, which is not room for one arrowhead let alone three; these
# defaults reproduce the export's vertical rhythm inside the same box.
EGIS_COL_DX = 68                       # column pitch, shared by both rows
EGIS_SEAL_SIZE = ov.scalar("egis.seal.size", 42, "EGIS agency seal size")
EGIS_TOOL_SIZE = ov.scalar("egis.tool.size", 34, "EGIS tool icon size")
EGIS_SEAL_Y = ov.scalar("egis.seal.y", BOX_EGIS[1] + 34, "EGIS seal row top")
EGIS_TOOL_Y = ov.scalar("egis.tool.y", BOX_EGIS[1] + 126, "EGIS tool row top")
EGIS_LABEL_Y = ov.scalar("egis.label.y", BOX_EGIS[1] + 172,
                         "EGIS tool label baseline")
EGIS_JUNCTION = ov.point("egis.junction",
                         (BOX_EGIS[0] + BOX_EGIS[2] / 2, BOX_EGIS[1] + 103),
                         "EGIS converge point")
EGIS_BUS_Y = ov.scalar("egis.bus_y", BOX_EGIS[1] + 108, "EGIS fan-out bus")

EGIS_SEALS = ("Census", "NOAA", "FEMA")            # left to right, as exported
EGIS_TOOLS = ("ArcGIS Desktop", "ArcGIS Online", "Service Workflows")


def egis_col_x(i):
    """Centre of EGIS column i. Both rows and the labels share it, so the
    converge and fan-out arrows land on the marks rather than near them."""
    return BOX_EGIS[0] + BOX_EGIS[2] / 2 + (i - 1) * EGIS_COL_DX


def egis_converge(i):
    """Agency seal i -> the shared junction."""
    return ov.path("egis.converge.%d" % i,
                   [(egis_col_x(i), EGIS_SEAL_Y + EGIS_SEAL_SIZE + 2),
                    EGIS_JUNCTION],
                   "%s -> junction" % EGIS_SEALS[i])


def egis_fanout(i):
    """The junction's bus, fanning down into tool i."""
    return ov.path("egis.fanout.%d" % i,
                   [(EGIS_JUNCTION[0], EGIS_BUS_Y),
                    (egis_col_x(i), EGIS_BUS_Y),
                    (egis_col_x(i), EGIS_TOOL_Y - 4)],
                   "junction -> %s" % EGIS_TOOLS[i])


# ------------------------------------------ data processing innards ----------
# The Disasters Hub and the Data Processing System are one combined capability,
# so they are drawn as one lockup rather than two unrelated marks: notebooks
# and the batch system that runs their algorithms are the same story.
DPS_C = ov.point("node.dps", (BOX_PROCESSING[0] + BOX_PROCESSING[2] / 2,
                              BOX_PROCESSING[1] + 66),
                 "Jupyter + DPS", size_key="node.dps.size")
DPS_SIZE = ov.scalar("node.dps.size", 40, "Jupyter + DPS size")


# ------------------------------------------------- data integration innards --
SRC_ICON_W = 46
# The three marks inside a bucket icon (circle, square, triangle) sit as a
# group in the barrel below the rim. Authored at h=44; gen_frames scales them
# with the icon, so this one number holds at every size the bucket is drawn at,
# including the 0.72 variant the Disasters bucket uses.
BUCKET_GLYPH_DY = ov.scalar("icon.bucket.glyph_dy", 8,
                            "bucket glyph group, below the rim")
SRC_LABEL_DY = 46              # label baseline below the icon centre.
                               # The icon is 46 tall, so this clears its
                               # bottom edge by 23px instead of 9.
SRC_LABEL_CHARS = 14           # wrap width for a stacked label.
                               # 14, not 15: "CSDA AWS Bucket" is exactly
                               # 15 and sat on one long line while its
                               # neighbours stacked. 14 breaks it after
                               # "AWS" and changes nothing else.
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
    # GIBS has no mark of its own -- it is an EOSDIS service presented under
    # NASA Earthdata branding -- so the meatball stands in for it. cx.png is
    # 120x100, and `meet` fits it by WIDTH into a square slot, so a size that
    # matches the EGIS globe by area has to be smaller than the globe's: 56
    # renders 56x47, against the globe's ~50x50 of ink inside its 66 slot.
    {"label": "GIBS Catalog", "kind": "cyl", "logo": "cx.png", "size": 56},
    # The globe PNG has whitespace padding baked in, so it reads smaller than
    # the drawn icons at the same nominal size. Give it a larger default.
    {"label": "EGIS", "kind": "cyl", "logo": "bJ.png", "size": 66},
    {"label": "DAAC S3 Bucket",       "kind": "bucket"},
    {"label": "External AWS Bucket",  "kind": "bucket"},
    {"label": "CSDA AWS Bucket",      "kind": "bucket"},
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
A_SHOT_HOME = FRAME_ASSETS + "/aX.jpg"     # portal home page, recovered from the export
                                           # like the other three shots below
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


# ------------------------------------------------ STAC's vertical exchanges --
# Earthdata GIS and Data Processing each exchange with STAC in BOTH directions.
# The block -> STAC leg is the MAIN one (animated, full weight); STAC -> block
# is the minor return, drawn thin and muted so it cannot compete.
#
# The export puts the downward lane on the left of each gap and the upward lane
# on the right, so the two pairs circulate consistently. Every leg meets the
# neighbour box on the ArcGIS column's vertical -- the tools' side of Earthdata
# GIS, never the agency seals, which are sources only.
#
# Portal Content is deliberately absent: TinaCMS is not two-way yet, so STAC ->
# Portal is a single one-way link.
STAC_PAIR_DX = ov.scalar("stac.pair_dx", 15,
                         "half-gap between the two lanes of a STAC exchange")


def egis_to_stac():
    """MAIN: the three ArcGIS tools push catalogued data up into STAC."""
    x = egis_col_x(1) - STAC_PAIR_DX
    return ov.path("flow.egis_to_stac",
                   [(x, BOX_EGIS[1] + BOX_EGIS[3]), (x, BOX_STAC[1])],
                   "Earthdata GIS -> STAC")


def stac_to_egis():
    """MINOR: STAC's return leg to those same three tools."""
    x = egis_col_x(1) + STAC_PAIR_DX
    return ov.path("flow.stac_to_egis",
                   [(x, BOX_STAC[1]), (x, BOX_EGIS[1] + BOX_EGIS[3])],
                   "STAC -> Earthdata GIS (minor)")


def processing_to_stac():
    """MAIN: Data Processing publishes its products back into STAC."""
    x = BOX_PROCESSING[0] + BOX_PROCESSING[2] / 2 + STAC_PAIR_DX
    return ov.path("flow.processing_to_stac",
                   [(x, BOX_PROCESSING[1]), (x, BOX_STAC[1] + BOX_STAC[3])],
                   "Data Processing -> STAC")


def stac_to_processing():
    """MINOR: STAC's return leg down into Data Processing."""
    x = BOX_PROCESSING[0] + BOX_PROCESSING[2] / 2 - STAC_PAIR_DX
    return ov.path("flow.stac_to_processing",
                   [(x, BOX_STAC[1] + BOX_STAC[3]), (x, BOX_PROCESSING[1])],
                   "STAC -> Data Processing (minor)")


def stac_to_portal():
    """One way only. Nothing comes back from Portal Content."""
    y = BOX_STAC[1] + BOX_STAC[3] / 2
    return ov.path("flow.stac_to_portal",
                   [(BOX_STAC[0] + BOX_STAC[2], y), (BOX_PORTAL[0], y)],
                   "STAC -> Portal Content")


# ---------------------------------------------------------- portal content --
PORTAL_SHOTS = ("Home Page", "Event / Story Page",
                "Data Visualization", "Training Page")
PORTAL_SHOT_W, PORTAL_SHOT_H = 240, 215
# The top row is captioned ABOVE its tiles, so the first row has to clear the
# block's title by the caption's height as well as its own gap. At the old 55
# the "Home Page" caption's cap-height started 5px under the title's baseline
# and the two read as one smudge; 80 puts ~24px of air between them. The bottom
# row and its captions ride down with it and still clear the block's floor.
PORTAL_ROW_TOP = ov.scalar("portal.row_top", 80,
                           "Portal Content first tile row, below the title")
PORTAL_ROW_DY = 285            # row pitch


def portal_shot(i):
    """Screenshot tile i (0..3), row-major -- the same order as the export."""
    return ov.rect("portal.shot.%d" % i,
                   (BOX_PORTAL[0] + 30 + (i % 2) * 265,
                    BOX_PORTAL[1] + PORTAL_ROW_TOP + (i // 2) * PORTAL_ROW_DY,
                    PORTAL_SHOT_W, PORTAL_SHOT_H),
                   PORTAL_SHOTS[i])


def portal_fan(i):
    """
    TinaCMS -> tile i: the four-way fan the export draws inside Portal Content.

    Each leg aims at the point on the tile CLOSEST to the llama, which is what
    keeps the upper-right leg clear of the upper-left tile -- targeting a tile's
    centre or its left edge would drive it straight through the neighbour.
    """
    rx, ry, rw, rh = portal_shot(i)
    tx, ty = TINA_C
    ex = max(rx, min(rx + rw, tx))
    ey = max(ry, min(ry + rh, ty))
    dx, dy = ex - tx, ey - ty
    d = math.hypot(dx, dy) or 1.0
    gap = 8                                   # stop short of the frame
    return ov.path("flow.portal_fan.%d" % i,
                   [(tx + dx / d * TINA_SIZE * 0.42, ty + dy / d * TINA_SIZE * 0.42),
                    (ex - dx / d * gap, ey - dy / d * gap)],
                   "TinaCMS -> " + PORTAL_SHOTS[i])


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


# --------------------------------------------------------------- sections ---
# A section is one chapter of the diagram, rendered as its own GIF.
#
# Every section GIF shows the WHOLE canvas. A section is not a crop -- it is a
# choice about what MOVES, made in gen_frames.SECTION_SCOPE, while the rest of
# the ecosystem stays visible and still. Per-section frames were tried and
# removed: cropping to a block cut it out of the system it belongs to, which is
# the one thing the diagram exists to show.
#
# So there is no geometry here. Nothing about a section is tunable by hand,
# because nothing about it is positional.
