#!/usr/bin/env python3
"""
Live-preview server for the layout editor.

    python3 serve.py          # then open http://localhost:8750/editor.html

Without this, editing is: drag -> Download overrides.json -> move the file ->
rebuild -> look. With it, the editor can ask the real renderer for a new
backdrop and show you the actual result in a second or two, and can write
overrides.json straight into the project. No download, no file shuffling.

Two endpoints:

  POST /render  {"overrides": {...}, "style": "flat"|"sketch"}
                -> {"png": "<base64>", "bg": "#ffffff"}
                Renders the static scene with those overrides applied WITHOUT
                touching the project's overrides.json -- it is a preview, so it
                must not have side effects.

  POST /save    {"overrides": {...}}
                -> {"ok": true, "path": "...", "count": N}
                Writes overrides.json into the project for real.

Stdlib only. Ctrl-C to stop.
"""
import base64
import json
import os
import subprocess
import sys
import tempfile
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
PORT = int(os.environ.get("FLOWGIF_PORT", "8750"))
CANVAS = (1600, 900)
MAX_BODY = 4 << 20          # a payload this big is a bug, not a layout
# A full scene with all its logos renders to ~370KB. Losing the sprites drops it
# to ~108KB, so anything near that means they silently failed to load.
MIN_PLAUSIBLE_PNG = 200_000


def render_scene(overrides, style):
    """Render frame 0 with `overrides` applied, and return (base64 png, bg)."""
    fd, ov_path = tempfile.mkstemp(suffix=".json", prefix="flowgif_ov_")
    with os.fdopen(fd, "w") as fh:
        json.dump(overrides, fh)
    # These MUST live inside the project directory, not in tempdir. librsvg
    # refuses to load an <image href> outside the referencing document's own
    # directory tree, and does it SILENTLY -- exit code 0, no warning, the
    # logos simply do not draw. A scene rendered from /tmp cannot reach
    # <project>/frames/assets, so every sprite vanishes and you get a
    # plausible-looking but wrong preview.
    svg_path = os.path.join(HERE, f"_preview_{style}.svg")
    png_path = os.path.join(HERE, f"_preview_{style}.png")
    try:
        code = (
            "import sys; sys.path.insert(0, %r);"
            "import gen_frames as G;"
            # frame_svg() alone does not stage sprites -- main() does, and we
            # never call it. Without this the preview silently loses every logo.
            "G.stage_assets();"
            "from style import S;"
            "open(%r, 'w').write(G.frame_svg(0));"
            "print(S.bg)" % (HERE, svg_path)
        )
        env = dict(os.environ, FLOWGIF_STYLE=style, FLOWGIF_OVERRIDES=ov_path)
        proc = subprocess.run([sys.executable, "-c", code], env=env,
                              capture_output=True, text=True)
        if proc.returncode != 0:
            raise RuntimeError(proc.stderr.strip()[-1200:] or "frame generation failed")
        bg = proc.stdout.strip() or "white"
        r = subprocess.run(["rsvg-convert", "-w", str(CANVAS[0]), "-h", str(CANVAS[1]),
                            "-b", bg, "-o", png_path, svg_path],
                           capture_output=True, text=True)
        if r.returncode != 0:
            raise RuntimeError(r.stderr.strip()[-1200:] or "rsvg-convert failed")
        size = os.path.getsize(png_path)
        if size < MIN_PLAUSIBLE_PNG:
            # Almost certainly the containment failure above. Better to shout
            # than to hand back a picture with the artwork quietly missing.
            raise RuntimeError(
                f"render looks wrong: {size} bytes, under {MIN_PLAUSIBLE_PNG}. "
                "Sprites are probably not loading -- check that the scene SVG "
                "is written inside the project directory.")
        with open(png_path, "rb") as fh:
            return base64.b64encode(fh.read()).decode(), bg
    finally:
        for p in (ov_path, svg_path, png_path):
            try:
                os.remove(p)
            except OSError:
                pass


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=HERE, **kw)

    def log_message(self, fmt, *args):
        # BaseHTTPRequestHandler calls this from log_request AND log_error, and
        # the two pass different argument types (a request line vs an
        # HTTPStatus). Assuming a string here raised TypeError inside the
        # handler thread, which aborted the response mid-flight -- the browser
        # saw ERR_EMPTY_RESPONSE and the page lost whatever it was fetching.
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

        overrides = data.get("overrides") or {}
        if not isinstance(overrides, dict):
            return self._json(400, {"error": "overrides must be an object"})

        if self.path.rstrip("/") == "/render":
            style = data.get("style") if data.get("style") in ("flat", "sketch") else "flat"
            try:
                png, bg = render_scene(overrides, style)
            except Exception as exc:                       # surface it, don't swallow
                return self._json(500, {"error": str(exc)})
            return self._json(200, {"png": png, "bg": bg})

        if self.path.rstrip("/") == "/save":
            path = os.path.join(HERE, "overrides.json")
            with open(path, "w") as fh:
                json.dump(overrides, fh, indent=2, sort_keys=True)
                fh.write("\n")
            return self._json(200, {"ok": True, "path": path, "count": len(overrides)})

        self._json(404, {"error": "no such endpoint"})


def main():
    os.chdir(HERE)
    srv = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print(f"flowgif editor  ->  http://localhost:{PORT}/editor.html")
    print("   POST /render  live preview   POST /save  write overrides.json")
    print("   Ctrl-C to stop")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped")


if __name__ == "__main__":
    main()
