"""
The disasters example's opening section: STAC alone, then why it matters.

Runs in a subprocess, like the other example tests: importing the example
registers its handles in the global overrides module, which would leak into
every other test in the process. FLOWGIF_OVERRIDES is pinned to an empty file,
so these are assertions about the DEFAULT layout.

Needs the gitignored artwork -- gen_frames reads the Airflow blades at import.
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
import gen_frames as G, layout as L

def images(doc):
    return sorted(set(re.findall(r'<image href="([^"]+)"', doc)))

def has(doc, s):
    return ">%%s</text>" %% G.esc(s) in doc

panels = {}
for side, head, items in G.INTRO_PANELS:
    lines = G.intro_layout(side, head, items)
    panels[side] = dict(rect=L.intro_panel(side), head=head,
                        last_baseline=lines[-1][2],
                        texts=[l[3] for l in lines],
                        # each line exactly as the slide draws it, to rasterise
                        elements=[G.text(l[1], l[2], l[3], l[4], weight=l[5])
                                  for l in lines])

# Each point's first line, checked in the RENDERED frames on either side of
# its beat -- the timeline numbers alone would agree with themselves.
beats = []
for (side, head, pts), (_s, _e, starts) in zip(G.INTRO_PANELS, G.INTRO_SPANS):
    lines = G.intro_layout(side, head, pts)
    for j, t in enumerate(starts):
        line = [l[3] for l in lines if l[0] == j][0]
        beats.append(dict(start=t, line=line,
                          before=has(G.intro_svg(t), line),
                          after=has(G.intro_svg(t + G.FADE), line)))

first, last = G.intro_svg(0), G.intro_svg(G.INTRO_TOTAL - 1)

# STAC's scale in every rendered frame -- the pulse, read off the frames
def stac_scale(doc):
    m = re.search(r'class="stac" transform="[^"]*scale\(([0-9.]+)\)', doc)
    return float(m.group(1)) if m else None
scales = [stac_scale(G.intro_svg(f)) for f in range(G.INTRO_TOTAL)]
full = G.intro_svg(G.INTRO_HOLD_END - 1)
left_only = G.intro_svg(G.INTRO_SPANS[1][0] - 1)
print(json.dumps(dict(
    style=G.S.name, fps=G.FPS, total=G.INTRO_TOTAL, main_total=G.TOTAL,
    first_section=G.sections()[0][0], span=G.section_span(G.INTRO),
    via_section_frame=G.section_frame(5, G.INTRO) == G.intro_svg(5),
    stac=L.BOX_STAC, canvas=(L.W, L.H), panels=panels, beats=beats,
    pad=G.INTRO_PAD, scales=scales, alone=G.INTRO_STAC_ALONE,
    close_at=G.INTRO_SPANS[-1][1],
    last_glow=G.intro_stac_pulse(G.INTRO_TOTAL - 1)[0],
    first_images=images(first), stac_images=sorted([L.A_STAC, L.A_VEDA]),
    first_has_panel_text=any(has(first, t) for p in panels.values()
                             for t in p["texts"]),
    last_missing=[t for p in panels.values() for t in p["texts"]
                  if not has(last, t)],
    last_images=images(last),
    loops=dict([(k, G.section_loop(k)) for k, _l, _r in G.sections()]
               + [("full", G.section_loop(None))]),
    slides=list(G.slides()),
    full_missing=[t for p in panels.values() for t in p["texts"]
                  if not has(full, t)],
    left_only_has_left=has(left_only, panels["left"]["head"]),
    left_only_has_right=has(left_only, panels["right"]["head"]),
    full_leaks=len(re.findall(r'<(rect|ellipse)[^>]*stroke="[^"]*"[^>]*>', full)),
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
class IntroCase(unittest.TestCase):
    style = "sketch"

    @classmethod
    def setUpClass(cls):
        cls.P = probe(cls.style)

    def test_it_is_the_first_section_and_covers_its_own_timeline(self):
        self.assertEqual(self.P["style"], self.style)
        self.assertEqual(self.P["first_section"], "intro")
        self.assertEqual(self.P["span"], [0, self.P["total"] - 1])
        self.assertTrue(self.P["via_section_frame"],
                        "--section=intro must render the intro, not the film")

    def test_it_is_short(self):
        # The opening, not another chapter of the film.
        self.assertLess(self.P["total"], self.P["main_total"])

    def test_frame_zero_is_stac_alone(self):
        self.assertEqual(self.P["first_images"], self.P["stac_images"],
                         "frame 0 should draw STAC and nothing else")
        self.assertFalse(self.P["first_has_panel_text"])

    def test_it_plays_once_and_the_chapters_keep_looping(self):
        loops = self.P["loops"]
        self.assertIn("intro", self.P["slides"])
        for k in self.P["slides"]:
            self.assertEqual(loops.pop(k), -1, "slide %s should play once" % k)
        self.assertEqual(set(loops.values()), {0},
                         "only the slides may play once: %r" % loops)

    def test_it_ends_on_the_whole_picture(self):
        # It plays once, so its last frame is what stays on screen.
        self.assertEqual(self.P["last_missing"], [])
        self.assertEqual(self.P["last_images"], self.P["stac_images"])

    def test_every_benefit_is_on_screen_once_revealed(self):
        self.assertEqual(self.P["full_missing"], [])

    def test_each_point_arrives_five_seconds_after_the_last(self):
        # One steady beat, across the change of panel too.
        starts = [b["start"] for b in self.P["beats"]]
        self.assertEqual({b - a for a, b in zip(starts, starts[1:])},
                         {5 * self.P["fps"]})
        for b in self.P["beats"]:
            self.assertFalse(b["before"], "%r is up before its beat" % b["line"])
            self.assertTrue(b["after"], "%r never arrives" % b["line"])

    def test_the_panels_arrive_one_side_at_a_time(self):
        self.assertTrue(self.P["left_only_has_left"])
        self.assertFalse(self.P["left_only_has_right"])

    def test_the_text_fits_its_panel(self):
        # The two styles wrap differently, which is why both classes run this.
        for side, p in self.P["panels"].items():
            x, y, w, h = p["rect"]
            self.assertLess(p["last_baseline"] + 10, y + h,
                            "%s panel's last line runs into its floor" % side)

    def test_stac_pulses_at_the_start_and_the_close_and_ends_at_rest(self):
        # STAC is the focal point. A pulse is a local peak of its scale.
        sc = self.P["scales"]
        self.assertNotIn(None, sc, "a frame without STAC's pulse group")
        peaks = [f for f in range(1, len(sc) - 1)
                 if sc[f] > 1.01 and sc[f - 1] < sc[f] >= sc[f + 1]]
        opening = [f for f in peaks if f < self.P["alone"]]
        closing = [f for f in peaks if f >= self.P["close_at"]]
        self.assertGreaterEqual(len(opening), 2, "no pulse while STAC is alone")
        self.assertGreaterEqual(len(closing), 2, "no pulse at the close")
        self.assertEqual(len(opening) + len(closing), len(peaks),
                         "STAC pulses while the panels are being told")
        # it plays once: the frame left on screen is STAC still lit, at rest
        self.assertAlmostEqual(sc[-1], 1.0, places=3)
        self.assertGreater(self.P["last_glow"], 0.3)

    @sup.needs_rsvg
    @sup.needs_magick
    def test_every_line_fits_its_panel_as_rendered(self):
        # The wrap width is an estimate of glyph advance, and the heading is
        # not wrapped at all -- only the rasterised text says whether a line
        # runs out through the panel's right edge. Each line alone on the
        # canvas, so its ink box is that line's and nothing else's.
        cw, ch = self.P["canvas"]
        for side, p in self.P["panels"].items():
            x, y, w, h = p["rect"]
            for s, el in zip(p["texts"], p["elements"]):
                self.assertLessEqual(
                    sup.ink_extent(el, cw, ch)[1], x + w - self.P["pad"] // 2,
                    "%s panel: %r runs past its right edge" % (side, s))

    def test_the_panels_clear_stac_and_stay_on_canvas(self):
        sx, sy, sw, sh = self.P["stac"]
        cw, ch = self.P["canvas"]
        for side, p in self.P["panels"].items():
            x, y, w, h = p["rect"]
            self.assertTrue(x + w < sx or x > sx + sw, "%s panel overlaps STAC" % side)
            self.assertTrue(0 <= x and x + w <= cw and 0 <= y and y + h <= ch,
                            "%s panel leaves the canvas" % side)

    def test_no_flat_primitive_leaks_into_the_revealed_frame(self):
        # build.sh checks f0000 for leaks, and the intro's f0000 has no panels
        # in it -- that guard cannot see this section's own shapes.
        if self.style == "sketch":
            self.assertEqual(self.P["full_leaks"], 0)


class TestIntroFlat(IntroCase):
    style = "flat"


if __name__ == "__main__":
    unittest.main()
