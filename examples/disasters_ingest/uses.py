#!/usr/bin/env python3
"""
The uses slide: what the data is FOR -- a web dashboard, an analysis tool, a
news or event article, a lesson -- and how it got there before STAC, and after.

Before: no catalog. Each application is its own silo: its own lane, its own
copy of the data, its own schedule, and a person in the way doing the hand-off
by hand (download, convert, screenshot, re-upload). A person takes longer per
granule than the gap between granules, so every line grows, and the apps drift
out of step with each other. After: one system drives them all -- STAC, the
single source of truth for the data, and one editor (TinaCMS) that reaches
every app. The separate copies glide together into it, the parallel lanes bend
into one fan out of it, and the four hand-offs become one person at one
editor: not automated, simplified. The same data reaches every app.

Like the bottleneck's, the queue is computed, not simulated: each dot's place
is a pure function of the frame, so any frame renders alone and in any order.
A granule's place is the distance it still has to go to its card. That is the
same on a lane and on the fan wherever the two run level, so a line waiting at
a person stays put while the route bends around it.
"""
import math

import gen_frames as G
import layout as L
from bottleneck import DOT_COLORS
from journey import ramp, window
from style import S

FPS, FADE = G.FPS, G.FADE

# ------------------------------------------------------------------ layout ---
SYSTEM = (50, 262, 290, 400)          # after: the one system...
STAC_BOX = (70, 300, 250, 190)        # ...STAC for the data...
TINA_BOX = (70, 508, 250, 132)        # ...one editor for every app
COPY_X = 185                          # before: each app's own copy, on its lane
SILO_X = 250                          # before: a lane starts here
CARD_X, CARD_W, CARD_H = 1010, 550, 150
CARD_Y = (120, 290, 460, 630)
LANE_Y = tuple(y + CARD_H / 2 for y in CARD_Y)
SHOT = (12, 12, 216, 126)             # a card's picture: dx, dy, w, h
TEXT_DX = 246                         # a card's words start here
BEND_X = 560                          # the fan runs level from here to the card
PERSON_X = 760                        # where the hand-off happens
EDITOR_Y = 712                        # after: the one editor, under the system
FRONT = 46                            # the head of the line waits outside the ring
SPACING = 16                          # between granules waiting in line
CAPTION = (230, 806, 1140, 62)
WARN, MUTED, GRAY = "#c0392b", "#6b7280", "#9aa1ab"
# (title, what it is, what a person does by hand today, picture, its anchor)
DESTS = (
    ("Web dashboard", "Disasters PORTAL home", "download · re-tile · upload",
     L.A_SHOT_HOME, "xMinYMin"),
    ("Analysis tool", "MMGIS · notebooks · GIS", "download · convert · load",
     L.A_SHOT_VIZ, "xMidYMin"),
    ("News & event article", "PORTAL event story", "screenshot · crop · paste",
     L.A_SHOT_STORY, "xMidYMin"),
    ("Teach & educate", "PORTAL training", "package · rebuild the lesson",
     L.A_SHOT_TRAINING, "xMidYMin"),
)
N_ROUTES = len(DESTS)
# Not automation: a person still edits, once, in one place. The words say so.
SIMPLIFIED = "simplified · via STAC"
SOURCE_OF_TRUTH = "single source of truth"
UP_TO_DATE = "same data · up to date"

# ---------------------------------------------------------------- timeline ---
MAX_SECONDS = 30                      # a slide, not a film: the hard ceiling
FIRST_EMIT = 20                       # the apps and their lanes, alone
EMIT_EVERY = 30                       # by hand: a granule every two seconds...
SERVICE = (54, 66, 60, 72)            # ...and a person takes longer than that
LANE_OFFSET = (0, 11, 4, 17)          # each silo on its own schedule
AUTOMATE_AT = 240                     # 16 s of the problem
MORPH = 30                            # frames the switch to one system takes
DRAIN = 3                             # frames between backlog granules released
AUTO_EVERY = 24                       # one system: a granule every 24 frames --
                                      # enough to read as flow, few enough to read
FROM_STAC = 4                         # granules sent from STAC, then the slide ends
END_HOLD = 12                         # after the last lands: its card's glow fades
V, V_AUTO = 9.0, 18.0                 # px/frame: by hand, from the one system
MOVE = 8                              # frames for the line to shuffle up a place
CAPTIONS = (
    (0, "Before STAC, every app kept its own copy, and people carried data to "
        "each by hand."),
    (105, "Each hand-off is a queue: the work piles up, and every audience "
          "waits days."),
    (AUTOMATE_AT, "Now one system drives them all: STAC for the data, one "
                  "editor (TinaCMS) for every app."),
    (AUTOMATE_AT + 75, "One source of truth: the same data in every "
                        "dashboard, analysis, article and lesson."),
)


