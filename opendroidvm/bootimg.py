"""Extracts kernel and ramdisk from an Android boot/recovery image (v0-v4)."""
import hashlib
import os
import struct
import zlib
from pathlib import Path

from .i18n import t

MAGIC = b"ANDROID!"


class NotBootImage(ValueError):
    """No ANDROID! magic (may be a raw kernel)."""


class CorruptImage(ValueError):
    """Magic is present but kernel/ramdisk sizes do not fit the file."""


def _align(n, a):
    return (n + a - 1) // a * a


def parse(data):
    """Return (kernel, ramdisk) bytes."""
    if data[:8] != MAGIC:
        raise NotBootImage(t("not_boot"))
    version = struct.unpack_from("<I", data, 40)[0]
    if version >= 3:
        ksz, rsz = struct.unpack_from("<II", data, 8)
        page = 4096
    else:
        ksz, _, rsz = struct.unpack_from("<III", data, 8)
        page = struct.unpack_from("<I", data, 36)[0]
    if page < 512 or page & (page - 1):      # must be a power of two (0 would divide by zero)
        raise CorruptImage(t("corrupt"))
    koff = page
    roff = koff + _align(ksz, page)
    if ksz == 0 or koff + ksz > len(data) or roff + rsz > len(data):
        raise CorruptImage(t("corrupt"))
    return data[koff:koff + ksz], data[roff:roff + rsz]


def _gunzip(blob):
    if blob[:2] != b"\x1f\x8b":
        return blob
    d = zlib.decompressobj(31)  # ignores trailing data such as an appended dtb
    return d.decompress(blob)


def extract(img_path, out_dir):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    kernel, ramdisk = parse(Path(img_path).read_bytes())
    kp, rp = out / "kernel", out / "ramdisk.img"
    kp.write_bytes(_gunzip(kernel))
    rp.write_bytes(ramdisk)
    return kp, rp


def cache_dir(img_path):
    """Per-image persistent cache folder (avoids re-extracting)."""
    st = os.stat(img_path)
    key = hashlib.sha1(f"{os.path.abspath(img_path)}|{st.st_size}|{st.st_mtime_ns}"
                       .encode()).hexdigest()[:16]
    base = os.environ.get("XDG_CACHE_HOME") or os.path.join(os.path.expanduser("~"), ".cache")
    return Path(base) / "opendroidvm" / key


def kernel_kind(path):
    """'arm64' | 'arm32' | 'unknown' from the kernel header (Image / zImage magic)."""
    try:
        with open(path, "rb") as f:
            head = f.read(64)
    except OSError:
        return "unknown"
    if len(head) >= 60 and head[56:60] == b"ARMd":
        return "arm64"
    if len(head) >= 40 and struct.unpack_from("<I", head, 36)[0] == 0x016F2818:
        return "arm32"
    return "unknown"
