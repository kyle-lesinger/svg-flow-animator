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
from style import S         # noqa: E402

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


def render_backdrop(style):
    """
    Render the static scene for one style and return it as base64.

    Runs in a subprocess because `style.py` picks its backend once at import
    time via a module-level singleton -- switching inside this process would
    mean reloading gen_frames and layout, which is more fragile than just
    paying for a second interpreter.
    """
    svg_path = os.path.join(HERE, f"_scene_{style}.svg")
    png_path = os.path.join(HERE, f"_scene_{style}.png")
    code = (
        "import sys; sys.path.insert(0, %r);"
        "import gen_frames as G;"
        "from style import S;"
        "open(%r, 'w').write(G.frame_svg(%d));"
        "print(S.bg)" % (HERE, svg_path, SCENE_FRAME)
    )
    env = dict(os.environ, FLOWGIF_STYLE=style)
    bg = subprocess.run([sys.executable, "-c", code], env=env, check=True,
                        capture_output=True, text=True).stdout.strip() or "white"
    subprocess.run(["rsvg-convert", "-w", str(L.W), "-h", str(L.H),
                    "-b", bg, "-o", png_path, svg_path], check=True)
    with open(png_path, "rb") as fh:
        b64 = base64.b64encode(fh.read()).decode()
    os.remove(svg_path)
    os.remove(png_path)
    return b64, bg


