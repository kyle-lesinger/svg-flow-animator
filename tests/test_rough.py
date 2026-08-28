"""
rough: sketchy geometry, and above all DETERMINISM.

docs/GOTCHAS.md, "Sketch-mode determinism": seed jitter from each shape's
IDENTITY (never the frame number), and give every shape its OWN PRNG. A shared
stream re-jitters everything downstream the moment a flow or caption appears,
and the whole diagram visibly boils. Nothing errors; the frames just churn.

`hash()` is out for the same reason: it is salted per process, so frames stop
being reproducible between runs. The cross-process tests below are the ones
that would actually catch a regression to `hash()`.
"""
import ast
import json
import os
import subprocess
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

try:
    from . import _support as sup
except ImportError:
    import _support as sup

from svg_flow_animator import rough as R, styles  # noqa: E402


BOX = (10.0, 20.0, 300.0, 200.0)
LINE = [(40.0, 40.0), (220.0, 90.0), (400.0, 60.0)]


def box_d(key, sw=2):
    o = R.Opt(R.seed_for("out", key), stroke_width=sw)
    pts = R.rounded_rect_points(*BOX, 8)
    return "".join(R.ops_to_d(p) for p in R.linear_path_continuous(pts + [pts[0]], o))


# ============================================================== the PRNG ====
class TestRandom(unittest.TestCase):
    def test_sequence_is_reproducible_for_a_seed(self):
        a = [R.Random(12345).next() for _ in range(20)]
        b = [R.Random(12345).next() for _ in range(20)]
        self.assertEqual(a, b)

    def test_different_seeds_diverge(self):
        self.assertNotEqual([R.Random(1).next() for _ in range(8)],
                            [R.Random(2).next() for _ in range(8)])

    def test_values_stay_in_the_unit_interval(self):
        rng = R.Random(99)
        for _ in range(500):
            v = rng.next()
            self.assertGreaterEqual(v, 0.0)
            self.assertLess(v, 1.0)

    def test_zero_seed_is_rewritten(self):
        # 0 means "use Math.random()" in JS; here it must become a fixed seed
        # or a shape whose crc32 happens to be 0 would jitter every run.
        self.assertEqual(R.Random(0).s, 1)
        self.assertEqual([R.Random(0).next() for _ in range(4)],
                         [R.Random(0).next() for _ in range(4)])

    def test_each_instance_is_independent(self):
        a, b = R.Random(7), R.Random(7)
        a.next(); a.next(); a.next()
        self.assertEqual(b.next(), R.Random(7).next())


# ================================================================ seeding ===
class TestSeedFor(unittest.TestCase):
    def test_stable_within_a_process(self):
        self.assertEqual(R.seed_for("box", "box.stac"), R.seed_for("box", "box.stac"))
        self.assertEqual(R.seed_for("out", (1, 2, 3)), R.seed_for("out", (1, 2, 3)))

    def test_distinct_identities_give_distinct_seeds(self):
        seeds = {R.seed_for("out", k) for k in
                 ("box.stac", "box.ingest", "node.hub", "flow.a", "flow.b")}
        self.assertEqual(len(seeds), 5)

    def test_never_returns_zero(self):
        # 0 would collapse to Random's fallback and merge two shapes' jitter.
        for k in range(400):
            self.assertNotEqual(R.seed_for("s", k), 0)

    def test_floats_are_quantised_not_repr_dependent(self):
        self.assertEqual(R.seed_for("x", 1.0005), R.seed_for("x", 1.0004999))
        self.assertNotEqual(R.seed_for("x", 1.000), R.seed_for("x", 1.002))

    def test_fits_in_32_bits(self):
        for k in ("a", "bb", "ccc", 1, 2.5, (3, 4)):
            self.assertTrue(0 < R.seed_for("t", k) <= 0xFFFFFFFF)

    def test_no_package_module_calls_builtin_hash(self):
        # A source-level guard, because a regression here is invisible in a
        # single run: everything looks fine until you render twice. Parsed as
        # an AST so prose about hash() in a docstring does not trip it.
        for path, text in sup.package_sources():
            tree = ast.parse(text, filename=path)
            for node in ast.walk(tree):
                if (isinstance(node, ast.Call)
                        and isinstance(node.func, ast.Name)
                        and node.func.id == "hash"):
                    self.fail("%s:%d calls hash(), which is salted per process "
                              "(PYTHONHASHSEED) -- use zlib.crc32"
                              % (os.path.basename(path), node.lineno))


