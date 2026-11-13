#!/usr/bin/env python3
"""
The standards slide: from inconsistent formats to one standard, deployed into
every user's application, in about 40 seconds.

    showcase     the story's globe; satellites pass and paint their swaths,
                 each mission's data its own shape -- GeoTIFF, NetCDF, NITF,
                 HDF5, HDF4 -- so "inconsistent formats" is seen at once
    bottleneck   briefly: inconsistent formats mean manual work -- download,
                 convert by hand, copy per tool -- and the queue backs up
    standard     the neck opens into scalable, cloud-native ingest that turns
                 every shape into the one circle (cloud-optimized), stored
                 once, indexed in STAC: an open standard any tool can read
    deployment   from STAC's edge every granule fans out as one copy per
                 application -- PORTAL, MMGIS, ArcGIS -- which read it directly

The story slide (story.py) ends on decision makers; this one ends on the
applications, so there is no "Web apps" column: the apps ARE the destinations,
as cards on the right, and the fan out of STAC is the deployment. Manual-path
copies keep their format shape all the way to the cards -- the manual path
never standardised anything -- and only automated ingest makes a circle.

The globe, cast and shapes are the story's; the queue is funnel.py's; the fan
and the cards follow the response slide. Every dot's place is a pure function
of the frame, so any frame renders alone and in any order.
"""
import math

import bottleneck as B
import gen_frames as G
import globe as GL
import layout as L
import story as ST
import uses as U
from funnel import Funnel
from journey import ramp, window
from style import S

FPS, FADE = G.FPS, G.FADE
WARN, MUTED = B.WARN, B.MUTED

# ---------------------------------------------------------------- timeline ---
MAX_SECONDS = 40
MAX_TOTAL = MAX_SECONDS * FPS             # 600 frames; TOTAL is derived, below
GLIDE = ST.GLIDE                          # the showcase globe steps aside
PIPE_IN = 135                             # funnel, routes and the app cards fade in
SQUEEZE = 160                             # the bottleneck is named
NAME_STATIONS = 190
OPEN_AT = SQUEEZE + 8 * FPS               # 280: the bottleneck has had 8 s
MORPH = 45
FIX_BEAT = 70
STAC_BEAT = OPEN_AT + FIX_BEAT            # 350: the open standard
DEPLOY_AT = OPEN_AT + 120                 # 400: deployed into every application
END_HOLD = 10                             # after the last copy lands: the picture, still
CAPTIONS = (
    (0, "NASA, NOAA and commercial satellites, each delivering data in its own format."),
    (SQUEEZE, "Inconsistent formats mean manual work: download, convert by hand, "
              "copy into every tool."),
    (OPEN_AT, "Scalable, cloud-native ingest converts every format to one standard: "
              "cloud-optimized, stored once."),
    (STAC_BEAT, "Indexed in STAC, an open standard, so any compatible tool reads the "
                "same data in place."),
    (DEPLOY_AT, "From one interoperable catalog, data deploys into every user's "
                "application: PORTAL, MMGIS, ArcGIS."),
)
STATION_LIT = [(NAME_STATIONS + 16 * k, OPEN_AT - FADE) for k in range(3)]
PROBLEM_TITLE = "Inconsistent data: every format needs its own handling"
TITLE = "One standard, every tool: scalable, interoperable, compatible"

# ------------------------------------------------------------------ layout ---
BIG, SMALL = ST.BIG, ST.SMALL
MID_Y = 440
SRC_X = SMALL[0] + SMALL[2] + 15          # 440
MOUTH_X, NECK_X = 480, 640
MOUTH_H, NECK_H, OPEN_H = 210, 20, 200
STATIONS = (720, 850, 980)
PROBLEM = (("Download", "terabytes"), ("Convert", "by hand"), ("Copy", "per tool"))
# No "Web apps" column: the applications are the destinations, on the right.
COLUMNS = (("Automated ingest", "scalable · cloud-native · one format", "#fff4df"),
           ("Cloud storage", "stored once · cloud-optimized", "#eef4fb"),
           ("STAC", "open standard · interoperable", L.FILL_STAC))
