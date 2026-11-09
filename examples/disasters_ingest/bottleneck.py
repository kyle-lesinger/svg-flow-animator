#!/usr/bin/env python3
"""
The bottleneck slide: data pours in, squeezes through one narrow neck before
anyone can act, and then the neck opens into a cloud-native web architecture.

The neck carries three stations, one per bottleneck, in the order the work
happens -- the copies are made last, once each tool's version exists -- and
the architecture takes their place, in its own order:

    download terabytes   (moving the data)  |  cloud storage, COG: data stays put
    convert and analyze  (time to decision) |  STAC: indexed once, interoperable
    copy per tool        (silos)            |  web apps: PORTAL, MMGIS, ArcGIS

The dots are a queue, computed rather than simulated -- see funnel.py, which
the story slide shares.
"""
import math

import gen_frames as G
import layout as L
from funnel import Funnel
from journey import ramp, window
from style import S

FPS, FADE = G.FPS, G.FADE

# ------------------------------------------------------------------ layout ---
SRC_X = 150                       # dots leave the sources here
MOUTH_X, NECK_X, NECK_END = 380, 620, 1180
MID_Y = 450
MOUTH_H, NECK_H, OPEN_H = 230, 20, 210   # half-heights: funnel mouth, neck, opened
STATIONS = (720, 880, 1040)       # along the neck
DECIDE_X = 1250                   # dots are absorbed by the decision makers here
CAPTION = (300, 796, 1000, 56)
TITLE = ("Data-driven, interoperable, cloud-native web architecture "
         "for actionable decisions")
WARN = "#c0392b"
MUTED = "#6b7280"
# Dots are see-through, as ONE group: the words and columns behind them stay
# readable, and a packed queue is no darker than a single dot.
DOT_ALPHA = 0.55
DOT_COLORS = ("#ed6925", "#21918c", "#d6457f", "#3b528b", "#fbb61a",
              "#5ec962", "#781c6d", "#3f8fd6")

PROBLEM = (("Download", "terabytes"), ("Convert,", "analyze"), ("Copy", "per tool"))
COPY_STATION = 2                  # where a dot becomes one copy per tool
SOLUTION = (("Cloud storage", "cloud-optimized · data stays put", "#eef4fb"),
            ("STAC", "indexed once \u00b7 interoperable", L.FILL_STAC),
            ("Web apps", "PORTAL · MMGIS · ArcGIS", L.FILL_PORTAL))

# ---------------------------------------------------------------- timeline ---
MAX_SECONDS = 30                  # a slide, not a film: the hard ceiling
SQUEEZE = 60                      # "one bottleneck" -- and the line is counted
NAME_STATIONS = 120               # the three stations, named in turn
DECISIONS_WAIT = 190
OPEN_AT = 255                     # the neck opens: the problem has had 17 s
MORPH = 45                        # frames the walls take to swing open
FIX_BEAT = 65                     # each caption of the fix, ~4.3 s
TOTAL = OPEN_AT + 3 * FIX_BEAT - 5          # 445 frames: under MAX_SECONDS
CAPTIONS = (
    (0, "Data pours in from satellites, aircraft, models and partners."),
    (SQUEEZE, "But all of it has to squeeze through one bottleneck."),
    (NAME_STATIONS, "Download terabytes, convert and analyze, then copy into "
                    "every tool."),
    (DECISIONS_WAIT, "By the time it is usable, days to weeks have passed. "
                     "Decisions wait."),
    (OPEN_AT, "We removed the bottleneck with a cloud-native web architecture."),
    (OPEN_AT + FIX_BEAT, "Data stays in the cloud, indexed once in interoperable "
                         "STAC, streamed to every web tool."),
    (OPEN_AT + 2 * FIX_BEAT, "Actionable decisions in hours, not weeks."),
)
STATION_LIT = [(NAME_STATIONS + 22 * k, DECISIONS_WAIT) for k in range(3)]

# ------------------------------------------------------------------- queue ---
SPAWN_EVERY = 3                   # ...and every frame once it opens: a flood
FIRST_SPAWN = -60                 # the stream is already flowing at frame 0
V = 5.0                           # free speed toward the funnel, px/frame
V_OPEN = 11.0                     # speed through the opened architecture
SERVICE = 22                      # the neck lets one dot through this often
MOVE = 10                         # frames for the line to shuffle up one place
DRAIN = 0.4                       # frames between queued dots once it opens
# Through the neck: (frames, x from, x to, split into copies?). Dwelling at a
# station is a segment that goes nowhere.
NECK_PATH = ((12, NECK_X, STATIONS[0], False), (24, STATIONS[0], STATIONS[0], False),
             (14, STATIONS[0], STATIONS[1], False), (24, STATIONS[1], STATIONS[1], False),
             (14, STATIONS[1], STATIONS[2], False), (10, STATIONS[2], STATIONS[2], True),
             (18, STATIONS[2], DECIDE_X, True))


