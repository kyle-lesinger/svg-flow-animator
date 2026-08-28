"""
A browser editor for whatever a project registered through `overrides`.

Nothing in here knows about any particular diagram. It takes three things:

    handles    the registry `overrides` filled in (key -> kind/default/value)
    backdrop   a callback producing the current picture to trace over
    size       the canvas the coordinates are expressed in

and emits one self-contained HTML file. Drag a handle, download
`overrides.json`, rebuild. A new `ov.point(...)` anywhere in a layout shows up
in the editor on the next run without touching this module.

    from svg_flow_animator import editor, overrides as ov

    ov.use("overrides.json")
    import layout                       # importing populates ov.HANDLES
    layout.warm_up()                    # see the gotcha below

    editor.build("editor.html", (960, 540), layout.scene_svg, title="my diagram")

`backdrop` is a CALLBACK rather than a picture so the backdrop is generated
after the overrides are loaded -- which is what makes it agree with the handles
drawn on top of it. It may return:

    bytes                a PNG
    str                  an SVG document, rasterised here with rsvg-convert
    (bytes|str, colour)  either of those, plus the page colour behind it

Pass a *dict* of them and the editor grows a switcher between named views:

    editor.build(..., backdrop={"Flat": flat_svg, "Hand-drawn": sketch_svg})

The geometry is shared across views, so the handles never move when you switch
-- only the picture behind them. That is the whole point: one set of overrides
driving several renders of the same diagram.

THE GOTCHA: `ov.path()` only registers a handle when the function owning it is
actually called, and connector functions normally run during frame generation.
A project must call them once up front or the editor will offer no bendable
lines at all -- which is most of what it is for.
"""
import base64
import json
import os
import shutil
import subprocess

from . import overrides as _overrides

__all__ = ["build", "payload", "layer_of", "LAYER_ORDER"]

# Canvas layers, in draw order: boxes underneath, so their large hit areas
# never sit on top of the small things they contain.
LAYER_ORDER = ["boxes", "flows", "nodes", "labels"]


def layer_of(key, kind, label_prefix="label."):
    """
    Which toggleable layer a handle belongs to.

    Driven by KIND rather than by key naming, so a project gets sensible layers
    without having to adopt a prefix convention. The one convention honoured is
    `label_prefix`: a point whose key starts with it is a piece of text rather
    than a node, and gets its own colour and its own toggle. Scalars have no
    canvas handle at all -- they are panel fields -- so they get no layer.
    """
    if kind == "rect":
        return "boxes"
    if kind == "path":
        return "flows"
    if kind == "scalar":
        return ""
    return "labels" if label_prefix and key.startswith(label_prefix) else "nodes"


def payload(handles=None, label_prefix="label."):
    """The handle registry, reduced to something JSON will accept."""
    handles = _overrides.HANDLES if handles is None else handles
    out = {}
    for key, h in handles.items():
        entry = dict(kind=h["kind"], label=h.get("label") or key,
                     value=_jsonable(h["value"]),
                     default=_jsonable(h["default"]),
                     layer=layer_of(key, h["kind"], label_prefix))
        # A point may name a scalar that controls its size; the editor turns
        # that into a resize grip next to the move handle.
        if h.get("size_key") in handles:
            entry["size_key"] = h["size_key"]
        out[key] = entry
    return out


def _jsonable(v):
    if isinstance(v, (int, float)):
        return round(float(v), 4)
    if v and isinstance(v[0], (list, tuple)):
        return [[round(float(a), 2), round(float(b), 2)] for a, b in v]
    return [round(float(x), 2) for x in v]


