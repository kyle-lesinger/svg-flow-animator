"""
workflow: declared diagrams, their automatic layout, and their animation.

The layout is only a default -- every node is an `ov.rect` -- but it is the
picture most people will ship, so it is held to: columns from the edges, no two
boxes overlapping, lines crossing as little as the graph allows, and a canvas
at the requested aspect.

`overrides` is module-global, so every case saves and restores its registry.
"""
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

from svg_flow_animator import overrides as ov  # noqa: E402
from svg_flow_animator import styles  # noqa: E402
from svg_flow_animator import workflow as wf  # noqa: E402

SVGNS = "{http://www.w3.org/2000/svg}"
PERSON = wf.Component(shape="pill")
TASK = wf.Component(fill="#a5d8ff", stroke="#1971c2")


class Isolated(unittest.TestCase):
    def setUp(self):
        self._saved = (dict(ov.HANDLES), dict(ov._data), ov._loaded_from, ov.PATH)
        ov.HANDLES.clear()
        ov._data = {}

    def tearDown(self):
        handles, data, loaded, path = self._saved
        ov.HANDLES.clear()
        ov.HANDLES.update(handles)
        ov._data, ov._loaded_from, ov.PATH = data, loaded, path


def review_like():
    """Reviewers -> tasks -> one subject, shaped like the real example."""
    d = wf.Diagram("Review")
    for k, colour in (("io", "#1971c2"), ("proc", "#2f9e44"), ("nb", "#f08c00"),
                      ("out", "#e03131")):
        d.node(k, k.upper(), TASK.but(stroke=colour), detail="what it covers")
    d.node("subject", "Subject", wf.Component(fill="#1e1e1e"))
    people = {"p1": ["proc", "out"], "p2": ["io", "nb"], "p3": ["nb"],
              "p4": ["proc", "nb"], "p5": ["proc", "out"], "p6": ["out"]}
    for p, tasks in people.items():
        d.node(p, p.title(), PERSON)
        for t in tasks:
            d.edge(p, t)
    for t in ("io", "proc", "nb", "out"):
        d.edge(t, "subject")
    d.group("People", list(people))
    d.group("Tasks", ["io", "proc", "nb", "out"])
    for t in ("io", "proc", "nb", "out"):
        d.beat(t)
    return d


def overlaps(a, b):
    return (a[0] < b[0] + b[2] and b[0] < a[0] + a[2]
            and a[1] < b[1] + b[3] and b[1] < a[1] + a[3])


class TestDeclare(unittest.TestCase):
    def test_an_edge_to_an_undeclared_node_is_refused(self):
        # A typo in a name must not quietly become a new box.
        d = wf.Diagram()
        d.node("a", "A")
        with self.assertRaises(ValueError):
            d.edge("a", "b")

    def test_a_node_cannot_be_declared_twice_or_point_at_itself(self):
        d = wf.Diagram()
        d.node("a", "A")
        with self.assertRaises(ValueError):
            d.node("a", "again")
        with self.assertRaises(ValueError):
            d.edge("a", "a")

    def test_a_repeated_edge_is_drawn_once(self):
        d = wf.Diagram()
        d.node("a", "A")
        d.node("b", "B")
        d.edge("a", "b")
        d.edge("a", "b")
        self.assertEqual(len(d.edges), 1)

    def test_but_derives_a_variant_without_touching_the_original(self):
        blue = TASK.but(fill="#000000")
        self.assertEqual(blue.fill, "#000000")
        self.assertEqual(blue.stroke, TASK.stroke)
        self.assertEqual(TASK.fill, "#a5d8ff")

    def test_an_unknown_shape_is_refused(self):
        with self.assertRaises(ValueError):
            wf.Component(shape="hexagon")


class TestColumns(unittest.TestCase):
    def test_a_node_sits_right_of_the_furthest_thing_pointing_at_it(self):
        d = wf.Diagram()
        for k in "abcd":
            d.node(k, k)
        d.edge("a", "b")
        d.edge("b", "c")
        d.edge("a", "c")
        d.edge("d", "c")
        col, _ = d.columns()
        self.assertEqual(col, {"a": 0, "b": 1, "c": 2, "d": 0})

    def test_a_cycle_still_settles(self):
        # "Right of everything pointing at it" has no answer on a cycle; the
        # edge closing it has to be left out or this never terminates.
        d = wf.Diagram()
        for k in "abc":
            d.node(k, k)
        d.edge("a", "b")
        d.edge("b", "c")
        d.edge("c", "a")
        col, fwd = d.columns()
        self.assertEqual(col, {"a": 0, "b": 1, "c": 2})
        self.assertNotIn(("c", "a"), fwd)
        self.assertEqual(len(d.layout()[0]), 3)


class TestOrder(unittest.TestCase):
    def test_reorders_a_column_to_uncross_lines(self):
        d = wf.Diagram()
        for k in ("p1", "p2", "t1", "t2"):
            d.node(k, k)
        d.edge("p1", "t2")
        d.edge("p2", "t1")          # declared order crosses these two
        layers, crossings = d.order()
        self.assertEqual(crossings, 0)
        pos = {k: i for layer in layers for i, k in enumerate(layer)}
        self.assertEqual(pos["p1"] < pos["p2"], pos["t2"] < pos["t1"])

    def test_the_review_graph_crosses_only_where_it_must(self):
        # p1 and p5 point at the same two tasks, so their lines must cross
        # once whatever the order. Nothing else needs to.
        _, crossings = review_like().order()
        self.assertEqual(crossings, 1)


