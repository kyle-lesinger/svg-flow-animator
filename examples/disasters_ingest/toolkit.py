#!/usr/bin/env python3
"""
The toolkit slide: the reusable cyberinfrastructure laid out in a tray across
the top -- Ingest UI, Airflow, STAC, JupyterHub, TinaCMS, MyST Docs, Grafana,
GitHub -- and the ecosystem assembled beneath it, section by section, each
piece moving down out of the tray to where it works.

    1. Data Integration + Funded Projects & Partners  <- Ingest UI, Airflow
    2. (the centre)                                   <- STAC
    3. Federal Partners + Data Processing             <- JupyterHub, GitHub
    4. Portal Content                                 <- TinaCMS
    5. Community & Engagement                         <- MyST Docs, GitHub, Grafana

GitHub is used in two places, so its first trip is a copy and it leaves the
tray only on its last -- reuse, shown rather than said. Once everything is in
place the tray gives way to what it adds up to: interoperable,
cloud-optimized, cost-effective -- and the connections draw themselves in.
The sources' spokes first, faint, meeting at the hub the leg into STAC leaves
from; then the legs INTO STAC, one after another, each arriving with a pulse
as the catalogue's glow rises: everything converges on STAC. Then the legs
out of it, and the Portal fan, faint, once the Portal leg has landed. Then
one link from Community & Engagement's toolkit pieces -- MyST
Docs, GitHub, Grafana -- up into STAC, labelled "docs · code · metrics" and
drawn grey, not flow green: it is engagement, not a data path, and the block
stays dashed. Nothing travels along any of them; lines draw in, that is all.

The ecosystem is drawn at ECO_S of its size, below the tray, by the same block
and piece functions as the diagram (gen_frames.*_block, infra.piece), so a
piece lands exactly where the diagram draws it: in place it is drawn with no
transform at all. In the tray, and on the way down, it is the same markup
moved and scaled by a transform -- never re-placed geometry, which in sketch
mode would boil.
"""
import gen_frames as G
import infra as I
import layout as L
from journey import ramp, window
from style import S

FPS, FADE = G.FPS, G.FADE

TITLE = I.TITLE
QUALITIES = I.QUALITIES
NAMES = dict((k, name) for k, name, _role in I.PIECES)
# (blocks that appear, pieces that come down into them)
STEPS = (
    (("integration", "funded"), ("ingest", "airflow")),
    ((), ("stac",)),
    (("egis", "processing"), ("jupyter", "github")),
    (("portal",), ("tina",)),
    (("community",), ("myst", "github", "grafana")),
)
COMMUNITY_PIECES = ("MyST Docs", "Github", "Grafana")
GLOW_REST = 0.45

# ------------------------------------------------------------------ layout ---
TITLE_Y = 34
SLOT_W, SLOT_H = 154, 72             # a tray slot's frame
FIT_W, FIT_H = 138, 58               # the room a piece gets inside it
SLOT_TOP = 50
SLOT_PITCH = 172
LABEL_Y = SLOT_TOP + SLOT_H + 18
ECO_Y = 156                          # the ecosystem, below the tray...
ECO_S = (L.H - ECO_Y - 4) / float(L.H)
ECO_X = (L.W - L.W * ECO_S) / 2      # ...scaled to fit, centred


def slot_c(k):
    """Centre of the tray slot for piece k, in canvas coordinates."""
    return (L.W / 2 + (k - (len(I.KEYS) - 1) / 2.0) * SLOT_PITCH,
            SLOT_TOP + SLOT_H / 2)


def to_eco(p):
    """Canvas point -> ecosystem coordinates (inside the scaled group)."""
    return ((p[0] - ECO_X) / ECO_S, (p[1] - ECO_Y) / ECO_S)


def to_canvas(p):
    return (ECO_X + p[0] * ECO_S, ECO_Y + p[1] * ECO_S)


# ---------------------------------------------------------------- timeline ---
MAX_SECONDS = 30
INTRO = 3 * FPS                      # the tray alone: here is the toolkit
STEP = 4 * FPS                       # each section, and its pieces arriving
APPEAR = 12                          # a section fades in...
FLY = 24                             # ...then each piece takes this to land,
STAGGER = 10                         # one after another
LAND_FLASH = 14                      # the glow on landing, before it settles
FINALE = 7 * FPS                     # all in place, what it adds up to, and
                                     # the connections drawing in


