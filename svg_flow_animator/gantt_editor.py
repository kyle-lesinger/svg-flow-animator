"""
A browser editor for a Gantt chart's dates: type them, or drag the bars.

    from svg_flow_animator import gantt_editor, serve

    dates, draft = gantt_editor.load("schedule.json")
    chart = ...                      # a gantt.Gantt built from those dates
    gantt_editor.write_page("timeline.html", "my plan", back="editor.html")
    serve.serve(HERE, "module", size, page="timeline.html",
                routes=gantt_editor.routes(chart, "schedule.json", style))

The schedule is a small JSON file, readable and editable by hand:

    {
      "draft": true,
      "dates": {
        "samples": ["2026-11-09", "2026-11-20"],
        ...
      }
    }

The page asks POST /timeline/render for the picture and the bar geometry after
every change, and only POST /timeline/save writes the file, so nothing is saved
until Save. While a bar is being dragged only its outline moves; the chart is
re-rendered when it is dropped (GOTCHAS: re-rendering mid-drag destroys the drag).
"""
import json
from datetime import date

__all__ = ["load", "save", "routes", "write_page"]


def _parse(data):
    """{"dates": {key: [start, end]}, "draft": bool} -> (dates, draft)."""
    if not isinstance(data, dict) or not isinstance(data.get("dates"), dict):
        raise ValueError('expected {"dates": {key: [start, end]}, "draft": true|false}')
    dates = {}
    for k, v in data["dates"].items():
        if not (isinstance(v, (list, tuple)) and len(v) == 2):
            raise ValueError(f"{k}: expected [start, end]")
        dates[k] = (date.fromisoformat(v[0]), date.fromisoformat(v[1]))
    return dates, bool(data.get("draft", False))


def load(path):
    """(dates, draft) from a schedule file."""
    with open(path) as fh:
        return _parse(json.load(fh))


def save(path, dates, draft, order=None):
    """Write a schedule file, one row per line so it stays easy to edit by hand."""
    rows = [f'    {json.dumps(k)}: ["{dates[k][0].isoformat()}", '
            f'"{dates[k][1].isoformat()}"]' for k in (order or list(dates))]
    with open(path, "w") as fh:
        fh.write('{\n  "draft": %s,\n  "dates": {\n%s\n  }\n}\n'
                 % ("true" if draft else "false", ",\n".join(rows)))
    return path


def routes(chart, path, st):
    """
    POST endpoints for `serve.serve(routes=...)`. `chart` is the Gantt whose
    rows are being scheduled; `st` the style to preview in.
    """
    def view(dates, draft):
        c = chart.retimed(dates, draft)      # raises on a bad schedule
        return {"svg": c.frame_svg(None, st), "layout": c.editor_layout()}

    def state(_data):
        dates, draft = load(path)
        return dict(view(dates, draft), draft=draft)

    def render(data):
        return view(*_parse(data))

    def store(data):
        dates, draft = _parse(data)
        view(dates, draft)                   # refuse what could not be drawn
        save(path, dates, draft, order=[r["key"] for r in chart.rows])
        return {"ok": True, "path": path}

    return {"/timeline/state": state, "/timeline/render": render,
            "/timeline/save": store}


def write_page(path, title, back=None):
    """The editor page. `back` links to another editor served alongside."""
    link = f'<a href="{back}">Workflow layout editor</a>' if back else ""
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(PAGE.replace("__TITLE__", title).replace("__BACK__", link))
    return path


