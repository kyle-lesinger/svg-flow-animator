#!/usr/bin/env python3
"""
Generate a browser-based editor for nudging the diagram's geometry by hand.

    python3 editor.py && open editor.html

It renders the current diagram as a backdrop, overlays a draggable handle on
every coordinate `layout.py` requested through `overrides.py`, and writes the
result back out as `overrides.json`. Rerun `build.sh` and the change is in.

Nothing here is hardcoded to this diagram: the handle list is whatever
`overrides.HANDLES` contains after importing `layout`, so a new `ov.point(...)`
call in layout.py shows up in the editor automatically.

What you can move:
  * points  -- drag (nodes, the hub, the "+" glyph)
  * rects   -- drag the body to move, the corner to resize (every container)
  * paths   -- drag a vertex; double-click a segment to INSERT a vertex, which
               is how a straight connector becomes an angled one; right-click a
               vertex to remove it
  * scalars -- numeric fields in the side panel (arc bow, pitch, spoke launch x)
"""
import base64
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import layout as L          # noqa: E402  -- importing populates ov.HANDLES
import overrides as ov      # noqa: E402
import gen_frames as G      # noqa: E402

SCENE_FRAME = 0             # frame 0 is the static scene, before any flow draws


def warm_up():
    """
    Force every connector to register itself.

    `ov.path()` only records a handle when the function that owns it is called,
    and the flow functions normally run during frame generation. Without this
    the editor would offer no bendable lines at all -- which is most of what it
    is for.
    """
    for i in range(len(L.SOURCES)):
        L.spoke(i)
    L.hub_to_ingest()
    L.ingest_to_stac()
    L.disasters_riser()
    L.disasters_to_stac()
    L.stac_return()
    L.push_path()


def render_backdrop():
    svg_path = os.path.join(HERE, "_scene.svg")
    png_path = os.path.join(HERE, "_scene.png")
    with open(svg_path, "w") as fh:
        fh.write(G.frame_svg(SCENE_FRAME))
    subprocess.run(["rsvg-convert", "-w", str(L.W), "-h", str(L.H),
                    "-b", "white", "-o", png_path, svg_path], check=True)
    with open(png_path, "rb") as fh:
        b64 = base64.b64encode(fh.read()).decode()
    os.remove(svg_path)
    os.remove(png_path)
    return b64


