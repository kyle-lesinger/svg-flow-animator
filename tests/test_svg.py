"""
svg / styles emitters: well-formedness, escaping, and the `fill="transparent"` ban.

Frames are built by string concatenation, so nothing validates them on the way
out -- a malformed attribute produces a file rsvg-convert renders as a blank
frame with exit code 0. Every emitter here is parsed with ElementTree.

docs/GOTCHAS.md: `fill="none"` is not hit-testable, `fill="transparent"` is --
it is a fully transparent PAINT and it swallows clicks. A 550x640 container
rect with a transparent fill intercepted every click aimed at the nodes inside
it, and nothing errored.
"""
import ast
import os
import sys
import unittest
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

try:
    from . import _support as sup
except ImportError:
    import _support as sup

from svg_flow_animator import styles, svg  # noqa: E402

SVGNS = "{http://www.w3.org/2000/svg}"


def all_emitter_output():
    """One sample from every public emitter, plus both style backends."""
    out = {
        "text": svg.text(10, 20, "hello"),
        "text_escaped": svg.text(1, 2, 'a & b < c > d "e" <script>x</script>'),
        "image": svg.image("assets/logo.png", 1, 2, 30, 40),
        "image_slice": svg.image("assets/logo.png", 1, 2, 30, 40,
                                 preserve="xMidYMid slice"),
        "rect": svg.rect(1, 2, 30, 40),
        "rect_full": svg.rect(1, 2, 30, 40, fill="#fff", stroke="#000", rx=6,
                              dash="4 3", opacity=0.5),
        "circle": svg.circle(5, 6, 7),
        "circle_stroked": svg.circle(5, 6, 7, stroke="#f00", sw=1.5, opacity=0.2),
        "path": svg.path("M 0,0 L 10,10"),
        "path_full": svg.path("M 0,0 L 10,10", stroke="#0f0", sw=3, dash="13 15",
                              dashoffset=-12.5, marker_end="arrow_0", opacity=0.9),
        "group": svg.group("<rect x='1' y='1' width='2' height='2'/>", opacity=0.4,
                           transform="translate(3,4)"),
        "marker_defs": svg.marker_defs("#0f0", "#f80"),
        "glow": svg.glow(10, 20, 100, 50, "#1a6ae0"),
    }
    for name, st in (("flat", styles.FLAT), ("sketch", styles.SKETCH)):
        out["%s.box" % name] = st.box(10, 20, 300, 200, "#c9f2d2", key="box.t")
        out["%s.box_none" % name] = st.box(10, 20, 300, 200, "none", key="box.n")
        out["%s.circle" % name] = st.circle(50, 50, 20, fill="#fff", stroke="#000",
                                            key="c.t")
        out["%s.ellipse" % name] = st.ellipse(50, 50, 30, 20, fill="#eee", key="e.t")
        out["%s.poly" % name] = st.poly([(0, 0), (10, 10), (20, 0)], "#000",
                                        key="p.t")
        out["%s.text" % name] = st.text(1, 2, "label & more")
        out["%s.img" % name] = st.img("assets/a.png", 1, 2, 200, 200)
    return out


class TestWellFormed(unittest.TestCase):
    def test_every_emitter_parses(self):
        for name, markup in all_emitter_output().items():
            with self.subTest(emitter=name):
                sup.parse_fragment(markup)          # raises ParseError if broken

    def test_document_is_a_complete_svg(self):
        doc = svg.document(960, 540, svg.rect(1, 2, 3, 4), background="#fff")
        root = ET.fromstring(doc)
        self.assertEqual(root.tag, SVGNS + "svg")
        self.assertEqual(root.get("viewBox"), "0 0 960 540")
        self.assertEqual(root.get("width"), "960")
        self.assertEqual(root.get("height"), "540")

    def test_document_without_a_background_has_no_backing_rect(self):
        root = ET.fromstring(svg.document(10, 10, ""))
        self.assertEqual(len(list(root)), 0)
        root = ET.fromstring(svg.document(10, 10, "", background="#abc"))
        self.assertEqual(root[0].get("fill"), "#abc")

    def test_xlink_namespace_is_declared(self):
        # Some exports reference sprites through xlink:href; the document must
        # carry the declaration or the frame will not parse at all.
        self.assertIn('xmlns:xlink=', svg.document(10, 10, ""))


