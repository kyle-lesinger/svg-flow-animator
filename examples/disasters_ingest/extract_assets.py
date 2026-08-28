#!/usr/bin/env python3
"""
Extract every embedded raster asset from the Lucidchart SVG export.

The export stashes each bitmap in <defs> as
    <image width="10" height="10" id="XX" xlink:href="data:image/png;base64,...">
and then places it with <use xlink:href="#XX" transform="scale(w,h)">.
So the declared 10x10 is meaningless -- the real pixels are in the payload.

Stdlib only: no Pillow on this machine.
"""
import base64
import os
import re
import struct
import sys

SRC = "/Users/klesinge/Downloads/disasters f2f - full diagram.svg"
OUT = "/private/tmp/claude-502/-Users-klesinge-Downloads/44908f80-5123-4585-99a3-0a23e090fa1d/scratchpad/flowgif/assets"

IMG_RE = re.compile(
    r'<image[^>]*id="([A-Za-z0-9]+)"[^>]*xlink:href="data:image/(png|jpeg);base64,([^"]+)"'
)


def png_size(raw):
    return struct.unpack(">II", raw[16:24])


def jpeg_size(raw):
    i = 2
    while i < len(raw) - 1:
        if raw[i] != 0xFF:
            i += 1
            continue
        marker = raw[i + 1]
        if marker in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB):
            h, w = struct.unpack(">HH", raw[i + 5:i + 9])
            return w, h
        if marker in (0xD8, 0xD9) or 0xD0 <= marker <= 0xD7:
            i += 2
            continue
        i += 2 + struct.unpack(">H", raw[i + 2:i + 4])[0]
    return 0, 0


def main():
    svg = open(SRC, encoding="utf-8", errors="replace").read()
    os.makedirs(OUT, exist_ok=True)

    found = []
    for m in IMG_RE.finditer(svg):
        aid, fmt, b64 = m.group(1), m.group(2), m.group(3)
        raw = base64.b64decode(b64)
        w, h = png_size(raw) if fmt == "png" else jpeg_size(raw)
        ext = "png" if fmt == "png" else "jpg"
        path = os.path.join(OUT, f"{aid}.{ext}")
        with open(path, "wb") as f:
            f.write(raw)
        found.append((aid, ext, w, h, len(raw)))

    for aid, ext, w, h, n in sorted(found):
        print(f"{aid:<4} {ext:<4} {w:>5}x{h:<5} {n:>8} bytes")
    print(f"\n{len(found)} assets -> {OUT}")
    return 0 if found else 1


if __name__ == "__main__":
    sys.exit(main())
