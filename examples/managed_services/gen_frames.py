#!/usr/bin/env python3
"""
The Managed Services / External accounts walkthrough, one SVG per frame.

    ./build.sh                          the whole story -> managed-services.gif
    FLOWGIF_STYLE=flat ./build.sh       clean render    -> managed-services-flat.gif
    ./build.sh --list-sections          the chapters
    ./build.sh --section=monitor        one chapter     -> sections/monitor.gif
    ./build.sh --all-sections
    ./build.sh --poster                 a still         -> sections/overview.png
    ./edit.sh                           drag things, live preview, Save

Sketch is the default style, as in disasters_ingest; the filename suffix goes
on whatever is NOT the default.

The words are in story.py, the geometry in layout.py. This file only draws.
"""
import math
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import icons  # noqa: E402
import layout as L  # noqa: E402
import story  # noqa: E402
from svg_flow_animator import (editor, render, styles, svg,  # noqa: E402
                               timeline)
from svg_flow_animator import serve as live_server  # noqa: E402
from svg_flow_animator.geometry import point_at, smooth, wrap  # noqa: E402

DEFAULT_STYLE = "sketch"
os.environ.setdefault("FLOWGIF_STYLE", DEFAULT_STYLE)
S = styles.select()

FPS = 15
FADE = 7                        # frames a caption takes to fade in / out
GAP = 12                        # quiet frames between one beat and the next
MIN_CAPTION_FRAMES = int(round(story.MIN_CAPTION_SEC * FPS))
DIM = 0.62                      # how far the rest of the figure recedes
DASH_RATE = 7.0
GIF_SIZE = (1280, 888)          # 0.8 of the 1600x1110 canvas

ASSETS = os.path.join(HERE, "assets")
OUT = os.path.join(HERE, "out")
FRAMES = os.path.join(OUT, "frames")
# Sprites are mirrored below the frame dir: librsvg will not load an <image>
# outside the referencing SVG's own directory, and fails silently.
STAGED = os.path.join(FRAMES, "assets")

BLUE, BLUE_FILL = "#1f5fbf", "#f3f7fd"
RED, RED_FILL = "#b3261e", "#fdf5f4"
LINE = "#8f9aa6"                # every connector, before its beat
SETTLED = "#4d5b6a"             # ...and after it: the path the story has walked
ACTIVE, PACKET = "#1a6ae0", "#ff7a00"
EDGE_LABEL = "#56616c"
CAPTION_BG, CAPTION_FG, CAPTION_KICKER = "#12243d", "#ffffff", "#9cc3ff"
CROSS_DASH = "8 6"              # a connector that crosses between accounts


# ------------------------------------------------------------------ beats ---
def _anchor(name):
    if name.startswith("node."):
        return L.NODES[name[5:]]["c"]
    x, y, w, h = L.BOXES[name]
    return (x + w / 2, y + h / 2)


def _build_beats(first=8):
    out, f = [], first
    for i, b in enumerate(story.BEATS):
        dur = b["dur"]
        # Derived, not authored: every caption clears the readability floor
        # however fast its motion is.
        hold = max(10, MIN_CAPTION_FRAMES - dur)
        st = timeline.Stage(f"{b['chapter']}.{i}", f, dur, anchor=_anchor(b["anchor"]),
                            text=b["text"], hold=hold)
        # A nested list in `flows` draws in together; keep the groups for
        # timing and a flat list for everything that just asks "is k here".
        groups = [list(g) if isinstance(g, (list, tuple)) else [g]
                  for g in b.get("flows", ())]
        out.append(dict(b, stage=st, end=f + dur + hold, groups=groups,
                        flows=[k for g in groups for k in g]))
        f += dur + hold + GAP + 2 * FADE
    return out, f + 20


BEATS, TOTAL = _build_beats()
CHAPTERS = list(dict.fromkeys(b["chapter"] for b in BEATS))