def _one_backdrop(source, size, background, workdir, tag):
    """
    Normalise one backdrop callback's output to {"png": base64, "bg": colour}.

    A string is an SVG document, which has to be rasterised -- and written into
    `workdir` to do it, because librsvg resolves a relative `<image href>`
    against the SVG's OWN directory. Rasterising via a system temp dir would
    silently drop every sprite in the picture.
    """
    data = source() if callable(source) else source
    if isinstance(data, tuple):
        data, background = data
    if isinstance(data, bytes):
        return dict(png=base64.b64encode(data).decode(), bg=background)
    if shutil.which("rsvg-convert") is None:
        raise RuntimeError("rsvg-convert not found (brew install librsvg)")

    w, h = size
    svg_path = os.path.join(workdir, "_editor_backdrop_%s.svg" % tag)
    png_path = os.path.join(workdir, "_editor_backdrop_%s.png" % tag)
    try:
        with open(svg_path, "w") as fh:
            fh.write(data)
        subprocess.run(["rsvg-convert", "-w", str(int(w)), "-h", str(int(h)),
                        "-b", background, "-o", png_path, svg_path], check=True)
        with open(png_path, "rb") as fh:
            return dict(png=base64.b64encode(fh.read()).decode(), bg=background)
    finally:
        for stale in (svg_path, png_path):
            if os.path.exists(stale):
                os.remove(stale)


def build(out_path, size, backdrop, handles=None, title="layout",
          background="#ffffff", workdir=None, label_prefix="label."):
    """
    Write a standalone editor HTML file. Returns its path.

    out_path      where to write the HTML
    size          (w, h) of the coordinate space the handles live in
    backdrop      callable (or PNG bytes / SVG string), or a dict of them
                  keyed by the name to show on the switcher
    handles       defaults to `overrides.HANDLES`
    title         shown in the tab and the panel header
    background    page colour behind the backdrop, unless a callback returns
                  its own
    workdir       where to rasterise; defaults to out_path's directory, which
                  is where a project's asset hrefs already resolve
    label_prefix  key prefix that marks a handle as a text position
    """
    out_path = os.path.abspath(out_path)
    workdir = workdir or os.path.dirname(out_path)

    views = backdrop if isinstance(backdrop, dict) else {"view": backdrop}
    backdrops = {name: _one_backdrop(src, size, background, workdir, str(i))
                 for i, (name, src) in enumerate(views.items())}

    hs = payload(handles, label_prefix)
    layers = [name for name in LAYER_ORDER
              if any(v["layer"] == name for v in hs.values())]

    html = (HTML
            .replace("__BACKDROPS__", json.dumps(backdrops))
            .replace("__VIEWS__", json.dumps(list(views) if len(views) > 1 else []))
            .replace("__HANDLES__", json.dumps(hs))
            .replace("__LAYERS__", json.dumps(layers))
            .replace("__TITLE__", str(title))
            .replace("__W__", str(size[0]))
            .replace("__H__", str(size[1])))
    with open(out_path, "w") as fh:
        fh.write(html)
    return out_path


