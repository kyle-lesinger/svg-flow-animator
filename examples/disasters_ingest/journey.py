#!/usr/bin/env python3
"""
The journey slide: satellites' swaths become datasets, the problem with getting
datasets into tools by converting and copying them, and the fix.

    1  a satellite paints a swath on the globe; it peels off as a dataset
    2  the way it is done today: a copy, in the format it needs, into every tool
    3  other satellites, other formats -- copies multiply, datasets x tools
    4  instead: each dataset converted ONCE to a cloud-optimized format, stored once
    5  STAC indexes them, whatever the satellite, so they are searchable
    6  the Disasters PORTAL and MMGIS find data through STAC and read in place
    7  a new satellite and format is one file and one STAC item; every tool has it

The tools never move between the problem and the fix, so the reader compares
the same two boxes before and after rather than two different pictures.

MMGIS draws each swath on a flat map cut from the SAME texture as the globe,
placed from the swath's own latitudes and longitudes against the crop's exact
extent -- so what the reader saw painted on the globe lands on the same
coastline in the 2-D view. The PORTAL is a website, shown as its pages; a page
screenshot has no geographic extent, so data there is a chip per dataset, not
an overlay that could only be placed by eye.

Like the intro, this is a slide, not a chapter of the diagram: its own picture,
its own timeline, and it plays once (gen_frames.slides()). Its geometry lives
here rather than in layout.py for the same reason the intro's panels are not
handles: the editor previews the main film, where none of this exists.
"""
import math
import os

import gen_frames as G
import globe as GL
import layout as L
from style import S

FPS, FADE = G.FPS, G.FADE

# ---------------------------------------------------------------- the cast ---
# Real missions and the formats their products ship in. Swath widths are
# widened to read at slide size but keep their order: VIIRS widest, Landsat
# and ECOSTRESS narrowest. The last one arrives after the fix.
SATS = (
    dict(name="Landsat 9", short="Landsat 9", fmt="GeoTIFF", incl=98.2,
         half=3.0, at=(33, -74), span=52, panel="#2f5fb3"),
    dict(name="NOAA-20 VIIRS", short="NOAA-20", fmt="NetCDF", incl=98.7,
         half=8.0, at=(22, -95), span=60, panel="#b7791f"),
    dict(name="ISS ECOSTRESS", short="ISS", fmt="HDF5", incl=51.6,
         half=3.5, at=(8, -62), span=46, panel="#7b3fa0"),
    dict(name="Terra MODIS", short="Terra", fmt="HDF4", incl=98.2,
         half=6.5, at=(26, -117), span=56, panel="#2f855a"),
)
N_DUP = 3                # datasets copied into every tool: the problem's peak
CLOUD_FMT = "COG"

# ------------------------------------------------------------------ layout ---
GLOBE = GL.Globe(275, 420, 210, 22, -88)       # centred on the Gulf of Mexico
TEXTURE = os.path.join(L.ASSETS, "blue-marble-2048.jpg")
ALT = 1.22               # drawn orbit radius in Earth radii -- exaggerated to read
ROWS, COLS = 36, 6       # cells along / across a swath

STORE = (555, 236, 195, 290)
TILE_X, TILE_W, TILE_H = STORE[0] + 22, 150, 24
SLOT_Y = tuple(STORE[1] + 64 + 52 * k for k in range(len(SATS)))
STAC = (790, 300, 215, 222)
TOOLS = (("portal", "Disasters PORTAL", "website", (1045, 120, 515, 280)),
         ("mmgis", "MMGIS", "analyze", (1045, 470, 515, 280)))
# (caption, screenshot, crop anchor). The home page is twice as wide as the
# card: cropped from the middle it lost the logo and title that identify it.
PAGES = (("Home Page", L.A_SHOT_HOME, "xMinYMin"),
         ("Event / Story", L.A_SHOT_STORY, "xMidYMin"),
         ("Training", L.A_SHOT_TRAINING, "xMidYMin"))
# The 2-D map's requested box; flat_extent snaps it to whole texture pixels.
FLAT_BOX, FLAT_EXT = GL.flat_extent(-152, -24, -20, 58)
CAPTION = (300, 796, 1000, 56)
WARN = "#c0392b"
MUTED = "#6b7280"