# flow key -> (beat, its index within the beat). A flow belongs to exactly one
# beat; a second claim would make its state depend on which one ran last.
FLOW_BEAT = {}
for _b in BEATS:
    for _i, _group in enumerate(_b["groups"]):
        for _k in _group:
            if _k in FLOW_BEAT:
                raise SystemExit(f"story: flow {_k!r} is animated by two beats")
            FLOW_BEAT[_k] = (_b, _i)


def _inside(pt, rect):
    x, y, w, h = rect
    return x <= pt[0] <= x + w and y <= pt[1] <= y + h


def focus_of(b):
    """The nodes a beat is about: its pulses, its flows' ends, and whatever sits
    inside a box it lights up."""
    nodes = set(b.get("pulse", ()))
    for k in b.get("flows", ()):
        nodes |= {L.FLOWS[k]["src"], L.FLOWS[k]["dst"]}
    for box in b.get("glow", ()):
        nodes |= {n for n, v in L.NODES.items() if _inside(v["c"], L.BOXES[box])}
    return nodes


def live_beat(f, scope=None):
    """(beat, alpha) of the caption showing at frame f, or (None, 0)."""
    best = (None, 0.0)
    for b in BEATS:
        if scope and b["chapter"] not in scope:
            continue
        a = b["stage"].alpha(f, FADE)
        if a > best[1]:
            best = (b, a)
    return best


def flow_state(k, f):
    """('base'|'active'|'settled', local progress) for flow k at frame f."""
    if k not in FLOW_BEAT:
        return "base", 0.0          # drawn, never narrated
    b, i = FLOW_BEAT[k]
    p = b["stage"].progress(f)
    if p < 0:
        return "base", 0.0
    # Groups within one beat arrive one after another, overlapping a little.
    n = len(b["groups"])
    step = 0.55 / n if n > 1 else 0.0
    local = max(0.0, min(1.0, (p - i * step) / (1 - (n - 1) * step)))
    if local <= 0:
        return "base", 0.0
    return ("active" if f <= b["end"] else "settled"), local


# ---------------------------------------------------------------- drawing ---
def _lines(st, pts, key, color, sw, dash=None, opacity=1.0):
    """A connector in either style. stroke_layers is seeded from `key`, so a
    sketchy line is the same line in every frame (GOTCHAS: boiling)."""
    da = f' stroke-dasharray="{dash}"' if dash else ""
    op = f' opacity="{opacity:.3f}"' if opacity < 1 else ""
    return "".join(f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{sw}" '
                   f'stroke-linecap="round" stroke-linejoin="round"{da}{op}/>'
                   for d, _len in st.stroke_layers(pts, key=key))


def _arrowhead(st, pts, color, sw, key, opacity=1.0):
    if hasattr(st, "arrowhead"):
        body = st.arrowhead(pts, color, sw=sw, key=key, size=11)
    else:
        (x1, y1), (x2, y2) = pts[-2], pts[-1]
        a = math.atan2(y2 - y1, x2 - x1)
        tip = [(x2 + 11 * math.cos(a + s), y2 + 11 * math.sin(a + s))
               for s in (2.6, -2.6)]
        body = st.poly([tip[0], (x2, y2), tip[1]], color, sw=sw)
    return svg.group(body, opacity=opacity)


def _halo_text(st, x, y, s, size, fill, anchor="middle", weight="normal",
               opacity=1.0):
    """Text with a paper-coloured halo, so an edge label sitting ON its line
    stays legible -- the way the Lucid figure prints them."""
    op = f' opacity="{opacity:.3f}"' if opacity < 1 else ""
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-family="{st.font}" '
            f'font-size="{size * st.font_scale:.1f}" font-weight="{weight}" '
            f'fill="{fill}" text-anchor="{anchor}" stroke="{st.bg}" '
            f'stroke-width="5" stroke-linejoin="round" paint-order="stroke"{op}>'
            f'{svg.esc(s)}</text>')


