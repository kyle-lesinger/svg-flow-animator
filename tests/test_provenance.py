"""
provenance: the comment embedded in a finished GIF / PNG / APNG.

docs/GOTCHAS.md: ffmpeg accepts `-metadata comment=...` for GIF, PNG and APNG
and writes nothing, silently. So the comment is written by hand from the file
formats' own specifications, and every assertion here is about what is IN the
file afterwards -- read back by this module, and, where ImageMagick is on the
PATH, by a second implementation that did not write it.
"""
import ast
import os
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
import zlib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

try:
    from . import _support as sup
except ImportError:
    import _support as sup

from svg_flow_animator import provenance as pv  # noqa: E402

# The smallest valid GIF89a: 1x1, a two-entry global colour table, one frame
# behind a Graphic Control Extension. 43 bytes, the classic tracking pixel.
TINY_GIF = bytes.fromhex(
    "474946383961" "0100 0100" "80 00 00" "000000 ffffff"
    "21f9 04 01 0000 00 00" "2c 0000 0000 0100 0100 00" "02 02 44 01 00" "3b")

TEXT = "SI-assisted media (NASA NID 1383.155). A human-directed diagram."


def _tmp(suffix, data):
    fd, path = tempfile.mkstemp(suffix=suffix)
    with os.fdopen(fd, "wb") as fh:
        fh.write(data)
    return path


def _magick_comment(path):
    fmt = "%c" if path.endswith(".gif") else "%[comment]"
    out = subprocess.run(["magick", "identify", "-format", fmt + "\n", path],
                         capture_output=True, text=True, check=True).stdout
    return out.split("\n")[0]


class GifCase(unittest.TestCase):
    def setUp(self):
        self.path = _tmp(".gif", TINY_GIF)
        self.addCleanup(os.remove, self.path)

    def test_round_trip_and_structure(self):
        pv.stamp(self.path, TEXT)
        self.assertEqual(pv.read(self.path), [TEXT])
        with open(self.path, "rb") as fh:
            blob = fh.read()
        self.assertTrue(blob.startswith(b"GIF89a"))
        self.assertTrue(blob.endswith(b"\x3b"), "trailer must survive")
        # The comment sits right after the global colour table, and the
        # Graphic Control Extension is still glued to its image descriptor.
        self.assertEqual(blob[13 + 6:13 + 6 + 2], b"\x21\xfe")
        self.assertIn(b"\x21\xf9\x04\x01\x00\x00\x00\x00\x2c", blob)
        self.assertEqual(len(blob), len(TINY_GIF) + 2 + 1 + len(TEXT) + 1)

    def test_stamping_twice_leaves_one_comment(self):
        pv.stamp(self.path, "first")
        pv.stamp(self.path, TEXT)
        self.assertEqual(pv.read(self.path), [TEXT])
        with open(self.path, "rb") as fh:
            self.assertNotIn(b"first", fh.read())

    def test_long_text_spans_sub_blocks(self):
        long = TEXT + " " + "x" * 600          # 255-byte sub-blocks, three of them
        pv.stamp(self.path, long)
        self.assertEqual(pv.read(self.path), [long])

    def test_unstamped_reads_empty(self):
        self.assertEqual(pv.read(self.path), [])

    def test_gif87a_is_refused(self):
        with open(self.path, "wb") as fh:
            fh.write(b"GIF87a" + TINY_GIF[6:])
        with self.assertRaises(ValueError):
            pv.stamp(self.path, TEXT)

    @sup.needs_magick
    def test_imagemagick_reads_it_back(self):
        pv.stamp(self.path, TEXT)
        self.assertEqual(_magick_comment(self.path), TEXT)


class PngCase(unittest.TestCase):
    def setUp(self):
        self.path = _tmp(".png", sup.png_bytes(4, 3))
        self.addCleanup(os.remove, self.path)

    def _chunks(self):
        with open(self.path, "rb") as fh:
            blob = fh.read()
        out, p = [], 8
        while p < len(blob):
            n, = struct.unpack(">I", blob[p:p + 4])
            kind, data, crc = blob[p + 4:p + 8], blob[p + 8:p + 8 + n], blob[p + 8 + n:p + 12 + n]
            out.append((kind, data, crc))
            p += 12 + n
        return out

    def test_round_trip_and_structure(self):
        pv.stamp(self.path, TEXT)
        self.assertEqual(pv.read(self.path), [TEXT])
        chunks = self._chunks()
        self.assertEqual([c[0] for c in chunks[:2]], [b"IHDR", b"tEXt"])
        self.assertEqual(chunks[-1][0], b"IEND")
        kind, data, crc = chunks[1]
        self.assertEqual(data, b"Comment\x00" + TEXT.encode("latin-1"))
        self.assertEqual(crc, struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF))

    def test_stamping_twice_leaves_one_comment(self):
        pv.stamp(self.path, "first")
        pv.stamp(self.path, TEXT)
        self.assertEqual(pv.read(self.path), [TEXT])
        self.assertEqual(sum(1 for c in self._chunks() if c[0] == b"tEXt"), 1)

    def test_other_text_chunks_are_left_alone(self):
        # A tEXt with another keyword is somebody else's; only "Comment" is ours.
        body = b"Software\x00rsvg-convert"
        other = (struct.pack(">I", len(body)) + b"tEXt" + body
                 + struct.pack(">I", zlib.crc32(b"tEXt" + body) & 0xFFFFFFFF))
        with open(self.path, "rb") as fh:
            blob = fh.read()
        ihdr_end = 8 + 12 + 13
        with open(self.path, "wb") as fh:
            fh.write(blob[:ihdr_end] + other + blob[ihdr_end:])
        pv.stamp(self.path, TEXT)
        kinds = [c[0] for c in self._chunks()]
        self.assertEqual(kinds.count(b"tEXt"), 2)
        self.assertEqual(pv.read(self.path), [TEXT])

    @sup.needs_magick
    def test_imagemagick_reads_it_back(self):
        pv.stamp(self.path, TEXT)
        self.assertEqual(_magick_comment(self.path), TEXT)


