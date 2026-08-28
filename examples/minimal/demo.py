#!/usr/bin/env python3
"""
A complete, self-contained example: three sources fan into a hub, the hub
feeds a processor, the processor writes to a store.

Draws everything from primitives, so it needs no external artwork and the
resulting GIF is safe to publish anywhere. Run it:

    python3 examples/minimal/demo.py                  # flat
    python3 examples/minimal/demo.py --style=sketch   # hand-drawn
    python3 examples/minimal/demo.py --editor         # -> out/editor.html

Every coordinate goes through `overrides`, so the editor is free: drag things
in the browser, download `overrides.json` next to this file, rerun. Nothing in
`svg_flow_animator.editor` knows anything about this diagram -- it reads the
same handle registry the layout below fills in.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "..")))

from svg_flow_animator import (editor, overrides as ov, render,  # noqa: E402
                               styles, svg, timeline)

S = styles.select()          # --style=sketch or FLOWGIF_STYLE=sketch
ov.use(os.path.join(HERE, "overrides.json"))     # missing file == all defaults

W, H = 960, 540
FPS = 15
INK, EDGE = "#22303c", "#46525e"
GREEN, AMBER, GLOW = "#0f9d58", "#ff7a00", "#1a6ae0"

# -------------------------------------------------------------- geometry ----
# Anything a person might reasonably want to nudge is requested through `ov`
# instead of being hardcoded. Each call registers a handle, and the handle
# registry is the entire interface the editor needs.
PRODUCERS = ov.rect("box.producers", (40, 100, 300, 360), "Producers")
PROC = ov.rect("box.processor", (390, 236, 170, 68), "Processor")
STORE = ov.rect("box.store", (660, 210, 220, 120), "Catalog")

HUB = ov.point("node.hub", (330, 270), "collection hub",
               size_key="node.hub.size")
HUB_SIZE = ov.scalar("node.hub.size", 11, "hub dot size")

SRC_W, SRC_H = 170, 54
SOURCES = []
for _i, (_label, _cy) in enumerate([("Ingest API", 140), ("Batch drop", 270),
                                    ("Partner feed", 400)]):
    _c = ov.point("src.%d" % _i, (145, _cy), _label)
    SOURCES.append(dict(
        label=_label,
        c=_c,
        # The caption is its own handle, so a crowded label can be nudged
        # without dragging the box (and its spoke) along with it -- but an
        # OFFSET, not a point. Stored as a delta from the source it names, it
        # stays attached however far the source is dragged; an absolute
        # position detaches the first time it is nudged.
        label_c=ov.offset("label.src.%d" % _i, (0, 5), "src.%d" % _i, _c,
                          _label + " (label)"),
    ))

LABEL_PRODUCERS = ov.point("label.producers", (58, 128), '"Producers" title')
LABEL_PROC = ov.point("label.processor", (PROC[0] + PROC[2] / 2, 275),
                      '"Processor" title')
LABEL_STORE = ov.point("label.store", (STORE[0] + STORE[2] / 2, 262),
                       '"Catalog" title')
LABEL_STORE_SUB = ov.point("label.store_sub", (STORE[0] + STORE[2] / 2, 292),
                           "catalog subtitle")

OBSTACLES = [PRODUCERS, PROC, STORE]

STAGES = [
    timeline.Stage("collect", 6, 54, anchor=(PRODUCERS[0] + 110, HUB[1]),
                   text="Three independent producers write into the same "
                        "collection point.", hold=45),
    timeline.Stage("process", 120, 34, anchor=(PROC[0] + PROC[2] / 2, HUB[1]),
                   text="One processor normalises whatever arrives, whatever "
                        "its shape.", hold=65),
    timeline.Stage("store", 232, 42, anchor=(STORE[0] + STORE[2] / 2, HUB[1]),
                   text="Everything lands in a single catalog, so downstream "
                        "readers only learn one interface.", hold=57),
]
TOTAL = 360


# ------------------------------------------------------------ connectors ----
# `ov.path()` registers only when the function owning it is CALLED, and these
# normally run during frame generation -- so an editor has to warm them up
# first or it shows no bendable lines at all.
def spoke(i):
    src = SOURCES[i]
    cx, cy = src["c"]
    return ov.path("flow.spoke.%d" % i, [(cx + SRC_W / 2, cy), HUB],
                   src["label"] + " -> hub")


def hub_to_proc():
    return ov.path("flow.hub_to_proc", [HUB, (PROC[0], HUB[1])],
                   "hub -> processor")


def proc_to_store():
    return ov.path("flow.proc_to_store",
                   [(PROC[0] + PROC[2], HUB[1]), (STORE[0], HUB[1])],
                   "processor -> catalog")


def warm_up():
    """Force every connector to register its handle."""
    for i in range(len(SOURCES)):
        spoke(i)
    hub_to_proc()
    proc_to_store()


# ----------------------------------------------------------------- scene ----
def static_scene(st=None):
    """The still picture. `st` selects the drawing backend; defaults to the
    one chosen on the command line."""
    st = st or S
    out = [st.box(*PRODUCERS, "#f6f4e8", stroke=EDGE, rx=10),
           st.text(LABEL_PRODUCERS[0], LABEL_PRODUCERS[1], "Producers", 16,
                   fill=INK, weight="bold")]
    for src in SOURCES:
        cx, cy = src["c"]
        lx, ly = src["label_c"]
        out.append(st.box(cx - SRC_W / 2, cy - SRC_H / 2, SRC_W, SRC_H,
                          "#ffffff", stroke=EDGE, rx=6))
        out.append(st.text(lx, ly, src["label"], 13.5, fill=INK,
                           anchor="middle"))
    out.append(st.circle(HUB[0], HUB[1], HUB_SIZE / 2, fill=EDGE))
    out.append(st.box(*PROC, "#12243d", stroke="#12243d", rx=6))
    out.append(st.text(LABEL_PROC[0], LABEL_PROC[1], "Processor", 16,
                       fill="#ffffff", anchor="middle", weight="bold"))
    out.append(st.box(*STORE, "#c9f2d2", stroke=EDGE, rx=8))
    out.append(st.text(LABEL_STORE[0], LABEL_STORE[1], "Catalog", 26,
                       fill="#14603a", anchor="middle", weight="bold"))
    out.append(st.text(LABEL_STORE_SUB[0], LABEL_STORE_SUB[1],
                       "one interface", 12.5, fill="#14603a", anchor="middle"))
    return "".join(out)


def frame(f):
    body = [static_scene()]
    prog = {s.key: s.progress(f) for s in STAGES}
    dash = f * 7.0

    if prog["collect"] >= 0:
        for i in range(len(SOURCES)):
            local = min(1.0, max(0.0, prog["collect"] * 1.5 - i * 0.08))
            if local > 0:
                body.append(timeline.flow(spoke(i), local, dash + i * 9,
                                          GREEN, AMBER, width=3))
    if prog["process"] >= 0:
        body.append(svg.glow(*PROC, color=GLOW, strength=1.0, rx=6))
        body.append(timeline.flow(hub_to_proc(), prog["process"], dash, GREEN,
                                  AMBER, width=3.5))
    if prog["store"] >= 0:
        body.append(svg.glow(*STORE, color=GLOW, strength=1.0))
        body.append(timeline.flow(proc_to_store(), prog["store"], dash, GREEN,
                                  AMBER, width=4))

    live = [(s.alpha(f), s) for s in STAGES]
    live = [(a, s) for a, s in live if a > 0]
    if live:
        a, s = max(live, key=lambda t: t[0])
        # Widest first: a wide bubble wraps to fewer lines and is therefore
        # shorter, which fits strips a tall one cannot. The narrower fallbacks
        # cover the tight side corridors.
        body.append(timeline.callout(s, a, OBSTACLES, (W, H),
                                     width=(380, 300, 240)))

    return svg.document(W, H, "".join(body), S.bg)


# ---------------------------------------------------------------- editor ----
def build_editor():
    """
    Generate the browser editor for this diagram.

    The whole of it is one `editor.build(...)` call. Both renders are offered
    as switchable views over the SAME handles, so a saved overrides.json
    applies to flat and hand-drawn alike.
    """
    warm_up()
    out_dir = os.path.join(HERE, "out")
    os.makedirs(out_dir, exist_ok=True)
    views = {
        name: (lambda st=st: (svg.document(W, H, static_scene(st), st.bg),
                              st.bg))
        for name, st in (("Flat", styles.FLAT), ("Hand-drawn", styles.SKETCH))
    }
    path = editor.build(os.path.join(out_dir, "editor.html"), (W, H),
                        backdrop=views, title="minimal demo")
    print(f"{len(ov.HANDLES)} movable handles -> {path}")
    print(ov.summary())
    return path


def main():
    if "--editor" in sys.argv:
        build_editor()
        return

    out_dir = os.path.join(HERE, "out")
    frame_dir = os.path.join(out_dir, "frames")
    os.makedirs(frame_dir, exist_ok=True)
    for stale in os.listdir(frame_dir):
        os.remove(os.path.join(frame_dir, stale))

    for f in range(TOTAL):
        with open(os.path.join(frame_dir, f"f{f:04d}.svg"), "w") as fh:
            fh.write(frame(f))
    print(f"wrote {TOTAL} frames ({TOTAL / FPS:.1f}s at {FPS}fps)")
    print(ov.summary())

    render.render_frames(frame_dir, W, H, background=S.bg)
    gif = os.path.join(out_dir, f"demo-{S.name}.gif" if S.name != "flat"
                       else "demo.gif")
    render.build_gif(frame_dir, gif, fps=FPS, width=W, height=H, colors=96)
    print("gif:", render.probe_gif(gif))


if __name__ == "__main__":
    main()
