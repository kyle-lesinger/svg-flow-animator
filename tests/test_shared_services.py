"""
The shared_services example: every managed_services guard, rerun against it,
plus the one claim this variant exists to make -- each shared capability is
drawn ONCE, inside the purple box, and nowhere else.

The base classes are reached through the module, not imported by name, so the
test loader does not collect them a second time here.
"""
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

try:
    from . import test_managed_services as M
except ImportError:
    import test_managed_services as M

SHARED = os.path.join(ROOT, "examples", "shared_services")

# The three capabilities the purple box holds, by the label a viewer reads.
SHARED_LABELS = ("Algorithm Catalog", "Data Catalog", "Visualization Tools")


class TestSharedStoryAgreesWithLayout(M.TestStoryAgreesWithLayout):
    example = SHARED


class TestSharedConnectors(M.TestConnectors):
    example = SHARED


class TestSharedFrames(M.TestFrames):
    example = SHARED


class TestSharedUsersChapter(M.TestUsersChapter):
    example = SHARED


class TestSharedCaptionBand(M.TestCaptionBand):
    example = SHARED


class TestSharedSketchHasNoFlatLeaks(M.TestSketchHasNoFlatLeaks):
    example = SHARED


class TestSharedFlatStyleToo(M.TestFlatStyleToo):
    example = SHARED


class TestSharedRenders(M.TestRenders):
    example = SHARED


class TestNothingIsDuplicated(M.ManagedCase):
    example = SHARED

    def _inside(self, pt, rect):
        x, y, w, h = rect
        return x <= pt[0] <= x + w and y <= pt[1] <= y + h

    def test_each_shared_capability_appears_exactly_once(self):
        for label in SHARED_LABELS:
            hits = [k for k, n in self.P["nodes"].items() if n["label"] == label]
            self.assertEqual(len(hits), 1, f"{label!r} is drawn {len(hits)} times: {hits}")

    def test_each_shared_capability_sits_in_the_purple_box(self):
        box = self.P["boxes"]["box.shared"]
        for label in SHARED_LABELS:
            k, n = next((k, n) for k, n in self.P["nodes"].items() if n["label"] == label)
            self.assertEqual(n["account"], "shared", k)
            self.assertTrue(self._inside(n["c"], box), f"{k} is outside the purple box")

    def test_only_shared_nodes_live_in_the_purple_box(self):
        box = self.P["boxes"]["box.shared"]
        for k, n in self.P["nodes"].items():
            self.assertEqual(self._inside(n["c"], box), n["account"] == "shared", k)

    def test_the_purple_box_sits_between_blue_and_red_without_overlapping(self):
        blue, purple, red = (self.P["boxes"][k] for k in
                             ("box.managed", "box.shared", "box.external"))
        self.assertLessEqual(blue[1] + blue[3], purple[1], "purple overlaps blue")
        self.assertLessEqual(purple[1] + purple[3], red[1], "purple overlaps red")

    def test_no_line_points_at_a_removed_duplicate(self):
        for k, f in self.P["flows"].items():
            for end in (f["src"], f["dst"]):
                self.assertNotEqual(end, "orgviz", f"{k} still targets the old duplicate")


if __name__ == "__main__":
    unittest.main()
