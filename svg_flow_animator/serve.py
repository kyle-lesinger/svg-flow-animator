"""
Live-preview server for a generated editor.

Without it, editing is: drag -> Download overrides.json -> move the file ->
rebuild -> look. With it the editor asks the project's real renderer for a new
backdrop after each change, and writes overrides.json straight into the
project.

    from svg_flow_animator import serve
    serve.serve(HERE, "gen_frames", (1600, 900))

Two endpoints:

  POST /render  {"overrides": {...}, "style": "flat"|"sketch"}
                -> {"png": "<base64>", "bg": "#ffffff"}
                Renders the scene with those overrides WITHOUT touching the
                project's overrides.json -- it is a preview, so it must have no
                side effects.

  POST /save    {"overrides": {...}}
                -> {"ok": true, "path": "...", "count": N}

THE MODULE CONTRACT. `module` is imported in a fresh subprocess, because a
layout resolves its geometry once at import time and a style backend is picked
once too. Two environment variables carry the request in:

    FLOWGIF_STYLE      the style to render, for `styles.select()`
    FLOWGIF_OVERRIDES  path of a scratch JSON file holding the candidate
                       overrides; the module must `ov.use()` it when set

and the module must define

    preview_svg(path) -> background colour

which writes the static scene as an SVG document to `path` and returns the
page colour behind it. `path` is always inside `project_dir`: librsvg refuses
an <image href> outside the referencing document's own directory, silently, so
a scene written to a temp dir loses every sprite. `preview_svg` is also where
sprites must be staged -- nothing else here will do it.
"""
import base64
import json
import os
import subprocess
import sys
import tempfile
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

__all__ = ["serve", "make_handler", "render_scene"]

MAX_BODY = 4 << 20          # a payload this big is a bug, not a layout
STYLES = ("flat", "sketch")


def render_scene(project_dir, module, canvas, overrides, style, min_png=0):
    """Render `module`'s scene with `overrides`. Returns (base64 png, bg)."""
    fd, ov_path = tempfile.mkstemp(suffix=".json", prefix="flowgif_ov_")
    with os.fdopen(fd, "w") as fh:
        json.dump(overrides, fh)
    # Inside the project, never tempdir -- see the module docstring.
    svg_path = os.path.join(project_dir, f"_preview_{style}.svg")
    png_path = os.path.join(project_dir, f"_preview_{style}.png")
    try:
        code = ("import sys; sys.path.insert(0, %r); import %s as M; "
                "print(M.preview_svg(%r))" % (project_dir, module, svg_path))
        env = dict(os.environ, FLOWGIF_STYLE=style, FLOWGIF_OVERRIDES=ov_path)
        proc = subprocess.run([sys.executable, "-c", code], env=env,
                              cwd=project_dir, capture_output=True, text=True)
        if proc.returncode != 0:
            raise RuntimeError(proc.stderr.strip()[-1200:] or "scene generation failed")
        # Only the LAST line is the colour; the module may print progress.
        lines = proc.stdout.strip().splitlines()
        bg = lines[-1].strip() if lines else "white"
        r = subprocess.run(["rsvg-convert", "-w", str(canvas[0]), "-h", str(canvas[1]),
                            "-b", bg, "-o", png_path, svg_path],
                           capture_output=True, text=True)
        if r.returncode != 0:
            raise RuntimeError(r.stderr.strip()[-1200:] or "rsvg-convert failed")
        size = os.path.getsize(png_path)
        if size < min_png:
            # Almost always the containment failure. Better to shout than to
            # hand back a picture with the artwork quietly missing.
            raise RuntimeError(
                f"render looks wrong: {size} bytes, under {min_png}. Sprites are "
                "probably not loading -- check they are staged below the project "
                "directory.")
        with open(png_path, "rb") as fh:
            return base64.b64encode(fh.read()).decode(), bg
    finally:
        for p in (ov_path, svg_path, png_path):
            try:
                os.remove(p)
            except OSError:
                pass


def make_handler(project_dir, module, canvas, min_png=0,
                 overrides_name="overrides.json"):
    """The request handler class, separate from `serve` so tests can bind it."""

    class Handler(SimpleHTTPRequestHandler):
        def __init__(self, *a, **kw):
            super().__init__(*a, directory=project_dir, **kw)

        def log_message(self, fmt, *args):
            # log_request and log_error pass different argument types (a request
            # line vs an HTTPStatus). Assuming a string raised TypeError inside
            # the handler thread, which aborted the response mid-flight and the
            # browser saw ERR_EMPTY_RESPONSE.
            try:
                line = fmt % args
            except Exception:
                line = " ".join(str(a) for a in args)
            if "POST" in line:
                sys.stderr.write("  %s\n" % line)

        def _json(self, code, payload):
            body = json.dumps(payload).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self):
            try:
                n = int(self.headers.get("Content-Length") or 0)
                if n <= 0 or n > MAX_BODY:
                    return self._json(400, {"error": "bad content length"})
                data = json.loads(self.rfile.read(n))
            except (ValueError, OSError) as exc:
                return self._json(400, {"error": f"unreadable request: {exc}"})

            overrides = data.get("overrides") if isinstance(data, dict) else None
            if not isinstance(overrides, dict):
                return self._json(400, {"error": "overrides must be an object"})

            route = self.path.rstrip("/")
            if route == "/render":
                style = data.get("style") if data.get("style") in STYLES else "flat"
                try:
                    png, bg = render_scene(project_dir, module, canvas, overrides,
                                           style, min_png)
                except Exception as exc:                   # surface it, don't swallow
                    return self._json(500, {"error": str(exc)})
                return self._json(200, {"png": png, "bg": bg})

            if route == "/save":
                path = os.path.join(project_dir, overrides_name)
                with open(path, "w") as fh:
                    json.dump(overrides, fh, indent=2, sort_keys=True)
                    fh.write("\n")
                return self._json(200, {"ok": True, "path": path,
                                        "count": len(overrides)})

            self._json(404, {"error": "no such endpoint"})

    return Handler


def serve(project_dir, module, canvas, port=None, min_png=0, page="editor.html"):
    """Serve `project_dir` with live preview until Ctrl-C."""
    project_dir = os.path.abspath(project_dir)
    port = int(port or os.environ.get("FLOWGIF_PORT", "8750"))
    srv = ThreadingHTTPServer(("127.0.0.1", port),
                              make_handler(project_dir, module, canvas, min_png))
    print(f"flowgif editor  ->  http://localhost:{port}/{page}")
    print("   POST /render  live preview   POST /save  write overrides.json")
    print("   Ctrl-C to stop", flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped")
