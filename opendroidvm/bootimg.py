"""Android boot/recovery imajindan kernel ve ramdisk cikarir (v0-v4)."""
import struct
import zlib
from pathlib import Path

MAGIC = b"ANDROID!"


def _align(n, a):
    return (n + a - 1) // a * a


def parse(data):
    """(kernel, ramdisk) bytes dondurur."""
    if data[:8] != MAGIC:
        raise ValueError("Android boot imaji degil (ANDROID! imzasi yok)")
    version = struct.unpack_from("<I", data, 40)[0]
    if version >= 3:
        ksz, rsz = struct.unpack_from("<II", data, 8)
        page = 4096
    else:
        ksz, _, rsz = struct.unpack_from("<III", data, 8)
        page = struct.unpack_from("<I", data, 36)[0]
    koff = page
    roff = koff + _align(ksz, page)
    return data[koff:koff + ksz], data[roff:roff + rsz]


def _gunzip(blob):
    if blob[:2] != b"\x1f\x8b":
        return blob
    d = zlib.decompressobj(31)  # sondaki dtb gibi artiklari yoksayar
    return d.decompress(blob)


def extract(img_path, out_dir):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    kernel, ramdisk = parse(Path(img_path).read_bytes())
    kp, rp = out / "kernel", out / "ramdisk.img"
    kp.write_bytes(_gunzip(kernel))
    rp.write_bytes(ramdisk)
    return kp, rp
