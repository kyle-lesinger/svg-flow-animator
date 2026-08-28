"""
overrides: the handle registry, defaults vs overrides, active(), round-trip.

The registry is module-global state, so every test snapshots and restores it.
"""
import json
import os
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

try:
    from . import _support as sup
except ImportError:                                   # discovered as a top-level module
    import _support as sup

from svg_flow_animator import overrides as ov  # noqa: E402


class RegistryCase(unittest.TestCase):
    """Isolates the module-global registry so tests cannot leak into each other."""

    def setUp(self):
        self._saved = (dict(ov.HANDLES), dict(ov._data), ov._loaded_from, ov.PATH)
        ov.HANDLES.clear()
        ov._data = {}
        ov._loaded_from = None
        self.tmp = tempfile.mkdtemp(prefix="sfa-ov-")

    def tearDown(self):
        handles, data, loaded, path = self._saved
        ov.HANDLES.clear()
        ov.HANDLES.update(handles)
        ov._data = data
        ov._loaded_from = loaded
        ov.PATH = path
        for name in os.listdir(self.tmp):
            os.remove(os.path.join(self.tmp, name))
        os.rmdir(self.tmp)

    def write_overrides(self, data, name="overrides.json"):
        p = os.path.join(self.tmp, name)
        with open(p, "w") as fh:
            json.dump(data, fh)
        return p


# ============================================================== registry ====
class TestRegistration(RegistryCase):
    def test_every_kind_registers_a_handle(self):
        ov.point("node.hub", (10, 20), "hub")
        ov.rect("box.stac", (1, 2, 3, 4), "STAC")
        ov.path("flow.a", [(0, 0), (5, 5)], "A")
        ov.scalar("node.hub.size", 11, "hub size")
        self.assertEqual(set(ov.HANDLES), {"node.hub", "box.stac", "flow.a",
                                           "node.hub.size"})
        self.assertEqual([ov.HANDLES[k]["kind"] for k in
                          ("node.hub", "box.stac", "flow.a", "node.hub.size")],
                         ["point", "rect", "path", "scalar"])

    def test_label_defaults_to_the_key(self):
        ov.point("node.hub", (10, 20))
        self.assertEqual(ov.HANDLES["node.hub"]["label"], "node.hub")
        ov.point("node.other", (1, 2), "Nice name")
        self.assertEqual(ov.HANDLES["node.other"]["label"], "Nice name")

    def test_defaults_are_recorded_alongside_the_value(self):
        ov.point("p", (10, 20))
        h = ov.HANDLES["p"]
        self.assertEqual(h["default"], (10, 20))
        self.assertEqual(h["value"], (10, 20))

    def test_size_key_is_carried_through(self):
        ov.point("node.hub", (10, 20), size_key="node.hub.size")
        self.assertEqual(ov.HANDLES["node.hub"]["size_key"], "node.hub.size")

    def test_returns_the_default_when_nothing_is_loaded(self):
        self.assertEqual(ov.point("p", (10, 20)), (10, 20))
        self.assertEqual(ov.rect("r", (1, 2, 3, 4)), (1, 2, 3, 4))
        self.assertEqual(ov.path("f", [(0, 0), (5, 5)]), [(0, 0), (5, 5)])
        self.assertEqual(ov.scalar("s", 11), 11.0)

    def test_re_registration_replaces_rather_than_duplicates(self):
        ov.point("p", (10, 20))
        ov.point("p", (10, 20))
        self.assertEqual(len(ov.HANDLES), 1)


