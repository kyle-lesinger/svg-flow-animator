"""
SLOW / INTEGRATION -- the real pipeline, end to end.

Set SFA_SKIP_SLOW=1 to skip everything here. It also skips itself when
rsvg-convert / ffmpeg / magick are absent.

A handful of frames only: the minimal demo's full run is ~360 frames and this
suite is meant to stay fast. The frames are chosen from the MIDDLE of the
animation on purpose -- docs/GOTCHAS.md, "Guards that inspect the wrong frame
cannot fire": frame 0 is before any stage starts, so a check pointed at it sees
no animated content and passes forever.

Everything asserted here is a plausibility check, not an exit status. These
failures produce valid files that are wrong.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

try:
    from . import _support as sup
except ImportError:
    import _support as sup

from svg_flow_animator import overrides as ov, render  # noqa: E402

# Frames spanning two stages: mid-reveal, mid-hold, and a later beat. Every one
# of them carries a flow, a glow and a callout.
#
# The exact numbers matter. The packet dash pattern is "13 15" offset by
# frame*7, so its period is 4 frames: frames 4 apart after the reveal finishes
# rasterise to IDENTICAL pixels even though their SVGs differ. Picking a
# regular stride would make test_7 fail on frames that are working correctly.
SOURCE_FRAMES = [121, 123, 125, 128, 235, 238, 243, 251]
MIN_PLAUSIBLE_SVG = 2000
MIN_PLAUSIBLE_PNG = 4096
MIN_PLAUSIBLE_GIF = 10000


def load_demo():
    """Import the minimal demo, isolating the global override registry."""
    saved = (dict(ov.HANDLES), ov.PATH, dict(ov._data), ov._loaded_from)
    sys.path.insert(0, sup.MINIMAL_DIR)
    try:
        import demo
        return demo, saved
    except BaseException:
        restore(saved)
        raise


def restore(saved):
    if sup.MINIMAL_DIR in sys.path:
        sys.path.remove(sup.MINIMAL_DIR)
    ov.HANDLES.clear()
    ov.HANDLES.update(saved[0])
    ov.PATH, ov._data, ov._loaded_from = saved[1], saved[2], saved[3]


@sup.skip_if_slow_disabled
@sup.needs_rsvg
class TestFramePipeline(unittest.TestCase):
    """SVG frames -> PNGs -> GIF, asserted on plausibility."""

    @classmethod
    def setUpClass(cls):
        cls.demo, cls._saved = load_demo()
        cls.tmp = tempfile.mkdtemp(prefix="sfa-integration-")
        cls.frame_dir = os.path.join(cls.tmp, "frames")
        os.makedirs(cls.frame_dir)
        for i, f in enumerate(SOURCE_FRAMES):
            with open(os.path.join(cls.frame_dir, "f%04d.svg" % i), "w") as fh:
                fh.write(cls.demo.frame(f))

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)
        restore(cls._saved)

    def svgs(self):
        return sorted(f for f in os.listdir(self.frame_dir) if f.endswith(".svg"))

    def pngs(self):
        return sorted(f for f in os.listdir(self.frame_dir) if f.endswith(".png"))

    def size(self, name):
        return os.path.getsize(os.path.join(self.frame_dir, name))

    # --- 1. the frames themselves ------------------------------------------
    def test_1_every_frame_was_written_and_is_well_formed(self):
        self.assertEqual(len(self.svgs()), len(SOURCE_FRAMES))
        for name in self.svgs():
            with self.subTest(frame=name):
                with open(os.path.join(self.frame_dir, name)) as fh:
                    text = fh.read()
                self.assertGreater(len(text), MIN_PLAUSIBLE_SVG,
                                   "%s is suspiciously small" % name)
                ET.fromstring(text)

    def test_2_the_frames_actually_animate(self):
        # Identical frames would mean the stages never fired -- a GIF that
        # renders perfectly and shows nothing moving.
        bodies = set()
        for name in self.svgs():
            with open(os.path.join(self.frame_dir, name)) as fh:
                bodies.add(fh.read())
        self.assertEqual(len(bodies), len(SOURCE_FRAMES),
                         "some frames are byte-identical: nothing is moving")

    def test_3_the_frames_carry_the_animated_layers(self):
        with open(os.path.join(self.frame_dir, "f0002.svg")) as fh:
            mid = fh.read()
        self.assertIn("stroke-dasharray", mid, "no flow drawn in a mid-stage frame")
        self.assertIn("<text", mid, "no narration in a mid-stage frame")

    def test_4_no_frame_uses_a_pointer_capturing_transparent_fill(self):
        for name in self.svgs():
            with open(os.path.join(self.frame_dir, name)) as fh:
                self.assertNotIn('fill="transparent"', fh.read(), name)

    # --- 2. rasterisation ---------------------------------------------------
    def test_5_rasterises_one_png_per_frame(self):
        n_svg, n_png = render.render_frames(self.frame_dir, 960, 540,
                                            background=self.demo.S.bg)
        self.assertEqual((n_svg, n_png), (len(SOURCE_FRAMES), len(SOURCE_FRAMES)))
        self.assertEqual(len(self.pngs()), len(SOURCE_FRAMES))

    def test_6_every_png_is_a_plausible_picture(self):
        self.assertTrue(self.pngs(), "test_5 must run first")
        for name in self.pngs():
            with self.subTest(frame=name):
                self.assertGreater(self.size(name), MIN_PLAUSIBLE_PNG,
                                   "%s rendered to %d bytes -- a blank or "
                                   "near-blank frame" % (name, self.size(name)))

    def test_7_the_rendered_pngs_differ_from_each_other(self):
        # An empty frame becomes a black flash in the GIF; identical frames
        # mean the animation never reached the raster.
        digests = set()
        for name in self.pngs():
            with open(os.path.join(self.frame_dir, name), "rb") as fh:
                digests.add(fh.read())
        self.assertEqual(len(digests), len(SOURCE_FRAMES),
                         "rasterised frames are identical")

    # --- 3. assembly --------------------------------------------------------
    @sup.needs_ffmpeg
    def test_8_assembles_a_gif(self):
        self.assertTrue(self.pngs(), "test_5 must run first")
        out = os.path.join(self.tmp, "demo.gif")
        render.build_gif(self.frame_dir, out, fps=15, width=960, height=540,
                         colors=96)
        self.assertTrue(os.path.exists(out))
        self.assertGreater(os.path.getsize(out), MIN_PLAUSIBLE_GIF,
                           "the GIF is too small to contain this many frames")

    @sup.needs_ffmpeg
    @sup.needs_magick
    def test_9_the_gif_reads_back_with_the_expected_shape(self):
        out = os.path.join(self.tmp, "demo.gif")
        if not os.path.exists(out):
            self.skipTest("test_8 did not produce a GIF")
        info = render.probe_gif(out)
        self.assertEqual(info["frames"], len(SOURCE_FRAMES))
        self.assertEqual((info["width"], info["height"]), (960, 540))
        self.assertGreater(info["bytes"], MIN_PLAUSIBLE_GIF)


_FRAME_PROBE = r"""
import hashlib, json, os, sys
root, minimal, style, frame = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4])
sys.path.insert(0, root)
sys.path.insert(0, minimal)
os.environ["FLOWGIF_STYLE"] = style
import demo
body = demo.frame(frame)
print(json.dumps({"sha": hashlib.sha256(body.encode()).hexdigest(),
                  "len": len(body)}))
