"""Screenshots through the QEMU monitor (screendump -> PNG, no extra libraries)."""
import os
import struct
import tempfile
import time
import zlib

from . import keys
from .i18n import t


def ppm_to_png(src, dst):
    data = open(src, "rb").read()
    if data[:2] != b"P6":
        raise ValueError("not a P6 PPM")
    pos, vals = 2, []
    while len(vals) < 3:                       # width, height, maxval (comments allowed)
        while data[pos:pos + 1].isspace():
            pos += 1
        if data[pos:pos + 1] == b"#":
            pos = data.index(b"\n", pos) + 1
            continue
        end = pos
        while not data[end:end + 1].isspace():
            end += 1
        vals.append(int(data[pos:end])); pos = end
    w, h, _ = vals
    pix = data[pos + 1:pos + 1 + w * h * 3]
    if len(pix) < w * h * 3:
        raise ValueError("truncated PPM")
    raw = b"".join(b"\x00" + pix[y * w * 3:(y + 1) * w * 3] for y in range(h))

    def chunk(tag, body):
        c = struct.pack(">I", len(body)) + tag + body
        return c + struct.pack(">I", zlib.crc32(tag + body) & 0xFFFFFFFF)
    png = (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
           + chunk(b"IDAT", zlib.compress(raw, 6)) + chunk(b"IEND", b""))
    with open(dst, "wb") as f:
        f.write(png)
    return w, h


def dump_ppm(path, port=keys.DEFAULT_MONITOR_PORT):
    """Ask QEMU for a raw screen dump (PPM). Raises RuntimeError when there is no picture."""
    try:
        os.remove(path)
    except OSError:
        pass
    reply = keys.monitor_cmd(f"screendump {path}", port, wait=0.5)
    for _ in range(20):
        if os.path.exists(path) and os.path.getsize(path) > 16:
            return path
        time.sleep(0.2)
    raise RuntimeError(t("shot_none") + (f" ({reply})" if reply else ""))


def art_rows(ppm, cw=16, ch=32):
    """Coarse picture of a PPM: '#' where a cell holds any non-black pixel."""
    d = open(ppm, "rb").read()
    parts = d.split(b"\n", 3)
    w, h = (int(x) for x in parts[1].split())
    pix = parts[3]
    rows = []
    for cy in range(0, h, ch):
        row = ""
        for cx in range(0, w, cw):
            hit = any(pix[(y * w + cx) * 3:(y * w + cx) * 3 + cw * 3].strip(b"\0")
                      for y in range(cy, min(cy + ch, h), 4))
            row += "#" if hit else "."
        rows.append(row)
    return rows


def has_picture(rows, min_rows=5):
    """A text console fills many rows; QEMU's 'Display output is not active' is one line."""
    return sum(1 for r in rows if "#" in r) >= min_rows


def take(out, port=keys.DEFAULT_MONITOR_PORT):
    tmp = os.path.join(tempfile.gettempdir(), f"odvm-shot-{os.getpid()}.ppm")
    dump_ppm(tmp, port)
    try:
        return ppm_to_png(tmp, out)
    finally:
        try:
            os.remove(tmp)
        except OSError:
            pass
