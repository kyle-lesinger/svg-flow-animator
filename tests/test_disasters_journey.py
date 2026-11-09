"""
The disasters example's journey slide: a swath becomes a dataset, copies
multiply across tools, then one store + STAC + read-in-place replaces them.

The slide makes claims -- 8 copies at the problem's peak, 0 at the end, every
dataset in every tool -- so these tests count them in RENDERED frames rather
than trusting the timeline's numbers to agree with themselves.

Subprocess-run with overrides pinned empty, like the intro's tests. Needs the
gitignored artwork, the Blue Marble texture, and ImageMagick to decode it.
"""
import json
import os
import struct
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
import gen_frames as G, journey as J, globe as GL, layout as L

def count(doc, cls):
    return len(re.findall(r'class="%%s"' %% re.escape(cls), doc))

def has(doc, s):
    return ">%%s</text>" %% G.esc(s) in doc

def leaks(doc):
    return len(re.findall(r'<(rect|ellipse)[^>]*stroke="[^"]*"[^>]*>', doc))

def cell_pts(doc):
    pts = []
    for d in re.findall(r'<path class="cell" d="([^"]+)"', doc):
        pts += [tuple(map(float, p.split(","))) for p in re.findall(r"[-\d.]+,[-\d.]+", d)]
    return pts

peak = J.DIFFICULTY + 20
docs = {f: J.journey_svg(f) for f in (0, J.REC[0][0] + 45, peak, J.READ_AT + 60,
                                      J.TOTAL - 1)}
first, peak_doc, last = docs[0], docs[peak], docs[J.TOTAL - 1]
zs = [GL.Globe.view(J.GLOBE, v)[2] for p in J.PASSES
      for _r, _c, q in p.cells(J.ROWS, J.COLS) for v in q]
