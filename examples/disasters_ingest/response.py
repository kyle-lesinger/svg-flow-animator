#!/usr/bin/env python3
"""
The response slide: the whole network, end to end, in 15 seconds.

Observation to action. Satellites paint their swaths on a globe and their data
leaves in its own format; automated ingest makes every format cloud-optimized,
cloud storage keeps it once, STAC indexes it; from STAC the same granule
reaches every destination at once -- a web dashboard, an analysis tool, a news
or event article, a lesson, and any other tool or API that speaks STAC, which
is what interoperable means -- and from each of those it reaches the people:
the Disasters community, decision makers, emergency managers, responders.
Nothing here is a problem being solved: it is the solved system, running, so
the eye can follow one observation all the way to the people who act on it.

The globe, its cast of satellites and the format shapes are the story's
(story.py); the first four destinations are the uses slide's (uses.py). What
is new is the picture: everything on screen at once, no caption, and a granule
that splits at STAC into one copy per destination, then pulses on from each
destination to the people, so "the same data, to everyone" is watched rather
than read. Few granules -- a quarter of what the story sends -- so each one
can be followed.

Each dot's place is a pure function of the frame, as on every slide: any frame
renders alone and in any order.
"""
import math

import bottleneck as B
import gen_frames as G
import globe as GL
import layout as L
import story as ST
import uses as U
from journey import ramp, window
from style import S

FPS, FADE = G.FPS, G.FADE
WARN, MUTED = ST.WARN, ST.MUTED

# ---------------------------------------------------------------- timeline ---
MAX_SECONDS = 15                      # the whole network, in a quarter of a minute
MAX_TOTAL = MAX_SECONDS * FPS         # 225 frames; TOTAL is derived, below
NETWORK_IN = (4, 18)                  # the pipeline settles in; the cards just after
EMIT_EVERY = 12                       # frames between granules while a satellite
                                      # records: a few per pass, each followable
T_EMIT = 10                           # frames from the swath to the channel
V = 12.0                              # px/frame along the channel and the routes
FAN_T = 18                            # frames to bend out of STAC towards a card
PULSE_T = 10                          # frames from a destination to the people
END_HOLD = 15                         # after the last pulse lands: the picture, still
LIT_COLUMNS = 24                      # the pipeline's headers, lit one after another
LIT_CARDS = 80                        # the destinations, lit one after another
LIT_PEOPLE = 150                      # the people
TITLE = "Observation to action: one network, end to end"

# ------------------------------------------------------------------ layout ---
GLOBE = (235, 470, 175)               # centre and radius
ENTRY_X = 450                         # where a granule joins the channel
MID_Y = 480                           # the channel's centre line
COL_W, COL_GAP = 116, 10              # "Cloud storage" overran 112 (story.py)
COL_X = tuple(470 + COL_W / 2 + k * (COL_W + COL_GAP) for k in range(3))
COLUMNS = (("Automated ingest", "to cloud- · optimized · format", "#fff4df"),
           ("Cloud storage", "stored once", "#eef4fb"),
           ("STAC", "indexed · interoperable", L.FILL_STAC))
INGEST, STORE, STAC = 0, 1, 2
HEADER = (236, 112)                   # y and height of the column headers
COL_BODY = (360, 250)                 # y and height of the column bodies
SPLIT_X = COL_X[STAC] + COL_W / 2     # a granule leaves STAC as one copy per destination
BAND = (440, 372, SPLIT_X - 440, 216)  # the channel: x, y, w, h
LANE_SPREAD = 80                      # granules ride the channel this far off centre
ROUTE_SPREAD = 40                     # the routes leave STAC this far apart
BEND_X = 960                          # a route runs level from here into its card
CARD_X, CARD_W, CARD_H = 990, 450, 136
CARD_Y = (100, 252, 404, 556, 708)
CARD_MID = tuple(y + CARD_H / 2 for y in CARD_Y)
SHOT = (12, 12, 176, 112)             # a card's picture: dx, dy, w, h
TEXT_DX = 200                         # a card's words start here
# The uses slide's four, and a fifth: whatever else speaks STAC. The data is
# pulled into it, not copied for it -- that is the interoperability claim.
API = ("Other tools & APIs", "any STAC client · any platform", None, None, None)
DESTS = U.DESTS + (API,)
N_ROUTES = len(DESTS)
INTEROP = "interoperable · open standard"
PEOPLE = (1476, 100, 118, 744)        # who acts on it, beside every destination
HEADING_Y = 88
COMMUNITY = "Disasters community"
ROLES = ("decision makers", "emergency", "managers", "responders", "partners")
HOURS = ("act in hours,", "not weeks")
BADGE_Y = 626                         # STAC's "single source of truth", under its column
LEGEND = (70, 745)

