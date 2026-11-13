#!/usr/bin/env python3
"""
The story slide: the journey and the bottleneck, told once, in 45 seconds.

    showcase    a large globe; satellites pass and paint their swaths
    formats     each mission's data is its own shape -- GeoTIFF, NetCDF, HDF5,
                HDF4 -- so "many formats" is something the eye sees at once
    bottleneck  the globe steps aside; data streams off it, from wherever a
                satellite is scanning, into a funnel that queues it behind a
                manual neck: download, convert by hand, copy per tool
    automation  the neck opens into an automated, cloud-native workflow:
                ingest turns every shape into the same circle (COG), stored
                once, indexed in STAC, read in place by the web apps -- while
                the satellites keep passing and their data now flows straight
                through to the people deciding

The queue is the bottleneck slide's (funnel.py); the globe, orbits and
satellites are the journey's (globe.py, journey.py). What is new here is only
the telling: one picture, one transformation, and a shape for every format.
"""
import math

import bottleneck as B
import gen_frames as G
import globe as GL
import layout as L
from funnel import Funnel
from journey import RAMPS, SATS, TEXTURE, ramp, ramp_color, satellite, tag, value, window
from style import S

FPS, FADE = G.FPS, G.FADE
WARN, MUTED = B.WARN, B.MUTED

# ---------------------------------------------------------------- timeline ---
MAX_SECONDS = 45
TOTAL = MAX_SECONDS * FPS                  # 675 frames
GLIDE = (105, 150)        # the showcase globe steps aside for the pipeline
PIPE_IN = 135             # funnel and decision makers fade in
SQUEEZE = 160             # the bottleneck is named
NAME_STATIONS = 240
DECISIONS_WAIT = 320
OPEN_AT = 390             # automation: the neck opens at 26 s
MORPH = 45
FIX_BEAT = 70
CAPTIONS = (
    (0, "NASA, NOAA and commercial satellites watch Earth around the clock, "
        "each in its own format."),
    (SQUEEZE, "All of it squeezes through one manual bottleneck: download, "
              "convert by hand, copy into every tool."),
    (DECISIONS_WAIT, "Decisions wait weeks for the data, so we automated it: "
                     "a cloud-native workflow, end to end."),
    (OPEN_AT + FIX_BEAT, "Actionable decisions in hours, not weeks."),
)
STATION_LIT = [(NAME_STATIONS + 22 * k, DECISIONS_WAIT) for k in range(3)]

# ------------------------------------------------------------------ layout ---
BIG = (800, 430, 300)     # the showcase globe: centre and radius
SMALL = (245, 440, 180)   # ...and where it settles beside the pipeline
ALT = 1.22
MID_Y = 440
SRC_X = SMALL[0] + SMALL[2] + 15
MOUTH_X, NECK_X, NECK_END = 500, 700, 1230
MOUTH_H, NECK_H, OPEN_H = 210, 20, 200
DECIDE_X = 1265
STATIONS = (790, 940, 1090)
PROBLEM = (("Download", "terabytes"), ("Convert", "by hand"), ("Copy", "per tool"))
COPY_STATION = 2
COLUMNS = (("Automated ingest", "to cloud- · optimized · format", "#fff4df"),
           ("Cloud storage", "stored once", "#eef4fb"),
           ("STAC", "indexed · interoperable", L.FILL_STAC),
           ("Web apps", "PORTAL · MMGIS · ArcGIS", L.FILL_PORTAL))
COL_W = 116              # "Cloud storage" overran 108
COL_X = tuple(712 + COL_W / 2 + k * (COL_W + 8) for k in range(4))
INGEST = 0                # the column where every format becomes a COG
CAPTION = B.CAPTION
TITLE = B.TITLE
PROBLEM_TITLE = "The bottleneck: data waits, so decisions wait"
LEGEND_Y = 700
DX = 1300                 # decision makers

# One shape per format; COG is the circle every shape becomes.
# A hexagon was tried for HDF4: at dot size it read as the COG circle, which
# is the one confusion this legend must not allow.
# The journey's four missions, plus a commercial one bought through NASA's
# CSDA programme. Umbra is SAR and TASKED: it images where it is ordered to,
# so its pass is a spotlight -- the beam stays on one scene (Tampa Bay, a
# hurricane coast) while the satellite flies over -- not a swath. SAR also
# looks to the SIDE: the track passes `look` degrees east of the scene and the
# beam slants across to it. NITF is how SAR products like SICD ship.
UMBRA = dict(name="Umbra (CSDA)", fmt="NITF", incl=97.5, half=2.4,
             at=(27.8, -82.6), look=7.0, span=40, spot=4.5, panel="#4b5563")