class TestOverridesWin(RegistryCase):
    def test_loaded_values_beat_defaults(self):
        ov.use(self.write_overrides({
            "p": [99, 98],
            "r": [1, 2, 30, 40],
            "f": [[0, 0], [3, 3], [6, 6]],
            "s": 42,
        }))
        self.assertEqual(ov.point("p", (10, 20)), (99.0, 98.0))
        self.assertEqual(ov.rect("r", (1, 2, 3, 4)), (1.0, 2.0, 30.0, 40.0))
        self.assertEqual(ov.path("f", [(0, 0), (6, 6)]),
                         [(0.0, 0.0), (3.0, 3.0), (6.0, 6.0)])
        self.assertEqual(ov.scalar("s", 11), 42.0)

    def test_override_values_are_floats(self):
        ov.use(self.write_overrides({"p": [99, 98]}))
        self.assertTrue(all(isinstance(v, float) for v in ov.point("p", (1, 2))))

    def test_unlisted_keys_still_use_their_default(self):
        ov.use(self.write_overrides({"p": [99, 98]}))
        self.assertEqual(ov.point("other", (5, 6)), (5, 6))

    def test_path_can_gain_vertices(self):
        # Inserting a waypoint is how a straight connector becomes an angled
        # one; the override must be able to change the vertex COUNT.
        ov.use(self.write_overrides({"f": [[0, 0], [5, 9], [10, 0]]}))
        self.assertEqual(len(ov.path("f", [(0, 0), (10, 0)])), 3)

    def test_scalar_zero_is_an_override_not_a_falsy_miss(self):
        ov.use(self.write_overrides({"s": 0}))
        self.assertEqual(ov.scalar("s", 11), 0.0)

    def test_missing_file_means_all_defaults(self):
        self.assertEqual(ov.use(os.path.join(self.tmp, "nope.json")), {})
        self.assertEqual(ov.point("p", (1, 2)), (1, 2))

    def test_broken_json_never_takes_the_build_down(self):
        p = os.path.join(self.tmp, "broken.json")
        with open(p, "w") as fh:
            fh.write("{ this is not json")
        self.assertEqual(ov.use(p), {})          # warns, does not raise
        self.assertEqual(ov.point("p", (1, 2)), (1, 2))

    def test_empty_file_contents_mean_all_defaults(self):
        p = os.path.join(self.tmp, "null.json")
        with open(p, "w") as fh:
            fh.write("null")
        self.assertEqual(ov.use(p), {})

    def test_use_repoints_path_and_load_is_idempotent(self):
        p = self.write_overrides({"p": [7, 7]})
        ov.use(p)
        self.assertEqual(ov.PATH, p)
        self.assertEqual(ov.load(), ov.load())


# ================================================================ active ====
class TestActive(RegistryCase):
    def test_untouched_handles_are_not_active(self):
        ov.point("p", (10, 20))
        ov.rect("r", (1, 2, 3, 4))
        ov.path("f", [(0, 0), (5, 5)])
        ov.scalar("s", 11)
        self.assertEqual(ov.active(), {})

    def test_only_changed_keys_are_reported(self):
        ov.use(self.write_overrides({"p": [99, 98]}))
        ov.point("p", (10, 20))
        ov.point("q", (10, 20))
        self.assertEqual(list(ov.active()), ["p"])

    def test_an_override_equal_to_its_default_is_not_active(self):
        # The editor writes back everything it is holding; a value nudged and
        # nudged back must not linger in the file as a phantom override.
        ov.use(self.write_overrides({"p": [10, 20], "s": 11}))
        ov.point("p", (10, 20))
        ov.scalar("s", 11)
        self.assertEqual(ov.active(), {})

    def test_int_default_versus_float_override_compares_equal(self):
        ov.use(self.write_overrides({"p": [10.0, 20.0]}))
        ov.point("p", (10, 20))
        self.assertEqual(ov.active(), {})

    def test_path_activity_sees_nested_coordinates(self):
        ov.use(self.write_overrides({"f": [[0, 0], [5, 9], [10, 0]]}))
        ov.path("f", [(0, 0), (10, 0)])
        ov.path("g", [(0, 0), (10, 0)])
        self.assertEqual(list(ov.active()), ["f"])

    def test_scalar_activity(self):
        ov.use(self.write_overrides({"s": 42}))
        ov.scalar("s", 11)
        ov.scalar("t", 11)
        self.assertEqual(list(ov.active()), ["s"])

    def test_summary_counts_handles_and_overrides(self):
        ov.use(self.write_overrides({"p": [99, 98]}))
        ov.point("p", (10, 20))
        ov.point("q", (10, 20))
        s = ov.summary()
        self.assertIn("2 movable handles", s)
        self.assertIn("1 overridden", s)


# ============================================================ round-trip ====
class TestRoundTrip(RegistryCase):
    LAYOUT = [("point", "node.hub", (318, 450)),
              ("rect", "box.stac", (660, 350, 280, 200)),
              ("path", "flow.a", [(500, 450), (580, 428), (660, 450)]),
              ("scalar", "node.hub.size", 11.0)]

    def declare(self):
        out = {}
        for kind, key, default in self.LAYOUT:
            out[key] = getattr(ov, kind)(key, default)
        return out

    def test_save_then_load_reproduces_the_same_geometry(self):
        ov.use(self.write_overrides({
            "node.hub": [320, 455],
            "box.stac": [661, 351, 281, 201],
            "flow.a": [[500, 450], [590, 400], [660, 450]],
            "node.hub.size": 14,
        }))
        first = self.declare()
        active = ov.active()
        self.assertEqual(len(active), 4)

        out = os.path.join(self.tmp, "saved.json")
        # active() hands back tuples; json turns those into lists, which is
        # exactly what the file format is.
        self.assertEqual(ov.save(json.loads(json.dumps(active)), out), out)

        ov.HANDLES.clear()
        ov.use(out)
        self.assertEqual(self.declare(), first)
        self.assertEqual(ov.active(), active)

    def test_saved_file_is_valid_stable_json(self):
        ov.point("b", (1, 2))
        ov.point("a", (3, 4))
        out = ov.save({"b": [1, 2], "a": [3, 4]}, os.path.join(self.tmp, "s.json"))
        with open(out) as fh:
            text = fh.read()
        self.assertTrue(text.endswith("\n"))
        self.assertEqual(json.loads(text), {"a": [3, 4], "b": [1, 2]})
        self.assertLess(text.index('"a"'), text.index('"b"'), "not sort_keys")

    def test_saving_nothing_is_a_valid_empty_override_file(self):
        out = ov.save({}, os.path.join(self.tmp, "empty.json"))
        ov.HANDLES.clear()
        self.assertEqual(ov.use(out), {})
        self.assertEqual(ov.point("p", (1, 2)), (1, 2))


