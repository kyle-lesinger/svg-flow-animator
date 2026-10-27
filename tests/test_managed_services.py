"""
The managed_services example: its story agrees with its geometry, and its
frames are the picture they claim to be.

Everything runs in a subprocess. Importing the example points the global
overrides module at the example's file and registers its handles, which would
leak into every other test in the process. The probe also pins
FLOWGIF_OVERRIDES to an empty file, so these assertions are about the DEFAULT
layout and a saved overrides.json cannot make them flaky.
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

try:
    from . import _support as sup
except ImportError:
    import _support as sup

EXAMPLE = os.path.join(ROOT, "examples", "managed_services")

PROBE = r'''
import hashlib, io, json, math, os, re, sys, tempfile
sys.path.insert(0, %(here)r)
import gen_frames as G, layout as L, story
from svg_flow_animator import overrides as ov
L.warm_up()

h = lambda s: hashlib.sha1(s.encode()).hexdigest()
out = dict(style=G.S.name, handles=sorted(ov.HANDLES), personas=list(L.PERSONAS),
           nodes={k: dict(c=v["c"], size=v["size"], label=v["label"],
                          account=v["account"]) for k, v in L.NODES.items()},
           boxes={k: v for k, v in L.BOXES.items()},
           flows={k: dict(src=v["src"], dst=v["dst"], pts=L.flow_path(k))
                  for k, v in L.FLOWS.items()},
           beats=[{k: b.get(k) for k in ("chapter", "anchor", "flows", "pulse", "glow",
                                         "shots", "text")} for b in G.BEATS],
           shots=sorted(story.SHOTS), chapters=G.CHAPTERS, total=G.TOTAL,
           canvas=(L.W, L.H), diagram_h=L.DIAGRAM_H,
           band_rects=[L.CAPTION, L.CAPTION_BESIDE_SHOT] + [L.shot_rect(k) for k in story.SHOTS],
           title_ys=[L.TITLE_MANAGED[1], L.TITLE_EXTERNAL[1], L.TITLE_DASHBOARD[1]],
           label_ys=[v["label_c"][1] + 18 * (len(v["label"].splitlines()) - 1)
                     for v in L.NODES.values()])

frame0 = G.frame_svg(0)
mids, leaks, shots_seen, captions = {}, {}, {}, {}
for b in G.BEATS:
    f = b["stage"].start + b["stage"].dur // 2
    doc = G.frame_svg(f)
    mids[b["stage"].key] = h(doc) != h(frame0)
    captions[b["stage"].key] = doc.count('fill="' + G.CAPTION_BG + '"')
    leaks[b["stage"].key] = len(re.findall(r'<(rect|ellipse)[^>]*stroke="[^"]*"[^>]*>', doc))
    # A real screenshot, or the placeholder a fresh clone (no assets/) draws.
    shots_seen[b["stage"].key] = doc.count("<image") + doc.count("screenshot missing")
out.update(mid_differs=mids, leaks=leaks, images=shots_seen, captions=captions,
           frame0_leaks=len(re.findall(r'<(rect|ellipse)[^>]*stroke="[^"]*"[^>]*>', frame0)))

# Users' lines are temporary and late users appear; probe both at the
# frames where they should and should not show.
last = G.TOTAL - 1
tmp = {}
for k in sorted(L.TRANSIENT):
    b = G.FLOW_BEAT[k][0]["stage"]
    tmp[k] = dict(mid=bool(G.flow_markup(G.S, k, b.start + b.dur // 2, 1.0)),
                  gone_after=bool(G.flow_markup(G.S, k, G.VANISH[k] + G.LINE_FADE + 1, 1.0)),
                  before=bool(G.flow_markup(G.S, k, b.start - 1, 1.0)),
                  last=bool(G.flow_markup(G.S, k, last, 1.0)),
                  editor=bool(G.flow_markup(G.S, k, None, 1.0)))
out.update(transient=tmp, late=list(L.LATE_PERSONAS),
           appear={n: dict(first=G.node_alpha(n, 0), last=G.node_alpha(n, last),
                           before=G.node_alpha(n, G.APPEAR[n] - G.FADE - 1))
                   for n in L.LATE_PERSONAS})

# A screenshot that is not there must say so, loudly, rather than vanish.
G.STAGED = tempfile.mkdtemp()
err, sys.stderr = sys.stderr, io.StringIO()
G._warned.clear()
missing = G.shot_markup(G.S, sorted(story.SHOTS)[0], 1.0)
out.update(placeholder="screenshot missing" in missing, warned=sys.stderr.getvalue())
sys.stderr = err
print(json.dumps(out))
'''


def probe(style, example=EXAMPLE):
    fd, empty = tempfile.mkstemp(suffix=".json")
    with os.fdopen(fd, "w") as fh:
        fh.write("{}")
    try:
        env = dict(os.environ, FLOWGIF_STYLE=style, FLOWGIF_OVERRIDES=empty)
        proc = subprocess.run([sys.executable, "-c", PROBE % dict(here=example)],
                              env=env, cwd=example, capture_output=True, text=True)
    finally:
        os.remove(empty)
    if proc.returncode != 0:
        raise AssertionError("probe failed:\n" + proc.stderr[-3000:])
    return json.loads(proc.stdout.strip().splitlines()[-1])


class ManagedCase(unittest.TestCase):
    # test_shared_services.py reruns every class here against its own example
    # by overriding `example`, so the cache is keyed by both.
    example = EXAMPLE
    style = "sketch"
    _cache = {}

    @classmethod
    def setUpClass(cls):
        key = (cls.example, cls.style)
        if key not in cls._cache:
            cls._cache[key] = probe(cls.style, cls.example)
        cls.P = cls._cache[key]


class TestStoryAgreesWithLayout(ManagedCase):
    def test_every_beat_anchors_on_something_that_exists(self):
        for b in self.P["beats"]:
            kind, _, name = b["anchor"].partition(".")
            pool = self.P["nodes"] if kind == "node" else self.P["boxes"]
            key = name if kind == "node" else b["anchor"]
            self.assertIn(key, pool, f"beat {b['chapter']} anchors on {b['anchor']}")

    def test_every_reference_in_the_story_is_real(self):
        for b in self.P["beats"]:
            for k in b["flows"] or ():
                self.assertIn(k, self.P["flows"], f"{b['chapter']}: flow {k}")
            for n in b["pulse"] or ():
                self.assertIn(n, self.P["nodes"], f"{b['chapter']}: pulse {n}")
            for box in b["glow"] or ():
                self.assertIn(box, self.P["boxes"], f"{b['chapter']}: glow {box}")
            for s in b["shots"] or ():
                self.assertIn(s, self.P["shots"], f"{b['chapter']}: shot {s}")

    def test_every_beat_has_words(self):
        for b in self.P["beats"]:
            self.assertTrue((b["text"] or "").strip(), f"silent beat in {b['chapter']}")

    def test_the_run_beat_writes_outputs_only_after_reaching_the_catalog(self):
        run = next(b for b in self.P["beats"] if b["chapter"] == "run")
        order = run["flows"]
        for later in ("dps_files", "dps_catalog"):
            self.assertLess(order.index("dps_algcat"), order.index(later))

    def test_the_journey_starts_at_the_operator_with_both_tools(self):
        first = self.P["beats"][0]
        self.assertEqual(first["anchor"], "node.operator")
        self.assertEqual(set(first["pulse"]), {"ade", "jmd"})

    def test_compute_instances_are_gone(self):
        # Dropped as redundant: the DPS produces into File Storage directly.
        self.assertNotIn("compute", self.P["nodes"])
        self.assertEqual(self.P["flows"]["dps_files"]["src"], "dps")


class TestConnectors(ManagedCase):
    def _near(self, end, pt):
        if end in self.P["nodes"]:
            n = self.P["nodes"][end]
            x, y = n["c"]
            return abs(pt[0] - x) <= n["size"] / 2 + 70 and abs(pt[1] - y) <= n["size"] / 2 + 70
        x, y, w, h = self.P["boxes"]["box." + end]
        return x - 8 <= pt[0] <= x + w + 8 and y - 8 <= pt[1] <= y + h + 8

    def test_every_connector_starts_at_its_source_and_ends_at_its_target(self):
        for k, f in self.P["flows"].items():
            self.assertTrue(self._near(f["src"], f["pts"][0]),
                            f"{k} starts at {f['pts'][0]}, nowhere near {f['src']}")
            self.assertTrue(self._near(f["dst"], f["pts"][-1]),
                            f"{k} ends at {f['pts'][-1]}, nowhere near {f['dst']}")

    def test_personas_are_sources_only(self):
        # A flow INTO a persona would claim the system pushes to people.
        for k, f in self.P["flows"].items():
            self.assertNotIn(f["dst"], self.P["personas"], f"{k} terminates on a persona")

    def test_every_connector_is_a_handle(self):
        for k in self.P["flows"]:
            self.assertIn("flow." + k, self.P["handles"])
            self.assertIn("flowlabel.%s.t" % k, self.P["handles"])

    def test_labels_are_offsets_anchored_to_their_node(self):
        for n in self.P["nodes"]:
            self.assertIn("label." + n, self.P["handles"])
            self.assertIn("node.%s.size" % n, self.P["handles"])


class TestFrames(ManagedCase):
    def test_every_beat_actually_moves(self):
        # Aimed at a frame mid-beat: frame 0 is still and would pass forever.
        still = [k for k, moved in self.P["mid_differs"].items() if not moved]
        self.assertEqual(still, [], "beats whose middle frame equals frame 0")

    def test_the_monitor_beat_shows_its_screenshot(self):
        monitor = [k for k in self.P["images"] if k.startswith("monitor.")]
        self.assertTrue(monitor)
        for k in monitor:
            self.assertGreaterEqual(self.P["images"][k], 1, f"{k} shows no screenshot")

    def test_a_missing_screenshot_draws_a_placeholder_and_warns(self):
        self.assertTrue(self.P["placeholder"])
        self.assertIn("missing", self.P["warned"])


class TestUsersChapter(ManagedCase):
    """The closing chapter: each user's lines draw in and then fade as the next
    user's arrive, and users join the column one at a time."""

    def test_temporary_lines_show_only_while_in_play(self):
        for k, t in self.P["transient"].items():
            self.assertTrue(t["mid"], f"{k} is not drawn during its own beat")
            self.assertFalse(t["before"], f"{k} shows before its beat")
            self.assertFalse(t["gone_after"], f"{k} never fades")
            self.assertFalse(t["last"], f"{k} is still on the closing frame")

    def test_the_editor_still_sees_every_temporary_line(self):
        for k, t in self.P["transient"].items():
            self.assertTrue(t["editor"], f"{k} would be impossible to drag")

    def test_late_users_appear_and_then_stay(self):
        for n, a in self.P["appear"].items():
            self.assertEqual(a["first"], 0.0, f"{n} is on screen from the start")
            self.assertEqual(a["before"], 0.0, f"{n} appears early")
            self.assertEqual(a["last"], 1.0, f"{n} is gone by the end")

    def test_the_operator_never_disappears(self):
        self.assertNotIn("operator", self.P["late"])

    def test_the_operator_is_back_before_anyone_else_arrives(self):
        chapters = [b["chapter"] for b in self.P["beats"]]
        view = next(b for b in self.P["beats"] if b["chapter"] == "view")
        self.assertIn("operator", view["pulse"])
        self.assertLess(chapters.index("view"), chapters.index("users"))


