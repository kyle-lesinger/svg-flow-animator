#!/usr/bin/env python3
"""
A complete, self-contained example: three sources fan into a hub, the hub
feeds a processor, the processor writes to a store.

Draws everything from primitives, so it needs no external artwork and the
resulting GIF is safe to publish anywhere. Run it:

    python3 examples/minimal/demo.py                  # flat
    python3 examples/minimal/demo.py --style=sketch   # hand-drawn
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "..")))

from svg_flow_animator import geometry, render, styles, svg, timeline  # noqa: E402

S = styles.select()          # --style=sketch or FLOWGIF_STYLE=sketch

W, H = 960, 540
FPS = 15
INK, EDGE = "#22303c", "#46525e"
GREEN, AMBER, GLOW = "#0f9d58", "#ff7a00", "#1a6ae0"
PAPER = "#ffffff"

SOURCES = [("Ingest API", 140), ("Batch drop", 270), ("Partner feed", 400)]
SRC_BOX = (60, 0, 170, 54)          # y filled in per source
HUB = (330, 270)
PROC = (390, 236, 170, 68)
STORE = (660, 210, 220, 120)

OBSTACLES = [(40, 100, 300, 360), PROC, STORE]

STAGES = [
    timeline.Stage("collect", 6, 54, anchor=(150, 270),
                   text="Three independent producers write into the same "
                        "collection point.", hold=45),
    timeline.Stage("process", 120, 34, anchor=(475, 270),
                   text="One processor normalises whatever arrives, whatever "
                        "its shape.", hold=65),
    timeline.Stage("store", 232, 42, anchor=(770, 270),
                   text="Everything lands in a single catalog, so downstream "
                        "readers only learn one interface.", hold=57),
]
TOTAL = 360


def spoke(i):
    _, cy = SOURCES[i][0], SOURCES[i][1]
    return [(SRC_BOX[0] + SRC_BOX[2], cy), HUB]


def hub_to_proc():
    return [HUB, (PROC[0], 270)]


def proc_to_store():
    return [(PROC[0] + PROC[2], 270), (STORE[0], 270)]


def static_scene():
    out = [S.box(40, 100, 300, 360, "#f6f4e8", stroke=EDGE, rx=10),
           S.text(58, 128, "Producers", 16, fill=INK, weight="bold")]
    for label, cy in SOURCES:
        out.append(S.box(SRC_BOX[0], cy - 27, SRC_BOX[2], SRC_BOX[3],
                         "#ffffff", stroke=EDGE, rx=6))
        out.append(S.text(SRC_BOX[0] + SRC_BOX[2] / 2, cy + 5, label, 13.5,
                          fill=INK, anchor="middle"))
    out.append(S.circle(HUB[0], HUB[1], 5, fill=EDGE))
    out.append(S.box(*PROC, "#12243d", stroke="#12243d", rx=6))
    out.append(S.text(PROC[0] + PROC[2] / 2, 275, "Processor", 16,
                      fill="#ffffff", anchor="middle", weight="bold"))
    out.append(S.box(*STORE, "#c9f2d2", stroke=EDGE, rx=8))
    out.append(S.text(STORE[0] + STORE[2] / 2, 262, "Catalog", 26,
                      fill="#14603a", anchor="middle", weight="bold"))
    out.append(S.text(STORE[0] + STORE[2] / 2, 292, "one interface", 12.5,
                      fill="#14603a", anchor="middle"))
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
        body.append(timeline.callout(s, a, OBSTACLES, (W, H), width=330))

    return svg.document(W, H, "".join(body), S.bg)


def main():
    out_dir = os.path.join(HERE, "out")
    frame_dir = os.path.join(out_dir, "frames")
    os.makedirs(frame_dir, exist_ok=True)
    for stale in os.listdir(frame_dir):
        os.remove(os.path.join(frame_dir, stale))

    for f in range(TOTAL):
        with open(os.path.join(frame_dir, f"f{f:04d}.svg"), "w") as fh:
            fh.write(frame(f))
    print(f"wrote {TOTAL} frames ({TOTAL / FPS:.1f}s at {FPS}fps)")

    render.render_frames(frame_dir, W, H, background=S.bg)
    gif = os.path.join(out_dir, f"demo-{S.name}.gif" if S.name != "flat"
                       else "demo.gif")
    render.build_gif(frame_dir, gif, fps=FPS, width=W, height=H, colors=96)
    print("gif:", render.probe_gif(gif))


if __name__ == "__main__":
    main()