# ------------------------------------------------------------------ passes ---
# The cast runs a little past the slide's own length so a satellite is still
# recording when the last granule lands; nothing it records is emitted.
PASSES = ST.passes(MAX_TOTAL + 25)
VIEW = GL.Globe(GLOBE[0], GLOBE[1], GLOBE[2], 22, -88)

# A granule's whole trip, in frames: swath to channel, channel to STAC, the
# bend out of STAC, the level run into the cards, the pulse on to the people.
# Nothing is emitted that cannot finish before the hold at the end.
TRANSIT = (T_EMIT + int(math.ceil((SPLIT_X - ENTRY_X) / V)) + FAN_T
           + int(math.ceil((CARD_X - BEND_X) / V)) + PULSE_T)
LAST_EMIT = MAX_TOTAL - 1 - END_HOLD - TRANSIT


def _hash(i, salt):
    h = math.sin(i * 12.9898 + salt * 78.233) * 43758.5453
    return h - math.floor(h)


def _emissions():
    """(emit frame, pass index) for every granule: off the scan line, a few
    times while a satellite records, until the last that can land."""
    out = []
    for k, pz in enumerate(PASSES):
        a, b = pz["rec"]
        out.extend((f, k) for f in range(a, b, EMIT_EVERY) if f <= LAST_EMIT)
    return out


EMIT = _emissions()
N = len(EMIT)
LANE = [MID_Y - LANE_SPREAD + 2 * LANE_SPREAD * _hash(i, 1) for i in range(N)]
SAT = [PASSES[k]["sat"] for _e, k in EMIT]
COLOR = [ST.SAT_COLOR[s] for s in SAT]


def times(i):
    """(emitted, joins the channel, leaves STAC, runs level, lands) for granule i."""
    e = EMIT[i][0]
    t1 = e + T_EMIT
    t2 = t1 + (SPLIT_X - ENTRY_X) / V
    t3 = t2 + FAN_T
    return e, t1, t2, t3, t3 + (CARD_X - BEND_X) / V


ARRIVAL = [times(i)[4] for i in range(N)]
# The slide ends a fixed hold after the last pulse reaches the people --
# derived, like the uses slide's, so the frame left on screen is the finished
# picture exactly.
TOTAL = int(math.ceil(max(ARRIVAL) + PULSE_T)) + END_HOLD


def updates(f):
    """Granules landed by frame f -- on every destination, since each lands on all."""
    return sum(1 for t in ARRIVAL if t <= f)


def reached_people(f):
    """Granules whose pulse has reached the people by frame f."""
    return sum(1 for t in ARRIVAL if t + PULSE_T <= f)


def route_start(r):
    return (SPLIT_X, MID_Y + (r - (N_ROUTES - 1) / 2.0) * ROUTE_SPREAD)


def bend(p0, r, u):
    """u of the way along the bend from p0 (at STAC's edge) to where route r
    runs level into its card."""
    y1 = CARD_MID[r]
    return U._cubic(p0, (p0[0] + 110, p0[1]), (BEND_X - 110, y1), (BEND_X, y1), u)


