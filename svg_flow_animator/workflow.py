"""
Workflow diagrams declared as data: reusable components, nodes and edges.

    from svg_flow_animator import workflow as wf

    PERSON = wf.Component(shape="pill")
    TASK = wf.Component(fill="#a5d8ff", stroke="#1971c2")

    d = wf.Diagram("Who reviews what")
    d.node("io", "Code review", TASK, detail="reading files")
    d.node("ana", "Ana", PERSON)
    d.edge("ana", "io")
    d.group("Reviewers", ["ana"])
    d.beat("io")                     # the animation visits beats in this order

    d.frame_svg(f, style)            # one frame; f=None is the finished picture

A Component is a look -- shape, fill, outline, text colour -- written once and
given to every node that shares it. `TASK.but(fill=...)` derives a variant.

The layout is automatic, and only a default. Columns come from the edges: a
node sits one column right of the furthest thing pointing at it, and each
column is ordered to keep lines from crossing. Every node then resolves through
`overrides.rect`, so the editor can move and resize any of them. Lines and
group frames are derived from the nodes and never stored, so they follow.

The animation opens on the finished picture -- anything that shows only the
first frame of an APNG still shows the whole diagram. The lines then fade back,
each beat draws its node's lines in (arrivals first, then departures) while the
rest recedes, and it ends on the finished picture again, so the loop has no
seam.
"""
import math

from . import overrides as ov
from . import svg, timeline
from .geometry import label_width, smooth

__all__ = ["Component", "Diagram"]

TITLE_SIZE, TITLE_LH = 20, 26
DETAIL_SIZE, DETAIL_LH = 15, 19
PAD_X, PAD_Y, MIN_W = 20, 14, 110
COL_GAP, ROW_GAP = 190, 22
GROUP_PAD, GROUP_HEAD = 20, 44
HEADING, HEADING_BLOCK = 32, 72          # diagram title size, and the room it takes
MUTED = "#868e96"

INTRO, OUTRO = 30, 45                    # frames
BEAT, HOLD, GAP, FADE = 30, 16, 4, 4
RESET = FADE                             # lines fade back as the receding fades in
DIM = 0.6                                # how far the rest recedes during a beat
WAITING = 0.16                           # opacity of a line waiting for its beat
DASH_RATE = 7.0


class Component:
    """A reusable node look. `shape` is "box" or "pill"; `text` defaults to
    white on a dark fill and the style's ink otherwise."""

    def __init__(self, shape="box", fill="none", stroke=None, text=None):
        if shape not in ("box", "pill"):
            raise ValueError(f"shape must be 'box' or 'pill', not {shape!r}")
        self.shape, self.fill, self.stroke, self.text = shape, fill, stroke, text

    def but(self, **changes):
        """A copy with some attributes changed: TASK.but(fill="#b2f2bb")."""
        return Component(**{**vars(self), **changes})


