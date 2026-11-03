"""
A Gantt timeline in either style, animated bar by bar.

    from datetime import date
    from svg_flow_animator import gantt

    g = gantt.Gantt("Review timeline", draft=True)
    g.row("io", "Code review", date(2026, 11, 23), date(2026, 12, 11),
          stroke="#1971c2", fill="#a5d8ff", note="Ana")
    g.frame_svg(f, style)            # f=None is the finished chart

Dates are inclusive: a bar covers its end day. The axis runs from the Monday on
or before the first start to the Monday after the last end, a tick a week.

`draft=True` stamps the chart, so placeholder dates cannot pass for a plan.

Rows are keyed, so a schedule is just {key: (start, end)}: `retimed()` swaps
one in, and `gantt_editor` edits one in the browser.

Animated like `workflow`: it opens on the finished chart (all that anything
showing only an APNG's first frame will see), the bars fade back and grow in
date order -- bars that start together grow together -- and it ends on the
finished chart, so the loop has no seam.
"""
import math
from datetime import timedelta

from . import svg
from .geometry import label_width, smooth

__all__ = ["Gantt"]

LABEL_SIZE, LABEL_LH = 19, 24
DETAIL_SIZE, DETAIL_LH = 14, 18
NOTE_SIZE = 16
HEADING, HEADING_BLOCK, AXIS_H = 32, 84, 44
MUTED, GRID, DRAFT_INK = "#868e96", "#ced4da", "#e03131"
DRAFT_TEXT = "DRAFT: placeholder dates"

INTRO, RESET, OUTRO = 30, 10, 45         # frames
GROW, STAGGER = 24, 8
GHOST = 0.14                             # a bar waiting to grow