# One colour ramp per dataset, so each reads as a different product.
RAMPS = (
    ("#320a5e", "#781c6d", "#bc3754", "#ed6925", "#fbb61a", "#fcffa4"),
    ("#440154", "#3b528b", "#21918c", "#5ec962", "#fde725"),
    ("#4a0d36", "#8c1f5d", "#d6457f", "#f59bb8", "#ffe3ee"),
    ("#00302a", "#03684f", "#1f9e6e", "#7fd18b", "#e5f5b0"),
)

# ---------------------------------------------------------------- timeline ---
# Derived from a few lengths, so the pace is tuned here and nowhere else. The
# beats overlap on purpose -- the next pass starts while the last copies land
# -- which is why this is frame numbers and not a stage list.
LEAD = 8                 # globe alone before the first pass
FIRST_PASS = 4 * FPS     # the first pass is watched...
PASS = 2 * FPS           # ...the rest are quick
SCALE_STEP = 5 * FPS     # one extra satellite every five seconds
PROBLEM_HOLD = 8 * FPS   # the peak, held long enough to say it out loud
STEP = 4 * FPS           # each beat of the fix

REC, PEEL, COPY = [], [], []
_a = LEAD
REC.append((_a, _a + FIRST_PASS))
PEEL.append((_a + FIRST_PASS + 4, _a + FIRST_PASS + 32))
TOOLS_IN = PEEL[0][1]
COPY.append((TOOLS_IN + 10, TOOLS_IN + 40))
SCALE_AT = TOOLS_IN + 5 * FPS
for _i in range(N_DUP - 1):
    _a = SCALE_AT + _i * SCALE_STEP
    REC.append((_a, _a + PASS))
    PEEL.append((_a + PASS + 3, _a + PASS + 18))
    COPY.append((_a + PASS + 20, _a + PASS + 40))
DIFFICULTY = COPY[-1][1] + 10
STORE_AT = DIFFICULTY + PROBLEM_HOLD     # where the problem ends: ~30 s
INDEX_AT = STORE_AT + STEP
META = [(INDEX_AT + 7 + 8 * k, INDEX_AT + 25 + 8 * k) for k in range(N_DUP)]
READ_AT = INDEX_AT + STEP
NEW_AT = READ_AT + STEP
_a = NEW_AT + 5
REC.append((_a, _a + PASS))
PEEL.append((_a + PASS + 3, _a + PASS + 19))
META.append((PEEL[-1][1] + 14, PEEL[-1][1] + 28))
NEW_SHOWN = META[-1][1] + 3
TOTAL = NEW_SHOWN + 5 * FPS
# When each dataset's file becomes the cloud format: all of the problem's at
# once when the store appears, the newcomer as it lands.
CONVERT = [STORE_AT + 10] * N_DUP + [PEEL[-1][1] + 2]

CAPTIONS = (
    (0, "A satellite sweeps a swath of Earth: one new dataset."),
    (TOOLS_IN, "Today, each tool gets its own copy, in the format it needs."),
    (SCALE_AT, "Another satellite, another format, another copy for every tool."),
    (DIFFICULTY, "It doesn't scale: every format converted and copied for every tool."),
    (STORE_AT, "Instead, convert each dataset once to a cloud-optimized format, "
               "and store it once."),
    (INDEX_AT, "STAC indexes them all: one search across every satellite's data."),
    (READ_AT, "Every tool finds the data through STAC and reads it in place."),
    (NEW_AT, "A new satellite or format is one file and one STAC item, "
             "and every tool has it."),
)


def problem_label(n):
    return "%d satellites · %d formats × 2 tools = %d copies" % (n, n, 2 * n)


def ramp(f, a, b):
    """0 before a, 1 after b, eased between."""
    if f <= a:
        return 0.0
    if f >= b:
        return 1.0
    return G.smooth((f - a) / float(b - a))


def window(f, a, b):
    """Fades in over FADE from a, holds, fades out over FADE after b."""
    return min(ramp(f, a, a + FADE), 1.0 - ramp(f, b, b + FADE))


# ---------------------------------------------------------------- the data ---
def _hex(c):
    return tuple(int(c[i:i + 2], 16) for i in (1, 3, 5))