# ------------------------------------------------------------------ routes ---
def _cubic(p0, c1, c2, p1, t):
    u = 1 - t
    return (u ** 3 * p0[0] + 3 * u * u * t * c1[0] + 3 * u * t * t * c2[0] + t ** 3 * p1[0],
            u ** 3 * p0[1] + 3 * u * u * t * c1[1] + 3 * u * t * t * c2[1] + t ** 3 * p1[1])


def card_rect(r):
    return (CARD_X, CARD_Y[r], CARD_W, CARD_H)


def _fan(r):
    """The system to card r: a bend out of it, then level into the card."""
    sx, sy, sw, sh = SYSTEM
    y0 = sy + sh / 2 + (r - (N_ROUTES - 1) / 2.0) * 40
    y1 = LANE_Y[r]
    p0, p1 = (sx + sw, y0), (BEND_X, y1)
    pts = [_cubic(p0, (p0[0] + 130, y0), (BEND_X - 130, y1), p1, i / 40.0)
           for i in range(41)]
    return pts + [(CARD_X, y1)]


def _cumulative(pts):
    out = [0.0]
    for a, b in zip(pts, pts[1:]):
        out.append(out[-1] + math.hypot(b[0] - a[0], b[1] - a[1]))
    return out


FAN = [_fan(r) for r in range(N_ROUTES)]
FAN_CUM = [_cumulative(p) for p in FAN]
D_FAN = [c[-1] for c in FAN_CUM]
D_LANE = CARD_X - SILO_X              # every lane is level, and as long
E_PERSON = CARD_X - PERSON_X          # still to go, at the person...
E_FRONT = E_PERSON + FRONT            # ...and at the head of their line


def _along(r, d):
    """The point d px along fan route r."""
    pts, cum = FAN[r], FAN_CUM[r]
    d = max(0.0, min(d, cum[-1]))
    for i in range(1, len(cum)):
        if d <= cum[i]:
            t = (d - cum[i - 1]) / ((cum[i] - cum[i - 1]) or 1.0)
            a, b = pts[i - 1], pts[i]
            return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)
    return pts[-1]


def point(r, e, m):
    """Where route r is with e px still to go: m=0 on its own lane, m=1 on the
    fan out of the one system, in between while one becomes the other."""
    lx, ly = CARD_X - min(e, D_LANE), LANE_Y[r]
    if m <= 0:
        return (lx, ly)
    fx, fy = _along(r, D_FAN[r] - min(e, D_FAN[r]))
    if m >= 1:
        return (fx, fy)
    return (lx + (fx - lx) * m, ly + (fy - ly) * m)


def route(r, m, n=60):
    """Route r's polyline, m of the way from its own lane to the fan."""
    top = D_LANE + (D_FAN[r] - D_LANE) * m
    return [point(r, top * (1 - i / float(n)), m) for i in range(n + 1)]


# ---------------------------------------------------------------- schedule ---
HAND = list(range(FIRST_EMIT, AUTOMATE_AT - 30, EMIT_EVERY))
# new granules leave the one system once it is there -- not mid-switch, from
# where the lanes' starts are still gliding across it
AUTO = [AUTOMATE_AT + MORPH + k * AUTO_EVERY for k in range(FROM_STAC)]
N_GRANULES = len(HAND) + len(AUTO)
COLOR = [DOT_COLORS[(g * 3) % len(DOT_COLORS)] for g in range(N_GRANULES)]


def emit_at(r, g):
    """When granule g sets off for card r. By hand each silo fetches it on its
    own schedule; from one system it goes to every app at once."""
    return HAND[g] + LANE_OFFSET[r] if g < len(HAND) else AUTO[g - len(HAND)]


def _schedule(r):
    """
    Per granule on route r: dict(emit, start, done, rel).

    start/done: the person's work on it, if they got to it before the
    automation. rel: when the automation released it, if they did not. A
    granule a person was still working on is released too -- the person goes.
    """
    out, free, k = [], -10 ** 9, 0
    for g in range(N_GRANULES):
        emit = emit_at(r, g)
        s = dict(emit=emit, start=None, done=None, rel=None)
        if g < len(HAND):
            start = max(emit + (D_LANE - E_FRONT) / V, free)
            if start < AUTOMATE_AT:
                s["start"] = start
                free = start + SERVICE[r]
                if free <= AUTOMATE_AT:
                    s["done"] = free
            if s["done"] is None:
                s["rel"] = AUTOMATE_AT + MORPH / 2.0 + DRAIN * k
                k += 1
        out.append(s)
    return out


