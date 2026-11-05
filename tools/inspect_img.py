"""Prints the Android boot image header of every .img under a folder (debug helper for CI)."""
import struct
import sys
from pathlib import Path

lines = []
for f in sorted(Path(sys.argv[1]).rglob("*.img")):
    d = f.read_bytes()
    head = d[:48]
    if d[:8] != b"ANDROID!":
        lines.append(f"{f.parent.name}: size={len(d)} magic={d[:8]!r}")
        continue
    ksz, kaddr, rsz, raddr, ssz, saddr, taddr, page, ver = struct.unpack_from("<9I", d, 8)
    al = lambda n: (n + page - 1) // page * page if page else -1
    roff = page + al(ksz)
    lines.append(f"{f.parent.name}: size={len(d)} ver={ver} page={page} kernel={ksz} ramdisk={rsz} "
                 f"second={ssz} kernel_end={page + ksz} ramdisk_end={roff + rsz} tail={d[-16:]!r}")
for l in lines:
    print(l)
print("::notice::" + " || ".join(lines)[:3500])
