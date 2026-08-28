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

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import layout as L
import rough as R
from style import S

FPS = 15
FONT_BUMP = 4                   # every label four points larger, for projection
FADE = 7                        # frames to fade a bubble in / out
MIN_BUBBLE_SEC = 7.0            # every caption must be readable this long
MIN_BUBBLE_FRAMES = int(round(MIN_BUBBLE_SEC * FPS))
GAP = 12                        # quiet frames between one caption and the next

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


def bucket(cx, cy, w=46, h=44, stroke="#6f7681", fill="#ffffff", accent="#6f7681"):
    x, y = cx - w / 2, cy - h / 2
    inset = w * 0.13
    return (
        S.poly([(x, y + 6), (x + w, y + 6), (x + w - inset, y + h), (x + inset, y + h)],
               stroke, sw=2, fill=fill, closed=True, key=("bukb", cx, cy))
        + S.ellipse(cx, y + 6, w / 2, 5, fill=fill, stroke=stroke, sw=2,
                    key=("bukt", cx, cy))
        + S.circle(cx + 5, cy + 4, 4, stroke=accent, sw=1.6, opacity=0.85,
                   key=("bukc", cx, cy))
        + S.poly([(cx - 11, cy), (cx - 3, cy), (cx - 3, cy + 8), (cx - 11, cy + 8)],
                 accent, sw=1.6, closed=True, opacity=0.85, key=("buks", cx, cy))
        + S.poly([(cx - 9, cy - 8), (cx - 4, cy - 15), (cx + 1, cy - 8)],
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


# --------------------------------------------------------- static scenery ---
def context_boxes():
    """Everything that is never animated: drawn muted, purely as context."""
    o = L.CONTEXT_OPACITY
    out = []

    # ---- Earthdata GIS (above STAC)
    x, y, w, h = L.BOX_EGIS
    out.append(box(x, y, w, h, L.FILL_EGIS, opacity=o))
    out.append(text(x + w / 2, y + 24, "Earthdata GIS", 15, anchor="middle",
                    weight="bold", opacity=o))
    for i, a in enumerate((L.A_FEMA, L.A_NOAA, L.A_CENSUS)):
        out.append(img(a, x + 26 + i * 68, y + 36, 46, 46, opacity=o))
    for i, (a, lab) in enumerate(((L.A_ARCGIS_DESKTOP, "ArcGIS Desktop"),
                                  (L.A_ARCGIS_ONLINE, "ArcGIS Online"),
                                  (L.A_NOTEBOOK, "Service Workflows"))):
        px = x + 26 + i * 68
        out.append(img(a, px + 6, y + 108, 36, 36, opacity=o))
        for j, line in enumerate(wrap(lab, 9)):
            out.append(text(px + 24, y + 160 + j * 12, line, 9.5, anchor="middle", opacity=o))

    # ---- Data Processing (below STAC)
    x, y, w, h = L.BOX_PROCESSING
    out.append(box(x, y, w, h, L.FILL_PROCESSING, opacity=o))
    out.append(text(x + w / 2, y + 24, "Data Processing", 14, anchor="middle",
                    weight="bold", opacity=o))
    out.append(img(L.A_JUPYTER, x + 75, y + 40, 90, 50, opacity=o))
    for j, line in enumerate(("Disasters Hub /", "Algorithm Repo /", "User Notebooks")):
        out.append(text(x + w / 2, y + 112 + j * 15, line, 11.5, anchor="middle", opacity=o))
    out.append(img(L.A_GITHUB, x + 26, y + 156, 40, 40, opacity=o))
    out.append(img(L.A_NOTEBOOK, x + w - 62, y + 157, 32, 38, opacity=o))


    # ---- Portal Content (right, mirrors Data Integration)
    x, y, w, h = L.BOX_PORTAL
    out.append(box(x, y, w, h, L.FILL_PORTAL, opacity=o))
    out.append(text(x + w / 2, y + 28, "Portal Content", 17, anchor="middle",
                    weight="bold", opacity=o))
    shots = ((L.A_SHOT_HOME, "Home Page"), (L.A_SHOT_STORY, "Event / Story Page"),
             (L.A_SHOT_VIZ, "Data Visualization"), (L.A_SHOT_TRAINING, "Training Page"))
    for i, (a, lab) in enumerate(shots):
        px = x + 30 + (i % 2) * 265
        py = y + 55 + (i // 2) * 285
        out.append(S.box(px, py, 240, 215, "#ffffff", stroke="#c9ccd1", rx=2,
                         sw=1.5, opacity=o, key=("shot", px, py)))
        out.append(img(a, px + 5, py + 5, 230, 205, opacity=o,
                       preserve="xMinYMin slice"))
        out.append(text(px + 120, py + 238, lab, 11.5, anchor="middle", opacity=o))

    # ---- Community & Engagement (bottom-right, mirrors Funded Projects)
    x, y, w, h = L.BOX_COMMUNITY
    out.append(box(x, y, w, h, L.FILL_COMMUNITY, opacity=o, dash="7 5"))
    out.append(text(x + 18, y + 28, "Community &", 14, weight="bold", opacity=o))
    out.append(text(x + 18, y + 46, "Engagement", 14, weight="bold", opacity=o))
    out.append(text(x + 18, y + 64, "no automated data path", 9.5, opacity=o))
    items = ((L.A_LISTSERV, "list-serv"), (L.A_MYST, "MyST Docs"),
             (L.A_GITHUB, "Github"), (L.A_GRAFANA, "Grafana"),
             (L.A_NEWSLETTER, "Newsletter"))
    for i, (a, lab) in enumerate(items):
        px = x + 190 + i * 70
        out.append(img(a, px + 12, y + 12, 34, 34, opacity=o))
        out.append(text(px + 29, y + 62, lab, 9.5, anchor="middle", opacity=o))

    # ---- TinaCMS, mirroring Airflow on the right of STAC
    out.append(img(L.A_TINA, L.TINA_C[0] - L.TINA_SIZE / 2,
                   L.TINA_C[1] - L.TINA_SIZE / 2, L.TINA_SIZE, L.TINA_SIZE, opacity=o))
    out.append(text(L.LABEL_TINA[0], L.LABEL_TINA[1], "TinaCMS", 11,
                    anchor="middle", opacity=o))

    # ---- muted static links from STAC out to its neighbours
    sx, sy, sw, sh = L.BOX_STAC
    for d in (f"M {sx+sw/2},{sy} V {L.BOX_EGIS[1]+L.BOX_EGIS[3]}",
              f"M {sx+sw/2},{sy+sh} V {L.BOX_PROCESSING[1]}",
              f"M {sx+sw},{sy+sh/2} H {L.BOX_PORTAL[0]}"):
        out.append(f'<path d="{d}" stroke="{L.FLOW}" stroke-width="3" fill="none" '
                   f'opacity="{o}" marker-end="url(#ctxArrow)"/>')
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
    return "\n".join([
        f'<path d="M {gap_x0},{fwd[0][1]} H {fwd[-1][0]}" stroke="{L.FLOW}" '
        f'stroke-width="3.5" fill="none" opacity="0.55" marker-end="url(#ctxArrow)"/>',
        f'<path d="M {ret[0][0]},{ret[0][1]} H {ret[1][0]}" stroke="{L.FLOW}" '
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
        # Three equal-height slots on a shared centre line (y=832), pitched
        # evenly at 113px between centres, so the marks line up optically.
        img(L.A_NASA, x + 215, y + 10, 64, 44),
        img(L.A_VEDA, x + 300, y + 10, 120, 44),
        img(L.A_ESRI, x + 445, y + 10, 56, 44),
        text(x + 247, y + 70, "ROSES", 10, anchor="middle"),
    ])


def airflow_static(angle):
    return "\n".join([
        airflow_group(L.AIRFLOW_C[0], L.AIRFLOW_C[1], L.AIRFLOW_SIZE, angle),
        text(L.LABEL_AIRFLOW[0], L.LABEL_AIRFLOW[1], "Airflow SM2A", 11,
             anchor="middle"),
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


def place_bubble(anchor, bw, bh, strict=False):
    """
    Find the spot closest to `anchor` that collides with no container.

    This is the fix for bubbles drifting away from what they describe: instead
    of pinning each stage to a hand-chosen slot, sweep the canvas and take the
    nearest collision-free position. Falls back to the top strip if the canvas
    is somehow full.
    """
    ax, ay = anchor
    boxes = L.occupied()
    pad = L.BUBBLE_CLEARANCE
    best, best_d = None, None
    for gx in range(16, int(L.W - bw) - 15, 12):
        for gy in range(12, int(L.H - bh) - 11, 12):
            cand = (gx, gy, bw, bh)
            if any(_overlaps(cand, b, pad) for b in boxes):
                continue
            d = math.hypot(gx + bw / 2 - ax, gy + bh / 2 - ay)
            if best_d is None or d < best_d:
                best, best_d = cand, d
    if best is None and strict:
        return None          # caller will retry at a different width
    return best or (40, 16, bw, bh)


def bubble(stage, alpha):
    if alpha <= 0.01:
        return ""
    px, py = stage["anchor"]
    fs, lh, pad = 14.5, 22, 18
    boxes = L.occupied()

    # Try the widest bubble first: fewer lines means a shorter box, which is
    # what lets it sit in the short strip above the containers. Fall back to
    # narrower ones for the tight bottom corridor. Only if nothing places
    # cleanly do we accept an overlap.
    chosen = None
    for bw in L.BUBBLE_WIDTHS:
        chars = max(18, int((bw - 2 * pad) / ((fs + FONT_BUMP) * 0.52)))
        lines = wrap(stage["bubble"], chars)
        bh = len(lines) * lh + 26
        spot = place_bubble((px, py), bw, bh, strict=True)
        if spot:
            chosen = (spot, lines, bw, bh)
            break
    if chosen is None:
        bw = L.BUBBLE_WIDTHS[-1]
        chars = max(18, int((bw - 2 * pad) / ((fs + FONT_BUMP) * 0.52)))
        lines = wrap(stage["bubble"], chars)
        bh = len(lines) * lh + 26
        chosen = (place_bubble((px, py), bw, bh), lines, bw, bh)

    (x, y, bw, bh), lines, bw, bh = chosen

    # A tail that spans half the canvas stops reading as "this points at that"
    # and just looks like a stray arrow -- past this distance, omit it.
    TAIL_MAX = 260
    near_x = max(x, min(x + bw, px))
    near_y = max(y, min(y + bh, py))
    if math.hypot(px - near_x, py - near_y) > TAIL_MAX:
        tail = None
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


def frame_svg(f):
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{L.W}" height="{L.H}" '
        f'viewBox="0 0 {L.W} {L.H}">',
        '<defs>'
        f'<marker id="ctxArrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="5" '
        f'markerHeight="5" orient="auto-start-reverse">'
        f'<path d="M 0 0 L 10 5 L 0 10 z" fill="{L.FLOW}"/></marker>'
        f'<marker id="pushArrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="5" '
        f'markerHeight="5" orient="auto-start-reverse">'
        f'<path d="M 0 0 L 10 5 L 0 10 z" fill="{L.FLOW}"/></marker>'
        '</defs>',
        f'<rect width="{L.W}" height="{L.H}" fill="{S.bg}"/>',
        context_boxes(),
        integration_static(),
        funded_static(),
        stac_static(),
        di_stac_link(),
    ]

    prog = {s["key"]: stage_progress(s, f) for s in STAGES}
    dash = f * 7.0

    # --- Airflow spins only while it is doing work
    spin = 0.0
    if prog["airflow"] >= 0 or prog["tostac"] >= 0.45:
        spin = (f - STAGES[2]["start"]) * 4.2
    # --- highlights
    di = L.BOX_INTEGRATION
    if 0 <= prog["sources"] < 1.0:
        parts.append(halo(*di, strength=1.0 - abs(prog["sources"] - 0.5) * 0.7))
    if 0 <= prog["ingest"]:
        s = 1.0 if prog["ingest"] < 1 else 0.45
        parts.append(halo(*L.BOX_INGEST, strength=s, rx=5))
    if 0 <= prog["airflow"] or prog["tostac"] >= 0.7:
        parts.append(halo(*L.BOX_STAC, strength=1.0))
    if 0 <= prog["push"] < 1.3:
        parts.append(halo(*L.BOX_FUNDED, strength=1.0))
        parts.append(node_pulse(L.DISASTERS_C[0], L.DISASTERS_C[1],
                                strength=max(0.0, prog["push"]), r=34))

    # --- flows
    if prog["sources"] >= 0:
        # six catalog spokes plus the Disasters bucket's own riser: the bucket
        # is an ingest source from the outset, not something introduced later.
        inbound = [L.spoke(i) for i in range(6)] + [L.disasters_riser()]
        for i, pts in enumerate(inbound):
            local = min(1.0, max(0.0, (prog["sources"] * 1.5) - i * 0.055))
            if local > 0:
                parts.append(flow_path(pts, local, dash + i * 9, width=2.8))
    if prog["ingest"] >= 0:
        parts.append(flow_path(L.hub_to_ingest(), prog["ingest"], dash, width=4))
    if prog["airflow"] >= 0:
        parts.append(flow_path(L.ingest_to_stac(), prog["airflow"], dash, width=4.5))
    if prog["push"] >= 0:
        parts.append(flow_path(L.push_path(), prog["push"], dash, width=4))
    if prog["tostac"] >= 0:
        parts.append(flow_path(L.disasters_to_stac(), prog["tostac"], dash, width=4.5))

    # pinwheel last, so the flow line passes behind it rather than through it
    parts.append(airflow_static(spin))

    # --- narration
    live = [(stage_alpha(s, f), s) for s in STAGES]
    live = [(a, s) for a, s in live if a > 0]
    if live:
        a, s = max(live, key=lambda t: t[0])
        parts.append(bubble(s, a))

    parts.append("</svg>")
    return "\n".join(parts)


def main():
    outdir = L.FRAMES
    os.makedirs(outdir, exist_ok=True)
    # librsvg will not read a resource outside the frame's own directory tree.
    os.makedirs(L.FRAME_ASSETS, exist_ok=True)
    for name in os.listdir(L.ASSETS):
        src, dst = os.path.join(L.ASSETS, name), os.path.join(L.FRAME_ASSETS, name)
        if not os.path.exists(dst) or os.path.getmtime(src) > os.path.getmtime(dst):
            with open(src, "rb") as a, open(dst, "wb") as b:
                b.write(a.read())
    for old in os.listdir(outdir):
        if old.endswith((".svg", ".png")):
            os.remove(os.path.join(outdir, old))
    for f in range(TOTAL):
        with open(f"{outdir}/f{f:04d}.svg", "w", encoding="utf-8") as fh:
            fh.write(frame_svg(f))
    print(f"wrote {TOTAL} frames -> {outdir}  ({TOTAL/FPS:.1f}s at {FPS}fps)")


if __name__ == "__main__":
    main()