def step_start(s):
    return INTRO + s * STEP


ALL_AT = step_start(len(STEPS))
TOTAL = ALL_AT + FINALE

# ----------------------------------------------------------- connections ---
CONVERGE_AT = ALL_AT + FADE          # the tray has gone; the sources' spokes draw
LINK_T = 14                          # frames a leg takes to draw itself in
LINK_STAGGER = 8                     # one leg after another
PULSE_T = 14                         # the ring where a leg arrives
FAINT, FAINT_W = 0.45, 2             # the spokes and the Portal fan: there, quietly
HUB_AT = CONVERGE_AT + 6             # hub -> Ingest UI, once the spokes have met
INTO_AT = CONVERGE_AT + LINK_T       # the legs into STAC, once the spokes have met
INTO_STAC = ("disasters_to_stac", "egis_to_stac", "processing_to_stac")
ENGAGE_AT = CONVERGE_AT + 46         # Community's link, once the data legs are in
ENGAGE_T = 24
OUT_AT = CONVERGE_AT + 52            # the legs out of STAC, together
FAN_AT = OUT_AT + LINK_T             # TinaCMS -> the pages, once Portal's leg lands
OUT_OF_STAC = (("stac_to_portal", G.STAC_MAIN_W), ("stac_return", G.STAC_MINOR_W),
               ("stac_to_egis", G.STAC_MINOR_W), ("stac_to_processing", G.STAC_MINOR_W))
ENGAGE_ITEMS = (1, 2, 3)             # MyST Docs, GitHub, Grafana: the toolkit's
ENGAGE_Y = 789                       # the trunk, in the gap under Portal Content
ENGAGE_X = 950                       # ...up the gap right of STAC...
ENGAGE_END_Y = 530                   # ...into STAC's right edge, below TinaCMS
ENGAGE_LABEL = "docs · code · metrics"
ENGAGE_COLOR = "#8a94a6"             # grey: engagement, not a data path
ENGAGE_INK = "#5b6472"               # ...and its label, dark enough to read small


def engagement():
    """(stubs, trunk): a stub up from each of Community's toolkit pieces to
    one trunk, which runs left under Portal Content and up into STAC."""
    xs = [G.community_item_c(i)[0] for i in ENGAGE_ITEMS]
    top = L.BOX_COMMUNITY[1]
    stubs = [[(x, top), (x, ENGAGE_Y)] for x in xs]
    trunk = [(max(xs), ENGAGE_Y), (ENGAGE_X, ENGAGE_Y), (ENGAGE_X, ENGAGE_END_Y),
             (L.BOX_STAC[0] + L.BOX_STAC[2], ENGAGE_END_Y)]
    return stubs, trunk


def label_rect():
    """Where the engagement label sits: over the trunk, under Portal Content."""
    w = len(ENGAGE_LABEL) * 7.2 + 16
    cx = (L.BOX_PORTAL[0] + ENGAGE_X) / 2 + 120
    return (cx - w / 2, L.BOX_PORTAL[1] + L.BOX_PORTAL[3] + 1, w, 16)


def _leg(name, pts, width, color, t0, dur, f, out, opacity=1.0, head=True):
    """One connection drawing itself in from t0 over dur frames. Returns 1
    once it has arrived."""
    p = (f - t0) / float(dur)
    if p <= 0:
        return 0
    out.append('<g class="link" data-link="%s" data-progress="%.3f" '
               'data-opacity="%.2f">%s</g>'
               % (name, min(1.0, p), opacity,
                  G.link(pts, color=color, width=width, progress=p, opacity=opacity,
                         head=head, key=("tklink", name))))
    return 1 if p >= 1 else 0