INGEST, STORE, STAC = 0, 1, 2
COL_W, COL_GAP = 116, 8
COL_X = tuple(660 + COL_W / 2 + k * (COL_W + COL_GAP) for k in range(3))
SPLIT_X = COL_X[STAC] + COL_W / 2         # 1024: a granule leaves STAC as one copy per app
NECK_END = SPLIT_X
ROUTE_SPREAD = 40                         # the drawn routes leave STAC this far apart
BEND_K = 60                               # how far a route's bend reaches, in x
BEND_X = 1130                             # a route runs level from here into its card
CARD_X, CARD_W, CARD_H = 1150, 420, 136
CARD_Y = (172, 372, 572)
CARD_MID = tuple(y + CARD_H / 2 for y in CARD_Y)
SHOT = (12, 12, 176, 112)                 # a card's picture: dx, dy, w, h
TEXT_DX = 200                             # a card's words start here
# (name, what it is, picture, its anchor). ArcGIS has no page to show: its
# card carries the ArcGIS Online and Desktop marks instead.
APPS = (("PORTAL", "Disasters web portal", L.A_SHOT_HOME, "xMinYMin"),
        ("MMGIS", "analysis & mapping tool", L.A_SHOT_VIZ, "xMidYMin"),
        ("ArcGIS", "Online · Desktop · services", None, None))
N_APPS = len(APPS)
BY_HAND = "converted by hand"             # a card's status while the neck is shut...
DIRECT = "reads STAC directly"            # ...and once the standard is in place
ROUTE_GREY = "#9aa1ab"
CAPTION = B.CAPTION
LEGEND_Y = 700

# ------------------------------------------------------------------ passes ---
# The cast runs past the slide's own length so a satellite is still recording
# when the last copy lands; nothing it records then is emitted.
PASSES = ST.passes(MAX_TOTAL + 25)


def globe_at(f):
    """The globe for frame f: showcase-sized, gliding, or settled."""
    t = ramp(f, *GLIDE)
    cx, cy, r = (BIG[i] + (SMALL[i] - BIG[i]) * t for i in range(3))
    return GL.Globe(cx, cy, r, 22, -88)


# -------------------------------------------------------------------- dots ---
T_EMIT = 14                               # frames from the swath to the funnel
V, V_OPEN = 5.0, 11.0
FAN_T = 18                                # frames to bend out of STAC towards a card
# A granule's longest trip once the neck is open: swath to funnel, funnel to
# STAC, the bend, the level run into its card. Nothing is emitted that cannot
# land before the hold at the end.
TRANSIT = (T_EMIT + int(math.ceil((SPLIT_X - SRC_X) / V_OPEN)) + FAN_T
           + int(math.ceil((CARD_X - BEND_X) / V_OPEN)))
LAST_EMIT = MAX_TOTAL - 1 - END_HOLD - TRANSIT


def _emissions():
    """(emit frame, pass index) for every dot: off the scan line, every few
    frames while a satellite records -- oftener once the neck is open, though
    not as often as the story's, since every one becomes three on the right."""
    out = []
    for k, pz in enumerate(PASSES):
        a, b = pz["rec"]
        if a < GLIDE[1]:
            continue                      # the showcase passes are for looking at
        f = a
        while f < b and f <= LAST_EMIT:
            out.append((f, k))
            f += 4 if f < OPEN_AT else 3
    return out


EMIT = _emissions()
N = len(EMIT)
LANE = [MID_Y - 170 + 340 * ST._hash(i, 1) for i in range(N)]
SAT = [PASSES[k]["sat"] for _e, k in EMIT]
COLOR = [ST.SAT_COLOR[s] for s in SAT]
# Through the neck: (frames, x from, x to, split?). Dwelling at a station is a
# segment that goes nowhere. Nothing splits here: "copy per tool" is the fan
# at STAC's edge, in both worlds.
NECK_PATH = ((12, NECK_X, STATIONS[0], False), (22, STATIONS[0], STATIONS[0], False),
             (14, STATIONS[0], STATIONS[1], False), (24, STATIONS[1], STATIONS[1], False),
             (14, STATIONS[1], STATIONS[2], False), (10, STATIONS[2], STATIONS[2], False),
             (16, STATIONS[2], SPLIT_X, False))
FUNNEL = Funnel(SRC_X, MOUTH_X, NECK_X, NECK_END, MID_Y, MOUTH_H, NECK_H, OPEN_H,
                SPLIT_X, OPEN_AT, MORPH, [e + T_EMIT for e, _k in EMIT], LANE,
                NECK_PATH, v=V, v_open=V_OPEN)