class Gantt:
    def __init__(self, title, draft=False, size=(1600, 900), margin=64):
        self.title, self.draft, self.size, self.margin = title, draft, size, margin
        self.rows = []

    def row(self, key, label, start, end, stroke, fill, detail=None, note=None):
        """One bar. `detail` may hold "\\n"; `note` is written beside the bar."""
        if any(r["key"] == key for r in self.rows):
            raise ValueError(f"row {key!r} is declared twice")
        if end < start:
            raise ValueError(f"{label!r} ends ({end}) before it starts ({start})")
        self.rows.append(dict(key=key, label=label, start=start, end=end, stroke=stroke,
                              fill=fill, detail=detail, note=note))

    def dates(self):
        return {r["key"]: (r["start"], r["end"]) for r in self.rows}

    def retimed(self, dates, draft=None):
        """The same chart on another schedule: {key: (start, end)} for every row."""
        missing = [r["key"] for r in self.rows if r["key"] not in dates]
        if missing:
            raise ValueError(f"no dates for: {', '.join(missing)}")
        unknown = sorted(set(dates) - {r["key"] for r in self.rows})
        if unknown:
            raise ValueError(f"no row called: {', '.join(unknown)}")
        out = Gantt(self.title, self.draft if draft is None else draft, self.size,
                    self.margin)
        for r in self.rows:
            out.row(**dict(r, start=dates[r["key"]][0], end=dates[r["key"]][1]))
        return out

    def axis(self):
        """(Monday on or before the first start, Monday after the last day)."""
        first = min(r["start"] for r in self.rows)
        after = max(r["end"] for r in self.rows) + timedelta(days=1)
        return (first - timedelta(days=first.weekday()),
                after + timedelta(days=(7 - after.weekday()) % 7))

    def layout(self):
        w, h = self.size
        m = self.margin
        label_w = max(max([label_width(r["label"], LABEL_SIZE)]
                          + [label_width(s, DETAIL_SIZE)
                             for s in (r["detail"] or "").split("\n")])
                      for r in self.rows) + 40
        x0, x1 = m + label_w, w - m
        a, b = self.axis()
        ppd = (x1 - x0) / (b - a).days
        row_h = max(64.0, min(104.0, (h - 2 * m - HEADING_BLOCK - AXIS_H) / len(self.rows)))
        bar_h = min(46.0, row_h * 0.48)
        top = max(m, (h - HEADING_BLOCK - AXIS_H - len(self.rows) * row_h) / 2)
        rows_y = top + HEADING_BLOCK + AXIS_H
        bars = [(x0 + (r["start"] - a).days * ppd,
                 rows_y + i * row_h + (row_h - bar_h) / 2,
                 ((r["end"] - r["start"]).days + 1) * ppd, bar_h)
                for i, r in enumerate(self.rows)]
        return dict(x0=x0, x1=x1, ppd=ppd, a=a, b=b, top=top, rows_y=rows_y,
                    row_h=row_h, bars=bars)

    def editor_layout(self):
        """What a browser needs to turn a drag into days: the canvas, where the
        axis starts and its scale, and each row's bar."""
        lay = self.layout()
        return dict(size=list(self.size), axis_start=lay["a"].isoformat(),
                    px_per_day=lay["ppd"],
                    rows=[dict(key=r["key"], label=r["label"], detail=r["detail"],
                               stroke=r["stroke"], start=r["start"].isoformat(),
                               end=r["end"].isoformat(),
                               bar=[round(v, 2) for v in lay["bars"][i]])
                          for i, r in enumerate(self.rows)])

    # ---------------------------------------------------------- animation ---
    def stages(self):
        """({row index: frame its bar starts growing}, total frames)."""
        starts = sorted({r["start"] for r in self.rows})
        at = {d: INTRO + RESET + j * (GROW + STAGGER) for j, d in enumerate(starts)}
        return ({i: at[r["start"]] for i, r in enumerate(self.rows)},
                INTRO + RESET + len(starts) * (GROW + STAGGER) + OUTRO)

    @property
    def total(self):
        return self.stages()[1]

    def _bar_state(self, i, f, begins):
        """(opacity of the whole bar, how much of a growing copy shows or None)."""
        if f is None or f < INTRO:
            return 1.0, None
        if f < begins[i]:
            return 1.0 - (1.0 - GHOST) * smooth((f - INTRO) / RESET), None
        grown = smooth((f - begins[i]) / GROW)
        return (1.0, None) if grown >= 1 else (GHOST, grown)

    # ------------------------------------------------------------- drawing --
    def scene(self, f, st):
        lay = self.layout()
        begins, _ = self.stages()
        m, x1, ppd = self.margin, lay["x1"], lay["ppd"]
        rows_y, row_h = lay["rows_y"], lay["row_h"]
        bottom = rows_y + len(self.rows) * row_h
        ty = lay["top"] + HEADING
        out = [st.text(m, ty, self.title, HEADING, fill=st.ink, weight="bold")]
        if self.draft:
            sw = label_width(DRAFT_TEXT, 15, ratio=0.56) + 28
            out.append(st.box(x1 - sw, ty - 27, sw, 36, "none", stroke=DRAFT_INK, rx=6,
                              sw=2, key="draft"))
            out.append(st.text(x1 - sw / 2, ty - 3, DRAFT_TEXT, 15, fill=DRAFT_INK,
                               anchor="middle", weight="bold"))

        weeks = (lay["b"] - lay["a"]).days // 7
        step = max(1, math.ceil(70 / (7 * ppd)))     # keep tick labels apart
        for wk in range(weeks + 1):
            x = lay["x0"] + wk * 7 * ppd
            out.append(st.poly([(x, rows_y - 10), (x, bottom)], GRID, sw=1.2,
                               key=("week", wk)))
            if wk < weeks and wk % step == 0:
                d = lay["a"] + timedelta(days=7 * wk)
                out.append(st.text(x + 6, rows_y - 18, f"{d:%b} {d.day}", 14, fill=MUTED))
        for i in range(len(self.rows) + 1):
            y = rows_y + i * row_h
            out.append(st.poly([(m, y), (x1, y)], GRID, sw=1, opacity=0.7, key=("rule", i)))

        for i, r in enumerate(self.rows):
            bx, by, bw, bh = lay["bars"][i]
            cy = by + bh / 2
            lines = [(r["label"], LABEL_SIZE, LABEL_LH, st.ink)] + [
                (s, DETAIL_SIZE, DETAIL_LH, MUTED)
                for s in (r["detail"].split("\n") if r["detail"] else [])]
            ly = cy - sum(lh for _, _, lh, _ in lines) / 2
            for s, size, lh, color in lines:
                out.append(st.text(m, ly + lh / 2 + size * 0.36, s, size, fill=color))
                ly += lh

            shown, grown = self._bar_state(i, f, begins)
            bar = st.box(bx, by, bw, bh, r["fill"], stroke=r["stroke"], rx=6, sw=2,
                         key=("bar", i))
            out.append(svg.group(bar, opacity=shown))
            if grown is not None:
                # Reveal the finished bar rather than redraw a shorter one: a
                # sketchy shape regenerated at every width would boil as it grew.
                out.append(f'<clipPath id="grow{i}"><rect x="{bx - 8:.1f}" '
                           f'y="{by - 8:.1f}" width="{(bw + 16) * grown:.1f}" '
                           f'height="{bh + 16:.1f}"/></clipPath>'
                           f'<g clip-path="url(#grow{i})">{bar}</g>')
            if r["note"]:
                nw = label_width(r["note"], NOTE_SIZE)
                if bx + bw + 14 + nw <= x1 + m / 2:      # after the bar
                    nx, anchor = bx + bw + 14, "start"
                elif bw >= nw + 28:                      # inside it
                    nx, anchor = bx + 14, "start"
                else:                                    # before it
                    nx, anchor = bx - 14, "end"
                note_op = shown if grown is None else max(GHOST, smooth((grown - 0.7) / 0.3))
                out.append(st.text(nx, cy + NOTE_SIZE * 0.36, r["note"], NOTE_SIZE,
                                   fill=st.ink, anchor=anchor, opacity=note_op))
        return "".join(out)

    def frame_svg(self, f, st):
        """One whole SVG document; f=None is the finished chart."""
        return svg.document(*self.size, self.scene(f, st), st.bg)
