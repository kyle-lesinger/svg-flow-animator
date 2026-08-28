"""
Generated-editor guards. READ-ONLY: nothing here modifies svg_flow_animator/editor.py.

Two documented silent failures live in this file's blast radius:

  * "Escapes passed through two levels of Python string parsing" -- a `\\n`
    written in a NON-raw template becomes a real newline inside a JS string
    literal, which is an unterminated literal, which takes the whole script
    down. There is no Python-side error: the editor simply renders blank with
    one message in a console nobody opened. Hence: the template must be a raw
    string, and generated JS gets `node --check` before it is believed.

  * "getElementById + CSS.escape never matches" -- `CSS.escape('box.stac')`
    is correct for a selector but ids match LITERALLY, so every dotted key
    silently stopped tracking.
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

from svg_flow_animator import editor, overrides as ov  # noqa: E402


HANDLES = {
    # Dotted keys throughout: they are what the CSS.escape bug ate.
    "box.stac": dict(kind="rect", default=(660, 350, 280, 200),
                     value=(660, 350, 280, 200), label="STAC"),
    "flow.ingest_to_stac": dict(kind="path", default=[(500, 450), (660, 450)],
                                value=[(500, 450), (580, 428), (660, 450)],
                                label="Ingest -> STAC"),
    "node.hub": dict(kind="point", default=(318, 450), value=(320, 455),
                     label="hub", size_key="node.hub.size"),
    "node.hub.size": dict(kind="scalar", default=11.0, value=14.0,
                          label="hub dot size"),
    "label.hub": dict(kind="point", default=(318, 480), value=(318, 480),
                      label="hub caption"),
    "node.orphan": dict(kind="point", default=(1, 2), value=(1, 2),
                        label="no size key", size_key="does.not.exist"),
}


def unterminated_quote(line):
    """The quote character a line ends inside, or None. Comments stripped first."""
    i, n = 0, len(line)
    while i < n:
        c = line[i]
        if c == "\\":
            i += 2
            continue
        if c in "'\"":
            quote, i = c, i + 1
            while i < n and line[i] != quote:
                i += 2 if line[i] == "\\" else 1
            if i >= n:
                return quote
        i += 1
    return None


class TestTemplateIsRaw(unittest.TestCase):
    """The escaping guard, asserted on the module source and on the value."""

    def source(self):
        with open(editor.__file__, encoding="utf-8") as fh:
            return fh.read()

    def test_html_is_assigned_from_a_raw_string_literal(self):
        self.assertRegex(
            self.source(), r'(?m)^HTML\s*=\s*r("""|\'\'\'|"|\')',
            "editor.HTML must be a RAW string. A non-raw template turns every "
            "backslash escape into its expanded character one level too early, "
            "and a real newline inside a JS string literal breaks the script "
            "with no Python-side error.")

    def test_backslash_escapes_survived_into_the_template(self):
        # The load-bearing consequence: two characters, not one newline.
        self.assertIn("\\n", editor.HTML,
                      "the template lost its backslash escapes -- it is not raw")

    def test_no_javascript_string_literal_spans_a_line(self):
        # An unterminated single-quoted literal is exactly what the double
        # un-escaping produced, and it is invisible until the browser runs it.
        # A cheap check that still works on a machine with no `node`.
        for script in sup.extract_scripts(editor.HTML):
            for i, line in enumerate(sup.strip_comments(script).splitlines(), 1):
                self.assertIsNone(
                    unterminated_quote(line),
                    "a string literal is left open at the end of script line "
                    "%d: %r" % (i, line[:110]))


class TestKnownJsPitfalls(unittest.TestCase):
    def test_does_not_look_handles_up_by_escaped_id(self):
        # Comments stripped: the template explains this bug next to its fix.
        self.assertNotIn("CSS.escape", sup.strip_comments(editor.HTML),
                         "getElementById matches ids LITERALLY, so CSS.escape's "
                         "backslashes mean a dotted key never resolves")

    def test_keeps_a_map_from_key_to_element(self):
        self.assertIn("new Map(", editor.HTML)

    def test_the_canvas_has_a_ground_colour_in_css(self):
        # An element with a background IMAGE but no background COLOUR shows the
        # dark page through it wherever the image fails to install, which reads
        # as "the editor came up black". Setting it only from the code that
        # installs the image means it is never set on the path where that code
        # does not run -- so it has to be in the stylesheet.
        css = sup.strip_comments(editor.HTML).split("<style>", 1)[-1] \
                                             .split("</style>", 1)[0]
        self.assertIn("background-color", css,
                      "the backdrop container must set its ground colour in "
                      "CSS, not only from the code that installs a backdrop")

    def test_an_unknown_view_fails_loudly(self):
        # A view switcher that returns quietly on an unknown key leaves the
        # canvas blank with nothing said anywhere.
        self.assertIn("console.error", editor.HTML)


