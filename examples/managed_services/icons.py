"""
Outline icons, vendored from Lucide (https://lucide.dev), v0.460.0.

Stroke-only glyphs on a 24x24 grid: understated, one weight, and close to the
line icons in the source Lucid figure. Every element was converted to a plain
`<path d>` at vendoring time -- circles and rects included -- for two reasons:

  * the sketch build fails on any STROKED <rect>/<ellipse> in a frame, as a
    flat primitive leaking into hand-drawn mode;
  * inline vectors need no asset staging, so they cannot go silently missing
    the way a sprite outside librsvg's reach does (docs/GOTCHAS.md).

To swap an icon, change the name in layout.NODES. To add one, fetch
https://unpkg.com/lucide-static@0.460.0/icons/<name>.svg and convert it the
same way (circle -> two arcs, rect -> rounded path, polyline -> M/L).

Lucide is ISC-licensed:

    ISC License

    Copyright (c) for portions of Lucide are held by Cole Bemis 2013-2022 as
    part of Feather (MIT). All other copyright (c) for Lucide are held by
    Lucide Contributors 2022.

    Permission to use, copy, modify, and/or distribute this software for any
    purpose with or without fee is hereby granted, provided that the above
    copyright notice and this permission notice appear in all copies.

    THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
    WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
    MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
    ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
    WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
    ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
    OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
"""

GRID = 24.0