# When each dot reaches STAC's edge, in either mode: the funnel's "arrival".
AT_STAC = [FUNNEL.arrival(i) for i in range(N)]
LANDS = [t + FAN_T + (CARD_X - BEND_X) / V_OPEN for t in AT_STAC]
ARRIVAL = sorted(LANDS)
LANDED_ORDER = sorted(range(N), key=lambda i: LANDS[i])
# The slide ends a fixed hold after the last copy lands -- derived, so the
# frame left on screen is the finished picture exactly.
TOTAL = int(math.ceil(max(LANDS))) + END_HOLD
assert TOTAL <= MAX_TOTAL, (TOTAL, MAX_TOTAL)


def updates(f):
    """Granules landed by frame f -- on every app, since each lands on all."""
    return sum(1 for t in ARRIVAL if t <= f)


def exit_y(i):
    """Where dot i leaves STAC: a manual copy on the centre line, an automated
    one on its own lane, inside the channel as open as it is by then."""
    if FUNNEL.mode[i] == "neck":
        return MID_Y
    return FUNNEL.inside(SPLIT_X, LANE[i], FUNNEL.morph(AT_STAC[i]))


def route_start(r):
    return (SPLIT_X, MID_Y + (r - (N_APPS - 1) / 2.0) * ROUTE_SPREAD)


def bend(p0, r, u):
    """u of the way along the bend from p0 (at STAC's edge) to where route r
    runs level into its card."""
    y1 = CARD_MID[r]
    return U._cubic(p0, (p0[0] + BEND_K, p0[1]), (BEND_X - BEND_K, y1), (BEND_X, y1), u)


def route(r, n=40):
    """Route r as drawn: the bend out of STAC, then level into its card."""
    p0 = route_start(r)
    return [bend(p0, r, i / float(n)) for i in range(n + 1)] + [(CARD_X, CARD_MID[r])]


def scan_point(k, f):
    return ST.scan_point_on(globe_at(f), PASSES[k], f)


def positions(i, f):
    """[(x, y, shape, route)] for dot i at frame f: one glyph in its
    satellite's shape -- a circle only once automated ingest has made it
    cloud-optimized -- and from STAC's edge on, one glyph per application."""
    e, k = EMIT[i]
    if f < e:
        return []
    own = ST.SHAPES[SAT[i]]
    if f < e + T_EMIT:
        (x0, y0), t = scan_point(k, e), G.smooth((f - e) / float(T_EMIT))
        return [(x0 + (SRC_X - x0) * t, y0 + (LANE[i] - y0) * t, own, None)]
    t2 = AT_STAC[i]
    if f < t2:
        auto = FUNNEL.mode[i] == "open"
        return [(x, y, ST.COG_SHAPE if auto and x >= COL_X[INGEST] else own, None)
                for x, y in FUNNEL.position(i, f)]
    if f >= LANDS[i]:
        return []
    shape = ST.COG_SHAPE if FUNNEL.mode[i] == "open" else own
    if f < t2 + FAN_T:
        u = G.smooth((f - t2) / float(FAN_T))
        return [bend((SPLIT_X, exit_y(i)), r, u) + (shape, r) for r in range(N_APPS)]
    x = BEND_X + V_OPEN * (f - t2 - FAN_T)
    return [(x, CARD_MID[r], shape, r) for r in range(N_APPS)]


def dots(f):
    """Every dot glyph on screen at frame f: (dot, x, y, shape, route)."""
    return [(i,) + p for i in range(N) for p in positions(i, f)]


# ---------------------------------------------------------------- drawing ----
def _d(pts, close=False):
    return "M" + " L".join("%.1f,%.1f" % p for p in pts) + (" Z" if close else "")


def header_rect(k):
    # 112 tall: the ingest header carries two lines of title and three of sub
    return (COL_X[k] - COL_W / 2, MID_Y - OPEN_H - 122, COL_W, 112)


def station_rect(k):
    return (STATIONS[k] - 58, MID_Y - 112, 116, 56)


def card_rect(r):
    return (CARD_X, CARD_Y[r], CARD_W, CARD_H)


def shot_rect(r):
    x, y, _w, _h = card_rect(r)
    return (x + SHOT[0], y + SHOT[1], SHOT[2], SHOT[3])


