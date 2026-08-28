#!/usr/bin/env python3
"""
Emit one standalone SVG per animation frame.

Each frame is fully self-contained except for <image> hrefs, which point at the
sprite PNGs on disk -- librsvg resolves local paths, so we avoid base64-inlining
~1.6MB of logos into all 288 frames.

Stdlib only (no Pillow on this machine); all raster work is shelled out to
ImageMagick/ffmpeg by build.sh.
"""
import math
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
# The repo root goes AFTER _HERE on purpose: this example keeps its own
# overrides.py and rough.py, and they must keep shadowing the package's.
sys.path.insert(1, os.path.abspath(os.path.join(_HERE, "..", "..")))
import layout as L
import overrides as ov
import rough as R
from style import S
from svg_flow_animator.geometry import fit_viewbox

FPS = 15
FONT_BUMP = 4                   # every label four points larger, for projection
FADE = 7                        # frames to fade a bubble in / out
MIN_BUBBLE_SEC = 7.0            # every caption must be readable this long
MIN_BUBBLE_FRAMES = int(round(MIN_BUBBLE_SEC * FPS))
GAP = 12                        # quiet frames between one caption and the next

# The five ways in, left to right as the block draws them. Defined ABOVE the
# stage table so each beat can anchor its caption on the mark it is naming --
# one shared anchor pointed every caption at the same spot regardless of which
# channel it described.
COMMUNITY_ITEMS = ((L.A_LISTSERV, "list-serv"), (L.A_MYST, "MyST Docs"),
                   (L.A_GITHUB, "Github"), (L.A_GRAFANA, "Grafana"),
                   (L.A_NEWSLETTER, "Newsletter"))


def community_item_c(i):
    """Centre of channel `i`'s mark."""
    x, y, _w, _h = L.BOX_COMMUNITY
    return (x + 190 + i * 70 + 29, y + 29)


# (key, motion frames, caption, anchor). The caption's HOLD is derived so that
# motion + hold always clears MIN_BUBBLE_FRAMES, and stages are laid end to end
# so two captions are never competing for the reader at once.
_SPEC = [
    ("sources", 60,
     "Data arrives from many different locations \u2014 GIBS and EGIS catalogs, "
     "DAAC and CSDA buckets, external AWS and GIS sources, and the "
     "NASA Disasters AWS bucket.",
     (150, 450)),
    ("ingest", 30,
     "Every source converges on the VEDA Ingest UI, a single front door for "
     "getting data into the system.",
     (419, 450)),
    ("airflow", 45,
     "Airflow SM2A orchestrates the ingest and writes the resulting records "
     "into the STAC catalog.",
     (800, 450)),
    ("push", 40,
     "Separately, funded projects and partners push their own data products "
     "straight into the NASA Disasters AWS bucket.",
     (330, 756)),
    ("tostac", 50,
     "That bucket feeds the same ingest path \u2014 so partner data lands in "
     "STAC alongside everything else. One catalog for all of it.",
     (800, 450)),
    # --- the Earthdata GIS chapter. Three beats: agency data arrives, the
    # ArcGIS environments read it, and STAC feeds new service workflows.
    ("egis_agencies", 45,
     "Earthdata GIS draws from the federal agencies \u2014 NOAA, FEMA and the "
     "Department of Commerce.",
     (800, 150)),
    ("egis_tools", 45,
     "That data is read into the ArcGIS environments: ArcGIS Desktop, "
     "ArcGIS Online, and Service Workflows.",
     (800, 240)),
    ("egis_stac", 45,
     "STAC integrates with the same environments, so the catalog can drive "
     "new service workflows of its own.",
     (800, 300)),
    # --- the Data Processing chapter. Produced in the hub, written to STAC,
    # and read back out again -- the loop is the point of this one.
    ("dp_produce", 45,
     "Data is produced in the Jupyter Disasters Hub, alongside the Data "
     "Processing System that runs its algorithms.",
     (800, 700)),
    ("dp_tostac", 45,
     "What the hub and DPS produce is written into the STAC catalog.",
     (800, 600)),
    ("dp_readback", 45,
     "And STAC can be read straight back into the hub — easy processing and "
     "data retrieval from the same catalog.",
     (800, 600)),
    # --- the Portal Content chapter. STAC -> TinaCMS -> the four pages. One
    # way throughout: TinaCMS does not write back to the catalog.
    ("portal_cms", 45,
     "STAC data flows out to TinaCMS, the content management system behind "
     "the public site.",
     (975, 450)),
    ("portal_pages", 50,
     "From there it reaches the portal itself — the home page, event and "
     "story pages, the visualisation tool and the training pages.",
     (1285, 450)),
    # --- the Community & Engagement chapter. No data moves here, so the beats
    # highlight the channels themselves rather than animating a path.
    ("comm_listserv", 35,
     "list-serv is the mailing list — announcements straight to your inbox.",
     community_item_c(0)),
    ("comm_myst", 35,
     "MyST Docs is the documentation hub.",
     community_item_c(1)),
    ("comm_github", 35,
     "GitHub hosts the discussion board, where questions and proposals are "
     "worked through in the open.",
     community_item_c(2)),
    ("comm_grafana", 35,
     "Grafana tracks the metrics.",
     community_item_c(3)),
    ("comm_news", 35,
     "And the newsletter is NASA Disasters' own — the programme's direct "
     "line to its community.",
     community_item_c(4)),
]


def _build_stages(first_start=8):
    stages, t = [], first_start
    for key, dur, bubble, anchor in _SPEC:
        hold = max(0, MIN_BUBBLE_FRAMES - dur)
        stages.append(dict(key=key, start=t, dur=dur, hold=hold,
                           bubble=bubble, anchor=anchor))
        t += dur + hold + FADE + GAP
    return stages, t + 18      # a beat of full-picture hold at the end


STAGES, TOTAL = _build_stages()

# Some of the diagram is AMBIENT rather than staged: it has no caption of its
# own. The Portal Content fan-out draws itself in once STAC exists (the Airflow
# stage, index 2) and then runs for the rest of the film -- that is how it
# animates without adding another caption to the queue, and why it is absent
# from frame 0, which no guard should be pointed at.
AMBIENT_START = STAGES[2]["start"]
AMBIENT_RAMP = 34               # frames one ambient link takes to draw itself in
PORTAL_FAN_DELAY = 20           # the quiet fan-out waits for the STAC pairs
PORTAL_FAN_STEP = 9             # ...and its four legs arrive one at a time
PORTAL_CYCLE = 26               # frames one tile spends being gently highlighted

# STAC's two vertical exchanges are STRUCTURE, not narration: they are drawn
# from frame 0 and never appear or disappear. What they do have is a moment
# they are allowed to start MOVING, and it is not during the Airflow caption.
# That caption is the one about this part of the diagram, and those two links
# were drawing themselves in and running packets underneath the whole of it.
# They hold still until it has faded out, then the packets simply start.
_AIRFLOW = STAGES[2]
EXCHANGE_MOTION_START = (_AIRFLOW["start"] + _AIRFLOW["dur"]
                         + _AIRFLOW["hold"] + FADE + 1)

DASH_RATE = 7.0                 # packet travel, in user units per frame


HOP_PERIOD = 60                 # 4 seconds at 15fps
HOP_RISE = 14                   # frames the hop itself lasts
HOP_HEIGHT = 7                  # user units at the top of the arc


def hop_dy(f):
    """
    Vertical offset for the TinaCMS llama: a small bounce every HOP_PERIOD.

    Negative is up. The arc is a half sine over HOP_RISE frames and flat for
    the rest of the period, so the llama sits still between hops instead of
    drifting continuously -- a constant wobble reads as a rendering fault,
    a discrete hop reads as a character.
    """
    t = f % HOP_PERIOD
    if t >= HOP_RISE:
        return 0.0
    return -HOP_HEIGHT * math.sin(math.pi * t / float(HOP_RISE))


def ambient(f, delay=0):
    """Draw-in progress 0..1 for an ambient link; -1 before it starts."""
    t = f - AMBIENT_START - delay
    return -1.0 if t < 0 else min(1.0, t / float(AMBIENT_RAMP))


# ---------------------------------------------------------------- sections ---
# A "section" is one labelled box of the diagram, rendered as its own GIF.
#
# The list is DERIVED from the handle registry rather than written out here, for
# the same reason the editor is: a hand-maintained list drifts the moment
# someone adds a box. Importing `layout` populates ov.HANDLES, so every
# `ov.rect("box.*", ...)` is automatically a buildable section.
SECTION_PREFIX = "box."

# Boxes that are NOT buildable sections. They are still drawn -- they are part
# of the diagram -- they simply have no chapter of their own: the Ingest UI and
# STAC are told inside the Data Integration chapter, and Funded Projects inside
# the same run of the story.
SECTION_SKIP = frozenset(("ingest", "stac", "funded"))