# ================================================================ offset ====
class TestOffset(RegistryCase):
    """
    `offset` -- a point stored as a delta from another handle.

    Labels stored absolutely track their node only until nudged once, after
    which the override pins them and they stop following (docs/DECISIONS.md).
    """

    def test_documented_kinds_all_exist_on_the_package_module(self):
        # CLAUDE.md routes coordinates through
        # `overrides.point/rect/path/scalar/offset`, and docs/ARCHITECTURE.md
        # lists the same set. A project following the docs must not hit
        # AttributeError.
        for name in ("point", "rect", "path", "scalar", "offset"):
            self.assertTrue(callable(getattr(ov, name, None)), name)

    def test_resolves_against_its_anchor(self):
        anchor = ov.point("node.airflow", (400, 300))
        label = ov.offset("label.airflow", (0, 40), "node.airflow", anchor)
        self.assertEqual(label, (400, 340))

    def test_stays_attached_when_the_anchor_moves(self):
        # The whole reason offsets exist: move the node, the label comes too.
        ov.use(self.write_overrides({"node.airflow": [500, 100]}))
        anchor = ov.point("node.airflow", (400, 300))
        label = ov.offset("label.airflow", (0, 40), "node.airflow", anchor)
        self.assertEqual(anchor, (500.0, 100.0))
        self.assertEqual(label, (500.0, 140.0))

    def test_the_override_stores_the_delta_not_the_absolute_position(self):
        ov.use(self.write_overrides({"label.airflow": [12, -6]}))
        anchor = ov.point("node.airflow", (400, 300))
        self.assertEqual(ov.offset("label.airflow", (0, 40), "node.airflow", anchor),
                         (412.0, 294.0))
        self.assertEqual(ov.HANDLES["label.airflow"]["value"], (12.0, -6.0))

    def test_registers_with_kind_offset_and_its_anchor_key(self):
        ov.offset("label.airflow", (0, 40), "node.airflow", (400, 300))
        h = ov.HANDLES["label.airflow"]
        self.assertEqual(h["kind"], "offset")
        self.assertEqual(h["anchor_key"], "node.airflow")
        self.assertEqual(h["default"], (0, 40))

    def test_active_reports_the_delta(self):
        ov.use(self.write_overrides({"label.airflow": [12, -6]}))
        ov.offset("label.airflow", (0, 40), "node.airflow", (400, 300))
        self.assertEqual(ov.active(), {"label.airflow": (12.0, -6.0)})

    def test_moving_the_anchor_alone_does_not_make_the_label_active(self):
        ov.use(self.write_overrides({"node.airflow": [500, 100]}))
        anchor = ov.point("node.airflow", (400, 300))
        ov.offset("label.airflow", (0, 40), "node.airflow", anchor)
        self.assertEqual(list(ov.active()), ["node.airflow"])

    def test_round_trips_through_save_and_load(self):
        ov.use(self.write_overrides({"label.airflow": [12, -6]}))
        anchor = ov.point("node.airflow", (400, 300))
        first = ov.offset("label.airflow", (0, 40), "node.airflow", anchor)
        out = ov.save(json.loads(json.dumps(ov.active())),
                      os.path.join(self.tmp, "saved.json"))
        ov.HANDLES.clear()
        ov.use(out)
        anchor2 = ov.point("node.airflow", (400, 300))
        self.assertEqual(ov.offset("label.airflow", (0, 40), "node.airflow", anchor2),
                         first)

    def test_example_fork_agrees_with_the_package(self):
        # examples/disasters_ingest/overrides.py is a diverged copy. If the two
        # drift apart, an example silently stops matching the documented API.
        src = os.path.join(sup.DISASTERS_DIR, "overrides.py")
        if not os.path.exists(src):
            self.skipTest("disasters example absent")
        with open(src, encoding="utf-8") as fh:
            fork = fh.read()
        for name in ("point", "rect", "path", "scalar", "offset"):
            self.assertIn("def %s(" % name, fork, "example fork lost %s()" % name)


if __name__ == "__main__":
    unittest.main()
