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

WD = "/private/tmp/claude-502/-Users-klesinge-Downloads/44908f80-5123-4585-99a3-0a23e090fa1d/scratchpad/flowgif"
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
BOX_INTEGRATION = (40, 130, 550, 640)
BOX_PORTAL = (1010, 130, 550, 640)
BOX_EGIS = (680, 120, 240, 210)
BOX_PROCESSING = (680, 570, 240, 210)
BOX_STAC = (660, 350, 280, 200)
BOX_FUNDED = (40, 800, 550, 80)
BOX_COMMUNITY = (1010, 800, 550, 80)

# Symmetry checks these satisfy:
#   left margin  40 == right margin  1600-1560
#   STAC centre  (800, 450) == canvas centre
#   gap DI->STAC 680-590 == 90 == gap STAC->Portal 1010-920
#   EGIS top 120 is 330 above centre; Processing bottom 780 is 330 below centre

# ------------------------------------------------- data integration innards --
SRC_ICON_X = 55                # icon left edge
SRC_ICON_W = 46
SRC_LABEL_X = 111              # label left edge
SRC_SPOKE_X = 245              # every spoke leaves from this x, at its own cy
HUB = (318, 450)               # where all six spokes converge
BOX_INGEST = (338, 418, 162, 64)

PLUS_C = (516, 450)            # the "+" between Ingest UI and Airflow
AIRFLOW_C = (550, 450)         # inside the yellow box, per the source diagram
AIRFLOW_SIZE = 48
TINA_C = (975, 450)            # mirror position, right of STAC
TINA_SIZE = 58

# Seven source nodes on one evenly spaced rank, centred on y=450.
# kind: "cyl" = catalog cylinder, "bucket" = S3 bucket, "disasters" = the green one.
SOURCES = [
    {"label": "GIBS Catalog",         "cy": 235, "kind": "cyl"},
    {"label": "EGIS",                 "cy": 321, "kind": "cyl", "logo": "bJ.png"},
    {"label": "DAAC S3 Bucket",       "cy": 407, "kind": "bucket"},
    {"label": "External AWS Bucket",  "cy": 493, "kind": "bucket"},
    {"label": "CSDA AWS bucket",      "cy": 579, "kind": "bucket"},
    {"label": "External GIS Catalog", "cy": 665, "kind": "bucket"},
]

# The Disasters AWS Bucket sits ON the hub's vertical (x = HUB[0]) rather than
# in the source rank. That is what makes stage 4->5 a single uninterrupted
# straight run instead of a dogleg.
DISASTERS_C = (HUB[0], 712)
DISASTERS_ICON = 48
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
def label_width(s, size=14.5):
    """Rough Helvetica advance width -- good enough to place a line after text."""
    return len(s) * size * 0.52


def spoke_start(idx):
    """Each spoke leaves just past its own label, so the line grows out of the text."""
    src = SOURCES[idx]
    return (SRC_LABEL_X + label_width(src["label"]) + 12, src["cy"])


def spoke(idx):
    """Polyline for source `idx` converging on the hub."""
    return [spoke_start(idx), HUB]


def hub_to_ingest():
    return [HUB, (BOX_INGEST[0], 450)]


def ingest_to_stac():
    """Ingest UI -> through the Airflow pinwheel -> STAC's left edge."""
    return [(BOX_INGEST[0] + BOX_INGEST[2], 450), (BOX_STAC[0], 450)]


def stac_return():
    """STAC -> Data Integration: the return half of the two-way link."""
    return [(BOX_STAC[0], 486),
            (BOX_INTEGRATION[0] + BOX_INTEGRATION[2], 486)]


def push_path():
    return [(PUSH_X, PUSH_FROM_Y), (PUSH_X, PUSH_TO_Y)]


def disasters_riser():
    """
    The Disasters AWS Bucket's own line up into the ingest hub.

    This is part of the OPENING picture: the bucket is already an ingest source
    alongside the six catalogs. The partner connection feeding *into* it is what
    gets added later.
    """
    return [(DISASTERS_C[0], DISASTERS_TOP - 2), HUB]


def disasters_to_stac():
    """The full second story: green bucket -> hub -> ingest -> Airflow -> STAC."""
    return disasters_riser() + [
        (BOX_INGEST[0], 450), (BOX_INGEST[0] + BOX_INGEST[2], 450),
        (BOX_STAC[0], 450)]


# ---------------------------------------------------------------- bubbles ---
# Bubbles are AUTO-PLACED: rather than pinning each one to a hand-picked slot,
# the generator searches the canvas for the position closest to that stage's
# subject that collides with nothing. These are the regions it must avoid.
def occupied():
    return [BOX_INTEGRATION, BOX_PORTAL, BOX_EGIS, BOX_PROCESSING,
            BOX_STAC, BOX_FUNDED, BOX_COMMUNITY]


BUBBLE_W = 380          # narrow enough to fit both the top strip and the
                        # bottom-centre corridor between the two bottom boxes
BUBBLE_CLEARANCE = 14   # keep this much air between a bubble and any box