SCHED = [_schedule(r) for r in range(N_ROUTES)]


def _leaves_line(s):
    """When a granule stops waiting in line: its person starts, or it is released."""
    if s["start"] is not None:
        return s["start"]
    if s["rel"] is not None:
        return s["rel"]
    return s["emit"]                  # from the one system: never queues


def _rank(r, g, f):
    """Places ahead of granule g, fractional while the line shuffles up."""
    n = 0.0
    for s in SCHED[r][:g]:
        t = _leaves_line(s)
        if t > f:
            n += 1
        elif f - t < MOVE:
            n += 1 - (f - t) / float(MOVE)
    return n


def _slot(r, g, f):
    """Still to go at granule g's place in line."""
    return E_FRONT + SPACING * _rank(r, g, f)


def _queued(r, g, f):
    return max(D_LANE - V * (f - SCHED[r][g]["emit"]), _slot(r, g, f))


def _at_person(s, f):
    """Still to go while a person has it: stepping up from the head of the line."""
    return E_FRONT - FRONT * min(1.0, (f - s["start"]) / 6.0)


def remaining(r, g, f):
    """How far granule g still has to go to card r at frame f; None if it is
    not on its route (not yet set off, or delivered)."""
    s = SCHED[r][g]
    if f < s["emit"]:
        return None
    if s["start"] is None and s["rel"] is None:          # from the one system
        e = D_FAN[r] - V_AUTO * (f - s["emit"])
    elif f < _leaves_line(s):
        e = _queued(r, g, f)
    elif s["done"] is not None:                          # by hand, finished
        e = _at_person(s, f) if f < s["done"] else E_PERSON - V * (f - s["done"])
    elif s["start"] is not None:                         # in hand when released
        e = _at_person(s, f) if f < s["rel"] else E_PERSON - V_AUTO * (f - s["rel"])
    else:                                                # released from the line
        e = _queued(r, g, s["rel"]) - V_AUTO * (f - s["rel"])
    return None if e <= 0 else e


def arrival(r, g):
    s = SCHED[r][g]
    if s["start"] is None and s["rel"] is None:
        return s["emit"] + D_FAN[r] / V_AUTO
    if s["done"] is not None:
        return s["done"] + E_PERSON / V
    if s["start"] is not None:
        return s["rel"] + E_PERSON / V_AUTO
    return s["rel"] + _queued(r, g, s["rel"]) / V_AUTO


ARRIVALS = [sorted(arrival(r, g) for g in range(N_GRANULES)) for r in range(N_ROUTES)]
# The slide is as long as its story: it ends once the last granule from STAC
# has reached every app. It plays once, so that last frame is what stays on
# screen -- every app holding the same data, nothing in flight.
TOTAL = int(math.ceil(max(a[-1] for a in ARRIVALS))) + END_HOLD


def gone(f):
    """0 while people carry the data, 1 once one system drives every app."""
    return ramp(f, AUTOMATE_AT, AUTOMATE_AT + MORPH)


def words_out(f):
    """Words of the old world: out over the first half of the switch..."""
    return 1 - ramp(f, AUTOMATE_AT, AUTOMATE_AT + MORPH / 2)


def words_in(f):
    """...and the new world's in over the second, so the two never overlap."""
    return ramp(f, AUTOMATE_AT + MORPH / 2, AUTOMATE_AT + MORPH)


def dots(f):
    """[(route, granule, x, y)] for every granule on screen at frame f."""
    m, out = gone(f), []
    for r in range(N_ROUTES):
        for g in range(N_GRANULES):
            e = remaining(r, g, f)
            if e is not None:
                out.append((r, g) + point(r, e, m))
    return out


def in_service(r, f):
    """(granule, 0..1 done) the person on route r is working on, or None."""
    for g, s in enumerate(SCHED[r]):
        if s["start"] is None or f < s["start"]:
            continue
        end = s["done"] if s["done"] is not None else s["rel"]
        if f < end:
            return g, (f - s["start"]) / float(SERVICE[r])
    return None


