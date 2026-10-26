"""
The live-preview server (svg_flow_animator.serve).

The load-bearing promise: /render is a PREVIEW. It must never touch the
project's overrides.json, or dragging a handle in the editor would silently
overwrite saved work. Only /save writes.

A throwaway project with a tiny scene module stands in for an example, so
nothing here needs artwork -- only rsvg-convert.
"""
import base64
import json
import os
import shutil
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

try:
    from . import _support as sup
except ImportError:
    import _support as sup

from svg_flow_animator import serve  # noqa: E402

# Records what it was handed, so the test can see the request arrive intact.
SCENE = r'''
import json, os
def preview_svg(path):
    with open(os.environ["FLOWGIF_OVERRIDES"]) as fh:
        seen = json.load(fh)
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, "seen.json"), "w") as fh:
        json.dump(dict(overrides=seen, style=os.environ["FLOWGIF_STYLE"],
                       svg_dir=os.path.dirname(path)), fh)
    if seen.get("explode"):
        raise RuntimeError("scene blew up on purpose")
    with open(path, "w") as fh:
        fh.write('<svg xmlns="http://www.w3.org/2000/svg" width="40" height="30">'
                 '<rect width="40" height="30" fill="#c33"/></svg>')
    print("progress chatter that is not the colour")
    return "#fdfcf8"
'''

SAVED = '{"node.hub": [1, 2]}\n'


@sup.needs_rsvg
class TestServe(unittest.TestCase):
    min_png = 0

    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="sfa-serve-")
        with open(os.path.join(self.dir, "scene_mod.py"), "w") as fh:
            fh.write(SCENE)
        self.saved = os.path.join(self.dir, "overrides.json")
        with open(self.saved, "w") as fh:
            fh.write(SAVED)
        base = serve.make_handler(self.dir, "scene_mod", (40, 30), self.min_png)

        class Quiet(base):
            def log_message(self, *a):
                pass

        self.srv = ThreadingHTTPServer(("127.0.0.1", 0), Quiet)
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()
        self.base = "http://127.0.0.1:%d" % self.srv.server_address[1]

    def tearDown(self):
        self.srv.shutdown()
        self.srv.server_close()
        shutil.rmtree(self.dir)

    def post(self, path, body):
        raw = body if isinstance(body, bytes) else json.dumps(body).encode()
        req = urllib.request.Request(self.base + path, data=raw, method="POST",
                                     headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.status, json.loads(r.read())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read())

    def seen(self):
        with open(os.path.join(self.dir, "seen.json")) as fh:
            return json.load(fh)


class TestRender(TestServe):
    def test_returns_a_png_and_the_scene_background(self):
        code, j = self.post("/render", {"overrides": {}, "style": "sketch"})
        self.assertEqual(code, 200, j)
        self.assertTrue(base64.b64decode(j["png"]).startswith(b"\x89PNG"))
        # The LAST stdout line is the colour; earlier chatter must not win.
        self.assertEqual(j["bg"], "#fdfcf8")

    def test_is_side_effect_free(self):
        self.post("/render", {"overrides": {"node.hub": [99, 99]}, "style": "flat"})
        with open(self.saved) as fh:
            self.assertEqual(fh.read(), SAVED,
                             "/render rewrote overrides.json -- a preview destroyed saved work")

    def test_hands_the_candidate_overrides_and_style_to_the_scene(self):
        self.post("/render", {"overrides": {"node.hub": [5, 6]}, "style": "sketch"})
        seen = self.seen()
        self.assertEqual(seen["overrides"], {"node.hub": [5, 6]})
        self.assertEqual(seen["style"], "sketch")

    def test_an_unknown_style_falls_back_to_flat(self):
        self.post("/render", {"overrides": {}, "style": "<script>"})
        self.assertEqual(self.seen()["style"], "flat")

    def test_scene_is_written_inside_the_project(self):
        # GOTCHAS: librsvg will not load an <image> outside the SVG's own
        # directory, so a scene rendered from tempdir loses every sprite.
        self.post("/render", {"overrides": {}, "style": "flat"})
        self.assertEqual(os.path.realpath(self.seen()["svg_dir"]),
                         os.path.realpath(self.dir))

    def test_leaves_no_scratch_files_behind(self):
        self.post("/render", {"overrides": {}, "style": "flat"})
        left = [f for f in os.listdir(self.dir) if f.startswith("_preview_")]
        self.assertEqual(left, [])

    def test_a_failing_scene_is_reported_not_swallowed(self):
        code, j = self.post("/render", {"overrides": {"explode": 1}, "style": "flat"})
        self.assertEqual(code, 500)
        self.assertIn("scene blew up on purpose", j["error"])


class TestImplausibleRender(TestServe):
    min_png = 10 ** 9

    def test_a_suspiciously_small_png_is_an_error(self):
        code, j = self.post("/render", {"overrides": {}, "style": "flat"})
        self.assertEqual(code, 500)
        self.assertIn("render looks wrong", j["error"])


class TestSaveAndValidation(TestServe):
    def test_save_writes_sorted_json(self):
        code, j = self.post("/save", {"overrides": {"b": [1, 2], "a": 3}})
        self.assertEqual(code, 200, j)
        self.assertEqual(j["count"], 2)
        with open(self.saved) as fh:
            text = fh.read()
        self.assertEqual(json.loads(text), {"a": 3, "b": [1, 2]})
        self.assertLess(text.index('"a"'), text.index('"b"'))

    def test_unreadable_body_is_400(self):
        code, _j = self.post("/render", b"{not json")
        self.assertEqual(code, 400)

    def test_overrides_must_be_an_object(self):
        code, _j = self.post("/save", {"overrides": [1, 2]})
        self.assertEqual(code, 400)
        with open(self.saved) as fh:
            self.assertEqual(fh.read(), SAVED)

    def test_unknown_endpoint_is_404(self):
        code, _j = self.post("/nope", {"overrides": {}})
        self.assertEqual(code, 404)


if __name__ == "__main__":
    unittest.main()