def ramp_color(stops, v):
    v = max(0.0, min(1.0, v)) * (len(stops) - 1)
    i = min(int(v), len(stops) - 2)
    a, b, t = _hex(stops[i]), _hex(stops[i + 1]), v - i
    return "#%02x%02x%02x" % tuple(int(a[j] + (b[j] - a[j]) * t) for j in range(3))


def value(k, r, c):
    """A smooth, data-looking field. Deterministic: the swath must not boil."""
    h = math.sin(k * 12.9898 + r * 78.233 + c * 37.719) * 43758.5453
    noise = (h - math.floor(h)) - 0.5
    return (0.5 + 0.3 * math.sin(r * 0.29 + c * 0.8 + k * 1.7)
            + 0.18 * math.sin(r * 0.11 - c * 0.5 + k) + 0.12 * noise)


PASSES = [GL.pass_over(GLOBE, s["incl"], s["at"], math.radians(s["half"]),
                       math.radians(s["span"])) for s in SATS]


def _cells(k):
    """[(row, col, ECEF corners, globe quad, tile quad, colour)] for dataset k."""
    cw, ch = TILE_W / float(ROWS), TILE_H / float(COLS)
    out = []
    for r, c, q in PASSES[k].cells(ROWS, COLS):
        gq = [GLOBE.xy(v)[0] for v in q]
        x0, y0 = TILE_X + r * cw, SLOT_Y[k] + c * ch
        # corner order matches Pass.cells: along-track -> x, across -> y
        tq = [(x0, y0), (x0, y0 + ch), (x0 + cw, y0 + ch), (x0 + cw, y0)]
        out.append((r, c, q, gq, tq, ramp_color(RAMPS[k], value(k, r, c))))
    return out


