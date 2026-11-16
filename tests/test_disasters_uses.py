"""
The disasters example's uses slide: what the data is for -- a dashboard, an
analysis tool, an article, a lesson -- fed before STAC by separate silos and
people doing hand-offs, then by one system (STAC + one editor, TinaCMS).

The slide makes claims, so these count them: before, there is no catalog and
each app has its own copy, lane and schedule; a person really holds each
granule for their whole hand-off, and their line grows; after, one system
feeds every route, nobody is left on one, and every audience is updated many
times over; old and new words never overlap mid-switch; the screen is never
crowded; no granule overtakes another or is drawn over words; and every word
fits its card, tag or box as actually rendered.

Subprocess-run with overrides pinned empty. Needs the gitignored artwork (the
cards are page screenshots); measuring rendered text needs rsvg and magick.
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
import gen_frames as G, uses as U, layout as L

def has(doc, s):
    return ">%%s</text>" %% G.esc(s) in doc

def count(doc, cls):
    return len(re.findall(r'class="%%s"' %% re.escape(cls), doc))

def leaks(doc):
    return len(re.findall(r'<(rect|ellipse)[^>]*stroke="[^"]*"[^>]*>', doc))

def element(doc, s):
    """The <text> element that draws `s`, exactly as the frame has it."""
    m = re.search(r'<text[^>]*>%%s</text>' %% re.escape(G.esc(s)), doc)
    return m.group(0) if m else None

A = U.AUTOMATE_AT
hand, last = U.uses_svg(A - 1), U.uses_svg(U.TOTAL - 1)
images = lambda doc: set(re.findall(r'<image href="([^"]+)"', doc))
switch = [U.uses_svg(f) for f in range(A, A + U.MORPH + 1)]
both_worlds = [A + i for i, doc in enumerate(switch)
               if (has(doc, "by hand · days behind") and has(doc, U.UP_TO_DATE))
               or any(has(doc, d[2]) for d in U.DESTS) and has(doc, U.SIMPLIFIED)]
lanes = [U.route(r, 0) for r in range(U.N_ROUTES)]
fans = [U.route(r, 1) for r in range(U.N_ROUTES)]
settled = range(A + U.MORPH + 60, U.TOTAL)

# every granule a person finished: (route, start, done, reaches its card)
by_hand = [(r, s["start"], s["done"], U.arrival(r, g))
           for r in range(U.N_ROUTES) for g, s in enumerate(U.SCHED[r])
           if s["done"] is not None]

overtakes, over_text = [], []
for f in range(0, U.TOTAL, 2):
    zones = U.word_zones(f)
    for r in range(U.N_ROUTES):
        es = [U.remaining(r, g, f) for g in range(U.N_GRANULES)]
        on = [(g, e) for g, e in enumerate(es) if e is not None]
        for (g0, e0), (g1, e1) in zip(on, on[1:]):
            if e1 < e0 - 1e-6:
                overtakes.append((f, r, g0, g1))
    for r, g, x, y in U.dots(f):
        for zx, zy, zw, zh in zones:
            if zx - 7 <= x <= zx + zw + 7 and zy - 7 <= y <= zy + zh + 7:
                over_text.append((f, r, g, round(x), round(y)))

# words that must fit where they sit, as drawn: (element, right limit)
fits = []
for doc in (hand, last):
    for r, (title, what, work, _h, _a) in enumerate(U.DESTS):
        x, y, w, h = U.card_rect(r)
        for s in (title, what, "by hand · days behind", U.UP_TO_DATE):
            el = element(doc, s)
            if el:
                fits.append(dict(s=s, el=el, x0=x + U.TEXT_DX - 2, x1=x + w - 10))
        tx, ty, tw, th = U.tag_rect(r)
        for s in (work, U.SIMPLIFIED):
            el = element(doc, s)
            if el:
                fits.append(dict(s=s, el=el, x0=tx + 6, x1=tx + tw - 6))
tx, ty, tw, th = U.TINA_BOX
for s in ("TinaCMS", "one editor", "for every app"):
    fits.append(dict(s=s, el=element(last, s), x0=tx, x1=tx + tw - 6))
bx, by, bw, bh = U.badge_rect()
fits.append(dict(s=U.SOURCE_OF_TRUTH, el=element(last, U.SOURCE_OF_TRUTH),
                 x0=bx + 6, x1=bx + bw - 6))

print(json.dumps(dict(
    style=G.S.name, slides=list(G.slides()), span=G.section_span("uses"),
    total=U.TOTAL, fps=U.FPS, max_seconds=U.MAX_SECONDS,
    gif=G.section_gif("uses"),
    via_section_frame=G.section_frame(9, "uses") == U.uses_svg(9),
    service=list(U.SERVICE), emit_every=U.EMIT_EVERY, automate_at=A,
    n_hand=len(U.HAND), n_routes=U.N_ROUTES, by_hand=by_hand,
    waiting_before=[len(U.waiting(r, A - 1)) for r in range(U.N_ROUTES)],
    waiting_after=[len(U.waiting(r, A + U.MORPH + 30)) for r in range(U.N_ROUTES)],
    hand_updates=[U.updates(r, A - 1) for r in range(U.N_ROUTES)],
    end_updates=[U.updates(r, U.TOTAL - 1) for r in range(U.N_ROUTES)],
    n_granules=U.N_GRANULES, from_stac=len(U.AUTO), end_hold=U.END_HOLD,
    last_arrival=max(U.ARRIVALS[r][-1] for r in range(U.N_ROUTES)),
    first_from_stac=min(U.AUTO), in_flight_last=len(U.dots(U.TOTAL - 1)),
    people=dict(hand=count(hand, "person"), last=count(last, "person")),
    tasks=dict(hand=[has(hand, d[2]) for d in U.DESTS],
               last=[has(last, d[2]) for d in U.DESTS]),
    titles_last=[has(last, d[0]) for d in U.DESTS],
    simplified_last=last.count(">%%s</text>" %% G.esc(U.SIMPLIFIED)),
    source_of_truth=has(last, U.SOURCE_OF_TRUTH),
    editors=dict(hand=count(hand, "editor"), last=count(last, "editor")),
    claims=[t for t in re.findall(r">([^<>]*)</text>", last)
            if re.search(r"(?i)automat|hand-offs", t)],
    stac=L.A_STAC, tina=L.A_TINA,
    hand_images=sorted(images(hand)), last_images=sorted(images(last)),
    copies=dict(hand=count(hand, "copy"), last=count(last, "copy")),
    silos=dict(hand=count(hand, "silo"), last=count(last, "silo")),
    one_system_last=has(last, "One system"),
    first_departures=[U.emit_at(r, 0) for r in range(U.N_ROUTES)],
    lane_starts=[l[0] for l in lanes], lane_ys=[sorted({round(p[1], 3) for p in l})
                                                for l in lanes],
    silo_x=U.SILO_X, fan_starts=[l[0] for l in fans],
    system_right=U.SYSTEM[0] + U.SYSTEM[2],
    system_span=(U.SYSTEM[1], U.SYSTEM[1] + U.SYSTEM[3]),
    both_worlds=both_worlds,
    most_settled=max(len(U.dots(f)) for f in settled),
    captions=[s for _t, s in U.CAPTIONS],
    overtakes=overtakes[:5], over_text=over_text[:5], fits=fits,
    canvas=(L.W, L.H), leaks=dict(hand=leaks(hand), last=leaks(last)),
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
class UsesCase(unittest.TestCase):
    style = "sketch"

    @classmethod
    def setUpClass(cls):
        cls.P = probe(cls.style)

    def test_it_is_a_slide_that_plays_once_within_30_seconds(self):
        P = self.P
        self.assertEqual(P["style"], self.style)
        self.assertIn("uses", P["slides"])
        self.assertEqual(P["span"], [0, P["total"] - 1])
        self.assertTrue(P["via_section_frame"])
        self.assertLessEqual(P["total"], P["max_seconds"] * P["fps"])
        self.assertEqual(P["gif"], [-1, 256, "full"],
                         "plays once; screenshots need the full palette")

    def test_a_person_holds_every_granule_for_their_whole_hand_off(self):
        self.assertTrue(self.P["by_hand"], "nobody delivered anything by hand")
        for r, start, done, reaches in self.P["by_hand"]:
            self.assertAlmostEqual(done - start, self.P["service"][r])
            self.assertGreater(reaches, done, "a granule skipped its person")
            self.assertLessEqual(done, self.P["automate_at"])

    def test_by_hand_the_line_grows_and_the_audience_waits(self):
        P = self.P
        # a person takes longer than the gap between granules: the problem
        for s in P["service"]:
            self.assertGreater(s, P["emit_every"])
        for q in P["waiting_before"]:
            self.assertGreaterEqual(q, 2, "no backlog to clear")
        for n in P["hand_updates"]:
            self.assertLess(n, P["n_hand"], "every granule got through by hand")

    def test_before_stac_every_app_is_its_own_silo(self):
        P = self.P
        self.assertNotIn(P["stac"], P["hand_images"], "STAC is there before STAC")
        self.assertNotIn(P["tina"], P["hand_images"])
        self.assertEqual(P["copies"]["hand"], P["n_routes"], "a copy per app")
        self.assertEqual(P["silos"]["hand"], 1, "the silos' dividers")
        # its own lane: level, from the same start, at its own height
        for (x, _y), ys in zip(P["lane_starts"], P["lane_ys"]):
            self.assertEqual(x, P["silo_x"])
            self.assertEqual(len(ys), 1, "a lane should run level")
        self.assertEqual(len({ys[0] for ys in P["lane_ys"]}), P["n_routes"])
        # its own schedule: the same granule sets off for each at its own time
        self.assertEqual(len(set(P["first_departures"])), P["n_routes"])

    def test_after_one_system_feeds_every_app(self):
        P = self.P
        self.assertIn(P["stac"], P["last_images"])
        self.assertIn(P["tina"], P["last_images"])
        self.assertTrue(P["one_system_last"])
        self.assertEqual(P["copies"]["last"], 0, "the separate copies remain")
        self.assertEqual(P["silos"]["last"], 0)
        lo, hi = P["system_span"]
        for x, y in P["fan_starts"]:
            self.assertAlmostEqual(x, P["system_right"])
            self.assertTrue(lo < y < hi, "a route starts outside the system")

    def test_old_and_new_words_never_share_the_screen(self):
        # crossfaded together they read as one smudged line mid-switch
        self.assertEqual(self.P["both_worlds"], [])

    def test_the_screen_is_never_crowded(self):
        # once the backlog has cleared: a couple of granules per route, which
        # reads as flow -- a stream of them buried the words
        self.assertLessEqual(self.P["most_settled"], 2 * self.P["n_routes"])

    def test_simplified_one_editor_not_a_person_per_app(self):
        # Not automation: the four hand-offs become one person at one editor,
        # and STAC is named for what it is -- the single source of truth.
        P = self.P
        self.assertEqual(P["editors"], dict(hand=0, last=1))
        self.assertTrue(P["source_of_truth"])
        self.assertEqual(P["claims"], [], "the slide claims automation")

    def test_one_system_nobody_is_in_the_way_and_every_audience_keeps_up(self):
        P = self.P
        self.assertEqual(P["people"]["hand"], P["n_routes"])
        self.assertEqual(P["people"]["last"], 0, "a person is still on a route")
        self.assertEqual(P["tasks"]["hand"], [True] * P["n_routes"])
        self.assertEqual(P["tasks"]["last"], [False] * P["n_routes"])
        self.assertEqual(P["simplified_last"], P["n_routes"])
        self.assertEqual(P["titles_last"], [True] * P["n_routes"])
        self.assertEqual(P["waiting_after"], [0] * P["n_routes"],
                         "the backlog should empty once one system runs")
        # one source of truth: every app ends holding every granule
        self.assertEqual(P["end_updates"], [P["n_granules"]] * P["n_routes"])
        self.assertEqual(P["in_flight_last"], 0, "it ends mid-flight")

    def test_it_stops_once_four_granules_have_left_stac(self):
        # kept short: four granules from STAC, each to every app, then the end
        P = self.P
        self.assertEqual(P["from_stac"], 4)
        self.assertGreater(P["first_from_stac"], P["automate_at"])
        self.assertLessEqual(P["total"] - 1 - P["last_arrival"], P["fps"],
                             "it lingers over a second after the last lands")

    def test_no_granule_overtakes_another(self):
        self.assertEqual(self.P["overtakes"], [])

    def test_no_granule_is_ever_drawn_over_words(self):
        self.assertEqual(self.P["over_text"], [])

    @sup.needs_rsvg
    @sup.needs_magick
    def test_every_word_fits_its_card_or_tag_as_rendered(self):
        cw, ch = self.P["canvas"]
        self.assertGreaterEqual(len(self.P["fits"]), 4 * 4 + 3)
        for fit in self.P["fits"]:
            x0, x1 = sup.ink_extent(fit["el"], cw, ch)
            self.assertGreaterEqual(x0, fit["x0"], "%r starts outside" % fit["s"])
            self.assertLessEqual(x1, fit["x1"], "%r runs out" % fit["s"])

    def test_no_flat_primitive_leaks_into_sketch(self):
        if self.style == "sketch":
            self.assertEqual(self.P["leaks"], dict(hand=0, last=0))


class TestUsesFlat(UsesCase):
    style = "flat"


if __name__ == "__main__":
    unittest.main()
