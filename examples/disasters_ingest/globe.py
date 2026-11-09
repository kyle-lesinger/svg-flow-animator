#!/usr/bin/env python3
"""
An orthographic globe for the journey slide: projection, orbits, swaths, and
the textured Earth itself -- all stdlib.

The Earth is a raster (NASA Blue Marble) projected ONCE into a PNG and cached
below frames/, because librsvg will only load an image at or below the frame's
own directory. Everything that moves -- orbit rings, the satellite, its beam and
the swath it paints -- is vector, projected here and drawn by gen_frames.

The Earth does not rotate during a pass: at slide timescales a pass is seconds
and the picture reads better still. Successive passes ARE shifted west, which
is what Earth's rotation does to a sun-synchronous ground track between orbits.

Decoding the JPEG is the one step that shells out (to ImageMagick); the
projection and the PNG encoder are plain Python, per docs/DECISIONS.md.
"""
import math
import os
import struct
import subprocess
import zlib


# ----------------------------------------------------------------- vectors ---
def dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0])


def norm(v):
    n = math.sqrt(dot(v, v)) or 1.0
    return (v[0] / n, v[1] / n, v[2] / n)


def comb(a, ka, b, kb):
    """ka*a + kb*b."""
    return (a[0] * ka + b[0] * kb, a[1] * ka + b[1] * kb, a[2] * ka + b[2] * kb)


def from_latlon(lat, lon):
    """Unit vector, ECEF (z = north), degrees in."""
    la, lo = math.radians(lat), math.radians(lon)
    return (math.cos(la) * math.cos(lo), math.cos(la) * math.sin(lo), math.sin(la))


def to_latlon(p):
    return (math.degrees(math.asin(max(-1.0, min(1.0, p[2])))),
            math.degrees(math.atan2(p[1], p[0])))


def rotate_z(v, deg):
    """Rotate about the polar axis -- how a ground track moves between orbits."""
    a = math.radians(deg)
    c, s = math.cos(a), math.sin(a)
    return (v[0] * c - v[1] * s, v[0] * s + v[1] * c, v[2])


# ------------------------------------------------------------------- globe ---
class Globe:
    """An orthographic view of the unit sphere centred on (lat0, lon0)."""

    def __init__(self, cx, cy, r, lat0, lon0):
        self.cx, self.cy, self.r = cx, cy, r
        self.lat0, self.lon0 = lat0, lon0
        self.out = from_latlon(lat0, lon0)              # toward the viewer
        self.east = norm(cross((0.0, 0.0, 1.0), self.out))
        self.north = cross(self.out, self.east)

    def view(self, p):
        """ECEF -> view coords (x right, y up, z toward the viewer)."""
        return (dot(p, self.east), dot(p, self.north), dot(p, self.out))

    def xy(self, p):
        """ECEF point (any radius) -> canvas (x, y), and its depth z."""
        x, y, z = self.view(p)
        return (self.cx + self.r * x, self.cy - self.r * y), z

    def hidden(self, p):
        """Behind the globe from the viewer's side."""
        x, y, z = self.view(p)
        return z < 0 and x * x + y * y < 1.0


# ------------------------------------------------------------------ orbits ---
class Pass:
    """
    One pass of an inclined circular orbit, and the swath it paints.

    The ground track is the great circle g(s) = cos(s) a + sin(s) b. `s0..s1`
    is the stretch the instrument records; `half` is the swath half-width, as
    an angle at Earth's centre.
    """

    def __init__(self, normal, node, s0, s1, half):
        self.n = norm(normal)
        self.a = norm(node)
        self.b = cross(self.n, self.a)
        self.s0, self.s1, self.half = s0, s1, half

    def track(self, s):
        return comb(self.a, math.cos(s), self.b, math.sin(s))

    def ground(self, s, u):
        """Point on the surface at along-track s, cross-track angle u."""
        return comb(self.track(s), math.cos(u), self.n, math.sin(u))

    def sat(self, s, alt):
        g = self.track(s)
        return (g[0] * alt, g[1] * alt, g[2] * alt)

    def cells(self, rows, cols):
        """[(row, col, (4 ECEF corners))] covering the recorded swath."""
        out = []
        for r in range(rows):
            sa = self.s0 + (self.s1 - self.s0) * r / rows
            sb = self.s0 + (self.s1 - self.s0) * (r + 1) / rows
            for c in range(cols):
                ua = -self.half + 2 * self.half * c / cols
                ub = -self.half + 2 * self.half * (c + 1) / cols
                out.append((r, c, (self.ground(sa, ua), self.ground(sa, ub),
                                   self.ground(sb, ub), self.ground(sb, ua))))
        return out


