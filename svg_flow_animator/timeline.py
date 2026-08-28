"""
Stages, timing, and the animated primitives that ride on top of a static scene.

The model is deliberately small. An animation is a list of `Stage`s, each with
a start frame, a duration, and a subject. For any frame you ask a stage for its
`progress` (0..1 across its motion) and its `alpha` (bubble opacity, including
fade in/out), then draw accordingly.

Holds are free: consecutive identical frames collapse to almost nothing under
the GIF's inter-frame delta, so generous pauses between beats cost little.
"""
import math

from . import svg
from .geometry import (path_len, point_at, poly_d, smooth, place_near, wrap)

__all__ = ["Stage", "flow", "pulse", "callout"]


class Stage:
    """
    One beat of the animation.

    start, dur  in frames
    anchor      (x, y) of what this beat is ABOUT. The callout position is
                derived from this, not authored -- so the narration stays
                attached to its subject when the layout changes.
    text        narration; omit for a silent beat
    hold        frames the callout lingers after the motion finishes
    """

    def __init__(self, key, start, dur, anchor=None, text=None, hold=10):
        self.key = key
        self.start = start
        self.dur = dur
        self.anchor = anchor
        self.text = text
        self.hold = hold

    def progress(self, f):
        """0..1 across the motion; negative before the stage begins."""
        if f < self.start:
            return -1.0
        return min(1.0, (f - self.start) / float(self.dur))

    def alpha(self, f, fade=7):
        """Callout opacity, with a fade in before and a fade out after."""
        s, e = self.start, self.start + self.dur + self.hold
        if f < s - fade or f > e + fade:
            return 0.0
        if f < s:
            return (f - (s - fade)) / float(fade)
        if f <= e:
            return 1.0
        return 1.0 - (f - e) / float(fade)

    def __repr__(self):
        return f"<Stage {self.key} {self.start}..{self.start + self.dur}>"


# ------------------------------------------------------------------- flows ---
def flow(pts, progress, dash_phase, color, packet_color, width=3.5,
         reveal=0.28):
    """
    A connector that draws itself in, then carries travelling packets.

    Phase one (0..reveal) grows the line from its origin, with a head dot at the
    growing tip. Phase two runs a dashed overlay along the finished line, offset
    by `dash_phase`, which reads as motion without needing per-packet state.

    Do not paint the dashes before the reveal completes -- packets appearing on
    track the head has not reached yet is the giveaway that it is faked.
    """
    total = path_len(pts)
    d = poly_d(pts)
    out = []

    grown = smooth(min(1.0, progress / reveal))
    out.append(svg.path(d, stroke=color, sw=width, opacity=0.28,
                        dash=f"{total * grown:.1f} {total:.1f}"))

    if progress >= reveal:
        out.append(svg.path(d, stroke=packet_color, sw=width,
                            dash="13 15", dashoffset=-dash_phase))
        hx, hy = point_at(pts, 1.0)
    else:
        hx, hy = point_at(pts, grown)

    out.append(svg.circle(hx, hy, width + 2.2, fill=packet_color))
    out.append(svg.circle(hx, hy, width + 6, stroke=packet_color, sw=1.6,
                          opacity=0.45))
    return "".join(out)


def pulse(cx, cy, strength, color, r=34):
    """An expanding ring, for calling attention to a single node."""
    if strength <= 0.01:
        return ""
    return svg.circle(cx, cy, r * (1 + 0.18 * strength), stroke=color, sw=2.5,
                      opacity=0.55 * strength)


# ---------------------------------------------------------------- callouts ---
def callout(stage, alpha, obstacles, bounds, width=380, bg="#12243d",
            fg="#ffffff", font_size=14.5, line_height=19, pad=18,
            clearance=14, tail_max=260):
    """
    A narration bubble, auto-placed near its stage's anchor.

    Position comes from `place_near`, so the bubble lands at the closest spot to
    the subject that collides with nothing in `obstacles`. The tail then leaves
    from whichever edge actually faces the anchor -- a tail pinned to the bottom
    edge points into space as soon as the bubble ends up beside its subject
    rather than above it.

    `width` may be a SEQUENCE of widths, which are tried widest-first. A wider
    bubble wraps to fewer lines, so it is shorter, and a short bubble fits in
    strips a tall one cannot -- trying wide first is what lets a caption slot
    into the gap above a container instead of being pushed into a corner.
    Narrower fallbacks cover the tight vertical corridors. Only if nothing
    places cleanly at any width is an overlap accepted.

    `tail_max` drops the tail once the bubble ends up further than that from
    its subject: a pointer spanning half the canvas stops reading as "this
    describes that" and just looks like a stray arrow.
    """
    if alpha <= 0.01 or not stage.text:
        return ""
    ax, ay = stage.anchor
    widths = [width] if isinstance(width, (int, float)) else list(width)

    def lay_out(bw):
        chars = max(18, int((bw - 2 * pad) / (font_size * 0.52)))
        lines = wrap(stage.text, chars)
        return lines, len(lines) * line_height + 26

    # Try EVERY width and keep the closest fit, rather than taking the first
    # width that places. `place_near` already returns the nearest position for
    # one width, but returning on the first success means the widest candidate
    # always wins wherever only one region admits it -- and "nearest to the
    # anchor" silently degrades into "widest that fits anywhere".
    spot = lines = None
    best_d = None
    for bw in widths:
        cand_lines, height = lay_out(bw)
        cand = place_near((ax, ay), (bw, height), obstacles, bounds,
                          pad=clearance, strict=True)
        if not cand:
            continue
        # Centre distance, matching how place_near ranks candidates within one
        # width. Measuring to the nearest edge instead would rank widths by a
        # different metric than the search itself uses.
        d = math.hypot(cand[0] + cand[2] / 2 - ax, cand[1] + cand[3] / 2 - ay)
        if best_d is None or d < best_d:
            spot, lines, best_d = cand, cand_lines, d
    if spot is None:
        lines, height = lay_out(widths[-1])
        spot = place_near((ax, ay), (widths[-1], height), obstacles, bounds,
                          pad=clearance)
    x, y, w, h = spot

    near_x = max(x, min(x + w, ax))
    near_y = max(y, min(y + h, ay))
    if tail_max and math.hypot(ax - near_x, ay - near_y) > tail_max:
        tail = None
    elif ax < x:
        ty = max(y + 22, min(y + h - 22, ay))
        tail = f"M {x},{ty-12} L {x},{ty+12} L {x-16},{ty} Z"
    elif ax > x + w:
        ty = max(y + 22, min(y + h - 22, ay))
        tail = f"M {x+w},{ty-12} L {x+w},{ty+12} L {x+w+16},{ty} Z"
    else:
        tx = max(x + 24, min(x + w - 24, ax))
        if ay > y + h:
            tail = f"M {tx-12},{y+h} L {tx+12},{y+h} L {tx},{y+h+16} Z"
        else:
            tail = f"M {tx-12},{y} L {tx+12},{y} L {tx},{y-16} Z"

    body = [svg.rect(x, y, w, h, fill=bg, rx=12)]
    if tail:
        body.insert(0, svg.path(tail, fill=bg))
    for i, line in enumerate(lines):
        body.append(svg.text(x + pad, y + 26 + i * line_height, line,
                             font_size, fill=fg))
    return svg.group("".join(body), opacity=alpha)