def _halo_box(st, rect, color, strength, key):
    """A glow from concentric outlines (librsvg's blur support is poor). Drawn
    through the style, so sketch gets hand-drawn rings rather than a leaked
    flat <rect>."""
    if strength <= 0.01:
        return ""
    x, y, w, h = rect
    return "".join(
        st.box(x - g, y - g, w + 2 * g, h + 2 * g, "none", stroke=color, rx=10 + g,
               sw=sw, opacity=op * strength, key=(key, g))
        for g, op, sw in ((10, .14, 3), (5, .28, 3), (1, .7, 2.5)))


def boxes(st):
    out = []
    for key, rect, stroke, fill in (("box.managed", L.MANAGED, BLUE, BLUE_FILL),
                                    ("box.external", L.EXTERNAL, RED, RED_FILL)):
        out.append(st.box(*rect, fill, stroke=stroke, rx=10, sw=2.5, key=key))
    out.append(st.box(*L.DASHBOARD, "#ffffff", stroke=BLUE, rx=8, sw=1.5,
                      key="box.dashboard"))
    out.append(st.text(*L.TITLE_MANAGED, "Managed Services Account", 25,
                       fill=BLUE, weight="bold"))
    out.append(st.text(*L.TITLE_EXTERNAL, "Externally Managed Accounts", 25,
                       fill=RED, weight="bold"))
    out.append(st.text(*L.TITLE_DASHBOARD, "User Dashboard", 14, fill=BLUE,
                       weight="bold"))
    return "".join(out)


def flow_markup(st, k, f, dim):
    """Everything one connector contributes at frame f."""
    pts = L.flow_path(k)
    dash = CROSS_DASH if L.crosses(k) and k not in L.SOLID else None
    state, local = flow_state(k, f) if f is not None else ("base", 0.0)
    key = f"flow.{k}"
    out = [_lines(st, pts, key, LINE, 1.6, dash, opacity=dim)]
    color = LINE
    if state == "settled":
        out.append(_lines(st, pts, key, SETTLED, 2.4, dash, opacity=dim))
        color = SETTLED
    elif state == "active":
        out.append(timeline.flow(pts, local, f * DASH_RATE, ACTIVE, PACKET, width=3.5))
        if local >= 1:
            color = ACTIVE
    out.append(_arrowhead(st, pts, color, 2.2 if state != "base" else 1.6, key,
                          opacity=dim))
    lx, ly = point_at(pts, L.flow_label_t(k))
    out.append(_halo_text(st, lx, ly + 4.5, L.FLOWS[k]["label"], 13.5, EDGE_LABEL,
                          opacity=dim))
    return "".join(out)


def node_markup(st, n, opacity=1.0):
    v = L.NODES[n]
    cx, cy = v["c"]
    lx, ly = v["label_c"]
    out = [icons.icon(v["icon"], cx, cy, v["size"], st.ink, sw=2.0)]
    for i, line in enumerate(v["label"].splitlines()):
        out.append(st.text(lx, ly + i * 18, line, 14.5, fill=st.ink, anchor="middle"))
    return svg.group("".join(out), opacity=opacity)


def caption_markup(b, alpha, rect):
    """
    A beat's caption as a card in the band under the figure. No tail: the
    pulse and the dimming already say what it is about, and a pointer reaching
    up into the figure would be the overlap the band exists to prevent.

    The font steps down until the words fit the card, so a longer caption
    shrinks rather than spilling out.
    """
    if alpha <= 0.01:
        return ""
    x, y, w, h = rect
    pad = 22
    for size in (22, 20, 18, 16, 14):
        lh = size * 1.32
        lines = wrap(b["text"], max(18, int((w - 2 * pad) / (size * 0.52))))
        block = 22 + len(lines) * lh
        if block <= h - 28:
            break
    ty = y + (h - block) / 2
    n = CHAPTERS.index(b["chapter"]) + 1
    kicker = f"{n} / {len(CHAPTERS)}   {story.CHAPTER_TITLES.get(b['chapter'], '').upper()}"
    out = [svg.rect(x, y, w, h, fill=CAPTION_BG, rx=12),
           svg.text(x + pad, ty + 13, kicker, 12.5, fill=CAPTION_KICKER, weight="bold")]
    for i, line in enumerate(lines):
        out.append(svg.text(x + pad, ty + 22 + (i + 0.82) * lh, line, size,
                            fill=CAPTION_FG))
    return svg.group("".join(out), opacity=alpha)