class Diagram:
    def __init__(self, title=None, aspect=16 / 9, margin=56):
        self.title, self.aspect, self.margin = title, aspect, margin
        self.nodes = {}                  # key -> dict(label, comp, detail)
        self.edges = []                  # [(src, dst, colour or None)]
        self.groups = []                 # [(label, [keys])]
        self.beats = []                  # [key]
        self._geo = None

    # ------------------------------------------------------------ declare ---
    def node(self, key, label, component=None, detail=None):
        """`label` and `detail` may hold "\\n" for explicit line breaks."""
        if key in self.nodes:
            raise ValueError(f"node {key!r} is declared twice")
        self.nodes[key] = dict(label=label, comp=component or Component(),
                               detail=detail)
        self._geo = None
        return key

    def edge(self, src, dst, color=None):
        """src -> dst. The line is `color`, else the outline colour of whichever
        end has one, the target's first."""
        self._known(src, dst)
        if src == dst:
            raise ValueError(f"edge {src!r} -> itself")
        if all((a, b) != (src, dst) for a, b, _ in self.edges):
            self.edges.append((src, dst, color))
        self._geo = None

    def group(self, label, keys):
        """A labelled frame around `keys`. It is derived from where they are,
        so it follows them; it reads best when they share a column."""
        self._known(*keys)
        self.groups.append((label, list(keys)))
        self._geo = None

    def beat(self, key):
        """One step of the animation: `key` and its lines, in declared order."""
        self._known(key)
        self.beats.append(key)

    def _known(self, *keys):
        for k in keys:
            if k not in self.nodes:
                raise ValueError(f"no node {k!r}")

    # ------------------------------------------------------------- layout ---
    def columns(self):
        """
        {key: column}, and the edges that decided it. An edge that closes a
        cycle is left out, or "right of everything pointing at it" would never
        settle.
        """
        succ = {k: [] for k in self.nodes}
        for a, b, _ in self.edges:
            succ[a].append(b)
        back, state = set(), {}

        def visit(k):
            state[k] = "open"
            for n in succ[k]:
                if state.get(n) == "open":
                    back.add((k, n))
                elif n not in state:
                    visit(n)
            state[k] = "done"

        for k in self.nodes:
            if k not in state:
                visit(k)
        fwd = [(a, b) for a, b, _ in self.edges if (a, b) not in back]
        col = dict.fromkeys(self.nodes, 0)
        for _ in self.nodes:             # longest path; settles within len(nodes)
            moved = False
            for a, b in fwd:
                if col[b] <= col[a]:
                    col[b], moved = col[a] + 1, True
            if not moved:
                break
        return col, fwd

    def order(self):
        """Each column top to bottom: barycentre sweeps, keeping whichever
        arrangement crossed the fewest lines. Starts from declaration order."""
        col, fwd = self.columns()
        n = max(col.values()) + 1
        layers = [[k for k in self.nodes if col[k] == c] for c in range(n)]
        up = {k: [a for a, b in fwd if b == k and col[a] == col[k] - 1]
              for k in self.nodes}
        down = {k: [b for a, b in fwd if a == k and col[b] == col[k] + 1]
                for k in self.nodes}

        def crossings(ls):
            pos = {k: i for layer in ls for i, k in enumerate(layer)}
            total = 0
            for layer in ls[:-1]:
                es = [(pos[a], pos[b]) for a in layer for b in down[a]]
                total += sum((a1 - a2) * (b1 - b2) < 0
                             for i, (a1, b1) in enumerate(es) for a2, b2 in es[i + 1:])
            return total

        best, fewest = [layer[:] for layer in layers], crossings(layers)
        for sweep in range(8):
            pos = {k: i for layer in layers for i, k in enumerate(layer)}
            downward = sweep % 2 == 0
            nb = up if downward else down
            for c in (range(1, n) if downward else range(n - 2, -1, -1)):
                bary = {k: (sum(pos[m] for m in nb[k]) / len(nb[k]) if nb[k] else pos[k])
                        for k in layers[c]}
                layers[c].sort(key=bary.get)
                pos.update((k, i) for i, k in enumerate(layers[c]))
            here = crossings(layers)
            if here < fewest:
                best, fewest = [layer[:] for layer in layers], here
        return best, fewest

    def _text_size(self, k):
        n = self.nodes[k]
        lines = n["label"].split("\n")
        detail = n["detail"].split("\n") if n["detail"] else []
        text_w = max([label_width(s, TITLE_SIZE) for s in lines]
                     + [label_width(s, DETAIL_SIZE) for s in detail])
        h = len(lines) * TITLE_LH + len(detail) * DETAIL_LH + 2 * PAD_Y
        # A pill's round ends eat into the room for text.
        pad = max(PAD_X, h / 2) if n["comp"].shape == "pill" else PAD_X
        return max(MIN_W, text_w + 2 * pad), h

    def layout(self):
        """Default rects, canvas size and title position, before overrides."""
        layers, _ = self.order()
        size = {k: self._text_size(k) for k in self.nodes}
        widths = [max(size[k][0] for k in layer) for layer in layers]
        heights = [sum(size[k][1] for k in layer) + ROW_GAP * (len(layer) - 1)
                   for layer in layers]
        rects, x = {}, 0.0
        for c, layer in enumerate(layers):
            y = (max(heights) - heights[c]) / 2
            for k in layer:
                rects[k] = (x, y, widths[c], size[k][1])   # a column shares a width
                y += size[k][1] + ROW_GAP
            x += widths[c] + COL_GAP

        shapes = list(rects.values()) + [_frame(keys, rects) for _, keys in self.groups]
        x0 = min(r[0] for r in shapes)
        y0 = min(r[1] for r in shapes)
        x1 = max(r[0] + r[2] for r in shapes)
        y1 = max(r[1] + r[3] for r in shapes)
        head = HEADING_BLOCK if self.title else 0
        w = x1 - x0 + 2 * self.margin
        h = y1 - y0 + 2 * self.margin + head
        width, height = max(w, h * self.aspect), max(h, w / self.aspect)
        ox = (width - w) / 2 + self.margin - x0
        oy = (height - h) / 2 + self.margin + head - y0
        rects = {k: tuple(round(v, 1) for v in (r[0] + ox, r[1] + oy, r[2], r[3]))
                 for k, r in rects.items()}
        title_at = (round(x0 + ox, 1), round(y0 + oy - head + HEADING, 1))
        return rects, (int(math.ceil(width)), int(math.ceil(height))), title_at

    def geometry(self):
        """Resolved rects, edge paths, canvas size and title position. Every
        node is an `ov.rect`: this is where overrides win."""
        if self._geo is None:
            rects, size, title_at = self.layout()
            rects = {k: ov.rect(f"node.{k}", r, self.nodes[k]["label"].replace("\n", " "))
                     for k, r in rects.items()}
            title = ov.point("label.title", title_at, "title") if self.title else None
            start, end = self._ports(rects)
            paths = [_curve(start[i], end[i]) for i in range(len(self.edges))]
            self._geo = dict(rects=rects, size=size, title=title, paths=paths)
        return self._geo

    @property
    def size(self):
        return self.geometry()["size"]

    def _ports(self, rects):
        """Where each edge leaves and arrives. Lines sharing a side fan out
        along it, in the order of whatever is at their far end, so they leave
        without crossing each other."""
        start, end = {}, {}
        for i_end, far, right, out in ((0, 1, True, start), (1, 0, False, end)):
            by_node = {}
            for i, e in enumerate(self.edges):
                by_node.setdefault(e[i_end], []).append(i)
            for k, idx in by_node.items():
                idx.sort(key=lambda i: _mid_y(rects[self.edges[i][far]]))
                for j, i in enumerate(idx):
                    out[i] = self._port(k, rects[k], j, len(idx), right)
        return start, end

    def _port(self, k, rect, j, n, right):
        x, y, w, h = rect
        spread = min(12.0, h * 0.6 / (n - 1)) if n > 1 else 0.0
        dy = (j - (n - 1) / 2) * spread
        inset = 0.0
        if self.nodes[k]["comp"].shape == "pill":
            r = h / 2                    # the end is a half circle: sit ON it
            inset = r - math.sqrt(max(0.0, r * r - dy * dy))
        return (x + w - inset if right else x + inset, y + h / 2 + dy)

    def edge_color(self, i, st):
        a, b, color = self.edges[i]
        return (color or self.nodes[b]["comp"].stroke or self.nodes[a]["comp"].stroke
                or st.ink)

    # ---------------------------------------------------------- animation ---
    def stages(self):
        """([Stage per beat], total frames)."""
        f, out = INTRO + RESET, []
        for k in self.beats:
            out.append(timeline.Stage(k, f, BEAT, hold=HOLD))
            f += BEAT + HOLD + GAP
        return out, f + OUTRO

    @property
    def total(self):
        return self.stages()[1]

    def owners(self):
        """{edge index: (beat index, arriving?)} -- each edge belongs to the
        first beat at either of its ends."""
        out = {}
        for bi, k in enumerate(self.beats):
            for i, (a, b, _) in enumerate(self.edges):
                if i not in out and k in (a, b):
                    out[i] = (bi, b == k)
        return out

    def focus(self, key):
        """A beat's subject and everything one line away from it."""
        return {key} | {b for a, b, _ in self.edges if a == key} | {
            a for a, b, _ in self.edges if b == key}

    @staticmethod
    def _recede(f, stages):
        """
        How far the unfocused part of the picture recedes at f: up into the
        first beat, held across all of them, down after the last.

        Held FLAT between beats, with only the focus crossfading. Easing back
        to the full picture between beats repaints nearly every pixel for
        several frames each time, and that was most of the APNG's bytes.
        """
        if f is None or not stages:
            return 0.0
        first, last = stages[0], stages[-1]
        if f < first.start:
            return smooth((f - (first.start - FADE)) / FADE)
        return 1.0 - smooth((f - (last.start + last.dur + last.hold)) / FADE)

    def _edge_state(self, i, f, stages, owners):
        """(opacity of the resting line, progress of the travelling one or None)."""
        if f is None or i not in owners or f < INTRO:
            return 1.0, None
        bi, arriving = owners[i]
        stage = stages[bi]
        if f > stage.start + stage.dur + stage.hold:
            return 1.0, None
        p = stage.progress(f)
        local = p / 0.6 if arriving else (p - 0.45) / 0.55
        if p < 0 or local <= 0:
            # Waiting for its beat, faded back from the finished picture.
            return 1.0 - (1.0 - WAITING) * smooth((f - INTRO) / RESET), None
        return WAITING, min(1.0, local)

    # ------------------------------------------------------------- drawing --
    def scene(self, f, st):
        """Body markup at frame f; f=None is the finished picture."""
        g = self.geometry()
        rects = g["rects"]
        stages, _ = self.stages()
        owners = self.owners()
        lit = [s.alpha(f, FADE) if f is not None else 0.0 for s in stages]
        recede = DIM * self._recede(f, stages)
        # How much each node is in focus. Summed, not maxed: a node in two
        # consecutive beats would otherwise dip as one fades out and the next
        # fades in.
        held = dict.fromkeys(self.nodes, 0.0)
        for bi, k in enumerate(self.beats):
            for n in self.focus(k):
                held[n] = min(1.0, held[n] + lit[bi])

        out = []
        for label, keys in self.groups:
            fx, fy, fw, fh = _frame(keys, rects)
            out.append(st.box(fx, fy, fw, fh, "none", stroke=MUTED, rx=14, sw=1.5,
                              key=("group", label)))
            out.append(st.text(fx + 16, fy + 28, label, 17, fill=MUTED, weight="bold"))

        for i, (a, b, _) in enumerate(self.edges):
            rest, moving = self._edge_state(i, f, stages, owners)
            mine = lit[owners[i][0]] if i in owners else 0.0
            pts, color, key = g["paths"][i], self.edge_color(i, st), ("edge", a, b)
            body = [_lines(st, pts, key, color, 2.2, rest)]
            if moving is not None:
                body.append(timeline.flow(pts, moving, f * DASH_RATE, color, color,
                                          width=3.2, reveal=0.85))
            if moving is None or moving >= 1:
                body.append(_arrowhead(st, pts, color, 2.2, key,
                                       rest if moving is None else 1.0))
            out.append(svg.group("".join(body), opacity=1.0 - recede * (1.0 - mine)))

        for bi, k in enumerate(self.beats):
            if lit[bi] <= 0.01:
                continue
            x, y, w, h = rects[k]
            comp = self.nodes[k]["comp"]
            breathe = lit[bi] * (0.6 + 0.4 * math.sin(max(0.0, stages[bi].progress(f))
                                                      * math.pi * 3))
            rx = h / 2 if comp.shape == "pill" else 8
            for gap, op in ((10, 0.18), (5, 0.36)):
                out.append(st.box(x - gap, y - gap, w + 2 * gap, h + 2 * gap, "none",
                                  stroke=comp.stroke or st.ink, rx=rx + gap, sw=3,
                                  opacity=op * breathe, key=("glow", k, gap)))

        for k in self.nodes:
            out.append(self._node(st, k, rects[k], 1.0 - recede * (1.0 - held[k])))
        if self.title:
            out.append(st.text(*g["title"], self.title, HEADING, fill=st.ink,
                               weight="bold"))
        return "".join(out)

    def _node(self, st, k, rect, opacity):
        n = self.nodes[k]
        comp = n["comp"]
        x, y, w, h = rect
        out = [st.box(x, y, w, h, comp.fill, stroke=comp.stroke or st.edge,
                      rx=h / 2 if comp.shape == "pill" else 8, sw=2, key=("node", k))]
        ink = comp.text or ("#ffffff" if _dark(comp.fill) else st.ink)
        lines = n["label"].split("\n")
        detail = n["detail"].split("\n") if n["detail"] else []
        ty = y + (h - len(lines) * TITLE_LH - len(detail) * DETAIL_LH) / 2
        for s, size, lh, op in ([(s, TITLE_SIZE, TITLE_LH, 1.0) for s in lines]
                                + [(s, DETAIL_SIZE, DETAIL_LH, 0.78) for s in detail]):
            out.append(st.text(x + w / 2, ty + lh / 2 + size * 0.36, s, size, fill=ink,
                               anchor="middle", opacity=op))
            ty += lh
        return svg.group("".join(out), opacity=opacity)

    def frame_svg(self, f, st):
        """One whole SVG document; f=None is the finished picture."""
        w, h = self.size
        return svg.document(w, h, self.scene(f, st), st.bg)

    # -------------------------------------------------------------- editor --
    def build_editor(self, path, title, live=True):
        """
        The browser editor: every node a box to drag or resize over the real
        render, in both styles. `live` offers preview and Save, which need the
        `serve` module's server; see the example's edit.sh.
        """
        from . import editor, styles
        self.geometry()                  # registers every handle
        views = {"Hand-drawn": styles.SKETCH, "Flat": styles.FLAT}
        return editor.build(
            path, self.size,
            {name: (lambda st=st: (self.frame_svg(None, st), st.bg))
             for name, st in views.items()},
            title=title, live={n: st.name for n, st in views.items()} if live else None)


