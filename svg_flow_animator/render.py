"""
Frame SVGs -> PNGs -> GIF.

Two external binaries, both doing what they are best at:

  rsvg-convert (librsvg)  static SVG rasterisation. Fast enough to render a
                          300-frame 1600x900 sequence in a few seconds.
  ffmpeg                  palettegen/paletteuse. Produces a visibly better GIF
                          than ImageMagick's quantiser at the same size.

Two librsvg behaviours are load-bearing here and are handled for you:

  1. RESOURCE CONTAINMENT. librsvg refuses to load an <image href> that
     resolves outside the referencing document's own directory tree. A frame in
     `frames/` cannot reach `../assets/`. `stage_assets()` mirrors the sprite
     directory below the frame directory so hrefs resolve. This fails silently
     -- images simply do not draw -- so it is worth knowing about.
  2. WEAK FILTER SUPPORT. Do not reach for feGaussianBlur to make a glow.
     Stack a few concentric strokes at decreasing opacity instead.
"""
import os
import shutil
import subprocess

__all__ = ["stage_assets", "render_frames", "build_gif", "probe_gif"]


def stage_assets(asset_dir, frame_dir, name="assets"):
    """
    Mirror `asset_dir` to `<frame_dir>/<name>` so librsvg will load the sprites.

    Copies only what changed. Returns the staged directory, which is what your
    frame SVGs should reference in their href attributes.
    """
    dst_root = os.path.join(frame_dir, name)
    os.makedirs(dst_root, exist_ok=True)
    for entry in os.listdir(asset_dir):
        src = os.path.join(asset_dir, entry)
        if not os.path.isfile(src):
            continue
        dst = os.path.join(dst_root, entry)
        # Compare SIZE, not mtime. Anything that preserves timestamps -- cp -p,
        # rsync -t, tar -x, restoring a backup, a build cache -- leaves an mtime
        # check believing the copy is current. You replace a logo, rebuild, see
        # the old one, and conclude your edit did not save.
        if (not os.path.exists(dst)
                or os.path.getsize(src) != os.path.getsize(dst)):
            shutil.copy2(src, dst)
    return dst_root


def render_frames(frame_dir, width, height, background="white", jobs=None,
                  pattern="f*.svg"):
    """
    Rasterise every frame SVG in parallel. Returns (n_svg, n_png).

    Raises RuntimeError if any frame failed to produce a non-trivial PNG -- an
    empty frame becomes a black flash in the final GIF, which is easy to miss
    when scrubbing but obvious to a viewer.
    """
    if shutil.which("rsvg-convert") is None:
        raise RuntimeError("rsvg-convert not found (brew install librsvg)")
    jobs = jobs or (os.cpu_count() or 8)

    svgs = sorted(f for f in os.listdir(frame_dir) if f.endswith(".svg"))
    if not svgs:
        raise RuntimeError("no frame SVGs in %s" % frame_dir)

    script = (
        'rsvg-convert -w %d -h %d -b "%s" -o "${1%%.svg}.png" "$1"'
        % (width, height, background)
    )
    proc = subprocess.run(
        ["xargs", "-P", str(jobs), "-I", "{}", "sh", "-c", script, "_", "{}"],
        input="\n".join(os.path.join(frame_dir, s) for s in svgs),
        text=True, capture_output=True,
    )
    if proc.returncode != 0:
        raise RuntimeError("rsvg-convert failed:\n" + proc.stderr[:2000])

    pngs = [f for f in os.listdir(frame_dir) if f.endswith(".png")]
    if len(pngs) != len(svgs):
        raise RuntimeError("frame count mismatch: %d svg -> %d png"
                           % (len(svgs), len(pngs)))
    empty = [f for f in pngs
             if os.path.getsize(os.path.join(frame_dir, f)) < 1024]
    if empty:
        raise RuntimeError("frames rendered empty: %s" % ", ".join(sorted(empty)[:5]))
    return len(svgs), len(pngs)


def build_gif(frame_dir, out_path, fps=15, width=1280, height=720, colors=128,
              frame_glob="f%04d.png", loop=0):
    """
    Assemble the PNG sequence into a looping GIF.

    stats_mode=diff weights the palette toward the pixels that actually change
    between frames. For a mostly-static diagram with a few moving elements that
    spends the colour budget where it is visible instead of on the background.
    """
    if shutil.which("ffmpeg") is None:
        raise RuntimeError("ffmpeg not found (brew install ffmpeg)")
    vf = (f"scale={width}:{height}:flags=lanczos,split[a][b];"
          f"[a]palettegen=max_colors={colors}:stats_mode=diff[p];"
          f"[b][p]paletteuse=dither=bayer:bayer_scale=3:diff_mode=rectangle")
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
           "-framerate", str(fps), "-i", os.path.join(frame_dir, frame_glob),
           "-filter_complex", vf, "-loop", str(loop), out_path]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError("ffmpeg failed:\n" + proc.stderr[:2000])
    return out_path


def probe_gif(path):
    """Read back frame count / size / bytes, so a build can assert on them."""
    out = subprocess.run(
        ["magick", "identify", "-format", "%n %w %h\n", path],
        capture_output=True, text=True, check=True).stdout.strip().splitlines()[0]
    n, w, h = out.split()
    return dict(frames=int(n), width=int(w), height=int(h),
                bytes=os.path.getsize(path))