# ------------------------------------------------------------ screenshots ---
_warned = set()


def shot_markup(st, key, alpha, grow=1.0):
    """A screenshot card in the caption band, beside the caption."""
    if alpha <= 0.01:
        return ""
    meta = story.SHOTS[key]
    x, y, w, h = L.shot_rect(key)
    cx, cy = x + w / 2, y + h / 2
    w2, h2 = w * grow, h * grow
    x, y = cx - w2 / 2, cy - h2 / 2
    staged = os.path.join(STAGED, meta["file"])
    out = [
        svg.rect(x + 6, y + 8, w2, h2 + 34, fill="#000000", rx=10, opacity=0.12),
        svg.rect(x, y, w2, h2 + 34, fill="#ffffff", rx=10),
        st.box(x, y, w2, h2 + 34, "none", stroke=ACTIVE, rx=10, sw=2, key=("shot", key)),
        st.text(x + 16, y + 23, meta["caption"], 15, fill=st.ink, weight="bold"),
    ]
    if os.path.exists(staged):
        out.append(st.img(staged, x + 10, y + 32, w2 - 20, h2 - 8, frame=False))
    else:
        if key not in _warned:
            _warned.add(key)
            sys.stderr.write(f"WARNING: screenshot {meta['file']!r} is missing from "
                             f"{os.path.relpath(ASSETS)}/ -- drawing a placeholder\n")
        out.append(svg.rect(x + 10, y + 32, w2 - 20, h2 - 8, fill="#eef1f4", rx=6))
        out.append(st.text(cx, y + 32 + h2 / 2, f"screenshot missing: assets/{meta['file']}",
                           16, fill="#8a5a00", anchor="middle"))
    return svg.group("".join(out), opacity=alpha)


SHOT_DELAY = 0.4                # fraction of a beat's motion before its insets appear


def visible_shots(f, scope=None):
    """[(key, alpha, grow)] for frame f."""
    out = []
    for b in BEATS:
        keys = b.get("shots") or ()
        if not keys or (scope and b["chapter"] not in scope):
            continue
        st = b["stage"]
        a = st.alpha(f, FADE)
        if a <= 0:
            continue
        # A screenshot waits for the beat's own flows, so the line draws in
        # before the picture of its result appears.
        delay = SHOT_DELAY if b.get("flows") else 0.0
        p = (max(0.0, st.progress(f)) - delay) / (1 - delay)
        if p < 0:
            continue
        idx = min(len(keys) - 1, int(p * len(keys)))
        since = f - (st.start + st.dur * (delay + (1 - delay) * idx / len(keys)))
        ramp = smooth(max(0.0, min(1.0, since / 8.0)))
        out.append((keys[idx], a * (ramp if idx == 0 else 1.0), 0.92 + 0.08 * ramp))
    return out