def waiting(r, f):
    """Granules standing in line for route r's person at frame f."""
    return [g for g, s in enumerate(SCHED[r])
            if (s["start"] is not None or s["rel"] is not None)
            and s["emit"] <= f < _leaves_line(s)
            and _slot(r, g, f) >= D_LANE - V * (f - s["emit"])]


def updates(r, f):
    return sum(1 for t in ARRIVALS[r] if t <= f)


# --------------------------------------------------------- text and zones ----
def tag_rect(r):
    """The hand-off's words, above its route -- where no granule ever goes."""
    y = CARD_Y[r] + CARD_H / 2
    w = max(len(DESTS[r][2]), 9) * 8.6 + 30
    return (PERSON_X - w / 2, y - 76, w, 32)


def word_zones(f):
    """Every rect holding words drawn at frame f, which no granule may cross:
    the slide's tests check the dots against these. Per frame, because the two
    worlds put words in different places -- the one system's sit across the
    old lanes, and are only drawn once those lanes are gone."""
    zones = [tag_rect(r) for r in range(N_ROUTES)]
    zones.append((L.W / 2 - 420, 36, 840, 44))          # the title
    zones += [(CARD_X + TEXT_DX - 6, y, CARD_W - TEXT_DX + 6, CARD_H)
              for y in CARD_Y]
    zones.append(CAPTION)
    if gone(f) < 1:
        zones.append((COPY_X - 80, 120, 160, 28))        # "a copy per app"
        for r in range(N_ROUTES):                        # "N waiting"
            zones.append((PERSON_X - 160, LANE_Y[r] + 20, 110, 20))
    if words_in(f) > 0:
        sx, sy, sw, sh = SYSTEM
        zones.append((sx, sy - 40, sw, 32))              # "One system"
        zones.append(badge_rect())                       # STAC's badge
        tx, ty, tw, th = TINA_BOX
        zones.append((tx + 120, ty + 36, tw - 120, 72))  # what TinaCMS is
    return zones


# ---------------------------------------------------------------- drawing ----
def person(cx, cy, key):
    """Someone in the way. Seeded on `key`, not position: it drifts as it goes."""
    return (S.circle(cx, cy - 22, 12, fill="#ffffff", stroke=S.ink, sw=2.4,
                     key=("uhead", key))
            + S.poly([(cx - 20, cy + 22), (cx - 20, cy + 6), (cx - 11, cy - 5),
                      (cx + 11, cy - 5), (cx + 20, cy + 6), (cx + 20, cy + 22)],
                     S.ink, sw=2.4, fill="#ffffff", closed=True, key=("ubody", key)))


def progress(cx, cy, t, op):
    """A ring filling while the person works -- flat: it changes every frame."""
    t = max(0.0, min(0.999, t))
    a = 2 * math.pi * t
    x, y = cx + 34 * math.sin(a), cy - 34 * math.cos(a)
    return ('<g opacity="%.3f"><circle cx="%.1f" cy="%.1f" r="34" fill="none" '
            'stroke="#f3c7c2" stroke-width="5"/>'
            '<path d="M%.1f,%.1f A34,34 0 %d 1 %.1f,%.1f" fill="none" stroke="%s" '
            'stroke-width="5" stroke-linecap="round"/></g>'
            % (op, cx, cy, cx, cy - 34, 1 if t > 0.5 else 0, x, y, WARN))