class TestLayerOf(unittest.TestCase):
    def test_kind_drives_the_layer(self):
        self.assertEqual(editor.layer_of("box.stac", "rect"), "boxes")
        self.assertEqual(editor.layer_of("flow.a", "path"), "flows")
        self.assertEqual(editor.layer_of("node.hub", "point"), "nodes")

    def test_scalars_get_no_canvas_layer(self):
        self.assertEqual(editor.layer_of("node.hub.size", "scalar"), "")

    def test_label_prefix_splits_text_out_of_nodes(self):
        self.assertEqual(editor.layer_of("label.hub", "point"), "labels")
        self.assertEqual(editor.layer_of("label.hub", "point", label_prefix=""),
                         "nodes")
        self.assertEqual(editor.layer_of("caption.hub", "point",
                                         label_prefix="caption."), "labels")

    def test_every_layer_is_declared_in_the_draw_order(self):
        produced = {editor.layer_of(k, h["kind"]) for k, h in HANDLES.items()}
        for layer in produced - {""}:
            self.assertIn(layer, editor.LAYER_ORDER)


class TestPayload(unittest.TestCase):
    def test_is_json_serialisable(self):
        json.dumps(editor.payload(HANDLES))

    def test_carries_kind_label_value_default_and_layer(self):
        p = editor.payload(HANDLES)
        entry = p["node.hub"]
        self.assertEqual(entry["kind"], "point")
        self.assertEqual(entry["label"], "hub")
        self.assertEqual(entry["value"], [320.0, 455.0])
        self.assertEqual(entry["default"], [318.0, 450.0])
        self.assertEqual(entry["layer"], "nodes")

    def test_paths_stay_nested(self):
        self.assertEqual(editor.payload(HANDLES)["flow.ingest_to_stac"]["value"],
                         [[500.0, 450.0], [580.0, 428.0], [660.0, 450.0]])

    def test_scalars_are_plain_numbers(self):
        entry = editor.payload(HANDLES)["node.hub.size"]
        self.assertEqual(entry["value"], 14.0)
        self.assertNotIsInstance(entry["value"], list)

    def test_size_key_is_dropped_when_it_names_nothing(self):
        # A resize grip bound to a missing scalar would throw on first drag.
        p = editor.payload(HANDLES)
        self.assertEqual(p["node.hub"]["size_key"], "node.hub.size")
        self.assertNotIn("size_key", p["node.orphan"])

    def test_defaults_to_the_live_registry(self):
        saved = dict(ov.HANDLES)
        try:
            ov.HANDLES.clear()
            ov.point("only.one", (1, 2))
            self.assertEqual(list(editor.payload()), ["only.one"])
        finally:
            ov.HANDLES.clear()
            ov.HANDLES.update(saved)


class EditorBuildCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="sfa-editor-")

    def tearDown(self):
        for root, _dirs, files in os.walk(self.tmp, topdown=False):
            for f in files:
                os.remove(os.path.join(root, f))
            os.rmdir(root)

    def build(self, backdrop=None, handles=None, **kw):
        out = os.path.join(self.tmp, "editor.html")
        # PNG bytes rather than an SVG string: no rsvg-convert needed, and the
        # rasterisation path is covered separately.
        backdrop = backdrop or sup.png_bytes(8, 6)
        path = editor.build(out, (960, 540), backdrop,
                            handles=HANDLES if handles is None else handles, **kw)
        with open(path, encoding="utf-8") as fh:
            return path, fh.read()


