"""
The disasters example's standards slide: from inconsistent formats to one
standard, deployed into every user's application -- PORTAL, MMGIS, ArcGIS --
in about 40 seconds, with a short manual bottleneck on the way.

The slide makes claims, so these count them in rendered frames: five formats
in, one format out and only after automated ingest -- a manual copy keeps its
shape all the way to the cards; a queue that backs up and drains; every
granule that reaches STAC lands on all three applications, and nothing is in
flight at the end; no "Web apps" column (the apps are the destinations); no
dot drawn over words; every word fits where it sits as rendered.

Subprocess-run with overrides pinned empty. Needs the gitignored artwork, the
Blue Marble texture, and ImageMagick to decode it.
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

TEXTURE = os.path.join(sup.DISASTERS_ASSETS, "blue-marble-2048.jpg")

PROBE = r'''
import json, re, sys
sys.path.insert(0, %(here)r)
import gen_frames as G, standards as T, story as ST, layout as L

def has(doc, s):
    return ">%%s</text>" %% G.esc(s) in doc

def count(doc, s):
    return doc.count(">%%s</text>" %% G.esc(s))

def count_cls(doc, cls):
    return len(re.findall(r'class="%%s"' %% re.escape(cls), doc))

def leaks(doc):
    return len(re.findall(r'<(rect|ellipse)[^>]*stroke="[^"]*"[^>]*>', doc))

def element(doc, s):
    m = re.search(r'<text[^>]*>%%s</text>' %% re.escape(G.esc(s)), doc)
    return m.group(0) if m else None

F = T.FUNNEL
W, H = L.W, L.H
KEY = {60: 60, "squeeze": T.SQUEEZE + 20, "shut": T.OPEN_AT - 1,
       "stac": T.STAC_BEAT + 15, "deploy": T.DEPLOY_AT + 30, "last": T.TOTAL - 1}
frames = {k: T.standards_svg(f) for k, f in KEY.items()}
show, shut, last = frames[60], frames["shut"], frames["last"]

# where every dot is, and what shape, across the whole slide
wrong_shape, copies, over_text, off_canvas = [], [], [], []
always = [T.header_rect(k) for k in range(len(T.COLUMNS))]
always += [(0, 0, W, 100), T.CAPTION, (80, T.LEGEND_Y - 20, 420, 70),
           (T.MOUTH_X + 10, T.MID_Y + T.MOUTH_H + 14, 220, 30)]
# a card's words, not its whole rect: copies run level into its left edge
always += [(x + T.TEXT_DX - 10, y, w - T.TEXT_DX, h)
           for x, y, w, h in (T.card_rect(r) for r in range(T.N_APPS))]
stations = [T.station_rect(k) for k in range(3)]
for f in range(0, T.TOTAL, 2):
    zones = always + (stations if f < T.OPEN_AT + 20 else [])
    seen = {}
    for i, x, y, shape, r in T.dots(f):
        own = ST.SHAPES[T.SAT[i]]
        if not (0 <= x <= W and 0 <= y <= H):
            off_canvas.append((f, i, round(x), round(y)))
        if F.mode[i] == "neck" and shape != own:
            wrong_shape.append((f, i, shape, "manual path changed a format"))
        if F.mode[i] == "open" and r is None and x < T.COL_X[T.INGEST] and shape != own:
            wrong_shape.append((f, i, shape, "before ingest"))
        if F.mode[i] == "open" and (r is not None or x >= T.COL_X[T.INGEST]) \
                and shape != ST.COG_SHAPE:
            wrong_shape.append((f, i, shape, "after ingest"))
        seen.setdefault(i, []).append(r)
        for zx, zy, zw, zh in zones:
            if zx - 5 <= x <= zx + zw + 5 and zy - 5 <= y <= zy + zh + 5:
                over_text.append((f, i, round(x), round(y)))
    for i, rs in seen.items():
        if T.AT_STAC[i] <= f < T.LANDS[i] and sorted(rs) != list(range(T.N_APPS)):
            copies.append((f, i, rs))
        if f < T.AT_STAC[i] and rs != [None]:
            copies.append((f, i, rs))

neck = [F.dep[i] for i in range(F.n) if F.mode[i] == "neck"]

# words that must fit where they sit, as drawn
fits = []
n_last = T.updates(T.TOTAL - 1)
for r, (title, what, _href, _a) in enumerate(T.APPS):
    x, y, w, h = T.card_rect(r)
    for s in (title, what, T.DIRECT, "%%d updates" %% n_last):
        fits.append(dict(s=s, el=element(last, s), x0=x + T.TEXT_DX - 2, x1=x + w - 10))
for k, (title, sub, _fill) in enumerate(T.COLUMNS):
    hx, hy, hw, hh = T.header_rect(k)
    for s in (title.split(" ") if k == T.INGEST else [title]) + sub.split(" · "):
        fits.append(dict(s=s, el=element(last, s), x0=hx + 2, x1=hx + hw - 2))
cx, cy, cw, ch = T.CAPTION
def caption_fit(f, s):
    el = element(T.standards_svg(f), s)
    # white on the bubble: recoloured so the ink can be measured on white
    el = el.replace('fill="%%s"' %% L.BUBBLE_FG, 'fill="#000000"') if el else el
    return dict(s=s, el=el, x0=cx + 12, x1=cx + cw - 12)
for start, s in T.CAPTIONS:
    fits.append(caption_fit(start + 30, s))
fits.append(dict(s=T.TITLE, el=element(last, T.TITLE), x0=20, x1=W - 20))
fits.append(dict(s=T.PROBLEM_TITLE, el=element(frames["squeeze"], T.PROBLEM_TITLE),
                 x0=20, x1=W - 20))

print(json.dumps(dict(
    style=G.S.name, slides=list(G.slides()), span=G.section_span("standards"),
    total=T.TOTAL, fps=T.FPS, max_seconds=T.MAX_SECONDS, gif=G.section_gif("standards"),
    via_section_frame=G.section_frame(9, "standards") == T.standards_svg(9),
    n=T.N, n_apps=T.N_APPS, end_hold=T.END_HOLD, last_land=max(T.LANDS),
    in_flight_last=len(T.dots(T.TOTAL - 1)),
    bottleneck_seconds=(T.OPEN_AT - T.SQUEEZE) / float(T.FPS),
    big_r=T.globe_at(60).r, small_r=T.globe_at(T.TOTAL - 1).r, BIG=T.BIG, SMALL=T.SMALL,
    shapes=list(ST.SHAPES), cog=ST.COG_SHAPE, n_sats=len(ST.CAST),
    show=dict(pipeline=has(show, "Download"), cards=[has(show, a[0]) for a in T.APPS],
              dots=count_cls(show, "dots") and len(T.dots(60))),
    legend_shut=[count_cls(shut, "key %%s" %% s) for s in ST.SHAPES],
    legend_cog_shut=count_cls(shut, "key circle"), legend_cog_last=count_cls(last, "key circle"),
    shut=dict(stations=[has(shut, a) for a, _b in T.PROBLEM],
              granules=bool(re.search(r">\d+ granules waiting</text>", shut)),
              problem_title=has(frames["squeeze"], T.PROBLEM_TITLE),
              by_hand=count(shut, T.BY_HAND), direct=count(shut, T.DIRECT),
              columns=[has(shut, t) for t, _s, _f in T.COLUMNS]),
    last=dict(title=has(last, T.TITLE), stations=sum(1 for a, _b in T.PROBLEM if has(last, a)),
              columns=[has(last, t.split(" ")[0] if k == T.INGEST else t)
                       for k, (t, _s, _f) in enumerate(T.COLUMNS)],
              apps=[has(last, a[0]) for a in T.APPS],
              direct=count(last, T.DIRECT), by_hand=count(last, T.BY_HAND),
              updates=count(last, "%%d updates" %% n_last), n_updates=n_last,
              web_apps="Web apps" in last, interoperable="interoperable" in last,
              scalable="scalable" in last, waiting="granules waiting" in last,
              images=sorted(set(re.findall(r'<image href="([^"]+)"', last)))),
    any_web_apps=any("Web apps" in d for d in frames.values()),
    needed=[L.A_STAC, L.A_SHOT_HOME, L.A_SHOT_VIZ, L.A_ARCGIS_ONLINE, L.A_ARCGIS_DESKTOP],
    wrong_shape=wrong_shape[:5], copies=copies[:5], off_canvas=off_canvas[:5],
    n_over=len(over_text), over=over_text[:5],
    neck=neck, service=F.service,
    q_shut=len(F.waiting(T.OPEN_AT - 1)), q_end=len(F.waiting(T.TOTAL - 1)),
    before=sum(1 for t in T.ARRIVAL if t < T.OPEN_AT),
    after=sum(1 for t in T.ARRIVAL if T.OPEN_AT <= t < T.OPEN_AT + (T.OPEN_AT - T.SQUEEZE)),
    fits=fits, canvas=(W, H),
    n_captions=len(T.CAPTIONS), dwell=T.DWELL, min_dwell=T.MIN_DWELL,
    caption_size=T.CAPTION_SIZE, story_caption_size=15,
    caption_box=T.CAPTION, caption_in_last=count_cls(last, "caption"),
    leaks={k: leaks(d) for k, d in frames.items()},
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
class StandardsCase(unittest.TestCase):
    style = "sketch"

    @classmethod
    def setUpClass(cls):
        cls.P = probe(cls.style)

    def test_it_is_a_slide_of_at_most_40_seconds_that_plays_once(self):
        P = self.P
        self.assertEqual(P["style"], self.style)
        self.assertIn("standards", P["slides"])
        self.assertEqual(P["slides"].index("standards"), P["slides"].index("story") + 1)
        self.assertLessEqual(P["total"], P["max_seconds"] * P["fps"])
        self.assertGreater(P["total"], 35 * P["fps"])
        self.assertEqual(P["span"], [0, P["total"] - 1])
        self.assertEqual(P["gif"], [-1, 256, "full"])
        self.assertTrue(P["via_section_frame"])

    def test_it_opens_on_the_globe_alone(self):
        self.assertEqual(self.P["big_r"], self.P["BIG"][2])
        self.assertEqual(self.P["small_r"], self.P["SMALL"][2])
        self.assertFalse(self.P["show"]["pipeline"])
        self.assertEqual(self.P["show"]["cards"], [False] * self.P["n_apps"])
        self.assertEqual(self.P["show"]["dots"], 0)

    def test_every_format_has_its_own_shape_and_none_is_the_cog(self):
        self.assertEqual(len(set(self.P["shapes"])), self.P["n_sats"])
        self.assertNotIn(self.P["cog"], self.P["shapes"])
        self.assertEqual(self.P["legend_shut"], [1] * self.P["n_sats"])
        self.assertEqual(self.P["legend_cog_shut"], 0)
        self.assertEqual(self.P["legend_cog_last"], 1)

    def test_only_automated_ingest_makes_a_standard_format(self):
        # a manual copy keeps its format all the way to the application; an
        # automated one is cloud-optimized from ingest on, on every route
        self.assertEqual(self.P["wrong_shape"], [])

    def test_the_bottleneck_is_short_backs_up_then_drains(self):
        P = self.P
        self.assertLessEqual(P["bottleneck_seconds"], 8)
        neck = P["neck"]
        self.assertEqual(neck, sorted(neck))
        self.assertGreaterEqual(min(b - a for a, b in zip(neck, neck[1:])), P["service"])
        self.assertGreater(P["q_shut"], 10)
        self.assertEqual(P["q_end"], 0)
        self.assertGreater(P["after"], 5 * max(1, P["before"]))

    def test_every_granule_reaching_stac_lands_on_every_application(self):
        P = self.P
        self.assertEqual(P["copies"], [], "a granule past STAC is not one copy per app")
        self.assertEqual(P["off_canvas"], [])
        self.assertEqual(P["in_flight_last"], 0)
        self.assertLessEqual(P["last_land"] + P["end_hold"], P["total"])
        self.assertEqual(P["last"]["n_updates"], P["n"], "every granule lands")
        self.assertEqual(P["last"]["updates"], P["n_apps"], "the same count on every card")

    def test_it_names_the_problem_then_the_standard_and_the_apps(self):
        shut, last = self.P["shut"], self.P["last"]
        self.assertEqual(shut["stations"], [True] * 3)
        self.assertTrue(shut["granules"])
        self.assertTrue(shut["problem_title"])
        self.assertEqual(shut["columns"], [False] * 3, "the standard is not there yet")
        self.assertEqual(shut["by_hand"], self.P["n_apps"])
        self.assertEqual(shut["direct"], 0)
        self.assertTrue(last["title"])
        self.assertEqual(last["stations"], 0)
        self.assertEqual(last["columns"], [True] * 3)
        self.assertEqual(last["apps"], [True] * self.P["n_apps"])
        self.assertEqual(last["direct"], self.P["n_apps"])
        self.assertEqual(last["by_hand"], 0)
        self.assertTrue(last["interoperable"])
        self.assertTrue(last["scalable"])
        self.assertFalse(last["waiting"])
        for href in self.P["needed"]:
            self.assertIn(href, last["images"], href)

    def test_each_caption_stays_long_enough_to_read_and_is_set_large(self):
        P = self.P
        self.assertLessEqual(P["n_captions"], 4)
        self.assertGreaterEqual(min(P["dwell"]), P["min_dwell"], P["dwell"])
        self.assertGreaterEqual(P["min_dwell"], 8 * P["fps"])
        self.assertGreater(P["caption_size"], P["story_caption_size"])
        x, y, w, h = P["caption_box"]
        self.assertLessEqual(y + h, P["canvas"][1])
        self.assertEqual(P["caption_in_last"], 1)

    def test_the_apps_are_the_destinations_so_there_is_no_web_apps_column(self):
        self.assertFalse(self.P["any_web_apps"])
        self.assertEqual(self.P["n_apps"], 3)

    def test_no_dot_ever_covers_words(self):
        self.assertEqual(self.P["n_over"], 0, self.P["over"])

    @sup.needs_rsvg
    def test_every_word_fits_where_it_sits_as_rendered(self):
        cw, ch = self.P["canvas"]
        self.assertGreaterEqual(len(self.P["fits"]), 3 * 4 + 3 * 3 + 4 + 2)
        for fit in self.P["fits"]:
            self.assertIsNotNone(fit["el"], "%r is not drawn" % fit["s"])
            x0, x1 = sup.ink_extent(fit["el"], cw, ch)
            self.assertGreaterEqual(x0, fit["x0"], "%r starts outside" % fit["s"])
            self.assertLessEqual(x1, fit["x1"], "%r runs out" % fit["s"])

    def test_no_flat_primitive_leaks_into_sketch(self):
        if self.style == "sketch":
            self.assertEqual(set(self.P["leaks"].values()), {0}, self.P["leaks"])


class TestStandardsFlat(StandardsCase):
    style = "flat"


if __name__ == "__main__":
    unittest.main()
