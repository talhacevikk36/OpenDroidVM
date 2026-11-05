"""Static check: can this kernel boot on QEMU's generic 'virt' machine?

A phone's TWRP kernel is built for the phone's SoC. For QEMU's `virt` board it
needs: machine support (32-bit ARM: mach-virt), the PL011 serial driver, and the
virtio drivers (disk/display). We look for those drivers' names inside the kernel
image (decompressing gzip/xz/bzip2 payloads), so the answer is based on evidence.
"""
import bz2
import lzma
import struct
import zlib
from dataclasses import dataclass, field

from . import bootimg

MAX_OUT = 256 * 1024 * 1024
MIN_BLOB = 64 * 1024
MARKERS = {
    "virt_machine": [b"linux,dummy-virt"],
    "uart": [b"arm,pl011", b"amba-pl011", b"ttyAMA"],
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
    best = max(vendor_hits.items(), key=lambda kv: kv[1], default=("", 0))
    r.vendor = best[0] if best[1] >= 5 else ""
    if kernel[:4] == b"\x02\x21\x4c\x18" or (not seen_blob and not any(r.found.values())
                                             and r.arch == "unknown"):
        r.compression = "lz4?" if kernel[:4] == b"\x02\x21\x4c\x18" else r.compression
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
    """Scan a boot/recovery image or a raw kernel file."""
    data = open(path, "rb").read()
    try:
        kernel, _ = bootimg.parse(data)
    except bootimg.NotBootImage:
        kernel = data
    return scan_bytes(kernel)
