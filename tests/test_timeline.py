"""
timeline: stage timing and auto-placed callouts.

A stage declares its SUBJECT, not its caption position -- placement is searched
for at render time, so the narration stays attached when the layout moves.
"""
import math
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

try:
    from . import _support as sup
except ImportError:
    import _support as sup

from svg_flow_animator import timeline  # noqa: E402
from svg_flow_animator.geometry import (place_near, rects_overlap,  # noqa: E402
                                        wrap)

SVGNS = "{http://www.w3.org/2000/svg}"
TEXT = ("One processor normalises whatever arrives, whatever shape it is in "
        "when it lands, and hands it on unchanged.")


def bubble_rect(markup):
    """(x, y, w, h) of the callout body."""
    root = sup.parse_fragment(markup)
    rects = [e for e in root.iter() if e.tag == SVGNS + "rect"]
    assert rects, "callout drew no body rect"
    r = rects[0]
    return tuple(float(r.get(a)) for a in ("x", "y", "width", "height"))


def dist(rect, anchor):
    x, y, w, h = rect
    return math.hypot(x + w / 2 - anchor[0], y + h / 2 - anchor[1])


# ================================================================== stage ===
class TestStageProgress(unittest.TestCase):
    S = timeline.Stage("collect", 100, 40)

    def test_negative_before_the_stage_begins(self):
        self.assertEqual(self.S.progress(0), -1.0)
        self.assertEqual(self.S.progress(99), -1.0)

    def test_zero_at_the_first_frame(self):
        self.assertEqual(self.S.progress(100), 0.0)

    def test_one_at_the_last_frame_and_after(self):
        self.assertEqual(self.S.progress(140), 1.0)
        self.assertEqual(self.S.progress(1000), 1.0)

    def test_monotone_and_bounded_once_started(self):
        prev = 0.0
        for f in range(100, 200):
            p = self.S.progress(f)
            self.assertGreaterEqual(p, prev)
            self.assertLessEqual(p, 1.0)
            prev = p

    def test_midpoint(self):
        self.assertAlmostEqual(self.S.progress(120), 0.5)

    def test_repr_names_the_span(self):
        self.assertIn("collect", repr(self.S))
        self.assertIn("100..140", repr(self.S))


class TestStageAlpha(unittest.TestCase):
    S = timeline.Stage("collect", 100, 40, hold=20)

    def test_invisible_well_outside_the_window(self):
        self.assertEqual(self.S.alpha(0), 0.0)
        self.assertEqual(self.S.alpha(92), 0.0)          # start - fade
        self.assertEqual(self.S.alpha(500), 0.0)

    def test_fully_visible_across_motion_and_hold(self):
        for f in range(100, 161):                        # start .. start+dur+hold
            self.assertEqual(self.S.alpha(f), 1.0, "dim at frame %d" % f)

    def test_fades_in_then_out(self):
        rising = [self.S.alpha(f) for f in range(93, 101)]
        self.assertEqual(rising, sorted(rising))
        falling = [self.S.alpha(f) for f in range(160, 168)]
        self.assertEqual(falling, sorted(falling, reverse=True))

    def test_stays_within_zero_and_one(self):
        for f in range(0, 300):
            a = self.S.alpha(f)
            self.assertGreaterEqual(a, 0.0)
            self.assertLessEqual(a, 1.0)

    def test_hold_extends_visibility(self):
        short = timeline.Stage("s", 100, 40, hold=0)
        self.assertEqual(short.alpha(150), 0.0)
        self.assertEqual(self.S.alpha(150), 1.0)