# ---------------------------------------------------------------- helpers ---
def _frame(keys, rects):
    """A group's frame: its members' extent, plus room for the label on top."""
    rs = [rects[k] for k in keys]
    x0 = min(r[0] for r in rs) - GROUP_PAD
    y0 = min(r[1] for r in rs) - GROUP_HEAD
    x1 = max(r[0] + r[2] for r in rs) + GROUP_PAD
    y1 = max(r[1] + r[3] for r in rs) + GROUP_PAD
    return (x0, y0, x1 - x0, y1 - y0)


def _mid_y(rect):
    return rect[1] + rect[3] / 2


def _curve(p0, p1, steps=20):
    """An S-curve from p0 to p1, leaving and arriving horizontally, flattened
    to a polyline: the sketch style roughens polylines, and timeline.flow
    reveals them."""
    (x0, y0), (x1, y1) = p0, p1
    k = max(40.0, abs(x1 - x0) * 0.5)
    c0, c1 = (x0 + k, y0), (x1 - k, y1)
    pts = []
    for i in range(steps + 1):
        t = i / steps
        m = 1 - t
        pts.append((m ** 3 * x0 + 3 * m * m * t * c0[0] + 3 * m * t * t * c1[0] + t ** 3 * x1,
                    m ** 3 * y0 + 3 * m * m * t * c0[1] + 3 * m * t * t * c1[1] + t ** 3 * y1))
    return pts