def positions(i, f):
    """[(x, y, shape, route)] for granule i at frame f: one glyph in its
    satellite's shape until automated ingest makes it cloud-optimized, then
    one circle -- and from STAC on, one circle per destination."""
    e, t1, t2, t3, t4 = times(i)
    if f < e or f >= t4:
        return []
    shape = ST.SHAPES[SAT[i]]
    if f < t1:
        x0, y0 = ST.scan_point_on(VIEW, PASSES[EMIT[i][1]], e)
        t = G.smooth((f - e) / float(T_EMIT))
        return [(x0 + (ENTRY_X - x0) * t, y0 + (LANE[i] - y0) * t, shape, None)]
    if f < t2:
        x = ENTRY_X + V * (f - t1)
        return [(x, LANE[i], ST.COG_SHAPE if x >= COL_X[INGEST] else shape, None)]
    if f < t3:
        u = G.smooth((f - t2) / float(FAN_T))
        return [bend((SPLIT_X, LANE[i]), r, u) + (ST.COG_SHAPE, r)
                for r in range(N_ROUTES)]
    x = BEND_X + V * (f - t3)
    return [(x, CARD_MID[r], ST.COG_SHAPE, r) for r in range(N_ROUTES)]


def dots(f):
    """Every granule glyph on screen at frame f: (granule, x, y, shape, route)."""
    return [(i,) + p for i in range(N) for p in positions(i, f)]


def pulses(f):
    """Every pulse on its way from a destination to the people at frame f:
    (granule, x, y, route). One per destination, the moment a granule lands."""
    x0, x1 = CARD_X + CARD_W, PEOPLE[0] - 10
    out = []
    for i, t in enumerate(ARRIVAL):
        if t <= f < t + PULSE_T:
            u = G.smooth((f - t) / float(PULSE_T))
            out.extend((i, x0 + (x1 - x0) * u, CARD_MID[r], r) for r in range(N_ROUTES))
    return out


# ---------------------------------------------------------------- drawing ----
def header_rect(k):
    return (COL_X[k] - COL_W / 2, HEADER[0], COL_W, HEADER[1])


def card_rect(r):
    return (CARD_X, CARD_Y[r], CARD_W, CARD_H)


def shot_rect(r):
    x, y, _w, _h = card_rect(r)
    return (x + SHOT[0], y + SHOT[1], SHOT[2], SHOT[3])


def badge_rect():
    bw = len(U.SOURCE_OF_TRUTH) * 8.6 + 30
    return (COL_X[STAC] - bw / 2, BADGE_Y, bw, 26)


def route(r, n=40):
    """Route r as drawn: the bend out of STAC, then level into its card."""
    p0 = route_start(r)
    return [bend(p0, r, i / float(n)) for i in range(n + 1)] + [(CARD_X, CARD_MID[r])]


def _band(out, a):
    """The channel the pipeline sits across: open, end to end."""
    x, y, w, h = BAND
    out.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" rx="24" '
               'fill="#f1f2f4" opacity="%.3f"/>' % (x, y, w, h, 0.8 * a))
    for key, yy in (("top", y), ("bot", y + h)):
        out.append(S.poly([(x, yy), (x + w, yy)], S.ink, sw=3, opacity=a,
                          key=("rwall", key)))


def _routes(out, a):
    x0, x1 = CARD_X + CARD_W, PEOPLE[0]
    for r in range(N_ROUTES):
        out.append(S.poly(route(r), L.FLOW, sw=4, opacity=0.6 * a, key=("rroute", r)))
        # ...and on from the destination to the people
        out.append(S.poly([(x0, CARD_MID[r]), (x1, CARD_MID[r])], L.FLOW, sw=3,
                          opacity=0.6 * a, key=("rlink", r)))