# A RAW string, like editor.HTML: a "\n" here must reach the browser as the two
# characters the JavaScript regex expects, not as a real newline (GOTCHAS).
PAGE = r"""<!doctype html>
<meta charset="utf-8">
<link rel="icon" href="data:,">
<title>timeline editor - __TITLE__</title>
<style>
  :root { --paper:#fdfcf8; --ink:#1e1e1e; --muted:#868e96; --line:#dee2e6; --accent:#1971c2; }
  * { box-sizing:border-box; }
  body { margin:0; font:14px/1.45 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
         background:var(--paper); color:var(--ink); }
  header { display:flex; align-items:center; gap:16px; flex-wrap:wrap; padding:12px 20px;
           border-bottom:1px solid var(--line); }
  h1 { font-size:16px; margin:0 8px 0 0; }
  .spacer { flex:1; }
  button { font:inherit; padding:6px 16px; border-radius:6px; border:1px solid var(--ink);
           background:var(--ink); color:#fff; cursor:pointer; }
  button:disabled { opacity:.35; cursor:default; }
  #status { color:var(--muted); }
  #status.err { color:#e03131; }
  main { padding:16px 20px 40px; display:grid; gap:16px; }
  .help { color:var(--muted); margin:0; max-width:80ch; }
  table { border-collapse:collapse; justify-self:start; }
  th, td { text-align:left; padding:4px 14px 4px 0; vertical-align:middle; }
  th { color:var(--muted); font-size:12px; font-weight:600; text-transform:uppercase;
       letter-spacing:.04em; }
  .chip { display:inline-block; width:12px; height:12px; border-radius:3px; margin-right:8px;
          vertical-align:-1px; }
  td small { display:block; margin-left:20px; color:var(--muted); }
  input[type=date] { font:inherit; padding:3px 6px; border:1px solid var(--line);
                     border-radius:6px; background:#fff; }
  #stage { position:relative; max-width:1600px; background:#fff; box-shadow:0 1px 14px #0002; }
  #chart svg { display:block; width:100%; height:auto; }
  #bars { position:absolute; inset:0; }
  .bar { position:absolute; cursor:grab; border-radius:6px; touch-action:none; }
  .bar:hover, .bar.drag { outline:2px dashed var(--accent); outline-offset:3px; }
  .bar.drag { cursor:grabbing; }
  .edge { position:absolute; top:0; bottom:0; width:12px; cursor:ew-resize; }
  .edge.l { left:-6px; }
  .edge.r { right:-6px; }
  #tip { position:absolute; display:none; pointer-events:none; transform:translate(-50%,-100%);
         background:var(--ink); color:#fff; font-size:12px; padding:3px 8px; border-radius:4px;
         white-space:nowrap; }
</style>
<header>
  <h1>Timeline: __TITLE__</h1>
  <label><input type="checkbox" id="draft"> Draft (stamps &ldquo;placeholder dates&rdquo;)</label>
  <span class="spacer"></span>
  <span id="status"></span>
  <button id="save" disabled>Save</button>
  __BACK__
</header>
<main>
  <p class="help">Drag a bar to move it in time, or drag either end to change its start or
  end. Or type the dates. Dates snap to whole days and both ends are inclusive.
  <b>Save</b> writes schedule.json; then run ./build.sh for the APNGs.</p>
  <table>
    <thead><tr><th>Task</th><th>Start</th><th>End</th><th>Days</th></tr></thead>
    <tbody id="rows"></tbody>
  </table>
  <div id="stage"><div id="chart"></div><div id="bars"></div><div id="tip"></div></div>
</main>
<script>
"use strict";
const $ = (id) => document.getElementById(id);
const DAY = 86400000;
let layout = null, dates = {}, dirty = false, seq = 0, drag = null;

// Dates are whole days in UTC, so no timezone can shift one by a day.
const parse = (s) => new Date(s + "T00:00:00Z");
const fmt = (d) => d.toISOString().slice(0, 10);
const shift = (s, n) => fmt(new Date(parse(s).getTime() + n * DAY));
const span = (a, b) => Math.round((parse(b) - parse(a)) / DAY) + 1;

function status(msg, err) {
  $("status").textContent = msg;
  $("status").className = err ? "err" : "";
}

function setDirty(v) {
  dirty = v;
  $("save").disabled = !v;
  if (v) status("unsaved changes");
}

async function post(path, body) {
  const r = await fetch(path, { method: "POST", headers: { "Content-Type": "application/json" },
                                body: JSON.stringify(body) });
  let j = {};
  try { j = await r.json(); } catch (e) { /* not JSON: reported below */ }
  if (!r.ok || j.error) throw new Error(j.error || ("HTTP " + r.status));
  return j;
}

const payload = () => ({ dates: dates, draft: $("draft").checked });

function show(j) {
  layout = j.layout;
  $("chart").innerHTML = j.svg;
  dates = {};
  for (const row of layout.rows) dates[row.key] = [row.start, row.end];
  table();
  bars();
}

async function render() {
  const mine = ++seq;
  try {
    const j = await post("/timeline/render", payload());
    if (mine !== seq || drag) return;   // a newer edit is on its way, or a drag is live
    show(j);
    if (dirty) status("unsaved changes");
  } catch (e) { status(e.message, true); }
}

function table() {
  const tb = $("rows");
  tb.textContent = "";
  for (const row of layout.rows) {
    const tr = document.createElement("tr");
    const task = document.createElement("td");
    const chip = document.createElement("span");
    chip.className = "chip";
    chip.style.background = row.stroke;
    task.append(chip, row.label);
    if (row.detail) {
      const s = document.createElement("small");
      s.textContent = row.detail.replace(/\n/g, " ");
      task.append(s);
    }
    tr.append(task);
    for (const i of [0, 1]) {
      const td = document.createElement("td");
      const inp = document.createElement("input");
      inp.type = "date";
      inp.id = "d-" + row.key + "-" + i;
      inp.value = dates[row.key][i];
      inp.addEventListener("change", () => {
        if (!inp.value) return;
        dates[row.key][i] = inp.value;
        setDirty(true);
        render();
      });
      td.append(inp);
      tr.append(td);
    }
    const n = document.createElement("td");
    n.id = "n-" + row.key;
    n.textContent = span(dates[row.key][0], dates[row.key][1]);
    tr.append(n);
    tb.append(tr);
  }
}

const scale = () => $("stage").clientWidth / layout.size[0];

function place(el, x, w, y, h, k) {
  el.style.left = (x * k) + "px";
  el.style.width = Math.max(4, w * k) + "px";
  el.style.top = (y * k) + "px";
  el.style.height = (h * k) + "px";
}

function bars() {
  const box = $("bars");
  box.textContent = "";
  const k = scale();
  for (const row of layout.rows) {
    const el = document.createElement("div");
    el.className = "bar";
    el.dataset.key = row.key;
    el.title = "drag to move; drag an end to resize";
    place(el, row.bar[0], row.bar[2], row.bar[1], row.bar[3], k);
    for (const side of ["l", "r"]) {
      const e = document.createElement("div");
      e.className = "edge " + side;
      e.dataset.mode = side === "l" ? "start" : "end";
      el.append(e);
    }
    el.addEventListener("pointerdown", (ev) => begin(ev, row, el));
    box.append(el);
  }
}

function begin(ev, row, el) {
  ev.preventDefault();
  el.setPointerCapture(ev.pointerId);
  drag = { row: row, el: el, mode: ev.target.dataset.mode || "move", x0: ev.clientX,
           from: dates[row.key].slice(), k: scale(), days: 0 };
  el.classList.add("drag");
  el.addEventListener("pointermove", move);
  el.addEventListener("pointerup", end);
  el.addEventListener("pointercancel", end);
}

function proposed(d) {
  // The dates a drag of d days gives; a bar never ends before it starts.
  let [s, e] = drag.from;
  if (drag.mode !== "end") s = shift(s, d);
  if (drag.mode !== "start") e = shift(e, d);
  if (parse(e) < parse(s)) {
    if (drag.mode === "start") s = e; else e = s;
  }
  return [s, e];
}

function tip(el, text) {
  const t = $("tip");
  t.textContent = text;
  t.style.display = "block";
  t.style.left = (el.offsetLeft + el.offsetWidth / 2) + "px";
  t.style.top = (el.offsetTop - 8) + "px";
}

function move(ev) {
  if (!drag) return;
  const d = Math.round((ev.clientX - drag.x0) / drag.k / layout.px_per_day);
  if (d === drag.days) return;
  drag.days = d;
  const [s, e] = proposed(d);
  const [x, y, , h] = drag.row.bar;
  const ppd = layout.px_per_day;
  place(drag.el, x + (parse(s) - parse(drag.from[0])) / DAY * ppd, span(s, e) * ppd,
        y, h, drag.k);
  $("d-" + drag.row.key + "-0").value = s;
  $("d-" + drag.row.key + "-1").value = e;
  $("n-" + drag.row.key).textContent = span(s, e);
  tip(drag.el, s + "  to  " + e);
}

function end(ev) {
  if (!drag) return;
  const el = drag.el;
  if (el.hasPointerCapture(ev.pointerId)) el.releasePointerCapture(ev.pointerId);
  el.classList.remove("drag");
  el.removeEventListener("pointermove", move);
  el.removeEventListener("pointerup", end);
  el.removeEventListener("pointercancel", end);
  $("tip").style.display = "none";
  const moved = drag.days !== 0;
  if (moved) dates[drag.row.key] = proposed(drag.days);
  drag = null;
  if (moved) {
    setDirty(true);
    render();
  }
}

$("draft").addEventListener("change", () => { setDirty(true); render(); });
$("save").addEventListener("click", async () => {
  try {
    const j = await post("/timeline/save", payload());
    setDirty(false);
    status("Saved " + j.path.split("/").pop() + ". Run ./build.sh to make the APNGs.");
  } catch (e) { status(e.message, true); }
});
window.addEventListener("resize", () => { if (layout && !drag) bars(); });
window.addEventListener("beforeunload", (e) => {
  if (dirty) { e.preventDefault(); e.returnValue = ""; }
});

(async () => {
  try {
    const j = await post("/timeline/state", {});
    $("draft").checked = j.draft;
    show(j);
  } catch (e) {
    status("No server: " + e.message + ". Open this page through ./edit.sh.", true);
  }
})();
</script>
"""