class TestCaptionBand(ManagedCase):
    """Words and screenshots live in the band under the figure, so they can
    never land on a line or a label. Floating bubbles kept doing exactly that."""

    def test_captions_and_screenshots_sit_wholly_inside_the_band(self):
        w, h = self.P["canvas"]
        for x, y, rw, rh in self.P["band_rects"]:
            self.assertGreaterEqual(y, self.P["diagram_h"], (x, y, rw, rh))
            self.assertLessEqual(y + rh, h, (x, y, rw, rh))
            self.assertGreaterEqual(x, 0)
            self.assertLessEqual(x + rw, w)

    def test_the_figure_stays_above_the_band(self):
        top = self.P["diagram_h"]
        for k, f in self.P["flows"].items():
            for pt in f["pts"]:
                self.assertLess(pt[1], top, f"{k} reaches into the caption band")
        for k, n in self.P["nodes"].items():
            self.assertLess(n["c"][1] + n["size"] / 2, top, k)
        for k, (x, y, rw, rh) in self.P["boxes"].items():
            self.assertLessEqual(y + rh, top, k)
        for y in self.P["title_ys"] + self.P["label_ys"]:
            self.assertLess(y, top)

    def test_every_beat_shows_its_caption(self):
        missing = [k for k, n in self.P["captions"].items() if n < 1]
        self.assertEqual(missing, [])


