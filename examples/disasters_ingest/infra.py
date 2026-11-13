#!/usr/bin/env python3
"""
The infrastructure slide: the whole ecosystem at once, with the reusable
cyberinfrastructure it runs on brought forward -- the Ingest UI, Airflow,
STAC, JupyterHub, TinaCMS, MyST Docs, Grafana and GitHub. Built once, reused
for every event: that is what makes a fast response to decision makers
possible.

No flows. The other slides are about data moving; this one is about what is
built once and reused, so nothing travels and there are no arrows. The picture
is drawn whole, quietened under a wash, and the eight pieces are drawn again on
top at full strength. They are drawn by the SAME functions the diagram uses
(gen_frames.ingest_ui, processing_hub, ...), so each comes through the wash
exactly where it sits; the blocks' headings come through it too, so the reader
can still find their way around. In the GIF the eight come forward one at a
time, each named with what it does, ending on all eight and what they add up
to.

The PNG (./build.sh --poster=infra, poster_svg) is that ending with everything
else taken away: only the blocks' frames and headings and the eight pieces,
each where it sits in the ecosystem.
"""
import gen_frames as G
import layout as L
from journey import ramp, window
from style import S

FPS, FADE = G.FPS, G.FADE

TITLE = "Reusable cyberinfrastructure for fast response to decision making"
QUALITIES = ("Interoperable", "Cloud-optimized", "Cost-effective")
# (key, name, what it does), in the order data meets them
PIECES = (
    ("ingest", "Ingest UI", "add a dataset through a form, no code"),
    ("airflow", "Airflow", "automated ingest to cloud-optimized formats"),
    ("stac", "STAC", "one interoperable catalog, the single source of truth"),
    ("jupyter", "JupyterHub", "analysis next to the data, no downloads"),
    ("tina", "TinaCMS", "edit every portal page in one place"),
    ("myst", "MyST Docs", "documentation and tutorials, written once, reused"),
    ("grafana", "Grafana", "dashboards to monitor and share"),
    ("github", "GitHub", "everything as code: reused, not rebuilt"),
)
KEYS = [p[0] for p in PIECES]
WASH = 0.55                    # how far everything else recedes
GLOW_REST = 0.45               # their glow once all are named
TITLE_Y, LINE_Y = 40, 80       # both clear of Federal Partners, the topmost box
PILL_H = 28

# ---------------------------------------------------------------- timeline ---
MAX_SECONDS = 30
WHOLE = 2 * FPS                # the ecosystem at full strength, first
RECEDE = 15                    # then everything steps back
BEAT = 42                      # each piece: lit and named, 2.8 s -- eight
                               # beats of 3 s ran past MAX_SECONDS
FINALE = 4 * FPS               # all eight, and what they add up to
START = WHOLE + RECEDE
ALL_AT = START + len(PIECES) * BEAT
TOTAL = ALL_AT + FINALE


def beat_start(k):
    return START + k * BEAT


def beat_end(k):
    """When piece k's line starts to fade: out before the next one comes in."""
    return beat_start(k + 1) - FADE - 1


def spin(f):
    """Airflow turns while it is the one named -- it runs things -- and stops
    where it stopped, so the GIF's last frame and the PNG agree."""
    s = beat_start(KEYS.index("airflow"))
    return (min(max(f, s), s + BEAT) - s) * 4.2


# ------------------------------------------------------------------ pieces ---
def _item(name):
    return [lab for _a, lab in G.COMMUNITY_ITEMS].index(name)


def _item_rect(i):
    cx, cy = G.community_item_c(i)
    return (cx - 32, cy - 22, 64, L.BOX_COMMUNITY[1] + 68 - (cy - 22))


def piece(key, angle=0.0):
    """[markup] of piece `key`, each drawn by the function the diagram draws
    it with -- one part per place it appears on the canvas. `angle` is
    Airflow's pinwheel; each slide turns it on its own clock."""
    if key == "ingest":
        return [G.ingest_ui()]
    if key == "airflow":
        return [G.airflow_static(angle)]
    if key == "stac":
        return [G.stac_static()]
    if key == "jupyter":
        return [G.processing_hub()]
    if key == "tina":
        return [G.tina_node()]
    if key == "myst":
        return [G.community_item(_item("MyST Docs"))]
    if key == "grafana":
        return [G.community_item(_item("Grafana"))]
    if key == "github":                       # on the canvas twice
        return [G.processing_github(), G.community_item(_item("Github"))]
    raise KeyError(key)


