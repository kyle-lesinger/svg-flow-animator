#!/usr/bin/env python3
"""
Render-style switcher.  gen_frames.py asks `style.S` for its primitives instead
of formatting SVG inline, so the two looks share one set of call sites.

    from style import S            # module-level singleton
    S.box(x, y, w, h, fill)        # <rect> in flat mode, sketchy path in sketch

Selected by  --style=sketch  on argv, or FLOWGIF_STYLE=sketch in the env.
Stdlib only.
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from . import rough as R


# ---------------------------------------------------------------- helpers ---
def _rr_d(x, y, w, h, r):
    """Exact rounded-rect path -- used as the solid fill under a sketchy edge."""
    r = max(0.0, min(r, w / 2, h / 2))
    return (f"M{x+r:.2f},{y:.2f} H{x+w-r:.2f} A{r},{r} 0 0 1 {x+w:.2f},{y+r:.2f} "
            f"V{y+h-r:.2f} A{r},{r} 0 0 1 {x+w-r:.2f},{y+h:.2f} H{x+r:.2f} "
            f"A{r},{r} 0 0 1 {x:.2f},{y+h-r:.2f} V{y+r:.2f} "
            f"A{r},{r} 0 0 1 {x+r:.2f},{y:.2f} Z")


def _op(opacity):
    return "" if opacity >= 1 else f' opacity="{opacity:.3f}"'


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# ============================================================== flat style ===
class FlatStyle:
    name = "flat"
    bg = "#ffffff"
    ink = "#2b3138"
    edge = "#3a414a"
    font = "Helvetica Neue, Helvetica, Arial, sans-serif"
    font_scale = 1.0
    sw_scale = 1.0
    image_filter = ""          # attribute string appended to <image>
    frame_images = False

    # --- containers ---------------------------------------------------------
    def box(self, x, y, w, h, fill, stroke=None, rx=8, opacity=1.0, sw=2,
            key=None, dash=None):
        stroke = stroke or self.edge
        da = f' stroke-dasharray="{dash}"' if dash else ""
        return (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" '
                f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}"'
                f'{da}{_op(opacity)}/>')

    def ellipse(self, cx, cy, rx, ry, fill="none", stroke=None, sw=2,
                opacity=1.0, key=None):
        stroke = stroke or self.edge
        return (f'<ellipse cx="{cx:.2f}" cy="{cy:.2f}" rx="{rx:.2f}" ry="{ry:.2f}" '
                f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{_op(opacity)}/>')

    def circle(self, cx, cy, r, fill="none", stroke=None, sw=2, opacity=1.0, key=None):
        st = f' stroke="{stroke}" stroke-width="{sw}"' if stroke else ""
        return (f'<circle cx="{cx:.2f}" cy="{cy:.2f}" r="{r:.2f}" fill="{fill}"'
                f'{st}{_op(opacity)}/>')

    # --- open polylines -----------------------------------------------------
    def stroke_layers(self, pts, key=None):
        """[(d, arclength)] -- one entry in flat mode, two sketchy passes in
        sketch mode. Callers set stroke-dasharray from the length they get."""
        d = "M " + " L ".join(f"{x:.2f},{y:.2f}" for x, y in pts)
        total = sum(math.hypot(pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1])
                    for i in range(len(pts) - 1))
        return [(d, total)]

    def poly(self, pts, stroke, sw=2, fill="none", closed=False, opacity=1.0, key=None):
        d = "M " + " L ".join(f"{x:.2f},{y:.2f}" for x, y in pts) + (" Z" if closed else "")
        return (f'<path d="{d}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}" '
                f'stroke-linecap="round" stroke-linejoin="round"{_op(opacity)}/>')

    # --- text / images ------------------------------------------------------
    def text(self, x, y, s, size=13, fill=None, anchor="start",
             weight="normal", opacity=1.0):
        fill = fill or self.ink
        return (f'<text x="{x:.1f}" y="{y:.1f}" font-family="{self.font}" '
                f'font-size="{size * self.font_scale:.1f}" font-weight="{weight}" '
                f'fill="{fill}" text-anchor="{anchor}"{_op(opacity)}>{esc(s)}</text>')

    def img(self, href, x, y, w, h, opacity=1.0, preserve="xMidYMid meet", frame=True):
        return (f'<image href="{href}" x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" '
                f'height="{h:.1f}" preserveAspectRatio="{preserve}"'
                f'{self.image_filter}{_op(opacity)}/>')

    def defs(self):
        return ""


# ============================================================ sketch style ===
class SketchStyle(FlatStyle):
    name = "sketch"
    bg = "#fdfcf8"                    # Excalidraw-ish warm paper
    ink = "#1e1e1e"
    edge = "#1e1e1e"
    # Handwriting faces present on this machine; Excalifont/Virgil first in
    # case they are ever installed, then macOS fallbacks, then generic.
    font = "Excalifont, Virgil, Noteworthy, Chalkboard SE, Comic Sans MS, sans-serif"
    font_scale = 1.08                 # Noteworthy/Chalkboard run small; scale up
    sw_scale = 1.0
    image_filter = ""
    # Frames around raster sprites read as stray boxes on small marks (the
    # EGIS globe, the NASA/VEDA/ESRI lockups), so only the large Portal Content
    # screenshots get one -- those genuinely need the edge to sit in the scene.
    frame_images = True
    frame_min_size = 150

    ROUGHNESS = 1.0                   # Excalidraw "artist"
    FILL_MODE = "solid+hachure"       # "solid" | "hachure" | "solid+hachure"
    SOLID_ALPHA = 0.55                # underlay opacity when both are drawn
    HACHURE_MUL = 4.0                 # gap = stroke_width * this
    _cache = {}

    # --- internals ----------------------------------------------------------
    def _opt(self, tag, key, **kw):
        kw.setdefault("roughness", self.ROUGHNESS)
        return R.Opt(R.seed_for(tag, key), **kw)

    def _memo(self, cache_key, fn):
        """288 frames redraw the same static scenery; compute each shape once."""
        v = self._cache.get(cache_key)
        if v is None:
            v = self._cache[cache_key] = fn()
        return v

    def _outline(self, pts, key, sw, closed=True):
        """One continuous subpath per pass: half the `M`s of roughjs's
        per-segment linearPath, visually identical at this scale."""
        o = self._opt("out", key, stroke_width=sw)
        p = list(pts) + ([pts[0]] if closed else [])
        return "".join(R.ops_to_d(x) for x in R.linear_path_continuous(p, o))

    @staticmethod
    def _is_dark(c):
        if not (isinstance(c, str) and c.startswith("#") and len(c) == 7):
            return False
        r, g, b = (int(c[i:i+2], 16) for i in (1, 3, 5))
        return (0.299*r + 0.587*g + 0.114*b) < 128

    def _hachure(self, pts, key, sw):
        o = self._opt("fill", key, stroke_width=sw, hachure_gap=sw * self.HACHURE_MUL)
        return R.ops_to_d(R.hachure_ops(pts, o))

    # --- containers ---------------------------------------------------------
    def box(self, x, y, w, h, fill, stroke=None, rx=8, opacity=1.0, sw=2,
            key=None, dash=None):
        stroke = stroke or self.edge
        k = key if key is not None else (x, y, w, h, rx)
        ck = ("box", k, fill, stroke, rx, sw, dash, self.FILL_MODE, round(x, 2), round(y, 2),
              round(w, 2), round(h, 2))

        def build():
            pts = R.rounded_rect_points(x, y, w, h, rx)
            out = []
            mode = "solid" if self._is_dark(fill) else self.FILL_MODE
            if fill and fill != "none":
                if mode in ("solid", "solid+hachure"):
                    a = 1.0 if mode == "solid" else self.SOLID_ALPHA
                    out.append(f'<path d="{_rr_d(x, y, w, h, rx)}" fill="{fill}"'
                               f'{_op(a)}/>')
                if mode in ("hachure", "solid+hachure"):
                    out.append(f'<path d="{self._hachure(pts, k, sw)}" fill="none" '
                               f'stroke="{fill}" stroke-width="{sw*0.6:.2f}" '
                               f'stroke-linecap="round"/>')
            da = f' stroke-dasharray="{dash}"' if dash else ""
            out.append(f'<path d="{self._outline(pts, k, sw)}" fill="none" '
                       f'stroke="{stroke}" stroke-width="{sw}" stroke-linecap="round" '
                       f'stroke-linejoin="round"{da}/>')
            return "".join(out)

        body = self._memo(ck, build)
        return f'<g{_op(opacity)}>{body}</g>' if opacity < 1 else body

    def ellipse(self, cx, cy, rx, ry, fill="none", stroke=None, sw=2,
                opacity=1.0, key=None):
        stroke = stroke or self.edge
        k = key if key is not None else (cx, cy, rx, ry)

        def build():
            out = []
            if fill and fill != "none":
                out.append(f'<ellipse cx="{cx:.2f}" cy="{cy:.2f}" rx="{rx:.2f}" '
                           f'ry="{ry:.2f}" fill="{fill}"/>')
            o = self._opt("ell", k, stroke_width=sw)
            out.append(f'<path d="{R.ops_to_d(R.ellipse_ops(cx, cy, rx*2, ry*2, o))}" '
                       f'fill="none" stroke="{stroke}" stroke-width="{sw}" '
                       f'stroke-linecap="round"/>')
            return "".join(out)

        body = self._memo(("ell", k, fill, stroke, sw, round(rx, 2), round(ry, 2),
                           round(cx, 2), round(cy, 2)), build)
        return f'<g{_op(opacity)}>{body}</g>' if opacity < 1 else body

    def circle(self, cx, cy, r, fill="none", stroke=None, sw=2, opacity=1.0, key=None):
        # A filled dot smaller than ~7px reads as noise if roughened -- keep it exact.
        if r <= 7 and not stroke:
            return FlatStyle.circle(self, cx, cy, r, fill, stroke, sw, opacity, key)
        return self.ellipse(cx, cy, r, r, fill, stroke, sw, opacity,
                            key if key is not None else (cx, cy, "c"))

    # --- open polylines -----------------------------------------------------
    def stroke_layers(self, pts, key=None):
        k = key if key is not None else tuple(map(tuple, pts))

        def build():
            o = self._opt("line", k, stroke_width=3)
            return [(R.ops_to_d(p), R.ops_length(p))
                    for p in R.linear_path_continuous(pts, o)]

        return self._memo(("lay", k, tuple((round(a, 2), round(b, 2)) for a, b in pts)),
                          build)

    def poly(self, pts, stroke, sw=2, fill="none", closed=False, opacity=1.0, key=None):
        k = key if key is not None else tuple(map(tuple, pts))

        def build():
            out = []
            if fill and fill != "none":
                d = "M " + " L ".join(f"{x:.2f},{y:.2f}" for x, y in pts) + " Z"
                out.append(f'<path d="{d}" fill="{fill}"/>')
            o = self._opt("poly", k, stroke_width=sw)
            out.append(f'<path d="{R.ops_to_d(R.linear_path(pts, closed, o))}" '
                       f'fill="none" stroke="{stroke}" stroke-width="{sw}" '
                       f'stroke-linecap="round" stroke-linejoin="round"/>')
            return "".join(out)

        body = self._memo(("poly", k, stroke, sw, fill, closed,
                           tuple((round(a, 2), round(b, 2)) for a, b in pts)), build)
        return f'<g{_op(opacity)}>{body}</g>' if opacity < 1 else body

    # --- arrowhead ----------------------------------------------------------
    def arrowhead(self, pts, stroke, sw=3, key=None, size=None):
        (x1, y1), (x2, y2) = pts[-2], pts[-1]
        a = math.atan2(y2 - y1, x2 - x1)
        ln = size or (10 + sw * 2)
        k = key if key is not None else (x2, y2, round(a, 3))
        o = self._opt("ah", k, stroke_width=sw)
        d = "".join(R.ops_to_d(R.double_line(x2, y2, x2 + ln * math.cos(a + s),
                                             y2 + ln * math.sin(a + s), o))
                    for s in (2.6, -2.6))
        return (f'<path d="{d}" fill="none" stroke="{stroke}" stroke-width="{sw}" '
                f'stroke-linecap="round"/>')

    # --- images -------------------------------------------------------------
    def img(self, href, x, y, w, h, opacity=1.0, preserve="xMidYMid meet", frame=True):
        el = FlatStyle.img(self, href, x, y, w, h, opacity, preserve)
        if not (frame and self.frame_images) or min(w, h) < getattr(self, "frame_min_size", 26):
            return el
        pad = 5
        pts = R.rounded_rect_points(x - pad, y - pad, w + 2 * pad, h + 2 * pad, 5)
        d = self._memo(("imgf", round(x, 1), round(y, 1), round(w, 1), round(h, 1)),
                       lambda: self._outline(pts, (x, y, w, h, "img"), 1.6))
        return (el + f'<path d="{d}" fill="none" stroke="{self.ink}" '
                f'stroke-width="1.6" stroke-linecap="round" '
                f'stroke-linejoin="round"{_op(opacity)}/>')


# ============================================================== selection ===
FLAT = FlatStyle()
SKETCH = SketchStyle()
STYLES = {"flat": FLAT, "sketch": SKETCH}


def select(argv=None, env_var="FLOWGIF_STYLE"):
    argv = sys.argv if argv is None else argv
    name = os.environ.get(env_var, "flat")
    for a in argv[1:]:
        if a.startswith("--style="):
            name = a.split("=", 1)[1]
    if name not in STYLES:
        raise SystemExit(f"unknown style {name!r}; choose from {sorted(STYLES)}")
    return STYLES[name]


S = select()
