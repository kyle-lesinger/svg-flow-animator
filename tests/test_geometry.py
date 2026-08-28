"""geometry: easing, polylines, wrapping, collision-aware placement, viewBox fit."""
import math
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from svg_flow_animator import geometry as G  # noqa: E402


# ================================================================= easing ===
class TestEasing(unittest.TestCase):
    FNS = ("smooth", "ease_in_out")

    def each(self):
        for name in self.FNS:
            yield name, getattr(G, name)

    def test_endpoints_are_exact(self):
        for name, fn in self.each():
            with self.subTest(fn=name):
                self.assertEqual(fn(0.0), 0.0)
                self.assertEqual(fn(1.0), 1.0)

    def test_clamps_outside_unit_interval(self):
        for name, fn in self.each():
            with self.subTest(fn=name):
                self.assertEqual(fn(-5.0), 0.0)
                self.assertEqual(fn(-1e-9), 0.0)
                self.assertEqual(fn(1.0 + 1e-9), 1.0)
                self.assertEqual(fn(37.0), 1.0)

    def test_stays_in_bounds(self):
        for name, fn in self.each():
            with self.subTest(fn=name):
                for i in range(0, 201):
                    v = fn(i / 200.0)
                    self.assertGreaterEqual(v, 0.0)
                    self.assertLessEqual(v, 1.0)

    def test_monotonically_non_decreasing(self):
        # A non-monotone ease makes a flow connector visibly retreat mid-reveal.
        for name, fn in self.each():
            with self.subTest(fn=name):
                prev = -1.0
                for i in range(0, 201):
                    v = fn(i / 200.0)
                    self.assertGreaterEqual(v, prev, "dipped at t=%.3f" % (i / 200.0))
                    prev = v

    def test_symmetric_about_the_midpoint(self):
        for name, fn in self.each():
            with self.subTest(fn=name):
                self.assertAlmostEqual(fn(0.5), 0.5, places=12)
                for t in (0.1, 0.25, 0.4, 0.73):
                    self.assertAlmostEqual(fn(t) + fn(1 - t), 1.0, places=12)

    def test_zero_derivative_at_both_ends(self):
        # "Zero derivative at both ends" is the documented contract for smooth().
        eps = 1e-4
        for name, fn in self.each():
            with self.subTest(fn=name):
                self.assertLess((fn(eps) - fn(0.0)) / eps, 1e-3)
                self.assertLess((fn(1.0) - fn(1 - eps)) / eps, 1e-3)


# =============================================================== polyline ===
class TestPolyline(unittest.TestCase):
    L = [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0)]

    def test_seg_lengths(self):
        self.assertEqual(G.seg_lengths(self.L), [10.0, 10.0])
        self.assertEqual(G.seg_lengths([(0, 0), (3, 4)]), [5.0])
        self.assertEqual(len(G.seg_lengths(self.L)), len(self.L) - 1)

    def test_seg_lengths_degenerate(self):
        self.assertEqual(G.seg_lengths([(1, 1)]), [])
        self.assertEqual(G.seg_lengths([(1, 1), (1, 1)]), [0.0])

    def test_path_len(self):
        self.assertEqual(G.path_len(self.L), 20.0)
        self.assertEqual(G.path_len([(0, 0), (3, 4)]), 5.0)
        self.assertEqual(G.path_len([(2, 2)]), 0.0)

    def test_point_at_t_zero_is_exactly_the_first_point(self):
        self.assertEqual(G.point_at(self.L, 0.0), (0.0, 0.0))

    def test_point_at_t_one_is_exactly_the_last_point(self):
        # The loop's `or i == len(segs) - 1` fallthrough is what makes t=1 land
        # on the final vertex; an off-by-one here strands the flow head short of
        # its target, which reads as "the arrow does not reach the box".
        self.assertEqual(G.point_at(self.L, 1.0), (10.0, 10.0))
        self.assertEqual(G.point_at([(4, 5), (9, 5)], 1.0), (9.0, 5.0))

    def test_point_at_midpoint(self):
        self.assertEqual(G.point_at(self.L, 0.5), (10.0, 0.0))
        self.assertEqual(G.point_at(self.L, 0.25), (5.0, 0.0))
        self.assertEqual(G.point_at(self.L, 0.75), (10.0, 5.0))

    def test_point_at_clamps(self):
        self.assertEqual(G.point_at(self.L, -3.0), (0.0, 0.0))
        self.assertEqual(G.point_at(self.L, 4.0), (10.0, 10.0))

    def test_point_at_zero_length_path(self):
        # A collapsed connector must not divide by zero mid-frame.
        self.assertEqual(G.point_at([(7, 8), (7, 8)], 0.5), (7, 8))
        self.assertEqual(G.point_at([(7, 8), (7, 8), (7, 8)], 1.0), (7, 8))

    def test_point_at_advances_monotonically(self):
        prev = 0.0
        for i in range(0, 101):
            x, y = G.point_at(self.L, i / 100.0)
            travelled = (math.hypot(x, y) if x <= 10 and y == 0
                         else 10 + math.hypot(x - 10, y))
            self.assertGreaterEqual(travelled + 1e-9, prev)
            prev = travelled

    def test_poly_d(self):
        self.assertEqual(G.poly_d([(1, 2), (3.456, 4)]), "M 1.00,2.00 L 3.46,4.00")