def sections():
    """[(key, label, rect)] for every box in the registry, in declaration order."""
    return [(k[len(SECTION_PREFIX):], h["label"], h["value"])
            for k, h in ov.HANDLES.items()
            if h["kind"] == "rect" and k.startswith(SECTION_PREFIX)
            and k[len(SECTION_PREFIX):] not in SECTION_SKIP]


def section_view(name):
    """
    The viewBox for one section: the WHOLE canvas, for every section.

    A section GIF exists to showcase the ecosystem, so it must show all of it.
    Sections differ by what MOVES, not by what is visible -- see SECTION_SCOPE.
    Cropping to the block a section is about was tried and abandoned: it cut the
    section out of the system it belongs to, which is the one thing the diagram
    is for. The name is still validated, so a typo fails loudly instead of
    silently building the wrong thing.
    """
    if name not in {k for k, _, _ in sections()}:
        raise KeyError("no such section: %s (have: %s)"
                       % (name, ", ".join(k for k, _, _ in sections())))
    return (0, 0, L.W, L.H)


# Every section rasterises at most this large, and its GIF is that scaled down
# -- the same 1600x900 -> 1280x720 the full diagram uses, but a section keeps
# its own shape inside those bounds instead of being letterboxed into 16:9.
RENDER_MAX = (L.W, L.H)
GIF_SCALE = 0.8


def _even(v):
    """ffmpeg is happier with even dimensions, and a GIF loses nothing to it."""
    return max(2, int(round(v / 2.0)) * 2)


def section_size(name=None):
    """(render_w, render_h, gif_w, gif_h) for a section, or the full diagram."""
    vw, vh = (L.W, L.H) if name is None else section_view(name)[2:]
    s = min(RENDER_MAX[0] / float(vw), RENDER_MAX[1] / float(vh))
    rw, rh = _even(vw * s), _even(vh * s)
    return rw, rh, _even(rw * GIF_SCALE), _even(rh * GIF_SCALE)


# ------------------------------------------------------------ content scope --
# A section's viewport decides what the reader SEES. Its scope decides what the
# reader sees MOVE, and cropping alone cannot do that job: the Data Integration
# chapter reaches as far as STAC, so the STAC exchanges and the TinaCMS fan-out
# fall inside its frame and animate there -- motion belonging to a later
# chapter, competing with the one being told.
#
# Out-of-scope content is not deleted, it is FROZEN: drawn exactly as the full
# render draws it, evaluated at one fixed instant. Deleting it would leave
# holes in a diagram whose whole point is that everything connects. Freezing
# leaves the picture whole and simply still.
#
# A section with no entry here animates everything, as the full render does.
CONTENT_GROUPS = ("integration", "stac", "funded", "egis", "processing",
                  "portal", "community")

# Which group each staged flow belongs to.
STAGE_GROUP = {"sources": "integration", "ingest": "integration",
               "airflow": "stac", "push": "funded", "tostac": "stac",
               "egis_agencies": "egis", "egis_tools": "egis",
               "egis_stac": "egis",
               "dp_produce": "processing", "dp_tostac": "processing",
               "dp_readback": "processing",
               "portal_cms": "portal", "portal_pages": "portal",
               "comm_listserv": "community", "comm_myst": "community",
               "comm_github": "community", "comm_grafana": "community",
               "comm_news": "community"}

# Indices of the Earthdata GIS beats, derived rather than written down: a
# hardcoded index silently points at the wrong stage the moment _SPEC is
# reordered, and nothing downstream would complain.
EGIS_STAGE_IDX = [i for i, s in enumerate(STAGES)
                  if STAGE_GROUP.get(s["key"]) == "egis"]
DP_STAGE_IDX = [i for i, s in enumerate(STAGES)
                if STAGE_GROUP.get(s["key"]) == "processing"]
PORTAL_STAGE_IDX = [i for i, s in enumerate(STAGES)
                    if STAGE_GROUP.get(s["key"]) == "portal"]
COMMUNITY_STAGE_IDX = [i for i, s in enumerate(STAGES)
                       if STAGE_GROUP.get(s["key"]) == "community"]

# A section GIF covers ITS OWN CHAPTER, not the whole film. Rendering the full
# timeline for a section meant the Earthdata GIS GIF opened with 42 seconds of
# a completely still picture before its chapter began -- it looked broken, and
# a viewer reasonably concluded nothing was animating.
SPAN_LEAD_IN = 12               # a beat of settled diagram before the motion
SPAN_TAIL = 20                  # ...and after it, so the last caption can land
SPAN_STILL = 45                 # length of a section that never animates


def section_span(name):
    """
    Inclusive (first, last) frames a section's GIF should cover.

    A section with no scope is the whole film. A section whose scope names no
    staged chapter -- Community, which has no automated data path -- gets a
    short still clip rather than 68 seconds of the same frame.
    """
    scope = SECTION_SCOPE.get(name)
    if scope is None:
        return 0, TOTAL - 1
    idx = [i for i, s in enumerate(STAGES) if STAGE_GROUP.get(s["key"]) in scope]
    if not idx:
        return 0, min(TOTAL - 1, SPAN_STILL)
    first = STAGES[idx[0]]["start"]
    last = STAGES[idx[-1]]
    end = last["start"] + last["dur"] + last["hold"] + FADE
    return max(0, first - SPAN_LEAD_IN), min(TOTAL - 1, end + SPAN_TAIL)


# Every flow that touches STAC is drawn at one of two weights, never an ad-hoc
# number: the MAIN legs all match each other, and the minor returns all match
# each other. Mixed widths on the same hub read as significance the diagram
# does not mean -- a 4.0 leg next to a 4.5 leg looks like a claim about volume.
STAC_MAIN_W = 4.5
STAC_MINOR_W = 2.0

# Every section shows the whole ecosystem, so scope is the ONLY thing that
# distinguishes one section GIF from another. Each entry names the chapter that
# moves; everything else is frozen at its settled state, present but still.
SECTION_SCOPE = {
    # The journey's first chapter is three blocks and the flows between them:
    # Data Integration, STAC, and the partners pushing into the bucket.
    # Earthdata GIS, Data Processing, TinaCMS and Portal Content are context
    # here and must hold still.
    "integration": ("integration", "stac", "funded"),
    # The VEDA Ingest UI is the front door *inside* Data Integration, so its
    # chapter is that group -- the sources converging and the ingest itself.
    "ingest": ("integration",),
    # Partners pushing into the Disasters bucket. The bucket is drawn inside
    # Data Integration, but the push is its own beat and its own group.
    "funded": ("funded",),
    # The hub. Its own chapter is what is written INTO it -- the Airflow
    # ingest and the partner data arriving by the same path.
    "stac": ("stac",),
    # The two vertical exchanges each belong to the block they serve, not to
    # STAC, so a chapter about one of them moves alone.
    "egis": ("egis",),
    "processing": ("processing",),
    "portal": ("portal",),
    # Community & Engagement has NO automated data path -- the diagram says so
    # in as many words. Its group therefore carries no flows and no stages:
    # naming it here makes the block the section's SUBJECT (drawn bright) while
    # still animating nothing. That is not an oversight, and it must not be
    # "fixed" by giving it something to move.
    "community": ("community",),
}


def emphasis(scope):
    """
    Which groups are drawn at full strength; the rest recede to context weight.

    A section is ABOUT something, and the reader needs to see which part that
    is -- dimming was previously a fixed property of a few blocks, so a section
    about Earthdata GIS drew its own subject muted while unrelated blocks
    stayed bright.

    The STAC BOX is always bright: it is the hub every chapter connects to, so
    dimming it would leave each section's flows arriving at a grey box. Its
    FLOWS are not -- see flow_emphasis. Exempting the group wholesale left the
    entire hub-to-Airflow-to-STAC run at full strength in every section, which
    is most of the width of the diagram.
    """
    if scope is None:
        return set(CONTENT_GROUPS)          # the full film dims nothing
    return set(scope) | {"stac"}


def flow_emphasis(scope):
    """
    Like `emphasis`, but for the moving parts, with no STAC exemption.

    A flow is a line across the canvas; the box is a destination. Keeping the
    box visible costs nothing, and keeping its flows bright costs the section
    the reader's attention.
    """
    if scope is None:
        return set(CONTENT_GROUPS)
    return set(scope)

# The frame frozen content is evaluated at: the last one, where every flow is
# drawn and every stage has finished, so a frozen group shows the settled
# diagram rather than a half-drawn one.
FREEZE_FRAME = TOTAL - 1

# A misspelt group name is not an error anywhere downstream -- it simply never
# matches, and the section silently freezes the very thing it meant to animate.
# That is a complete-looking GIF that is wrong, so refuse it at import.
for _key, _groups in SECTION_SCOPE.items():
    _unknown = [g for g in _groups if g not in CONTENT_GROUPS]
    if _unknown:
        raise ValueError("section %r scopes unknown content group(s): %s"
                         % (_key, ", ".join(_unknown)))