class TestLayout(Isolated):
    def test_no_two_boxes_overlap_and_all_sit_on_the_canvas(self):
        d = review_like()
        rects, (w, h), _ = d.layout()
        items = list(rects.items())
        for i, (ka, a) in enumerate(items):
            self.assertTrue(0 <= a[0] and a[0] + a[2] <= w and 0 <= a[1] and a[1] + a[3] <= h, ka)
            for kb, b in items[i + 1:]:
                self.assertFalse(overlaps(a, b), f"{ka} overlaps {kb}")

    def test_the_canvas_has_the_requested_aspect(self):
        _, (w, h), _ = review_like().layout()
        self.assertAlmostEqual(w / h, 16 / 9, places=2)

    def test_a_column_shares_one_width(self):
        rects, _, _ = review_like().layout()
        self.assertEqual(len({rects[k][2] for k in ("io", "proc", "nb", "out")}), 1)

    def test_every_node_is_a_movable_box(self):
        d = review_like()
        d.geometry()
        for k in d.nodes:
            self.assertEqual(ov.HANDLES[f"node.{k}"]["kind"], "rect")
        self.assertEqual(ov.HANDLES["label.title"]["kind"], "point")

    def test_lines_and_frames_follow_a_moved_node(self):
        # The point of deriving them rather than storing them.
        d = review_like()
        before = d.geometry()
        x, y, w, h = before["rects"]["io"]
        ov._data = {"node.io": [x, y + 300, w, h]}
        d._geo = None
        after = d.geometry()
        i = next(i for i, e in enumerate(d.edges) if e[:2] == ("io", "subject"))
        self.assertAlmostEqual(after["paths"][i][0][1] - before["paths"][i][0][1], 300, delta=13)
        self.assertEqual(after["rects"]["io"][1], y + 300)

    def test_lines_sharing_a_side_leave_in_the_order_of_their_far_ends(self):
        d = review_like()
        g = d.geometry()
        mine = [i for i, e in enumerate(d.edges) if e[0] == "p1"]
        far = sorted(mine, key=lambda i: g["rects"][d.edges[i][1]][1])
        starts = [g["paths"][i][0][1] for i in far]
        self.assertEqual(starts, sorted(starts))
        self.assertGreater(starts[-1] - starts[0], 5)


class TestEdgeColour(unittest.TestCase):
    def test_target_first_then_source_then_ink(self):
        d = wf.Diagram()
        d.node("p", "P", PERSON)
        d.node("t", "T", TASK)
        d.node("s", "S", wf.Component(fill="#1e1e1e"))
        d.node("q", "Q", PERSON)
        d.edge("p", "t")
        d.edge("t", "s")
        d.edge("p", "q")
        d.edge("q", "s", color="#123456")
        st = styles.SKETCH
        self.assertEqual([d.edge_color(i, st) for i in range(4)],
                         ["#1971c2", "#1971c2", st.ink, "#123456"])


class TestAnimation(Isolated):
    def test_it_opens_and_closes_on_the_finished_picture(self):
        # Frame 0 is all that anything without APNG support shows, and the
        # loop has a seam unless the last frame matches the first.
        d, st = review_like(), styles.SKETCH
        still = d.frame_svg(None, st)
        self.assertEqual(d.frame_svg(0, st), still)
        self.assertEqual(d.frame_svg(d.total - 1, st), still)

    def test_every_beat_actually_moves(self):
        d, st = review_like(), styles.SKETCH
        still = d.frame_svg(None, st)
        stages, _ = d.stages()
        for s in stages:
            self.assertNotEqual(d.frame_svg(s.start + s.dur // 2, st), still, s.key)

    def test_the_receding_holds_flat_from_first_beat_to_last(self):
        # Easing back to the full picture between beats repaints nearly every
        # pixel each time; it more than doubled the APNG.
        d = review_like()
        stages, _ = d.stages()
        end = stages[-1].start + stages[-1].dur + stages[-1].hold
        for f in range(stages[0].start, end + 1):
            self.assertEqual(d._recede(f, stages), 1.0, f)

    def test_total_is_the_sum_of_its_parts(self):
        d = review_like()
        self.assertEqual(d.total, wf.INTRO + wf.RESET + 4 * (wf.BEAT + wf.HOLD + wf.GAP)
                         + wf.OUTRO)

    def test_sketch_frames_are_reproducible(self):
        # GOTCHAS: sketchy geometry must be seeded from identity, or it boils.
        st = styles.SKETCH
        a, b = review_like(), review_like()
        f = a.stages()[0][1].start + 5
        self.assertEqual(a.frame_svg(f, st), b.frame_svg(f, st))

    def test_no_flat_stroked_shape_leaks_into_sketch_mid_beat(self):
        d, st = review_like(), styles.SKETCH
        s = d.stages()[0][2]
        root = sup.parse_fragment(d.scene(s.start + s.dur // 2, st))
        leaks = [el for el in root.iter()
                 if el.tag in (SVGNS + "rect", SVGNS + "ellipse")
                 and el.get("stroke") not in (None, "none")]
        self.assertEqual(leaks, [])

    def test_frames_are_well_formed_in_both_styles(self):
        d = review_like()
        f = d.stages()[0][1].start + 10
        for st in (styles.FLAT, styles.SKETCH):
            sup.parse_fragment(d.scene(f, st))


if __name__ == "__main__":
    unittest.main()