def piece_rects(key):
    """Where piece `key` is: what its glow surrounds."""
    if key == "ingest":
        return [L.BOX_INGEST]
    if key == "airflow":
        cx, cy = L.AIRFLOW_C
        return [(cx - 34, cy - 32, 68, 98)]
    if key == "stac":
        return [L.BOX_STAC]
    if key == "jupyter":
        x, y, w, _h = L.BOX_PROCESSING
        top = L.DPS_C[1] - L.DPS_SIZE / 2 - 10
        return [(x + 10, top, w - 20, y + 150 - top)]
    if key == "tina":
        cx, cy = L.TINA_C
        top = cy - L.TINA_SIZE / 2 - 6
        return [(cx - 40, top, 80, L.LABEL_TINA[1] + 10 - top)]
    if key == "myst":
        return [_item_rect(_item("MyST Docs"))]
    if key == "grafana":
        return [_item_rect(_item("Grafana"))]
    if key == "github":
        x, y, _w, _h = L.BOX_PROCESSING
        return [(x + 20, y + 150, 52, 52), _item_rect(_item("Github"))]
    raise KeyError(key)


def lit(k, f):
    """0..1: how far piece k has come forward through the wash."""
    return ramp(f, beat_start(k), beat_start(k) + FADE)


# ----------------------------------------------------------------- drawing ---
def pill_rects():
    """The qualities, in a row under the title, centred."""
    ws = [len(q) * 10.0 + 40 for q in QUALITIES]
    gap = 18
    x = L.W / 2 - (sum(ws) + gap * (len(ws) - 1)) / 2
    out = []
    for w in ws:
        out.append((x, LINE_Y - 22, w, PILL_H))
        x += w + gap
    return out


def _heading(f):
    W = L.W
    out = [G.text(W / 2, TITLE_Y, TITLE, 24, anchor="middle", weight="bold")]
    for k, (_key, name, role) in enumerate(PIECES):
        a = window(f, beat_start(k), beat_end(k))
        if a > 0:
            out.append(G.text(W / 2, LINE_Y, "%s: %s" % (name, role), 17,
                              fill=L.GLOW, anchor="middle", weight="bold",
                              opacity=a))
    a = ramp(f, ALL_AT, ALL_AT + FADE)
    if a > 0:
        body = []
        for q, (x, y, w, h) in zip(QUALITIES, pill_rects()):
            body.append(G.box(x, y, w, h, "#eef3fe", stroke=L.GLOW, rx=14)
                        + G.text(x + w / 2, y + 20, q, 15, fill=L.GLOW,
                                 anchor="middle", weight="bold"))
        out.append('<g class="qualities" opacity="%.3f">%s</g>' % (a, "".join(body)))
    return "".join(out)


def infra_svg(f):
    W, H = L.W, L.H
    out = ['<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" '
           'viewBox="0 0 %d %d">' % (W, H, W, H),
           '<rect width="%d" height="%d" fill="%s"/>' % (W, H, S.bg),
           base(f)]
    w = WASH * ramp(f, WHOLE, WHOLE + RECEDE)
    if w > 0:
        out.append('<rect class="wash" width="%d" height="%d" fill="%s" '
                   'opacity="%.3f"/>' % (W, H, S.bg, w))
        out.append(_titles())
    out += _forward(f)
    out.append(_heading(f))
    out.append("</svg>")
    return "\n".join(out)


def base(f):
    """The whole ecosystem, block by block as the diagram draws it -- minus
    every path, and minus Community's "no automated data path" note."""
    return "\n".join([G.egis_block(), G.processing_block(), G.portal_block(),
                      G.community_block(note=False), G.tina_node(),
                      G.integration_static(paths=False), G.funded_static(),
                      G.stac_static(), G.airflow_static(spin(f))])


def heading(block):
    """A block's heading, as this slide draws it: without Community's note."""
    return G.block_title(block, note=False)


def _titles():
    """The blocks' headings: never washed out -- they are how a reader finds
    their way around the picture."""
    return ('<g class="titles">%s</g>'
            % "\n".join(heading(b) for b in G.BLOCKS))


def _forward(f):
    """The pieces, as far forward as they have come by frame f, with their glow."""
    out = []
    rest = GLOW_REST * ramp(f, ALL_AT, ALL_AT + FADE)
    for k, key in enumerate(KEYS):
        a = lit(k, f)
        if a <= 0:
            continue
        glow = max(window(f, beat_start(k), beat_end(k)), rest)
        for rect in piece_rects(key):
            out.append(G.halo(*rect, strength=glow))
        out.append('<g class="piece" data-piece="%s" opacity="%.3f">%s</g>'
                   % (key, a, "".join(piece(key, spin(f)))))
    return out


def poster_svg():
    """
    The PNG: the GIF's ending with everything that is not reusable
    infrastructure taken away -- no sources, partners, screenshots, funded
    projects or other channels. The blocks keep their frames and headings, so
    each piece still sits where it does in the ecosystem.
    """
    W, H = L.W, L.H
    f = TOTAL - 1
    out = ['<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" '
           'viewBox="0 0 %d %d">' % (W, H, W, H),
           '<rect width="%d" height="%d" fill="%s"/>' % (W, H, S.bg)]
    out += [G.block_box(b) for b in G.BLOCKS]
    out.append(_titles())
    out += _forward(f)
    out.append(_heading(f))
    out.append("</svg>")
    return "\n".join(out)