def _pipeline(f, out, a):
    m = FUNNEL.morph(f)
    top, bot = FUNNEL.walls(m)
    out.append('<path d="%s" fill="#f1f2f4" opacity="%.3f"/>'
               % (_d(top + bot[::-1], True), 0.8 * a))
    for k, (title, sub, fill) in enumerate(COLUMNS):
        ca = a * ramp(f, OPEN_AT + 18 + 8 * k, OPEN_AT + 38 + 8 * k)
        if ca <= 0:
            continue
        x = COL_X[k]
        hx, hy, hw, hh = header_rect(k)
        lit = window(f, OPEN_AT + FIX_BEAT + 14 * k, OPEN_AT + FIX_BEAT + 30 + 14 * k)
        out.append(G.halo(hx, hy, hw, hh, strength=lit * ca))
        out.append('<g class="column" opacity="%.3f">' % ca
                   + G.box(x - COL_W / 2, MID_Y - OPEN_H + 12, COL_W, 2 * OPEN_H - 24,
                           fill)
                   + G.box(hx, hy, hw, hh, fill)
                   + G.text(x, hy + 28, title.split(" ")[0] if k == INGEST else title,
                            12.5, anchor="middle", weight="bold")
                   + (G.text(x, hy + 45, "ingest", 12.5, anchor="middle",
                             weight="bold") if k == INGEST else "")
                   + "".join(G.text(x, hy + (64 if k == INGEST else 50) + 16 * j, line,
                                    10, fill="#4b5563", anchor="middle")
                             for j, line in enumerate(sub.split(" · ")))
                   + "</g>")
        if k == INGEST:
            # the automation itself: Airflow, turning while the work flows
            out.append('<g opacity="%.3f">' % (ca * 0.9)
                       + G.airflow_group(x, MID_Y, 64, (f - OPEN_AT) * 5.0) + "</g>")
        elif k == STORE:
            out.append('<g opacity="%.3f">' % ca + G.cylinder(x, MID_Y, w=54, h=60)
                       + "</g>")
        else:
            out.append('<g opacity="%.3f">' % ca
                       + G.img(L.A_STAC, x - 46, MID_Y - 26, 92, 52) + "</g>")
    for key, wall in (("top", top), ("bot", bot)):
        out.append(S.poly(wall, S.ink, sw=3, opacity=a, key=("dwall", key, round(m, 2))))
    gone = a * (1.0 - ramp(f, OPEN_AT, OPEN_AT + 20))
    for k, (l1, l2) in enumerate(PROBLEM):
        if gone <= 0:
            break
        x = STATIONS[k]
        sx, sy, sw, sh = station_rect(k)
        s, e = STATION_LIT[k]
        lit = window(f, s, e) if f >= s else 0.0
        out.append(G.halo(sx, sy, sw, sh, strength=lit * gone))
        out.append('<g class="station" opacity="%.3f">' % gone
                   + G.box(sx, sy, sw, sh, "#fdecea", stroke=WARN)
                   + G.text(x, MID_Y - 90, l1, 12.5, fill=WARN, anchor="middle",
                            weight="bold")
                   + G.text(x, MID_Y - 72, l2, 10.5, fill=WARN, anchor="middle")
                   + '<path d="M%.1f,%.1f v30" stroke="%s" stroke-width="1.4" '
                   'stroke-dasharray="3 3"/>' % (x, MID_Y - 56, WARN)
                   + "</g>")


def _routes(f, out, a):
    """From STAC's edge into every application: grey while copies are made by
    hand, the flow's green once the standard is in place."""
    m = FUNNEL.morph(f)
    for r in range(N_APPS):
        pts = route(r)
        if m < 1:
            out.append(S.poly(pts, ROUTE_GREY, sw=3, opacity=0.6 * a * (1 - m),
                              key=("droute", r)))
        if m > 0:
            out.append(S.poly(pts, L.FLOW, sw=4, opacity=0.6 * a * m,
                              key=("droute", r)))