class TestLabelWidth(unittest.TestCase):
    def test_scales_with_length_and_size(self):
        self.assertAlmostEqual(G.label_width("abcd", 10), 4 * 10 * 0.52)
        self.assertEqual(G.label_width("", 14), 0.0)
        self.assertGreater(G.label_width("abcd", 20), G.label_width("abcd", 10))


# =================================================================== wrap ===
class TestWrap(unittest.TestCase):
    def test_no_line_exceeds_width(self):
        text = ("One processor normalises whatever arrives, whatever shape it "
                "happens to be in when it lands here.")
        for width in (12, 18, 24, 40, 80):
            with self.subTest(width=width):
                for line in G.wrap(text, width):
                    if " " in line:                 # a lone over-long word may not fit
                        self.assertLessEqual(len(line), width)

    def test_preserves_every_word_in_order(self):
        text = "alpha beta gamma delta epsilon zeta"
        for width in (5, 11, 12, 100):
            self.assertEqual(" ".join(G.wrap(text, width)).split(), text.split())

    def test_empty_and_whitespace(self):
        self.assertEqual(G.wrap("", 20), [])
        self.assertEqual(G.wrap("   ", 20), [])

    def test_exact_fit_boundary(self):
        self.assertEqual(G.wrap("ab cd", 5), ["ab cd"])
        self.assertEqual(G.wrap("ab cd", 4), ["ab", "cd"])

    def test_word_longer_than_width_is_not_dropped(self):
        self.assertEqual(G.wrap("supercalifragilistic ok", 5),
                         ["supercalifragilistic", "ok"])


# ============================================================== placement ===
class TestRectsOverlap(unittest.TestCase):
    def test_clearly_separated(self):
        self.assertFalse(G.rects_overlap((0, 0, 10, 10), (50, 50, 10, 10)))

    def test_clearly_overlapping(self):
        self.assertTrue(G.rects_overlap((0, 0, 10, 10), (5, 5, 10, 10)))

    def test_containment_counts_as_overlap(self):
        self.assertTrue(G.rects_overlap((0, 0, 100, 100), (40, 40, 5, 5)))
        self.assertTrue(G.rects_overlap((40, 40, 5, 5), (0, 0, 100, 100)))

    def test_edge_contact_is_not_an_overlap(self):
        self.assertFalse(G.rects_overlap((0, 0, 10, 10), (10, 0, 10, 10)))
        self.assertFalse(G.rects_overlap((0, 0, 10, 10), (0, 10, 10, 10)))

    def test_pad_enforces_clearance(self):
        a, b = (0, 0, 10, 10), (12, 0, 10, 10)
        self.assertFalse(G.rects_overlap(a, b))
        self.assertFalse(G.rects_overlap(a, b, pad=2))     # exactly touching
        self.assertTrue(G.rects_overlap(a, b, pad=3))

    def test_symmetric(self):
        pairs = [((0, 0, 10, 10), (5, 5, 10, 10)), ((0, 0, 10, 10), (99, 0, 1, 1)),
                 ((0, 0, 10, 10), (10, 10, 10, 10))]
        for a, b in pairs:
            for pad in (0, 5):
                self.assertEqual(G.rects_overlap(a, b, pad),
                                 G.rects_overlap(b, a, pad))


