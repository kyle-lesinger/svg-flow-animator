"""
Wording the disasters slides must never put on screen.

"COG" is out: the work uses many cloud-optimized formats, and naming one says
every file becomes that one. The slides say "cloud-optimized" instead. Checked
in rendered frames -- every slide, start, middle and end -- because a label is
only wrong once it is drawn; a constant or a comment saying COG is fine.
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
import gen_frames as G

found = {}
for key, (_label, render, total) in G.slides().items():
    for f in sorted({0, total // 4, total // 2, 3 * total // 4, total - 1}):
        for t in re.findall(r">([^<>]*)</text>", render(f)):
            if re.search(r"\bCOGs?\b", t):
                found.setdefault(key, []).append((f, t))
print(json.dumps(dict(slides=list(G.slides()), found=found)))
'''


@sup.needs_disasters_assets
@sup.needs_magick
@unittest.skipUnless(os.path.exists(TEXTURE), "Blue Marble texture absent")
class TestWording(unittest.TestCase):

    def test_no_slide_says_cog(self):
        here = sup.DISASTERS_DIR
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
            fh.write("{}")
        try:
            env = dict(os.environ, FLOWGIF_OVERRIDES=fh.name)
            out = subprocess.run([sys.executable, "-c", PROBE % dict(here=here)],
                                 env=env, cwd=here, capture_output=True, text=True)
        finally:
            os.remove(fh.name)
        if out.returncode != 0:
            raise AssertionError(out.stderr[-2000:])
        p = json.loads(out.stdout)
        self.assertGreaterEqual(len(p["slides"]), 4)
        self.assertEqual(p["found"], {}, "say 'cloud-optimized', not COG")


if __name__ == "__main__":
    unittest.main()