def _links(f):
    """The connections, once everything is in place: into STAC, then out of
    it, then Community's. In ecosystem coordinates."""
    if f < CONVERGE_AT:
        return []
    out, arrived = [], 0
    # the sources' spokes, faint, meeting at the hub; then hub -> Ingest UI
    for i in range(len(L.SOURCES)):
        _leg("spoke_%d" % i, L.spoke(i), FAINT_W, L.FLOW, CONVERGE_AT, LINK_T, f, out,
             opacity=FAINT, head=False)
    _leg("hub_to_ingest", L.hub_to_ingest(), FAINT_W, L.FLOW, HUB_AT, 8, f, out,
         opacity=FAINT, head=False)
    for i, name in enumerate(INTO_STAC):
        pts = getattr(L, name)()
        t0 = INTO_AT + LINK_STAGGER * i
        arrived += _leg(name, pts, G.STAC_MAIN_W, L.FLOW, t0, LINK_T, f, out)
        since = f - (t0 + LINK_T)
        if 0 <= since < PULSE_T:
            out.append(G.node_pulse(pts[-1][0], pts[-1][1],
                                    strength=1 - since / float(PULSE_T), r=16))
    for name, width in OUT_OF_STAC:
        _leg(name, getattr(L, name)(), width, L.FLOW, OUT_AT, LINK_T, f, out)
    # TinaCMS -> the four pages, faint, once Portal's leg has landed
    for i in range(len(L.PORTAL_SHOTS) if hasattr(L, "PORTAL_SHOTS") else 4):
        _leg("portal_fan_%d" % i, L.portal_fan(i), FAINT_W, L.FLOW, FAN_AT, LINK_T, f,
             out, opacity=FAINT, head=False)
    stubs, trunk = engagement()
    for i, pts in enumerate(stubs):
        out.append('<g class="link" data-link="engage_stub">%s</g>'
                   % G.link(pts, color=ENGAGE_COLOR, width=2, head=False,
                            opacity=ramp(f, ENGAGE_AT, ENGAGE_AT + FADE),
                            key=("tkstub", i)))
    if _leg("engagement", trunk, 2, ENGAGE_COLOR, ENGAGE_AT, ENGAGE_T, f, out):
        x, y, w, h = label_rect()
        out.append(G.text(x + w / 2, y + 12, ENGAGE_LABEL, 11, fill=ENGAGE_INK,
                          anchor="middle",
                          opacity=ramp(f, ENGAGE_AT + ENGAGE_T, ENGAGE_AT + ENGAGE_T + FADE)))
    # everything converges on the catalogue: its glow rises as the legs arrive
    out.insert(0, G.halo(*L.BOX_STAC, strength=arrived / float(len(INTO_STAC))))
    return out


def _drops():
    """[(step, order, key, part)]: every trip down. A piece used in two places
    makes two trips, one per part, in the order its uses come."""
    out, seen = [], {}
    for s, (_blocks, keys) in enumerate(STEPS):
        for j, key in enumerate(keys):
            part = seen.get(key, 0)
            seen[key] = part + 1
            out.append((s, j, key, part))
    return out


DROPS = _drops()


def drop_start(s, j):
    return step_start(s) + APPEAR + STAGGER * j


def landed_at(s, j):
    return drop_start(s, j) + FLY


# ------------------------------------------------------------------ pieces ---
def _part(key, part):
    return I.piece(key)[part], I.piece_rects(key)[part]


def _center(rect):
    x, y, w, h = rect
    return (x + w / 2.0, y + h / 2.0)


def tray_scale(key, part):
    """Scale (in ecosystem units) that fits the part into a tray slot."""
    _m, (_x, _y, w, h) = _part(key, part)
    return min(FIT_W / float(w), FIT_H / float(h)) / ECO_S


def state(s, j, f):
    """'tray', 'flying' or 'placed' for drop (s, j) at frame f."""
    if f < drop_start(s, j):
        return "tray"
    if f < landed_at(s, j):
        return "flying"
    return "placed"


def _moved(markup, rect, c, k):
    """`markup`, authored around `rect`, drawn centred on c at scale k."""
    rx, ry = _center(rect)
    return ('<g transform="translate(%.2f,%.2f) scale(%.4f) translate(%.2f,%.2f)">'
            '%s</g>' % (c[0], c[1], k, -rx, -ry, markup))


def _drop(s, j, key, part, f):
    """One trip: in the tray, on the way down, or in place."""
    markup, rect = _part(key, part)
    st = state(s, j, f)
    tag = ('<g class="piece" data-piece="%s" data-part="%d" data-state="%s">'
           % (key, part, st))
    if st == "placed":
        land = landed_at(s, j)
        glow = GLOW_REST + (1 - GLOW_REST) * window(f, land - FADE, land + LAND_FLASH)
        return G.halo(*rect, strength=glow) + tag + markup + "</g>"
    k0, c0 = tray_scale(key, part), to_eco(slot_c(I.KEYS.index(key)))
    if st == "tray":
        return tag + _moved(markup, rect, c0, k0) + "</g>"
    t = G.smooth((f - drop_start(s, j)) / float(FLY))
    c1 = _center(rect)
    c = (c0[0] + (c1[0] - c0[0]) * t, c0[1] + (c1[1] - c0[1]) * t)
    return tag + _moved(markup, rect, c, k0 + (1 - k0) * t) + "</g>"


