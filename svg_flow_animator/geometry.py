"""
Polyline geometry, easing, and collision-aware label placement.

Pure stdlib. No numpy, no shapely -- everything here is a handful of lines and
the whole point is that the package installs with zero dependencies.
"""
import math

__all__ = [
    "smooth", "ease_in_out", "seg_lengths", "path_len", "point_at", "poly_d",
    "label_width", "rects_overlap", "place_near",
]


# ------------------------------------------------------------------ easing ---
def smooth(t):
    """Smoothstep. Clamps to [0,1]; zero derivative at both ends."""
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def ease_in_out(t):
    """Cosine ease. Slightly softer than smoothstep."""
    t = max(0.0, min(1.0, t))
    return 0.5 - 0.5 * math.cos(math.pi * t)


# ---------------------------------------------------------------- polyline ---
def seg_lengths(pts):
    return [math.hypot(pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1])
            for i in range(len(pts) - 1)]


def path_len(pts):
    return sum(seg_lengths(pts))


def point_at(pts, t):
    """The point a fraction `t` of the way along a polyline (t clamped to [0,1])."""
    segs = seg_lengths(pts)
    total = sum(segs)
    if total <= 0:
        return pts[0]
    d = max(0.0, min(1.0, t)) * total
    for i, s in enumerate(segs):
        if d <= s or i == len(segs) - 1:
            f = (d / s) if s else 0.0
            (x0, y0), (x1, y1) = pts[i], pts[i + 1]
            return (x0 + (x1 - x0) * f, y0 + (y1 - y0) * f)
        d -= s
    return pts[-1]


def poly_d(pts):
    """Polyline -> SVG path `d`."""
    return "M " + " L ".join(f"{x:.2f},{y:.2f}" for x, y in pts)


# -------------------------------------------------------------------- text ---
def label_width(s, size, ratio=0.52):
    """
    Rough advance width for a proportional sans face.

    0.52em/char is a decent average for Helvetica/Arial at normal weight. This
    is deliberately an estimate: it exists to decide where a connector can
    start or how many characters fit on a line, not to typeset anything.
    """
    return len(s) * size * ratio


def wrap(text, width_chars):
    words, lines, cur = text.split(), [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        if len(trial) <= width_chars:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


# --------------------------------------------------------------- placement ---
def rects_overlap(a, b, pad=0):
    """(x, y, w, h) intersection test, with `pad` of required clearance."""
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    return not (ax + aw + pad <= bx or bx + bw + pad <= ax or
                ay + ah + pad <= by or by + bh + pad <= ay)


def place_near(anchor, size, obstacles, bounds, pad=14, step=12, margin=12,
               strict=False):
    """
    Find the position for a `size` box closest to `anchor` that hits nothing.

    This is what keeps callout bubbles attached to the thing they describe.
    Hand-picking a slot per callout looks fine until the layout moves; sweeping
    for the nearest free spot keeps them honest automatically.

    anchor    (x, y) the point of interest
    size      (w, h) of the box to place
    obstacles iterable of (x, y, w, h) to avoid
    bounds    (w, h) of the canvas
    strict    return None instead of overlapping, so a caller can retry at a
              different size rather than accept a collision
    returns   (x, y, w, h), falling back to the top-left margin if nothing fits
    """
    ax, ay = anchor
    bw, bh = size
    cw, ch = bounds
    best, best_d = None, None
    for gx in range(margin, int(cw - bw) - margin + 1, step):
        for gy in range(margin, int(ch - bh) - margin + 1, step):
            cand = (gx, gy, bw, bh)
            if any(rects_overlap(cand, o, pad) for o in obstacles):
                continue
            d = math.hypot(gx + bw / 2 - ax, gy + bh / 2 - ay)
            if best_d is None or d < best_d:
                best, best_d = cand, d
    if best is None and strict:
        return None
    return best or (margin, margin, bw, bh)
