#!/usr/bin/env python3
"""
Sentinel-2 & Landsat algorithm review: who reviews what, and when.

    ./build.sh          review-workflow.apng + .png    who does what
                        review-timeline.apng + .png    when (DRAFT dates)
    ./build.sh flat     the same in the clean style, with a -flat suffix
    ./edit.sh           in a browser: drag the timeline's bars or type dates,
                        and move or resize any box of the workflow

Who does what is in the two tables below; when is in schedule.json, which the
timeline editor writes. Change either and rebuild; nothing else needs touching.
The names committed here are placeholders; real ones go in people.local.json.
"""
import json
import os
import sys
import threading
import webbrowser

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "..")))

from svg_flow_animator import gantt, gantt_editor, render, serve, styles  # noqa: E402
from svg_flow_animator import overrides as ov  # noqa: E402
from svg_flow_animator import workflow as wf  # noqa: E402

# The live-preview server passes candidate overrides in through the
# environment (svg_flow_animator.serve); otherwise, this example's own file.
ov.use(os.environ.get("FLOWGIF_OVERRIDES") or os.path.join(HERE, "overrides.json"))

os.environ.setdefault("FLOWGIF_STYLE", "sketch")
S = styles.select()

# ------------------------------------------------------------ the review ---
# key: (title, detail, outline colour, fill colour)
TASKS = {
    "io":      ("Code review", "reading files, COG conversion,\nwriting files",
                "#1971c2", "#a5d8ff"),
    "proc":    ("Code review", "data processing, band math", "#2f9e44", "#b2f2bb"),
    "nb":      ("Jupyter notebook review", None, "#f08c00", "#ffec99"),
    "out":     ("Data output review", None, "#e03131", "#ffc9c9"),
    "samples": ("Test samples", "sample scripts & conditions\nfor Landsat and Sentinel",
                "#6741d9", "#d0bfff"),
}

# Placeholder names, because this repository is public. Real ones go in
# people.local.json beside this file -- the same shape, {"Name": [task, ...]},
# and gitignored -- which is used instead whenever it exists.
PEOPLE = {
    "Reviewer A": ["proc", "out"],
    "Reviewer B": ["io", "nb"],
    "Reviewer C": ["nb"],
    "Reviewer D": ["proc", "nb"],
    "Reviewer E": ["proc", "out"],
    "Reviewer F": ["out", "samples"],
    "Reviewer G": ["out", "samples"],
}
PEOPLE_LOCAL = os.path.join(HERE, "people.local.json")
if os.path.exists(PEOPLE_LOCAL):
    with open(PEOPLE_LOCAL) as fh:
        PEOPLE = json.load(fh)

# When: schedule.json, {task: [start, end]} with both ends inclusive. It starts
# as PLACEHOLDER dates in the agreed order -- test samples first, then the code
# and notebook reviews in parallel, then the data output review -- with
# "draft": true, which stamps DRAFT on the timeline. ./edit.sh edits it.
SCHEDULE_PATH = os.path.join(HERE, "schedule.json")
SCHEDULE, DRAFT = gantt_editor.load(SCHEDULE_PATH)
_unscheduled = sorted(set(TASKS) - set(SCHEDULE))
if _unscheduled:
    raise SystemExit(f"schedule.json has no dates for: {', '.join(_unscheduled)}")

# ------------------------------------------------------------ components ---
# A component is a look, written once and shared by every node that has it.
# The tasks are one component in five colours.
PERSON = wf.Component(shape="pill", fill="#f1f3f5")
TASK = wf.Component(shape="box")
SUBJECT = wf.Component(fill="#1e1e1e")


# Reviewers are keyed by their place in the table (p1, p2, ...), never by
# name, so nothing the editor saves -- overrides.json -- can carry a name.
PERSON_KEYS = {name: f"p{i}" for i, name in enumerate(PEOPLE, 1)}


def reviewers(task):
    return [name for name, tasks in PEOPLE.items() if task in tasks]