def _columns(f, out, a):
    for k, (title, sub, fill) in enumerate(COLUMNS):
        x = COL_X[k]
        hx, hy, hw, hh = header_rect(k)
        lit = window(f, LIT_COLUMNS + 14 * k, LIT_COLUMNS + 34 + 14 * k)
        out.append(G.halo(hx, hy, hw, hh, strength=lit * a))
        out.append('<g class="column" opacity="%.3f">' % a
                   + G.box(x - COL_W / 2, COL_BODY[0], COL_W, COL_BODY[1], fill)
                   + G.box(hx, hy, hw, hh, fill)
                   + G.text(x, hy + 28, title.split(" ")[0] if k == INGEST else title,
                            12.5, anchor="middle", weight="bold")
                   + (G.text(x, hy + 45, "ingest", 12.5, anchor="middle",
                             weight="bold") if k == INGEST else "")
                   + "".join(G.text(x, hy + (64 if k == INGEST else 50) + 16 * j, line,
                                    10, fill="#4b5563", anchor="middle")
                             for j, line in enumerate(sub.split(" · ")))
                   + "</g>")
    # inside them: the automation turning, the store, the catalogue
    out.append('<g opacity="%.3f">' % (0.9 * a)
               + G.airflow_group(COL_X[INGEST], MID_Y, 64, f * 5.0) + "</g>")
    out.append('<g opacity="%.3f">' % a
               + G.cylinder(COL_X[STORE], MID_Y, w=54, h=60)
               + G.img(L.A_STAC, COL_X[STAC] - 46, MID_Y - 26, 92, 52)
               + "</g>")
    bx, by, bw, bh = badge_rect()
    out.append('<g class="badge" opacity="%.3f">' % a
               + '<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" rx="13" '
               'fill="#eaf7ec"/>' % (bx, by, bw, bh)
               + G.box(bx, by, bw, bh, "#eaf7ec", stroke=L.FLOW, rx=13)
               + G.text(bx + bw / 2, by + 18, U.SOURCE_OF_TRUTH, 12, fill=L.FLOW,
                        anchor="middle", weight="bold")
               + "</g>")


def _card(r, f, out, a):
    title, what, _work, href, anchor = DESTS[r]
    x, y, w, h = card_rect(r)
    sx, sy, sw, sh = shot_rect(r)
    fresh = sum(1 for t in ARRIVAL if f - 10 < t <= f)
    lit = window(f, LIT_CARDS + 10 * r, LIT_CARDS + 36 + 10 * r)
    out.append(G.halo(x, y, w, h, strength=a * max(lit, min(1.0, 0.8 * fresh))))
    n = updates(f)
    body = [G.box(x, y, w, h, "#ffffff")]
    if href:
        body.append(G.img(href, sx, sy, sw, sh, preserve=anchor + " slice", frame=False))
    else:
        # no page to show: the data is pulled through the API, wherever it is used
        body += [G.box(sx, sy, sw, sh, "#eef4fb"),
                 G.text(sx + sw / 2, sy + 46, "STAC API", 18, anchor="middle",
                        weight="bold"),
                 G.text(sx + sw / 2, sy + 68, "open standard", 11, fill=MUTED,
                        anchor="middle"),
                 G.text(sx + sw / 2, sy + 86, "pull, don't copy", 11, fill=MUTED,
                        anchor="middle")]
    # the latest granules on the page: what an update looks like
    for i, j in enumerate(range(max(0, n - 8), n)):
        body.append('<path d="M%.1f,%.1f h14 v14 h-14 Z" fill="%s" '
                    'stroke="#ffffff" stroke-width="1.5"/>'
                    % (sx + 6 + 17 * i, sy + sh - 20, COLOR[j]))
    body.append('<path d="M%.1f,%.1f h%.1f v%.1f h%.1f Z" fill="none" '
                'stroke="#3a414a" stroke-width="1.2"/>' % (sx, sy, sw, sh, -sw))
    tx = x + TEXT_DX
    body += [G.text(tx, y + 36, title, 17, weight="bold"),
             G.text(tx, y + 60, what, 12.5, fill=MUTED),
             G.text(tx, y + 92, INTEROP if href is None else U.UP_TO_DATE, 13,
                    fill=L.FLOW, weight="bold"),
             G.text(tx, y + 114, "%d update%s" % (n, "" if n == 1 else "s"), 12,
                    fill=MUTED)]
    out.append('<g class="card" opacity="%.3f">%s</g>' % (a, "".join(body)))


