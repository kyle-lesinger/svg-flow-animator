"""
roughjs-compatible sketchy geometry, stdlib-only.

Ports the parts of roughjs (renderer.ts / fillers) that Excalidraw actually
uses: _line/doubleLine, linearPath, curve/_curveWithOffset, ellipse, and the
scan-line polygon hachure filler. Same constants, same PRNG, so output is
visually indistinguishable from Excalidraw's.
"""
import math
import zlib

# ---------------------------------------------------------------- options ---
# roughjs defaults; Excalidraw overrides only roughness / fillWeight / hachureGap.
DEFAULTS = dict(
    roughness=1.0,            # Excalidraw "artist". 0=architect, 2=cartoonist
    bowing=1.0,
    max_offset=2.0,           # maxRandomnessOffset
    curve_fitting=0.95,
    curve_tightness=0.0,
    curve_step_count=9,
    hachure_angle=-41.0,
    hachure_gap=-1.0,         # <0 -> stroke_width * 4
    fill_weight=-1.0,         # <0 -> stroke_width / 2
    stroke_width=1.0,
    disable_multi_stroke=False,
    disable_multi_stroke_fill=True,   # roughjs default is False; see cost note
    preserve_vertices=False,
)


class Opt(dict):
    """Attribute-access options bag carrying its own PRNG."""
    def __init__(self, seed, **kw):
        super().__init__(DEFAULTS)
        self.update(kw)
        self.rng = Random(seed)

    def __getattr__(self, k):
        return self[k]


# ------------------------------------------------------------------- PRNG ---
class Random:
    """Exactly roughjs's Random: Lehmer / MINSTD, seed*48271 mod 2^31-1 style."""
    __slots__ = ("s",)

    def __init__(self, seed):
        self.s = (seed & 0xFFFFFFFF) or 1      # 0 would mean Math.random() in JS

    def next(self):
        self.s = (self.s * 48271) & 0xFFFFFFFF      # Math.imul
        return (self.s & 0x7FFFFFFF) / 2147483648.0


def seed_for(*parts):
    """
    Stable 32-bit seed from a shape's IDENTITY.

    zlib.crc32, not hash(): str/bytes hashing is salted per process
    (PYTHONHASHSEED), so hash() would change between runs.
    """
    key = "|".join(f"{p:.3f}" if isinstance(p, float) else str(p) for p in parts)
    return zlib.crc32(key.encode()) or 1


# ---------------------------------------------------------------- offsets ---
def _offset(lo, hi, o, gain=1.0):
    return o.roughness * gain * (o.rng.next() * (hi - lo) + lo)


def _off(x, o, gain=1.0):
    return _offset(-x, x, o, gain)


# ------------------------------------------------------------------- line ---
def _line_ops(x1, y1, x2, y2, o, move, overlay):
    """One sketchy pass over a segment -> list of path ops. Port of rough _line."""
    len_sq = (x1 - x2) ** 2 + (y1 - y2) ** 2
    length = math.sqrt(len_sq)

    # long lines get *less* jitter, or they read as wobbly rather than sketchy
    if length < 200:
        gain = 1.0
    elif length > 500:
        gain = 0.4
    else:
        gain = -0.0016668 * length + 1.233334

    off = o.max_offset
    if off * off * 100 > len_sq:          # short segment -> shrink the jitter
        off = length / 10.0
    half = off / 2.0
    diverge = 0.2 + o.rng.next() * 0.2    # where the two control points sit

    # "bowing": push the middle perpendicular to the segment, so a long line
    # bows like a hand-drawn one instead of just wobbling.
    mdx = o.bowing * o.max_offset * (y2 - y1) / 200.0
    mdy = o.bowing * o.max_offset * (x1 - x2) / 200.0
    mdx = _off(mdx, o, gain)
    mdy = _off(mdy, o, gain)

    amp = half if overlay else off
    pv = o.preserve_vertices
    ops = []
    if move:
        m = half if overlay else off
        ops.append(("M", (x1 + (0 if pv else _off(m, o, gain)),
                          y1 + (0 if pv else _off(m, o, gain)))))
    ops.append(("C", (
        mdx + x1 + (x2 - x1) * diverge + _off(amp, o, gain),
        mdy + y1 + (y2 - y1) * diverge + _off(amp, o, gain),
        mdx + x1 + 2 * (x2 - x1) * diverge + _off(amp, o, gain),
        mdy + y1 + 2 * (y2 - y1) * diverge + _off(amp, o, gain),
        x2 + (0 if pv else _off(amp, o, gain)),
        y2 + (0 if pv else _off(amp, o, gain)),
    )))
    return ops


def double_line(x1, y1, x2, y2, o, filling=False):
    single = o.disable_multi_stroke_fill if filling else o.disable_multi_stroke
    ops = _line_ops(x1, y1, x2, y2, o, True, False)
    if single or o.roughness == 0:
        return ops
    return ops + _line_ops(x1, y1, x2, y2, o, True, True)