# ------------------------------------------------------------------ utils ---
def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def smooth(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def seg_lengths(pts):
    return [math.hypot(pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1])
            for i in range(len(pts) - 1)]


def path_len(pts):
    return sum(seg_lengths(pts))


def point_at(pts, t):
    """Point a fraction t along a polyline."""
    segs = seg_lengths(pts)
    total = sum(segs)
    if total <= 0:
        return pts[0]
    d = max(0.0, min(1.0, t)) * total
    for i, s in enumerate(segs):
        if d <= s or i == len(segs) - 1:
            f = d / s if s else 0
            x0, y0 = pts[i]
            x1, y1 = pts[i + 1]
            return (x0 + (x1 - x0) * f, y0 + (y1 - y0) * f)
        d -= s
    return pts[-1]


def poly_d(pts):
    return "M " + " L ".join(f"{x:.2f},{y:.2f}" for x, y in pts)


def wrap(text, width_chars):
    words, lines, cur = text.split(), [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        if len(trial) <= width_chars:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def text(x, y, s, size=13, fill=None, anchor="start", weight="normal", opacity=1.0):
    return S.text(x, y, s, size + FONT_BUMP, fill or S.ink, anchor, weight, opacity)


def img(href, x, y, w, h, opacity=1.0, preserve="xMidYMid meet", frame=True):
    return S.img(href, x, y, w, h, opacity, preserve, frame)


def box(x, y, w, h, fill, stroke=None, rx=8, opacity=1.0, sw=2, dash=None):
    return S.box(x, y, w, h, fill, stroke or S.edge, rx, opacity, sw, dash=dash)


# ------------------------------------------------------------------ icons ---
def cylinder(cx, cy, w=46, h=46, stroke="#6f7681"):
    """Barrel + top ellipse. The barrel's rounded base is sampled as a polyline
    because SVG arc commands have no sketchy equivalent."""
    x, y = cx - w / 2, cy - h / 2
    ry = h * 0.17
    arc = [(cx + (w / 2) * math.cos(a), y + h - ry + ry * math.sin(a))
           for a in [math.pi * i / 10 for i in range(11)]]
    body = [(x, y + ry)] + arc[::-1] + [(x + w, y + ry)]
    return (S.poly(body, stroke, sw=2, fill="#ffffff", key=("cylb", cx, cy))
            + S.ellipse(cx, y + ry, w / 2, ry, fill="#ffffff", stroke=stroke,
                        sw=2, key=("cylt", cx, cy)))


def dps_icon(cx, cy, w=38, h=38, stroke="#3f6ea8", accent="#3f6ea8", opacity=1.0):
    """
    The Data Processing System: a processor die with pins and work in progress.

    Drawn rather than extracted, because DPS has no logo -- it is a subsystem,
    not a product, and there is no mark to recover from the export or anywhere
    else. Drawing it through S.* also keeps it hand-drawn in sketch mode, which
    a raster would not be.
    """
    x, y = cx - w / 2, cy - h / 2
    inset = w * 0.17
    pin = w * 0.13
    out = [S.box(x + inset, y + inset, w - 2 * inset, h - 2 * inset, "#ffffff",
                 stroke=stroke, rx=3, sw=1.8, opacity=opacity,
                 key=("dpsbody", cx, cy))]
    # Pins on all four sides -- what makes it read as a processor rather than
    # just another box in a diagram already full of boxes.
    for i in (0.3, 0.5, 0.7):
        out.append(S.poly([(x + w * i, y), (x + w * i, y + inset)], accent,
                          sw=1.6, opacity=opacity, key=("dpspt", cx, cy, i)))
        out.append(S.poly([(x + w * i, y + h - inset), (x + w * i, y + h)],
                          accent, sw=1.6, opacity=opacity,
                          key=("dpspb", cx, cy, i)))
        out.append(S.poly([(x, y + h * i), (x + inset, y + h * i)], accent,
                          sw=1.6, opacity=opacity, key=("dpspl", cx, cy, i)))
        out.append(S.poly([(x + w - inset, y + h * i), (x + w, y + h * i)],
                          accent, sw=1.6, opacity=opacity,
                          key=("dpspr", cx, cy, i)))
    # Two bars inside: a job running.
    for j, frac in enumerate((0.42, 0.58)):
        out.append(S.poly([(x + inset + pin, y + h * frac),
                           (x + w - inset - pin * (1 + j), y + h * frac)],
                          accent, sw=2.0, opacity=opacity * 0.85,
                          key=("dpsbar", cx, cy, j)))
    return "".join(out)


def jupyter_dps(cx, cy, size=34, opacity=1.0):
    """
    The Jupyter mark and the DPS processor, side by side as one lockup.

    They are a combined capability -- notebooks and the batch system that runs
    their algorithms -- so they are drawn joined by a "+" rather than as two
    marks that happen to be adjacent.
    """
    gap = size * 0.42
    # The Jupyter PNG is 512x585 -- TALLER than wide -- so a wide slot under
    # `meet` fits it by height and leaves it narrower than the chip beside it.
    # Give it a slot of its own aspect at the chip's height instead.
    jh = size
    jw = size * 0.88
    jx = cx - gap / 2 - jw
    dx = cx + gap / 2 + size / 2
    out = [img(L.A_JUPYTER, jx, cy - jh / 2, jw, jh, opacity=opacity,
               frame=False),
           text(cx, cy + 4, "+", 12, anchor="middle", opacity=opacity * 0.7),
           dps_icon(dx, cy, size, size, opacity=opacity)]
    # No caption of its own: the three lines beneath this slot already name
    # both halves, and a second label would just repeat them.
    return "".join(out)


def bucket(cx, cy, w=46, h=44, stroke="#6f7681", fill="#ffffff", accent="#6f7681"):
    """
    A tapered barrel with a rim, carrying three accent marks.

    Everything here is proportional to the icon, including the rim and the
    marks. It used to mix the two: the barrel scaled with w/h but the rim
    offset, the rim radius and all three marks were absolute, so the 0.72
    variant `disasters_bucket()` draws had its triangle sitting on top of the
    rim with no offset able to fix it -- there was no gap left to move it into.

    The marks are placed as ONE group, `L.BUCKET_GLYPH_DY` below where they
    were authored, so they read as a set and stay clear of both the rim above
    them and the taper closing in beside them.
    """
    x, y = cx - w / 2, cy - h / 2
    g = h / 44.0                       # everything below was authored at h=44
    inset = w * 0.13
    rim, ry = 6 * g, 5 * g
    dy = L.BUCKET_GLYPH_DY * g

    def mark(pts):
        return [(cx + px * g, cy + py * g + dy) for px, py in pts]

    return (
        S.poly([(x, y + rim), (x + w, y + rim),
                (x + w - inset, y + h), (x + inset, y + h)],
               stroke, sw=2, fill=fill, closed=True, key=("bukb", cx, cy))
        + S.ellipse(cx, y + rim, w / 2, ry, fill=fill, stroke=stroke, sw=2,
                    key=("bukt", cx, cy))
        + S.circle(cx + 5 * g, cy + 4 * g + dy, 4 * g, stroke=accent, sw=1.6,
                   opacity=0.85, key=("bukc", cx, cy))
        + S.poly(mark([(-11, 0), (-3, 0), (-3, 8), (-11, 8)]),
                 accent, sw=1.6, closed=True, opacity=0.85, key=("buks", cx, cy))
        + S.poly(mark([(-9, -8), (-4, -15), (1, -8)]),
                 accent, sw=1.6, closed=True, opacity=0.85, key=("bukt2", cx, cy)))


def disasters_bucket(cx, cy, w=48, h=46):
    x, y = cx - w / 2, cy - h / 2
    return (S.box(x, y, w, h, "#2e7d32", stroke="#2e7d32", rx=4, sw=1.5,
                  key=("dbuk", cx, cy))
            + bucket(cx, cy, w=w * 0.72, h=h * 0.72, stroke="#ffffff",
                     fill="none", accent="#ffffff"))


def source_icon(src, cx, cy, size=None):
    """Size is per-node, so a mark that reads small at the shared default
    (the EGIS globe, say) can be scaled up on its own."""
    sz = float(size or L.SRC_ICON_W)
    if src["kind"] == "disasters":
        return disasters_bucket(cx, cy, w=sz, h=sz - 2)
    if src.get("logo"):
        return img(L.FRAME_ASSETS + "/" + src["logo"],
                   cx - sz / 2, cy - sz / 2, sz, sz)
    if src["kind"] == "cyl":
        return cylinder(cx, cy, w=sz, h=sz)
    return bucket(cx, cy, w=sz, h=sz - 2)


def airflow_group(cx, cy, size, angle=0.0):
    """Inline the four extracted blade paths so the spin stays vector."""
    vx, vy, vw, vh = L.AIRFLOW_SRC_VIEWBOX
    s = size / vw
    return (f'<g transform="translate({cx:.2f},{cy:.2f}) rotate({angle:.2f}) '
            f'scale({s:.5f}) translate({-vx - vw/2:.2f},{-vy - vh/2:.2f})">'
            f'{AIRFLOW_BLADES}</g>')


def _load_airflow_blades():
    raw = open(L.A_AIRFLOW, encoding="utf-8").read()
    inner = raw.split(">", 1)[1].rsplit("</svg>", 1)[0]
    return inner.strip()


AIRFLOW_BLADES = _load_airflow_blades()


# ------------------------------------------------------------ connectors ---
def arrow_head(pts, color, size=10, opacity=1.0, key=None):
    """
    A filled triangle on the last segment of `pts`.

    Drawn as a closed S.poly rather than a `marker-end`, because a marker is a
    flat primitive that sketch mode cannot jitter -- the connector would wobble
    and its head would not.
    """
    (x1, y1), (x2, y2) = pts[-2], pts[-1]
    a = math.atan2(y2 - y1, x2 - x1)
    if x1 == x2 and y1 == y2:          # a degenerate elbow has no direction
        return ""
    wing = 0.42
    tri = [(x2, y2),
           (x2 - size * math.cos(a - wing), y2 - size * math.sin(a - wing)),
           (x2 - size * math.cos(a + wing), y2 - size * math.sin(a + wing))]
    return S.poly(tri, color, sw=1, fill=color, closed=True, opacity=opacity,
                  key=key or ("head", round(x2, 2), round(y2, 2), round(a, 3)))


def link(pts, color=None, width=1.8, opacity=1.0, progress=1.0, head=True,
         key=None):
    """
    A connector drawn through the style backend, optionally only part drawn.

    `progress` < 1 reveals it by dasharray -- the same trick flow_path() uses,
    minus the travelling packets. That is what lets secondary structure animate
    itself in without competing with the main flows for the reader's eye. The
    arrowhead appears only once the line has actually arrived.
    """
    color = color or S.edge
    p = max(0.0, min(1.0, progress))
    out = []
    for d, total in S.stroke_layers(pts, key=key):
        shown = total * smooth(p)
        out.append(f'<path d="{d}" stroke="{color}" stroke-width="{width}" '
                   f'fill="none" stroke-linecap="round" opacity="{opacity:.3f}" '
                   f'stroke-dasharray="{shown:.2f} {total:.2f}"/>')
    if head and p >= 1.0:
        out.append(arrow_head(pts, color, size=6 + width * 2.4, opacity=opacity))
    return "\n".join(out)


# --------------------------------------------------------- static scenery ---
def _dim(markup, group, bright):
    """
    Recede a block that draws at full strength when it is not the subject.

    Wrapping in a group is what keeps this honest: these blocks compose their
    own opacities internally, and multiplying every one of them by a factor
    would compound with the ones already muted.
    """
    if group in bright:
        return markup
    return '<g opacity="%.2f">%s</g>' % (L.CONTEXT_OPACITY, markup)


def _op(group, bright):
    """Full strength if this block is what the section is about, else muted."""
    return 1.0 if group in bright else L.CONTEXT_OPACITY


def context_boxes(bright=frozenset(CONTENT_GROUPS), tina_dy=0.0):
    """
    The blocks that carry no staged flow of their own.

    Each is drawn at full strength or at context weight depending on whether
    the section being told is about it -- so Earthdata GIS is bright in its own
    chapter and muted in everyone else's.
    """
    out = []

    # ---- Earthdata GIS (above STAC)
    o = _op("egis", bright)
    x, y, w, h = L.BOX_EGIS
    out.append(box(x, y, w, h, L.FILL_EGIS, opacity=o))
    out.append(text(x + w / 2, y + 24, "Earthdata GIS", 15, anchor="middle",
                    weight="bold", opacity=o))
    # Seals left to right in the export's order. They are pure sources: the
    # arrows below all leave them, and nothing from STAC terminates on one.
    sz = L.EGIS_SEAL_SIZE
    for i, a in enumerate((L.A_CENSUS, L.A_NOAA, L.A_FEMA)):
        out.append(img(a, L.egis_col_x(i) - sz / 2, L.EGIS_SEAL_Y, sz, sz,
                       opacity=o))
    tz = L.EGIS_TOOL_SIZE
    for i, a in enumerate((L.A_ARCGIS_DESKTOP, L.A_ARCGIS_ONLINE, L.A_NOTEBOOK)):
        cx = L.egis_col_x(i)
        out.append(img(a, cx - tz / 2, L.EGIS_TOOL_Y, tz, tz, opacity=o))
        for j, line in enumerate(wrap(L.EGIS_TOOLS[i], 9)):
            out.append(text(cx, L.EGIS_LABEL_Y + j * 12, line, 9.5,
                            anchor="middle", opacity=o))

    # Three seals converge on one junction, which fans out over a short bus
    # into the three tools. The converge legs share a SINGLE arrowhead at the
    # junction, as the export draws it -- three stacked heads on one point just
    # read as a blob.
    for i in range(3):
        out.append(link(L.egis_converge(i), color=S.edge, width=1.8, opacity=o,
                        head=False, key=("egis.in", i)))
    jx, jy = L.EGIS_JUNCTION
    out.append(arrow_head([(jx, jy - 12), (jx, jy)], S.edge, size=9, opacity=o,
                          key=("egis.junction",)))
    for i in range(3):
        out.append(link(L.egis_fanout(i), color=S.edge, width=1.8, opacity=o,
                        key=("egis.out", i)))

    # ---- Data Processing (below STAC)
    o = _op("processing", bright)
    x, y, w, h = L.BOX_PROCESSING
    out.append(box(x, y, w, h, L.FILL_PROCESSING, opacity=o))
    out.append(text(x + w / 2, y + 24, "Data Processing", 14, anchor="middle",
                    weight="bold", opacity=o))
    # Jupyter and DPS side by side as ONE lockup, in the block's main slot:
    # the hub and the system that runs its algorithms are one capability, and
    # the caption below names both.
    out.append(jupyter_dps(L.DPS_C[0], L.DPS_C[1], L.DPS_SIZE, opacity=o))
    for j, line in enumerate(("Disasters Hub /", "Data Processing System /",
                              "User Notebooks")):
        out.append(text(x + w / 2, y + 112 + j * 15, line, 11.5, anchor="middle", opacity=o))
    out.append(img(L.A_GITHUB, x + 26, y + 156, 40, 40, opacity=o))
    out.append(img(L.A_NOTEBOOK, x + w - 62, y + 157, 32, 38, opacity=o))


    # ---- Portal Content (right, mirrors Data Integration)
    o = _op("portal", bright)
    x, y, w, h = L.BOX_PORTAL
    out.append(box(x, y, w, h, L.FILL_PORTAL, opacity=o))
    # Right-justified, mirroring Data Integration's left-justified title: these
    # two are the outer halves of the diagram, so each title sits against its
    # own outer edge rather than both being centred inward.
    out.append(text(x + w - 22, y + 28, "Portal Content", 17, anchor="end",
                    weight="bold", opacity=o))
    for i, a in enumerate((L.A_SHOT_HOME, L.A_SHOT_STORY,
                           L.A_SHOT_VIZ, L.A_SHOT_TRAINING)):
        px, py, pw, ph = L.portal_shot(i)
        out.append(S.box(px, py, pw, ph, "#ffffff", stroke="#c9ccd1", rx=2,
                         sw=1.5, opacity=o, key=("shot", px, py)))
        # `meet`, not `slice`. The tile is 1.12 and the home page is 1.92, so
        # slicing it to fill threw away 40% of the width -- and the tile
        # already draws a white bordered frame, so fitting inside it reads as
        # a framed screenshot rather than a letterbox.
        out.append(img(a, px + 5, py + 5, pw - 10, ph - 10, opacity=o,
                       preserve="xMidYMid meet"))
        # Top row captioned ABOVE, bottom row below -- the export's own
        # arrangement, and the thing that keeps the TinaCMS fan from being
        # drawn straight through the upper captions.
        ly = py - 11 if i < 2 else py + ph + 23
        out.append(text(px + pw / 2, ly, L.PORTAL_SHOTS[i], 11.5,
                        anchor="middle", opacity=o))

    # ---- Community & Engagement (bottom-right, mirrors Funded Projects)
    o = _op("community", bright)
    x, y, w, h = L.BOX_COMMUNITY
    out.append(box(x, y, w, h, L.FILL_COMMUNITY, opacity=o, dash="7 5"))
    out.append(text(x + 18, y + 28, "Community &", 14, weight="bold", opacity=o))
    out.append(text(x + 18, y + 46, "Engagement", 14, weight="bold", opacity=o))
    out.append(text(x + 18, y + 64, "no automated data path", 9.5, opacity=o))
    for i, (a, lab) in enumerate(COMMUNITY_ITEMS):
        cx, cy = community_item_c(i)
        out.append(img(a, cx - 17, cy - 17, 34, 34, opacity=o))
        out.append(text(cx, y + 62, lab, 9.5, anchor="middle", opacity=o))

    # ---- TinaCMS, mirroring Airflow on the right of STAC
    o = _op("portal", bright)
    # Only the llama hops -- its label stays put. A caption bouncing with it
    # would read as the whole node vibrating rather than the animal jumping.
    out.append(img(L.A_TINA, L.TINA_C[0] - L.TINA_SIZE / 2,
                   L.TINA_C[1] - L.TINA_SIZE / 2 + tina_dy,
                   L.TINA_SIZE, L.TINA_SIZE, opacity=o))
    out.append(text(L.LABEL_TINA[0], L.LABEL_TINA[1], "TinaCMS", 11,
                    anchor="middle", opacity=o))

    # ---- static links from STAC out to its neighbours.
    #
    # For Earthdata GIS and Data Processing the leg drawn here is the MINOR
    # return (STAC -> block): thin and faint on purpose, because the main leg
    # runs the other way and is animated at full weight in frame_svg(). Portal
    # Content has no return leg at all -- TinaCMS is not two-way yet -- so its
    # single link keeps the heavier stroke.
    for pts, width in ((L.stac_to_egis(), STAC_MINOR_W),
                       (L.stac_to_processing(), STAC_MINOR_W),
                       (L.stac_to_portal(), STAC_MAIN_W)):
        out.append(link(pts, color=L.FLOW, width=width, opacity=o,
                        key=("stacctx", pts[0], pts[-1])))
    return "\n".join(out)


def integration_static():
    """The Data Integration container, its seven sources, and the Ingest UI."""
    out = []
    x, y, w, h = L.BOX_INTEGRATION
    out.append(box(x, y, w, h, L.FILL_INTEGRATION))
    out.append(text(L.LABEL_TITLE_DI[0], L.LABEL_TITLE_DI[1],
                    "Data Integration", 18, weight="bold"))

    for i, src in enumerate(L.SOURCES):
        cx, cy = src["c"]
        out.append(source_icon(src, cx, cy, src["size"]))
        # Label stacked UNDER the icon and centred: at the bumped type size a
        # right-hand label would run into the fan.
        lx, ly = src["label_c"]
        for j, line in enumerate(wrap(src["label"], L.SRC_LABEL_CHARS)):
            out.append(text(lx, ly + j * L.SRC_LABEL_LH, line, 12.5,
                            anchor="middle"))

    # The Disasters AWS Bucket now sits on the hub's own vertical.
    out.append(disasters_bucket(L.DISASTERS_C[0], L.DISASTERS_C[1],
                                w=L.DISASTERS_ICON, h=L.DISASTERS_ICON - 2))
    out.append(text(L.LABEL_DISASTERS[0], L.LABEL_DISASTERS[1],
                    "Disasters AWS Bucket", 12.5))

    # hub dot + the short connector into the ingest box
    out.append(S.circle(L.HUB[0], L.HUB[1], 5, fill=S.edge, key=("hub",)))

    bx, by, bw, bh = L.BOX_INGEST
    out.append(S.box(bx, by, bw, bh, "#0d1b2a", stroke="#0d1b2a", rx=5, sw=1.5,
                     key=("ingest",)))
    out.append(img(L.A_INGEST, bx + 6, by + 5, bw - 12, bh - 10))

    # the "+" the original diagram puts between the Ingest UI and Airflow
    out.append(text(L.PLUS_C[0], L.PLUS_C[1] + 9, "+", 26, anchor="middle"))

    # "Push data" riser annotation
    out.append(text(L.LABEL_PUSH[0], L.LABEL_PUSH[1], "Push data", 11))
    return "\n".join(out)


def stac_static():
    x, y, w, h = L.BOX_STAC
    # The wordmark is 1.4:1; give it a slot tall enough that "meet" scales it by
    # height to ~179x122 instead of the old 104x74.
    return "\n".join([
        box(x, y, w, h, L.FILL_STAC),
        img(L.A_STAC, x + 24, y + 18, w - 48, 122),
        img(L.A_VEDA, x + (w - 130) / 2, y + 148, 130, 38),
    ])


def di_stac_link():
    """Persistent two-way link between Data Integration and STAC."""
    fwd = L.ingest_to_stac()
    ret = L.stac_return()
    gap_x0 = L.BOX_INTEGRATION[0] + L.BOX_INTEGRATION[2]
    # poly_d, not an H command: "M x,y H x2" throws away every waypoint in
    # between, so an edited bend would vanish from the persistent link.
    fwd_vis = [p for p in fwd if p[0] >= gap_x0] or [fwd[-1]]
    return "\n".join([
        f'<path d="{poly_d([(gap_x0, fwd[0][1])] + fwd_vis)}" stroke="{L.FLOW}" '
        f'stroke-width="3.5" fill="none" opacity="0.55" marker-end="url(#ctxArrow)"/>',
        f'<path d="{poly_d(ret)}" stroke="{L.FLOW}" '
        f'stroke-width="3.5" fill="none" opacity="0.55" marker-end="url(#ctxArrow)"/>',
    ])


def funded_static():
    x, y, w, h = L.BOX_FUNDED
    return "\n".join([
        box(x, y, w, h, L.FILL_FUNDED),
        text(L.LABEL_TITLE_FUNDED[0], L.LABEL_TITLE_FUNDED[1],
             "Funded Projects", 15, weight="bold"),
        text(L.LABEL_TITLE_FUNDED[0], L.LABEL_TITLE_FUNDED[1] + 20,
             "& Partners", 15, weight="bold"),
        # Four equal-height slots on a shared centre line, re-spaced from three
        # to fit CSDA. Like ROSES, CSDA is a NASA PROGRAMME rather than a
        # product: it has no mark of its own, so it takes the meatball and is
        # told apart by its caption, exactly as ROSES is.
        img(L.A_NASA, x + 205, y + 10, 60, 44),
        img(L.A_NASA, x + 278, y + 10, 60, 44),
        img(L.A_VEDA, x + 351, y + 10, 112, 44),
        img(L.A_ESRI, x + 476, y + 10, 54, 44),
        text(x + 235, y + 70, "ROSES", 10, anchor="middle"),
        text(x + 308, y + 70, "CSDA", 10, anchor="middle"),
    ])


def airflow_static(angle):
    # Two lines, not one: the pinwheel sits right against the Data Integration
    # border, and "Airflow SM2A" on a single line runs across it.
    lx, ly = L.LABEL_AIRFLOW
    return "\n".join([
        airflow_group(L.AIRFLOW_C[0], L.AIRFLOW_C[1], L.AIRFLOW_SIZE, angle),
        text(lx, ly, "Airflow", 11, anchor="middle"),
        # 16, not 13: at the label's rendered size (11 + FONT_BUMP) the glyphs
        # are ~15 tall, so a 13px step left the two lines touching.
        text(lx, ly + 16, "SM2A", 11, anchor="middle"),
    ])


# ------------------------------------------------------------- animation ----
def flow_path(pts, progress, dash_phase, width=3.5, color=None):
    """
    Draw a connector that first draws itself in, then carries flowing dashes.
    progress 0..1 across the stage.
    """
    color = color or L.FLOW
    total = path_len(pts)
    d = poly_d(pts)
    out = []
    REVEAL = 0.28                      # fraction of the stage spent drawing the line in
    draw_in = min(1.0, progress / REVEAL)
    shown = total * smooth(draw_in)

    # faint base
    out.append(f'<path d="{d}" stroke="{color}" stroke-width="{width}" fill="none" '
               f'opacity="0.28" stroke-linecap="round" '
               f'stroke-dasharray="{shown:.1f} {total:.1f}"/>')
    if progress >= REVEAL:
        # line is fully drawn -- now run amber packets along it
        out.append(f'<path d="{d}" stroke="{L.DOT}" stroke-width="{width}" fill="none" '
                   f'stroke-linecap="round" stroke-dasharray="13 15" '
                   f'stroke-dashoffset="{-dash_phase:.1f}"/>')
        hx, hy = point_at(pts, 1.0)
    else:
        hx, hy = point_at(pts, smooth(draw_in))

    # the moving head is drawn flat in both styles: a jittered dot would boil,
    # since its position genuinely changes every frame
    out.append(f'<circle cx="{hx:.2f}" cy="{hy:.2f}" r="{width+2.2:.1f}" '
               f'fill="{L.DOT}"/>')
    out.append(f'<circle cx="{hx:.2f}" cy="{hy:.2f}" r="{width+6:.1f}" '
               f'fill="none" stroke="{L.DOT}" stroke-width="1.6" opacity="0.45"/>')
    return "\n".join(out)


def halo(x, y, w, h, strength, rx=8):
    """Fake a glow with concentric strokes -- librsvg's filter support is weak."""
    if strength <= 0.01:
        return ""
    out = []
    for grow, op, sw in ((10, 0.10, 3), (6, 0.20, 3), (2, 0.55, 2.5)):
        # seeded on the STATIC geometry, never on `strength` -- otherwise the
        # ring would re-jitter as it fades and shimmer
        out.append(S.box(x - grow, y - grow, w + 2 * grow, h + 2 * grow,
                         "none", stroke=L.GLOW, rx=rx + grow, sw=sw,
                         opacity=op * strength, key=("halo", x, y, w, h, grow)))
    return "\n".join(out)


def node_pulse(cx, cy, strength, r=34):
    if strength <= 0.01:
        return ""
    return (f'<circle cx="{cx}" cy="{cy}" r="{r*(1+0.18*strength):.1f}" fill="none" '
            f'stroke="{L.GLOW}" stroke-width="2.5" opacity="{0.55*strength:.3f}"/>')


def _overlaps(a, b, pad):
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    return not (ax + aw + pad <= bx or bx + bw + pad <= ax or
                ay + ah + pad <= by or by + bh + pad <= ay)


def place_bubble(anchor, bw, bh, strict=False, view=None):
    """
    Find the spot closest to `anchor` that collides with no container.

    This is the fix for bubbles drifting away from what they describe: instead
    of pinning each stage to a hand-chosen slot, sweep the canvas and take the
    nearest collision-free position. Falls back to the top strip if the canvas
    is somehow full.

    `view` narrows the sweep to a section's crop. The captions are placed in
    the top strip of the FULL canvas, which most section crops do not contain
    -- swept against the canvas, a section would show a caption sliced by its
    own frame edge, or none of it at all.
    """
    ax, ay = anchor
    vx, vy, vw, vh = view if view else (0, 0, L.W, L.H)
    boxes = L.occupied()
    pad = L.BUBBLE_CLEARANCE
    best, best_d = None, None
    for gx in range(int(vx) + 16, int(vx + vw - bw) - 15, 12):
        for gy in range(int(vy) + 12, int(vy + vh - bh) - 11, 12):
            cand = (gx, gy, bw, bh)
            if any(_overlaps(cand, b, pad) for b in boxes):
                continue
            d = math.hypot(gx + bw / 2 - ax, gy + bh / 2 - ay)
            if best_d is None or d < best_d:
                best, best_d = cand, d
    if best is None and strict:
        return None          # caller will retry at a different width
    return best or (int(vx) + 40, int(vy) + 16, bw, bh)


def _inside(view, x, y):
    return view[0] <= x <= view[0] + view[2] and view[1] <= y <= view[1] + view[3]


def bubble(stage, alpha, view=None):
    if alpha <= 0.01:
        return ""
    px, py = stage["anchor"]
    if view and not _inside(view, px, py):
        # The subject is off this crop entirely, so the caption is not about
        # anything the reader can see and its leader would run off the frame.
        return ""
    fs, lh, pad = 14.5, 22, 18
    boxes = L.occupied()

    # Try the widest bubble first: fewer lines means a shorter box, which is
    # what lets it sit in the short strip above the containers. Fall back to
    # narrower ones for the tight bottom corridor. Only if nothing places
    # cleanly do we accept an overlap.
    # Try EVERY width and keep the closest result, rather than accepting the
    # first that happens to fit. Widest-first return-on-first-fit meant the
    # 560 candidate always won (it is the only box the top strip admits), so
    # the narrower options were unreachable and the anchor was ignored.
    chosen, best_d = None, None
    for bw in L.BUBBLE_WIDTHS:
        chars = max(18, int((bw - 2 * pad) / ((fs + FONT_BUMP) * 0.52)))
        lines = wrap(stage["bubble"], chars)
        bh = len(lines) * lh + 26
        spot = place_bubble((px, py), bw, bh, strict=True, view=view)
        if not spot:
            continue
        d = math.hypot(spot[0] + bw / 2 - px, spot[1] + bh / 2 - py)
        if best_d is None or d < best_d:
            chosen, best_d = (spot, lines, bw, bh), d
    if chosen is None and view:
        # A crop this tight has nowhere to put a caption. Showing it anyway
        # means showing it sliced by the frame edge, which is worse than
        # showing none -- the section is a close-up, not the narration.
        return ""
    if chosen is None:
        # Nothing placed cleanly at any width. Take the least-bad overlap
        # rather than dumping the caption at (40,16), which lands it squarely
        # on the container the stage is highlighting.
        bw = L.BUBBLE_WIDTHS[-1]
        chars = max(18, int((bw - 2 * pad) / ((fs + FONT_BUMP) * 0.52)))
        lines = wrap(stage["bubble"], chars)
        bh = len(lines) * lh + 26
        chosen = (place_bubble((px, py), bw, bh), lines, bw, bh)
    (x, y, bw, bh), lines, bw, bh = chosen

    # A solid tail spanning half the canvas stops reading as "this points at
    # that" and just looks like a stray arrow. But with the captions parked in
    # the top strip, EVERY one exceeds the threshold -- so a plain cutoff left
    # all five visually unattached to what they describe.
    #
    # So: a tail when the subject is close, and a thin dashed LEADER with a
    # small ring at the subject when it is far. The leader carries the
    # association across the canvas without pretending to be an arrow.
    TAIL_MAX = 260
    near_x = max(x, min(x + bw, px))
    near_y = max(y, min(y + bh, py))
    far = math.hypot(px - near_x, py - near_y) > TAIL_MAX
    tail, leader = None, None
    if far:
        leader = (f'<path d="M {near_x:.1f},{near_y:.1f} L {px:.1f},{py:.1f}" '
                  f'stroke="{L.BUBBLE_BG}" stroke-width="1.6" fill="none" '
                  f'stroke-dasharray="5 5" opacity="0.55"/>'
                  f'<circle cx="{px:.1f}" cy="{py:.1f}" r="5" fill="none" '
                  f'stroke="{L.BUBBLE_BG}" stroke-width="2" opacity="0.75"/>')
    elif px < x:
        ty = max(y + 22, min(y + bh - 22, py))
        tail = f"M {x},{ty-12} L {x},{ty+12} L {x-16},{ty} Z"
    elif px > x + bw:
        ty = max(y + 22, min(y + bh - 22, py))
        tail = f"M {x+bw},{ty-12} L {x+bw},{ty+12} L {x+bw+16},{ty} Z"
    else:
        axx = max(x + 24, min(x + bw - 24, px))
        if py > y + bh:
            tail = f"M {axx-12},{y+bh} L {axx+12},{y+bh} L {axx},{y+bh+16} Z"
        else:
            tail = f"M {axx-12},{y} L {axx+12},{y} L {axx},{y-16} Z"

    out = [f'<g opacity="{alpha:.3f}">']
    if leader:
        out.append(leader)
    if tail:
        out.append(f'<path d="{tail}" fill="{L.BUBBLE_BG}"/>')
    out += [S.box(x, y, bw, bh, L.BUBBLE_BG, stroke=L.BUBBLE_BG, rx=12, sw=1.5,
                  key=("bub", x, y, bw, bh))]
    for i, line in enumerate(lines):
        out.append(text(x + pad, y + 26 + i * lh, line, fs, fill=L.BUBBLE_FG))
    out.append("</g>")
    return "\n".join(out)


def stage_alpha(stage, f):
    """Bubble opacity: fades in at stage start, out after its hold expires."""
    s, d = stage["start"], stage["dur"]
    hold_out = stage["hold"]
    if f < s - FADE:
        return 0.0
    if f < s:
        return (f - (s - FADE)) / FADE
    if f <= s + d + hold_out:
        return 1.0
    if f <= s + d + hold_out + FADE:
        return 1.0 - (f - (s + d + hold_out)) / FADE
    return 0.0


def stage_progress(stage, f):
    s, d = stage["start"], stage["dur"]
    if f < s:
        return -1.0
    return min(1.0, (f - s) / d)


def frame_svg(f, view=None, scope=None, captions=True):
    """
    One frame.

    `view` is an optional (x, y, w, h) viewBox -- the whole scene is still
    drawn, the viewport just crops to a region of it, so a section GIF stays
    consistent with the full one by construction.

    `scope` is an optional collection of CONTENT_GROUPS naming what may move.
    Anything outside it is drawn frozen at FREEZE_FRAME rather than removed:
    the picture stays whole, and only the section's own subject animates.
    Highlights are narration, not structure, so those are simply omitted --
    a halo held at a fixed strength is a ring the reader cannot explain.

    The root width/height follow the view, so a section rasterises at its own
    aspect instead of being letterboxed into the full diagram's 16:9.
    """
    vx, vy, vw, vh = view if view else (0, 0, L.W, L.H)

    bright = emphasis(scope)
    bright_flows = flow_emphasis(scope)

    def moves(group):
        return scope is None or group in scope

    def at(group):
        """The frame `group` is animated at -- frozen if it is out of scope."""
        return f if moves(group) else FREEZE_FRAME

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{vw:.0f}" '
        f'height="{vh:.0f}" '
        f'viewBox="{vx:.2f} {vy:.2f} {vw:.2f} {vh:.2f}">',
        '<defs>'
        f'<marker id="ctxArrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="5" '
        f'markerHeight="5" orient="auto-start-reverse">'
        f'<path d="M 0 0 L 10 5 L 0 10 z" fill="{L.FLOW}"/></marker>'
        f'<marker id="pushArrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="5" '
        f'markerHeight="5" orient="auto-start-reverse">'
        f'<path d="M 0 0 L 10 5 L 0 10 z" fill="{L.FLOW}"/></marker>'
        '</defs>',
        f'<rect width="{L.W}" height="{L.H}" fill="{S.bg}"/>',
        context_boxes(bright, hop_dy(at("portal"))),
        _dim(integration_static(), "integration", bright),
        _dim(funded_static(), "funded", bright),
        _dim(stac_static(), "stac", bright),
        _dim(di_stac_link(), "integration", bright),
    ]

    # Each stage animates on its own group's clock, so a group that is out of
    # scope sits at its settled state instead of running.
    prog = {s["key"]: stage_progress(s, at(STAGE_GROUP[s["key"]])) for s in STAGES}
    dash = {s["key"]: at(STAGE_GROUP[s["key"]]) * DASH_RATE for s in STAGES}

    # --- Airflow spins only while it is doing work. The pinwheel is a thing
    # inside Data Integration, so it runs on that group's clock: out of scope
    # it holds one angle rather than freewheeling through a still section.
    spin, ef = 0.0, at("integration")
    if stage_progress(STAGES[2], ef) >= 0 or stage_progress(STAGES[4], ef) >= 0.45:
        spin = (ef - STAGES[2]["start"]) * 4.2
    # --- highlights
    di = L.BOX_INTEGRATION
    if moves("integration") and 0 <= prog["sources"] < 1.0:
        parts.append(halo(*di, strength=1.0 - abs(prog["sources"] - 0.5) * 0.7))
    if moves("integration") and 0 <= prog["ingest"]:
        s = 1.0 if prog["ingest"] < 1 else 0.45
        parts.append(halo(*L.BOX_INGEST, strength=s, rx=5))
    if moves("stac") and (0 <= prog["airflow"] or prog["tostac"] >= 0.7):
        parts.append(halo(*L.BOX_STAC, strength=1.0))
    # progress is clamped to 1.0, so the old "< 1.3" bound never released.
    # Hold the highlight through the stage and its caption, then drop it.
    if (moves("funded") and 0 <= prog["push"]
            and f <= STAGES[3]["start"] + STAGES[3]["dur"] + STAGES[3]["hold"]):
        parts.append(halo(*L.BOX_FUNDED, strength=1.0))
        parts.append(node_pulse(L.DISASTERS_C[0], L.DISASTERS_C[1],
                                strength=max(0.0, prog["push"]), r=34))
    # The EGIS block stays lit for its whole chapter. All three beats happen
    # inside it, so releasing the halo between them would flicker.
    # The Data Processing block stays lit for its whole chapter, and its hub
    # pulses while beat 1 is producing.
    if moves("processing") and prog["dp_produce"] >= 0:
        _dp_last = STAGES[DP_STAGE_IDX[-1]]
        if f <= _dp_last["start"] + _dp_last["dur"] + _dp_last["hold"]:
            parts.append(halo(*L.BOX_PROCESSING, strength=1.0))
        if 0 <= prog["dp_produce"] < 1.0:
            parts.append(node_pulse(L.DPS_C[0], L.DPS_C[1],
                                    strength=prog["dp_produce"], r=40))

    # Community & Engagement: nothing travels, so each beat lights the channels
    # it is naming. A pulse is the right verb here -- these are destinations a
    # person goes to, not a route data takes.
    if moves("community") and prog["comm_listserv"] >= 0:
        _c_last = STAGES[COMMUNITY_STAGE_IDX[-1]]
        if f <= _c_last["start"] + _c_last["dur"] + _c_last["hold"]:
            parts.append(halo(*L.BOX_COMMUNITY, strength=1.0, rx=6))
        # One beat, one channel, one ring -- so the caption's leader and the
        # highlight are pointing at the same thing.
        for i, key in enumerate(("comm_listserv", "comm_myst", "comm_github",
                                 "comm_grafana", "comm_news")):
            s = STAGES[COMMUNITY_STAGE_IDX[i]]
            if s["start"] <= f <= s["start"] + s["dur"] + s["hold"]:
                cx, cy = community_item_c(i)
                parts.append(node_pulse(cx, cy,
                                        strength=max(0.0, prog[key]), r=26))

    if moves("portal") and prog["portal_cms"] >= 0:
        _p_last = STAGES[PORTAL_STAGE_IDX[-1]]
        if f <= _p_last["start"] + _p_last["dur"] + _p_last["hold"]:
            parts.append(halo(*L.BOX_PORTAL, strength=1.0))
        if 0 <= prog["portal_cms"] < 1.0:
            parts.append(node_pulse(L.TINA_C[0], L.TINA_C[1],
                                    strength=prog["portal_cms"], r=40))

    _egis_last = STAGES[EGIS_STAGE_IDX[-1]]
    if (moves("egis") and prog["egis_agencies"] >= 0
            and f <= _egis_last["start"] + _egis_last["dur"] + _egis_last["hold"]):
        parts.append(halo(*L.BOX_EGIS, strength=1.0))

    # --- flows
    # A frozen flow is still a bright amber dash pattern, and amber is the
    # loudest thing on this canvas. Out of scope it has to recede with the
    # block it serves, or a section about Earthdata GIS is read past in favour
    # of the Data Integration spokes sitting still at full strength.
    flows = []
    if prog["sources"] >= 0:
        # six catalog spokes plus the Disasters bucket's own riser: the bucket
        # is an ingest source from the outset, not something introduced later.
        inbound = [L.spoke(i) for i in range(6)] + [L.disasters_riser()]
        legs = []
        for i, pts in enumerate(inbound):
            local = min(1.0, max(0.0, (prog["sources"] * 1.5) - i * 0.055))
            if local > 0:
                legs.append(flow_path(pts, local, dash["sources"] + i * 9,
                                      width=2.8))
        flows.append(("integration", "".join(legs)))
    if prog["ingest"] >= 0:
        flows.append(("integration",
                      flow_path(L.hub_to_ingest(), prog["ingest"],
                                dash["ingest"], width=4)))
    if prog["airflow"] >= 0:
        flows.append(("stac",
                      flow_path(L.ingest_to_stac(), prog["airflow"],
                                dash["airflow"], width=STAC_MAIN_W)))
    if prog["push"] >= 0:
        flows.append(("funded",
                      flow_path(L.push_path(), prog["push"], dash["push"],
                                width=4)))

    # --- the Earthdata GIS chapter, running over the structure context_boxes()
    # already draws. Three beats: agency data reaches the junction, the ArcGIS
    # environments read it, then STAC feeds service workflows of its own. The
    # legs are staggered so three simultaneous packets do not read as one bar.
    egis_flows = []
    if prog["egis_agencies"] >= 0:
        for i in range(3):
            local = min(1.0, max(0.0, prog["egis_agencies"] * 1.35 - i * 0.12))
            if local > 0:
                egis_flows.append(flow_path(L.egis_converge(i), local,
                                            dash["egis_agencies"] + i * 9,
                                            width=2.6))
    if prog["egis_tools"] >= 0:
        for i in range(3):
            local = min(1.0, max(0.0, prog["egis_tools"] * 1.35 - i * 0.12))
            if local > 0:
                egis_flows.append(flow_path(L.egis_fanout(i), local,
                                            dash["egis_tools"] + i * 9,
                                            width=2.6))
    if prog["egis_stac"] >= 0:
        egis_flows.append(flow_path(L.stac_to_egis(), prog["egis_stac"],
                                    dash["egis_stac"], width=STAC_MINOR_W))
    if egis_flows:
        parts.append(_dim("".join(egis_flows), "egis", bright))

    # --- the Data Processing chapter. Beat 1 pulses the hub itself (nothing
    # travels while data is being MADE), then the pair of legs it shares with
    # STAC run in turn: up on beat 2, back down on beat 3.
    dp_flows = []
    if prog["dp_tostac"] >= 0:
        dp_flows.append(flow_path(L.processing_to_stac(), prog["dp_tostac"],
                                  dash["dp_tostac"], width=STAC_MAIN_W))
    if prog["dp_readback"] >= 0:
        dp_flows.append(flow_path(L.stac_to_processing(), prog["dp_readback"],
                                  dash["dp_readback"], width=STAC_MINOR_W))
    if dp_flows:
        parts.append(_dim("".join(dp_flows), "processing", bright_flows))

    # --- the Portal Content chapter: STAC out to TinaCMS, then TinaCMS out to
    # the four pages, staggered so the fan reads as four destinations rather
    # than one wavefront. One way throughout -- nothing returns to the catalog.
    portal_flows = []
    if prog["portal_cms"] >= 0:
        portal_flows.append(flow_path(L.stac_to_portal(), prog["portal_cms"],
                                      dash["portal_cms"], width=STAC_MAIN_W))
    if prog["portal_pages"] >= 0:
        for i in range(4):
            local = min(1.0, max(0.0, prog["portal_pages"] * 1.5 - i * 0.10))
            if local > 0:
                portal_flows.append(flow_path(L.portal_fan(i), local,
                                              dash["portal_pages"] + i * 9,
                                              width=2.4))
    if portal_flows:
        parts.append(_dim("".join(portal_flows), "portal", bright_flows))
    if prog["tostac"] >= 0:
        flows.append(("stac",
                      flow_path(L.disasters_to_stac(), prog["tostac"],
                                dash["tostac"], width=STAC_MAIN_W)))
    for _grp, _markup in flows:
        parts.append(_dim(_markup, _grp, bright_flows))

    # --- STAC's two-way exchange with its vertical neighbours.
    # These are the MAIN legs -- the ArcGIS tools and Data Processing pushing
    # back INTO STAC -- so they carry the same amber packets as the staged
    # flows. Their minor returns are the thin muted lines in context_boxes().
    #
    # They are always DRAWN. What is timed is only whether their packets MOVE:
    # holding the phase still leaves a line that is pixel-identical frame to
    # frame, and releasing it just starts the packets, with nothing appearing
    # or vanishing at the boundary. That is what keeps them quiet under the
    # Airflow caption and lets it end without a pop.
    #
    # Out of scope they drop to the muted weight their own minor returns are
    # drawn at, so the pair reads as one still piece of structure. Freezing the
    # packets instead would be motionless too, but a bright amber dash pattern
    # still asks to be followed, and in a section about somewhere else it is
    # the wrong thing to be reading.
    for group, pts, off in (("egis", L.egis_to_stac(), 5),
                            ("processing", L.processing_to_stac(), 12)):
        if moves(group):
            phase = max(f, EXCHANGE_MOTION_START) * DASH_RATE + off
            parts.append(flow_path(pts, 1.0, phase, width=STAC_MAIN_W))
        else:
            parts.append(link(pts, color=L.FLOW, width=STAC_MINOR_W,
                              opacity=L.CONTEXT_OPACITY, key=("exch", group)))

    # --- ambient: Portal Content. Deliberately quiet -- thin dark connectors
    # that draw themselves in one after another, then a slow highlight that
    # visits one tile at a time. No packets and no amber: this is a secondary
    # area and must stay behind the STAC flows.
    for i in range(4):
        p = ambient(at("portal"), PORTAL_FAN_DELAY + i * PORTAL_FAN_STEP)
        if p >= 0:
            parts.append(link(L.portal_fan(i), color=S.ink, width=1.6,
                              opacity=0.42, progress=p, key=("pfan", i)))
    settled = (f - AMBIENT_START - PORTAL_FAN_DELAY
               - 3 * PORTAL_FAN_STEP - AMBIENT_RAMP)
    if moves("portal") and settled >= 0:
        k = int(settled / PORTAL_CYCLE) % 4
        u = (settled % PORTAL_CYCLE) / float(PORTAL_CYCLE)
        parts.append(halo(*L.portal_shot(k),
                          strength=0.45 * (0.5 - 0.5 * math.cos(2 * math.pi * u)),
                          rx=2))

    # pinwheel last, so the flow line passes behind it rather than through it
    # The pinwheel and its label are part of the hub-to-STAC run, so they
    # recede with it. Undimmed, a full-colour spinner sat at the Data
    # Integration border pulling the eye in every other section.
    parts.append(_dim(airflow_static(spin), "stac", bright_flows))

    # --- narration
    # A caption belongs to a chapter, so it is scoped like everything else. A
    # section that narrated the whole film would describe the Airflow ingest
    # over a still diagram while its own subject was the only thing moving --
    # the words and the motion telling different stories at once.
    # A poster wants the diagram, not the commentary: a caption is a claim
    # about a moment, and a still has no moment to be about.
    live = [] if not captions else [(stage_alpha(s, f), s) for s in STAGES
                                    if moves(STAGE_GROUP.get(s["key"], ""))]
    live = [(a, s) for a, s in live if a > 0]
    if live:
        a, s = max(live, key=lambda t: t[0])
        parts.append(bubble(s, a, view=view))

    parts.append("</svg>")
    return "\n".join(parts)