class TestEscaping(unittest.TestCase):
    def test_esc_handles_the_markup_characters(self):
        self.assertEqual(svg.esc("a & b < c > d"), "a &amp; b &lt; c &gt; d")

    def test_esc_is_ampersand_first(self):
        # "&lt;" must not become "&amp;lt;" -- ordering bugs here double-escape.
        self.assertEqual(svg.esc("<"), "&lt;")
        self.assertEqual(svg.esc("&lt;"), "&amp;lt;")

    def test_esc_accepts_non_strings(self):
        self.assertEqual(svg.esc(42), "42")
        self.assertEqual(svg.esc(4.5), "4.5")

    def test_text_content_survives_a_round_trip(self):
        raw = "Ingest & <Catalog> > 3"
        root = sup.parse_fragment(svg.text(0, 0, raw))
        self.assertEqual(root[0].text, raw)

    def test_style_backends_escape_too(self):
        for st in (styles.FLAT, styles.SKETCH):
            root = sup.parse_fragment(st.text(0, 0, "a & <b>"))
            self.assertEqual(root[0].text, "a & <b>")


class TestOpacityAttribute(unittest.TestCase):
    def test_omitted_when_fully_opaque(self):
        self.assertNotIn("opacity", svg.rect(0, 0, 1, 1, opacity=1.0))
        self.assertNotIn("opacity", svg.rect(0, 0, 1, 1, opacity=None))
        self.assertNotIn("opacity", svg.rect(0, 0, 1, 1, opacity=2.0))

    def test_present_when_partial(self):
        self.assertIn('opacity="0.400"', svg.rect(0, 0, 1, 1, opacity=0.4))

    def test_zero_opacity_is_emitted(self):
        self.assertIn('opacity="0.000"', svg.circle(0, 0, 1, opacity=0.0))


class TestNoTransparentFill(unittest.TestCase):
    """
    `fill="transparent"` receives pointer events; `fill="none"` does not.

    Guarded at two levels: the rendered output of every emitter, and the
    package source itself (so the editor's CSS cannot reintroduce it either).
    """

    def test_no_emitter_produces_it(self):
        for name, markup in all_emitter_output().items():
            with self.subTest(emitter=name):
                self.assertNotIn("transparent", markup)

    def test_defaults_are_fill_none(self):
        for markup in (svg.rect(0, 0, 1, 1), svg.circle(0, 0, 1),
                       svg.path("M 0,0 L 1,1")):
            self.assertIn('fill="none"', markup)

    def test_no_package_source_writes_a_transparent_fill(self):
        # Scans what the modules can EMIT -- string literals with docstrings
        # and CSS/JS comments removed, so the warnings written next to these
        # fixes do not read as relapses.
        needles = ('fill="transparent"', "fill='transparent'", "fill:transparent",
                   "fill: transparent")
        for path, lit in sup.package_emitted_literals():
            for needle in needles:
                self.assertNotIn(needle, lit,
                                 "%s emits %s -- it captures pointer events; "
                                 "use fill:none plus a fat transparent stroke "
                                 "with pointer-events:stroke"
                                 % (os.path.basename(path), needle))

    def test_container_handles_are_grabbed_by_their_border(self):
        # The concrete shape of the fix in the editor's stylesheet: a container
        # is fill:none, and its grab band is a stroke.
        from svg_flow_animator import editor
        self.assertIn("pointer-events:stroke", editor.HTML)


class TestGlow(unittest.TestCase):
    def test_silent_below_the_threshold(self):
        self.assertEqual(svg.glow(0, 0, 10, 10, "#fff", strength=0.0), "")
        self.assertEqual(svg.glow(0, 0, 10, 10, "#fff", strength=0.005), "")

    def test_one_rect_per_ring(self):
        root = sup.parse_fragment(svg.glow(10, 20, 100, 50, "#1a6ae0"))
        self.assertEqual(len(list(root)), 3)
        for el in root:
            self.assertEqual(el.get("fill"), "none")
            self.assertEqual(el.get("stroke"), "#1a6ae0")

    def test_rings_are_concentric_and_grow_outward(self):
        root = sup.parse_fragment(svg.glow(10, 20, 100, 50, "#1a6ae0"))
        widths = [float(el.get("width")) for el in root]
        self.assertEqual(widths, sorted(widths, reverse=True))
        for el in root:
            cx = float(el.get("x")) + float(el.get("width")) / 2
            cy = float(el.get("y")) + float(el.get("height")) / 2
            self.assertAlmostEqual(cx, 60.0)
            self.assertAlmostEqual(cy, 45.0)

    def test_no_gaussian_blur_is_ever_emitted(self):
        # librsvg's blur support is poor; a filter-based glow renders as
        # nothing at all. Concentric strokes are the supported approach.
        for path, lit in sup.package_emitted_literals():
            self.assertNotIn("feGaussianBlur", lit, os.path.basename(path))