# =================================================================== flow ===
class TestFlow(unittest.TestCase):
    PTS = [(40, 40), (220, 90), (400, 60)]

    def test_parses_at_every_progress(self):
        for p in (0.0, 0.1, 0.28, 0.5, 1.0):
            with self.subTest(progress=p):
                sup.parse_fragment(timeline.flow(self.PTS, p, 12.5,
                                                 "#0f9d58", "#ff7a00"))

    def test_packets_are_held_back_until_the_reveal_finishes(self):
        # Packets on track the head has not reached is the tell that the
        # motion is faked.
        early = timeline.flow(self.PTS, 0.1, 0.0, "#0f9d58", "#ff7a00", reveal=0.28)
        late = timeline.flow(self.PTS, 0.9, 0.0, "#0f9d58", "#ff7a00", reveal=0.28)
        self.assertNotIn('stroke-dasharray="13 15"', early)
        self.assertIn('stroke-dasharray="13 15"', late)

    def test_the_head_reaches_the_end_of_the_path(self):
        root = sup.parse_fragment(timeline.flow(self.PTS, 1.0, 0.0,
                                                "#0f9d58", "#ff7a00"))
        circles = [e for e in root.iter() if e.tag == SVGNS + "circle"]
        self.assertTrue(circles)
        self.assertAlmostEqual(float(circles[0].get("cx")), 400.0, places=1)
        self.assertAlmostEqual(float(circles[0].get("cy")), 60.0, places=1)

    def test_the_reveal_grows_monotonically(self):
        def revealed(p):
            markup = timeline.flow(self.PTS, p, 0.0, "#0f9d58", "#ff7a00")
            head = markup.split('stroke-dasharray="', 1)[1].split(" ", 1)[0]
            return float(head)

        lengths = [revealed(p) for p in (0.0, 0.05, 0.1, 0.2, 0.28)]
        self.assertEqual(lengths, sorted(lengths))

    def test_pulse_is_silent_below_the_threshold(self):
        self.assertEqual(timeline.pulse(0, 0, 0.0, "#fff"), "")
        self.assertEqual(timeline.pulse(0, 0, 0.005, "#fff"), "")
        sup.parse_fragment(timeline.pulse(10, 10, 1.0, "#fff"))

    def test_pulse_ring_grows_with_strength(self):
        def r(s):
            return float(sup.parse_fragment(
                timeline.pulse(10, 10, s, "#fff"))[0].get("r"))
        self.assertLess(r(0.2), r(1.0))


