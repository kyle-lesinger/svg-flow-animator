"""
The disasters example writes frames in parallel, so every frame must be a pure
function of f (docs/GOTCHAS.md: frames are written in parallel).

Runs in a subprocess, like the other example tests: importing the example
registers its handles in the global overrides module. Frames go to a temp dir,
never the real frames/. Needs the gitignored artwork -- the journey's globe is
rendered from the Blue Marble texture.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

try:
    from . import _support as sup
except ImportError:
    import _support as sup

PROBE = r'''
import json, os, sys
sys.path.insert(0, %(here)r)
import gen_frames as G, layout as L
L.FRAMES, L.FRAME_ASSETS = %(dir)r, os.path.join(%(dir)r, "assets")

out = dict(sections={})
for name in ("journey", "egis"):
    a, b = G.section_span(name)
    span = (a, min(b, a + 150))
    G.write_frames(span=span, render=lambda f: G.section_frame(f, name))
    seq = [G.section_frame(f, name) for f in range(span[0], span[1] + 1)]
    got = [open(os.path.join(L.FRAMES, "f%%04d.svg" %% i), encoding="utf-8").read()
           for i in range(len(seq))]
    out["sections"][name] = dict(
        n=len(seq), differ=[i for i in range(len(seq)) if got[i] != seq[i]][:5])
out["globes"] = sorted(n for n in os.listdir(L.FRAME_ASSETS) if n.startswith("globe_"))
out["temps"] = [n for n in os.listdir(L.FRAME_ASSETS) if ".tmp" in n]
print(json.dumps(out))
'''


@sup.needs_disasters_assets
class ParallelFramesCase(unittest.TestCase):
    style = "sketch"

    @classmethod
    def setUpClass(cls):
        cls.dir = tempfile.mkdtemp(prefix="sfa-frames-")
        fd, ov = tempfile.mkstemp(suffix=".json")
        with os.fdopen(fd, "w") as fh:
            fh.write("{}")
        try:
            env = dict(os.environ, FLOWGIF_STYLE=cls.style, FLOWGIF_OVERRIDES=ov)
            run = subprocess.run(
                [sys.executable, "-c",
                 PROBE % dict(here=sup.DISASTERS_DIR, dir=cls.dir)],
                env=env, cwd=sup.DISASTERS_DIR, capture_output=True, text=True)
        finally:
            os.remove(ov)
        if run.returncode != 0:
            shutil.rmtree(cls.dir, ignore_errors=True)
            raise AssertionError(run.stderr[-2000:])
        cls.P = json.loads(run.stdout)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.dir, ignore_errors=True)

    def test_parallel_frames_match_sequential_ones(self):
        for name, s in self.P["sections"].items():
            self.assertGreater(s["n"], 100)
            self.assertEqual(s["differ"], [],
                             "%s: these frames differ when written in parallel "
                             "-- one depends on more than f" % name)

    def test_workers_leave_no_temp_files(self):
        # The journey renders its globe from scratch here, inside the workers;
        # a shared temp name lets two of them interleave into a corrupt PNG.
        self.assertTrue(self.P["globes"], "no globe rendered: the check is blind")
        self.assertEqual(self.P["temps"], [])


class ParallelFramesFlat(ParallelFramesCase):
    style = "flat"


if __name__ == "__main__":
    unittest.main()