class TestMarkerDefs(unittest.TestCase):
    def test_one_marker_per_colour_with_predictable_ids(self):
        root = sup.parse_fragment(svg.marker_defs("#0f0", "#f80"))
        markers = root[0].findall(SVGNS + "marker")
        self.assertEqual([m.get("id") for m in markers], ["arrow_0", "arrow_1"])
        self.assertEqual([m[0].get("fill") for m in markers], ["#0f0", "#f80"])

    def test_prefix_is_honoured(self):
        root = sup.parse_fragment(svg.marker_defs("#000", prefix="head"))
        self.assertEqual(root[0][0].get("id"), "head_0")

    def test_no_colours_is_an_empty_defs(self):
        root = sup.parse_fragment(svg.marker_defs())
        self.assertEqual(len(list(root[0])), 0)


class TestFontStacks(unittest.TestCase):
    def test_no_stack_ends_in_cursive(self):
        # `cursive` resolves to Zapfino on macOS -- unreadable at diagram sizes.
        for name, st in (("flat", styles.FLAT), ("sketch", styles.SKETCH)):
            with self.subTest(style=name):
                self.assertFalse(st.font.strip().endswith("cursive"), st.font)
                self.assertTrue(st.font.strip().endswith("sans-serif")
                                or st.font.strip().endswith("serif"), st.font)
        self.assertTrue(svg.DEFAULT_FONT.strip().endswith("sans-serif"))

    def test_no_emitted_font_stack_falls_back_to_cursive(self):
        for path, lit in sup.package_emitted_literals():
            for stack in lit.split(";"):
                if "font" in stack and "cursive" in stack:
                    self.fail("%s emits a font stack ending in cursive "
                              "(Zapfino on macOS): %r"
                              % (os.path.basename(path), stack.strip()[:120]))


class TestSketchLeaks(unittest.TestCase):
    """
    A roughjs outline cannot be filled, so sketch mode legitimately emits
    unstroked <rect>/<ellipse> underneath its sketchy edges. A leak check must
    therefore look for STROKED flat primitives only.
    """

    def stroked_flat_primitives(self, markup):
        root = sup.parse_fragment(markup)
        return [el for el in root.iter()
                if el.tag in (SVGNS + "rect", SVGNS + "ellipse")
                and el.get("stroke") not in (None, "none")]

    def test_sketch_box_has_no_stroked_flat_rect(self):
        out = styles.SketchStyle().box(10, 20, 300, 200, "#c9f2d2", key="box.leak")
        self.assertEqual(self.stroked_flat_primitives(out), [])

    def test_sketch_box_may_carry_an_unstroked_fill_rect(self):
        out = styles.SketchStyle().box(10, 20, 300, 200, "#c9f2d2", key="box.fill")
        self.assertIn("<path", out)

    def test_flat_box_does_use_a_stroked_rect(self):
        out = styles.FLAT.box(10, 20, 300, 200, "#c9f2d2")
        self.assertEqual(len(self.stroked_flat_primitives(out)), 1)


class TestSourceHygiene(unittest.TestCase):
    def test_every_package_module_parses(self):
        for path, text in sup.package_sources():
            ast.parse(text, filename=path)

    def test_package_exports_what_it_advertises(self):
        import svg_flow_animator as pkg
        for name in pkg.__all__:
            self.assertTrue(hasattr(pkg, name), name)

    def test_module_dunder_all_names_all_exist(self):
        import svg_flow_animator as pkg
        for name in pkg.__all__:
            mod = getattr(pkg, name)
            for exported in getattr(mod, "__all__", []):
                self.assertTrue(hasattr(mod, exported),
                                "%s.__all__ names missing %s" % (name, exported))


if __name__ == "__main__":
    unittest.main()