# =============================================================== callouts ===
class TestCallout(unittest.TestCase):
    BOUNDS = (960, 540)
    STAGE = timeline.Stage("s", 0, 20, anchor=(480, 270), text=TEXT)

    def test_silent_when_invisible_or_wordless(self):
        self.assertEqual(timeline.callout(self.STAGE, 0.0, [], self.BOUNDS), "")
        self.assertEqual(timeline.callout(self.STAGE, 0.005, [], self.BOUNDS), "")
        silent = timeline.Stage("q", 0, 10, anchor=(1, 1), text=None)
        self.assertEqual(timeline.callout(silent, 1.0, [], self.BOUNDS), "")

    def test_parses_and_carries_every_word(self):
        markup = timeline.callout(self.STAGE, 1.0, [(0, 0, 200, 100)], self.BOUNDS)
        root = sup.parse_fragment(markup)
        texts = [e.text for e in root.iter() if e.tag == SVGNS + "text"]
        self.assertEqual(" ".join(texts).split(), TEXT.split())

    def test_alpha_reaches_the_group(self):
        markup = timeline.callout(self.STAGE, 0.5, [], self.BOUNDS)
        self.assertEqual(sup.parse_fragment(markup)[0].get("opacity"), "0.500")

    def test_stays_on_canvas(self):
        for anchor in [(20, 20), (940, 520), (480, 270), (940, 20)]:
            st = timeline.Stage("s", 0, 10, anchor=anchor, text=TEXT)
            x, y, w, h = bubble_rect(
                timeline.callout(st, 1.0, [(300, 200, 300, 150)], self.BOUNDS))
            with self.subTest(anchor=anchor):
                self.assertGreaterEqual(x, 0)
                self.assertGreaterEqual(y, 0)
                self.assertLessEqual(x + w, self.BOUNDS[0])
                self.assertLessEqual(y + h, self.BOUNDS[1])

    def test_avoids_the_obstacles_it_is_given(self):
        obstacles = [(0, 0, 600, 300)]
        st = timeline.Stage("s", 0, 10, anchor=(830, 150), text=TEXT)
        got = bubble_rect(timeline.callout(st, 1.0, obstacles, self.BOUNDS))
        self.assertFalse(rects_overlap(got, obstacles[0]))

    def test_the_tail_points_at_the_anchor_from_whichever_edge_faces_it(self):
        # A tail pinned to one edge points into space as soon as the bubble
        # lands beside its subject rather than above it.
        # One central obstacle with the subject on each of its four edges, so
        # the bubble is pushed to a different side every time.
        checked = 0
        obstacles = [(330, 170, 300, 200)]
        for anchor in [(480, 180), (480, 360), (340, 270), (620, 270)]:
            st = timeline.Stage("s", 0, 10, anchor=anchor, text="short note")
            markup = timeline.callout(st, 1.0, obstacles, self.BOUNDS, width=200)
            root = sup.parse_fragment(markup)
            paths = [e for e in root.iter() if e.tag == SVGNS + "path"]
            x, y, w, h = bubble_rect(markup)
            if x <= anchor[0] <= x + w and y <= anchor[1] <= y + h:
                continue          # bubble sits on its subject; no edge faces it
            with self.subTest(anchor=anchor):
                self.assertTrue(paths, "no tail drawn for a nearby subject")
                pts = [tuple(float(v) for v in tok.split(","))
                       for tok in paths[0].get("d").replace("M ", "")
                                          .replace(" Z", "").split(" L ")]
                cx, cy = x + w / 2, y + h / 2
                apex = max(pts, key=lambda p: math.hypot(p[0] - cx, p[1] - cy))
                # The apex must leave the bubble on the side the subject is on.
                dot = ((apex[0] - cx) * (anchor[0] - cx)
                       + (apex[1] - cy) * (anchor[1] - cy))
                self.assertGreater(dot, 0,
                                   "tail leaves from the edge facing away from "
                                   "the subject (apex %r, bubble centre %r)"
                                   % (apex, (cx, cy)))
                checked += 1
        self.assertEqual(checked, 4, "the test exercised almost nothing")

    def test_a_distant_subject_gets_no_tail(self):
        # A pointer spanning half the canvas stops reading as "this describes
        # that" and just looks like a stray arrow.
        st = timeline.Stage("s", 0, 10, anchor=(950, 530), text=TEXT)
        markup = timeline.callout(st, 1.0, [(0, 0, 900, 500)], self.BOUNDS,
                                  tail_max=10)
        root = sup.parse_fragment(markup)
        self.assertEqual([e for e in root.iter() if e.tag == SVGNS + "path"], [])

    def test_a_single_width_is_accepted_as_well_as_a_sequence(self):
        one = timeline.callout(self.STAGE, 1.0, [], self.BOUNDS, width=300)
        many = timeline.callout(self.STAGE, 1.0, [], self.BOUNDS, width=(300,))
        self.assertEqual(one, many)

    def test_falls_back_to_an_overlap_rather_than_drawing_nothing(self):
        blocked = [(0, 0, 960, 540)]
        markup = timeline.callout(self.STAGE, 1.0, blocked, self.BOUNDS)
        self.assertTrue(markup)
        sup.parse_fragment(markup)

    def test_widths_are_closest_fit_not_first_fit(self):
        """
        REGRESSION. This was a real bug; the width loop now keeps the closest.

        docs/ARCHITECTURE.md, "Callout placement":

            Try every width and keep the closest, not the first that fits.
            Returning on the first success means the widest candidate always
            wins wherever only one region admits it -- and "nearest to the
            anchor" silently becomes a no-op.

        `timeline.callout` did `for bw in widths: ... if spot: break`, returning
        the FIRST width that placed anywhere at all. In the
        layout below the 380-wide bubble fits only 228px from its subject
        while the 240-wide one fits 6px away, and the caption was drawn at the
        far end of the canvas from the thing it describes. Nothing errored.
        """
        obstacles = [(0, 0, 600, 300)]
        anchor = (830, 150)
        st = timeline.Stage("s", 0, 10, anchor=anchor, text=TEXT)
        widths = (380, 300, 240)

        # What the search would find if it kept the closest across all widths.
        best = None
        for bw in widths:
            chars = max(18, int((bw - 36) / (14.5 * 0.52)))
            h = len(wrap(TEXT, chars)) * 19 + 26
            spot = place_near(anchor, (bw, h), obstacles, self.BOUNDS,
                              pad=14, strict=True)
            if spot and (best is None or dist(spot, anchor) < dist(best, anchor)):
                best = spot
        self.assertIsNotNone(best)

        got = bubble_rect(timeline.callout(st, 1.0, obstacles, self.BOUNDS,
                                           width=widths))
        self.assertAlmostEqual(dist(got, anchor), dist(best, anchor), delta=1.0,
                               msg="callout landed %.0fpx from its subject when "
                                   "%.0fpx was available"
                                   % (dist(got, anchor), dist(best, anchor)))


if __name__ == "__main__":
    unittest.main()