HTML = """<!doctype html>
<meta charset="utf-8">
<title>flowgif layout editor</title>
<style>
  * { box-sizing: border-box; }
  body { margin:0; font:13px/1.45 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
         background:#1b1f24; color:#e6e9ee; display:flex; height:100vh; overflow:hidden; }
  #stage { flex:1; overflow:auto; padding:16px; }
  #wrap { position:relative; width:__W__px; height:__H__px;
          background:#fff url(data:image/png;base64,__BG__) no-repeat 0 0;
          background-size:__W__px __H__px; box-shadow:0 2px 24px #0008; }
  svg { position:absolute; inset:0; width:100%; height:100%; }
  aside { width:340px; background:#22272e; border-left:1px solid #333a44;
          display:flex; flex-direction:column; }
  aside h1 { font-size:14px; margin:0; padding:14px 16px; border-bottom:1px solid #333a44;
             font-weight:600; letter-spacing:.02em; }
  #panel { flex:1; overflow:auto; padding:10px 14px; }
  .grp { margin-bottom:14px; }
  .grp h2 { font-size:11px; text-transform:uppercase; letter-spacing:.08em;
            color:#8b95a3; margin:10px 0 6px; font-weight:600; }
  .row { display:flex; align-items:center; gap:6px; padding:3px 0; }
  .row label { flex:1; font-size:12px; color:#c6cdd8; cursor:pointer;
               white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
  .row.on label { color:#ffd479; font-weight:600; }
  .row input { width:56px; background:#181c21; border:1px solid #39414c; color:#e6e9ee;
               border-radius:4px; padding:2px 5px; font:11px ui-monospace,monospace; }
  footer { border-top:1px solid #333a44; padding:12px 14px; display:flex;
           flex-direction:column; gap:8px; }
  button { background:#2f6feb; border:0; color:#fff; padding:8px 10px; border-radius:6px;
           font-size:12.5px; font-weight:600; cursor:pointer; }
  button.ghost { background:#333a44; }
  button:hover { filter:brightness(1.12); }
  pre { background:#12161a; border:1px solid #333a44; border-radius:6px; padding:8px;
        margin:0; max-height:170px; overflow:auto; font:10.5px ui-monospace,monospace;
        color:#9fb4cc; white-space:pre-wrap; }
  .hint { color:#7c8593; font-size:11px; line-height:1.5; }
  .hint b { color:#aab4c2; font-weight:600; }
  .vert { fill:#ff7a00; stroke:#fff; stroke-width:1.5; cursor:grab; }
  .vert:hover { fill:#ffa64d; r:7; }
  .pt { fill:#2f6feb; stroke:#fff; stroke-width:2; cursor:grab; }
  .pt:hover { fill:#5b93ff; }
  .rc { fill:transparent; stroke:#2f6feb; stroke-width:1.5; stroke-dasharray:5 4;
        cursor:move; }
  .rc:hover { stroke:#5b93ff; fill:#2f6feb18; }
  .rz { fill:#2f6feb; stroke:#fff; stroke-width:1.5; cursor:nwse-resize; }
  .seg { stroke:#ff7a00; stroke-width:2.5; fill:none; opacity:.55; cursor:copy; }
  .seg:hover { opacity:1; stroke-width:4; }
  .lbl { font:10px sans-serif; fill:#1b1f24; paint-order:stroke;
         stroke:#fff; stroke-width:3px; pointer-events:none; }
  .sel { outline:2px solid #ffd479; }
</style>
<div id="stage"><div id="wrap"><svg id="ov" viewBox="0 0 __W__ __H__"></svg></div></div>
<aside>
  <h1>Layout editor</h1>
  <div id="panel"></div>
  <footer>
    <div class="hint">
      <b>Drag</b> a handle to move it.<br>
      <b>Double-click</b> an orange line to add a bend point.<br>
      <b>Right-click</b> a bend point to delete it.<br>
      <b>Shift-drag</b> snaps to 5px.
    </div>
    <pre id="json"></pre>
    <button id="dl">Download overrides.json</button>
    <button id="copy" class="ghost">Copy to clipboard</button>
    <button id="reset" class="ghost">Reset all to defaults</button>
  </footer>
</aside>
<script>
const H = __HANDLES__;
const W = __W__, HH = __H__;
const svg = document.getElementById('ov');
const NS = 'http://www.w3.org/2000/svg';
const el = (n, a) => { const e = document.createElementNS(NS, n);
  for (const k in a) e.setAttribute(k, a[k]); return e; };

// deep copy of current values, keyed the same as overrides.json
const state = {};
for (const k in H) state[k] = JSON.parse(JSON.stringify(H[k].value));

function same(a, b) { return JSON.stringify(a) === JSON.stringify(b); }

function toSvg(evt) {
  const r = svg.getBoundingClientRect();
  return [ (evt.clientX - r.left) * W / r.width,
           (evt.clientY - r.top) * HH / r.height ];
}
const snap = (v, e) => e.shiftKey ? Math.round(v / 5) * 5 : Math.round(v * 10) / 10;

function drag(node, onMove) {
  node.addEventListener('pointerdown', e => {
    e.preventDefault(); e.stopPropagation();
    node.setPointerCapture(e.pointerId);
    const move = ev => { const [x, y] = toSvg(ev); onMove(snap(x, ev), snap(y, ev)); };
    const up = () => { node.removeEventListener('pointermove', move);
                       node.removeEventListener('pointerup', up); render(); };
    node.addEventListener('pointermove', move);
    node.addEventListener('pointerup', up);
  });
}

function render() {
  svg.textContent = '';
  for (const k in H) {
    const h = H[k], v = state[k];
    if (h.kind === 'point') {
      const c = el('circle', {cx: v[0], cy: v[1], r: 6, class: 'pt'});
      drag(c, (x, y) => { state[k] = [x, y]; c.setAttribute('cx', x); c.setAttribute('cy', y); sync(); });
      svg.append(c, el2label(v[0] + 10, v[1] - 8, h.label));
    } else if (h.kind === 'rect') {
      const r = el('rect', {x: v[0], y: v[1], width: v[2], height: v[3], rx: 6, class: 'rc'});
      drag(r, (x, y) => { state[k] = [x - v[2] / 2, y - v[3] / 2, v[2], v[3]];
        r.setAttribute('x', state[k][0]); r.setAttribute('y', state[k][1]); sync(); });
      const g = el('rect', {x: v[0] + v[2] - 5, y: v[1] + v[3] - 5, width: 11, height: 11, class: 'rz'});
      drag(g, (x, y) => { state[k] = [v[0], v[1], Math.max(40, x - v[0]), Math.max(30, y - v[1])];
        render(); });
      svg.append(r, g, el2label(v[0] + 8, v[1] + 16, h.label));
    } else if (h.kind === 'path') {
      for (let i = 0; i < v.length - 1; i++) {
        const seg = el('line', {x1: v[i][0], y1: v[i][1], x2: v[i+1][0], y2: v[i+1][1], class: 'seg'});
        seg.addEventListener('dblclick', e => {
          const [x, y] = toSvg(e);
          state[k] = v.slice(0, i + 1).concat([[Math.round(x), Math.round(y)]], v.slice(i + 1));
          render();
        });
        svg.append(seg);
      }
      v.forEach((p, i) => {
        const c = el('circle', {cx: p[0], cy: p[1], r: 5.5, class: 'vert'});
        drag(c, (x, y) => { state[k][i] = [x, y]; c.setAttribute('cx', x); c.setAttribute('cy', y);
          render2(); sync(); });
        c.addEventListener('contextmenu', e => { e.preventDefault();
          if (state[k].length > 2) { state[k].splice(i, 1); render(); } });
        svg.append(c);
      });
    }
  }
  sync();
}
// cheap re-draw of just the segments while dragging a vertex
function render2() { render(); }

function el2label(x, y, t) { const e = el('text', {x: x, y: y, class: 'lbl'}); e.textContent = t; return e; }

function payload() {
  const out = {};
  for (const k in H) if (!same(state[k], H[k].default)) out[k] = state[k];
  return out;
}

function sync() {
  const p = payload();
  document.getElementById('json').textContent =
    Object.keys(p).length ? JSON.stringify(p, null, 2) : '{}   (nothing changed yet)';
  for (const k in H) {
    const row = document.getElementById('row_' + CSS.escape(k));
    if (row) row.classList.toggle('on', !same(state[k], H[k].default));
    const f = document.querySelectorAll('[data-k="' + CSS.escape(k) + '"]');
    f.forEach((inp, i) => { if (document.activeElement !== inp)
      inp.value = H[k].kind === 'scalar' ? state[k] : flat(state[k])[i]; });
  }
}
const flat = v => (typeof v === 'number') ? [v]
  : (Array.isArray(v[0]) ? v.flat() : v);

function panel() {
  const groups = {};
  for (const k in H) {
    const g = k.split('.')[0];
    (groups[g] = groups[g] || []).push(k);
  }
  const host = document.getElementById('panel');
  for (const g in groups) {
    const d = document.createElement('div'); d.className = 'grp';
    d.innerHTML = '<h2>' + g + '</h2>';
    for (const k of groups[g]) {
      const h = H[k];
      const row = document.createElement('div');
      row.className = 'row'; row.id = 'row_' + k;
      const lab = document.createElement('label'); lab.textContent = h.label;
      row.append(lab);
      if (h.kind === 'scalar' || h.kind === 'point' || h.kind === 'rect') {
        flat(state[k]).forEach((n, i) => {
          const inp = document.createElement('input');
          inp.type = 'number'; inp.step = '1'; inp.value = n; inp.dataset.k = k;
          inp.addEventListener('input', () => {
            const val = parseFloat(inp.value); if (isNaN(val)) return;
            if (h.kind === 'scalar') state[k] = val;
            else { const a = flat(state[k]).slice(); a[i] = val; state[k] = a; }
            render();
          });
          row.append(inp);
        });
      } else {
        const n = document.createElement('span');
        n.style.cssText = 'color:#7c8593;font:11px ui-monospace,monospace';
        n.textContent = state[k].length + ' pts'; row.append(n);
      }
      d.append(row);
    }
    host.append(d);
  }
}

document.getElementById('dl').onclick = () => {
  const b = new Blob([JSON.stringify(payload(), null, 2) + '\\n'], {type: 'application/json'});
  const a = document.createElement('a');
  a.href = URL.createObjectURL(b); a.download = 'overrides.json'; a.click();
};
document.getElementById('copy').onclick = async () => {
  await navigator.clipboard.writeText(JSON.stringify(payload(), null, 2));
  const b = document.getElementById('copy');
  b.textContent = 'Copied'; setTimeout(() => b.textContent = 'Copy to clipboard', 1200);
};
document.getElementById('reset').onclick = () => {
  for (const k in H) state[k] = JSON.parse(JSON.stringify(H[k].default));
  render();
};

panel(); render();
</script>
"""


def main():
    warm_up()
    handles = {}
    for key, h in ov.HANDLES.items():
        handles[key] = dict(kind=h["kind"], label=h["label"],
                            value=_jsonable(h["value"]),
                            default=_jsonable(h["default"]))
    html = (HTML
            .replace("__BG__", render_backdrop())
            .replace("__HANDLES__", json.dumps(handles))
            .replace("__W__", str(L.W))
            .replace("__H__", str(L.H)))
    out = os.path.join(HERE, "editor.html")
    with open(out, "w") as fh:
        fh.write(html)
    print(f"{len(handles)} movable handles -> {out}")
    print(ov.summary())
    return out


def _jsonable(v):
    if isinstance(v, (int, float)):
        return v
    if v and isinstance(v[0], (list, tuple)):
        return [[round(float(a), 2), round(float(b), 2)] for a, b in v]
    return [round(float(x), 2) for x in v]


if __name__ == "__main__":
    main()
