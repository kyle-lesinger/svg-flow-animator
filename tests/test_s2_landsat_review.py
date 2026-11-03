"""
The s2_landsat_review example: the pictures say what its tables say.

Who does what lives in two tables in review.py and when in schedule.json, so
these check that the diagram and the timeline are built from them and nothing
else -- not the specific names, which are expected to change.

Everything runs in a subprocess: importing the example points the global
overrides module at its file and registers its handles. FLOWGIF_OVERRIDES is
pinned to an empty file, so a saved overrides.json cannot make this flaky.
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

try:
    from . import _support as sup
except ImportError:
    import _support as sup

EXAMPLE = os.path.join(ROOT, "examples", "s2_landsat_review")

PROBE = r'''
import json, re, shutil, sys, tempfile
sys.path.insert(0, %(here)r)
import review as R
from svg_flow_animator import gantt_editor, styles

W, T, st = R.WORKFLOW, R.TIMELINE, R.S
g = W.geometry()
stages, total = W.stages()
still = W.frame_svg(None, st)
mid = {s.key: W.frame_svg(s.start + s.dur // 2, st) for s in stages}
leak = re.compile(r'<(rect|ellipse)[^>]*stroke="[^"]*"[^>]*>')

tmp = tempfile.mkdtemp()
try:
    path = tmp + "/schedule.json"
    shutil.copy(R.SCHEDULE_PATH, path)
    routes = gantt_editor.routes(T, path, st)
    state = routes["/timeline/state"]({})
    dates = {r["key"]: [r["start"], r["end"]] for r in state["layout"]["rows"]}
    first = state["layout"]["rows"][0]["key"]
    dates[first] = ["2027-01-04", "2027-01-08"]
    routes["/timeline/save"]({"dates": dates, "draft": False})
    saved = gantt_editor.load(path)
    saved = ({k: [a.isoformat(), b.isoformat()] for k, (a, b) in saved[0].items()}, saved[1])
finally:
    shutil.rmtree(tmp)

print(json.dumps(dict(
    style=st.name,
    tasks=list(R.TASKS), people={n: t for n, t in R.PEOPLE.items()},
    keys=R.PERSON_KEYS,
    edges=[e[:2] for e in W.edges], beats=W.beats,
    schedule={k: [a.isoformat(), b.isoformat()] for k, (a, b) in R.SCHEDULE.items()},
    draft=R.DRAFT,
    rows=[dict(key=r["key"], start=r["start"].isoformat(), note=r["note"]) for r in T.rows],
    rects=g["rects"], size=W.size,
    frame0=W.frame_svg(0, st) == still, last=W.frame_svg(total - 1, st) == still,
    moves={k: v != still for k, v in mid.items()},
    leaks={k: len(leak.findall(v)) for k, v in mid.items()},
    timeline_loop=[T.frame_svg(0, st) == T.frame_svg(None, st),
                   T.frame_svg(T.total - 1, st) == T.frame_svg(None, st)],
    draft_stamp="DRAFT" in T.frame_svg(None, st),
    saved=saved, moved=[first, dates[first]],
)))
'''


def probe(style):
    fd, empty = tempfile.mkstemp(suffix=".json")
    with os.fdopen(fd, "w") as fh:
        fh.write("{}")
    try:
        env = dict(os.environ, FLOWGIF_STYLE=style, FLOWGIF_OVERRIDES=empty)
        proc = subprocess.run([sys.executable, "-c", PROBE % dict(here=EXAMPLE)],
                              env=env, cwd=EXAMPLE, capture_output=True, text=True)
    finally:
        os.remove(empty)
    if proc.returncode != 0:
        raise AssertionError("probe failed:\n" + proc.stderr[-3000:])
    return json.loads(proc.stdout.strip().splitlines()[-1])


class ReviewCase(unittest.TestCase):
    style = "sketch"
    _cache = {}

    @classmethod
    def setUpClass(cls):
        if cls.style not in cls._cache:
            cls._cache[cls.style] = probe(cls.style)
        cls.P = cls._cache[cls.style]


class TestTheDiagramIsTheTables(ReviewCase):
    def test_every_assignment_is_a_line_and_every_line_an_assignment(self):
        want = {(self.P["keys"][n], t) for n, ts in self.P["people"].items() for t in ts}
        got = {tuple(e) for e in self.P["edges"] if e[1] != "algos"}
        self.assertEqual(got, want)

    def test_every_task_has_a_reviewer_and_reaches_the_algorithms(self):
        edges = {tuple(e) for e in self.P["edges"]}
        for t in self.P["tasks"]:
            self.assertIn((t, "algos"), edges)
            self.assertTrue(any(t in ts for ts in self.P["people"].values()), t)

    def test_the_animation_follows_the_schedule(self):
        order = sorted(self.P["tasks"], key=lambda k: self.P["schedule"][k][0])
        self.assertEqual(self.P["beats"], order)

    def test_no_two_boxes_overlap_and_all_fit_the_canvas(self):
        w, h = self.P["size"]
        items = list(self.P["rects"].items())
        for i, (ka, a) in enumerate(items):
            self.assertTrue(0 <= a[0] and a[0] + a[2] <= w and 0 <= a[1] and a[1] + a[3] <= h)
            for kb, b in items[i + 1:]:
                self.assertFalse(a[0] < b[0] + b[2] and b[0] < a[0] + a[2]
                                 and a[1] < b[1] + b[3] and b[1] < a[1] + a[3],
                                 f"{ka} overlaps {kb}")


class TestTheTimelineIsTheSchedule(ReviewCase):
    def test_every_task_is_scheduled_and_ends_after_it_starts(self):
        self.assertEqual(set(self.P["schedule"]), set(self.P["tasks"]))
        for k, (a, b) in self.P["schedule"].items():
            self.assertLessEqual(a, b, k)

    def test_rows_run_in_date_order_and_name_their_reviewers(self):
        starts = [r["start"] for r in self.P["rows"]]
        self.assertEqual(starts, sorted(starts))
        for r in self.P["rows"]:
            names = [n for n, ts in self.P["people"].items() if r["key"] in ts]
            self.assertEqual(r["note"], ", ".join(names))

    def test_a_draft_says_so(self):
        self.assertEqual(self.P["draft_stamp"], self.P["draft"])

    def test_the_editor_saves_what_it_was_given(self):
        key, dates = self.P["moved"]
        self.assertEqual(self.P["saved"][0][key], dates)
        self.assertFalse(self.P["saved"][1])


class TestFrames(ReviewCase):
    def test_both_pictures_open_and_close_on_the_finished_picture(self):
        self.assertTrue(self.P["frame0"])
        self.assertTrue(self.P["last"])
        self.assertEqual(self.P["timeline_loop"], [True, True])

    def test_every_beat_moves(self):
        self.assertTrue(all(self.P["moves"].values()), self.P["moves"])


class TestFramesFlat(TestFrames):
    style = "flat"


class TestSketchLeaks(ReviewCase):
    def test_no_flat_stroked_shape_leaks_into_sketch_mid_beat(self):
        # Flat draws stroked rects on purpose; in sketch one is a missed
        # conversion. Checked mid-beat, where the glow and flows are on screen.
        self.assertEqual(self.P["style"], "sketch")
        self.assertEqual(set(self.P["leaks"].values()), {0}, self.P["leaks"])


if __name__ == "__main__":
    unittest.main()