# ------------------------------------------------------------------ frame ---
def scene(f=None, scope=None, captions=True, st=None, preview=False):
    """
    The picture at frame f, as SVG body markup. f=None is the still diagram
    with nothing in motion -- what the editor traces over.
    """
    st = st or S
    beat, alpha = live_beat(f, scope) if f is not None else (None, 0.0)
    focus = focus_of(beat) if beat else None
    # Nothing in focus means nothing to recede from.
    recede = DIM * alpha if focus else 0.0
    beat_flows = set(beat.get("flows", ())) if beat else set()

    def dim_node(n):
        return 1.0 - (recede if n not in focus else 0.0) if focus else 1.0

    body = [boxes(st)]
    if beat:
        for box in beat.get("glow", ()):
            color = RED if box == "box.external" else BLUE
            body.append(_halo_box(st, L.BOXES[box], color,
                                  smooth(min(1.0, max(0.0, beat["stage"].progress(f)) * 3))
                                  * alpha, key=box))

    for k in L.FLOWS:
        op = 1.0 if (not focus or k in beat_flows) else 1.0 - recede
        body.append(flow_markup(st, k, f, op))

    if beat:
        p = beat["stage"].progress(f)
        for n in beat.get("pulse", ()):
            v = L.NODES[n]
            # a slow breathe, rather than one ring, so it reads as "this one"
            strength = alpha * (0.55 + 0.45 * math.sin(max(0.0, p) * math.pi * 3))
            body.append(timeline.pulse(*v["c"], strength, ACTIVE, r=v["size"] * 0.78))

    for n in L.NODES:
        body.append(node_markup(st, n, dim_node(n)))

    if preview:
        # The editor needs to SEE where each inset sits to drag it.
        for k in story.SHOTS:
            body.append(shot_markup(st, k, 0.22))
    elif f is not None:
        for k, a, grow in visible_shots(f, scope):
            body.append(shot_markup(st, k, a, grow))

    if captions and beat:
        rect = L.CAPTION_BESIDE_SHOT if beat.get("shots") else L.CAPTION
        body.append(caption_markup(beat, alpha, rect))
    return "".join(body)


def frame_svg(f, scope=None, captions=True, st=None):
    st = st or S
    return svg.document(L.W, L.H, scene(f, scope, captions, st), st.bg)


def stage_assets():
    """Only this puts sprites where librsvg can reach them. Every entry point
    that renders calls it -- one that forgot rendered every screenshot blank."""
    os.makedirs(FRAMES, exist_ok=True)
    if os.path.isdir(ASSETS):
        render.stage_assets(ASSETS, FRAMES)
    else:
        os.makedirs(STAGED, exist_ok=True)


def preview_svg(path):
    """The svg_flow_animator.serve contract: write the still scene, return bg."""
    stage_assets()
    with open(path, "w") as fh:
        fh.write(svg.document(L.W, L.H, scene(preview=True), S.bg))
    return S.bg


# --------------------------------------------------------------- sections ---
LEAD_IN, TAIL = 12, 20


def section_span(chapter):
    beats = [b for b in BEATS if b["chapter"] == chapter]
    if not beats:
        raise SystemExit(f"no chapter {chapter!r}; have: {', '.join(CHAPTERS)}")
    return (max(0, beats[0]["stage"].start - FADE - LEAD_IN),
            min(TOTAL, beats[-1]["end"] + FADE + TAIL))


# ------------------------------------------------------------------ build ---
_LEAK = re.compile(r'<(rect|ellipse)[^>]*stroke="[^"]*"[^>]*>')


def write_frames(span, scope=None):
    stage_assets()
    # f*.svg / f*.png only. Clearing frames/* would take the staged assets
    # with it (GOTCHAS).
    for stale in os.listdir(FRAMES):
        if re.fullmatch(r"f\d{4}\.(svg|png)", stale):
            os.remove(os.path.join(FRAMES, stale))
    first, last = span
    for i, f in enumerate(range(first, last)):
        with open(os.path.join(FRAMES, f"f{i:04d}.svg"), "w") as fh:
            fh.write(frame_svg(f, scope))
    return last - first


def check_sketch(span, scope):
    """A half-converted sketch reads as a rendering bug, so fail on any flat
    STROKED rect/ellipse. Checked on a frame mid-beat, where glows, insets and
    pulses are all on screen -- frame 0 has none of them and would pass forever."""
    if S.name != "sketch":
        return
    probes = [b for b in BEATS if not scope or b["chapter"] in scope]
    for b in probes:
        f = b["stage"].start + b["stage"].dur // 2
        leaks = _LEAK.findall(frame_svg(f, scope))
        if leaks:
            raise SystemExit(f"FAIL: {len(leaks)} flat stroked primitives leaked into "
                             f"sketch mode at frame {f}")


