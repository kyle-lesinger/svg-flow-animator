"""
The disasters example's bottleneck slide: a queue that backs up behind a
narrow neck, then drains once the neck opens into the cloud architecture.

The queue is computed rather than simulated, so its promises can be checked
directly: first come first served, one dot through the neck at a time, a line
that grows while it is shut and is gone by the end, and many times the
throughput once it opens. The rendered frames are checked for the words the
slide exists to say.

Subprocess-run with overrides pinned empty, like the other slides' tests.
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest

try:
    from . import _support as sup
except ImportError:
    import _support as sup

PROBE = r'''
import json, re, sys
sys.path.insert(0, %(here)r)
import gen_frames as G, bottleneck as B

def has(doc, s):
    return ">%%s</text>" %% G.esc(s) in doc

def leaks(doc):
    return len(re.findall(r'<(rect|ellipse)[^>]*stroke="[^"]*"[^>]*>', doc))

shut, last = B.bottleneck_svg(B.OPEN_AT - 1), B.bottleneck_svg(B.TOTAL - 1)
neck = [B.DEP[i] for i in range(B.N) if B.MODE[i] == "neck"]
window = B.OPEN_AT - 75
before = sum(1 for t in B.ARRIVALS if 75 <= t < B.OPEN_AT)
after = sum(1 for t in B.ARRIVALS if B.OPEN_AT <= t < B.OPEN_AT + window)
outside = 0
for f in range(0, B.TOTAL, 5):
    m = B.morph(f)
    for i in range(B.N):
        for x, y in B.position(i, f):
            if B.MOUTH_X < x < B.NECK_END and abs(B.inside(x, y, m) - y) > 0.5:
                outside += 1
# Every place the slide writes words. A dot inside one is a dot over text.
always = [B.header_rect(k) for k in range(3)]
always += [(0, 0, 1600, 100), B.CAPTION, (0, 0, 120, 900), (1290, 0, 310, 900)]
# the problem's stations are only words while they are drawn
stations = [(x - 58, B.MID_Y - 112, 116, 56) for x in B.STATIONS]
over_text = []
for f in range(0, B.TOTAL, 3):
    zones = always + (stations if f < B.OPEN_AT + 20 else [])
    for i in range(B.N):
        for x, y in B.position(i, f):
            for zx, zy, zw, zh in zones:
                if zx - 5 <= x <= zx + zw + 5 and zy - 5 <= y <= zy + zh + 5:
                    over_text.append((f, i, round(x), round(y)))
print(json.dumps(dict(
    over_text=over_text[:5], n_over_text=len(over_text),
    style=G.S.name, slides=list(G.slides()), span=G.section_span("bottleneck"),
    total=B.TOTAL, fps=B.FPS, max_seconds=B.MAX_SECONDS,
    gif=G.section_gif("bottleneck"),
    via_section_frame=G.section_frame(7, "bottleneck") == B.bottleneck_svg(7),
    # FIFO where there is a line: through the neck, and the backlog's release.
    # Dots spawned after it opens never queue, and may pass the backlog.
    released=[B.DEP[i] for i in range(B.N)
              if B.MODE[i] == "open" and B.SPAWN[i] < B.OPEN_AT],
    neck=neck, neck_gaps=[b - a for a, b in zip(neck, neck[1:])],
    order=[a for a, _b in B.PROBLEM],
    first_split_x=min(x0 for _d, x0, _x1, split in B.NECK_PATH if split),
    copy_x=B.STATIONS[B.COPY_STATION], copy_name=B.PROBLEM[B.COPY_STATION][0],
    service=B.SERVICE, open_at=B.OPEN_AT,
    neck_after_open=[d for d in neck if d >= B.OPEN_AT],
    q_early=len(B.waiting(75)), q_shut=len(B.waiting(B.OPEN_AT - 1)),
    q_end=len(B.waiting(B.TOTAL - 1)), before=before, after=after,
    outside=outside,
    shut=dict(stations=[has(shut, a) for a, _b in B.PROBLEM],
              weeks=bool(re.search(r">\d+ weeks</text>", shut)),
              granules=bool(re.search(r">\d+ granules waiting</text>", shut)),
              title=has(shut, B.TITLE)),
    last=dict(title=has(last, B.TITLE), hours=has(last, "hours"),
              layers=[has(last, t) for t, _s, _f in B.SOLUTION],
              interoperable=has(last, "interoperable"),
              stations=sum(1 for a, _b in B.PROBLEM if has(last, a))),
    leaks={str(f): leaks(B.bottleneck_svg(f)) for f in (0, 200, B.OPEN_AT + 20,
                                                        B.TOTAL - 1)},
)))
'''


def probe(style):
    here = sup.DISASTERS_DIR
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
        fh.write("{}")
    try:
        env = dict(os.environ, FLOWGIF_STYLE=style, FLOWGIF_OVERRIDES=fh.name)
        out = subprocess.run([sys.executable, "-c", PROBE % dict(here=here)],
                             env=env, cwd=here, capture_output=True, text=True)
    finally:
        os.remove(fh.name)
    if out.returncode != 0:
        raise AssertionError(out.stderr[-2000:])
    return json.loads(out.stdout)


@sup.needs_disasters_assets
class BottleneckCase(unittest.TestCase):
    style = "sketch"

    @classmethod
    def setUpClass(cls):
        cls.P = probe(cls.style)

    def test_it_is_a_slide_that_plays_once(self):
        self.assertEqual(self.P["style"], self.style)
        self.assertIn("bottleneck", self.P["slides"])
        self.assertEqual(self.P["span"], [0, self.P["total"] - 1])
        self.assertEqual(self.P["gif"][0], -1)
        self.assertTrue(self.P["via_section_frame"])

    def test_it_lasts_thirty_seconds_at_most(self):
        # Asked for in so many words: the slide must not outrun its talk.
        self.assertLessEqual(self.P["total"] / self.P["fps"], 30)
        self.assertLessEqual(self.P["total"] / self.P["fps"], self.P["max_seconds"])

    def test_copies_are_made_last(self):
        # Download, then convert and analyze, then copy per tool -- and a dot
        # only becomes copies at the copy station, not before.
        self.assertEqual(self.P["order"], ["Download", "Convert,", "Copy"])
        self.assertEqual(self.P["copy_name"], "Copy")
        self.assertEqual(self.P["first_split_x"], self.P["copy_x"])

    def test_first_come_first_served_one_at_a_time(self):
        for line in (self.P["neck"], self.P["released"]):
            self.assertEqual(line, sorted(line), "a dot overtook the one ahead")
        self.assertGreaterEqual(min(self.P["neck_gaps"]), self.P["service"],
                                "the neck let two through at once")
        self.assertEqual(self.P["neck_after_open"], [],
                         "nothing should take the neck once it has opened")

    def test_the_line_grows_while_shut_and_drains_after(self):
        self.assertGreater(self.P["q_shut"], 2 * self.P["q_early"])
        self.assertEqual(self.P["q_end"], 0)

    def test_opening_it_multiplies_what_reaches_decision_makers(self):
        self.assertGreater(self.P["before"], 0)
        self.assertGreater(self.P["after"], 5 * self.P["before"])

    def test_no_dot_ever_covers_words(self):
        # Seen in review: dots running over the column labels made them hard
        # to read. Every label now sits where no dot can go.
        self.assertEqual(self.P["n_over_text"], 0, self.P["over_text"])

    def test_no_dot_ever_crosses_the_walls(self):
        self.assertEqual(self.P["outside"], 0)

    def test_it_names_the_bottleneck_then_the_architecture(self):
        shut, last = self.P["shut"], self.P["last"]
        self.assertEqual(shut["stations"], [True] * 3)
        self.assertTrue(shut["weeks"])
        self.assertTrue(shut["granules"], "a dot is one file -- a granule")
        self.assertFalse(shut["title"])
        self.assertTrue(last["title"])
        self.assertTrue(last["interoperable"])
        self.assertTrue(last["hours"])
        self.assertEqual(last["layers"], [True] * 3)
        self.assertEqual(last["stations"], 0, "a problem station outlived the fix")

    def test_no_flat_primitive_leaks_into_sketch(self):
        if self.style == "sketch":
            self.assertEqual(set(self.P["leaks"].values()), {0}, self.P["leaks"])


class TestBottleneckFlat(BottleneckCase):
    style = "flat"


if __name__ == "__main__":
    unittest.main()