def _hash(i, salt):
    h = math.sin(i * 12.9898 + salt * 78.233) * 43758.5453
    return h - math.floor(h)


SPAWN = (list(range(FIRST_SPAWN, OPEN_AT, SPAWN_EVERY))
         + list(range(OPEN_AT, TOTAL)))
N = len(SPAWN)
LANE = [MID_Y - 180 + 360 * _hash(i, 1) for i in range(N)]
COLOR = [DOT_COLORS[int(_hash(i, 2) * len(DOT_COLORS))] for i in range(N)]

FUNNEL = Funnel(SRC_X, MOUTH_X, NECK_X, NECK_END, MID_Y, MOUTH_H, NECK_H, OPEN_H,
                DECIDE_X, OPEN_AT, MORPH, SPAWN, LANE, NECK_PATH, v=V,
                v_open=V_OPEN, service=SERVICE, drain=DRAIN, move=MOVE)
# The names this slide, and its tests, have always used.
SLOTS, DEP, MODE, ARRIVALS = FUNNEL.slots, FUNNEL.dep, FUNNEL.mode, FUNNEL.arrivals
waiting, morph, inside = FUNNEL.waiting, FUNNEL.morph, FUNNEL.inside
position, arrival, walls = FUNNEL.position, FUNNEL.arrival, FUNNEL.walls


# ---------------------------------------------------------------- drawing ----
def _d(pts, close=False):
    return "M" + " L".join("%.1f,%.1f" % p for p in pts) + (" Z" if close else "")


def header_rect(k):
    """Where column k's words sit: above the opened channel, clear of the flow."""
    return (STATIONS[k] - 66, MID_Y - OPEN_H - 112, 132, 102)


def person(cx, cy, op, lit):
    color = L.FLOW if lit else S.ink
    return ('<g opacity="%.3f">' % op
            + S.circle(cx, cy - 16, 9, fill="#ffffff", stroke=color, sw=2,
                       key=("bhead", cx, cy))
            + S.poly([(cx - 15, cy + 16), (cx - 15, cy + 4), (cx - 8, cy - 4),
                      (cx + 8, cy - 4), (cx + 15, cy + 4), (cx + 15, cy + 16)],
                     color, sw=2, fill="#ffffff", closed=True, key=("bbody", cx, cy))
            + "</g>")


