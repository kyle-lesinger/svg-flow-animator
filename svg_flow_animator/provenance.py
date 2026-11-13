"""
Embedded provenance: a comment inside a finished GIF, PNG or APNG.

NASA NID 1383.155 requires SI-assisted media to carry embedded metadata that
says so. ffmpeg 9 accepts `-metadata comment=...` for all three formats and
writes nothing at all (docs/GOTCHAS.md), so the comment is written here, after
the file is complete, from the formats' own specifications:

  GIF   a Comment Extension (0x21 0xFE, GIF89a), inserted right after the
        global colour table, ahead of every frame and its Graphic Control
        Extension (which must stay glued to its image).
  PNG   a tEXt chunk with the keyword "Comment", inserted right after IHDR.
        APNG is PNG, so the same chunk serves both.

`stamp()` replaces any comment it wrote before, so stamping twice is the same
as stamping once. `read()` returns what is in the file, which is what the tests
and the build's verify step check: the point of the metadata is that it is in
the file, not that the command ran.

Both encodings are Latin-1 by specification. Keep the text ASCII.
"""
import struct

__all__ = ["stamp", "read"]

_GIF_EXT, _GIF_COMMENT, _GIF_IMAGE, _GIF_TRAILER = 0x21, 0xFE, 0x2C, 0x3B
_PNG_SIG = b"\x89PNG\r\n\x1a\n"
_PNG_KEYWORD = b"Comment"


def stamp(path, text):
    """Write `text` into the GIF/PNG/APNG at `path` as its comment."""
    data = text.encode("latin-1")
    with open(path, "rb") as fh:
        blob = fh.read()
    if blob[:6] in (b"GIF89a", b"GIF87a"):
        out = _gif_stamp(blob, data)
    elif blob[:8] == _PNG_SIG:
        out = _png_stamp(blob, data)
    else:
        raise ValueError(f"{path}: not a GIF or PNG")
    with open(path, "wb") as fh:
        fh.write(out)


def read(path):
    """The comments in the file, in order. [] if there are none."""
    with open(path, "rb") as fh:
        blob = fh.read()
    if blob[:6] in (b"GIF89a", b"GIF87a"):
        return [c.decode("latin-1") for c in _gif_split(blob)[1]]
    if blob[:8] == _PNG_SIG:
        return [c.decode("latin-1") for _, c in _png_comments(blob)]
    raise ValueError(f"{path}: not a GIF or PNG")


# -------------------------------------------------------------------- GIF ---
def _gif_split(blob):
    """(head, comments, rest): the bytes up to the first extension that is not
    a comment, the comments found before it, and everything from there on.
    Walks only the leading extension blocks -- that is where stamp() writes."""
    flags = blob[10]
    gct = 3 * (2 << (flags & 7)) if flags & 0x80 else 0
    p = 13 + gct
    comments = []
    while p < len(blob) and blob[p] == _GIF_EXT and blob[p + 1] == _GIF_COMMENT:
        q, parts = p + 2, []
        while blob[q]:
            n = blob[q]
            parts.append(blob[q + 1:q + 1 + n])
            q += 1 + n
        comments.append(b"".join(parts))
        p = q + 1
    return blob[:13 + gct], comments, blob[p:]


def _gif_stamp(blob, data):
    if blob[:6] != b"GIF89a":
        raise ValueError("GIF comments need GIF89a; this is GIF87a")
    head, _old, rest = _gif_split(blob)
    ext = bytes([_GIF_EXT, _GIF_COMMENT])
    for i in range(0, len(data), 255):
        chunk = data[i:i + 255]
        ext += bytes([len(chunk)]) + chunk
    ext += b"\x00"
    return head + ext + rest


# -------------------------------------------------------------------- PNG ---
def _png_chunks(blob):
    """Yield (offset, length, type, data) for each chunk."""
    p = 8
    while p < len(blob):
        n, = struct.unpack(">I", blob[p:p + 4])
        yield p, 12 + n, blob[p + 4:p + 8], blob[p + 8:p + 8 + n]
        p += 12 + n


def _png_comments(blob):
    for off, size, kind, data in _png_chunks(blob):
        if kind == b"tEXt" and data.startswith(_PNG_KEYWORD + b"\x00"):
            yield (off, size), data[len(_PNG_KEYWORD) + 1:]


def _png_stamp(blob, data):
    import zlib
    for (off, size), _ in reversed(list(_png_comments(blob))):
        blob = blob[:off] + blob[off + size:]
    body = _PNG_KEYWORD + b"\x00" + data
    chunk = (struct.pack(">I", len(body)) + b"tEXt" + body
             + struct.pack(">I", zlib.crc32(b"tEXt" + body) & 0xFFFFFFFF))
    off, size, kind, _ = next(_png_chunks(blob))
    if kind != b"IHDR":
        raise ValueError("PNG does not start with IHDR")
    cut = off + size
    return blob[:cut] + chunk + blob[cut:]