def stage_assets():
    """
    Mirror assets/ into frames/assets/.

    librsvg will not load an <image href> outside the referencing document's
    own directory tree, so a frame in frames/ cannot reach ../assets/. This
    copy is what makes the sprites resolvable.

    Compares SIZE, not mtime. Anything that preserves timestamps -- cp -p,
    rsync -t, tar -x, restoring a backup -- leaves an mtime check thinking the
    copy is current, and the build then renders the OLD sprite and reports
    success. Content is the only honest test.
    """
    os.makedirs(L.FRAME_ASSETS, exist_ok=True)
    copied = 0
    for name in os.listdir(L.ASSETS):
        src = os.path.join(L.ASSETS, name)
        if not os.path.isfile(src):
            continue                      # a stray directory must not crash us
        dst = os.path.join(L.FRAME_ASSETS, name)
        if (not os.path.exists(dst)
                or os.path.getsize(src) != os.path.getsize(dst)):
            with open(src, "rb") as a, open(dst, "wb") as b:
                b.write(a.read())
            copied += 1
    return copied


def _arg(argv, flag, default=None):
    for a in argv[1:]:
        if a.startswith(flag + "="):
            return a.split("=", 1)[1]
    return default


def section_frame(f, name):
    """One frame of a section: its crop AND its content scope, together.

    Two calls that must not drift apart -- a section rendered with its view but
    without its scope shows another chapter's motion inside its own frame.
    """
    return frame_svg(f, section_view(name), SECTION_SCOPE.get(name))


