"""
assets: image-header parsing and ink-bbox arithmetic.

The package parses PNG/JPEG dimensions from file headers rather than depending
on Pillow (docs/DECISIONS.md), so the header walk is hand-written code with no
library behind it -- exactly the kind of thing that returns a plausible wrong
number instead of raising.
"""
import base64
import os
import shutil
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

from svg_flow_animator import assets  # noqa: E402


class TestPngSize(unittest.TestCase):
    def test_reads_the_ihdr_dimensions(self):
        for w, h in [(1, 1), (7, 13), (640, 480), (1, 4096), (4096, 1)]:
            with self.subTest(size=(w, h)):
                self.assertEqual(assets._png_size(sup.png_bytes(w, h)), (w, h))

    def test_does_not_confuse_width_and_height(self):
        self.assertEqual(assets._png_size(sup.png_bytes(7, 13)), (7, 13))
        self.assertNotEqual(assets._png_size(sup.png_bytes(7, 13)), (13, 7))

    def test_only_the_header_is_consulted(self):
        # Trailing payload must not shift the answer.
        raw = sup.png_bytes(21, 34) + b"\x00" * 5000
        self.assertEqual(assets._png_size(raw), (21, 34))


class TestJpegSize(unittest.TestCase):
    def test_reads_sof0_after_skippable_segments(self):
        for w, h in [(1, 1), (11, 5), (1600, 900)]:
            with self.subTest(size=(w, h)):
                self.assertEqual(assets._jpeg_size(sup.jpeg_bytes(w, h)), (w, h))

    def test_walks_past_several_segments(self):
        raw = sup.jpeg_bytes(320, 200, extra_segments=4)
        self.assertEqual(assets._jpeg_size(raw), (320, 200))

    def test_progressive_sof2(self):
        self.assertEqual(assets._jpeg_size(sup.jpeg_bytes(64, 48, sof=0xC2)),
                         (64, 48))

    def test_other_sof_markers(self):
        for sof in (0xC1, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
            with self.subTest(sof=hex(sof)):
                self.assertEqual(assets._jpeg_size(sup.jpeg_bytes(30, 20, sof=sof)),
                                 (30, 20))

    def test_width_and_height_are_not_swapped(self):
        # SOF stores height FIRST; getting this backwards produces a picture
        # sized to the wrong aspect with no error anywhere.
        self.assertEqual(assets._jpeg_size(sup.jpeg_bytes(11, 5)), (11, 5))

    def test_garbage_returns_zero_rather_than_raising(self):
        self.assertEqual(assets._jpeg_size(b"\xff\xd8" + b"\x00" * 40), (0, 0))
        self.assertEqual(assets._jpeg_size(b"\xff\xd8"), (0, 0))
        self.assertEqual(assets._jpeg_size(b""), (0, 0))


class TestExtractRasters(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="sfa-assets-")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def write_svg(self, entries):
        parts = []
        for aid, mime, payload in entries:
            b64 = base64.b64encode(payload).decode()
            # The declared width/height in these exports is a placeholder; the
            # real size has to come from the payload header.
            parts.append('<image id="%s" width="10" height="10" '
                         'xlink:href="data:image/%s;base64,%s"/>'
                         % (aid, mime, b64))
        p = os.path.join(self.tmp, "export.svg")
        with open(p, "w") as fh:
            fh.write("<svg xmlns:xlink='x'>%s</svg>" % "".join(parts))
        return p

    def test_recovers_payloads_byte_exact(self):
        png = sup.png_bytes(7, 13)
        svg_path = self.write_svg([("logo", "png", png)])
        out = os.path.join(self.tmp, "out")
        found = assets.extract_rasters(svg_path, out)
        self.assertEqual(len(found), 1)
        with open(found[0]["path"], "rb") as fh:
            self.assertEqual(fh.read(), png)

    def test_dimensions_come_from_the_header_not_the_attributes(self):
        svg_path = self.write_svg([("logo", "png", sup.png_bytes(7, 13)),
                                   ("shot", "jpeg", sup.jpeg_bytes(320, 200))])
        found = {d["id"]: d for d in
                 assets.extract_rasters(svg_path, os.path.join(self.tmp, "out"))}
        self.assertEqual((found["logo"]["width"], found["logo"]["height"]), (7, 13))
        self.assertEqual((found["shot"]["width"], found["shot"]["height"]), (320, 200))

    def test_jpeg_extension_is_normalised(self):
        svg_path = self.write_svg([("shot", "jpeg", sup.jpeg_bytes(4, 4))])
        found = assets.extract_rasters(svg_path, os.path.join(self.tmp, "out"))
        self.assertEqual(found[0]["format"], "jpg")
        self.assertTrue(found[0]["path"].endswith("shot.jpg"))

    def test_byte_count_is_reported(self):
        png = sup.png_bytes(9, 9)
        svg_path = self.write_svg([("logo", "png", png)])
        found = assets.extract_rasters(svg_path, os.path.join(self.tmp, "out"))
        self.assertEqual(found[0]["bytes"], len(png))

    def test_no_images_is_an_empty_list_not_an_error(self):
        p = os.path.join(self.tmp, "plain.svg")
        with open(p, "w") as fh:
            fh.write("<svg><rect width='1' height='1'/></svg>")
        self.assertEqual(assets.extract_rasters(p, os.path.join(self.tmp, "o")), [])


class TestFillHistogram(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="sfa-fill-")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def svg(self, body):
        p = os.path.join(self.tmp, "a.svg")
        with open(p, "w") as fh:
            fh.write("<svg>%s</svg>" % body)
        return p

    def test_counts_and_orders_by_frequency(self):
        p = self.svg('<path fill="#FF0000"/><path fill="#ff0000"/>'
                     '<path fill="#00ff00"/>')
        hist = assets.fill_histogram(p)
        self.assertEqual(hist["#ff0000"], 2)
        self.assertEqual(hist["#00ff00"], 1)
        self.assertEqual(list(hist)[0], "#ff0000")

    def test_ignores_non_literal_fills(self):
        p = self.svg('<path fill="none"/><path fill="url(#g)"/><path fill="#abc"/>')
        self.assertEqual(assets.fill_histogram(p), {"#abc": 1})


class TestExtractPathsByFill(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="sfa-paths-")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def svg(self, body):
        p = os.path.join(self.tmp, "a.svg")
        with open(p, "w") as fh:
            fh.write("<svg>%s</svg>" % body)
        return p

    def test_returns_in_the_order_requested(self):
        p = self.svg('<path d="A" fill="#ff0000"/><path d="B" fill="#00ff00"/>')
        got = assets.extract_paths_by_fill(p, ["#00ff00", "#ff0000"])
        self.assertEqual(len(got), 2)
        self.assertIn('d="B"', got[0])
        self.assertIn('d="A"', got[1])

    def test_accepts_colours_with_or_without_a_hash_and_any_case(self):
        p = self.svg('<path d="A" fill="#Ff0000"/>')
        self.assertEqual(len(assets.extract_paths_by_fill(p, ["ff0000"])), 1)
        self.assertEqual(len(assets.extract_paths_by_fill(p, ["#FF0000"])), 1)

    def test_absent_colour_is_skipped(self):
        p = self.svg('<path d="A" fill="#ff0000"/>')
        self.assertEqual(assets.extract_paths_by_fill(p, ["#123456"]), [])


class TestInkBbox(unittest.TestCase):
    def test_unit_scale(self):
        self.assertEqual(assets.ink_bbox("504x504+4+4", (0, 0, 512, 512), 512),
                         (4.0, 4.0, 504.0, 504.0))

    def test_scales_pixels_back_into_user_units(self):
        # Rendered at 2x, so every pixel measurement halves.
        self.assertEqual(assets.ink_bbox("504x504+4+4", (0, 0, 512, 512), 1024),
                         (2.0, 2.0, 252.0, 252.0))

    def test_origin_offset_is_added(self):
        self.assertEqual(assets.ink_bbox("100x50+10+20", (30, 40, 200, 200), 200),
                         (40.0, 60.0, 100.0, 50.0))

    def test_scale_comes_from_the_viewbox_width(self):
        # A non-square window: the width ratio is the scale for both axes,
        # because rsvg renders the viewBox uniformly.
        got = assets.ink_bbox("40x20+0+0", (0, 0, 100, 50), 400)
        self.assertEqual(got, (0.0, 0.0, 10.0, 5.0))

    def test_tolerates_surrounding_whitespace(self):
        self.assertEqual(assets.ink_bbox("  504x504+4+4\n", (0, 0, 512, 512), 512),
                         (4.0, 4.0, 504.0, 504.0))

    def test_unparseable_raises_rather_than_guessing(self):
        for bad in ("", "nothing", "504x504", "504+4+4"):
            with self.subTest(value=bad):
                with self.assertRaises(ValueError):
                    assets.ink_bbox(bad, (0, 0, 512, 512), 512)


if __name__ == "__main__":
    unittest.main()
