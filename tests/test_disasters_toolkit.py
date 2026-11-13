"""
The disasters example's toolkit slide: the reusable cyberinfrastructure in a
tray across the top, and the ecosystem assembled beneath it section by
section, each piece moving down out of the tray to where it works.

These check its claims in rendered frames: it opens on the tray alone; the
sections arrive in the stated order -- Data Integration and Funded Projects &
Partners together first -- and stay; every piece goes tray -> flying ->
placed on its own beat, and lands drawn exactly as the diagram draws it, with
no transform left on it; GitHub, used twice, keeps its tray copy until its
last trip; no path is drawn until everything is in place, and no "no
automated data path"; then the legs into STAC draw in before the legs out of
it, Community's link reaches STAC and is grey, not flow green; it ends on
everything in place and connected under the three qualities, the tray gone;
and the words fit.

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
import json, re, sys
sys.path.insert(0, %(here)r)
import gen_frames as G, toolkit as T, infra as I, layout as L

def has(doc, s):
    return ">%%s</text>" %% G.esc(s) in doc

def leaks(doc):
    return len(re.findall(r'<(rect|ellipse)[^>]*stroke="[^"]*"[^>]*>', doc))

def element(doc, s):
    m = re.search(r'<text[^>]*>%%s</text>' %% re.escape(G.esc(s)), doc)
    return m.group(0) if m else None

def paths(doc):
    return dict(flow=doc.count('stroke="%%s"' %% L.FLOW),
                packets=doc.count('stroke="%%s"' %% L.DOT),
                markers=doc.count("marker-end"),
                push=has(doc, "Push data"))

def states(doc):
    return {"%%s/%%s" %% (k, p): s for k, p, s in re.findall(
        r'<g class="piece" data-piece="([a-z]+)" data-part="([0-9])" '
        r'data-state="([a-z]+)">', doc)}

def blocks(doc):
    return sorted(set(re.findall(r'<g class="block" data-block="([a-z]+)"', doc)))

first, last = T.toolkit_svg(0), T.toolkit_svg(T.TOTAL - 1)

steps = []
for s, (bs, keys) in enumerate(T.STEPS):
    doc = T.toolkit_svg(T.step_start(s) + T.APPEAR + 1)
    steps.append(dict(want=sorted(b for t in T.STEPS[:s + 1] for b in t[0]),
                      got=blocks(doc)))
before_first = blocks(T.toolkit_svg(T.step_start(0) - 1))

trips = []
for s, j, key, part in T.DROPS:
    name = "%%s/%%d" %% (key, part)
    trips.append(dict(
        name=name,
        before=states(T.toolkit_svg(T.drop_start(s, j) - 1)).get(name),
        mid=states(T.toolkit_svg(T.drop_start(s, j) + T.FLY // 2)).get(name),
        after=states(T.toolkit_svg(T.landed_at(s, j))).get(name)))

# GitHub after its first trip has landed, before its second starts
gh = [(s, j) for s, j, k, p in T.DROPS if k == "github"]
between = states(T.toolkit_svg(T.landed_at(*gh[0]) + 1))

# placed exactly as the diagram draws it: its markup, untransformed
exact = {"%%s/%%d" %% (k, p): ('data-state="placed">' + I.piece(k)[p]) in last
         for _s, _j, k, p in T.DROPS}

sampled = sorted({0, T.ALL_AT - 1} | {T.step_start(s) + T.APPEAR + 1
                                      for s in range(len(T.STEPS))})
docs = {f: T.toolkit_svg(f) for f in sampled}

def links(doc):
    return {n: float(p) for n, p, _o in re.findall(
        r'<g class="link" data-link="([a-z0-9_]+)" data-progress="([0-9.]+)" '
        r'data-opacity="([0-9.]+)">', doc)}

def opacities(doc):
    return {n: float(o) for n, _p, o in re.findall(
        r'<g class="link" data-link="([a-z0-9_]+)" data-progress="([0-9.]+)" '
        r'data-opacity="([0-9.]+)">', doc)}

# the order of the connections: into STAC first, then out, then Community's
out_before_in, engage_before_in, fan_before_portal, in_before_spokes = [], [], [], []
for f in range(T.CONVERGE_AT, T.TOTAL, 2):
    lk = links(T.toolkit_svg(f))
    all_in = all(lk.get(n, 0) >= 1 for n in T.INTO_STAC)
    spokes_met = all(lk.get("spoke_%%d" %% i, 0) >= 1 for i in range(len(L.SOURCES)))
    if any(n in lk for n in T.INTO_STAC) and not spokes_met:
        in_before_spokes.append(f)
    if any("portal_fan_%%d" %% i in lk for i in range(4)) and lk.get("stac_to_portal", 0) < 1:
        fan_before_portal.append(f)
    if any(n in lk for n, _w in T.OUT_OF_STAC) and not all_in:
        out_before_in.append(f)
    if "engagement" in lk and not all_in:
        engage_before_in.append(f)
last_links = links(last)
last_op = opacities(last)
faint = [n for n in last_op if n.startswith(("spoke_", "portal_fan_", "hub_to", "push"))]
stubs, trunk = T.engagement()
sx, sy, sw, sh = L.BOX_STAC
cx0, cy0, cw, ch = L.BOX_COMMUNITY
engage_grey = last.count('stroke="%%s"' %% T.ENGAGE_COLOR)
lx, ly, lw, lh = T.label_rect()

fits = [dict(s=T.TITLE, el=element(last, T.TITLE), x0=20, x1=L.W - 20),
        # drawn inside the ecosystem group, so measured in its coordinates
        dict(s=T.ENGAGE_LABEL, el=element(last, T.ENGAGE_LABEL), x0=lx, x1=lx + lw)]
for k, key in enumerate(I.KEYS):
    cx, _cy = T.slot_c(k)
    fits.append(dict(s=T.NAMES[key], el=element(first, T.NAMES[key]),
                     x0=cx - T.SLOT_W / 2, x1=cx + T.SLOT_W / 2))
for q, (x, y, w, h) in zip(T.QUALITIES, T.pill_rects()):
    fits.append(dict(s=q, el=element(last, q), x0=x + 6, x1=x + w - 6))

print(json.dumps(dict(
    style=G.S.name, slides=list(G.slides()), span=G.section_span("toolkit"),
    total=T.TOTAL, fps=T.FPS, max_seconds=T.MAX_SECONDS,
    gif=G.section_gif("toolkit"),
    via_section_frame=G.section_frame(9, "toolkit") == T.toolkit_svg(9),
    first_states=states(first), first_blocks=blocks(first),
    n_keys=len(I.KEYS), first_step=list(T.STEPS[0][0]),
    steps=steps, before_first=before_first, trips=trips, between=between,
    exact=exact, last_states=states(last),
    paths={f: paths(d) for f, d in docs.items()}, paths_last=paths(last),
    converge_at=T.CONVERGE_AT, all_at=T.ALL_AT,
    out_before_in=out_before_in, engage_before_in=engage_before_in,
    fan_before_portal=fan_before_portal, in_before_spokes=in_before_spokes,
    faint=faint, faint_ok=all(last_op[n] < 0.6 for n in faint),
    n_sources=len(L.SOURCES),
    last_links=last_links, into=list(T.INTO_STAC), outs=[n for n, _w in T.OUT_OF_STAC],
    engage_grey=engage_grey,
    trunk_end_on_stac=(trunk[-1][0] == sx + sw and sy < trunk[-1][1] < sy + sh),
    stubs_from_community=all(p[0][1] == cy0 and cx0 < p[0][0] < cx0 + cw for p in stubs),
    label_in_gap=(ly >= L.BOX_PORTAL[1] + L.BOX_PORTAL[3] and ly + lh <= cy0),
    stac_halo_last=('<g class="link"' in last),
    notes=[f for f, d in docs.items() if has(d, "no automated data path")],
    tray_last=('class="tray"' in last),
    qualities=[has(last, q) for q in T.QUALITIES],
    headings=[I.heading(b) in last for b in G.BLOCKS],
    fits=fits, canvas=(L.W, L.H), leaks=dict(first=leaks(first), last=leaks(last)),
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
class ToolkitCase(unittest.TestCase):
    style = "sketch"

    @classmethod
    def setUpClass(cls):
        cls.P = probe(cls.style)

    def test_it_is_a_new_slide_that_plays_once_within_30_seconds(self):
        P = self.P
        self.assertEqual(P["style"], self.style)
        self.assertIn("toolkit", P["slides"])
        self.assertIn("infra", P["slides"], "it must not replace the infra slide")
        self.assertEqual(P["span"], [0, P["total"] - 1])
        self.assertTrue(P["via_section_frame"])
        self.assertLessEqual(P["total"], P["max_seconds"] * P["fps"])
        self.assertEqual(P["gif"], [-1, 256, "full"])

    def test_it_opens_on_the_toolkit_alone(self):
        P = self.P
        self.assertEqual(P["first_blocks"], [])
        self.assertEqual(len(P["first_states"]), P["n_keys"], "one of each in the tray")
        self.assertEqual(set(P["first_states"].values()), {"tray"})

    def test_sections_arrive_in_order_and_stay(self):
        P = self.P
        self.assertEqual(P["first_step"], ["integration", "funded"])
        self.assertEqual(P["before_first"], [])
        for st in P["steps"]:
            self.assertEqual(st["got"], st["want"])

    def test_every_piece_moves_down_out_of_the_tray_on_its_beat(self):
        for t in self.P["trips"]:
            self.assertEqual((t["before"], t["mid"], t["after"]),
                             ("tray", "flying", "placed"), t["name"])

    def test_github_is_reused_its_tray_copy_stays_until_its_last_trip(self):
        self.assertEqual(self.P["between"].get("github/0"), "placed")
        self.assertEqual(self.P["between"].get("github/1"), "tray")

    def test_each_piece_lands_exactly_where_the_diagram_draws_it(self):
        self.assertEqual(self.P["exact"], {k: True for k in self.P["exact"]})

    def test_no_path_and_no_note_is_drawn_until_everything_is_in_place(self):
        for f, p in self.P["paths"].items():
            self.assertLess(int(f), self.P["all_at"])
            self.assertEqual(p, dict(flow=0, packets=0, markers=0, push=False),
                             "frame %s draws a path" % f)
        # ...and at the end the connections are drawn: lines only, nothing
        # travelling along them, and no "Push data"
        p = self.P["paths_last"]
        self.assertGreater(p["flow"], 0)
        self.assertEqual((p["packets"], p["push"]), (0, False))

    def test_everything_converges_on_stac_before_anything_leaves_it(self):
        P = self.P
        self.assertEqual(P["out_before_in"], [], "a leg out of STAC drew before the legs in")
        self.assertEqual(P["engage_before_in"], [])
        for n in P["into"] + P["outs"] + ["engagement"]:
            self.assertEqual(P["last_links"].get(n), 1.0, "%s never finished drawing" % n)

    def test_the_sources_spokes_and_the_portal_fan_are_there_faintly(self):
        P = self.P
        self.assertEqual(P["in_before_spokes"], [], "a leg into STAC drew before the spokes met")
        self.assertEqual(P["fan_before_portal"], [], "the Portal fan drew before its leg landed")
        self.assertEqual(len(P["faint"]), P["n_sources"] + 1 + 1 + 4, "spokes, hub, push, fan")
        self.assertIn("push", P["faint"], "Funded Projects -> Disasters bucket")
        self.assertTrue(P["faint_ok"], "spokes and fan should be faint, not at full weight")
        for n in P["faint"]:
            self.assertEqual(P["last_links"].get(n), 1.0, "%s never finished drawing" % n)

    def test_community_is_linked_to_stac_as_engagement_not_data(self):
        P = self.P
        self.assertTrue(P["stubs_from_community"], "the stubs do not rise from the block")
        self.assertTrue(P["trunk_end_on_stac"], "the trunk does not end on STAC's edge")
        self.assertGreater(P["engage_grey"], 0, "Community's link should be grey, not flow green")
        self.assertTrue(P["label_in_gap"], "the label must sit between Portal Content and Community")
        self.assertEqual(self.P["notes"], [])

    def test_it_ends_assembled_under_what_it_adds_up_to(self):
        P = self.P
        self.assertEqual(set(P["last_states"].values()), {"placed"})
        self.assertFalse(P["tray_last"], "the tray is still up at the end")
        self.assertEqual(P["qualities"], [True] * 3)
        self.assertEqual(P["headings"], [True] * 6)

    @sup.needs_rsvg
    @sup.needs_magick
    def test_every_word_fits_as_rendered(self):
        cw, ch = self.P["canvas"]
        for fit in self.P["fits"]:
            self.assertIsNotNone(fit["el"], "%r is not drawn" % fit["s"])
            x0, x1 = sup.ink_extent(fit["el"], cw, ch)
            self.assertGreaterEqual(x0, fit["x0"], "%r starts outside" % fit["s"])
            self.assertLessEqual(x1, fit["x1"], "%r runs out" % fit["s"])

    def test_no_flat_primitive_leaks_into_sketch(self):
        if self.style == "sketch":
            self.assertEqual(self.P["leaks"], dict(first=0, last=0))


class TestToolkitFlat(ToolkitCase):
    style = "flat"


if __name__ == "__main__":
    unittest.main()