def _system(f):
    """
    Before: a copy of the data per app, one on each lane. After: those copies
    merged into one system -- STAC for the data, TinaCMS for the content.

    Moved and scaled by transforms, never by re-placing geometry: the sketch is
    seeded on geometry, and would boil as it moved.
    """
    m = gone(f)
    sx, sy, sw, sh = SYSTEM
    cx, cy = sx + sw / 2, sy + sh / 2
    out = []
    fade = 1 - ramp(f, AUTOMATE_AT + MORPH / 2, AUTOMATE_AT + MORPH)
    if fade > 0:
        t = G.smooth(m)
        out.append(G.text(COPY_X, 140, "a copy per app", 14, fill=MUTED,
                          anchor="middle", weight="bold", opacity=1 - m))
        for r in range(N_ROUTES):
            out.append('<g class="copy" opacity="%.3f" transform="translate(%.1f,%.1f)">'
                       % (fade, (cx - COPY_X) * t, (cy - LANE_Y[r]) * t)
                       + G.cylinder(COPY_X, LANE_Y[r], w=54, h=60) + "</g>")
    a = ramp(f, AUTOMATE_AT + MORPH / 2, AUTOMATE_AT + MORPH)
    if a > 0:
        x, y, w, h = STAC_BOX
        tx, ty, tw, th = TINA_BOX
        k = 0.85 + 0.15 * a
        out.append(G.text(cx, sy - 16, "One system", 17, anchor="middle",
                          weight="bold", opacity=a))
        out.append('<g class="system" opacity="%.3f" transform="translate(%.1f,%.1f) '
                   'scale(%.4f) translate(%.1f,%.1f)">' % (a, cx, cy, k, -cx, -cy)
                   + G.box(sx, sy, sw, sh, "#ffffff")
                   + G.box(x, y, w, h, L.FILL_STAC)
                   + G.img(L.A_STAC, x + 24, y + 22, w - 48, 104)
                   + G.img(L.A_VEDA, x + (w - 130) / 2, y + 134, 130, 38)
                   + G.box(tx, ty, tw, th, "#fff4ee")
                   + G.img(L.A_TINA, tx + 14, ty + 16, 100, 100)
                   + G.text(tx + 126, ty + 58, "TinaCMS", 15, weight="bold")
                   + G.text(tx + 126, ty + 82, "one editor", 12, fill=MUTED)
                   + G.text(tx + 126, ty + 100, "for every app", 12, fill=MUTED)
                   + _badge()
                   + "</g>")
        # the four hand-offs, become one person at one editor: simplified
        out.append('<g class="editor" opacity="%.3f">' % a
                   + person(cx, EDITOR_Y, "editor") + "</g>")
    return "".join(out)


def badge_rect():
    """STAC's badge, straddling the top edge of its box."""
    x, y, w, _h = STAC_BOX
    bw = len(SOURCE_OF_TRUTH) * 8.6 + 30
    return (x + (w - bw) / 2, y - 13, bw, 26)


def _badge():
    """Solid underneath: a sketched fill is hatched, and the STAC box's edge
    showed through the words."""
    bx, by, bw, bh = badge_rect()
    return ('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" rx="13" '
            'fill="#eaf7ec"/>' % (bx, by, bw, bh)
            + G.box(bx, by, bw, bh, "#eaf7ec", stroke=L.FLOW, rx=13)
            + G.text(bx + bw / 2, by + 18, SOURCE_OF_TRUTH, 12, fill=L.FLOW,
                     anchor="middle", weight="bold"))


def _lanes(f):
    """Before: the silos, kept apart. Gone once one system drives them."""
    a = 1 - gone(f)
    if a <= 0:
        return ""
    d = " ".join("M60,%.1f H%.1f" % ((LANE_Y[r] + LANE_Y[r + 1]) / 2, CARD_X - 24)
                 for r in range(N_ROUTES - 1))
    return ('<path class="silo" d="%s" stroke="#c4c9d0" stroke-width="1.6" '
            'stroke-dasharray="8 7" fill="none" opacity="%.3f"/>' % (d, 0.9 * a))


# Each route's granules in the order they reach its card.
ORDER = [sorted(range(N_GRANULES), key=lambda g, r=r: arrival(r, g))
         for r in range(N_ROUTES)]


def _delivered(r, j):
    """The granule that was route r's j-th delivery."""
    return ORDER[r][j]


def _card(r, f):
    title, what, _work, href, anchor = DESTS[r]
    x, y, w, h = card_rect(r)
    sx, sy, sw, sh = x + SHOT[0], y + SHOT[1], SHOT[2], SHOT[3]
    m = gone(f)
    fresh = sum(1 for t in ARRIVALS[r] if f - 10 < t <= f)
    out = [G.halo(x, y, w, h, strength=min(1.0, 0.8 * fresh)),
           G.box(x, y, w, h, "#ffffff")]
    out.append(G.img(href, sx, sy, sw, sh, preserve=anchor + " slice",
                     frame=False))
    # the latest granules on the page: what an update looks like
    n = updates(r, f)
    for i, j in enumerate(range(max(0, n - 8), n)):
        out.append('<path d="M%.1f,%.1f h14 v14 h-14 Z" fill="%s" '
                   'stroke="#ffffff" stroke-width="1.5"/>'
                   % (sx + 6 + 17 * i, sy + sh - 20, COLOR[_delivered(r, j)]))
    out.append('<path d="M%.1f,%.1f h%.1f v%.1f h%.1f Z" fill="none" '
               'stroke="#3a414a" stroke-width="1.2"/>' % (sx, sy, sw, sh, -sw))
    tx = x + TEXT_DX
    out.append(G.text(tx, y + 40, title, 17, weight="bold"))
    out.append(G.text(tx, y + 66, what, 12.5, fill=MUTED))
    a, b = words_out(f), words_in(f)
    if a > 0:
        out.append(G.text(tx, y + 104, "by hand · days behind", 13, fill=WARN,
                          weight="bold", opacity=a))
    if b > 0:
        out.append(G.text(tx, y + 104, UP_TO_DATE, 13, fill=L.FLOW,
                          weight="bold", opacity=b))
    n = updates(r, f)
    out.append(G.text(tx, y + 128, "%d update%s" % (n, "" if n == 1 else "s"),
                      12, fill=MUTED))
    return "".join(out)