def write_frames(view=None, scope=None, span=None):
    """
    Render frames into frames/. `span` is an inclusive (first, last) range.

    Frames always go in frames/ itself, never a per-section subdirectory. The
    sprite hrefs are absolute paths under frames/assets/, and librsvg refuses a
    resource outside the referencing document's own directory tree -- a frame in
    frames/egis/ could not reach frames/assets/, and would render with every
    logo silently missing. So sections are built one at a time through this one
    directory; it is scratch space, and the GIFs are the artefacts worth keeping.

    Staging happens here rather than in the caller, because a caller that
    forgets gets that same silent failure (docs/GOTCHAS.md).
    """
    os.makedirs(L.FRAMES, exist_ok=True)
    stage_assets()
    # Only frames, never frames/* -- the latter takes the staged sprites too.
    for old in os.listdir(L.FRAMES):
        if old.endswith((".svg", ".png")):
            os.remove(os.path.join(L.FRAMES, old))
    first, last = span if span else (0, TOTAL - 1)
    # Output numbering restarts at zero regardless of where the span begins:
    # ffmpeg reads f%04d as a contiguous sequence, and a gap at the front makes
    # it silently read nothing at all.
    for i, f in enumerate(range(first, last + 1)):
        with open(f"{L.FRAMES}/f{i:04d}.svg", "w", encoding="utf-8") as fh:
            fh.write(frame_svg(f, view, scope))
    return last - first + 1