"""


@sup.skip_if_slow_disabled
class TestFrameReproducibility(unittest.TestCase):
    """
    A whole frame must be byte-identical between processes, in both styles.

    This is the end-to-end form of the determinism gotcha: if any seed were
    salted per process, the sketch frames would differ between runs and the
    diagram would boil. No external binaries needed.
    """

    def probe(self, style, frame, hashseed):
        env = dict(os.environ, PYTHONHASHSEED=hashseed, FLOWGIF_STYLE=style)
        proc = subprocess.run(
            [sys.executable, "-c", _FRAME_PROBE, ROOT, sup.MINIMAL_DIR,
             style, str(frame)],
            env=env, capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr[-2000:])
        return json.loads(proc.stdout)

    def test_flat_frames_are_reproducible(self):
        a = self.probe("flat", 130, "0")
        b = self.probe("flat", 130, "1")
        self.assertEqual(a, b)

    def test_sketch_frames_are_reproducible(self):
        # The one that actually depends on seeding: sketch geometry is jittered.
        a = self.probe("sketch", 130, "0")
        b = self.probe("sketch", 130, "1")
        self.assertEqual(a, b)
        self.assertGreater(a["len"], MIN_PLAUSIBLE_SVG)

    def test_the_two_styles_really_do_differ(self):
        # Otherwise the test above would pass on an accidental no-op.
        flat = self.probe("flat", 130, "0")
        sketch = self.probe("sketch", 130, "0")
        self.assertNotEqual(flat["sha"], sketch["sha"])


@sup.needs_disasters_assets
class TestDisastersExample(unittest.TestCase):
    """
    The real diagram, which needs gitignored third-party artwork.

    Skipped on a fresh clone. Present or not, the frame generator must at least
    stage its sprites BELOW the frame directory -- librsvg will not reach them
    otherwise, and the render succeeds with every logo missing.
    """

    def test_assets_are_staged_below_the_frame_directory(self):
        tmp = tempfile.mkdtemp(prefix="sfa-disasters-")
        try:
            frames = os.path.join(tmp, "frames")
            os.makedirs(frames)
            dst = render.stage_assets(sup.DISASTERS_ASSETS, frames)
            self.assertTrue(dst.startswith(frames + os.sep))
            self.assertTrue(os.listdir(dst), "no sprites staged")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