# ================================================== cross-process identity ==
_PROBE = r"""
import json, sys
sys.path.insert(0, sys.argv[1])
from svg_flow_animator import rough as R, styles
pts = R.rounded_rect_points(10.0, 20.0, 300.0, 200.0, 8)
o = R.Opt(R.seed_for("out", "box.stac"), stroke_width=2)
out = {
    "seeds": [R.seed_for("box", "box.stac"), R.seed_for("out", (1, 2, 3.5)),
              R.seed_for("line", "flow.a", 3.14159)],
    "rect": "".join(R.ops_to_d(p) for p in R.linear_path_continuous(pts + [pts[0]], o)),
    "sketch_box": styles.SketchStyle().box(10, 20, 300, 200, "#c9f2d2",
                                           key="box.stac"),
}
print(json.dumps(out))
"""


class TestCrossProcessDeterminism(unittest.TestCase):
    """Same shape identity -> byte-identical geometry in a fresh interpreter."""

    def run_probe(self, hashseed):
        env = dict(os.environ, PYTHONHASHSEED=hashseed)
        env.pop("FLOWGIF_STYLE", None)
        proc = subprocess.run([sys.executable, "-c", _PROBE, ROOT],
                              env=env, capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr[-2000:])
        return json.loads(proc.stdout)

    def test_identical_under_different_pythonhashseed(self):
        # THE regression test for "hash() is salted per process". If any seed
        # were derived from hash(), these two runs would disagree.
        a = self.run_probe("0")
        b = self.run_probe("1")
        self.assertEqual(a["seeds"], b["seeds"])
        self.assertEqual(a["rect"], b["rect"])
        self.assertEqual(a["sketch_box"], b["sketch_box"])

    def test_matches_this_process(self):
        got = self.run_probe("random")
        self.assertEqual(got["seeds"],
                         [R.seed_for("box", "box.stac"),
                          R.seed_for("out", (1, 2, 3.5)),
                          R.seed_for("line", "flow.a", 3.14159)])
        pts = R.rounded_rect_points(*BOX, 8)
        o = R.Opt(R.seed_for("out", "box.stac"), stroke_width=2)
        here = "".join(R.ops_to_d(p)
                       for p in R.linear_path_continuous(pts + [pts[0]], o))
        self.assertEqual(got["rect"], here)


# ================================================ in-process determinism ====
class TestGeometryDeterminism(unittest.TestCase):
    def test_same_identity_same_geometry(self):
        self.assertEqual(box_d("box.stac"), box_d("box.stac"))

    def test_different_identity_different_geometry(self):
        self.assertNotEqual(box_d("box.stac"), box_d("box.ingest"))

    def test_linear_path_is_seeded_not_random(self):
        def once():
            return R.ops_to_d(R.linear_path(LINE, False, R.Opt(R.seed_for("l", "k"))))
        self.assertEqual(once(), once())

    def test_ellipse_is_seeded_not_random(self):
        def once():
            return R.ops_to_d(R.ellipse_ops(100, 100, 60, 40,
                                            R.Opt(R.seed_for("e", "k"))))
        self.assertEqual(once(), once())

    def test_hachure_is_seeded_not_random(self):
        poly = R.rounded_rect_points(0, 0, 120, 80, 6)

        def once():
            return R.ops_to_d(R.hachure_ops(poly, R.Opt(R.seed_for("f", "k"),
                                                        stroke_width=2)))
        self.assertEqual(once(), once())

    def test_roughness_zero_is_not_jittered(self):
        o = R.Opt(R.seed_for("out", "k"), roughness=0)
        ops = R.double_line(0, 0, 100, 0, o)
        self.assertEqual(len(ops), 2, "roughness=0 must be a single pass")