class TestPlaceNear(unittest.TestCase):
    BOUNDS = (960, 540)

    def test_returns_the_closest_fit_not_the_first(self):
        # THE regression test. With no obstacles the very first candidate the
        # sweep looks at is the top-left margin; a first-fit implementation
        # returns that and "nearest to the anchor" silently becomes a no-op.
        anchor = (900, 500)
        x, y, w, h = G.place_near(anchor, (100, 40), [], self.BOUNDS)
        self.assertNotEqual((x, y), (12, 12), "returned the first slot, not the closest")
        self.assertLess(math.hypot(x + w / 2 - anchor[0], y + h / 2 - anchor[1]), 40)

    def test_closest_fit_beats_a_nearer_scan_order(self):
        # An obstacle covers the top-left, so first-fit and closest-fit differ
        # by more than scan order alone.
        anchor = (820, 460)
        obstacles = [(0, 0, 600, 300)]
        x, y, w, h = G.place_near(anchor, (120, 60), obstacles, self.BOUNDS)
        d = math.hypot(x + w / 2 - anchor[0], y + h / 2 - anchor[1])
        self.assertLess(d, 30, "landed %.1f from the anchor: %r" % (d, (x, y, w, h)))

    def test_result_never_overlaps_an_obstacle(self):
        obstacles = [(100, 100, 300, 200), (500, 60, 200, 400), (0, 460, 960, 80)]
        for anchor in [(120, 120), (480, 300), (700, 200), (900, 40)]:
            with self.subTest(anchor=anchor):
                got = G.place_near(anchor, (140, 70), obstacles, self.BOUNDS, pad=14)
                for o in obstacles:
                    self.assertFalse(G.rects_overlap(got, o, 14),
                                     "%r hits %r" % (got, o))

    def test_result_stays_inside_bounds(self):
        got = G.place_near((950, 530), (200, 90), [], self.BOUNDS, margin=12)
        x, y, w, h = got
        self.assertGreaterEqual(x, 12)
        self.assertGreaterEqual(y, 12)
        self.assertLessEqual(x + w, self.BOUNDS[0] - 12 + 12)
        self.assertLessEqual(y + h, self.BOUNDS[1] - 12 + 12)

    def test_strict_returns_none_when_nothing_fits(self):
        blocked = [(0, 0, 960, 540)]
        self.assertIsNone(G.place_near((480, 270), (200, 90), blocked,
                                       self.BOUNDS, strict=True))

    def test_non_strict_falls_back_to_the_margin(self):
        blocked = [(0, 0, 960, 540)]
        self.assertEqual(G.place_near((480, 270), (200, 90), blocked, self.BOUNDS),
                         (12, 12, 200, 90))

    def test_box_larger_than_canvas(self):
        # Empty sweep range; must not raise, must return the fallback.
        self.assertEqual(G.place_near((10, 10), (5000, 5000), [], self.BOUNDS),
                         (12, 12, 5000, 5000))

    def test_deterministic(self):
        args = ((400, 300), (150, 80), [(200, 200, 300, 120)], self.BOUNDS)
        self.assertEqual(G.place_near(*args), G.place_near(*args))