HTML = r"""<!doctype html>
<meta charset="utf-8">
<title>flowgif layout editor</title>
<style>
  * { box-sizing:border-box; }
  body { margin:0; font:13px/1.45 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
         background:#1b1f24; color:#e6e9ee; display:flex; height:100vh; overflow:hidden;
         user-select:none; }
  #stage { flex:1; overflow:auto; padding:16px; }
  #wrap { position:relative; width:__W__px; height:__H__px;
          /* an explicit ground: without it, a backdrop that fails to load
             leaves the wrap transparent and the dark page shows through,
             which reads as "the screen went black" */
          background-color:#fff;
          background-repeat:no-repeat; background-position:0 0;
          background-size:__W__px __H__px; box-shadow:0 2px 24px #0008; }
  svg { position:absolute; inset:0; width:100%; height:100%; }
  aside { width:330px; background:#22272e; border-left:1px solid #333a44;
          display:flex; flex-direction:column; }
  aside h1 { font-size:13.5px; margin:0; padding:12px 14px; border-bottom:1px solid #333a44;
             font-weight:600; }
  #offline { display:none; margin:10px 12px 2px; padding:10px 11px; border-radius:7px;
             background:#4a3410; border:1px solid #8a6220; color:#f0d9a8;
             font-size:11px; line-height:1.55; }
  #offline.show { display:block; }
  #offline b { color:#ffd479; }
  #offline code { display:block; margin-top:6px; padding:5px 6px; border-radius:4px;
                  background:#1b1f24; color:#9fe0b4; font:10.5px ui-monospace,monospace;
                  word-break:break-all; }
  #styles { display:flex; gap:6px; padding:11px 14px 8px; }
  #styles button { flex:1; padding:9px 6px; font-size:12.5px; background:#333a44; }
  #styles button.on { background:#2f6feb; }
  #stylenote { margin:0; padding:0 14px 11px; font-size:10.5px; color:#7c8593;
               line-height:1.45; border-bottom:1px solid #333a44; }
  #stylenote b { color:#aab4c2; }
  #layers { display:flex; gap:4px; padding:9px 14px; border-bottom:1px solid #333a44;
            flex-wrap:wrap; }
  #layers button { flex:1; min-width:66px; padding:5px 4px; font-size:11px; border-radius:5px;
                   background:#333a44; }
  #layers button.on { background:#2f6feb; }
  #panel { flex:1; overflow:auto; padding:8px 12px; }
  .grp h2 { font-size:10px; text-transform:uppercase; letter-spacing:.09em;
            color:#8b95a3; margin:12px 0 5px; font-weight:700; }
  .row { display:flex; align-items:center; gap:5px; padding:3px 5px; border-radius:5px;
         cursor:pointer; }
  .row:hover { background:#2c333c; }
  .row.sel { background:#2f6feb2e; outline:1px solid #2f6feb; }
  .row label { flex:1; font-size:11.5px; color:#c6cdd8; white-space:nowrap;
               overflow:hidden; text-overflow:ellipsis; cursor:pointer; }
  .row.on label { color:#ffd479; font-weight:600; }
  .row input { width:52px; background:#181c21; border:1px solid #39414c; color:#e6e9ee;
               border-radius:4px; padding:2px 4px; font:11px ui-monospace,monospace; }
  footer { border-top:1px solid #333a44; padding:10px 14px; display:flex;
           flex-direction:column; gap:7px; }
  button { background:#2f6feb; border:0; color:#fff; padding:7px 10px; border-radius:6px;
           font-size:12px; font-weight:600; cursor:pointer; }
  button.ghost { background:#333a44; }
  button:hover { filter:brightness(1.15); }
  button:disabled { opacity:.4; cursor:default; filter:none; }
  #refresh { background:#18a558; }
  #autowrap { display:flex; align-items:center; gap:7px; font-size:11.5px;
              color:#c6cdd8; cursor:pointer; padding:1px 0 3px; }
  #autowrap input { width:14px; height:14px; accent-color:#18a558; cursor:pointer; }
  #srvnote.busy { color:#7fb2ff; }
  #save { background:#8a5cf6; }
  #srvnote { padding:1px 0 2px; }
  #srvnote.warn { color:#e8a33d; }
  #srvnote.ok { color:#6fcf97; }
  pre { background:#12161a; border:1px solid #333a44; border-radius:6px; padding:7px;
        margin:0; max-height:120px; overflow:auto; font:10px ui-monospace,monospace;
        color:#9fb4cc; white-space:pre-wrap; }
  .hint { color:#7c8593; font-size:10.5px; line-height:1.5; }
  .hint b { color:#aab4c2; }
  .undo { display:flex; gap:6px; }
  .undo button { flex:1; }

  /* --- canvas handles ---------------------------------------------------- */
  /* Hit areas are invisible and generous; the visible dot never takes a click,
     so a near-miss still grabs the thing you were aiming at. */
  .hit  { fill:#fff0; stroke:none; cursor:grab; }
  .hit:active { cursor:grabbing; }
  .dot  { pointer-events:none; stroke:#fff; stroke-width:2; }
  .dot.node  { fill:#2f6feb; }
  .dot.label { fill:#18a558; }
  .dot.vert  { fill:#ff7a00; stroke-width:1.5; }
  .dot.sel   { stroke:#ffd479; stroke-width:3.5; }
  /* A container is grabbed by its BORDER only. Filling it would make a
     550x640 rect swallow every click meant for the nodes inside it. */
  .rcv  { fill:none; stroke:#2f6feb; stroke-width:1.5; stroke-dasharray:5 4;
          pointer-events:none; }
  .rcv.sel { stroke:#ffd479; stroke-width:2.5; }
  .rch  { fill:none; stroke:#0000; stroke-width:16; pointer-events:stroke; cursor:move; }
  .rz   { fill:#2f6feb; stroke:#fff; stroke-width:1.5; cursor:nwse-resize; }
  .segv { stroke:#ff7a00; stroke-width:2.5; fill:none; opacity:.5; pointer-events:none; }
  .segh { stroke:#0000; stroke-width:14; fill:none; pointer-events:stroke; cursor:copy; }
  .segh:hover + .segv, .segv.hot { opacity:1; stroke-width:4; }
  .tag  { font:10px sans-serif; fill:#1b1f24; paint-order:stroke; stroke:#fff;
          stroke-width:3px; pointer-events:none; }
</style>
<div id="stage"><div id="wrap"><svg id="ov" viewBox="0 0 __W__ __H__"></svg></div></div>
<aside>
  <h1>Layout editor</h1>
  <div id="offline">
    <b>Live preview is off.</b>
    You opened this file directly, so there is no renderer to talk to and
    <b>Refresh</b> / <b>Save</b> are disabled. To turn them on:
    <code>cd ~/Downloads/disasters-flowgif &amp;&amp; python3 serve.py</code>
    then open <b>http://localhost:8750/editor.html</b>
  </div>
  <div id="styles">
    <button data-s="flat">&#9633;&nbsp; Flat</button>
    <button data-s="sketch">&#9998;&nbsp; Hand-drawn</button>
  </div>
  <p id="stylenote">Geometry is shared &mdash; whichever you pick, the
     overrides you save apply to <b>both</b> renders.</p>
  <div id="layers"></div>
  <div id="panel"></div>
  <footer>
    <div class="undo">
      <button id="undo" class="ghost">&#8630; Undo</button>
      <button id="redo" class="ghost">Redo &#8631;</button>
    </div>
    <div class="hint">
      <b>Drag</b> a dot. <b>Boxes</b> grab by their dashed border.<br>
      <b>Double-click</b> an orange line to add a bend point.<br>
      <b>Right-click</b> a bend point to delete it.<br>
      <b>&#8984;Z</b> undo &middot; <b>&#8984;&#8679;Z</b> redo &middot; <b>Shift-drag</b> snaps to 5px.
    </div>
    <pre id="json"></pre>
    <label id="autowrap"><input type="checkbox" id="auto" checked>
      Auto-refresh after every change</label>
    <button id="refresh">&#8635;&nbsp; Refresh preview</button>
    <button id="save">Save to project</button>
    <div id="srvnote" class="hint"></div>
    <button id="dl" class="ghost">Download overrides.json</button>
    <button id="copy" class="ghost">Copy to clipboard</button>
    <button id="reset" class="ghost">Reset all to defaults</button>
  </footer>
</aside>
<script>
const H = __HANDLES__, W = __W__, HH = __H__;
const BACKDROPS = __BACKDROPS__;
let firstPaint = true;
let currentStyle = 'flat';
// The two styles are the same geometry drawn differently, so the handles never
// move when you switch -- only the picture behind them.
function setStyle(name) {
  const b = BACKDROPS[name];
  if (!b || !b.png) {           // refuse to blank the canvas
    setNote && setNote('no backdrop for "' + name + '" — keeping the current one', 'warn');
    return;
  }
  const wrap = document.getElementById('wrap');
  wrap.style.backgroundImage = 'url(data:image/png;base64,' + b.png + ')';
  wrap.style.backgroundColor = b.bg;
  document.querySelectorAll('#styles button').forEach(x =>
    x.classList.toggle('on', x.dataset.s === name));
  currentStyle = name;
  try { localStorage.setItem('flowgif.style', name); } catch (_) {}
}
const svg = document.getElementById('ov');
const NS = 'http://www.w3.org/2000/svg';
const el = (n, a) => { const e = document.createElementNS(NS, n);
  for (const k in a) e.setAttribute(k, a[k]); return e; };
const clone = o => JSON.parse(JSON.stringify(o));

let state = {};
for (const k in H) state[k] = clone(H[k].value);

// ---- undo / redo ---------------------------------------------------------
let past = [], future = [];
function snapshot() { past.push(JSON.stringify(state)); if (past.length > 200) past.shift();
                      future.length = 0; buttons(); }
function undo() { if (!past.length) return; future.push(JSON.stringify(state));
                  state = JSON.parse(past.pop()); render(); }
function redo() { if (!future.length) return; past.push(JSON.stringify(state));
                  state = JSON.parse(future.pop()); render(); }
function buttons() {
  document.getElementById('undo').disabled = !past.length;
  document.getElementById('redo').disabled = !future.length;
}
addEventListener('keydown', e => {
  if (!(e.metaKey || e.ctrlKey) || e.key.toLowerCase() !== 'z') return;
  if (['INPUT','TEXTAREA'].includes(document.activeElement.tagName)) return;
  e.preventDefault(); e.shiftKey ? redo() : undo();
});

// ---- layers --------------------------------------------------------------
const layerOf = k => k.startsWith('box.') ? 'boxes' : k.startsWith('label.') ? 'labels'
                   : k.startsWith('flow.') ? 'flows' : 'nodes';

// An "offset" handle is stored as a delta from another handle, so a label
// always travels with the thing it names. These resolve it for drawing, and
// convert a dropped position back into a delta.
const anchorXY = k => { const a = state[H[k].anchor_key]; return [a[0], a[1]]; };
const absXY = k => {
  if (H[k].kind !== 'offset') return state[k];
  const a = anchorXY(k);
  return [a[0] + state[k][0], a[1] + state[k][1]];
};
// anchor key -> the offset handles riding on it, so dragging a node drags its
// label along in real time rather than only snapping on release.
const DEPS = {};
for (const k in H) if (H[k].kind === 'offset')
  (DEPS[H[k].anchor_key] ||= []).push(k);
const vis = {boxes:true, nodes:true, labels:true, flows:true};
let sel = null;

// ---- geometry helpers ----------------------------------------------------
function toSvg(evt) { const r = svg.getBoundingClientRect();
  return [(evt.clientX - r.left) * W / r.width, (evt.clientY - r.top) * HH / r.height]; }
const snap = (v, e) => e.shiftKey ? Math.round(v / 5) * 5 : Math.round(v * 10) / 10;

function drag(node, key, onMove) {
  node.addEventListener('pointerdown', e => {
    if (e.button !== 0) return;
    e.preventDefault(); e.stopPropagation();
    snapshot(); sel = key;
    try { node.setPointerCapture(e.pointerId); } catch (_) {}
    const move = ev => { const [x, y] = toSvg(ev); onMove(snap(x, ev), snap(y, ev)); sync(); };
    const up = () => { node.removeEventListener('pointermove', move);
                       node.removeEventListener('pointerup', up); render(); };
    node.addEventListener('pointermove', move);
    node.addEventListener('pointerup', up);
    // Deliberately NOT render() here: it rebuilds the whole overlay and would
    // destroy `node` mid-gesture, taking these listeners with it.
    markSelection();
  });
}

let RENDER_DOTS = {};

// keep a node's dependent labels glued to it mid-drag
function moveDeps(k, dots) {
  for (const dk of (DEPS[k] || [])) {
    const nodes = (dots || RENDER_DOTS)[dk];
    if (!nodes) continue;
    const p = absXY(dk);
    for (const n of nodes) { n.setAttribute('cx', p[0]); n.setAttribute('cy', p[1]); }
  }
}

function markSelection() {
  document.querySelectorAll('#ov .dot, #ov .rcv').forEach(n =>
    n.classList.toggle('sel', n.dataset.k === sel));
  ROWS.forEach((row, k) => row.classList.toggle('sel', k === sel));
}

// ---- render --------------------------------------------------------------
function render() {
  svg.textContent = '';
  const tags = [];

  // boxes first, so everything else sits on top of them
  if (vis.boxes) for (const k in H) {
    if (H[k].kind !== 'rect') continue;
    const v = state[k];
    const box = el('rect', {x:v[0], y:v[1], width:v[2], height:v[3], rx:6, class:'rcv'});
    box.dataset.k = k;
    const grab = el('rect', {x:v[0], y:v[1], width:v[2], height:v[3], rx:6, class:'rch'});
    const z = el('rect', {x:v[0]+v[2]-6, y:v[1]+v[3]-6, width:12, height:12, class:'rz'});
    const place = () => { const q = state[k];
      for (const n of [box, grab]) { n.setAttribute('x', q[0]); n.setAttribute('y', q[1]);
        n.setAttribute('width', q[2]); n.setAttribute('height', q[3]); }
      z.setAttribute('x', q[0]+q[2]-6); z.setAttribute('y', q[1]+q[3]-6); };
    drag(grab, k, (x, y) => { const w = state[k][2], h = state[k][3];
      state[k] = [Math.round(x - w/2), Math.round(y - h/2), w, h]; place(); moveDeps(k); });
    drag(z, k, (x, y) => { const q = state[k];
      state[k] = [q[0], q[1], Math.max(40, Math.round(x - q[0])),
                  Math.max(30, Math.round(y - q[1]))]; place(); });
    svg.append(box, grab, z);
    tags.push([v[0] + 7, v[1] + 15, H[k].label]);
  }

  // connectors
  if (vis.flows) for (const k in H) {
    if (H[k].kind !== 'path') continue;
    const v = state[k];
    const segs = [], verts = [];
    const place = () => { const q = state[k];
      segs.forEach((pair, i) => pair.forEach(n => {
        n.setAttribute('x1', q[i][0]);   n.setAttribute('y1', q[i][1]);
        n.setAttribute('x2', q[i+1][0]); n.setAttribute('y2', q[i+1][1]); }));
      verts.forEach((pair, i) => pair.forEach(n => {
        n.setAttribute('cx', q[i][0]); n.setAttribute('cy', q[i][1]); })); };
    for (let i = 0; i < v.length - 1; i++) {
      const a = {x1:v[i][0], y1:v[i][1], x2:v[i+1][0], y2:v[i+1][1]};
      const hit = el('line', Object.assign({class:'segh'}, a));
      const vis_ = el('line', Object.assign({class:'segv'}, a));
      hit.addEventListener('dblclick', ev => { const [x, y] = toSvg(ev); snapshot();
        const q = state[k];
        state[k] = q.slice(0, i+1).concat([[Math.round(x), Math.round(y)]], q.slice(i+1));
        sel = k; render(); });
      segs.push([hit, vis_]); svg.append(hit, vis_);
    }
    v.forEach((p, i) => {
      const hit = el('circle', {cx:p[0], cy:p[1], r:12, class:'hit'});
      const dot = el('circle', {cx:p[0], cy:p[1], r:5.5, class:'dot vert'});
      dot.dataset.k = k;
      drag(hit, k, (x, y) => { state[k][i] = [x, y]; place(); });
      hit.addEventListener('contextmenu', ev => { ev.preventDefault();
        if (state[k].length > 2) { snapshot(); state[k].splice(i, 1); render(); } });
      verts.push([hit, dot]); svg.append(hit, dot);
    });
  }

  // points and offsets last -- smallest targets on top
  const DOTS = {};
  for (const k in H) {
    if (H[k].kind !== 'point' && H[k].kind !== 'offset') continue;
    const lay = layerOf(k);
    if (!vis[lay]) continue;
    const v = absXY(k);
    const hit = el('circle', {cx:v[0], cy:v[1], r:13, class:'hit'});
    const dot = el('circle', {cx:v[0], cy:v[1], r:6,
      class:'dot ' + (lay === 'labels' ? 'label' : 'node')});
    dot.dataset.k = k;
    DOTS[k] = [hit, dot];
    drag(hit, k, (x, y) => {
      if (H[k].kind === 'offset') {
        const a = anchorXY(k);
        state[k] = [Math.round((x - a[0]) * 10) / 10, Math.round((y - a[1]) * 10) / 10];
      } else {
        state[k] = [x, y];
      }
      const p = absXY(k);
      for (const n of DOTS[k]) { n.setAttribute('cx', p[0]); n.setAttribute('cy', p[1]); }
      moveDeps(k, DOTS);
    });
    svg.append(hit, dot);
    if (sel === k) tags.push([v[0] + 11, v[1] - 9, H[k].label]);
  }
  RENDER_DOTS = DOTS;

  for (const [x, y, t] of tags) { const e = el('text', {x, y, class:'tag'});
    e.textContent = t; svg.append(e); }
  markSelection(); sync();
  if (!firstPaint) scheduleAuto();
  firstPaint = false;
}

const same = (a, b) => JSON.stringify(a) === JSON.stringify(b);
const flat = v => (typeof v === 'number') ? [v] : (Array.isArray(v[0]) ? v.flat() : v);

function payload() { const o = {};
  for (const k in H) if (!same(state[k], H[k].default)) o[k] = state[k];
  return o; }

function sync() {
  const p = payload();
  document.getElementById('json').textContent =
    Object.keys(p).length ? JSON.stringify(p, null, 1) : '{}   nothing changed yet';
  for (const k in H) {
    const row = ROWS.get(k);   // NOT getElementById + CSS.escape: ids match
                               // literally, and escaping the dots breaks it
    if (!row) continue;
    row.classList.toggle('on', !same(state[k], H[k].default));
    row.classList.toggle('sel', sel === k);
    row.querySelectorAll('input').forEach((inp, i) => {
      if (document.activeElement !== inp)
        inp.value = H[k].kind === 'scalar' ? state[k] : flat(state[k])[i]; });
  }
  buttons();
}

// ---- side panel ----------------------------------------------------------
const ROWS = new Map();

function panel() {
  const lay = document.getElementById('layers');
  for (const name of ['boxes','nodes','labels','flows']) {
    const b = document.createElement('button');
    b.textContent = name; b.className = 'on';
    b.onclick = () => { vis[name] = !vis[name]; b.classList.toggle('on', vis[name]); render(); };
    lay.append(b);
  }
  const groups = {};
  for (const k in H) (groups[k.split('.')[0]] ||= []).push(k);
  const host = document.getElementById('panel');
  for (const g in groups) {
    const d = document.createElement('div'); d.className = 'grp';
    d.innerHTML = '<h2>' + g + '</h2>';
    for (const k of groups[g]) {
      const h = H[k], row = document.createElement('div');
      row.className = 'row'; row.id = 'row_' + k; ROWS.set(k, row);
      row.onclick = ev => { if (ev.target.tagName !== 'INPUT') { sel = k; render(); } };
      const lb = document.createElement('label'); lb.textContent = h.label; row.append(lb);
      if (h.kind === 'path') {
        const n = document.createElement('span');
        n.style.cssText = 'color:#7c8593;font:10px ui-monospace,monospace';
        n.textContent = state[k].length + 'pt'; row.append(n);
      } else {
        flat(state[k]).forEach((num, i) => {
          const inp = document.createElement('input');
          inp.type = 'number'; inp.value = num;
          inp.onfocus = () => snapshot();
          inp.oninput = () => { const val = parseFloat(inp.value); if (isNaN(val)) return;
            if (h.kind === 'scalar') state[k] = val;
            else { const a = flat(state[k]).slice(); a[i] = val; state[k] = a; }
            render(); };
          row.append(inp);
        });
      }
      d.append(row);
    }
    host.append(d);
  }
}

// ---- live preview --------------------------------------------------------
// Only reachable when served by serve.py. Opened straight off disk (file://)
// there is no renderer to ask, so the buttons disable themselves and say why
// rather than failing silently when clicked.
const LIVE = location.protocol.startsWith('http');
const note = document.getElementById('srvnote');
function setNote(msg, cls) { note.textContent = msg; note.className = 'hint ' + (cls || ''); }
if (!LIVE) {
  document.getElementById('refresh').disabled = true;
  document.getElementById('save').disabled = true;
  document.getElementById('offline').classList.add('show');
  setNote('', '');
} else {
  setNote('Refresh re-renders with your changes. Save writes overrides.json.', '');
}

async function post(path, body) {
  const r = await fetch(path, {method:'POST', headers:{'Content-Type':'application/json'},
                               body: JSON.stringify(body)});
  const j = await r.json().catch(() => ({error:'bad response'}));
  if (!r.ok) throw new Error(j.error || ('HTTP ' + r.status));
  return j;
}

// A render round-trip takes a second or two, so changes are debounced and only
// ONE request is ever in flight. Later edits during a render collapse into a
// single follow-up, and a stale response is discarded by sequence number --
// otherwise fast dragging would queue a backlog and land an out-of-date image.
let renderSeq = 0, renderBusy = false, renderPending = false, debounceTimer = null;

function scheduleAuto() {
  if (!LIVE || !document.getElementById('auto').checked) return;
  clearTimeout(debounceTimer);
  setNote('change pending…', 'busy');
  debounceTimer = setTimeout(doRender, 450);
}

async function doRender() {
  if (renderBusy) { renderPending = true; return; }
  renderBusy = true;
  const seq = ++renderSeq;
  const btn = document.getElementById('refresh');
  btn.disabled = true; setNote('rendering…', 'busy');
  try {
    const j = await post('/render', {overrides: payload(), style: currentStyle});
    if (!j || !j.png) throw new Error('empty render response');
    if (seq === renderSeq) {                    // ignore an overtaken response
      BACKDROPS[currentStyle] = {png: j.png, bg: j.bg || '#ffffff'};
      setStyle(currentStyle);
      const c = Object.keys(payload()).length;
      setNote('preview live — ' + c + ' override' + (c === 1 ? '' : 's') + ' applied', 'ok');
    }
  } catch (e) {
    if (seq === renderSeq) setNote('render failed: ' + e.message, 'warn');
  } finally {
    renderBusy = false; btn.disabled = false;
    if (renderPending) { renderPending = false; doRender(); }
  }
}

document.getElementById('refresh').onclick = doRender;
document.getElementById('auto').onchange = e => {
  if (e.target.checked) scheduleAuto();
  else { clearTimeout(debounceTimer); setNote('auto-refresh off', ''); }
};
document.getElementById('save').onclick = async () => {
  const b = document.getElementById('save');
  b.disabled = true;
  try {
    const j = await post('/save', {overrides: payload()});
    setNote('saved ' + j.count + ' override' + (j.count === 1 ? '' : 's') +
            ' — now run ./build.sh', 'ok');
  } catch (e) { setNote('save failed: ' + e.message, 'warn'); }
  b.disabled = false;
};

document.getElementById('undo').onclick = undo;
document.getElementById('redo').onclick = redo;
document.getElementById('dl').onclick = () => {
  const b = new Blob([JSON.stringify(payload(), null, 2) + '\n'], {type:'application/json'});
  const a = document.createElement('a');
  a.href = URL.createObjectURL(b); a.download = 'overrides.json'; a.click(); };
document.getElementById('copy').onclick = async () => {
  await navigator.clipboard.writeText(JSON.stringify(payload(), null, 2));
  const b = document.getElementById('copy'); b.textContent = 'Copied';
  setTimeout(() => b.textContent = 'Copy to clipboard', 1200); };
document.getElementById('reset').onclick = () => { snapshot();
  for (const k in H) state[k] = clone(H[k].default); sel = null; render(); };
svg.addEventListener('pointerdown', e => { if (e.target === svg) { sel = null; render(); } });

document.querySelectorAll('#styles button').forEach(b =>
  b.onclick = () => setStyle(b.dataset.s));
// ?style= wins over the remembered choice, so ./edit.sh sketch lands you
// on the render you asked for.
let start = new URLSearchParams(location.search).get('style');
if (!start) { try { start = localStorage.getItem('flowgif.style'); } catch (_) {} }
start = start || 'flat';
setStyle(BACKDROPS[start] ? start : 'flat');

panel(); render(); buttons();
</script>
"""


def main():
    warm_up()
    handles = {}
    for key, h in ov.HANDLES.items():
        handles[key] = dict(kind=h["kind"], label=h["label"],
                            value=_jsonable(h["value"]),
                            default=_jsonable(h["default"]))
        # offsets resolve against another handle, and sizes pair with a grip;
        # both need their partner key on the client side
        for extra in ("anchor_key", "size_key"):
            if h.get(extra):
                handles[key][extra] = h[extra]

    backdrops = {}
    for style in ("flat", "sketch"):
        png, bg = render_backdrop(style)
        backdrops[style] = dict(png=png, bg=bg)
        print(f"  rendered {style} backdrop ({len(png) // 1024} KB base64)")

    html = (HTML
            .replace("__BACKDROPS__", json.dumps(backdrops))
            .replace("__HANDLES__", json.dumps(handles))
            .replace("__W__", str(L.W))
            .replace("__H__", str(L.H)))
    out = os.path.join(HERE, "editor.html")
    with open(out, "w") as fh:
        fh.write(html)
    print(f"{len(handles)} movable handles, both styles -> {out}")
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
