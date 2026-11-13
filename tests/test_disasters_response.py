"""
The disasters example's response slide: the whole network, end to end, in 15
seconds -- satellites to automated ingest, cloud storage and STAC, from STAC
to every destination at once (the uses slide's four, and any other tool or
API that speaks STAC), and from each destination on to the people.

The slide makes claims, so these check them in the frames: the whole network
is on screen once it has settled, people included; a granule keeps its
satellite's format until automated ingest, is cloud-optimized from there, and
leaves STAC as one copy per destination; every granule lands on every
destination and pulses on to the people, and nothing is in flight at the end;
there are few enough granules to follow; no granule is drawn over words; and
every word fits where it sits as actually rendered.

Subprocess-run with overrides pinned empty, like the other slide tests. Needs
the gitignored artwork; measuring rendered text needs rsvg and magick.
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
import gen_frames as G, response as R, story as ST, uses as U, layout as L

def has(doc, s):
    return ">%%s</text>" %% G.esc(s) in doc

def count(doc, s):
    return doc.count(">%%s</text>" %% G.esc(s))

def leaks(doc):
    return len(re.findall(r'<(rect|ellipse)[^>]*stroke="[^"]*"[^>]*>', doc))

def element(doc, s):
    m = re.search(r'<text[^>]*>%%s</text>' %% re.escape(G.esc(s)), doc)
    return m.group(0) if m else None

images = lambda doc: sorted(set(re.findall(r'<image href="([^"]+)"', doc)))
settled_at = R.NETWORK_IN[1] + 7
settled, last = R.response_svg(settled_at), R.response_svg(R.TOTAL - 1)
W, H = L.W, L.H
px, py, pw, ph = R.PEOPLE

# every glyph, every other frame: where it is and what shape it has
wrong_shape, off_canvas, copies, over_text = [], [], [], []
zones = [R.header_rect(k) for k in range(len(R.COLUMNS))] + [
    R.badge_rect(), (R.LEGEND[0] - 10, R.LEGEND[1] - 14, 480, 56),
    (W / 2 - 320, 40, 640, 34), (px + 4, py + 8, pw - 8, 16 * len(R.ROLES) + 14),
    (px + 4, py + ph - 50, pw - 8, 46), (px + pw - 170, R.HEADING_Y - 14, 170, 18)]
# a card's words, not its whole rect: granules run level into its left edge
# and pulses leave from its right; the words end 10 px inside (see `fits`)
zones += [(x + R.TEXT_DX - 10, y, w - R.TEXT_DX, h)
          for x, y, w, h in (R.card_rect(r) for r in range(R.N_ROUTES))]
for f in range(0, R.TOTAL, 2):
    seen = {}
    for i, x, y, shape, r in R.dots(f):
        if not (0 <= x <= W and 0 <= y <= H):
            off_canvas.append((f, i, round(x), round(y)))
        own = ST.SHAPES[R.SAT[i]]
        if r is None and x < R.COL_X[R.INGEST] and shape != own:
            wrong_shape.append((f, i, shape, "before ingest"))
        if (r is not None or x >= R.COL_X[R.INGEST]) and shape != ST.COG_SHAPE:
            wrong_shape.append((f, i, shape, "after ingest"))
        seen.setdefault(i, []).append(r)
        for zx, zy, zw, zh in zones:
            if zx - 7 < x < zx + zw + 7 and zy - 7 < y < zy + zh + 7:
                over_text.append((f, i, round(x), round(y)))
    for i, x, y, r in R.pulses(f):
        for zx, zy, zw, zh in zones:
            if zx - 7 < x < zx + zw + 7 and zy - 7 < y < zy + zh + 7:
                over_text.append((f, i, round(x), round(y), "pulse"))
    for i, rs in seen.items():
        e, t1, t2, t3, t4 = R.times(i)
        if t2 <= f < t4 and sorted(rs) != list(range(R.N_ROUTES)):
            copies.append((f, i, rs))
        if f < t2 and rs != [None]:
            copies.append((f, i, rs))
pulse_routes = sorted({r for f in range(0, R.TOTAL) for _i, _x, _y, r in R.pulses(f)})

# words that must fit where they sit, as drawn: (element, limits)
fits = []
n_last = R.updates(R.TOTAL - 1)
for r, (title, what, _work, href, _a) in enumerate(R.DESTS):
    x, y, w, h = R.card_rect(r)
    status = R.INTEROP if href is None else U.UP_TO_DATE
    for s in (title, what, status, "%%d updates" %% n_last):
        fits.append(dict(s=s, el=element(last, s), x0=x + R.TEXT_DX - 2, x1=x + w - 10))
    if href is None:
        sx, sy, sw, sh = R.shot_rect(r)
        for s in ("STAC API", "open standard", "pull, don't copy"):
            fits.append(dict(s=s, el=element(last, s), x0=sx + 2, x1=sx + sw - 2))
for k, (title, _sub, _fill) in enumerate(R.COLUMNS):
    hx, hy, hw, hh = R.header_rect(k)
    for s in title.split(" ") if k == R.INGEST else (title,):
        fits.append(dict(s=s, el=element(last, s), x0=hx + 2, x1=hx + hw - 2))
bx, by, bw, bh = R.badge_rect()
fits.append(dict(s=U.SOURCE_OF_TRUTH, el=element(last, U.SOURCE_OF_TRUTH),
                 x0=bx + 6, x1=bx + bw - 6))
for s in R.ROLES + R.HOURS:
    fits.append(dict(s=s, el=element(last, s), x0=px + 3, x1=px + pw - 3))
fits.append(dict(s=R.COMMUNITY, el=element(last, R.COMMUNITY), x0=R.CARD_X, x1=W - 6))
fits.append(dict(s=R.TITLE, el=element(last, R.TITLE), x0=20, x1=W - 20))

print(json.dumps(dict(
    style=G.S.name, slides=list(G.slides()), span=G.section_span("response"),
    total=R.TOTAL, fps=R.FPS, max_seconds=R.MAX_SECONDS, gif=G.section_gif("response"),
    via_section_frame=G.section_frame(9, "response") == R.response_svg(9),
    n=R.N, n_routes=R.N_ROUTES, n_passes=len(R.PASSES), emit_every=R.EMIT_EVERY,
    story_emit_every=2,
    last_rec_end=max(p["rec"][1] for p in R.PASSES),
    last_arrival=max(R.ARRIVAL), pulse_t=R.PULSE_T, end_hold=R.END_HOLD,
    in_flight_last=len(R.dots(R.TOTAL - 1)) + len(R.pulses(R.TOTAL - 1)),
    updates_last=n_last, reached_last=R.reached_people(R.TOTAL - 1),
    pulse_routes=pulse_routes,
    most_in_flight=max(len(R.dots(f)) for f in range(0, R.TOTAL, 2)),
    network=dict(
        titles=[has(settled, d[0]) for d in R.DESTS],
        up_to_date=count(settled, U.UP_TO_DATE), interop=count(settled, R.INTEROP),
        columns=[has(settled, "ingest"), has(settled, "Cloud storage"), has(settled, "STAC")],
        badge=has(settled, U.SOURCE_OF_TRUTH), legend=has(settled, "cloud-optimized"),
        community=has(settled, R.COMMUNITY), roles=[has(settled, s) for s in R.ROLES],
        hours=[has(settled, s) for s in R.HOURS], api=has(settled, "STAC API"),
        images=images(settled)),
    needed=[L.A_STAC] + [d[3] for d in U.DESTS],
    counts_last=count(last, "%%d updates" %% n_last),
    captions=len(re.findall(r'class="caption"', last)),
    wrong_shape=wrong_shape[:5], off_canvas=off_canvas[:5], copies=copies[:5],
    over_text=over_text[:5], fits=fits, canvas=(W, H),
    leaks=dict(settled=leaks(settled), last=leaks(last)),
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
class ResponseCase(unittest.TestCase):
    style = "sketch"

    @classmethod
    def setUpClass(cls):
        cls.P = probe(cls.style)

    def test_it_is_a_slide_that_plays_once_within_15_seconds(self):
        P = self.P
        self.assertEqual(P["style"], self.style)
        self.assertIn("response", P["slides"])
        self.assertEqual(P["span"], [0, P["total"] - 1])
        self.assertTrue(P["via_section_frame"])
        self.assertEqual(P["max_seconds"], 15)
        self.assertLessEqual(P["total"], P["max_seconds"] * P["fps"])
        self.assertEqual(P["gif"], [-1, 256, "full"],
                         "plays once; a globe and screenshots need the full palette")

    def test_the_whole_network_is_on_screen_once_settled_people_included(self):
        net = self.P["network"]
        self.assertEqual(net["titles"], [True] * self.P["n_routes"])
        self.assertEqual(self.P["n_routes"], 5, "four pages and the API")
        self.assertEqual(net["up_to_date"], 4)
        self.assertEqual(net["interop"], 1, "the API card says interoperable")
        self.assertTrue(net["api"])
        self.assertEqual(net["columns"], [True, True, True])
        self.assertTrue(net["badge"], "STAC is not named the single source of truth")
        self.assertTrue(net["legend"], "the formats legend says cloud-optimized")
        self.assertTrue(net["community"])
        self.assertEqual(net["roles"], [True] * len(net["roles"]))
        self.assertEqual(net["hours"], [True, True], "the responsiveness claim")
        for href in self.P["needed"]:
            self.assertIn(href, net["images"], "artwork missing from the settled frame")
        self.assertEqual(self.P["captions"], 0, "no caption box on this slide")

    def test_satellites_pass_the_whole_time(self):
        P = self.P
        self.assertGreaterEqual(P["n_passes"], 4)
        self.assertGreater(P["last_rec_end"], P["last_arrival"],
                           "the globe goes quiet before the last granule lands")

    def test_every_granule_reaches_every_destination_and_the_people(self):
        P = self.P
        self.assertEqual(P["updates_last"], P["n"])
        self.assertEqual(P["reached_last"], P["n"])
        self.assertEqual(P["counts_last"], P["n_routes"], "every card shows the same count")
        self.assertEqual(P["pulse_routes"], list(range(P["n_routes"])))
        self.assertEqual(P["in_flight_last"], 0, "it ends mid-flight")
        lag = P["total"] - 1 - P["last_arrival"] - P["pulse_t"]
        self.assertGreaterEqual(lag, P["end_hold"] - 1)
        self.assertLessEqual(lag, P["fps"], "it lingers over a second after the last lands")
        self.assertEqual(P["copies"], [], "a granule did not split into one per destination")

    def test_few_enough_granules_to_follow(self):
        # a quarter of what the story sends while a satellite records, and
        # never more than a handful of copies in the air at once
        P = self.P
        self.assertGreaterEqual(P["emit_every"], 4 * P["story_emit_every"])
        self.assertTrue(6 <= P["n"] <= 16, P["n"])
        self.assertLessEqual(P["most_in_flight"], 3 * P["n_routes"])

    def test_a_granule_keeps_its_format_until_ingest_then_is_cloud_optimized(self):
        self.assertEqual(self.P["wrong_shape"], [])
        self.assertEqual(self.P["off_canvas"], [])

    def test_nothing_is_ever_drawn_over_words(self):
        self.assertEqual(self.P["over_text"], [])

    @sup.needs_rsvg
    @sup.needs_magick
    def test_every_word_fits_where_it_sits_as_rendered(self):
        cw, ch = self.P["canvas"]
        self.assertGreaterEqual(len(self.P["fits"]), 5 * 4 + 3 + 4 + 1 + 7 + 2)
        for fit in self.P["fits"]:
            self.assertIsNotNone(fit["el"], "%r is not drawn" % fit["s"])
            x0, x1 = sup.ink_extent(fit["el"], cw, ch)
            self.assertGreaterEqual(x0, fit["x0"], "%r starts outside" % fit["s"])
            self.assertLessEqual(x1, fit["x1"], "%r runs out" % fit["s"])

    def test_no_flat_primitive_leaks_into_sketch(self):
        if self.style == "sketch":
            self.assertEqual(self.P["leaks"], dict(settled=0, last=0))


class TestResponseFlat(ResponseCase):
    style = "flat"


if __name__ == "__main__":
    unittest.main()