def linear_path(pts, close, o):
    """rough's linearPath: doubleLine every segment (this is what rectangle uses)."""
    pts = list(pts)
    if len(pts) < 2:
        return []
    if close and pts[0] != pts[-1]:
        pts = pts + [pts[0]]
    ops = []
    for i in range(len(pts) - 1):
        ops += double_line(pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1], o)
    return ops


# ------------------------------------------------------------------ curve ---
def _curve_ops(pts, o):
    """rough's _curve: Catmull-Rom through pts, emitted as cubics."""
    n = len(pts)
    ops = []
    if n < 4:
        return ops
    s = 1 - o.curve_tightness
    ops.append(("M", (pts[1][0], pts[1][1])))
    for i in range(1, n - 2):
        p0, p1, p2, p3 = pts[i - 1], pts[i], pts[i + 1], pts[i + 2]
        ops.append(("C", (
            p1[0] + (s * p2[0] - s * p0[0]) / 6, p1[1] + (s * p2[1] - s * p0[1]) / 6,
            p2[0] + (s * p1[0] - s * p3[0]) / 6, p2[1] + (s * p1[1] - s * p3[1]) / 6,
            p2[0], p2[1])))
    return ops


def _curve_with_offset(pts, offset, o):
    ps = [(pts[0][0] + _off(offset, o), pts[0][1] + _off(offset, o)),
          (pts[0][0] + _off(offset, o), pts[0][1] + _off(offset, o))]
    for i in range(1, len(pts)):
        ps.append((pts[i][0] + _off(offset, o), pts[i][1] + _off(offset, o)))
        if i == len(pts) - 1:
            ps.append((pts[i][0] + _off(offset, o), pts[i][1] + _off(offset, o)))
    return _curve_ops(ps, o)


def curve(pts, o):
    ops = _curve_with_offset(pts, 1 * (1 + o.roughness * 0.2), o)
    if o.disable_multi_stroke or o.roughness == 0:
        return ops
    return ops + _curve_with_offset(pts, 1.5 * (1 + o.roughness * 0.22), o)


# ---------------------------------------------------------------- ellipse ---
def _ellipse_points(inc, cx, cy, rx, ry, offset, overlap, o):
    """rough's _computeEllipsePoints. Note the deliberate over/under-shoot at
    the seam -- that is what makes the ellipse look open rather than closed."""
    allp = []
    rad = _off(0.5, o) - math.pi / 2
    allp.append((_off(offset, o) + cx + 0.9 * rx * math.cos(rad - inc),
                 _off(offset, o) + cy + 0.9 * ry * math.sin(rad - inc)))
    a = rad
    while a < math.pi * 2 + rad - 0.01:
        allp.append((_off(offset, o) + cx + rx * math.cos(a),
                     _off(offset, o) + cy + ry * math.sin(a)))
        a += inc
    allp.append((_off(offset, o) + cx + rx * math.cos(rad + math.pi * 2 + overlap * 0.5),
                 _off(offset, o) + cy + ry * math.sin(rad + math.pi * 2 + overlap * 0.5)))
    allp.append((_off(offset, o) + cx + 0.98 * rx * math.cos(rad + overlap),
                 _off(offset, o) + cy + 0.98 * ry * math.sin(rad + overlap)))
    allp.append((_off(offset, o) + cx + 0.9 * rx * math.cos(rad + overlap * 0.5),
                 _off(offset, o) + cy + 0.9 * ry * math.sin(rad + overlap * 0.5)))
    return allp


def ellipse_ops(cx, cy, w, h, o):
    psq = math.sqrt(math.pi * 2 * math.sqrt(((w / 2) ** 2 + (h / 2) ** 2) / 2))
    steps = math.ceil(max(o.curve_step_count,
                          (o.curve_step_count / math.sqrt(200)) * psq))
    inc = math.pi * 2 / steps
    rx, ry = abs(w / 2), abs(h / 2)
    cfr = 1 - o.curve_fitting
    rx += _off(rx * cfr, o)
    ry += _off(ry * cfr, o)
    ov = inc * _offset(0.1, _offset(0.4, 1, o), o)
    ops = _curve_with_offset(_ellipse_points(inc, cx, cy, rx, ry, 1, ov, o), 0, o)
    if not o.disable_multi_stroke and o.roughness != 0:
        ops += _curve_with_offset(
            _ellipse_points(inc, cx, cy, rx, ry, 1.5, 0, o), 0, o)
    return ops