# The template is a RAW string, and it has to stay one. A "\n" written in a
# normal Python string here survives Python's own parsing as a REAL newline,
# lands mid-way through a JS string literal, and an unterminated literal takes
# the whole script down -- an editor that renders as a blank page with a single
# syntax error in the console. Raw string, so the two characters reach the
# browser as the escape the JS parser expects.
HTML = r"""<!doctype html>
<meta charset="utf-8">
<title>layout editor - __TITLE__</title>
<style>
  * { box-sizing:border-box; }
  body { margin:0; font:13px/1.45 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
         background:#1b1f24; color:#e6e9ee; display:flex; height:100vh; overflow:hidden;
         user-select:none; }
  #stage { flex:1; overflow:auto; padding:16px; }
  /* background-color is the ground under the backdrop, and it must be set in
     CSS, not only by setView(). Without it the canvas is transparent until a
     backdrop installs, so any failure to install one shows the dark page
     through and reads as "the editor came up black". */
  #wrap { position:relative; width:__W__px; height:__H__px; background-color:#fff;
          background-repeat:no-repeat; background-position:0 0;
          background-size:__W__px __H__px; box-shadow:0 2px 24px #0008; }
  #err  { position:absolute; inset:0; display:none; place-items:center; padding:24px;
          text-align:center; background:#fff; color:#b3261e; white-space:pre-line;
          font:12.5px/1.6 ui-monospace,SFMono-Regular,Menlo,monospace; }
  svg { position:absolute; inset:0; width:100%; height:100%; }
  aside { width:330px; background:#22272e; border-left:1px solid #333a44;
          display:flex; flex-direction:column; }
  aside h1 { font-size:13.5px; margin:0; padding:12px 14px; border-bottom:1px solid #333a44;
             font-weight:600; }
  #views { display:flex; gap:6px; padding:11px 14px 8px; }
  #views button { flex:1; padding:9px 6px; font-size:12.5px; background:#333a44; }
  #views button.on { background:#2f6feb; }
  #viewnote { margin:0; padding:0 14px 11px; font-size:10.5px; color:#7c8593;
              line-height:1.45; border-bottom:1px solid #333a44; }
  #viewnote b { color:#aab4c2; }
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
  /* A container is grabbed by its BORDER only.
     `fill:transparent` reads as harmless but is not: in SVG a transparent fill
     still RECEIVES POINTER EVENTS. A 550x640 container rect then swallows
     every click aimed at the nodes inside it and none of them can be picked up
     at all. `fill:none` plus a fat transparent stroke with
     `pointer-events:stroke` gives a comfortable grab band on the border and
     leaves the whole interior click-through. */
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
<div id="stage"><div id="wrap"><svg id="ov" viewBox="0 0 __W__ __H__"></svg>
  <div id="err"></div></div></div>
<aside>
  <h1>Layout editor &middot; <span style="color:#ffd479">__TITLE__</span></h1>
  <div id="views"></div>
  <p id="viewnote">Geometry is shared &mdash; whichever view you pick, the
     overrides you save apply to <b>all</b> of them.</p>
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
    <button id="dl">Download overrides.json</button>
    <button id="copy" class="ghost">Copy to clipboard</button>
    <button id="reset" class="ghost">Reset all to defaults</button>
  </footer>
</aside>
<script>
const H = __HANDLES__, LAYERS = __LAYERS__, W = __W__, HH = __H__;
const BACKDROPS = __BACKDROPS__, VIEWS = __VIEWS__;
const svg = document.getElementById('ov');
const NS = 'http://www.w3.org/2000/svg';
const el = (n, a) => { const e = document.createElementNS(NS, n);
  for (const k in a) e.setAttribute(k, a[k]); return e; };
const clone = o => JSON.parse(JSON.stringify(o));

let state = {};
for (const k in H) state[k] = clone(H[k].value);

// ---- backdrop views ------------------------------------------------------
// Several renders of the SAME geometry. Switching swaps only the picture --
// the handles are identical, which is what makes one overrides.json drive all
// of them.
function setView(name) {
  const b = BACKDROPS[name];
  const err = document.getElementById('err');
  if (!b || !b.png) {
    // Returning quietly here is how a missing backdrop used to present: an
    // empty canvas and no explanation anywhere. Say what is wrong instead.
    const have = Object.keys(BACKDROPS).join(', ') || '(none)';
    const msg = 'no backdrop for view "' + name + '"\nbackdrops in this file: ' + have;
    console.error('[editor] ' + msg.replace('\n', '  '));
    err.textContent = msg;
    err.style.display = 'grid';
    return;
  }
  err.style.display = 'none';
  const wrap = document.getElementById('wrap');
  wrap.style.backgroundImage = 'url(data:image/png;base64,' + b.png + ')';
  wrap.style.backgroundColor = b.bg;
  document.querySelectorAll('#views button').forEach(x =>
    x.classList.toggle('on', x.dataset.v === name));
  try { localStorage.setItem('sfa.view', name); } catch (_) {}
}

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
// The layer is decided in Python and shipped with the handle, so the two sides
// cannot disagree about what a given key is.
const vis = {};
for (const name of LAYERS) vis[name] = true;
const shown = k => H[k].layer === '' || vis[H[k].layer];
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
    // Deliberately NOT render() here. Re-rendering to show the new selection
    // rebuilds the whole overlay, which destroys `node` in the middle of the
    // gesture and takes the two listeners just attached to it with it -- the
    // pointermove never fires again and nothing can be dragged at all. Handles
    // are moved IN PLACE while dragging (each `place()` below); the full
    // re-render happens once, on release.
    markSelection();
  });
}

function markSelection() {
  document.querySelectorAll('#ov .dot, #ov .rcv').forEach(n =>
    n.classList.toggle('sel', n.dataset.k === sel));
  rows.forEach((row, k) => row.classList.toggle('sel', k === sel));
}

// ---- render --------------------------------------------------------------
function render() {
  svg.textContent = '';
  const tags = [];

  // boxes first, so everything else sits on top of them
  for (const k in H) {
    if (H[k].kind !== 'rect' || !shown(k)) continue;
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
      state[k] = [Math.round(x - w/2), Math.round(y - h/2), w, h]; place(); });
    drag(z, k, (x, y) => { const q = state[k];
      state[k] = [q[0], q[1], Math.max(40, Math.round(x - q[0])),
                  Math.max(30, Math.round(y - q[1]))]; place(); });
    svg.append(box, grab, z);
    tags.push([v[0] + 7, v[1] + 15, H[k].label]);
  }

  // connectors
  for (const k in H) {
    if (H[k].kind !== 'path' || !shown(k)) continue;
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

  // points last -- smallest targets on top
  for (const k in H) {
    if (H[k].kind !== 'point' || !shown(k)) continue;
    const v = state[k];
    const hit = el('circle', {cx:v[0], cy:v[1], r:13, class:'hit'});
    const dot = el('circle', {cx:v[0], cy:v[1], r:6,
      class:'dot ' + (H[k].layer === 'labels' ? 'label' : 'node')});
    dot.dataset.k = k;

    // A point that names a size scalar gets a resize grip on its corner, so an
    // icon can be scaled where it sits instead of in a numeric field.
    const sk = H[k].size_key;
    const grip = sk ? el('rect', {width:11, height:11, class:'rz'}) : null;
    const place = () => { const q = state[k];
      for (const n of [hit, dot]) { n.setAttribute('cx', q[0]); n.setAttribute('cy', q[1]); }
      if (grip) { const s = state[sk] / 2;
        grip.setAttribute('x', q[0] + s - 5.5); grip.setAttribute('y', q[1] + s - 5.5); } };

    drag(hit, k, (x, y) => { state[k] = [x, y]; place(); });
    if (grip) drag(grip, sk, (x, y) => {
      const q = state[k];
      state[sk] = Math.max(8, Math.round(2 * Math.max(Math.abs(x - q[0]),
                                                      Math.abs(y - q[1]))));
      place(); });
    place();
    svg.append(hit, dot);
    if (grip) svg.append(grip);
    if (sel === k) tags.push([v[0] + 11, v[1] - 9, H[k].label]);
  }

  for (const [x, y, t] of tags) { const e = el('text', {x, y, class:'tag'});
    e.textContent = t; svg.append(e); }
  markSelection(); sync();
}

const same = (a, b) => JSON.stringify(a) === JSON.stringify(b);
const flat = v => (typeof v === 'number') ? [v] : (Array.isArray(v[0]) ? v.flat() : v);

function payload() { const o = {};
  for (const k in H) if (!same(state[k], H[k].default)) o[k] = state[k];
  return o; }

// Panel rows live in a Map keyed by the handle key. They used to be looked up
// with getElementById('row_' + CSS.escape(k)), which never matches: an id is
// matched LITERALLY, so the backslashes CSS.escape adds for the dots in
// "box.stac" mean nothing is found and the panel silently stops tracking the
// canvas for every dotted key -- which is most of them.
const rows = new Map();

function sync() {
  const p = payload();
  document.getElementById('json').textContent =
    Object.keys(p).length ? JSON.stringify(p, null, 1) : '{}   nothing changed yet';
  for (const k in H) {
    const row = rows.get(k);
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
function panel() {
  const vhost = document.getElementById('views');
  for (const name of VIEWS) {
    const b = document.createElement('button');
    b.textContent = name; b.dataset.v = name;
    b.onclick = () => setView(name);
    vhost.append(b);
  }
  if (!VIEWS.length) {
    vhost.remove();
    document.getElementById('viewnote').remove();
  }

  const lay = document.getElementById('layers');
  for (const name of LAYERS) {
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
      row.className = 'row'; row.dataset.k = k; rows.set(k, row);
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

panel();
let first = Object.keys(BACKDROPS)[0];
try { first = localStorage.getItem('sfa.view') || first; } catch (_) {}
setView(BACKDROPS[first] ? first : Object.keys(BACKDROPS)[0]);
render(); buttons();
</script>
"""