PATHS = {
    'activity': (
        'M22 12h-2.48a2 2 0 0 0-1.93 1.46l-2.35 8.36a.25.25 0 0 1-.48 0L9.24 2.18a.25.25 0 0 0-.48 0l-2.35 8.36A2 2 0 0 1 4.49 12H2',
    ),
    'arrow-left-right': (
        'M8 3 4 7l4 4',
        'M4 7h16',
        'm16 21 4-4-4-4',
        'M20 17H4',
    ),
    'chart-line': (
        'M3 3v16a2 2 0 0 0 2 2h16',
        'm19 9-5 5-4-4-3 3',
    ),
    'code-xml': (
        'm18 16 4-4-4-4',
        'm6 8-4 4 4 4',
        'm14.5 4-5 16',
    ),
    'cpu': (
        'M6 4h12a2 2 0 0 1 2 2v12a2 2 0 0 1 -2 2h-12a2 2 0 0 1 -2 -2v-12a2 2 0 0 1 2 -2Z',
        'M10 9h4a1 1 0 0 1 1 1v4a1 1 0 0 1 -1 1h-4a1 1 0 0 1 -1 -1v-4a1 1 0 0 1 1 -1Z',
        'M15 2v2',
        'M15 20v2',
        'M2 15h2',
        'M2 9h2',
        'M20 15h2',
        'M20 9h2',
        'M9 2v2',
        'M9 20v2',
    ),
    'database': (
        'M3 5a9 3 0 1 0 18 0a9 3 0 1 0 -18 0',
        'M3 5V19A9 3 0 0 0 21 19V5',
        'M3 12A9 3 0 0 0 21 12',
    ),
    'folder-open': (
        'm6 14 1.5-2.9A2 2 0 0 1 9.24 10H20a2 2 0 0 1 1.94 2.5l-1.54 6a2 2 0 0 1-1.95 1.5H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h3.9a2 2 0 0 1 1.69.9l.81 1.2a2 2 0 0 0 1.67.9H18a2 2 0 0 1 2 2v2',
    ),
    'hard-drive': (
        'M22 12L2 12',
        'M5.45 5.11 2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.89A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11z',
        'M6 16L6.01 16',
        'M10 16L10.01 16',
    ),
    'library': (
        'm16 6 4 14',
        'M12 6v14',
        'M8 8v12',
        'M4 4v16',
    ),
    'list-checks': (
        'm3 17 2 2 4-4',
        'm3 7 2 2 4-4',
        'M13 6h8',
        'M13 12h8',
        'M13 18h8',
    ),
    'monitor-dot': (
        'M16 6a3 3 0 1 0 6 0a3 3 0 1 0 -6 0',
        'M22 12v3a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h9',
        'M12 17v4',
        'M8 21h8',
    ),
    'notebook-pen': (
        'M13.4 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-7.4',
        'M2 6h4',
        'M2 10h4',
        'M2 14h4',
        'M2 18h4',
        'M21.378 5.626a1 1 0 1 0-3.004-3.004l-5.01 5.012a2 2 0 0 0-.506.854l-.837 2.87a.5.5 0 0 0 .62.62l2.87-.837a2 2 0 0 0 .854-.506z',
    ),
    'package': (
        'M11 21.73a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73z',
        'M12 22V12',
        'm3.3 7 7.703 4.734a2 2 0 0 0 1.994 0L20.7 7',
        'm7.5 4.27 9 5.15',
    ),
    'server': (
        'M4 2h16a2 2 0 0 1 2 2v4a2 2 0 0 1 -2 2h-16a2 2 0 0 1 -2 -2v-4a2 2 0 0 1 2 -2Z',
        'M4 14h16a2 2 0 0 1 2 2v4a2 2 0 0 1 -2 2h-16a2 2 0 0 1 -2 -2v-4a2 2 0 0 1 2 -2Z',
        'M6 6L6.01 6',
        'M6 18L6.01 18',
    ),
    'shield-check': (
        'M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z',
        'm9 12 2 2 4-4',
    ),
    'user-check': (
        'M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2',
        'M5 7a4 4 0 1 0 8 0a4 4 0 1 0 -8 0',
        'M16 11L18 13L22 9',
    ),
    'users': (
        'M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2',
        'M5 7a4 4 0 1 0 8 0a4 4 0 1 0 -8 0',
        'M22 21v-2a4 4 0 0 0-3-3.87',
        'M16 3.13a4 4 0 0 1 0 7.75',
    ),
    'map-pinned': (
        'M18 8c0 3.613-3.869 7.429-5.393 8.795a1 1 0 0 1-1.214 0C9.87 15.429 6 11.613 6 8a6 6 0 0 1 12 0',
        'M10 8a2 2 0 1 0 4 0a2 2 0 1 0 -4 0',
        'M8.714 14h-3.71a1 1 0 0 0-.948.683l-2.004 6A1 1 0 0 0 3 22h18a1 1 0 0 0 .948-1.316l-2-6a1 1 0 0 0-.949-.684h-3.712',
    ),
    'earth': (
        'M21.54 15H17a2 2 0 0 0-2 2v4.54',
        'M7 3.34V5a3 3 0 0 0 3 3a2 2 0 0 1 2 2c0 1.1.9 2 2 2a2 2 0 0 0 2-2c0-1.1.9-2 2-2h3.17',
        'M11 21.95V18a2 2 0 0 0-2-2a2 2 0 0 1-2-2v-1a2 2 0 0 0-2-2H2.05',
        'M2 12a10 10 0 1 0 20 0a10 10 0 1 0 -20 0',
    ),
    'map': (
        'M14.106 5.553a2 2 0 0 0 1.788 0l3.659-1.83A1 1 0 0 1 21 4.619v12.764a1 1 0 0 1-.553.894l-4.553 2.277a2 2 0 0 1-1.788 0l-4.212-2.106a2 2 0 0 0-1.788 0l-3.659 1.83A1 1 0 0 1 3 19.381V6.618a1 1 0 0 1 .553-.894l4.553-2.277a2 2 0 0 1 1.788 0z',
        'M15 5.764v15',
        'M9 3.236v15',
    ),
    'layers': (
        'm12.83 2.18a2 2 0 0 0-1.66 0L2.6 6.08a1 1 0 0 0 0 1.83l8.58 3.91a2 2 0 0 0 1.66 0l8.58-3.9a1 1 0 0 0 0-1.83Z',
        'm22 17.65-9.17 4.16a2 2 0 0 1-1.66 0L2 17.65',
        'm22 12.65-9.17 4.16a2 2 0 0 1-1.66 0L2 12.65',
    ),
}


def icon(name, cx, cy, size, stroke, sw=1.6, opacity=1.0):
    """
    Icon `name` centred on (cx, cy), `size` units square.

    `sw` is the stroke width ON THE CANVAS. Lucide's own width of 2 is on its
    24 grid, so a scaled-up icon would otherwise thicken with its size and
    outweigh the diagram's linework.
    """
    if name not in PATHS:
        # A misspelt name drawing nothing is the silent failure; refuse it.
        raise KeyError(f"no icon {name!r}; have {sorted(PATHS)}")
    k = size / GRID
    op = f' opacity="{opacity:.3f}"' if opacity < 1 else ""
    body = "".join(f'<path d="{d}"/>' for d in PATHS[name])
    return (f'<g transform="translate({cx - size / 2:.2f},{cy - size / 2:.2f}) '
            f'scale({k:.4f})" fill="none" stroke="{stroke}" '
            f'stroke-width="{sw / k:.3f}" stroke-linecap="round" '
            f'stroke-linejoin="round"{op}>{body}</g>')