class TestBuild(EditorBuildCase):
    def test_writes_the_file_and_returns_its_absolute_path(self):
        path, html = self.build()
        self.assertTrue(os.path.isabs(path))
        self.assertTrue(os.path.exists(path))
        self.assertTrue(html.lstrip().startswith("<!doctype html>"))

    def test_every_placeholder_is_substituted(self):
        _path, html = self.build(title="minimal demo")
        for token in ("__HANDLES__", "__LAYERS__", "__BACKDROPS__", "__VIEWS__",
                      "__TITLE__", "__W__", "__H__"):
            self.assertNotIn(token, html, "%s never got replaced" % token)
        self.assertIn("minimal demo", html)

    def test_the_handle_registry_reaches_the_page_verbatim(self):
        # Asserted as "the exact JSON blob is present" rather than by parsing
        # the script, so it does not depend on the template's variable names.
        _path, html = self.build()
        self.assertIn(json.dumps(editor.payload(HANDLES)),
                      sup.extract_scripts(html)[0])

    def test_single_backdrop_offers_no_view_switcher(self):
        _path, html = self.build()
        script = sup.extract_scripts(html)[0]
        self.assertIn(json.dumps([]), script)
        self.assertNotIn(json.dumps(["view"]), script,
                         "the internal single-view name leaked into the switcher")

    def test_named_backdrops_become_switchable_views(self):
        _path, html = self.build(backdrop={"Flat": sup.png_bytes(4, 4),
                                           "Hand-drawn": sup.png_bytes(4, 4)})
        script = sup.extract_scripts(html)[0]
        self.assertIn(json.dumps(["Flat", "Hand-drawn"]), script)
        for name in ("Flat", "Hand-drawn"):
            self.assertIn(json.dumps(name), script)

    def test_layers_are_only_the_ones_in_use(self):
        _path, html = self.build(handles={
            "node.hub": dict(kind="point", default=(1, 2), value=(1, 2), label="h")})
        self.assertIn(json.dumps(["nodes"]), sup.extract_scripts(html)[0])

    def test_backdrop_may_be_a_callback_returning_its_own_background(self):
        # The backdrop is a CALLBACK so it is generated after overrides load,
        # which is what makes it agree with the handles drawn on top of it.
        calls = []

        def source():
            calls.append(1)
            return (sup.png_bytes(4, 4), "#fdfcf8")

        _path, html = self.build(backdrop=source)
        self.assertEqual(len(calls), 1)
        self.assertIn('"bg": "#fdfcf8"', html)


@sup.needs_node
class TestGeneratedJavaScript(EditorBuildCase):
    """
    `node --check` on the emitted script.

    A template escaping bug once shipped a completely broken script with no
    Python-side error at all, so CLAUDE.md makes this check mandatory for
    generated JS. examples/minimal/edit.sh runs it on every build.
    """

    def check(self, html, tag):
        scripts = sup.extract_scripts(html)
        self.assertEqual(len(scripts), 1, "expected exactly one <script> block")
        js = os.path.join(self.tmp, "%s.js" % tag)
        with open(js, "w", encoding="utf-8") as fh:
            fh.write(scripts[0])
        proc = subprocess.run(["node", "--check", js], capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0,
                         "generated JS does not parse:\n" + proc.stderr[:3000])

    def test_synthetic_registry(self):
        _path, html = self.build(title="syntax check")
        self.check(html, "synthetic")

    def test_a_title_containing_quotes_does_not_break_the_script(self):
        _path, html = self.build(title="it's \"quoted\" & <angled>")
        self.check(html, "quoted")

    def test_empty_registry(self):
        _path, html = self.build(handles={})
        self.check(html, "empty")

    def test_the_real_minimal_demo_registry(self):
        # The minimal demo is the smoke test: self-contained, no artwork, and
        # it exercises every handle kind the editor knows about.
        saved = (dict(ov.HANDLES), ov.PATH, dict(ov._data), ov._loaded_from)
        try:
            sys.path.insert(0, sup.MINIMAL_DIR)
            import demo                                       # noqa: F401
            demo.warm_up()                                    # ov.path registers lazily
            self.assertGreater(len(ov.HANDLES), 10)
            self.assertIn("flow.spoke.0", ov.HANDLES, "warm_up did not run")
            _path, html = self.build(handles=dict(ov.HANDLES),
                                     title="minimal demo")
            self.check(html, "minimal")
        finally:
            if sup.MINIMAL_DIR in sys.path:
                sys.path.remove(sup.MINIMAL_DIR)
            ov.HANDLES.clear()
            ov.HANDLES.update(saved[0])
            ov.PATH, ov._data, ov._loaded_from = saved[1], saved[2], saved[3]


class TestMinimalSceneNeedsNoArtwork(unittest.TestCase):
    def test_the_minimal_demo_references_no_sprites(self):
        # librsvg only loads resources at or below the SVG's own directory, so
        # a scene that references sprites cannot be rasterised from a temp dir.
        # The minimal demo draws everything from primitives, which is what
        # makes it safe for the tests above (and for a fresh clone).
        saved = (dict(ov.HANDLES), ov.PATH, dict(ov._data), ov._loaded_from)
        try:
            sys.path.insert(0, sup.MINIMAL_DIR)
            import demo
            self.assertNotIn("<image", demo.static_scene())
            self.assertNotIn("<image", demo.frame(130))
        finally:
            if sup.MINIMAL_DIR in sys.path:
                sys.path.remove(sup.MINIMAL_DIR)
            ov.HANDLES.clear()
            ov.HANDLES.update(saved[0])
            ov.PATH, ov._data, ov._loaded_from = saved[1], saved[2], saved[3]


if __name__ == "__main__":
    unittest.main()