class TestSketchHasNoFlatLeaks(ManagedCase):
    style = "sketch"

    def test_frame0_and_every_mid_beat_frame(self):
        self.assertEqual(self.P["frame0_leaks"], 0)
        leaking = {k: n for k, n in self.P["leaks"].items() if n}
        self.assertEqual(leaking, {}, "flat stroked primitives in sketch frames")


class TestFlatStyleToo(ManagedCase):
    style = "flat"

    def test_flat_renders_every_beat(self):
        self.assertEqual(self.P["style"], "flat")
        still = [k for k, moved in self.P["mid_differs"].items() if not moved]
        self.assertEqual(still, [])


@sup.needs_rsvg
class TestRenders(unittest.TestCase):
    example = EXAMPLE

    def test_a_mid_beat_frame_rasterises_to_a_plausible_png(self):
        code = (
            "import sys; sys.path.insert(0, %r); import gen_frames as G;"
            "G.stage_assets(); b = G.BEATS[0];"
            "open(sys.argv[1], 'w').write(G.frame_svg(b['stage'].start + 20))" % self.example)
        with tempfile.TemporaryDirectory(dir=self.example) as d:
            svg_path, png = os.path.join(d, "f.svg"), os.path.join(d, "f.png")
            subprocess.run([sys.executable, "-c", code, svg_path], check=True,
                           cwd=self.example)
            subprocess.run(["rsvg-convert", "-w", "1600", "-h", "900", "-o", png, svg_path],
                           check=True)
            self.assertGreater(os.path.getsize(png), 100_000)


if __name__ == "__main__":
    unittest.main()