href = GL.globe_png(J.TEXTURE, L.FRAME_ASSETS, J.GLOBE)
flat = GL.flat_png(J.TEXTURE, L.FRAME_ASSETS, J.FLAT_BOX)
print(json.dumps(dict(
    style=G.S.name, slides=list(G.slides()), sections=[s[0] for s in G.sections()],
    span=G.section_span("journey"), total=J.TOTAL, fps=J.FPS,
    gif=G.section_gif("journey"),
    via_section_frame=G.section_frame(5, "journey") == J.journey_svg(5),
    href=href, frame_assets=L.FRAME_ASSETS, globe_d=int(round(2 * J.GLOBE.r)),
    min_z=min(zs),
    sats=[dict(name=s["name"], fmt=s["fmt"], incl=s["incl"]) for s in J.SATS],
    n_dup=J.N_DUP, flat=flat, flat_box=J.FLAT_BOX, flat_ext=J.FLAT_EXT,
    flat_rect=J.flat_rect(), src=(GL.SRC_W, GL.SRC_H),
    n_datasets=len(J.PASSES), n_tools=len(J.TOOLS), cells_each=J.ROWS * J.COLS,
    first=dict(copies=count(first, "copy"), items=count(first, "item"),
               store=has(first, "Cloud storage"), globe=href in first),
    mid_pass_cells=count(docs[J.REC[0][0] + 45], "cell"),
    peak=dict(copies=count(peak_doc, "copy"),
              label=has(peak_doc, J.problem_label(J.N_DUP)),
              formats=[s["fmt"] for s in J.SATS[:J.N_DUP]
                       if has(peak_doc, "%%s \u00b7 %%s" %% (s["name"], s["fmt"]))]),
    last=dict(copies=count(last, "copy"), flying=count(last, "flying"),
              items=count(last, "item"),
              portal=count(last, "chip portal"), mmgis=count(last, "layer mmgis"),
              cogs=[s["name"] for s in J.SATS
                    if has(last, "%%s \u00b7 %%s" %% (s["name"], J.CLOUD_FMT))],
              cells=count(last, "cell"), zero=last.count(">0 copies</text>"),
              caption=has(last, J.CAPTIONS[-1][1]), cell_pts=cell_pts(last)),
    store=J.STORE,
    leaks={str(f): leaks(d) for f, d in docs.items()},
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
class JourneyCase(unittest.TestCase):
    style = "sketch"

    @classmethod
    def setUpClass(cls):
        cls.P = probe(cls.style)

    def test_it_is_a_slide_that_plays_once(self):
        self.assertEqual(self.P["style"], self.style)
        self.assertIn("journey", self.P["slides"])
        self.assertEqual(self.P["sections"][:len(self.P["slides"])], self.P["slides"])
        self.assertEqual(self.P["span"], [0, self.P["total"] - 1])
        self.assertEqual(self.P["gif"][0], -1)
        self.assertTrue(self.P["via_section_frame"])

    def test_the_globe_is_staged_where_librsvg_can_reach_it(self):
        # docs/GOTCHAS.md: an image outside the frame's tree renders as nothing.
        self.assertTrue(self.P["href"].startswith(self.P["frame_assets"] + os.sep))
        with open(self.P["href"], "rb") as fh:
            head = fh.read(24)
        self.assertEqual(head[:8], b"\x89PNG\r\n\x1a\n")
        w, h = struct.unpack(">II", head[16:24])
        self.assertEqual((w, h), (self.P["globe_d"],) * 2)

    def test_every_swath_is_on_the_visible_face(self):
        # A cell behind the globe would be drawn on top of it, through Earth.
        self.assertGreater(self.P["min_z"], 0.05)

    def test_every_dataset_is_a_different_satellite_and_format(self):
        sats = self.P["sats"]
        self.assertEqual(len({s["name"] for s in sats}), len(sats))
        self.assertEqual(len({s["fmt"] for s in sats}), len(sats))
        self.assertGreater(len({s["incl"] for s in sats}), 1, "all one orbit")

    def test_the_flat_map_is_georeferenced_to_its_own_crop(self):
        # The MMGIS overlay is placed by lat/lon against FLAT_EXT, so FLAT_EXT
        # must be exactly what the cropped pixels cover -- re-derived here from
        # the pixel box, not taken from the code under test.
        x, y, w, h = self.P["flat_box"]
        sw, sh = self.P["src"]
        want = [x / sw * 360 - 180, (x + w) / sw * 360 - 180,
                90 - (y + h) / sh * 180, 90 - y / sh * 180]
        for got, exp in zip(self.P["flat_ext"], want):
            self.assertAlmostEqual(got, exp, places=9)
        with open(self.P["flat"], "rb") as fh:
            head = fh.read(24)
        self.assertEqual(struct.unpack(">II", head[16:24]), (w, h),
                         "the crop was resampled, so pixels and extent disagree")
        # and drawn without stretching: a degree is as wide as it is tall
        fx, fy, fw, fh = self.P["flat_rect"]
        lon0, lon1, lat0, lat1 = self.P["flat_ext"]
        self.assertAlmostEqual(fw / (lon1 - lon0), fh / (lat1 - lat0), places=6)

    def test_it_opens_on_the_globe_alone(self):
        f = self.P["first"]
        self.assertTrue(f["globe"])
        self.assertEqual((f["copies"], f["items"], f["store"]), (0, 0, False))

    def test_the_swath_is_painted_during_the_pass(self):
        self.assertGreater(self.P["mid_pass_cells"], 0)
        self.assertLess(self.P["mid_pass_cells"], self.P["cells_each"])

    def test_the_problem_peaks_at_datasets_times_tools_copies(self):
        p = self.P["peak"]
        self.assertEqual(p["copies"], self.P["n_dup"] * self.P["n_tools"])
        self.assertTrue(p["label"])
        # each file still in its own satellite's format at the peak
        self.assertEqual(len(p["formats"]), self.P["n_dup"])

    def test_it_ends_with_one_copy_of_each_dataset_and_every_tool_has_all(self):
        last, n = self.P["last"], self.P["n_datasets"]
        self.assertEqual((last["copies"], last["flying"]), (0, 0))
        self.assertEqual(last["items"], n, "one STAC item per dataset")
        self.assertEqual(last["portal"], 3 * n, "a chip per dataset on each page")
        self.assertEqual(last["mmgis"], n)
        self.assertEqual(len(last["cogs"]), n, "every file converted once")
        self.assertEqual(last["zero"], self.P["n_tools"])
        self.assertTrue(last["caption"])
        # every dataset's cells are filed in the store, and only there
        self.assertEqual(last["cells"], n * self.P["cells_each"])
        x, y, w, h = self.P["store"]
        stray = [p for p in last["cell_pts"]
                 if not (x <= p[0] <= x + w and y <= p[1] <= y + h)]
        self.assertEqual(stray, [], "a dataset's cells sit outside the store")

    def test_no_flat_primitive_leaks_into_sketch(self):
        if self.style == "sketch":
            self.assertEqual(set(self.P["leaks"].values()), {0}, self.P["leaks"])


class TestJourneyFlat(JourneyCase):
    style = "flat"


if __name__ == "__main__":
    unittest.main()
