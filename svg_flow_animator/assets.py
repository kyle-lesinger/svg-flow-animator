"""
Harvest reusable artwork out of a flattened SVG export.

Design-tool exports (Lucidchart, Figma, Illustrator) bury real assets inside
one enormous file. Two things are worth pulling back out:

  * embedded rasters -- logos and screenshots sitting in <defs> as base64
    data URIs, recoverable byte-exact at their native resolution
  * vector marks -- brand logos drawn as paths, identifiable by fill colour

Both beat screenshotting a render: you get the original pixels, or real vector
you can rotate and scale.

Pure stdlib. Image dimensions are parsed from PNG/JPEG headers directly rather
than pulling in Pillow.
"""
import base64
import os
import re
import struct

__all__ = ["extract_rasters", "extract_paths_by_fill", "fill_histogram", "ink_bbox"]

_IMG_RE = re.compile(
    r'<image[^>]*id="([A-Za-z0-9_-]+)"[^>]*(?:xlink:)?href="data:image/'
    r'(png|jpeg|jpg|gif|webp);base64,([^"]+)"'
)


def _png_size(raw):
    return struct.unpack(">II", raw[16:24])


def _jpeg_size(raw):
    i = 2
    while i < len(raw) - 1:
        if raw[i] != 0xFF:
            i += 1
            continue
        marker = raw[i + 1]
        if marker in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7,
                      0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
            h, w = struct.unpack(">HH", raw[i + 5:i + 9])
            return w, h
        if marker in (0xD8, 0xD9) or 0xD0 <= marker <= 0xD7:
            i += 2
            continue
        i += 2 + struct.unpack(">H", raw[i + 2:i + 4])[0]
    return (0, 0)


def extract_rasters(svg_path, out_dir):
    """
    Write every embedded bitmap to `out_dir`, named by its element id.

    The declared width/height on the <image> element is meaningless in these
    exports -- typically a placeholder like 10x10 that a later <use> transform
    scales up. The real dimensions come from the payload, so we read them from
    the file header.

    Returns a list of dicts: id, path, format, width, height, bytes.
    """
    svg = open(svg_path, encoding="utf-8", errors="replace").read()
    os.makedirs(out_dir, exist_ok=True)

    found = []
    for m in _IMG_RE.finditer(svg):
        aid, fmt, b64 = m.group(1), m.group(2).lower(), m.group(3)
        raw = base64.b64decode(b64)
        if fmt == "png":
            w, h = _png_size(raw)
        elif fmt in ("jpeg", "jpg"):
            w, h = _jpeg_size(raw)
        else:
            w = h = 0
        ext = {"jpeg": "jpg"}.get(fmt, fmt)
        path = os.path.join(out_dir, f"{aid}.{ext}")
        with open(path, "wb") as fh:
            fh.write(raw)
        found.append(dict(id=aid, path=path, format=ext,
                          width=w, height=h, bytes=len(raw)))
    return found


def fill_histogram(svg_path):
    """Count of every literal `fill="#..."` -- the fastest way to find a logo."""
    svg = open(svg_path, encoding="utf-8", errors="replace").read()
    hits = {}
    for m in re.finditer(r'fill="(#[0-9a-fA-F]{3,8})"', svg):
        key = m.group(1).lower()
        hits[key] = hits.get(key, 0) + 1
    return dict(sorted(hits.items(), key=lambda kv: -kv[1]))


def extract_paths_by_fill(svg_path, fills):
    """
    Pull out the <path> elements whose fill matches any of `fills`.

    Useful for lifting a multi-colour vector mark (each blade/segment of the
    logo is one path with one brand colour) so it stays vector and can be
    rotated or recoloured, instead of being cropped out of a raster render.

    Returns the raw path element strings, in the order `fills` was given.
    """
    svg = open(svg_path, encoding="utf-8", errors="replace").read()
    out = []
    for c in fills:
        c = c.lower().lstrip("#")
        m = re.search(r'<path[^>]*fill="#%s"[^>]*/>' % re.escape(c), svg,
                      re.IGNORECASE)
        if m:
            out.append(m.group(0))
    return out


def ink_bbox(render_png, viewbox, rendered_px):
    """
    Convert an ImageMagick ink bbox back into user units.

    Getting a tight viewBox for extracted paths is otherwise guesswork: render
    them into a deliberately oversized window, ask ImageMagick where the ink
    actually is (`identify -format %@`), and map that back.

    render_png   the `%@` string, e.g. "504x504+4+4"
    viewbox      (x, y, w, h) the oversized window you rendered
    rendered_px  width in pixels you rendered it at
    returns      (x, y, w, h) in user units
    """
    m = re.match(r"(\d+)x(\d+)\+(\d+)\+(\d+)", render_png.strip())
    if not m:
        raise ValueError("unparseable ink bbox: %r" % render_png)
    pw, ph, px, py = (int(g) for g in m.groups())
    vx, vy, vw, _vh = viewbox
    scale = vw / float(rendered_px)
    return (vx + px * scale, vy + py * scale, pw * scale, ph * scale)
