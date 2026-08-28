"""
render: asset staging and the rasterisation guards.

docs/GOTCHAS.md leads with librsvg's resource containment -- it refuses to load
an `<image href>` resolving outside the referencing document's own directory,
silently, with exit code 0. `stage_assets()` exists to mirror sprites below the
frame directory so hrefs resolve at all.
"""
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

from svg_flow_animator import render  # noqa: E402


class StagingCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="sfa-render-")
        self.assets = os.path.join(self.tmp, "assets")
        self.frames = os.path.join(self.tmp, "frames")
        os.makedirs(self.assets)
        os.makedirs(self.frames)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def write_asset(self, name, data):
        p = os.path.join(self.assets, name)
        with open(p, "wb") as fh:
            fh.write(data)
        return p

    def staged(self, name):
        with open(os.path.join(self.frames, "assets", name), "rb") as fh:
            return fh.read()


class TestStageAssets(StagingCase):
    def test_mirrors_files_below_the_frame_directory(self):
        # librsvg resolves hrefs against the SVG's own directory, so the copy
        # has to land INSIDE frames/, not beside it.
        self.write_asset("logo.png", sup.png_bytes(4, 4))
        dst = render.stage_assets(self.assets, self.frames)
        self.assertEqual(dst, os.path.join(self.frames, "assets"))
        self.assertTrue(dst.startswith(self.frames + os.sep))
        self.assertTrue(os.path.exists(os.path.join(dst, "logo.png")))

    def test_copies_content_byte_exact(self):
        payload = sup.png_bytes(9, 5)
        self.write_asset("logo.png", payload)
        render.stage_assets(self.assets, self.frames)
        self.assertEqual(self.staged("logo.png"), payload)

    def test_honours_a_custom_subdirectory_name(self):
        self.write_asset("logo.png", b"x")
        dst = render.stage_assets(self.assets, self.frames, name="sprites")
        self.assertEqual(dst, os.path.join(self.frames, "sprites"))

    def test_skips_subdirectories(self):
        os.makedirs(os.path.join(self.assets, "nested"))
        self.write_asset("logo.png", b"x")
        dst = render.stage_assets(self.assets, self.frames)
        self.assertEqual(sorted(os.listdir(dst)), ["logo.png"])

    def test_is_idempotent(self):
        self.write_asset("logo.png", b"x")
        first = render.stage_assets(self.assets, self.frames)
        second = render.stage_assets(self.assets, self.frames)
        self.assertEqual(first, second)
        self.assertEqual(self.staged("logo.png"), b"x")

    def test_empty_asset_directory_still_creates_the_staging_root(self):
        dst = render.stage_assets(self.assets, self.frames)
        self.assertTrue(os.path.isdir(dst))

    def test_sprites_land_in_a_subdirectory_so_a_naive_cleanup_cannot_eat_them(self):
        # "Cleanup must delete frames/f*.svg and frames/f*.png, NOT frames/*,
        # or it takes the staged assets with it." Staging into a nested
        # directory is what makes the wrong cleanup fail loudly (a directory
        # is not removable with os.remove) rather than quietly deleting the
        # artwork and rendering a complete-looking picture with no logos.
        self.write_asset("logo.png", sup.png_bytes(4, 4))
        render.stage_assets(self.assets, self.frames)
        entry = os.path.join(self.frames, "assets")
        self.assertTrue(os.path.isdir(entry))
        with self.assertRaises(OSError):
            os.remove(entry)

    def test_notices_a_changed_file(self):
        self.write_asset("logo.png", b"OLD")
        render.stage_assets(self.assets, self.frames)
        p = self.write_asset("logo.png", b"NEW-AND-LONGER")
        os.utime(p, None)                       # a normal edit: mtime moves forward
        render.stage_assets(self.assets, self.frames)
        self.assertEqual(self.staged("logo.png"), b"NEW-AND-LONGER")

    def test_mtime_preserving_copy_does_not_serve_stale_artwork(self):
        """
        REGRESSION. This was a real bug; `stage_assets` now compares size.

        docs/GOTCHAS.md, "Copying assets by mtime silently serves stale
        artwork":

            `if os.path.getmtime(src) > os.path.getmtime(dst)` looks reasonable
            and is wrong. Anything that preserves timestamps -- cp -p, rsync -t,
            tar -x, restoring a backup, a build cache -- leaves the destination
            looking current. You replace a logo, rebuild, see the old logo, and
            conclude your edit did not save.
            Compare size or content, or just copy unconditionally.

        `render.stage_assets` guarded its copy with exactly that mtime
        comparison until this was fixed. This test replaces
        the source with different content while preserving an older timestamp
        -- what `tar -x` or a restored backup does -- and the staged copy is
        not refreshed.
        """
        self.write_asset("logo.png", b"OLD-CONTENT")
        render.stage_assets(self.assets, self.frames)

        src = self.write_asset("logo.png", b"NEW-CONTENT-ENTIRELY-DIFFERENT")
        staged_stat = os.stat(os.path.join(self.frames, "assets", "logo.png"))
        os.utime(src, (staged_stat.st_atime - 100, staged_stat.st_mtime - 100))

        render.stage_assets(self.assets, self.frames)
        self.assertEqual(self.staged("logo.png"), b"NEW-CONTENT-ENTIRELY-DIFFERENT")


class TestMissingBinaries(StagingCase):
    """Both entry points must name the tool and the brew formula, not crash."""

    def run_without_path(self, fn):
        saved = os.environ.get("PATH", "")
        os.environ["PATH"] = os.path.join(self.tmp, "empty-bin")
        try:
            with self.assertRaises(RuntimeError) as cm:
                fn()
            return str(cm.exception)
        finally:
            os.environ["PATH"] = saved

    def test_render_frames_reports_missing_rsvg_convert(self):
        msg = self.run_without_path(
            lambda: render.render_frames(self.frames, 100, 100))
        self.assertIn("rsvg-convert", msg)
        self.assertIn("librsvg", msg)

    def test_build_gif_reports_missing_ffmpeg(self):
        msg = self.run_without_path(
            lambda: render.build_gif(self.frames, os.path.join(self.tmp, "o.gif")))
        self.assertIn("ffmpeg", msg)


@sup.needs_rsvg
class TestRenderFramesGuards(StagingCase):
    def test_an_empty_frame_directory_is_an_error_not_a_silent_no_op(self):
        with self.assertRaises(RuntimeError) as cm:
            render.render_frames(self.frames, 100, 100)
        self.assertIn("no frame SVGs", str(cm.exception))


if __name__ == "__main__":
    unittest.main()