def main():
    argv = sys.argv
    if "--list-sections" in argv:
        for key, label, _rect in sections():
            vx, vy, vw, vh = section_view(key)
            rw, rh, gw, gh = section_size(key)
            scope = ",".join(SECTION_SCOPE.get(key, ("all",)))
            print("  %-14s %-22s view=(%d %d %d %d)  gif=%dx%d  moves=%s"
                  % (key, label, vx, vy, vw, vh, gw, gh, scope))
        return

    # Machine-readable, for build.sh: a section is rendered at its own aspect,
    # so the rasteriser and ffmpeg cannot both be pinned to 1600x900 / 1280x720.
    size_of = _arg(argv, "--section-size")
    if size_of is not None:
        print("%d %d %d %d" % section_size(size_of or None))
        return

    # A single still of the whole ecosystem: everything settled, nothing
    # dimmed, nothing narrated. This is the poster the chapters are cut from.
    if "--poster" in argv:
        os.makedirs(L.FRAMES, exist_ok=True)
        stage_assets()
        out = os.path.join(L.FRAMES, "poster.svg")
        with open(out, "w", encoding="utf-8") as fh:
            fh.write(frame_svg(TOTAL - 1, captions=False))
        print(out)
        return

    name = _arg(argv, "--section")
    if name:
        view = section_view(name)
        span = section_span(name)
        n = write_frames(view, SECTION_SCOPE.get(name), span)
        print(f"wrote {n} frames -> {L.FRAMES}  (section '{name}', "
              f"frames {span[0]}..{span[1]}, {n/FPS:.1f}s at {FPS}fps)")
        return

    n = write_frames()
    print(f"wrote {n} frames -> {L.FRAMES}  ({n/FPS:.1f}s at {FPS}fps)")


if __name__ == "__main__":
    main()