def _route_line(r, f):
    m = gone(f)
    pts = route(r, m)
    out = [S.poly(pts, GRAY, sw=2.5, opacity=1 - 0.7 * m, key=("uroute", r))]
    if m > 0:
        out.append(S.poly(pts, L.FLOW, sw=4, opacity=0.75 * m, key=("uflow", r)))
    return "".join(out)


def _hand_off(r, f):
    """The person on route r, their work, and the words saying what it is."""
    cy = CARD_Y[r] + CARD_H / 2
    m = gone(f)
    out = []
    tx, ty, tw, th = tag_rect(r)
    a, b = words_out(f), words_in(f)
    if a > 0:
        out.append('<g opacity="%.3f">' % a
                   + G.box(tx, ty, tw, th, "#fdecea", stroke=WARN, rx=14)
                   + G.text(PERSON_X, ty + 22, DESTS[r][2], 12.5, fill=WARN,
                            anchor="middle", weight="bold")
                   + "</g>")
    if m < 1:
        work = in_service(r, f)
        out.append('<g class="person" opacity="%.3f" transform="translate(0,%.1f)">'
                   % (1 - m, 24 * m) + person(PERSON_X, cy, r) + "</g>")
        if work is not None:
            out.append(progress(PERSON_X, cy, work[1], 1 - m))
    if b > 0:
        out.append('<g opacity="%.3f">' % b
                   + G.box(tx, ty, tw, th, "#eaf7ec", stroke=L.FLOW, rx=14)
                   + G.text(PERSON_X, ty + 22, SIMPLIFIED, 12.5, fill=L.FLOW,
                            anchor="middle", weight="bold")
                   + "</g>")
    return "".join(out)


def uses_svg(f):
    W, H = L.W, L.H
    m = gone(f)
    out = ['<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" '
           'viewBox="0 0 %d %d">' % (W, H, W, H),
           '<rect width="%d" height="%d" fill="%s"/>' % (W, H, S.bg)]
    # the title says which world we are in; one line, then the other
    a = words_out(f)
    if a > 0:
        out.append(G.text(W / 2, 66, "Before STAC: every application on its "
                          "own", 22, fill=WARN, anchor="middle", weight="bold",
                          opacity=a))
    a = words_in(f)
    if a > 0:
        out.append(G.text(W / 2, 66, "One system: STAC for the data, one "
                          "editor for every app", 22, anchor="middle",
                          weight="bold", opacity=a))

    out.append(_lanes(f))
    # under the system: its box covers the routes' starts as it gathers them
    for r in range(N_ROUTES):
        out.append(_route_line(r, f))
    out.append(_system(f))
    for r in range(N_ROUTES):
        out.append(_card(r, f))
    for r in range(N_ROUTES):
        out.append(_hand_off(r, f))

    # the granules, last, so they pass over their routes and people
    body = "".join('<circle cx="%.1f" cy="%.1f" r="6.5" fill="%s" stroke="#ffffff"'
                   ' stroke-width="1.5"/>' % (x, y, COLOR[g])
                   for _r, g, x, y in dots(f))
    out.append('<g class="dots" opacity="0.9">%s</g>' % body)

    # how long each line is -- the problem made countable
    for r in range(N_ROUTES):
        q = len(waiting(r, f))
        if q and m < 1:
            cy = CARD_Y[r] + CARD_H / 2
            out.append(G.text(PERSON_X - 50, cy + 34, "%d waiting" % q, 11.5,
                              fill=WARN, anchor="end", weight="bold",
                              opacity=1 - m))

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
                           sw=1.5, key=("ucap",))
                   + G.text(x + w / 2, y + 40, s, 18, fill=L.BUBBLE_FG,
                            anchor="middle")
                   + "</g>")
    return "".join(out)