def orbit(incl, node_lon):
    """(normal, ascending node) of an orbit with inclination `incl`, degrees."""
    i, o = math.radians(incl), math.radians(node_lon)
    node = (math.cos(o), math.sin(o), 0.0)
    normal = (math.sin(i) * math.sin(o), -math.sin(i) * math.cos(o), math.cos(i))
    return normal, node


def pass_over(globe, incl, target, half, span, descending=True):
    """
    The pass of an `incl`-degree orbit whose track runs through `target`
    (lat, lon), recording `span` radians of track centred there.

    Solved by search rather than spherical trigonometry: it is run once per
    pass, and a brute-force answer cannot pick the wrong branch of an asin.
    """
    tp = from_latlon(*target)
    best = None
    for k in range(3600):
        node_lon = k / 10.0 - 180.0
        normal, node = orbit(incl, node_lon)
        p = Pass(normal, node, 0, 0, half)
        # the track point nearest the target is its projection onto the plane
        s = math.atan2(dot(tp, p.b), dot(tp, p.a))
        miss = abs(dot(tp, p.n))
        # descending = moving south at s, i.e. d/ds of z is negative
        dz = -math.sin(s) * p.a[2] + math.cos(s) * p.b[2]
        if (dz < 0) != descending:
            continue
        if best is None or miss < best[0]:
            best = (miss, normal, node, s)
    _miss, normal, node, s = best
    return Pass(normal, node, s - span / 2, s + span / 2, half)


# ------------------------------------------------------------- the raster ---
def write_png(path, w, h, rgba):
    """RGBA8 rows (bytes, len w*h*4) -> a PNG. Filter 0 on every row."""
    raw = bytearray()
    stride = w * 4
    for y in range(h):
        raw.append(0)
        raw += rgba[y * stride:(y + 1) * stride]

    def chunk(tag, data):
        return (struct.pack(">I", len(data)) + tag + data
                + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))

    with open(path, "wb") as fh:
        fh.write(b"\x89PNG\r\n\x1a\n"
                 + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0))
                 + chunk(b"IDAT", zlib.compress(bytes(raw), 9))
                 + chunk(b"IEND", b""))


TEX_W, TEX_H = 1024, 512          # decoded size; ample for a ~430px globe
LIGHT = norm((-0.45, 0.50, 0.74))  # upper-left, a little toward the viewer
AIR = (120, 170, 255)              # limb tint


