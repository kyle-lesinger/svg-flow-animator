"""
Frame SVGs -> PNGs -> GIF or APNG.

Two external binaries, both doing what they are best at:

  rsvg-convert (librsvg)  static SVG rasterisation. Fast enough to render a
                          300-frame 1600x900 sequence in a few seconds.
  ffmpeg                  palettegen/paletteuse. Produces a visibly better GIF
                          than ImageMagick's quantiser at the same size. Also
                          the APNG encoder, which needs no palette at all.

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
import re
import shutil
import struct
import subprocess

__all__ = ["stage_assets", "render_frames", "build_gif", "probe_gif",
           "build_apng", "probe_apng", "export"]


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


def build_apng(frame_dir, out_path, fps=15, width=1280, height=720,
               frame_glob="f%04d.png", plays=0):
    """
    Assemble the PNG sequence into an animated PNG (APNG).

    Full colour, so there is no palette and no dithering: the paper tone, the
    hachure fills and every anti-aliased edge arrive exactly as rsvg-convert
    drew them. Software that does not know APNG shows the first frame as an
    ordinary PNG, so frame 0 should be a complete picture.

    RGBA even though every frame is opaque: with an alpha channel the encoder
    can store a frame as only the pixels that changed, the rest transparent
    over the previous one. Measured on a 335-frame diagram, rgb24 came to
    25.7 MB and rgba to 10.4 MB; `-pred mixed` took another 5% off.

    `plays=0` loops forever. ffmpeg's own default is 1 -- play once and stop --
    which is easy to miss, because it only shows once the animation ends.
    """
    if shutil.which("ffmpeg") is None:
        raise RuntimeError("ffmpeg not found (brew install ffmpeg)")
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
           "-framerate", str(fps), "-i", os.path.join(frame_dir, frame_glob),
           "-vf", f"scale={width}:{height}:flags=lanczos", "-pix_fmt", "rgba",
           "-pred", "mixed", "-plays", str(plays), "-f", "apng", out_path]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError("ffmpeg failed:\n" + proc.stderr[:2000])
    return out_path


def probe_apng(path):
    """
    Frame count, size and loop count, read straight from the PNG chunks.

    acTL is the animation's own header; the fcTL chunks (one per frame) are
    counted as well, so a header that disagrees with its frames is caught
    rather than believed. A PNG with no acTL is a still and raises.
    """
    with open(path, "rb") as fh:
        data = fh.read()
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError(f"{path}: not a PNG")
    info, fctl, pos = {}, 0, 8
    while pos + 8 <= len(data):
        length, kind = struct.unpack(">I4s", data[pos:pos + 8])
        body = data[pos + 8:pos + 8 + length]
        if kind == b"IHDR":
            info["width"], info["height"] = struct.unpack(">II", body[:8])
        elif kind == b"acTL":
            info["frames"], info["plays"] = struct.unpack(">II", body[:8])
        elif kind == b"fcTL":
            fctl += 1
        elif kind == b"IEND":
            break
        pos += 12 + length                       # length, type, data, crc
    if "frames" not in info:
        raise ValueError(f"{path}: no acTL chunk -- a still PNG, not an animation")
    if fctl != info["frames"]:
        raise ValueError(f"{path}: acTL declares {info['frames']} frames, "
                         f"but {fctl} are present")
    info["bytes"] = len(data)
    return info


def export(frame_svg, total, size, out_base, frame_dir, background="white",
           fps=15):
    """
    Both artefacts of an animated chart, from one frame function:

        <out_base>.apng   frames 0 .. total-1, looping
        <out_base>.png    the finished picture, frame_svg(None), at 2x

    frame_svg(f) returns a whole SVG document. `size` is the output in pixels;
    the SVG is scaled to it while rasterising, so it stays sharp at any size.
    `frame_dir` is scratch. Returns probe_apng() of the animation.
    """
    os.makedirs(frame_dir, exist_ok=True)
    for stale in os.listdir(frame_dir):
        # f*.svg / f*.png only: staged assets may live here too (GOTCHAS).
        if re.fullmatch(r"f\d{4}\.(svg|png)", stale):
            os.remove(os.path.join(frame_dir, stale))
    for f in range(total):
        with open(os.path.join(frame_dir, f"f{f:04d}.svg"), "w") as fh:
            fh.write(frame_svg(f))
    render_frames(frame_dir, size[0], size[1], background=background)
    os.makedirs(os.path.dirname(os.path.abspath(out_base)), exist_ok=True)
    info = probe_apng(build_apng(frame_dir, out_base + ".apng", fps=fps,
                                 width=size[0], height=size[1]))
    if info["frames"] != total:
        raise RuntimeError(f"{out_base}.apng has {info['frames']} frames, "
                           f"expected {total}")

    # Inside frame_dir, not a temp dir: librsvg will not reach sprites from
    # anywhere else (GOTCHAS).
    still = os.path.join(frame_dir, "_still.svg")
    with open(still, "w") as fh:
        fh.write(frame_svg(None))
    try:
        proc = subprocess.run(["rsvg-convert", "-w", str(2 * size[0]),
                               "-h", str(2 * size[1]), "-b", background,
                               "-o", out_base + ".png", still],
                              capture_output=True, text=True)
    finally:
        os.remove(still)
    if proc.returncode != 0:
        raise RuntimeError("rsvg-convert failed:\n" + proc.stderr[:2000])
    return info