# =========================================================== fit_viewbox ====
class TestFitViewbox(unittest.TestCase):
    ASPECT = 16 / 9.0
    CANVAS = (0, 0, 1600, 900)

    def assert_aspect(self, box, aspect=None):
        _x, _y, w, h = box
        self.assertAlmostEqual(w / h, aspect or self.ASPECT, places=9,
                               msg="aspect drifted: %r" % (box,))

    def assert_contains(self, outer, inner):
        ox, oy, ow, oh = outer
        ix, iy, iw, ih = inner
        self.assertLessEqual(ox, ix + 1e-9)
        self.assertLessEqual(oy, iy + 1e-9)
        self.assertGreaterEqual(ox + ow, ix + iw - 1e-9)
        self.assertGreaterEqual(oy + oh, iy + ih - 1e-9)

    def test_very_wide_section(self):
        rect = (200, 200, 550, 80)          # a strip: 6.9:1
        got = G.fit_viewbox(rect, self.ASPECT, bounds=self.CANVAS)
        self.assert_aspect(got)
        self.assert_contains(got, rect)

    def test_tall_section(self):
        rect = (200, 100, 550, 640)         # nearly a column: 0.86:1
        got = G.fit_viewbox(rect, self.ASPECT, bounds=self.CANVAS)
        self.assert_aspect(got)
        self.assert_contains(got, rect)

    def test_aspect_holds_for_many_shapes(self):
        for rect in [(0, 0, 550, 80), (0, 0, 240, 200), (10, 10, 550, 640),
                     (300, 300, 1, 1), (100, 100, 900, 500), (5, 5, 80, 550)]:
            for aspect in (16 / 9.0, 4 / 3.0, 1.0, 2.4):
                with self.subTest(rect=rect, aspect=aspect):
                    self.assert_aspect(G.fit_viewbox(rect, aspect), aspect)

    def test_pad_grows_the_rect(self):
        rect = (200, 200, 300, 300)
        tight = G.fit_viewbox(rect, self.ASPECT, pad=0.0)
        padded = G.fit_viewbox(rect, self.ASPECT, pad=0.18)
        self.assertGreater(padded[2], tight[2])
        self.assert_aspect(tight)
        self.assert_aspect(padded)
        self.assert_contains(padded, rect)

    def test_stays_within_bounds(self):
        for rect in [(0, 0, 550, 80), (1050, 820, 550, 80), (0, 400, 300, 500),
                     (1400, 0, 200, 200)]:
            with self.subTest(rect=rect):
                x, y, w, h = G.fit_viewbox(rect, self.ASPECT, bounds=self.CANVAS)
                self.assertGreaterEqual(x, -1e-9)
                self.assertGreaterEqual(y, -1e-9)
                self.assertLessEqual(x + w, self.CANVAS[2] + 1e-9)
                self.assertLessEqual(y + h, self.CANVAS[3] + 1e-9)

    def test_clamping_shifts_rather_than_shrinks(self):
        # A view pushed against the edge must keep its aspect; shrinking it
        # would letterbox the output instead.
        near_edge = G.fit_viewbox((1200, 700, 300, 150), self.ASPECT,
                                  bounds=self.CANVAS)
        centred = G.fit_viewbox((700, 400, 300, 150), self.ASPECT,
                                bounds=self.CANVAS)
        self.assert_aspect(near_edge)
        self.assertAlmostEqual(near_edge[2], centred[2], places=9)
        self.assertAlmostEqual(near_edge[3], centred[3], places=9)

    def test_canvas_smaller_than_the_view_clips_to_the_canvas(self):
        # Documented give: there is nothing outside the canvas to show, so the
        # aspect yields rather than the view running off the edge.
        small = (0, 0, 400, 300)
        got = G.fit_viewbox((10, 10, 380, 280), self.ASPECT, bounds=small)
        self.assertEqual(got, (0.0, 0.0, 400.0, 300.0))

    def test_accepts_ints_and_returns_floats(self):
        got = G.fit_viewbox((1, 2, 3, 4), 1.0)
        self.assertTrue(all(isinstance(v, float) for v in got))


if __name__ == "__main__":
    unittest.main()