IN_ORDER = sorted(TASKS, key=lambda k: SCHEDULE[k][0])      # stable: ties keep TASKS order

# ------------------------------------------------------- who does what ---
WORKFLOW = wf.Diagram("Sentinel-2 & Landsat Algorithm Review")
for _k, (_title, _detail, _stroke, _fill) in TASKS.items():
    WORKFLOW.node(_k, _title, TASK.but(stroke=_stroke, fill=_fill), detail=_detail)
WORKFLOW.node("algos", "Sentinel-2 & Landsat\nAlgorithms", SUBJECT)
for _name, _tasks in PEOPLE.items():
    WORKFLOW.node(PERSON_KEYS[_name], _name, PERSON)
    for _t in _tasks:
        WORKFLOW.edge(PERSON_KEYS[_name], _t)
for _k in TASKS:
    WORKFLOW.edge(_k, "algos")
WORKFLOW.group("Reviewers", list(PERSON_KEYS.values()))
WORKFLOW.group("Review tasks", list(TASKS))
for _k in IN_ORDER:                     # the animation follows the schedule
    WORKFLOW.beat(_k)

# ---------------------------------------------------------------- when ---
TIMELINE = gantt.Gantt("Sentinel-2 & Landsat Algorithm Review: timeline", draft=DRAFT)
for _k in IN_ORDER:
    _title, _detail, _stroke, _fill = TASKS[_k]
    TIMELINE.row(_k, _title, *SCHEDULE[_k], stroke=_stroke, fill=_fill, detail=_detail,
                 note=", ".join(reviewers(_k)))

# --------------------------------------------------------------- build ---
FPS = 15
SIZE = (1600, 900)                      # output pixels; the SVG scales to fit
FRAMES = os.path.join(HERE, "out", "frames")
MIN_PREVIEW = 20_000                    # a blank preview PNG is far smaller


def suffix():
    return "" if S.name == "sketch" else f"-{S.name}"


def preview_svg(path):
    """The svg_flow_animator.serve contract: write the still scene, return bg."""
    with open(path, "w") as fh:
        fh.write(WORKFLOW.frame_svg(None, S))
    return S.bg


def main():
    argv = sys.argv[1:]
    if "--editor" in argv:
        path = WORKFLOW.build_editor(os.path.join(HERE, "editor.html"),
                                     "S2 & Landsat review")
        print(f"{len(ov.HANDLES)} movable handles -> {os.path.relpath(path)}")
        print(ov.summary())
        page = gantt_editor.write_page(os.path.join(HERE, "timeline.html"),
                                       "S2 & Landsat review", back="editor.html")
        print(f"timeline editor -> {os.path.relpath(page)}")
        return
    if "--serve" in argv:
        port = int(os.environ.get("FLOWGIF_PORT", "8752"))
        print(f"workflow editor ->  http://localhost:{port}/editor.html")
        if "--no-open" not in argv:
            threading.Timer(1.0, webbrowser.open,
                            [f"http://localhost:{port}/timeline.html"]).start()
        return serve.serve(HERE, "review", WORKFLOW.size, port=port, min_png=MIN_PREVIEW,
                           page="timeline.html",
                           routes=gantt_editor.routes(TIMELINE, SCHEDULE_PATH, S))

    for chart, name in ((WORKFLOW, "review-workflow"), (TIMELINE, "review-timeline")):
        out = os.path.join(HERE, name + suffix())
        info = render.export(lambda f, c=chart: c.frame_svg(f, S), chart.total, SIZE,
                             out, FRAMES, background=S.bg, fps=FPS)
        print(f"  -> {os.path.relpath(out)}.apng  {info['frames']} frames "
              f"({info['frames'] / FPS:.1f}s), {info['width']}x{info['height']}, "
              f"{info['bytes'] / 1e6:.2f} MB")
        print(f"  -> {os.path.relpath(out)}.png   still, "
              f"{2 * SIZE[0]}x{2 * SIZE[1]}")


if __name__ == "__main__":
    main()