CELLS = [_cells(k) for k in range(len(SATS))]
# One colour per row, for the small renderings (copies, chips).
STRIPES = [[ramp_color(RAMPS[k], value(k, r, COLS // 2)) for r in range(ROWS)]
           for k in range(len(SATS))]


def footprint(k):
    """Canvas outline of swath k -- what stays on the globe once it peels."""
    p = PASSES[k]
    n = 24
    left = [GLOBE.xy(p.ground(p.s0 + (p.s1 - p.s0) * i / n, -p.half))[0]
            for i in range(n + 1)]
    right = [GLOBE.xy(p.ground(p.s1 - (p.s1 - p.s0) * i / n, p.half))[0]
             for i in range(n + 1)]
    return left + right


FOOTPRINTS = [footprint(k) for k in range(len(SATS))]


# ----------------------------------------------------------------- geometry ---
def tool_rect(key):
    return [t[3] for t in TOOLS if t[0] == key][0]


def content_rect(rect):
    """Where a tool shows its data: right of the copies column."""
    x, y, w, _h = rect
    return (x + 140, y + 46, w - 155, 220)


def flat_rect():
    """The 2-D map inside MMGIS, at the crop's own aspect -- one degree of
    longitude is as wide as one of latitude is tall, as on the texture."""
    cx, cy, cw, ch = content_rect(tool_rect("mmgis"))
    lon0, lon1, lat0, lat1 = FLAT_EXT
    h = cw * (lat1 - lat0) / (lon1 - lon0)
    return (cx, cy + (ch - h) / 2, cw, h)


def to_flat(p):
    """ECEF point -> its place on the MMGIS map: the same lat/lon as on the globe."""
    lat, lon = GL.to_latlon(p)
    fx, fy, fw, fh = flat_rect()
    lon0, lon1, lat0, lat1 = FLAT_EXT
    return (fx + (lon - lon0) / (lon1 - lon0) * fw,
            fy + (lat1 - lat) / (lat1 - lat0) * fh)


FLAT_CELLS = [[([to_flat(v) for v in q], color) for _r, _c, q, _g, _t, color in cells]
              for cells in CELLS]


def stack_slot(rect, k):
    x, y, _w, _h = rect
    return (x + 22, y + 78 + k * 30)


def copy_line(k, rect):
    sx, sy = stack_slot(rect, k)
    return [(TILE_X + TILE_W + 8, SLOT_Y[k] + TILE_H / 2), (sx - 6, sy + 7)]


def item_y(k):
    return STAC[1] + 122 + k * 24


def meta_line(k):
    return [(TILE_X + TILE_W + 8, SLOT_Y[k] + TILE_H / 2),
            (STAC[0] - 4, item_y(k) - 4)]


def bezier(p0, c, p1, n=32):
    return [((1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * c[0] + t * t * p1[0],
             (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * c[1] + t * t * p1[1])
            for t in (i / float(n) for i in range(n + 1))]


def read_arc(key):
    """Storage -> a tool's data: the file itself, read where it lives."""
    cx, cy, _cw, ch = content_rect(tool_rect(key))
    sx, sy, sw, sh = STORE
    if key == "portal":
        return bezier((sx + sw, sy + 30), (900, 130), (cx, cy + 40))
    return bezier((sx + sw, sy + sh - 30), (900, 720), (cx, cy + ch - 40))


def find_line(key):
    """STAC -> a tool: how it finds the data (metadata, not pixels)."""
    x, y, w, h = STAC
    tx, ty, _tw, th = tool_rect(key)
    if key == "portal":
        return [(x + w + 4, y + 70), (tx - 4, ty + th - 50)]
    return [(x + w + 4, y + h - 70), (tx - 4, ty + 50)]


# ---------------------------------------------------------------- drawing ----
def _d(pts, close=True):
    return "M" + " L".join("%.1f,%.1f" % p for p in pts) + (" Z" if close else "")


def quad(pts, color, op=1.0, cls="cell"):
    # Stroked in its own colour: adjacent antialiased quads otherwise leave
    # hairline seams of background between them.
    return ('<path class="%s" d="%s" fill="%s" stroke="%s" stroke-width="0.6"'
            ' opacity="%.3f"/>' % (cls, _d(pts), color, color, op))


def lerp_quad(a, b, t):
    return [(p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t)
            for p, q in zip(a, b)]


def mini(x, y, k, w=100, h=14, op=1.0, cls="copy"):
    """A dataset, small: one stripe per row."""
    sw = w / float(ROWS)
    body = "".join('<path d="M%.2f,%.2f h%.2f v%.2f h%.2f Z" fill="%s"/>'
                   % (x + i * sw, y, sw + 0.4, h, -(sw + 0.4), c)
                   for i, c in enumerate(STRIPES[k]))
    return '<g class="%s" opacity="%.3f">%s</g>' % (cls, op, body)


def satellite(x, y, ang, op, panel):
    """Flat in both styles: it moves every frame, so a sketched one would boil."""
    return ('<g transform="translate(%.1f,%.1f) rotate(%.1f) scale(1.3)" '
            'opacity="%.3f">'
            '<path d="M-27,-5 h18 v10 h-18 Z M9,-5 h18 v10 h-18 Z" '
            'fill="%s" stroke="#1b2f57" stroke-width="1"/>'
            '<path d="M-18,-5 v10 M18,-5 v10" stroke="#ffffff" stroke-width="0.8"'
            ' opacity="0.7"/>'
            '<path d="M-7,-7 h14 v14 h-14 Z" fill="#e3e6ea" stroke="#3a414a" '
            'stroke-width="1.2"/></g>' % (x, y, ang, op, panel))


def tag(x, y, s, op):
    """A satellite's name, on a dark pill so it reads over globe and paper alike."""
    w = len(s) * 7.2 + 18
    return ('<g opacity="%.3f"><path d="M%.1f,%.1f h%.1f v22 h%.1f Z" fill="%s"'
            ' opacity="0.88"/>%s</g>'
            % (op, x, y - 16, w, -w, L.BUBBLE_BG,
               G.text(x + 9, y, s, 9.5, fill=L.BUBBLE_FG)))


def ring(p, front, op):
    """The half of pass p's orbit in front of (or behind) the globe."""
    pts = [p.sat(2 * math.pi * i / 240, ALT) for i in range(241)]
    runs, cur = [], []
    for v in pts:
        if (GLOBE.view(v)[2] >= 0) == front:
            cur.append(GLOBE.xy(v)[0])
        elif cur:
            runs.append(cur)
            cur = []
    if cur:
        runs.append(cur)
    dash = "" if front else ' stroke-dasharray="4 5"'
    return "".join('<path d="%s" fill="none" stroke="#7d8ea8" stroke-width="1.4"'
                   ' opacity="%.3f"%s/>' % (_d(r, close=False), op, dash)
                   for r in runs if len(r) > 1)


def lead(k):
    return 12 if k == 0 else 6


def sat_s(k, f):
    """Where along pass k the satellite is at frame f, or None if not flying."""
    a, b = REC[k]
    p = PASSES[k]
    if f < a - lead(k) or f > b + 8:
        return None
    return p.s0 + (f - a) * (p.s1 - p.s0) / float(b - a)


def rows_painted(k, f):
    a, b = REC[k]
    return max(0, min(ROWS, int((f - a) / float(b - a) * ROWS + 0.999)))


def shown_in_tools(k, f):
    """0..1: how far dataset k has appeared in the tools."""
    if k < len(COPY):
        return ramp(f, COPY[k][1], COPY[k][1] + FADE)
    return ramp(f, NEW_SHOWN, NEW_SHOWN + FADE)


# ------------------------------------------------------------------ frames ---
def journey_svg(f):
    href = GL.globe_png(TEXTURE, L.FRAME_ASSETS, GLOBE)
    W, H = L.W, L.H
    fx, fy, fw, fh = flat_rect()
    out = ['<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" '
           'viewBox="0 0 %d %d">' % (W, H, W, H),
           '<defs><clipPath id="jflat"><path d="M%.1f,%.1f h%.1f v%.1f h%.1f Z"/>'
           '</clipPath></defs>' % (fx, fy, fw, fh, -fw),
           '<rect width="%d" height="%d" fill="%s"/>' % (W, H, S.bg)]

    # --- the globe, and whichever pass is flying
    flying = [(k, sat_s(k, f)) for k in range(len(SATS))]
    flying = [(k, s) for k, s in flying if s is not None]
    for k, _s in flying:
        out.append(ring(PASSES[k], False, 0.5))
    r = GLOBE.r
    out.append(G.img(href, GLOBE.cx - r, GLOBE.cy - r, 2 * r, 2 * r, frame=False))
    out.append('<circle cx="%.1f" cy="%.1f" r="%.1f" fill="none" stroke="#9cc4ff" '
               'stroke-width="5" opacity="0.35"/>' % (GLOBE.cx, GLOBE.cy, r + 2))
    for k in range(len(SATS)):
        if f >= PEEL[k][0]:
            out.append('<path d="%s" fill="%s" fill-opacity="0.12" stroke="#ffffff" '
                       'stroke-width="1" stroke-opacity="0.55"/>'
                       % (_d(FOOTPRINTS[k]), STRIPES[k][ROWS // 2]))

    # --- the store and STAC sit under the cells, which fly in on top of them
    out.append(_store(f))
    out.append(_stac(f))
    for key, title, verb, rect in TOOLS:
        out.append(_tool(f, key, title, verb, rect))

    # the problem: every dataset copied into every tool
    gone = 1.0 - ramp(f, STORE_AT, STORE_AT + 15)
    hot = ramp(f, DIFFICULTY, DIFFICULTY + 12)
    for k, (a, b) in enumerate(COPY):
        if f < a or gone <= 0:
            continue
        for key, _t, _v, rect in TOOLS:
            line = copy_line(k, rect)
            out.append(G.link(line, color=WARN, width=1.6 + 0.8 * hot,
                              opacity=(0.55 + 0.4 * hot) * gone,
                              progress=ramp(f, a, a + 12), key=("jcopy", k, key)))
            t = ramp(f, a + 6, b)
            if 0 < t < 1:
                (x0, y0), (x1, y1) = line
                out.append(mini(x0 + (x1 - x0) * t - 50, y0 + (y1 - y0) * t - 7,
                                k, op=gone, cls="flying"))
    if f >= DIFFICULTY and gone > 0:
        a = ramp(f, DIFFICULTY, DIFFICULTY + FADE) * gone
        out.append(G.text(800, 700, problem_label(N_DUP), 14, fill=WARN,
                          anchor="middle", weight="bold", opacity=a))
        out.append(G.text(800, 724, "each converted, stored and kept in sync "
                          "separately", 11, fill=WARN, anchor="middle", opacity=a))

    # the fix: metadata into STAC, tools find it there and read in place
    for k, (a, b) in enumerate(META):
        if f >= a:
            out.append(G.link(meta_line(k), color=L.FLOW, width=1.5, opacity=0.8,
                              progress=ramp(f, a, b), key=("jmeta", k)))
    if f >= READ_AT:
        a = ramp(f, READ_AT + 40, READ_AT + 40 + FADE)
        for key, _t, _v, _r in TOOLS:
            out.append(G.link(find_line(key), color=L.FLOW, width=2.2,
                              progress=ramp(f, READ_AT + 4, READ_AT + 20),
                              key=("jfind", key)))
            arc = read_arc(key)
            p = ramp(f, READ_AT + 18, READ_AT + 50)
            if p > 0:
                out.append(G.flow_path(arc, p, f * G.DASH_RATE, width=3))
            # Set along the arc, just off it: a level label crossed the
            # steeper of the two.
            i = len(arc) // 2
            (x0, y0), (x1, y1) = arc[i - 1], arc[i + 1]
            ang = math.degrees(math.atan2(y1 - y0, x1 - x0))
            out.append('<g transform="translate(%.1f,%.1f) rotate(%.1f)">%s</g>'
                       % (arc[i][0], arc[i][1], ang,
                          G.text(0, -9, "reads the same file", 10.5, fill=MUTED,
                                 anchor="middle", opacity=a)))

    # --- swath cells: painted on the globe, peeling off, or filed as a dataset
    for k in range(len(SATS)):
        if f < REC[k][0]:
            continue
        pa, pb = PEEL[k]
        painted = rows_painted(k, f)
        t = (f - pa) / float(pb - pa)
        for r, _c, _q, gq, tq, color in CELLS[k]:
            if r >= painted:
                continue
            local = G.smooth(max(0.0, min(1.0, (t - 0.5 * r / ROWS) / 0.5)))
            q = gq if local <= 0 else (tq if local >= 1 else lerp_quad(gq, tq, local))
            out.append(quad(q, color, op=0.85 + 0.15 * local))

    # --- each satellite, its beam, the front of its orbit, and its name
    for k, s in flying:
        p, sat = PASSES[k], SATS[k]
        a, b = REC[k]
        op = min(ramp(f, a - lead(k), a - lead(k) + 5), 1.0 - ramp(f, b + 2, b + 8))
        out.append(ring(p, True, 0.7 * op))
        pos = p.sat(s, ALT)
        (x, y), _z = GLOBE.xy(pos)
        if a <= f <= b:
            e1, e2 = (GLOBE.xy(p.ground(s, u))[0] for u in (-p.half, p.half))
            out.append('<path d="%s" fill="#ffd27a" opacity="0.28"/>'
                       % _d([(x, y), e1, e2]))
            out.append('<path d="%s" stroke="#ffd27a" stroke-width="2.4" '
                       'fill="none"/>' % _d([e1, e2], close=False))
        if not GLOBE.hidden(pos):
            (x2, y2), _ = GLOBE.xy(p.sat(s + 0.02, ALT))
            ang = math.degrees(math.atan2(y2 - y, x2 - x)) + 90
            out.append(satellite(x, y, ang, op, sat["panel"]))
            out.append(tag(x + 26, y - 20, sat["name"], op))

    out.append(_caption(f))
    out.append("</svg>")
    return "\n".join(out)


def _store(f):
    """The dataset column: 'New datasets' in the problem, the cloud store after."""
    out = []
    x, y, w, h = STORE
    before = 1.0 - ramp(f, STORE_AT, STORE_AT + 10)
    if f >= PEEL[0][0] and before > 0:
        out.append(G.text(x + w / 2, y + 30, "New datasets", 15, anchor="middle",
                          weight="bold", opacity=before * ramp(f, PEEL[0][0],
                                                              PEEL[0][0] + FADE)))
    a = ramp(f, STORE_AT + 8, STORE_AT + 8 + FADE)
    if a > 0:
        lit = window(f, STORE_AT + 8, INDEX_AT - FADE)
        out.append(G.halo(x, y, w, h, strength=lit))
        out.append('<g opacity="%.3f">' % a
                   + G.box(x, y, w, h, "#eef4fb")
                   + G.text(x + w / 2, y + 30, "Cloud storage", 15,
                            anchor="middle", weight="bold")
                   + G.text(x + w / 2, y + h - 14, "each dataset stored once", 11,
                            fill=MUTED, anchor="middle")
                   + "</g>")
    # each file's name and format -- the native one, then the cloud format
    for k, sat in enumerate(SATS):
        landed = ramp(f, PEEL[k][1] - 6, PEEL[k][1])
        if landed <= 0:
            continue
        c = ramp(f, CONVERT[k], CONVERT[k] + 12)
        ty = SLOT_Y[k] - 6
        if c < 1:
            out.append(G.text(TILE_X, ty, "%s · %s" % (sat["name"], sat["fmt"]),
                              9, opacity=landed * (1 - c)))
        if c > 0:
            out.append(G.text(TILE_X, ty, "%s · %s" % (sat["name"], CLOUD_FMT),
                              9, fill=L.FLOW, weight="bold", opacity=c))
    return "".join(out)


def _stac(f):
    if f < INDEX_AT:
        return ""
    x, y, w, h = STAC
    a = ramp(f, INDEX_AT, INDEX_AT + FADE)
    lit = window(f, INDEX_AT, READ_AT - FADE)
    out = [G.halo(x, y, w, h, strength=lit), '<g opacity="%.3f">' % a,
           G.box(x, y, w, h, L.FILL_STAC),
           G.img(L.A_STAC, x + 35, y + 14, w - 70, 66, frame=False),
           G.text(x + w / 2, y + 92, "indexed · searchable", 11,
                  fill=MUTED, anchor="middle")]
    for k, (_s, e) in enumerate(META):
        if f >= e:
            iy = item_y(k)
            out.append('<g class="item" opacity="%.3f">' % ramp(f, e, e + FADE)
                       + '<path d="M%.1f,%.1f h22 v12 h-22 Z" fill="%s"/>'
                       % (x + 22, iy - 10, STRIPES[k][ROWS // 2])
                       + G.text(x + 54, iy, "item · %s" % SATS[k]["short"], 11)
                       + "</g>")
    out.append("</g>")
    return "".join(out)


def _pages(f, rect):
    """The PORTAL as what it is: a website, its pages, the data each one carries."""
    cx, cy, cw, _ch = content_rect(rect)
    pw, gap = (cw - 18) / 3.0, 9
    out = []
    for i, (label, href, anchor) in enumerate(PAGES):
        px = cx + i * (pw + gap)
        out.append(G.box(px, cy, pw, 186, "#ffffff", stroke="#9aa1ab", rx=3, sw=1.2))
        out.append('<path d="M%.1f,%.1f h%.1f v11 h%.1f Z" fill="#e9ecf0"/>'
                   % (px + 1, cy + 1, pw - 2, -(pw - 2)))
        for j, dot in enumerate(("#ff5f57", "#febc2e", "#28c840")):
            out.append('<circle cx="%.1f" cy="%.1f" r="1.9" fill="%s"/>'
                       % (px + 7 + j * 6, cy + 6.5, dot))
        out.append(G.img(href, px + 3, cy + 14, pw - 6, 140,
                         preserve=anchor + " slice", frame=False))
        for k in range(len(SATS)):
            s = shown_in_tools(k, f)
            if s > 0:
                out.append(mini(px + 5 + k * 27, cy + 162, k, w=24, h=10, op=s,
                                cls="chip portal"))
        out.append(G.text(px + pw / 2, cy + 204, label, 9, anchor="middle"))
    return "".join(out)


def _flat_map(f):
    """MMGIS: a 2-D map from the globe's own texture, swaths at their lat/lon."""
    fx, fy, fw, fh = flat_rect()
    out = [G.img(GL.flat_png(TEXTURE, L.FRAME_ASSETS, FLAT_BOX), fx, fy, fw, fh,
                 preserve="none", frame=False)]
    lon0, lon1, lat0, lat1 = FLAT_EXT
    grid = []
    for lon in range(-140, -20, 20):
        gx = fx + (lon - lon0) / (lon1 - lon0) * fw
        grid.append("M%.1f,%.1f v%.1f" % (gx, fy, fh))
    for lat in range(-20, 60, 20):
        gy = fy + (lat1 - lat) / (lat1 - lat0) * fh
        grid.append("M%.1f,%.1f h%.1f" % (fx, gy, fw))
    out.append('<path d="%s" stroke="#ffffff" stroke-width="0.8" opacity="0.25"/>'
               % " ".join(grid))
    for k in range(len(SATS)):
        s = shown_in_tools(k, f)
        if s > 0:
            out.append('<g class="layer mmgis" clip-path="url(#jflat)" '
                       'opacity="%.3f">' % s
                       + "".join(quad(q, color, op=0.9, cls="mcell")
                                 for q, color in FLAT_CELLS[k])
                       + "</g>")
    out.append('<path d="M%.1f,%.1f h%.1f v%.1f h%.1f Z" fill="none" '
               'stroke="#3a414a" stroke-width="1.2"/>' % (fx, fy, fw, fh, -fw))
    return "".join(out)


def _tool(f, key, title, verb, rect):
    if f < TOOLS_IN:
        return ""
    x, y, w, h = rect
    a = ramp(f, TOOLS_IN, TOOLS_IN + FADE)
    lit = max(window(f, TOOLS_IN, SCALE_AT - FADE),
              window(f, READ_AT, NEW_AT - FADE),
              window(f, NEW_SHOWN, NEW_SHOWN + 30))
    out = [G.halo(x, y, w, h, strength=lit), '<g opacity="%.3f">' % a,
           G.box(x, y, w, h, "#ffffff"),
           G.text(x + 18, y + 30, title, 15, weight="bold"),
           G.text(x + w - 18, y + 30, verb, 12, fill=MUTED, anchor="end"),
           _pages(f, rect) if key == "portal" else _flat_map(f)]

    # the copies it has to keep -- the problem made visible
    gone = 1.0 - ramp(f, STORE_AT, STORE_AT + 15)
    landed = [k for k in range(len(COPY)) if f >= COPY[k][1]]
    if gone > 0:
        out.append(G.text(x + 22, y + 66, "local copies", 10.5, fill=MUTED,
                          opacity=gone))
        for k in landed:
            sx, sy = stack_slot(rect, k)
            out.append(mini(sx, sy, k, op=gone))
        hot = ramp(f, DIFFICULTY, DIFFICULTY + 12)
        out.append(G.text(x + 22, y + h - 18, "%d cop%s" % (
            len(landed), "y" if len(landed) == 1 else "ies"), 12,
            fill=WARN if hot > 0 else S.ink, weight="bold" if hot > 0 else "normal",
            opacity=gone))
    after = ramp(f, STORE_AT + 10, STORE_AT + 10 + FADE)
    if after > 0:
        reads = ramp(f, READ_AT + 40, READ_AT + 40 + FADE)
        if reads > 0:
            for i, line in enumerate(("reads in place,", "via STAC")):
                out.append(G.text(x + 22, y + 120 + i * 18, line, 12,
                                  fill=L.FLOW, weight="bold", opacity=reads))
        out.append(G.text(x + 22, y + h - 18, "0 copies", 12, fill=L.FLOW,
                          weight="bold", opacity=after))
    out.append("</g>")
    return "".join(out)


def _caption(f):
    out = []
    for i, (start, s) in enumerate(CAPTIONS):
        end = CAPTIONS[i + 1][0] - FADE - 1 if i + 1 < len(CAPTIONS) else TOTAL + FADE
        a = window(f, start, end)
        if a <= 0:
            continue
        x, y, w, h = CAPTION
        out.append('<g class="caption" opacity="%.3f">' % a
                   + S.box(x, y, w, h, L.BUBBLE_BG, stroke=L.BUBBLE_BG, rx=12,
                           sw=1.5, key=("jcap",))
                   + G.text(x + w / 2, y + 36, s, 15, fill=L.BUBBLE_FG,
                            anchor="middle")
                   + "</g>")
    return "".join(out)