# ------------------------------------------------------------ rounded rect ---
def rounded_rect_points(x, y, w, h, r, per_corner=3):
    """Flatten a rounded rect to a closed polygon. Short corner chords get
    auto-tamed by _line's `offset = length/10` clamp, so the corners come out
    curved-and-sketchy rather than spiky."""
    r = max(0.0, min(r, w / 2, h / 2))
    pts = []

    def arc(ccx, ccy, a0, a1):
        for i in range(per_corner + 1):
            a = a0 + (a1 - a0) * i / per_corner
            pts.append((ccx + r * math.cos(a), ccy + r * math.sin(a)))

    pts.append((x + r, y))
    pts.append((x + w - r, y))
    arc(x + w - r, y + r, -math.pi / 2, 0)
    pts.append((x + w, y + h - r))
    arc(x + w - r, y + h - r, 0, math.pi / 2)
    pts.append((x + r, y + h))
    arc(x + r, y + h - r, math.pi / 2, math.pi)
    pts.append((x, y + r))
    arc(x + r, y + r, math.pi, math.pi * 3 / 2)
    return pts


# --------------------------------------------------------------- hachure ----
def _rot(pts, cx, cy, ang):
    c, s = math.cos(ang), math.sin(ang)
    return [((p[0] - cx) * c - (p[1] - cy) * s + cx,
             (p[0] - cx) * s + (p[1] - cy) * c + cy) for p in pts]


def hachure_lines(poly, o):
    """
    Scan-line hachure of a polygon, ported from roughjs's polygonHachureLines.
    The polygon is rotated so the hachure angle becomes horizontal, scanned,
    then the resulting segments are rotated back.
    """
    gap = o.hachure_gap
    if gap < 0:
        gap = o.stroke_width * 4
    gap = max(round(gap), 1)

    ang = math.radians(o.hachure_angle + 90)
    cx = sum(p[0] for p in poly) / len(poly)
    cy = sum(p[1] for p in poly) / len(poly)
    rp = _rot(poly, cx, cy, -ang)

    ys = [p[1] for p in rp]
    ymin, ymax = min(ys), max(ys)
    edges = []
    for i in range(len(rp)):
        a, b = rp[i], rp[(i + 1) % len(rp)]
        if a[1] == b[1]:
            continue
        if a[1] > b[1]:
            a, b = b, a
        edges.append((a[1], b[1], a[0], (b[0] - a[0]) / (b[1] - a[1])))

    segs = []
    yy = ymin + gap * 0.5
    while yy < ymax:
        xs = sorted(x0 + (yy - y0) * slope
                    for (y0, y1, x0, slope) in edges if y0 <= yy < y1)
        for i in range(0, len(xs) - 1, 2):
            if xs[i + 1] - xs[i] > 0.6:      # skip slivers at the tips
                segs.append(((xs[i], yy), (xs[i + 1], yy)))
        yy += gap

    return [(a, b) for a, b in
            (tuple(_rot([s0, s1], cx, cy, ang)) for s0, s1 in segs)]


def hachure_ops(poly, o):
    ops = []
    for (x1, y1), (x2, y2) in hachure_lines(poly, o):
        ops += double_line(x1, y1, x2, y2, o, filling=True)
    return ops


# ------------------------------------------------------------------ emit -----
def ops_to_d(ops, prec=1):
    out = []
    for op, d in ops:
        if op == "M":
            out.append(f"M{d[0]:.{prec}f} {d[1]:.{prec}f}")
        else:
            out.append("C" + " ".join(f"{v:.{prec}f}" for v in d))
    return "".join(out)


# ------------------------------------------------- continuous polyline ------
def linear_path_continuous(pts, o):
    """
    Like linear_path but each pass is ONE subpath (single M, chained C).

    This matters for the animated connectors: stroke-dasharray restarts at
    every `M`, so the per-segment linear_path would make a 5-point polyline
    reveal in five simultaneous pieces instead of drawing itself in.
    Returns a LIST of passes, so each can carry its own dasharray/length.
    """
    passes = []
    for overlay in ((False,) if (o.disable_multi_stroke or o.roughness == 0)
                    else (False, True)):
        ops = []
        for i in range(len(pts) - 1):
            seg = _line_ops(pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1],
                            o, i == 0, overlay)
            ops += seg
        passes.append(ops)
    return passes


def ops_length(ops, steps=16):
    """Flattened arc length of an op list -- needed for stroke-dasharray."""
    total = 0.0
    cx = cy = 0.0
    for op, d in ops:
        if op == "M":
            cx, cy = d
            continue
        x1, y1, x2, y2, x3, y3 = d
        px, py = cx, cy
        for k in range(1, steps + 1):
            t = k / steps
            mt = 1 - t
            bx = (mt ** 3 * cx + 3 * mt * mt * t * x1 + 3 * mt * t * t * x2 + t ** 3 * x3)
            by = (mt ** 3 * cy + 3 * mt * mt * t * y1 + 3 * mt * t * t * y2 + t ** 3 * y3)
            total += math.hypot(bx - px, by - py)
            px, py = bx, by
        cx, cy = x3, y3
    return total
