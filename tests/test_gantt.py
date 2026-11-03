"""
gantt and gantt_editor: the timeline, and the browser editor for its dates.

The schedule is the part people edit, so it gets the most scrutiny: dates are
inclusive, the axis is whole weeks, a schedule file round-trips, and the
editor's routes refuse what could not be drawn rather than saving it.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

try:
    from . import _support as sup
except ImportError:
    import _support as sup

from svg_flow_animator import gantt, gantt_editor, styles  # noqa: E402


def chart(draft=False):
    g = gantt.Gantt("Plan", draft=draft)
    g.row("a", "First", date(2026, 11, 11), date(2026, 11, 20), "#6741d9", "#d0bfff",
          note="Ana")
    g.row("b", "Second", date(2026, 11, 23), date(2026, 12, 11), "#1971c2", "#a5d8ff",
          detail="two\nlines", note="Ben")
    g.row("c", "Third", date(2026, 11, 23), date(2026, 12, 6), "#2f9e44", "#b2f2bb")
    return g


class TestGantt(unittest.TestCase):
    def test_the_axis_is_whole_weeks_monday_to_monday(self):
        a, b = chart().axis()
        self.assertEqual((a, b), (date(2026, 11, 9), date(2026, 12, 14)))
        self.assertEqual(a.weekday(), 0)
        self.assertEqual(b.weekday(), 0)

    def test_a_bar_covers_its_end_day(self):
        lay = chart().layout()
        x, _, w, _ = lay["bars"][0]
        self.assertAlmostEqual(x, lay["x0"] + 2 * lay["ppd"])      # Wed after Mon
        self.assertAlmostEqual(w, 10 * lay["ppd"])                 # 11th..20th inclusive

    def test_a_row_cannot_end_before_it_starts(self):
        with self.assertRaises(ValueError):
            gantt.Gantt("x").row("a", "A", date(2026, 1, 2), date(2026, 1, 1), "#000", "#fff")

    def test_retimed_swaps_dates_and_keeps_everything_else(self):
        g = chart().retimed({"a": (date(2026, 12, 1), date(2026, 12, 2)),
                             "b": (date(2026, 11, 23), date(2026, 12, 11)),
                             "c": (date(2026, 11, 23), date(2026, 12, 6))}, draft=True)
        self.assertTrue(g.draft)
        self.assertEqual(g.dates()["a"], (date(2026, 12, 1), date(2026, 12, 2)))
        self.assertEqual([r["note"] for r in g.rows], ["Ana", "Ben", None])

    def test_retimed_refuses_a_schedule_that_does_not_fit_the_rows(self):
        with self.assertRaises(ValueError):
            chart().retimed({"a": (date(2026, 12, 1), date(2026, 12, 2))})
        full = chart().dates()
        with self.assertRaises(ValueError):
            chart().retimed(dict(full, z=full["a"]))

    def test_the_draft_stamp_shows_only_on_a_draft(self):
        st = styles.SKETCH
        self.assertIn(gantt.DRAFT_TEXT, chart(draft=True).frame_svg(None, st))
        self.assertNotIn(gantt.DRAFT_TEXT, chart(draft=False).frame_svg(None, st))

    def test_bars_that_start_together_grow_together(self):
        begins, total = chart().stages()
        self.assertEqual(begins[1], begins[2])
        self.assertLess(begins[0], begins[1])
        self.assertEqual(total, gantt.INTRO + gantt.RESET
                         + 2 * (gantt.GROW + gantt.STAGGER) + gantt.OUTRO)

    def test_it_opens_and_closes_on_the_finished_chart(self):
        g, st = chart(), styles.SKETCH
        still = g.frame_svg(None, st)
        self.assertEqual(g.frame_svg(0, st), still)
        self.assertEqual(g.frame_svg(g.total - 1, st), still)
        begins, _ = g.stages()
        mid = g.frame_svg(begins[0] + gantt.GROW // 2, st)
        self.assertIn("<clipPath", mid)
        sup.parse_fragment(g.scene(begins[0] + gantt.GROW // 2, st))

    def test_names_sit_inside_their_bar(self):
        g = chart()
        lay = g.layout()
        for (bx, by, bw, bh), (lines, size), r in zip(lay["bars"], lay["notes"], g.rows):
            if not r["note"]:
                self.assertEqual(lines, [])
                continue
            self.assertEqual(" ".join(lines), r["note"])        # nothing dropped
            for s in lines:
                self.assertLessEqual(gantt.label_width(s, size), bw - 2 * gantt.NOTE_PAD, s)
            self.assertLessEqual(len(lines) * size * 1.3, bh)

    def test_a_short_bar_breaks_names_at_commas_and_grows_to_hold_them(self):
        g = gantt.Gantt("Plan")
        g.row("a", "Short", date(2026, 11, 9), date(2026, 11, 13), "#e03131", "#ffc9c9",
              note="Ana Long-Surname, Ben Long-Surname, Cy Long-Surname, Di Long-Surname")
        g.row("b", "Long", date(2026, 11, 9), date(2026, 12, 31), "#1971c2", "#a5d8ff",
              note="Ana")
        lay = g.layout()
        (_, _, _, short_h), (_, _, _, long_h) = lay["bars"]
        lines, _ = lay["notes"][0]
        self.assertGreater(len(lines), 1)
        self.assertGreater(short_h, long_h)
        for s in lines:                                         # a name is never split
            self.assertTrue(all(p.strip().endswith("Long-Surname")
                                for p in s.split(",") if p.strip()), s)
        self.assertIn("Di Long-Surname", g.frame_svg(None, styles.SKETCH))

    def test_editor_layout_is_plain_json(self):
        lay = chart().editor_layout()
        self.assertEqual(json.loads(json.dumps(lay)), lay)
        self.assertEqual([r["key"] for r in lay["rows"]], ["a", "b", "c"])
        self.assertEqual(lay["axis_start"], "2026-11-09")


class TestScheduleFile(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="sfa-gantt-")
        self.path = os.path.join(self.dir, "schedule.json")

    def tearDown(self):
        shutil.rmtree(self.dir)

    def test_round_trips(self):
        dates = chart().dates()
        gantt_editor.save(self.path, dates, True, order=["c", "a", "b"])
        self.assertEqual(gantt_editor.load(self.path), (dates, True))

    def test_is_written_one_row_per_line_in_the_given_order(self):
        gantt_editor.save(self.path, chart().dates(), False, order=["c", "a", "b"])
        with open(self.path) as fh:
            text = fh.read()
        self.assertEqual(re.findall(r'^\s+"(\w)": \["', text, re.M), ["c", "a", "b"])
        json.loads(text)

    def test_routes_preview_without_saving_and_save_only_when_asked(self):
        gantt_editor.save(self.path, chart().dates(), True)
        with open(self.path) as fh:
            before = fh.read()
        r = gantt_editor.routes(chart(), self.path, styles.SKETCH)
        state = r["/timeline/state"]({})
        self.assertTrue(state["draft"])
        self.assertIn("<svg", state["svg"])

        moved = {k: list(v) for k, v in
                 ((r_["key"], (r_["start"], r_["end"])) for r_ in state["layout"]["rows"])}
        moved["a"] = ["2026-12-01", "2026-12-04"]
        view = r["/timeline/render"]({"dates": moved, "draft": False})
        self.assertEqual(view["layout"]["rows"][0]["start"], "2026-12-01")
        with open(self.path) as fh:
            self.assertEqual(fh.read(), before, "a preview must not touch the file")

        r["/timeline/save"]({"dates": moved, "draft": False})
        dates, draft = gantt_editor.load(self.path)
        self.assertEqual(dates["a"], (date(2026, 12, 1), date(2026, 12, 4)))
        self.assertFalse(draft)

    def test_save_refuses_a_bar_that_ends_before_it_starts(self):
        gantt_editor.save(self.path, chart().dates(), True)
        with open(self.path) as fh:
            before = fh.read()
        bad = {k: [s.isoformat(), e.isoformat()] for k, (s, e) in chart().dates().items()}
        bad["a"] = ["2026-12-04", "2026-12-01"]
        with self.assertRaises(ValueError):
            gantt_editor.routes(chart(), self.path, styles.SKETCH)["/timeline/save"](
                {"dates": bad, "draft": True})
        with open(self.path) as fh:
            self.assertEqual(fh.read(), before)


@sup.needs_node
class TestEditorPage(unittest.TestCase):
    def test_the_page_script_parses(self):
        # GOTCHAS: a template escaping bug once shipped a script that did not
        # parse, with no Python-side error at all.
        d = tempfile.mkdtemp(prefix="sfa-gantt-page-")
        try:
            page = gantt_editor.write_page(os.path.join(d, "t.html"), "plan", back="e.html")
            with open(page, encoding="utf-8") as fh:
                html = fh.read()
            self.assertIn('href="e.html"', html)
            js = os.path.join(d, "t.js")
            with open(js, "w", encoding="utf-8") as fh:
                fh.write(sup.extract_scripts(html)[-1])
            proc = subprocess.run(["node", "--check", js], capture_output=True, text=True)
            self.assertEqual(proc.returncode, 0, proc.stderr)
        finally:
            shutil.rmtree(d)


if __name__ == "__main__":
    unittest.main()