def _people(f, out, a):
    """Who acts on it, beside every destination: lit once data has reached them."""
    x, y, w, h = PEOPLE
    just = sum(1 for t in ARRIVAL if f - 8 < t + PULSE_T <= f)
    lit = window(f, LIT_PEOPLE, LIT_PEOPLE + 40)
    out.append(G.halo(x, y, w, h, strength=a * max(lit, min(1.0, 0.6 * just))))
    out.append(G.text(x + w, HEADING_Y, COMMUNITY, 14, anchor="end", weight="bold",
                      opacity=a))
    body = [G.box(x, y, w, h, "#ffffff")]
    body += [G.text(x + w / 2, y + 26 + 16 * j, line, 10, fill=MUTED, anchor="middle")
             for j, line in enumerate(ROLES)]
    got = reached_people(f) > 0
    body += [B.person(x + 30 + (k % 2) * 50, y + 250 + k * 95, 1.0, lit=got)
             for k in range(5)]
    body += [G.text(x + w / 2, y + h - 34 + 18 * j, line, 11.5, fill=L.FLOW,
                    anchor="middle", weight="bold") for j, line in enumerate(HOURS)]
    out.append('<g class="people" opacity="%.3f">%s</g>' % (a, "".join(body)))


def _legend(out, a):
    """The formats, once: five shapes in, one shape out."""
    x, y = LEGEND
    out.append('<g class="legend" opacity="%.3f">' % a)
    cx = x
    for s, sat in enumerate(ST.CAST):
        fmt = sat["fmt"]
        out.append(ST.glyph(ST.SHAPES[s], cx, y, ST.SAT_COLOR[s], cls="key"))
        out.append(G.text(cx + 10, y + 5, fmt, 10))
        cx += 10 + len(fmt) * (10 + G.FONT_BUMP) * S.font_scale * 0.5 + 22
    out.append(G.text(x + 52, y + 34, "→ automated ingest →", 10, fill=MUTED)
               + ST.glyph(ST.COG_SHAPE, x + 214, y + 29, L.FLOW, cls="key")
               + G.text(x + 224, y + 34, "cloud-optimized", 10, fill=L.FLOW,
                        weight="bold"))
    out.append("</g>")


def response_svg(f):
    W, H = L.W, L.H
    out = ['<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" '
           'viewBox="0 0 %d %d">' % (W, H, W, H),
           '<rect width="%d" height="%d" fill="%s"/>' % (W, H, S.bg)]
    out.append(G.text(W / 2, 66, TITLE, 22, anchor="middle", weight="bold"))
    ST.globe_scene(VIEW, PASSES, f, out, tags_inward=True)
    a = ramp(f, *NETWORK_IN)
    b = ramp(f, NETWORK_IN[0] + 6, NETWORK_IN[1] + 6)
    if a > 0:
        _band(out, a)
        if b > 0:
            _routes(out, b)          # under the columns, the cards and the people
        _columns(f, out, a)
        _legend(out, a)
    if b > 0:
        for r in range(N_ROUTES):
            _card(r, f, out, b)
        _people(f, out, b)
    # the granules, last: over the channel, the columns and the routes
    body = "".join(ST.glyph(shape, x, y, COLOR[i])
                   for i, x, y, shape, _r in dots(f))
    out.append('<g class="dots" opacity="%.2f">%s</g>' % (ST.DOT_ALPHA, body))
    body = "".join('<circle cx="%.1f" cy="%.1f" r="4.5" fill="%s" stroke="#ffffff" '
                   'stroke-width="1.2"/>' % (x, y, L.FLOW)
                   for _i, x, y, _r in pulses(f))
    out.append('<g class="pulses" opacity="0.9">%s</g>' % body)
    out.append("</svg>")
    return "\n".join(out)
