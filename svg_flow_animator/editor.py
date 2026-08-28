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
        # An offset is a delta from another handle. Without the anchor the
        # editor cannot resolve it to a position at all, so it would have no
        # drag target -- the handle would silently not exist on the canvas.
        if h.get("anchor_key") in handles:
            entry["anchor_key"] = h["anchor_key"]
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
  .segv.sel { stroke:#ffd479; opacity:1; stroke-width:3.5; }
  .tag  { font:10px sans-serif; fill:#1b1f24; paint-order:stroke; stroke:#fff;
          stroke-width:3px; pointer-events:none; }
  /* The rubber band. `fill:none`, and emphatically NOT `fill:transparent`: a
     transparent PAINT is still hit-testable, so a band stretched across the
     canvas would sit over every handle it just selected and swallow the
     pointer events aimed at them. Stroke only, and inert either way. */
  .band { fill:none; stroke:#ffd479; stroke-width:1.5; stroke-dasharray:4 3;
          pointer-events:none; }
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
      <b>Drag empty canvas</b> to rubber-band a group, then drag any one of
      them to move all of them.<br>
      <b>Shift-click</b> adds or removes &middot; <b>Esc</b> clears.<br>
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

// ---- offsets -------------------------------------------------------------
// An "offset" handle stores a DELTA from another handle, never a position, so
// a label stays attached to the thing it names however far that thing is
// dragged. Everything on the canvas needs the resolved absolute point;
// everything saved needs the delta.
const absXY = (k, depth) => {
  const h = H[k];
  if (!h || h.kind !== 'offset') return state[k];
  const d = depth || 0;
  // A malformed registry could anchor an offset to itself. Bail rather than
  // recurse forever -- a hung page says nothing about why.
  if (d > 8) return state[k];
  const a = (h.anchor_key && H[h.anchor_key]) ? absXY(h.anchor_key, d + 1) : [0, 0];
  return [a[0] + state[k][0], a[1] + state[k][1]];
};
const anchorXY = k => { const a = H[k].anchor_key;
  return (a && H[a]) ? absXY(a) : [0, 0]; };

// anchor key -> the offsets riding on it, so dragging a node drags its labels
// in real time rather than only snapping into place on release.
const DEPS = {};
for (const k in H) if (H[k].kind === 'offset' && H[k].anchor_key)
  (DEPS[H[k].anchor_key] ||= []).push(k);

// ---- selection -----------------------------------------------------------
// `selSet` is every selected handle; `sel` is the primary one, whose name gets
// drawn on the canvas. `sel` is always a member of `selSet` or null.
let sel = null;
const selSet = new Set();
function selectOnly(k) { selSet.clear(); if (k) selSet.add(k); sel = k || null; }
function selectAdd(k) { if (k) { selSet.add(k); sel = k; } }
function clearSel() { selSet.clear(); sel = null; }

// key -> the function that repositions that handle's SVG nodes in place.
// Rebuilt by every render, because the nodes are. A group move needs to touch
// handles other than the one under the pointer, and re-rendering to do it
// would destroy the element the gesture is attached to.
let PLACERS = new Map();
function placeFrom(k, seen) {
  seen = seen || new Set();
  if (seen.has(k)) return;
  seen.add(k);
  const p = PLACERS.get(k);
  if (p) p();
  for (const d of (DEPS[k] || [])) placeFrom(d, seen);
}

// ---- geometry helpers ----------------------------------------------------
function toSvg(evt) { const r = svg.getBoundingClientRect();
  return [(evt.clientX - r.left) * W / r.width, (evt.clientY - r.top) * HH / r.height]; }
const snap = (v, e) => e.shiftKey ? Math.round(v / 5) * 5 : Math.round(v * 10) / 10;
const snapd = (d, e) => e.shiftKey ? Math.round(d / 5) * 5 : Math.round(d * 10) / 10;

// ---- group move ----------------------------------------------------------
// A copy of the selected geometry, taken once at the start of a gesture. Every
// move re-derives from it rather than accumulating: pointer deltas that are
// each rounded and then added drift away from the cursor.
const baseOf = set => { const b = {};
  for (const k of set) if (H[k] && H[k].kind !== 'scalar') b[k] = clone(state[k]);
  return b; };

function translate(base, dx, dy) {
  // Does this handle's ABSOLUTE position shift by (dx, dy)? An offset rides
  // its anchor, so it moves whenever the anchor moves even though nothing in
  // its own stored value changes -- and that is true however long the chain of
  // anchors is, and whether or not the intermediate links are selected.
  const moves = (k, seen) => {
    const h = H[k];
    if (!h || h.kind === 'scalar') return false;
    if (k in base) return true;
    if (h.kind !== 'offset') return false;
    seen = seen || new Set();
    if (seen.has(k)) return false;
    seen.add(k);
    return moves(h.anchor_key, seen);
  };
  for (const k in base) {
    const h = H[k], b = base[k];
    if (h.kind === 'rect') state[k] = [b[0] + dx, b[1] + dy, b[2], b[3]];
    else if (h.kind === 'path') state[k] = b.map(p => [p[0] + dx, p[1] + dy]);
    else if (h.kind === 'offset')
      // THE one that goes wrong quietly. Marquee a node together with the
      // label anchored to it and the label is ALREADY carried along by the
      // anchor; adding the delta to its own stored value as well displaces it
      // twice, and the label drifts off its node a little more on every drag.
      // Its delta is only touched when the anchor is standing still.
      state[k] = moves(h.anchor_key) ? b.slice() : [b[0] + dx, b[1] + dy];
    else state[k] = [b[0] + dx, b[1] + dy];
  }
  for (const k in base) placeFrom(k);
}

function drag(node, key, onMove, groupable) {
  node.addEventListener('pointerdown', e => {
    if (e.button !== 0) return;
    e.preventDefault(); e.stopPropagation();
    // Resize grips are not `groupable`: they change a size, not a position,
    // and must neither join a selection nor drag one around.
    if (groupable) {
      if (e.shiftKey && selSet.has(key)) {
        // Shift toggles. Having just dropped it out of the selection there is
        // nothing here to drag, so the gesture ends.
        selSet.delete(key);
        if (sel === key) sel = null;
        markSelection(); sync(); return;
      }
      if (e.shiftKey) selectAdd(key);
      else if (!selSet.has(key)) selectOnly(key);
      else sel = key;
    } else if (selSet.size <= 1) {
      // A grip still takes the selection when there is no group to disturb, so
      // its panel row highlights the way it always has. Once a group has been
      // assembled, grazing a corner grip must not throw it away.
      selectOnly(key);
    }
    try { node.setPointerCapture(e.pointerId); } catch (_) {}
    const group = groupable && selSet.size > 1 && selSet.has(key);
    const origin = toSvg(e);
    const base = group ? baseOf(selSet) : null;
    let took = false;
    const move = ev => {
      // One snapshot per gesture, taken on the first real movement. The whole
      // group move is then a single undo step, and a shift-click that only
      // changes the selection leaves no empty entry behind to undo.
      if (!took) { took = true; snapshot(); }
      const [x, y] = toSvg(ev);
      if (group) translate(base, snapd(x - origin[0], ev), snapd(y - origin[1], ev));
      else onMove(snap(x, ev), snap(y, ev));
      sync();
    };
    const up = () => { node.removeEventListener('pointermove', move);
                       node.removeEventListener('pointerup', up); render(); };
    node.addEventListener('pointermove', move);
    node.addEventListener('pointerup', up);
    // Deliberately NOT render() here. Re-rendering to show the new selection
    // rebuilds the whole overlay, which destroys `node` in the middle of the
    // gesture and takes the two listeners just attached to it with it -- the
    // pointermove never fires again and nothing can be dragged at all. Handles
    // are moved IN PLACE while dragging (`placeFrom` / each `place()` below);
    // the full re-render happens once, on release.
    markSelection();
  });
}

function markSelection() {
  document.querySelectorAll('#ov .dot, #ov .rcv, #ov .segv').forEach(n =>
    n.classList.toggle('sel', selSet.has(n.dataset.k)));
  rows.forEach((row, k) => row.classList.toggle('sel', selSet.has(k)));
}

// ---- render --------------------------------------------------------------
function render() {
  svg.textContent = '';
  const tags = [], placers = new Map();

  // A handle on a hidden layer must not stay selected: a later group move
  // would shift things that are nowhere on screen to account for themselves.
  for (const k of Array.from(selSet)) if (!H[k] || !shown(k)) selSet.delete(k);
  if (sel && !selSet.has(sel)) sel = null;

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
    placers.set(k, place);
    drag(grab, k, (x, y) => { const w = state[k][2], h = state[k][3];
      state[k] = [Math.round(x - w/2), Math.round(y - h/2), w, h]; placeFrom(k); }, true);
    drag(z, k, (x, y) => { const q = state[k];
      state[k] = [q[0], q[1], Math.max(40, Math.round(x - q[0])),
                  Math.max(30, Math.round(y - q[1]))]; place(); }, false);
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
    placers.set(k, place);
    for (let i = 0; i < v.length - 1; i++) {
      const a = {x1:v[i][0], y1:v[i][1], x2:v[i+1][0], y2:v[i+1][1]};
      const hit = el('line', Object.assign({class:'segh'}, a));
      const vis_ = el('line', Object.assign({class:'segv'}, a));
      // The visible segment carries the key so a selected connector lights up
      // along its whole length, not just at its vertices.
      vis_.dataset.k = k;
      hit.addEventListener('dblclick', ev => { const [x, y] = toSvg(ev); snapshot();
        const q = state[k];
        state[k] = q.slice(0, i+1).concat([[Math.round(x), Math.round(y)]], q.slice(i+1));
        selectOnly(k); render(); });
      segs.push([hit, vis_]); svg.append(hit, vis_);
    }
    v.forEach((p, i) => {
      const hit = el('circle', {cx:p[0], cy:p[1], r:12, class:'hit'});
      const dot = el('circle', {cx:p[0], cy:p[1], r:5.5, class:'dot vert'});
      dot.dataset.k = k;
      drag(hit, k, (x, y) => { state[k][i] = [x, y]; place(); }, true);
      hit.addEventListener('contextmenu', ev => { ev.preventDefault();
        if (state[k].length > 2) { snapshot(); state[k].splice(i, 1); render(); } });
      verts.push([hit, dot]); svg.append(hit, dot);
    });
  }

  // points and offsets last -- smallest targets on top
  for (const k in H) {
    const kind = H[k].kind;
    if ((kind !== 'point' && kind !== 'offset') || !shown(k)) continue;
    const v = absXY(k);
    const hit = el('circle', {cx:v[0], cy:v[1], r:13, class:'hit'});
    const dot = el('circle', {cx:v[0], cy:v[1], r:6,
      class:'dot ' + (H[k].layer === 'labels' ? 'label' : 'node')});
    dot.dataset.k = k;

    // A point that names a size scalar gets a resize grip on its corner, so an
    // icon can be scaled where it sits instead of in a numeric field.
    const sk = H[k].size_key;
    const grip = sk ? el('rect', {width:11, height:11, class:'rz'}) : null;
    const place = () => { const q = absXY(k);
      for (const n of [hit, dot]) { n.setAttribute('cx', q[0]); n.setAttribute('cy', q[1]); }
      if (grip) { const s = state[sk] / 2;
        grip.setAttribute('x', q[0] + s - 5.5); grip.setAttribute('y', q[1] + s - 5.5); } };
    placers.set(k, place);

    drag(hit, k, (x, y) => {
      // An offset is stored as a delta, so a dropped absolute position has to
      // be converted back against its anchor. Writing the position straight in
      // would detach the label from what it names.
      if (kind === 'offset') { const a = anchorXY(k);
        state[k] = [Math.round((x - a[0]) * 10) / 10,
                    Math.round((y - a[1]) * 10) / 10]; }
      else state[k] = [x, y];
      placeFrom(k); }, true);
    if (grip) drag(grip, sk, (x, y) => {
      const q = absXY(k);
      state[sk] = Math.max(8, Math.round(2 * Math.max(Math.abs(x - q[0]),
                                                      Math.abs(y - q[1]))));
      place(); }, false);
    place();
    svg.append(hit, dot);
    if (grip) svg.append(grip);
    if (sel === k) tags.push([v[0] + 11, v[1] - 9, H[k].label]);
  }

  PLACERS = placers;
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
    row.classList.toggle('sel', selSet.has(k));
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
      row.onclick = ev => { if (ev.target.tagName === 'INPUT') return;
        ev.shiftKey ? selectAdd(k) : selectOnly(k); render(); };
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
  for (const k in H) state[k] = clone(H[k].default); clearSel(); render(); };