def _lines(st, pts, key, color, sw, opacity=1.0):
    """A polyline in either style, seeded from `key` so a sketchy line is the
    same line in every frame (GOTCHAS: boiling)."""
    if opacity <= 0.01:
        return ""
    op = f' opacity="{opacity:.3f}"' if opacity < 1 else ""
    return "".join(f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{sw}" '
                   f'stroke-linecap="round" stroke-linejoin="round"{op}/>'
                   for d, _len in st.stroke_layers(pts, key=key))


def _arrowhead(st, pts, color, sw, key, opacity=1.0):
    if opacity <= 0.01:
        return ""
    if hasattr(st, "arrowhead"):
        body = st.arrowhead(pts, color, sw=sw, key=key, size=12)
    else:
        (x1, y1), (x2, y2) = pts[-2], pts[-1]
        a = math.atan2(y2 - y1, x2 - x1)
        tip = [(x2 + 12 * math.cos(a + s), y2 + 12 * math.sin(a + s)) for s in (2.6, -2.6)]
        body = st.poly([tip[0], (x2, y2), tip[1]], color, sw=sw)
    return svg.group(body, opacity=opacity)


def _dark(c):
    if not (isinstance(c, str) and len(c) == 7 and c.startswith("#")):
        return False
    r, g, b = (int(c[i:i + 2], 16) for i in (1, 3, 5))
    return 0.299 * r + 0.587 * g + 0.114 * b < 128