def _pieces(f):
    """Every piece, wherever it is at frame f. A piece still to be used sits in
    the tray; one used twice keeps its tray copy until its last trip starts."""
    out, shown = [], set()
    flying, placed = [], []
    for s, j, key, part in DROPS:
        st = state(s, j, f)
        if st == "tray":
            if key not in shown:          # one in the tray, however many trips
                shown.add(key)
                out.append(_drop(s, j, key, part, f))
        elif st == "flying":
            flying.append(_drop(s, j, key, part, f))
        else:
            placed.append(_drop(s, j, key, part, f))
    # placed under resting, flying over everything
    return placed + out + flying


# ---------------------------------------------------------------- sections ---
BLOCK_DRAW = {
    "integration": lambda: G.integration_static(paths=False, pieces=False),
    "funded": G.funded_static,
    "egis": G.egis_block,
    "processing": lambda: G.processing_block(pieces=False),
    "portal": G.portal_block,
    "community": lambda: G.community_block(skip=COMMUNITY_PIECES, note=False),
}


def _sections(f):
    out = []
    for s, (blocks, _keys) in enumerate(STEPS):
        a = ramp(f, step_start(s), step_start(s) + APPEAR)
        if a <= 0:
            continue
        for b in blocks:
            out.append('<g class="block" data-block="%s" opacity="%.3f">%s</g>'
                       % (b, a, BLOCK_DRAW[b]()))
    return out


# ------------------------------------------------------------------- frames --
def _tray(f):
    """The slots and their names: the toolkit. It gives way at the finale."""
    a = 1 - ramp(f, ALL_AT, ALL_AT + FADE)
    if a <= 0:
        return ""
    out = []
    for k, key in enumerate(I.KEYS):
        cx, cy = slot_c(k)
        out.append(G.box(cx - SLOT_W / 2, SLOT_TOP, SLOT_W, SLOT_H, "#f6f8fc",
                         stroke="#c9d3e6", rx=10, sw=1.5))
        out.append(G.text(cx, LABEL_Y, NAMES[key], 12, anchor="middle",
                          weight="bold"))
    return '<g class="tray" opacity="%.3f">%s</g>' % (a, "".join(out))


def pill_rects():
    ws = [len(q) * 10.0 + 40 for q in QUALITIES]
    gap = 18
    x = L.W / 2 - (sum(ws) + gap * (len(ws) - 1)) / 2
    out = []
    for w in ws:
        out.append((x, SLOT_TOP + SLOT_H / 2 - 14, w, 28))
        x += w + gap
    return out


def _qualities(f):
    a = ramp(f, ALL_AT, ALL_AT + FADE)
    if a <= 0:
        return ""
    body = []
    for q, (x, y, w, h) in zip(QUALITIES, pill_rects()):
        body.append(G.box(x, y, w, h, "#eef3fe", stroke=L.GLOW, rx=14)
                    + G.text(x + w / 2, y + 20, q, 15, fill=L.GLOW,
                             anchor="middle", weight="bold"))
    return '<g class="qualities" opacity="%.3f">%s</g>' % (a, "".join(body))


def toolkit_svg(f):
    W, H = L.W, L.H
    out = ['<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" '
           'viewBox="0 0 %d %d">' % (W, H, W, H),
           '<rect width="%d" height="%d" fill="%s"/>' % (W, H, S.bg),
           G.text(W / 2, TITLE_Y, TITLE, 24, anchor="middle", weight="bold"),
           _tray(f),
           _qualities(f),
           '<g class="ecosystem" transform="translate(%.2f,%.2f) scale(%.4f)">'
           % (ECO_X, ECO_Y, ECO_S)]
    out += _sections(f)
    out += _links(f)                 # under the pieces: Airflow sits on its leg
    out += _pieces(f)
    out.append("</g>")
    out.append("</svg>")
    return "\n".join(out)
