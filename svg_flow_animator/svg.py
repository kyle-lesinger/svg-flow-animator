"""
SVG element emitters.

Deliberately string-based rather than an element tree: frames are written once
and thrown away, nothing ever needs to query or mutate them, and plain f-strings
keep the generated markup readable when you open a frame to debug it.
"""

__all__ = ["esc", "document", "text", "image", "rect", "circle", "path",
           "group", "marker_defs", "glow", "DEFAULT_FONT"]

DEFAULT_FONT = "Helvetica Neue, Helvetica, Arial, sans-serif"


def esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def _op(opacity):
    return "" if opacity is None or opacity >= 1 else f' opacity="{opacity:.3f}"'


def document(width, height, body, background=None):
    bg = (f'<rect width="{width}" height="{height}" fill="{background}"/>'
          if background else "")
    return (f'<svg xmlns="http://www.w3.org/2000/svg" '
            f'xmlns:xlink="http://www.w3.org/1999/xlink" '
            f'width="{width}" height="{height}" viewBox="0 0 {width} {height}">'
            f'{bg}{body}</svg>')


def text(x, y, s, size=13, fill="#2b3138", anchor="start", weight="normal",
         opacity=1.0, font=DEFAULT_FONT):
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-family="{font}" '
            f'font-size="{size}" font-weight="{weight}" fill="{fill}" '
            f'text-anchor="{anchor}"{_op(opacity)}>{esc(s)}</text>')


def image(href, x, y, w, h, opacity=1.0, preserve="xMidYMid meet"):
    """
    `href` must resolve at or below the frame's own directory -- see render.py.
    Use preserve="xMidYMid slice" to make several differently-shaped images fill
    equal-sized frames uniformly instead of each letterboxing to its own ratio.
    """
    return (f'<image href="{href}" x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" '
            f'height="{h:.1f}" preserveAspectRatio="{preserve}"{_op(opacity)}/>')


def rect(x, y, w, h, fill="none", stroke=None, rx=0, sw=2, opacity=1.0,
         dash=None):
    st = f' stroke="{stroke}" stroke-width="{sw}"' if stroke else ""
    da = f' stroke-dasharray="{dash}"' if dash else ""
    return (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" '
            f'fill="{fill}"{st}{da}{_op(opacity)}/>')


def circle(cx, cy, r, fill="none", stroke=None, sw=2, opacity=1.0):
    st = f' stroke="{stroke}" stroke-width="{sw}"' if stroke else ""
    return (f'<circle cx="{cx:.2f}" cy="{cy:.2f}" r="{r:.2f}" '
            f'fill="{fill}"{st}{_op(opacity)}/>')


def path(d, stroke=None, fill="none", sw=2, opacity=1.0, dash=None,
         dashoffset=None, cap="round", marker_end=None):
    st = f' stroke="{stroke}" stroke-width="{sw}" stroke-linecap="{cap}"' if stroke else ""
    da = f' stroke-dasharray="{dash}"' if dash else ""
    do = f' stroke-dashoffset="{dashoffset:.1f}"' if dashoffset is not None else ""
    mk = f' marker-end="url(#{marker_end})"' if marker_end else ""
    return f'<path d="{d}" fill="{fill}"{st}{da}{do}{mk}{_op(opacity)}/>'


def group(body, opacity=1.0, transform=None):
    tr = f' transform="{transform}"' if transform else ""
    return f'<g{tr}{_op(opacity)}>{body}</g>'


def marker_defs(*colors, prefix="arrow"):
    """One arrowhead marker per colour. Reference as marker_end=f'{prefix}_{i}'."""
    out = []
    for i, c in enumerate(colors):
        out.append(
            f'<marker id="{prefix}_{i}" viewBox="0 0 10 10" refX="9" refY="5" '
            f'markerWidth="5" markerHeight="5" orient="auto-start-reverse">'
            f'<path d="M 0 0 L 10 5 L 0 10 z" fill="{c}"/></marker>')
    return "<defs>" + "".join(out) + "</defs>"


def glow(x, y, w, h, color, strength=1.0, rx=8, rings=((10, .10, 3),
                                                       (6, .20, 3),
                                                       (2, .55, 2.5))):
    """
    A highlight ring built from concentric strokes.

    librsvg's filter support is poor, so feGaussianBlur is not an option --
    stacking a few strokes at decreasing opacity reads as a glow and renders
    identically everywhere.
    """
    if strength <= 0.01:
        return ""
    return "".join(
        rect(x - g, y - g, w + 2 * g, h + 2 * g, stroke=color, rx=rx + g,
             sw=sw, opacity=op * strength)
        for g, op, sw in rings)