CAST = SATS[:2] + (UMBRA,) + SATS[2:]          # Umbra flies third: in the showcase
# SAR reads as greyscale backscatter; light enough to stand off the globe.
CAST_RAMPS = RAMPS[:2] + (("#4a5568", "#8a94a6", "#cbd2dc", "#ffffff"),) + RAMPS[2:]
SHAPES = ("square", "triangle", "star", "diamond", "cross")
COG_SHAPE = "circle"
# Dots are see-through, as ONE group: the words and columns behind them stay
# readable, and a packed queue is no darker than a single dot.
DOT_ALPHA = 0.55
# Each satellite's dots take a colour from its own swath's ramp -- sampled so
# no two read alike (NOAA-20's viridis and Terra's greens both go green at .6).
SAT_COLOR = [ramp_color(CAST_RAMPS[k], t)
             for k, t in enumerate((0.62, 0.32, 0.25, 0.55, 0.62))]

# ------------------------------------------------------------------ passes ---
PERIOD, REC_LEN, FIRST_REC = 40, 30, 8
ROWS, COLS = 20, 4
SPOT_ROWS = 6             # a tasked scene is short along track
DRIFT = 11                # degrees west per cycle, as successive orbits drift


def passes(total):
    """Every pass flown in a slide `total` frames long: the cast in turn, each
    orbit drifting west of the last. The response slide runs the same cast."""
    out, k = [], 0
    while FIRST_REC + k * PERIOD + REC_LEN < total - 15:
        s = k % len(CAST)
        sat = CAST[s]
        lat, lon = sat["at"]
        lon -= DRIFT * (k // len(CAST))
        look = sat.get("look", 0.0)
        p = GL.pass_over(None, sat["incl"], (lat, lon + look),
                         math.radians(sat["half"]), math.radians(sat.get("span", 40)))
        a = FIRST_REC + k * PERIOD
        spot = sat.get("spot")
        if spot:
            # one scene, beside the track: rows along it, columns across the
            # beam, centred `look` degrees off-nadir on whichever side the
            # scene is
            mid, h = (p.s0 + p.s1) / 2, math.radians(spot) / 2
            off = min((math.radians(look) * sgn for sgn in (1, -1)),
                      key=lambda u: abs(GL.to_latlon(p.ground(mid, u))[1] - lon))
            scene = (mid - h, mid + h, off - p.half, off + p.half)
            cells = []
            for r in range(SPOT_ROWS):
                sa = scene[0] + (scene[1] - scene[0]) * r / SPOT_ROWS
                sb = scene[0] + (scene[1] - scene[0]) * (r + 1) / SPOT_ROWS
                for c in range(COLS):
                    ua = scene[2] + (scene[3] - scene[2]) * c / COLS
                    ub = scene[2] + (scene[3] - scene[2]) * (c + 1) / COLS
                    q = (p.ground(sa, ua), p.ground(sa, ub), p.ground(sb, ub),
                         p.ground(sb, ua))
                    cells.append((r, c, q, ramp_color(CAST_RAMPS[s], value(k, r, c))))
            rows = SPOT_ROWS
        else:
            scene, rows = None, ROWS
            cells = [(r, c, q, ramp_color(CAST_RAMPS[s], value(k, r, c)))
                     for r, c, q in p.cells(rows, COLS)]
        out.append(dict(sat=s, p=p, scene=scene, rows=rows, spot=bool(spot),
                        rec=(a, a + REC_LEN), cells=cells))
        k += 1
    return out


PASSES = passes(TOTAL)


def globe_at(f):
    """The globe for frame f: showcase-sized, gliding, or settled."""
    t = ramp(f, *GLIDE)
    cx, cy, r = (BIG[i] + (SMALL[i] - BIG[i]) * t for i in range(3))
    return GL.Globe(cx, cy, r, 22, -88)


def sat_s(pz, f):
    a, b = pz["rec"]
    p = pz["p"]
    if f < a - 6 or f > b + 8:
        return None
    return p.s0 + (f - a) * (p.s1 - p.s0) / float(b - a)


# -------------------------------------------------------------------- dots ---
T_EMIT = 14               # frames a dot takes from the swath to the funnel


def _hash(i, salt):
    h = math.sin(i * 12.9898 + salt * 78.233) * 43758.5453
    return h - math.floor(h)


def _emissions():
    """(emit frame, pass index) for every dot: off the scan line, every few
    frames while a satellite records -- every frame once the neck is open."""
    out = []
    for k, pz in enumerate(PASSES):
        a, b = pz["rec"]
        if a < GLIDE[1]:
            continue          # the showcase passes are for looking at
        f = a
        while f < b:
            out.append((f, k))
            f += 2 if f < OPEN_AT else 1
    return out


EMIT = _emissions()
N = len(EMIT)
LANE = [MID_Y - 170 + 340 * _hash(i, 1) for i in range(N)]
FUNNEL = Funnel(SRC_X, MOUTH_X, NECK_X, NECK_END, MID_Y, MOUTH_H, NECK_H, OPEN_H,
                DECIDE_X, OPEN_AT, MORPH, [e + T_EMIT for e, _k in EMIT], LANE,
                ((12, NECK_X, STATIONS[0], False), (22, STATIONS[0], STATIONS[0], False),
                 (14, STATIONS[0], STATIONS[1], False),
                 (24, STATIONS[1], STATIONS[1], False),
                 (14, STATIONS[1], STATIONS[2], False),
                 (10, STATIONS[2], STATIONS[2], True),
                 (16, STATIONS[2], DECIDE_X, True)))


def scan_point(k, f):
    """Canvas point at the middle of pass k's scan line at frame f."""
    return scan_point_on(globe_at(f), PASSES[k], f)


def scan_point_on(gl, pz, f):
    """Where pass pz is scanning at frame f, on globe gl."""
    if pz["spot"]:                # a tasked satellite's data comes from its scene
        s0, s1, u0, u1 = pz["scene"]
        return gl.xy(pz["p"].ground((s0 + s1) / 2, (u0 + u1) / 2))[0]
    s = max(pz["p"].s0, min(pz["p"].s1, sat_s(pz, f) or pz["p"].s0))
    return gl.xy(pz["p"].track(s))[0]


def dot_positions(i, f):
    """[(x, y)] for dot i -- flying off the globe, then wherever the funnel says."""
    e, k = EMIT[i]
    if f < e:
        return []
    if f < e + T_EMIT:
        (x0, y0), t = scan_point(k, e), G.smooth((f - e) / float(T_EMIT))
        return [(x0 + (SRC_X - x0) * t, y0 + (LANE[i] - y0) * t)]
    return FUNNEL.position(i, f)


def shape_of(i, x):
    """A dot's format: its satellite's -- until automated ingest makes it a COG."""
    if FUNNEL.mode[i] == "open" and x >= COL_X[INGEST]:
        return COG_SHAPE
    return SHAPES[PASSES[EMIT[i][1]]["sat"]]


def glyph(shape, x, y, color, r=5.5, cls="dot"):
    if shape == "circle":
        return '<circle class="%s %s" cx="%.1f" cy="%.1f" r="%.1f" fill="%s"/>' % (
            cls, shape, x, y, r - 0.5, color)
    if shape == "square":
        pts = [(x - r * .8, y - r * .8), (x + r * .8, y - r * .8),
               (x + r * .8, y + r * .8), (x - r * .8, y + r * .8)]
    elif shape == "triangle":
        pts = [(x, y - r * 1.1), (x + r, y + r * .75), (x - r, y + r * .75)]
    elif shape == "star":
        pts = [(x + (r * 1.2 if j % 2 == 0 else r * 0.5) * math.sin(math.pi / 5 * j),
                y - (r * 1.2 if j % 2 == 0 else r * 0.5) * math.cos(math.pi / 5 * j))
               for j in range(10)]
    elif shape == "diamond":
        pts = [(x, y - r * 1.1), (x + r, y), (x, y + r * 1.1), (x - r, y)]
    else:
        a, b = r * 1.05, r * 0.4
        pts = [(x - b, y - a), (x + b, y - a), (x + b, y - b), (x + a, y - b),
               (x + a, y + b), (x + b, y + b), (x + b, y + a), (x - b, y + a),
               (x - b, y + b), (x - a, y + b), (x - a, y - b), (x - b, y - b)]
    return '<path class="%s %s" d="M%s Z" fill="%s"/>' % (
        cls, shape, " L".join("%.1f,%.1f" % p for p in pts), color)


# ---------------------------------------------------------------- drawing ----
def _d(pts, close=False):
    return "M" + " L".join("%.1f,%.1f" % p for p in pts) + (" Z" if close else "")


def header_rect(k):
    # 112 tall: the ingest header carries two lines of title and three of
    # "to cloud-optimized format"
    return (COL_X[k] - COL_W / 2, MID_Y - OPEN_H - 122, COL_W, 112)


def ring(gl, p, front, op):
    pts = [p.sat(2 * math.pi * i / 200, ALT) for i in range(201)]
    runs, cur = [], []
    for v in pts:
        if (gl.view(v)[2] >= 0) == front:
            cur.append(gl.xy(v)[0])
        elif cur:
            runs.append(cur)
            cur = []
    if cur:
        runs.append(cur)
    dash = "" if front else ' stroke-dasharray="4 5"'
    return "".join('<path d="%s" fill="none" stroke="#7d8ea8" stroke-width="1.4"'
                   ' opacity="%.3f"%s/>' % (_d(r), op, dash)
                   for r in runs if len(r) > 1)


def _globe(f, out):
    globe_scene(globe_at(f), PASSES, f, out)


def globe_scene(gl, passes, f, out, tags_inward=False):
    """Globe gl with every swath of `passes` flown so far painted on it, and
    whichever satellites are overhead at frame f. `tags_inward` keeps a
    satellite's name over the globe when something sits close to its right."""
    flying = [(k, sat_s(pz, f)) for k, pz in enumerate(passes)]
    flying = [(k, s) for k, s in flying if s is not None]
    for k, _s in flying:
        out.append(ring(gl, passes[k]["p"], False, 0.5))
    href = GL.globe_png(TEXTURE, L.FRAME_ASSETS, GL.Globe(0, 0, BIG[2], 22, -88))
    out.append(G.img(href, gl.cx - gl.r, gl.cy - gl.r, 2 * gl.r, 2 * gl.r,
                     frame=False))
    out.append('<circle cx="%.1f" cy="%.1f" r="%.1f" fill="none" stroke="#9cc4ff" '
               'stroke-width="5" opacity="0.35"/>' % (gl.cx, gl.cy, gl.r + 2))
    # every swath so far stays painted, so coverage builds up as you watch
    for k, pz in enumerate(passes):
        a, b = pz["rec"]
        if f < a:
            continue
        n = pz["rows"]
        rows = max(0, min(n, int((f - a) / float(b - a) * n + 0.999)))
        # older swaths recede, so the globe stays a globe once the eye
        # has moved on to the pipeline
        fade = 0.85 - 0.55 * ramp(f, b, b + 60)
        for r, _c, q, color in pz["cells"]:
            if r < rows:
                pts = [gl.xy(v)[0] for v in q]
                out.append('<path d="%s" fill="%s" stroke="%s" stroke-width="0.5" '
                           'opacity="%.3f"/>' % (_d(pts, True), color, color, fade))
        if pz["spot"]:
            # a tasked scene is framed, so a patch this small still reads
            s0, s1, u0, u1 = pz["scene"]
            ring_pts = [gl.xy(pz["p"].ground(sx, ux))[0]
                        for sx, ux in ((s0, u0), (s0, u1), (s1, u1), (s1, u0))]
            out.append('<path d="%s" fill="none" stroke="#ffffff" stroke-width="1.8" '
                       'opacity="%.3f"/>' % (_d(ring_pts, True), min(1.0, fade + 0.1)))
    for k, s in flying:
        pz = passes[k]
        p, sat = pz["p"], CAST[pz["sat"]]
        a, b = pz["rec"]
        op = min(ramp(f, a - 6, a - 1), 1.0 - ramp(f, b + 2, b + 8))
        out.append(ring(gl, p, True, 0.7 * op))
        pos = p.sat(s, ALT)
        (x, y), _z = gl.xy(pos)
        if a <= f <= b:
            # spotlight: the beam stays on its scene, off to the side, while
            # the satellite moves
            if pz["spot"]:
                s0, s1, u0, u1 = pz["scene"]
                e1, e2 = (gl.xy(p.ground((s0 + s1) / 2, u))[0] for u in (u0, u1))
            else:
                e1, e2 = (gl.xy(p.ground(s, u))[0] for u in (-p.half, p.half))
            out.append('<path d="%s" fill="#ffd27a" opacity="0.28"/>'
                       % _d([(x, y), e1, e2], True))
            out.append('<path d="%s" stroke="#ffd27a" stroke-width="2.4" '
                       'fill="none"/>' % _d([e1, e2]))
        if not gl.hidden(pos):
            (x2, y2), _ = gl.xy(p.sat(s + 0.02, ALT))
            ang = math.degrees(math.atan2(y2 - y, x2 - x)) + 90
            out.append(satellite(x, y, ang, op, sat["panel"]))
            name = "%s · %s" % (sat["name"], sat["fmt"])
            tx = x + 26
            if tags_inward and x > gl.cx:
                tx = x - 26 - (len(name) * 7.2 + 18)       # tag()'s own width
            out.append(tag(tx, y - 20, name, op))


def _pipeline(f, out):
    a = ramp(f, PIPE_IN, PIPE_IN + 2 * FADE)
    if a <= 0:
        return
    m = FUNNEL.morph(f)
    top, bot = FUNNEL.walls(m)
    out.append('<g opacity="%.3f">' % a)
    out.append('<path d="%s" fill="#f1f2f4" opacity="0.8"/>'
               % _d(top + bot[::-1], True))
    for k, (title, sub, fill) in enumerate(COLUMNS):
        ca = ramp(f, OPEN_AT + 18 + 8 * k, OPEN_AT + 38 + 8 * k)
        if ca <= 0:
            continue
        x = COL_X[k]
        lit = window(f, OPEN_AT + FIX_BEAT + 14 * k, OPEN_AT + FIX_BEAT + 30 + 14 * k)
        hx, hy, hw, hh = header_rect(k)
        out.append(G.halo(hx, hy, hw, hh, strength=lit * ca))
        out.append('<g class="column" opacity="%.3f">' % ca
                   + G.box(x - COL_W / 2, MID_Y - OPEN_H + 12, COL_W, 2 * OPEN_H - 24,
                           fill)
                   + G.box(hx, hy, hw, hh, fill)
                   + G.text(x, hy + 28, title.split(" ")[0] if k == 0 else title,
                            12.5, anchor="middle", weight="bold")
                   + (G.text(x, hy + 45, "ingest", 12.5, anchor="middle",
                             weight="bold") if k == 0 else "")
                   + "".join(G.text(x, hy + (64 if k == 0 else 50) + 16 * j, line,
                                    10, fill="#4b5563", anchor="middle")
                             for j, line in enumerate(sub.split(" · ")))
                   + "</g>")
        if k == INGEST:
            # the automation itself: Airflow, turning while the work flows
            out.append('<g opacity="%.3f">' % (ca * 0.9)
                       + G.airflow_group(x, MID_Y, 64, (f - OPEN_AT) * 5.0) + "</g>")
    for key, wall in (("top", top), ("bot", bot)):
        out.append(S.poly(wall, S.ink, sw=3, key=("swall", key, round(m, 2))))
    gone = 1.0 - ramp(f, OPEN_AT, OPEN_AT + 20)
    for k, (l1, l2) in enumerate(PROBLEM):
        if gone <= 0:
            break
        x = STATIONS[k]
        s, e = STATION_LIT[k]
        lit = window(f, s, e) if f >= s else 0.0
        out.append(G.halo(x - 58, MID_Y - 112, 116, 56, strength=lit * gone))
        out.append('<g class="station" opacity="%.3f">' % gone
                   + G.box(x - 58, MID_Y - 112, 116, 56, "#fdecea", stroke=WARN)
                   + G.text(x, MID_Y - 90, l1, 12.5, fill=WARN, anchor="middle",
                            weight="bold")
                   + G.text(x, MID_Y - 72, l2, 10.5, fill=WARN, anchor="middle")
                   + '<path d="M%.1f,%.1f v30" stroke="%s" stroke-width="1.4" '
                   'stroke-dasharray="3 3"/>' % (x, MID_Y - 56, WARN)
                   + "</g>")
    # decision makers, their clock, and what has reached them
    out.append(G.text(DX + 100, MID_Y - 150, "Decision makers", 15, anchor="middle",
                      weight="bold"))
    out.append(G.text(DX + 100, MID_Y - 128, "emergency managers · responders",
                      10, fill=MUTED, anchor="middle"))
    for k in range(3):
        out.append(B.person(DX + 40 + (k % 2) * 60, MID_Y - 60 + k * 70, 1.0,
                            lit=m > 0.5))
    recent = sum(1 for t in FUNNEL.arrivals if f - 8 <= t <= f)
    if recent:
        out.append(G.halo(DX, MID_Y - 100, 200, 220, strength=min(1.0, 0.35 * recent)))
    out.append(B.clock(DX + 30, MID_Y + 190, f, m, open_at=OPEN_AT,
                       morph_frames=MORPH))
    done = sum(1 for t in FUNNEL.arrivals if t <= f)
    out.append(G.text(DX + 66, MID_Y + 250, "%d granules delivered" % done, 12,
                      fill=L.FLOW if m > 0.5 else WARN, weight="bold",
                      anchor="middle"))
    out.append("</g>")


def _legend(f, out):
    """The formats, once: four shapes in, one shape out."""
    a = ramp(f, GLIDE[1], GLIDE[1] + FADE)
    if a <= 0:
        return
    x = SMALL[0] - 150
    items = [(SHAPES[s], CAST[s]["fmt"], SAT_COLOR[s]) for s in range(len(CAST))]
    out.append('<g class="legend" opacity="%.3f">' % a)
    # Each item as wide as its own name, then one even gap. A fixed pitch left
    # "NITF" with twice the air after it that "GeoTIFF" had.
    cx = x
    for shape, fmt, color in items:
        out.append(glyph(shape, cx, LEGEND_Y, color, cls="key"))
        out.append(G.text(cx + 10, LEGEND_Y + 5, fmt, 10))
        cx += 10 + len(fmt) * (10 + G.FONT_BUMP) * S.font_scale * 0.5 + 22
    c = ramp(f, OPEN_AT + FIX_BEAT, OPEN_AT + FIX_BEAT + FADE)
    if c > 0:
        out.append('<g opacity="%.3f">' % c
                   + G.text(x + 52, LEGEND_Y + 34, "→ automated ingest →",
                            10, fill=MUTED)
                   + glyph(COG_SHAPE, x + 214, LEGEND_Y + 29, L.FLOW, cls="key")
                   + G.text(x + 224, LEGEND_Y + 34, "cloud-optimized", 10,
                            fill=L.FLOW, weight="bold")
                   + "</g>")
    out.append("</g>")


def story_svg(f):
    W, H = L.W, L.H
    out = ['<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" '
           'viewBox="0 0 %d %d">' % (W, H, W, H),
           '<rect width="%d" height="%d" fill="%s"/>' % (W, H, S.bg)]
    a = window(f, SQUEEZE, OPEN_AT - FADE)
    if a > 0:
        out.append(G.text(W / 2, 74, PROBLEM_TITLE, 22, fill=WARN, anchor="middle",
                          weight="bold", opacity=a))
    a = ramp(f, OPEN_AT + MORPH / 2, OPEN_AT + MORPH)
    if a > 0:
        out.append(G.text(W / 2, 74, TITLE, 22, anchor="middle", weight="bold",
                          opacity=a))
    _globe(f, out)
    _pipeline(f, out)
    _legend(f, out)
    dots = []
    for i in range(N):
        color = SAT_COLOR[PASSES[EMIT[i][1]]["sat"]]
        for x, y in dot_positions(i, f):
            dots.append(glyph(shape_of(i, x), x, y, color))
    out.append('<g class="dots" opacity="%.2f">%s</g>' % (DOT_ALPHA, "".join(dots)))
    gone = 1.0 - ramp(f, OPEN_AT, OPEN_AT + 20)
    if gone > 0 and f >= SQUEEZE:
        out.append(G.text(MOUTH_X + 20, MID_Y + MOUTH_H + 34,
                          "%d granules waiting" % len(FUNNEL.waiting(f)), 13,
                          fill=WARN, weight="bold",
                          opacity=gone * ramp(f, SQUEEZE, SQUEEZE + FADE)))
    out.append(_caption(f))
    out.append("</svg>")
    return "\n".join(out)


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
                           sw=1.5, key=("scap",))
                   + G.text(x + w / 2, y + 36, s, 15, fill=L.BUBBLE_FG,
                            anchor="middle")
                   + "</g>")
    return "".join(out)
