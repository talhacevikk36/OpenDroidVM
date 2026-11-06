"""Static check: can this kernel boot on QEMU's generic 'virt' machine?

A phone's TWRP kernel is built for the phone's SoC. For QEMU's `virt` board it
needs: machine support (32-bit ARM: mach-virt), the PL011 serial driver, and the
virtio drivers (disk/display). We look for those drivers' names inside the kernel
image (decompressing gzip/xz/bzip2 payloads), so the answer is based on evidence.
"""
import bz2
import hashlib
import json
import lzma
import os
import struct
import zlib
from dataclasses import asdict, dataclass, field

from . import bootimg

MAX_OUT = 256 * 1024 * 1024
MIN_BLOB = 64 * 1024
MARKERS = {
    "virt_machine": [b"linux,dummy-virt"],
    "uart": [b"arm,pl011", b"amba-pl011", b"uart-pl011", b"ttyAMA"],
    "virtio_mmio": [b"virtio_mmio", b"virtio-mmio"],
    "virtio_pci": [b"virtio-pci", b"virtio_pci"],
    "virtio_blk": [b"virtio_blk"],
    "virtio_net": [b"virtio_net"],
    "virtio_gpu": [b"virtio_gpu", b"virtio-gpu"],
    "virtio_input": [b"virtio_input", b"virtio-input"],
}
VENDORS = [("Qualcomm", b"qcom,"), ("Samsung Exynos", b"samsung,exynos"),
           ("MediaTek", b"mediatek,"), ("HiSilicon Kirin", b"hisilicon,"),
           ("Rockchip", b"rockchip,"), ("NVIDIA Tegra", b"nvidia,tegra")]


SCAN_VERSION = 2
LZ4_LEGACY = b"\x02\x21\x4c\x18"