class NotAnImageCase(unittest.TestCase):
    def test_refused(self):
        path = _tmp(".bin", b"hello")
        self.addCleanup(os.remove, path)
        with self.assertRaises(ValueError):
            pv.stamp(path, TEXT)
        with self.assertRaises(ValueError):
            pv.read(path)


@sup.needs_ffmpeg
class RealEncoderCase(unittest.TestCase):
    """Files ffmpeg actually wrote: a looping multi-frame GIF and an APNG."""

    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.dir)

    def _ffmpeg(self, *args):
        subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                        "-f", "lavfi", "-i", "color=c=red:s=16x16:d=0.6:r=5",
                        "-metadata", "comment=FFMPEG_WROTE_THIS", *args],
                       check=True)

    def test_ffmpeg_metadata_goes_nowhere(self):
        # The GOTCHAS entry. If this starts failing, ffmpeg learned to write
        # comments and stamp() may be redundant -- good news, revisit.
        gif, apng = os.path.join(self.dir, "a.gif"), os.path.join(self.dir, "a.apng")
        self._ffmpeg(gif)
        self._ffmpeg("-plays", "0", "-f", "apng", apng)
        for path in (gif, apng):
            with open(path, "rb") as fh:
                self.assertNotIn(b"FFMPEG_WROTE_THIS", fh.read(), path)
            self.assertEqual(pv.read(path), [])

    def test_looping_gif_keeps_its_loop_and_frames(self):
        gif = os.path.join(self.dir, "a.gif")
        self._ffmpeg("-loop", "0", gif)
        pv.stamp(gif, TEXT)
        self.assertEqual(pv.read(gif), [TEXT])
        with open(gif, "rb") as fh:
            self.assertIn(b"NETSCAPE2.0", fh.read())
        if sup.HAVE_MAGICK:
            out = subprocess.run(["magick", "identify", "-format", "%n\n", gif],
                                 capture_output=True, text=True, check=True).stdout
            self.assertEqual(out.split("\n")[0], "3")
            self.assertEqual(_magick_comment(gif), TEXT)

    def test_apng_round_trip(self):
        apng = os.path.join(self.dir, "a.apng")
        self._ffmpeg("-plays", "0", "-f", "apng", apng)
        pv.stamp(apng, TEXT)
        self.assertEqual(pv.read(apng), [TEXT])
        with open(apng, "rb") as fh:
            blob = fh.read()
        self.assertLess(blob.index(b"tEXt"), blob.index(b"acTL"),
                        "the comment goes right after IHDR, before acTL")
        if sup.HAVE_MAGICK:
            self.assertEqual(_magick_comment(apng), TEXT)


class DisastersWiringCase(unittest.TestCase):
    """The disasters build stamps every output, with wording in current terms."""

    GEN = os.path.join(sup.DISASTERS_DIR, "gen_frames.py")
    BUILD = os.path.join(sup.DISASTERS_DIR, "build.sh")

    @classmethod
    def provenance_text(cls):
        with open(cls.GEN, encoding="utf-8") as fh:
            tree = ast.parse(fh.read())
        for node in tree.body:
            if (isinstance(node, ast.Assign)
                    and any(getattr(t, "id", None) == "PROVENANCE" for t in node.targets)):
                return ast.literal_eval(node.value)
        raise AssertionError("PROVENANCE not found in gen_frames.py")

    def test_wording(self):
        text = self.provenance_text()
        self.assertTrue(text.isascii(), "GIF comments and PNG tEXt are Latin-1; keep it ASCII")
        self.assertIn("SI-assisted", text)
        self.assertIn("NID 1383.155", text)
        self.assertIn("large language model", text)
        # Executive Order 14434: current terminology only, no legacy acronym.
        self.assertIsNone(re.search(r"\bAI\b|AI-", text), text)

    def test_build_stamps_the_gif_and_the_poster(self):
        with open(self.BUILD, encoding="utf-8") as fh:
            build = fh.read()
        self.assertIn('"--stamp=$out"', build)
        self.assertIn('"--stamp=$OUT_PNG"', build)
        # ... and after the file is complete, not before ffmpeg has written it.
        self.assertLess(build.index("==> 4/4  verifying"), build.index('"--stamp=$out"'))

    @sup.needs_disasters_assets
    def test_stamp_flag_writes_and_reads_back(self):
        path = _tmp(".gif", TINY_GIF)
        self.addCleanup(os.remove, path)
        env = dict(os.environ, FLOWGIF_OVERRIDES=os.devnull)
        proc = subprocess.run([sys.executable, self.GEN, "--stamp=" + path],
                              capture_output=True, text=True, env=env, cwd=sup.DISASTERS_DIR)
        self.assertEqual(proc.returncode, 0, proc.stderr[-2000:])
        self.assertIn("provenance:", proc.stdout)
        self.assertEqual(pv.read(path), [self.provenance_text()])


if __name__ == "__main__":
    unittest.main()