def clock(cx, cy, f, opened, open_at=OPEN_AT, morph_frames=MORPH):
    """Hands turn fast while the problem runs -- time passing -- then settle."""
    days = 1 + int(20 * min(1.0, f / float(open_at)))
    spin = (min(f, open_at) * 18.0) % 360
    out = [S.circle(cx, cy, 24, fill="#ffffff", stroke=S.ink, sw=2, key=("bclock",)),
           '<path d="M%.1f,%.1f L%.1f,%.1f M%.1f,%.1f L%.1f,%.1f" stroke="%s" '
           'stroke-width="2.4" stroke-linecap="round"/>'
           % (cx, cy, cx + 16 * math.sin(math.radians(spin)),
              cy - 16 * math.cos(math.radians(spin)), cx, cy,
              cx + 10 * math.sin(math.radians(spin / 12.0)),
              cy - 10 * math.cos(math.radians(spin / 12.0)), S.ink)]
    out.append(G.text(cx + 36, cy - 4, "time to decision", 11, fill=MUTED))
    a = ramp(f, open_at + morph_frames, open_at + morph_frames + FADE)
    if a < 1:
        v = "%d days" % days if days < 14 else "%d weeks" % (days // 7)
        out.append(G.text(cx + 36, cy + 18, v, 15, fill=WARN, weight="bold",
                          opacity=1 - a))
    if a > 0:
        out.append(G.text(cx + 36, cy + 18, "hours", 15, fill=L.FLOW,
                          weight="bold", opacity=a))
    return "".join(out)


def bottleneck_svg(f):
    W, H = L.W, L.H
    m = ramp(f, OPEN_AT, OPEN_AT + MORPH)
    out = ['<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" '
           'viewBox="0 0 %d %d">' % (W, H, W, H),
           '<rect width="%d" height="%d" fill="%s"/>' % (W, H, S.bg)]

    # --- titles: the problem, then the architecture that solved it
    # one after the other: crossfaded, the two lines sat on top of each other
    a = 1 - ramp(f, OPEN_AT, OPEN_AT + MORPH / 2)
    if a > 0:
        out.append(G.text(W / 2, 80, "The bottleneck: data waits, so decisions "
                          "wait", 22, fill=WARN, anchor="middle", weight="bold",
                          opacity=a))
    a = ramp(f, OPEN_AT + MORPH / 2, OPEN_AT + MORPH)
    if a > 0:
        out.append(G.text(W / 2, 80, TITLE, 22, anchor="middle", weight="bold",
                          opacity=a))

    # --- sources
    for k, name in enumerate(("Satellites", "Aircraft", "Models", "Partners")):
        y = MID_Y - 150 + k * 100
        out.append(G.text(40, y + 5, name, 13, weight="bold"))
        out.append('<circle cx="%.1f" cy="%.1f" r="4" fill="%s"/>'
                   % (SRC_X - 14, y, DOT_COLORS[k * 2]))

    # --- the funnel, opening
    top, bot = walls(m)
    out.append('<path d="%s" fill="#f1f2f4" opacity="0.8"/>'
               % _d(top + bot[::-1], close=True))
    # the opened architecture: each station replaced where it stood
    for k, (title, sub, fill) in enumerate(SOLUTION):
        a = ramp(f, OPEN_AT + 20 + 10 * k, OPEN_AT + 40 + 10 * k)
        if a <= 0:
            continue
        x = STATIONS[k]
        lit = window(f, OPEN_AT + FIX_BEAT + 20 * k, OPEN_AT + FIX_BEAT + 20 + 20 * k)
        # The words go in a header ABOVE the channel's top wall, where no dot
        # can reach (inside() keeps every dot between the walls); the lane
        # below carries the flow. Inside the channel the dots ran over them.
        hx, hy, hw, hh = header_rect(k)
        out.append(G.halo(hx, hy, hw, hh, strength=lit * a))
        out.append('<g class="layer" opacity="%.3f">' % a
                   + G.box(x - 66, MID_Y - OPEN_H + 12, 132, 2 * OPEN_H - 24, fill)
                   + G.box(hx, hy, hw, hh, fill)
                   + G.text(x, hy + 28, title, 14, anchor="middle", weight="bold")
                   + "".join(G.text(x, hy + 50 + 18 * j, line, 11,
                                    fill="#4b5563", anchor="middle")
                             for j, line in enumerate(sub.split(" · ")))
                   + "</g>")
    for key, wall in (("top", top), ("bot", bot)):
        out.append(S.poly(wall, S.ink, sw=3, key=("bwall", key, round(m, 2))))

    # the three stations of the problem, each named in turn
    gone = 1.0 - ramp(f, OPEN_AT, OPEN_AT + 20)
    for k, (a_line, b_line) in enumerate(PROBLEM):
        if gone <= 0:
            break
        x = STATIONS[k]
        s, e = STATION_LIT[k]
        lit = window(f, s, e) if f >= s else 0.0
        out.append(G.halo(x - 58, MID_Y - 112, 116, 56, strength=lit * gone))
        out.append('<g class="station" opacity="%.3f">' % gone
                   + G.box(x - 58, MID_Y - 112, 116, 56, "#fdecea", stroke=WARN)
                   + G.text(x, MID_Y - 90, a_line, 12.5, fill=WARN, anchor="middle",
                            weight="bold")
                   + G.text(x, MID_Y - 72, b_line, 10.5, fill=WARN, anchor="middle")
                   + '<path d="M%.1f,%.1f v%.1f" stroke="%s" stroke-width="1.4" '
                   'stroke-dasharray="3 3"/>' % (x, MID_Y - 56, 30, WARN)
                   + "</g>")

    # --- decision makers
    dx = 1300
    recent = sum(1 for t in ARRIVALS if f - 8 <= t <= f)
    out.append(G.text(dx + 100, MID_Y - 150, "Decision makers", 15, anchor="middle",
                      weight="bold"))
    out.append(G.text(dx + 100, MID_Y - 128, "emergency managers · responders",
                      10, fill=MUTED, anchor="middle"))
    for k in range(3):
        cy = MID_Y - 60 + k * 70
        out.append(person(dx + 40 + (k % 2) * 60, cy, 1.0, lit=m > 0.5))
    if recent:
        out.append(G.halo(dx, MID_Y - 100, 200, 220, strength=min(1.0, 0.35 * recent)))
    out.append(clock(dx + 30, MID_Y + 190, f, m))
    done = sum(1 for t in ARRIVALS if t <= f)
    out.append(G.text(dx + 66, MID_Y + 250, "%d granules delivered" % done, 12,
                      fill=L.FLOW if m > 0.5 else WARN, weight="bold",
                      anchor="middle"))

    # --- the dots, last, so they pass over every station and layer
    dots = []
    for i in range(N):
        for x, y in position(i, f):
            dots.append('<circle cx="%.1f" cy="%.1f" r="4.6" fill="%s"/>'
                        % (x, y, COLOR[i]))
    out.append('<g class="dots" opacity="%.2f">%s</g>' % (DOT_ALPHA, "".join(dots)))

    # how long the line is -- the problem made countable
    q = len(waiting(f))
    if gone > 0 and f >= SQUEEZE:
        out.append(G.text(MOUTH_X + 20, MID_Y + MOUTH_H + 40,
                          "%d granules waiting" % q, 13, fill=WARN, weight="bold",
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
                           sw=1.5, key=("bcap",))
                   + G.text(x + w / 2, y + 36, s, 15, fill=L.BUBBLE_FG,
                            anchor="middle")
                   + "</g>")
    return "".join(out)
