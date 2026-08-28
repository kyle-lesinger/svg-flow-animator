#!/usr/bin/env python3
"""
Manual geometry overrides.

`layout.py` asks for every movable coordinate through this module instead of
hardcoding it:

    HUB = ov.point("hub", (318, 450))

Two things fall out of that one indirection:

  1. A JSON file can nudge any of it without editing code. Nothing is
     recomputed or re-derived -- the override simply wins.
  2. Every request is REGISTERED, so `editor.py` can discover what is movable
     and draw a drag handle for it. Adding a new movable thing to the diagram
     means adding one `ov.*` call; the editor picks it up for free.

The file is written by the editor and read at import time:

    overrides.json
    {
      "hub": [318, 450],
      "flow.ingest_to_stac": [[500, 450], [580, 428], [660, 450]],
      "box.stac": [660, 350, 280, 200]
    }

Empty or missing file means "use every default", so the diagram always builds.
"""
import json
import os

# Default location; a project points this at its own file via load(path).
PATH = os.path.join(os.getcwd(), "overrides.json")

# key -> {"kind": point|rect|path, "default": ..., "value": ..., "label": str}
HANDLES = {}

_data = {}
_loaded_from = None


def load(path=None):
    """Read the override file. Safe to call repeatedly."""
    global _data, _loaded_from
    path = path or PATH
    if os.path.exists(path):
        try:
            with open(path) as fh:
                _data = json.load(fh) or {}
            _loaded_from = path
        except (ValueError, OSError) as exc:
            # A broken override file must never take the build down -- warn and
            # fall through to the defaults.
            print(f"[overrides] ignoring {path}: {exc}")
            _data = {}
    else:
        _data = {}
    return _data


def _register(key, kind, default, value, label):
    HANDLES[key] = dict(kind=kind, default=default, value=value,
                        label=label or key)


def point(key, default, label=None):
    """A draggable (x, y)."""
    raw = _data.get(key)
    val = (float(raw[0]), float(raw[1])) if raw else tuple(default)
    _register(key, "point", tuple(default), val, label)
    return val


def rect(key, default, label=None):
    """A movable/resizable (x, y, w, h)."""
    raw = _data.get(key)
    val = tuple(float(v) for v in raw) if raw else tuple(default)
    _register(key, "rect", tuple(default), val, label)
    return val


def path(key, default, label=None):
    """
    A polyline whose vertices can be dragged, and into which new vertices can
    be inserted. This is what bends a connector: give it a middle waypoint and
    the straight run becomes an angled one.
    """
    raw = _data.get(key)
    val = ([(float(p[0]), float(p[1])) for p in raw] if raw
           else [tuple(p) for p in default])
    _register(key, "path", [tuple(p) for p in default], val, label)
    return val


def scalar(key, default, label=None):
    """A single number (a spoke's launch x, a font size, an angle)."""
    raw = _data.get(key)
    val = float(raw) if raw is not None else float(default)
    _register(key, "scalar", float(default), val, label)
    return val


def save(data, path=None):
    path = path or PATH
    with open(path, "w") as fh:
        json.dump(data, fh, indent=2, sort_keys=True)
        fh.write("\n")
    return path


def active():
    """Only the keys that actually differ from their default."""
    return {k: h["value"] for k, h in HANDLES.items()
            if list(_as_list(h["value"])) != list(_as_list(h["default"]))}


def _as_list(v):
    if isinstance(v, (int, float)):
        return [v]
    if v and isinstance(v[0], (list, tuple)):
        return [c for p in v for c in p]
    return list(v)


def summary():
    n = len(HANDLES)
    a = len(active())
    src = _loaded_from or "(no overrides file)"
    return f"{n} movable handles, {a} overridden, from {src}"




def use(path):
    """Point the module at a project's override file and read it."""
    global PATH
    PATH = path
    return load(path)
