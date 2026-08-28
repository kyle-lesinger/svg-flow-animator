"""
Shared helpers. No third-party imports -- the package is stdlib-only by policy
(docs/DECISIONS.md) and its tests hold to the same rule.
"""
import os
import re
import shutil
import struct
import sys
import unittest
import xml.etree.ElementTree as ET
import zlib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

PKG_DIR = os.path.join(ROOT, "svg_flow_animator")
MINIMAL_DIR = os.path.join(ROOT, "examples", "minimal")
DISASTERS_DIR = os.path.join(ROOT, "examples", "disasters_ingest")
# Gitignored third-party artwork; absent on a fresh clone. Nothing may require it.
DISASTERS_ASSETS = os.path.join(DISASTERS_DIR, "assets")


# ------------------------------------------------------------ environment ---
def have(binary):
    return shutil.which(binary) is not None


HAVE_RSVG = have("rsvg-convert")
HAVE_FFMPEG = have("ffmpeg")
HAVE_MAGICK = have("magick")
HAVE_NODE = have("node")
HAVE_DISASTERS_ASSETS = os.path.isdir(DISASTERS_ASSETS) and bool(
    os.path.isdir(DISASTERS_ASSETS) and os.listdir(DISASTERS_ASSETS))

needs_rsvg = unittest.skipUnless(HAVE_RSVG, "rsvg-convert not on PATH")
needs_ffmpeg = unittest.skipUnless(HAVE_FFMPEG, "ffmpeg not on PATH")
needs_magick = unittest.skipUnless(HAVE_MAGICK, "magick (ImageMagick) not on PATH")
needs_node = unittest.skipUnless(HAVE_NODE, "node not on PATH")
needs_disasters_assets = unittest.skipUnless(
    HAVE_DISASTERS_ASSETS, "examples/disasters_ingest/assets/ absent (gitignored)")

SLOW_DISABLED = os.environ.get("SFA_SKIP_SLOW", "").strip() not in ("", "0")
skip_if_slow_disabled = unittest.skipIf(SLOW_DISABLED, "SFA_SKIP_SLOW is set")


def package_sources():
    """(path, text) for every module in the package."""
    out = []
    for name in sorted(os.listdir(PKG_DIR)):
        if name.endswith(".py"):
            p = os.path.join(PKG_DIR, name)
            with open(p, encoding="utf-8") as fh:
                out.append((p, fh.read()))
    return out


def emitted_literals(source, filename="<pkg>"):
    """
    Every string literal a module can actually EMIT, docstrings excluded.

    Source-level guards ("no module writes fill=transparent") have to look at
    what the code produces, not at prose describing the bug it is avoiding --
    most of these gotchas are documented right next to the code that avoids
    them, so a naive substring scan matches the warning instead of a relapse.
    """
    import ast

    tree = ast.parse(source, filename)
    prose = {id(n.value) for n in ast.walk(tree)
             if isinstance(n, ast.Expr) and isinstance(n.value, ast.Constant)
             and isinstance(n.value.value, str)}
    return [n.value for n in ast.walk(tree)
            if isinstance(n, ast.Constant) and isinstance(n.value, str)
            and id(n) not in prose]


_BLOCK_COMMENT = re.compile(r"/\*.*?\*/", re.S)
_LINE_COMMENT = re.compile(r"^[ \t]*//.*$", re.M)


def strip_comments(text):
    """Drop CSS/JS comments, so prose about a gotcha is not mistaken for one."""
    return _LINE_COMMENT.sub("", _BLOCK_COMMENT.sub("", text))


def package_emitted_literals():
    """(path, literal) pairs across the whole package, comments stripped."""
    for path, text in package_sources():
        for lit in emitted_literals(text, path):
            yield path, strip_comments(lit)


# -------------------------------------------------------------------- xml ---
def parse_fragment(markup):
    """
    Parse an SVG fragment by wrapping it in a root element.

    Emitters return bare elements, so they need a container before ElementTree
    will look at them. Raises ParseError on malformed markup, which is the point.
    """
    return ET.fromstring(
        '<svg xmlns="http://www.w3.org/2000/svg" '
        'xmlns:xlink="http://www.w3.org/1999/xlink">%s</svg>' % markup)


def iter_elements(markup):
    return list(parse_fragment(markup).iter())


# ------------------------------------------------------- synthesised media ---
def png_bytes(width, height, rgb=(0x7F, 0x30, 0x60)):
    """A real, decodable PNG of exactly `width` x `height`."""
    def chunk(typ, data):
        body = typ + data
        return (struct.pack(">I", len(data)) + body
                + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF))

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)  # 8-bit truecolour
    row = b"\x00" + bytes(rgb) * width                            # filter 0 + pixels
    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", zlib.compress(row * height))
            + chunk(b"IEND", b""))


def jpeg_bytes(width, height, sof=0xC0, extra_segments=1):
    """
    A JPEG header good enough for `assets._jpeg_size`.

    `extra_segments` inserts skippable segments before the SOF, so the parser's
    length-walk is genuinely exercised rather than finding SOF at a fixed offset.
    `sof=0xC2` gives a progressive JPEG, which uses a different SOF marker.
    """
    out = [b"\xff\xd8"]
    app0 = (b"JFIF\x00" b"\x01\x01" b"\x00" b"\x00\x01\x00\x01" b"\x00\x00")
    for _ in range(extra_segments):
        out.append(b"\xff\xe0" + struct.pack(">H", len(app0) + 2) + app0)
        out.append(b"\xff\xfe" + struct.pack(">H", 2 + 7) + b"comment")
    out.append(b"\xff" + bytes([sof]) + struct.pack(">H", 11) + b"\x08"
               + struct.pack(">HH", height, width) + b"\x01\x01\x11\x00")
    out.append(b"\xff\xd9")
    return b"".join(out)


# ------------------------------------------------------------------ misc ----
_SCRIPT_RE = re.compile(r"<script[^>]*>(.*?)</script>", re.S)


def extract_scripts(html):
    return _SCRIPT_RE.findall(html)