def render_globe(texture, out, globe):
    """
    Project an equirectangular `texture` onto `globe` and write `out` (RGBA).

    The disc edge is feathered over one pixel so it does not stair-step, and
    the limb is tinted toward AIR -- a cheap atmosphere that keeps the globe
    from reading as a flat sticker.
    """
    tex = subprocess.run(
        ["magick", texture, "-resize", "%dx%d!" % (TEX_W, TEX_H),
         "-depth", "8", "rgb:-"], check=True, capture_output=True).stdout
    if len(tex) != TEX_W * TEX_H * 3:
        raise RuntimeError("decoded %d bytes from %s, expected %d"
                           % (len(tex), texture, TEX_W * TEX_H * 3))
    d = int(round(2 * globe.r))
    rad = d / 2.0
    e, n, o = globe.east, globe.north, globe.out
    px = bytearray(d * d * 4)
    for j in range(d):
        y = 1.0 - (j + 0.5) / rad
        for i in range(d):
            x = (i + 0.5) / rad - 1.0
            rr = x * x + y * y
            edge = (1.0 - math.sqrt(rr)) * rad
            if edge <= 0:
                continue
            z = math.sqrt(max(0.0, 1.0 - rr))
            p = (x * e[0] + y * n[0] + z * o[0],
                 x * e[1] + y * n[1] + z * o[1],
                 x * e[2] + y * n[2] + z * o[2])
            lat = math.asin(max(-1.0, min(1.0, p[2])))
            lon = math.atan2(p[1], p[0])
            tu = int((lon + math.pi) / (2 * math.pi) * TEX_W) % TEX_W
            tv = min(TEX_H - 1, int((math.pi / 2 - lat) / math.pi * TEX_H))
            k = (tv * TEX_W + tu) * 3
            lit = 0.38 + 0.72 * max(0.0, x * LIGHT[0] + y * LIGHT[1] + z * LIGHT[2])
            air = 0.55 * (1.0 - z) ** 3
            q = (j * d + i) * 4
            for c in range(3):
                v = tex[k + c] * lit * (1 - air) + AIR[c] * air
                px[q + c] = 255 if v > 255 else int(v)
            px[q + 3] = 255 if edge >= 1 else int(255 * edge)
    write_png(out, d, d, px)


SRC_W, SRC_H = 2048, 1024          # the texture's own size: crops are in its pixels


def flat_extent(lon0, lon1, lat0, lat1):
    """
    The crop of the equirectangular texture covering the given box, snapped
    to whole texture pixels: ((x, y, w, h) in pixels, (lon0, lon1, lat0, lat1)
    the box those pixels ACTUALLY cover).

    Anything drawn over the crop must be placed with the snapped extent, not
    the requested one -- the difference is a fraction of a degree, which is
    exactly the misregistration that makes an overlay look wrong.
    """
    x0 = int(round((lon0 + 180) / 360.0 * SRC_W))
    x1 = int(round((lon1 + 180) / 360.0 * SRC_W))
    y0 = int(round((90 - lat1) / 180.0 * SRC_H))
    y1 = int(round((90 - lat0) / 180.0 * SRC_H))
    box = (x0, y0, x1 - x0, y1 - y0)
    ext = (x0 / float(SRC_W) * 360 - 180, x1 / float(SRC_W) * 360 - 180,
           90 - y1 / float(SRC_H) * 180, 90 - y0 / float(SRC_H) * 180)
    return box, ext


def flat_png(texture, cache_dir, box):
    """The texture cropped to `box` (texture pixels), cached like the globe."""
    x, y, w, h = box
    out = os.path.join(cache_dir, "flat_%d_%d_%d_%d.png" % (x, y, w, h))
    if not os.path.exists(out):
        os.makedirs(cache_dir, exist_ok=True)
        tmp = out + ".tmp.png"
        subprocess.run(["magick", texture, "-resize", "%dx%d!" % (SRC_W, SRC_H),
                        "-crop", "%dx%d+%d+%d" % (w, h, x, y), "+repage", tmp],
                       check=True, capture_output=True)
        os.replace(tmp, out)
    return out


def globe_png(texture, cache_dir, globe):
    """The cached globe image for `globe`, rendering it on first use.

    Keyed on everything the pixels depend on, so a moved or resized globe
    renders afresh instead of reusing a stale image."""
    name = "globe_%d_%g_%g.png" % (int(round(2 * globe.r)), globe.lat0, globe.lon0)
    out = os.path.join(cache_dir, name)
    if not os.path.exists(out):
        if not os.path.exists(texture):
            raise FileNotFoundError(
                "%s is missing -- the journey slide needs the Blue Marble "
                "texture (docs/ASSETS.md)" % texture)
        os.makedirs(cache_dir, exist_ok=True)
        tmp = out + ".tmp"
        render_globe(texture, tmp, globe)
        os.replace(tmp, out)
    return out