class TestPerShapePRNG(unittest.TestCase):
    """
    Each shape gets its OWN PRNG.

    With one shared stream, drawing an extra shape first shifts every later
    shape's jitter -- so a connector appearing at frame 120 re-rolls the whole
    static scene and the diagram boils. These tests draw the same shape with
    and without a neighbour and demand byte-identical output.
    """

    def fresh(self):
        st = styles.SketchStyle()
        st._cache = {}                # _cache is a CLASS attribute; isolate it
        return st

    def test_a_neighbour_does_not_disturb_a_shape(self):
        alone = self.fresh().box(10, 20, 300, 200, "#c9f2d2", key="box.stac")
        st = self.fresh()
        st.box(500, 40, 120, 90, "#ffffff", key="box.other")       # drawn first
        st.poly([(0, 0), (50, 60)], "#000", key="flow.noise")
        st.ellipse(700, 300, 30, 30, key="node.noise")
        together = st.box(10, 20, 300, 200, "#c9f2d2", key="box.stac")
        self.assertEqual(alone, together)

    def test_drawing_order_does_not_matter(self):
        a = self.fresh()
        first = (a.box(10, 20, 300, 200, "#c9f2d2", key="box.stac")
                 + a.box(500, 40, 120, 90, "#ffffff", key="box.other"))
        b = self.fresh()
        second_b = b.box(500, 40, 120, 90, "#ffffff", key="box.other")
        second_a = b.box(10, 20, 300, 200, "#c9f2d2", key="box.stac")
        self.assertEqual(first, second_a + second_b)

    def test_static_scenery_is_identical_across_frames(self):
        # Diff a never-animated region across two "frames": it must not move.
        def scene(style, extra):
            out = [style.box(10, 20, 300, 200, "#c9f2d2", key="box.stac"),
                   style.ellipse(400, 300, 40, 25, key="node.hub")]
            if extra:                     # a flow that only exists on frame 2
                out.append(style.poly([(0, 0), (100, 100)], "#0f0", key="flow.late"))
            return "".join(out[:2])

        f1 = self.fresh()
        f2 = self.fresh()
        self.assertEqual(scene(f1, False), scene(f2, True))

    def test_a_pulsing_ring_is_seeded_on_its_centre_not_its_radius(self):
        # Corollary from GOTCHAS: seeding on the animating radius re-rolls the
        # ring every frame. Passing an explicit key must decouple the two.
        st = self.fresh()
        frames = [st.ellipse(200, 200, r, r, stroke="#f00", key="pulse.hub")
                  for r in (30.0, 30.0, 30.0)]
        self.assertEqual(len(set(frames)), 1)
        seeds = {R.seed_for("ell", "pulse.hub") for _ in range(3)}
        self.assertEqual(len(seeds), 1)


# ============================================================== primitives ==
class TestPrimitives(unittest.TestCase):
    def test_rounded_rect_points_stay_inside_the_rect(self):
        for r in (0, 4, 8, 40, 1000):
            with self.subTest(r=r):
                for x, y in R.rounded_rect_points(10, 20, 300, 200, r):
                    self.assertGreaterEqual(x, 10 - 1e-9)
                    self.assertGreaterEqual(y, 20 - 1e-9)
                    self.assertLessEqual(x, 310 + 1e-9)
                    self.assertLessEqual(y, 220 + 1e-9)

    def test_rounded_rect_radius_is_clamped(self):
        huge = R.rounded_rect_points(0, 0, 100, 40, 9999)
        self.assertTrue(all(0 <= y <= 40 for _x, y in huge))

    def test_linear_path_needs_two_points(self):
        o = R.Opt(1)
        self.assertEqual(R.linear_path([], False, o), [])
        self.assertEqual(R.linear_path([(0, 0)], False, o), [])

    def test_linear_path_continuous_has_one_move_per_pass(self):
        # stroke-dasharray restarts at every `M`, so a multi-M pass makes an
        # animated connector reveal in several pieces at once.
        passes = R.linear_path_continuous(LINE, R.Opt(R.seed_for("l", "k")))
        self.assertEqual(len(passes), 2)
        for ops in passes:
            self.assertEqual(sum(1 for op, _ in ops if op == "M"), 1)

    def test_ops_to_d_shape(self):
        d = R.ops_to_d([("M", (1.24, 2.0)), ("C", (1, 2, 3, 4, 5, 6))])
        self.assertEqual(d, "M1.2 2.0C1.0 2.0 3.0 4.0 5.0 6.0")

    def test_ops_length_is_close_to_the_true_length(self):
        o = R.Opt(R.seed_for("l", "k"))
        ops = R.linear_path_continuous([(0, 0), (400, 0)], o)[0]
        n = R.ops_length(ops)
        self.assertGreater(n, 360)
        self.assertLess(n, 460)

    def test_ops_length_of_nothing_is_zero(self):
        self.assertEqual(R.ops_length([]), 0.0)

    def test_hachure_lines_cover_the_polygon(self):
        poly = [(0, 0), (100, 0), (100, 80), (0, 80)]
        o = R.Opt(R.seed_for("f", "k"), stroke_width=2)
        lines = R.hachure_lines(poly, o)
        self.assertGreater(len(lines), 3)
        for a, b in lines:
            for x, y in (a, b):
                self.assertGreater(x, -20)
                self.assertLess(x, 120)
                self.assertGreater(y, -20)
                self.assertLess(y, 100)

    def test_wider_hachure_gap_means_fewer_lines(self):
        poly = [(0, 0), (100, 0), (100, 80), (0, 80)]
        tight = R.hachure_lines(poly, R.Opt(1, stroke_width=2, hachure_gap=4))
        loose = R.hachure_lines(poly, R.Opt(1, stroke_width=2, hachure_gap=20))
        self.assertGreater(len(tight), len(loose))


if __name__ == "__main__":
    unittest.main()
