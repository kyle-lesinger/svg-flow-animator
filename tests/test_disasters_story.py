"""
The disasters example's story slide: the journey and the bottleneck in one
45-second picture -- a showcase globe, a shape per data format, a manual
bottleneck, then an automated cloud-native workflow.

The slide makes claims, so these count them in rendered frames: four formats
in, one format out and only after automated ingest; a queue that backs up and
then drains; nothing written over by a dot. The queue itself is funnel.py,
whose rules the bottleneck tests already pin -- they are re-checked here on
this slide's own schedule.

Subprocess-run with overrides pinned empty. Needs the gitignored artwork, the
Blue Marble texture, and ImageMagick to decode it.
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

TEXTURE = os.path.join(sup.DISASTERS_ASSETS, "blue-marble-2048.jpg")

PROBE = r'''
import json, re, sys
sys.path.insert(0, %(here)r)
import gen_frames as G, story as T, layout as L

def has(doc, s):
    return ">%%s</text>" %% G.esc(s) in doc

def count(doc, cls):
    return len(re.findall(r'class="%%s"' %% re.escape(cls), doc))

def leaks(doc):
    return len(re.findall(r'<(rect|ellipse)[^>]*stroke="[^"]*"[^>]*>', doc))

F = T.FUNNEL
frames = {f: T.story_svg(f) for f in (60, T.SQUEEZE + 20, T.OPEN_AT - 1,
                                      T.OPEN_AT + T.FIX_BEAT + 20, T.TOTAL - 1)}
show, shut, last = frames[60], frames[T.OPEN_AT - 1], frames[T.TOTAL - 1]

# where every dot is, and what shape, across the whole slide
wrong_shape, problem_circles, over_text = 0, 0, []
always = [T.header_rect(k) for k in range(4)]
always += [(0, 0, 1600, 100), T.CAPTION, (T.DX - 10, 0, 310, 900),
           (80, T.LEGEND_Y - 20, 420, 70)]
stations = [(x - 58, T.MID_Y - 112, 116, 56) for x in T.STATIONS]
for f in range(0, T.TOTAL, 3):
    zones = always + (stations if f < T.OPEN_AT + 20 else [])
    for i in range(T.N):
        for x, y in T.dot_positions(i, f):
            shape = T.shape_of(i, x)
            if F.mode[i] == "open" and x >= T.COL_X[T.INGEST] and shape != "circle":
                wrong_shape += 1
            if F.mode[i] == "neck" and shape == "circle":
                problem_circles += 1
            for zx, zy, zw, zh in zones:
                if zx - 5 <= x <= zx + zw + 5 and zy - 5 <= y <= zy + zh + 5:
                    over_text.append((f, i, round(x), round(y)))

neck = [F.dep[i] for i in range(F.n) if F.mode[i] == "neck"]
window = T.OPEN_AT - T.SQUEEZE
print(json.dumps(dict(
    style=G.S.name, slides=list(G.slides()), span=G.section_span("story"),
    total=T.TOTAL, fps=T.FPS, gif=G.section_gif("story"),
    via_section_frame=G.section_frame(9, "story") == T.story_svg(9),
    big_r=T.globe_at(60).r, small_r=T.globe_at(T.TOTAL - 1).r, BIG=T.BIG, SMALL=T.SMALL,
    shapes=list(T.SHAPES), cog=T.COG_SHAPE, n_sats=len(T.CAST),
    csda=[dict(name=c["name"], spot=bool(c.get("spot"))) for c in T.CAST
          if "CSDA" in c["name"]],
    spot_cells=[len(pz["cells"]) for pz in T.PASSES if pz["spot"]],
    swath_cells=[len(pz["cells"]) for pz in T.PASSES if not pz["spot"]],
    umbra_in_showcase=any("Umbra" in T.story_svg(f) for f in range(0, T.GLIDE[1], 5)),
    colors=T.SAT_COLOR,
    show=dict(pipeline=has(show, "Decision makers"), dots=count(show, "dot square")
              + count(show, "dot triangle") + count(show, "dot diamond")
              + count(show, "dot cross") + count(show, "dot star")
              + count(show, "dot circle")),
    legend_shut=[count(shut, "key %%s" %% s) for s in T.SHAPES],
    legend_cog_shut=count(shut, "key circle"),
    legend_cog_last=count(last, "key circle"),
    shut=dict(circles=count(shut, "dot circle"),
              granules=bool(re.search(r">\d+ granules waiting</text>", shut)),
              stations=[has(shut, a) for a, _b in T.PROBLEM],
              weeks=bool(re.search(r">\d+ weeks</text>", shut))),
    last=dict(title=has(last, T.TITLE), hours=has(last, "hours"),
              delivered=bool(re.search(r">\d+ granules delivered</text>", last)),
              # the ingest title is set on two lines; the rest whole
              columns=[has(last, t.split(" ")[0] if k == T.INGEST else t)
                       for k, (t, _s, _f) in enumerate(T.COLUMNS)],
              interoperable="interoperable" in last,
              stations=sum(1 for a, _b in T.PROBLEM if has(last, a))),
    wrong_shape=wrong_shape, problem_circles=problem_circles,
    n_over=len(over_text), over=over_text[:5],
    neck=neck, service=F.service,
    q_squeeze=len(F.waiting(T.SQUEEZE)), q_shut=len(F.waiting(T.OPEN_AT - 1)),
    q_end=len(F.waiting(T.TOTAL - 1)),
    before=sum(1 for t in F.arrivals if T.SQUEEZE <= t < T.OPEN_AT),
    after=sum(1 for t in F.arrivals if T.OPEN_AT <= t < T.OPEN_AT + window),
    leaks={str(f): leaks(d) for f, d in frames.items()},
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
@sup.needs_magick
@unittest.skipUnless(os.path.exists(TEXTURE), "Blue Marble texture absent")
class StoryCase(unittest.TestCase):
    style = "sketch"

    @classmethod
    def setUpClass(cls):
        cls.P = probe(cls.style)

    def test_it_is_a_45_second_slide_that_plays_once(self):
        self.assertEqual(self.P["style"], self.style)
        self.assertIn("story", self.P["slides"])
        self.assertEqual(self.P["total"] / self.P["fps"], 45)
        self.assertEqual(self.P["span"], [0, self.P["total"] - 1])
        self.assertEqual(self.P["gif"], [-1, 256, "full"])
        self.assertTrue(self.P["via_section_frame"])

    def test_it_opens_on_the_globe_alone(self):
        self.assertEqual(self.P["big_r"], self.P["BIG"][2])
        self.assertEqual(self.P["small_r"], self.P["SMALL"][2])
        self.assertFalse(self.P["show"]["pipeline"])
        self.assertEqual(self.P["show"]["dots"], 0)

    def test_every_format_has_its_own_shape_and_none_is_the_cog(self):
        shapes = self.P["shapes"]
        self.assertEqual(len(set(shapes)), self.P["n_sats"])
        self.assertNotIn(self.P["cog"], shapes)
        self.assertEqual(len(set(self.P["colors"])), self.P["n_sats"])
        self.assertEqual(self.P["legend_shut"], [1] * self.P["n_sats"])
        self.assertEqual(self.P["legend_cog_shut"], 0)
        self.assertEqual(self.P["legend_cog_last"], 1)

    def test_a_commercial_csda_mission_is_tasked_not_swept(self):
        # Asked for by name: a CSDA example. Commercial SAR images only where
        # it is ordered to, so its scene must be a patch, not a swath.
        self.assertEqual([c["spot"] for c in self.P["csda"]], [True])
        self.assertTrue(self.P["spot_cells"])
        self.assertLess(max(self.P["spot_cells"]), min(self.P["swath_cells"]) / 2)
        self.assertTrue(self.P["umbra_in_showcase"],
                        "the CSDA mission should be seen before the bottleneck")

    def test_only_automated_ingest_makes_a_cog(self):
        self.assertEqual(self.P["problem_circles"], 0,
                         "the manual path converted a format by itself")
        self.assertEqual(self.P["shut"]["circles"], 0)
        self.assertEqual(self.P["wrong_shape"], 0,
                         "a dot passed automated ingest and kept its format")

    def test_the_bottleneck_backs_up_then_drains(self):
        neck = self.P["neck"]
        self.assertEqual(neck, sorted(neck))
        self.assertGreaterEqual(min(b - a for a, b in zip(neck, neck[1:])),
                                self.P["service"])
        self.assertGreater(self.P["q_shut"], 30)
        self.assertEqual(self.P["q_end"], 0)
        self.assertGreater(self.P["after"], 5 * max(1, self.P["before"]))

    def test_it_names_the_bottleneck_then_the_workflow(self):
        shut, last = self.P["shut"], self.P["last"]
        self.assertEqual(shut["stations"], [True] * 3)
        self.assertTrue(shut["weeks"])
        # a dot is one file -- a granule, not a dataset
        self.assertTrue(shut["granules"])
        self.assertTrue(last["delivered"])
        self.assertTrue(last["title"])
        self.assertTrue(last["interoperable"])
        self.assertTrue(last["hours"])
        self.assertEqual(last["columns"], [True] * 4)
        self.assertEqual(last["stations"], 0)

    def test_no_dot_ever_covers_words(self):
        self.assertEqual(self.P["n_over"], 0, self.P["over"])

    def test_no_flat_primitive_leaks_into_sketch(self):
        if self.style == "sketch":
            self.assertEqual(set(self.P["leaks"].values()), {0}, self.P["leaks"])


class TestStoryFlat(StoryCase):
    style = "flat"


if __name__ == "__main__":
    unittest.main()