def _card(r, f, out, a):
    title, what, href, anchor = APPS[r]
    x, y, w, h = card_rect(r)
    sx, sy, sw, sh = shot_rect(r)
    m = FUNNEL.morph(f)
    fresh = sum(1 for t in ARRIVAL if f - 10 < t <= f)
    lit = window(f, DEPLOY_AT + 10 * r, DEPLOY_AT + 36 + 10 * r)
    out.append(G.halo(x, y, w, h, strength=a * max(lit, min(1.0, 0.8 * fresh))))
    n = updates(f)
    body = [G.box(x, y, w, h, "#ffffff")]
    if href:
        body.append(G.img(href, sx, sy, sw, sh, preserve=anchor + " slice", frame=False))
    else:
        # no page to show: the two ArcGIS marks
        body += [G.box(sx, sy, sw, sh, "#eef4fb"),
                 G.img(L.A_ARCGIS_ONLINE, sx + 10, sy + 12, 72, 72, frame=False),
                 G.img(L.A_ARCGIS_DESKTOP, sx + 94, sy + 12, 72, 72, frame=False)]
    # the latest granules on the page: what an update looks like
    for i, j in enumerate(range(max(0, n - 8), n)):
        body.append('<path d="M%.1f,%.1f h14 v14 h-14 Z" fill="%s" '
                    'stroke="#ffffff" stroke-width="1.5"/>'
                    % (sx + 6 + 17 * i, sy + sh - 20, COLOR[LANDED_ORDER[j]]))
    body.append('<path d="M%.1f,%.1f h%.1f v%.1f h%.1f Z" fill="none" '
                'stroke="#3a414a" stroke-width="1.2"/>' % (sx, sy, sw, sh, -sw))
    tx = x + TEXT_DX
    body += [G.text(tx, y + 36, title, 17, weight="bold"),
             G.text(tx, y + 60, what, 12.5, fill=MUTED)]
    if m < 1:
        body.append(G.text(tx, y + 92, BY_HAND, 13, fill=WARN, weight="bold",
                           opacity=1 - m))
    if m > 0:
        body.append(G.text(tx, y + 92, DIRECT, 13, fill=L.FLOW, weight="bold",
                           opacity=m))
    body.append(G.text(tx, y + 114, "%d update%s" % (n, "" if n == 1 else "s"), 12,
                       fill=MUTED))
    out.append('<g class="card" opacity="%.3f">%s</g>' % (a, "".join(body)))


def _legend(f, out):
    """The formats, once: five shapes in, one shape out."""
    a = ramp(f, GLIDE[1], GLIDE[1] + FADE)
    if a <= 0:
        return
    x = SMALL[0] - 150
    out.append('<g class="legend" opacity="%.3f">' % a)
    cx = x
    for s, sat in enumerate(ST.CAST):
        fmt = sat["fmt"]
        out.append(ST.glyph(ST.SHAPES[s], cx, LEGEND_Y, ST.SAT_COLOR[s], cls="key"))
        out.append(G.text(cx + 10, LEGEND_Y + 5, fmt, 10))
        cx += 10 + len(fmt) * (10 + G.FONT_BUMP) * S.font_scale * 0.5 + 22
    c = ramp(f, STAC_BEAT, STAC_BEAT + FADE)
    if c > 0:
        out.append('<g opacity="%.3f">' % c
                   + G.text(x + 52, LEGEND_Y + 34, "→ automated ingest →", 10, fill=MUTED)
                   + ST.glyph(ST.COG_SHAPE, x + 214, LEGEND_Y + 29, L.FLOW, cls="key")
                   + G.text(x + 224, LEGEND_Y + 34, "cloud-optimized", 10, fill=L.FLOW,
                            weight="bold")
                   + "</g>")
    out.append("</g>")


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
                           sw=1.5, key=("dcap",))
                   + G.text(x + w / 2, y + 36, s, 15, fill=L.BUBBLE_FG, anchor="middle")
                   + "</g>")
    return "".join(out)


def standards_svg(f):
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
    ST.globe_scene(globe_at(f), PASSES, f, out, tags_inward=True)
    a = ramp(f, PIPE_IN, PIPE_IN + 2 * FADE)
    if a > 0:
        _pipeline(f, out, a)
        _routes(f, out, a)               # under the cards
        for r in range(N_APPS):
            _card(r, f, out, a)
    _legend(f, out)
    body = "".join(ST.glyph(shape, x, y, COLOR[i]) for i, x, y, shape, _r in dots(f))
    out.append('<g class="dots" opacity="%.2f">%s</g>' % (ST.DOT_ALPHA, body))
    gone = 1.0 - ramp(f, OPEN_AT, OPEN_AT + 20)
    if gone > 0 and f >= SQUEEZE:
        out.append(G.text(MOUTH_X + 20, MID_Y + MOUTH_H + 34,
                          "%d granules waiting" % len(FUNNEL.waiting(f)), 13,
                          fill=WARN, weight="bold",
                          opacity=gone * ramp(f, SQUEEZE, SQUEEZE + FADE)))
    out.append(_caption(f))
    out.append("</svg>")
    return "\n".join(out)