def _lz4_block(src, limit):
    out = bytearray()
    i, n = 0, len(src)
    while i < n:
        token = src[i]; i += 1
        lit = token >> 4
        if lit == 15:
            while True:
                b = src[i]; i += 1; lit += b
                if b != 255:
                    break
        out += src[i:i + lit]; i += lit
        if i >= n:
            break
        off = src[i] | (src[i + 1] << 8); i += 2
        ml = token & 15
        if ml == 15:
            while True:
                b = src[i]; i += 1; ml += b
                if b != 255:
                    break
        ml += 4
        if off == 0 or off > len(out):
            raise ValueError("bad lz4 offset")
        start = len(out) - off
        if off >= ml:
            out += out[start:start + ml]
        else:
            out += (bytes(out[start:]) * (ml // off + 1))[:ml]
        if len(out) > limit:
            raise ValueError("lz4 too large")
    return bytes(out)


def lz4_legacy(data, limit=MAX_OUT):
    """Decode the 'legacy' LZ4 container used for Android kernels (Image.lz4). Partial on error."""
    out = bytearray()
    i = 4 if data[:4] == LZ4_LEGACY else 0
    try:
        while i + 4 <= len(data) and len(out) < limit:
            n = int.from_bytes(data[i:i + 4], "little"); i += 4
            if data[i - 4:i] == LZ4_LEGACY:
                continue
            if n == 0 or n > len(data) - i or n > 16 * 1024 * 1024:
                break
            out += _lz4_block(data[i:i + n], limit)
            i += n
    except (ValueError, IndexError):
        pass
    return bytes(out)


@dataclass
class Scan:
    arch: str = "unknown"            # arm64 | arm32 | unknown
    compression: str = "none"        # none | gzip | xz | bzip2 | lz4?
    found: dict = field(default_factory=dict)
    vendor: str = ""
    verdict: str = "unknown"         # yes | serial | no | unknown
    reason: str = ""                 # no_virt | no_uart | no_virtio | no_gpu | unreadable | ""


def _arch(head):
    if len(head) >= 60 and head[56:60] == b"ARMd":
        return "arm64"
    if len(head) >= 40 and struct.unpack_from("<I", head, 36)[0] == 0x016F2818:
        return "arm32"
    return "unknown"


def _blobs(data):
    """The kernel bytes plus every decompressible payload found inside them."""
    yield data, "none"
    probes = [(b"\x1f\x8b\x08", "gzip"), (b"\xfd7zXZ\x00", "xz"), (b"BZh", "bzip2")]
    pos = 0
    for _ in range(3):                      # LZ4 legacy (Pixel kernels): at the start or later
        pos = data.find(LZ4_LEGACY, pos)
        if pos < 0:
            break
        out = lz4_legacy(data[pos:])
        if len(out) >= MIN_BLOB:
            yield out, "lz4"
            break
        pos += 1
    for magic, name in probes:
        pos, tries = 0, 0
        while tries < 6:
            pos = data.find(magic, pos)
            if pos < 0:
                break
            tries += 1
            try:
                if name == "gzip":
                    out = zlib.decompressobj(31).decompress(data[pos:], MAX_OUT)
                elif name == "xz":
                    out = lzma.LZMADecompressor(format=lzma.FORMAT_XZ).decompress(data[pos:], MAX_OUT)
                else:
                    out = bz2.BZ2Decompressor().decompress(data[pos:], MAX_OUT)
            except (zlib.error, lzma.LZMAError, OSError, ValueError, EOFError):
                out = b""
            if len(out) >= MIN_BLOB:
                yield out, name
                break
            pos += 1


def scan_bytes(kernel):
    r = Scan()
    r.found = {k: False for k in MARKERS}
    r.arch = _arch(kernel[:64])
    seen_blob = False
    vendor_hits = {}
    for blob, comp in _blobs(kernel):
        if comp != "none":
            seen_blob = True
            if r.compression == "none":
                r.compression = comp
            if r.arch == "unknown":
                r.arch = _arch(blob[:64])
        for key, words in MARKERS.items():
            if not r.found[key] and any(w in blob for w in words):
                r.found[key] = True
        for name, w in VENDORS:
            vendor_hits[name] = vendor_hits.get(name, 0) + blob.count(w)
    ranked = sorted(vendor_hits.items(), key=lambda kv: kv[1], reverse=True) + [("", 0), ("", 0)]
    # a phone kernel is dominated by ONE vendor; generic kernels (distro) mention several
    r.vendor = ranked[0][0] if ranked[0][1] >= 5 and ranked[0][1] >= 3 * ranked[1][1] else ""
    if not seen_blob and not any(r.found.values()) and r.arch == "unknown":
        r.compression = "lz4?" if kernel[:4] == LZ4_LEGACY else r.compression
        r.reason = "unreadable"
        return r                                    # cannot see inside: no verdict
    f = r.found
    if r.arch == "arm32" and not f["virt_machine"]:
        r.verdict, r.reason = "no", "no_virt"
    elif not f["uart"]:
        r.verdict, r.reason = "no", "no_uart"
    elif not (f["virtio_mmio"] or f["virtio_pci"]):
        r.verdict, r.reason = "no", "no_virtio"
    elif not f["virtio_gpu"]:
        r.verdict, r.reason = "serial", "no_gpu"
    else:
        r.verdict = "yes"
    return r


def scan_file(path):
    """Scan a boot/recovery image or a raw kernel file (result cached per file)."""
    from . import paths
    st = os.stat(path)
    key = hashlib.sha1(f"{SCAN_VERSION}|{os.path.abspath(path)}|{st.st_size}|{st.st_mtime_ns}"
                       .encode()).hexdigest()[:16]
    cache = paths.cache_root() / f"scan-{key}.json"
    try:
        return Scan(**json.loads(cache.read_text(encoding="utf-8")))
    except (OSError, ValueError, TypeError):
        pass
    data = open(path, "rb").read()
    try:
        kernel, _ = bootimg.parse(data)
    except bootimg.NotBootImage:
        kernel = data
    r = scan_bytes(kernel)
    try:
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps(asdict(r)), encoding="utf-8")
    except OSError:
        pass
    return r
