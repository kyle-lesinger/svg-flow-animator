"""
The disasters example's infrastructure slide: the whole ecosystem at once,
with its reusable cyberinfrastructure -- Ingest UI, Airflow, STAC, JupyterHub,
TinaCMS, MyST Docs, Grafana, GitHub -- brought forward, and no data paths.

These check its claims in rendered frames: no flow, arrow or link is drawn
(the point is what is reused, not what moves); each piece comes forward on its
own beat, named while it does, and stays; each comes through the wash exactly
where the diagram draws it, because it is drawn by the same function; the
blocks' headings never wash out; the finished picture names what the pieces
add up to; the PNG is only the reusable infrastructure, in its blocks; and the
words fit.

Subprocess-run with overrides pinned empty. Needs the gitignored artwork.
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
import json, re, subprocess, sys
sys.path.insert(0, %(here)r)
import gen_frames as G, infra as I, layout as L

def has(doc, s):
    return ">%%s</text>" %% G.esc(s) in doc

def leaks(doc):
    return len(re.findall(r'<(rect|ellipse)[^>]*stroke="[^"]*"[^>]*>', doc))

def element(doc, s):
    m = re.search(r'<text[^>]*>%%s</text>' %% re.escape(G.esc(s)), doc)
    return m.group(0) if m else None

def paths(doc):
    """Anything that draws a data path: flows, packets, links, arrowheads."""
    return dict(flow=doc.count('stroke="%%s"' %% L.FLOW),
                packets=doc.count('stroke="%%s"' %% L.DOT),
                markers=doc.count("marker-end"),
                push=has(doc, "Push data"))

def forward(doc):
    """The pieces drawn above the wash, and how strongly."""
    return {k: float(o) for k, o in re.findall(
        r'<g class="piece" data-piece="([a-z]+)" opacity="([0-9.]+)"', doc)}

def line(k):
    return "%%s: %%s" %% I.PIECES[k][1:]

frames = sorted({0, I.WHOLE + I.RECEDE // 2, I.TOTAL - 1}
                | {I.beat_start(k) + I.FADE for k in range(len(I.PIECES))})
docs = {f: I.infra_svg(f) for f in frames}
last = docs[I.TOTAL - 1]

beats = []
for k, key in enumerate(I.KEYS):
    before, during = I.infra_svg(I.beat_start(k) - 1), docs[I.beat_start(k) + I.FADE]
    beats.append(dict(key=key, before=forward(before).get(key),
                      during=forward(during).get(key),
                      named=[j for j in range(len(I.PIECES)) if has(during, line(j))]))

# each piece's own markup, and whether the base picture draws it identically
base, _sep, above = last.partition('<rect class="wash"')
end = I.spin(I.TOTAL - 1)
parts = [p for k in I.KEYS for p in I.piece(k, end)]
in_place = {k: all(part in base for part in I.piece(k, end)) for k in I.KEYS}

out = subprocess.run([sys.executable, "gen_frames.py", "--poster=infra"],
                     capture_output=True, text=True, check=True).stdout.strip()
poster = open(out).read()
images = lambda doc: sorted(set(re.findall(r'<image href="([^"]+)"', doc)))
# words the PNG must not carry: everything named that is not reusable
others = ([lab for _a, lab in G.COMMUNITY_ITEMS
           if lab not in ("MyST Docs", "Grafana", "Github")]
          + list(L.PORTAL_SHOTS) + ["ROSES", "DRCS", "Push data"])

fits = [dict(s=I.TITLE, el=element(last, I.TITLE), x0=20, x1=L.W - 20)]
for k in range(len(I.PIECES)):
    doc = docs[I.beat_start(k) + I.FADE]
    fits.append(dict(s=line(k), el=element(doc, line(k)), x0=20, x1=L.W - 20))
for q, (x, y, w, h) in zip(I.QUALITIES, I.pill_rects()):
    fits.append(dict(s=q, el=element(last, q), x0=x + 6, x1=x + w - 6))

print(json.dumps(dict(
    style=G.S.name, slides=list(G.slides()), span=G.section_span("infra"),
    total=I.TOTAL, fps=I.FPS, max_seconds=I.MAX_SECONDS,
    gif=G.section_gif("infra"),
    via_section_frame=G.section_frame(9, "infra") == I.infra_svg(9),
    n=len(I.PIECES), keys=I.KEYS,
    paths={f: paths(d) for f, d in docs.items()},
    wash_first=('class="wash"' in docs[0]),
    first_forward=forward(docs[0]), beats=beats,
    last_forward=forward(last), in_place=in_place,
    title=I.TITLE, title_last=has(last, I.TITLE),
    qualities=[has(last, q) for q in I.QUALITIES],
    lines_last=[has(last, line(k)) for k in range(len(I.PIECES))],
    titles_forward=[I.heading(b) in above for b in G.BLOCKS],
    notes=[f for f, d in list(docs.items()) + [("png", poster)]
           if has(d, "no automated data path")],
    poster_images=images(poster), allowed_images=images("".join(parts)),
    poster_pieces=all(p in poster for p in parts),
    poster_titles=[I.heading(b) in poster for b in G.BLOCKS],
    poster_paths=paths(poster),
    poster_qualities=[has(poster, q) for q in I.QUALITIES],
    poster_others=[t for t in others if has(poster, t)],
    poster_leaks=leaks(poster),
    top_clear=I.LINE_Y + 8 < L.BOX_EGIS[1]
              and all(y + h < L.BOX_EGIS[1] for _x, y, _w, h in I.pill_rects()),
    fits=fits, canvas=(L.W, L.H), leaks=leaks(last),
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
class InfraCase(unittest.TestCase):
    style = "sketch"

    @classmethod
    def setUpClass(cls):
        cls.P = probe(cls.style)

    def test_it_is_a_slide_that_plays_once_within_30_seconds(self):
        P = self.P
        self.assertEqual(P["style"], self.style)
        self.assertIn("infra", P["slides"])
        self.assertEqual(P["span"], [0, P["total"] - 1])
        self.assertTrue(P["via_section_frame"])
        self.assertLessEqual(P["total"], P["max_seconds"] * P["fps"])
        self.assertEqual(P["gif"], [-1, 256, "full"],
                         "plays once; screenshots need the full palette")

    def test_no_data_path_is_drawn_in_any_frame(self):
        # the point is what is built once and reused, not what moves
        for f, p in self.P["paths"].items():
            self.assertEqual(p, dict(flow=0, packets=0, markers=0, push=False),
                             "frame %s draws a path" % f)

    def test_it_opens_on_the_whole_ecosystem(self):
        self.assertFalse(self.P["wash_first"], "frame 0 is already washed out")
        self.assertEqual(self.P["first_forward"], {})

    def test_each_piece_comes_forward_on_its_own_beat_named_and_stays(self):
        for k, b in enumerate(self.P["beats"]):
            self.assertIsNone(b["before"], "%s is forward early" % b["key"])
            self.assertEqual(b["during"], 1.0, "%s never comes forward" % b["key"])
            self.assertEqual(b["named"], [k], "beat %d names %r" % (k, b["named"]))
        self.assertEqual(self.P["last_forward"],
                         {k: 1.0 for k in self.P["keys"]}, "one has dropped back")

    def test_each_piece_comes_through_exactly_where_the_diagram_draws_it(self):
        # drawn by the same function as the diagram underneath, so the copy
        # above the wash covers the original pixel for pixel
        self.assertEqual(self.P["in_place"], {k: True for k in self.P["keys"]})

    def test_it_ends_on_what_the_seven_add_up_to(self):
        P = self.P
        self.assertIn("cyberinfrastructure", P["title"])
        self.assertTrue(P["title_last"])
        self.assertEqual(P["qualities"], [True] * 3)
        self.assertEqual(P["lines_last"], [False] * P["n"],
                         "a piece's line is left over the qualities")
        self.assertTrue(P["top_clear"], "the heading runs into Federal Partners")

    def test_the_headings_never_wash_out(self):
        self.assertEqual(self.P["titles_forward"], [True] * 6)

    def test_no_frame_and_not_the_png_says_no_automated_data_path(self):
        self.assertEqual(self.P["notes"], [])

    def test_the_png_is_only_the_reusable_infrastructure(self):
        P = self.P
        self.assertEqual(P["poster_images"], P["allowed_images"],
                         "an image that is not reusable infrastructure")
        self.assertEqual(P["poster_others"], [])
        self.assertTrue(P["poster_pieces"], "a piece is missing or moved")
        self.assertEqual(P["poster_titles"], [True] * 6, "a heading is missing")
        self.assertEqual(P["poster_paths"],
                         dict(flow=0, packets=0, markers=0, push=False))
        self.assertEqual(P["poster_qualities"], [True] * 3)
        if self.style == "sketch":
            self.assertEqual(P["poster_leaks"], 0)

    @sup.needs_rsvg
    @sup.needs_magick
    def test_every_word_fits_as_rendered(self):
        cw, ch = self.P["canvas"]
        self.assertEqual(len(self.P["fits"]), 1 + self.P["n"] + 3)
        for fit in self.P["fits"]:
            self.assertIsNotNone(fit["el"], "%r is not drawn" % fit["s"])
            x0, x1 = sup.ink_extent(fit["el"], cw, ch)
            self.assertGreaterEqual(x0, fit["x0"], "%r starts outside" % fit["s"])
            self.assertLessEqual(x1, fit["x1"], "%r runs out" % fit["s"])

    def test_no_flat_primitive_leaks_into_sketch(self):
        if self.style == "sketch":
            self.assertEqual(self.P["leaks"], 0)


class TestInfraFlat(InfraCase):
    style = "flat"


if __name__ == "__main__":
    unittest.main()