// ---- rubber band ---------------------------------------------------------
// Drag from empty canvas to enclose a group; shift keeps whatever was already
// selected. Scalars are excluded throughout -- they are numbers, not
// positions, they have no canvas handle to enclose, and translating one would
// resize a thing rather than move it.
const inside = (p, r) => p[0] >= r[0] && p[0] <= r[2] && p[1] >= r[1] && p[1] <= r[3];

function enclosed(r) {
  const out = [];
  for (const k in H) {
    const h = H[k];
    if (h.kind === 'scalar' || !shown(k)) continue;
    if (h.kind === 'path') {
      // A connector joins only when the WHOLE line is inside. Taking one whose
      // far end is outside would shear the diagram: the line would translate
      // away from the node it is still attached to.
      if (state[k].length && state[k].every(p => inside(p, r))) out.push(k);
    } else if (h.kind === 'rect') {
      const v = state[k];
      if (inside([v[0] + v[2] / 2, v[1] + v[3] / 2], r)) out.push(k);
    } else if (inside(absXY(k), r)) out.push(k);
  }
  return out;
}

svg.addEventListener('pointerdown', e => {
  // Every handle's own listener calls stopPropagation, so reaching here at all
  // means the press landed on bare canvas.
  if (e.button !== 0 || e.target !== svg) return;
  e.preventDefault();
  const keep = e.shiftKey ? new Set(selSet) : new Set();
  const [x0, y0] = toSvg(e);
  const band = el('rect', {class:'band', x:x0, y:y0, width:0, height:0});
  svg.append(band);
  try { svg.setPointerCapture(e.pointerId); } catch (_) {}
  let moved = false;
  const move = ev => {
    const [x, y] = toSvg(ev);
    if (Math.abs(x - x0) > 2 || Math.abs(y - y0) > 2) moved = true;
    const r = [Math.min(x0, x), Math.min(y0, y), Math.max(x0, x), Math.max(y0, y)];
    band.setAttribute('x', r[0]); band.setAttribute('y', r[1]);
    band.setAttribute('width', r[2] - r[0]); band.setAttribute('height', r[3] - r[1]);
    selSet.clear();
    for (const k of keep) selSet.add(k);
    for (const k of enclosed(r)) selSet.add(k);
    // Class toggling only. render() here would delete the band, and the svg
    // element the gesture is attached to keeps its listeners either way --
    // but the band would vanish the moment the selection first changed.
    markSelection();
  };
  const up = () => {
    svg.removeEventListener('pointermove', move);
    svg.removeEventListener('pointerup', up);
    band.remove();
    // A click that never moved is "clear the selection" -- or, with shift, a
    // deliberate no-op rather than a wipe of what was being assembled.
    if (!moved) { selSet.clear(); for (const k of keep) selSet.add(k); }
    sel = selSet.size === 1 ? selSet.values().next().value : null;
    render();
  };
  svg.addEventListener('pointermove', move);
  svg.addEventListener('pointerup', up);
});

addEventListener('keydown', e => {
  if (e.key !== 'Escape' || !selSet.size) return;
  if (['INPUT','TEXTAREA'].includes(document.activeElement.tagName)) return;
  clearSel(); render();
});

panel();
let first = Object.keys(BACKDROPS)[0];
try { first = localStorage.getItem('sfa.view') || first; } catch (_) {}
setView(BACKDROPS[first] ? first : Object.keys(BACKDROPS)[0]);
render(); buttons();
</script>
"""
