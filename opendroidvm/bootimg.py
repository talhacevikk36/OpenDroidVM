"""Android boot/recovery imajindan kernel ve ramdisk cikarir (v0-v4)."""
import hashlib
import os
import struct
import zlib
from pathlib import Path

MAGIC = b"ANDROID!"


class NotBootImage(ValueError):
    """ANDROID! imzasi yok (ham kernel olabilir)."""


class CorruptImage(ValueError):
    """Imza var ama kernel/ramdisk boyutlari dosyaya sigmiyor."""


def _align(n, a):
    return (n + a - 1) // a * a


def parse(data):
    """(kernel, ramdisk) bytes dondurur."""
    if data[:8] != MAGIC:
        raise NotBootImage("Android boot imaji degil (ANDROID! imzasi yok)")
    version = struct.unpack_from("<I", data, 40)[0]
    if version >= 3:
        ksz, rsz = struct.unpack_from("<II", data, 8)
        page = 4096
    else:
        ksz, _, rsz = struct.unpack_from("<III", data, 8)
        page = struct.unpack_from("<I", data, 36)[0]
    koff = page
    roff = koff + _align(ksz, page)
    if ksz == 0 or koff + ksz > len(data) or roff + rsz > len(data):
        raise CorruptImage("Bozuk ya da eksik imaj (kernel/ramdisk boyutu dosyaya sigmiyor)")
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


def cache_dir(img_path):
    """Imaja ozel kalici onbellek klasoru (tekrar tekrar acmamak icin)."""
    st = os.stat(img_path)
    key = hashlib.sha1(f"{os.path.abspath(img_path)}|{st.st_size}|{st.st_mtime_ns}"
                       .encode()).hexdigest()[:16]
    base = os.environ.get("XDG_CACHE_HOME") or os.path.join(os.path.expanduser("~"), ".cache")
    return Path(base) / "opendroidvm" / key