def build_gif(out_path, span=(0, TOTAL), scope=None):
    check_sketch(span, scope)
    n = write_frames(span, scope)
    print(f"  {n} frames ({n / FPS:.1f}s at {FPS}fps), style={S.name}")
    render.render_frames(FRAMES, L.W, L.H, background=S.bg)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    render.build_gif(FRAMES, out_path, fps=FPS, width=GIF_SIZE[0],
                     height=GIF_SIZE[1], colors=128)
    info = render.probe_gif(out_path)
    if info["frames"] < 2:
        raise SystemExit(f"FAIL: {out_path} has {info['frames']} frame(s)")
    print(f"  -> {os.path.relpath(out_path)}  {info['frames']} frames, "
          f"{info['width']}x{info['height']}, {info['bytes'] / 1e6:.2f} MB")


def suffix():
    return "" if S.name == DEFAULT_STYLE else f"-{S.name}"


POSTER_MIN_BYTES = 250_000


def build_poster():
    stage_assets()
    svg_path = os.path.join(OUT, "_poster.svg")
    png = os.path.join(HERE, "sections", f"overview{suffix()}.png")
    os.makedirs(os.path.dirname(png), exist_ok=True)
    # The settled diagram: every walked path drawn, nothing dimmed. No caption
    # -- a caption is a claim about a moment, and a still has none.
    # The figure only, at 16:9: the caption band has nothing to say here.
    with open(svg_path, "w") as fh:
        fh.write(svg.document(L.W, L.DIAGRAM_H, scene(TOTAL - 1, captions=False), S.bg))
    try:
        subprocess.run(["rsvg-convert", "-w", "3200", "-h", "1800", "-b", S.bg,
                        "-o", png, svg_path], check=True)
    finally:
        os.remove(svg_path)
    size = os.path.getsize(png)
    if size < POSTER_MIN_BYTES:
        raise SystemExit(f"FAIL: poster is only {size} bytes -- looks blank")
    print(f"  -> {os.path.relpath(png)}  ({size / 1e6:.2f} MB)")


VIEWS = {"Hand-drawn": styles.SKETCH, "Flat": styles.FLAT}


def build_editor():
    L.warm_up()
    stage_assets()
    views = {name: (lambda st=st: (svg.document(L.W, L.H, scene(st=st, preview=True),
                                                st.bg), st.bg))
             for name, st in VIEWS.items()}
    path = editor.build(os.path.join(HERE, "editor.html"), (L.W, L.H), views,
                        title="managed services",
                        live={name: st.name for name, st in VIEWS.items()})
    from svg_flow_animator import overrides as ov
    print(f"{len(ov.HANDLES)} movable handles -> {os.path.relpath(path)}")
    print(ov.summary())


def _arg(flag):
    for a in sys.argv[1:]:
        if a.startswith(flag + "="):
            return a.split("=", 1)[1]
    return None


def main():
    argv = sys.argv[1:]
    if "--list-sections" in argv:
        for c in CHAPTERS:
            a, b = section_span(c)
            print(f"{c:<14} {story.CHAPTER_TITLES.get(c, ''):<30} "
                  f"{(b - a) / FPS:5.1f}s")
        return
    if "--editor" in argv:
        return build_editor()
    if "--serve" in argv:
        # Preview renders sit well above this; a blank one would not.
        return live_server.serve(HERE, "gen_frames", (L.W, L.H), min_png=60_000)
    if "--poster" in argv:
        return build_poster()

    section = _arg("--section")
    targets = CHAPTERS if "--all-sections" in argv else ([section] if section else [])
    for c in targets:
        print(f"==> section {c}")
        build_gif(os.path.join(HERE, "sections", f"{c}{suffix()}.gif"),
                  section_span(c), scope={c})
    if not targets:
        print("==> full story")
        build_gif(os.path.join(HERE, f"managed-services{suffix()}.gif"))


if __name__ == "__main__":
    main()
