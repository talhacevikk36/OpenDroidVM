"""Takes QMP screendumps of a running QEMU and reports how much of the screen is non-black.
usage: display_probe.py QMP_SOCKET T1 T2 ...   (seconds since start)"""
import json
import socket
import sys
import time


def connect(path):
    for _ in range(30):
        try:
            s = socket.socket(socket.AF_UNIX)
            s.connect(path)
            break
        except OSError:
            time.sleep(1)
    f = s.makefile("rw")
    f.readline()

    def cmd(name, **args):
        f.write(json.dumps({"execute": name, "arguments": args}) + "\n")
        f.flush()
        while True:
            r = json.loads(f.readline())
            if "return" in r or "error" in r:
                return r
    cmd("qmp_capabilities")
    return cmd


def stats(ppm):
    d = open(ppm, "rb").read()
    parts = d.split(b"\n", 3)
    w, h = (int(x) for x in parts[1].split())
    pix = parts[3]
    triples = [pix[i:i + 3] for i in range(0, len(pix) - 2, 3)]
    colors = set(triples)
    nonblack = sum(1 for t in triples if t != b"\0\0\0")
    return w, h, 100.0 * nonblack / max(1, len(triples)), len(colors)


def art(ppm, cw=16, ch=32):
    """Coarse picture of the screen: '#' where a cell has any non-black pixel."""
    d = open(ppm, "rb").read()
    parts = d.split(b"\n", 3)
    w, h = (int(x) for x in parts[1].split())
    pix = parts[3]
    rows = []
    for cy in range(0, h, ch):
        row = ""
        for cx in range(0, w, cw):
            hit = False
            for y in range(cy, min(cy + ch, h), 4):
                base = (y * w + cx) * 3
                seg = pix[base:base + cw * 3]
                if seg.strip(b"\0"):
                    hit = True
                    break
            row += "#" if hit else "."
        rows.append(row)
    return rows


cmd = connect(sys.argv[1])
t0, out = time.time(), []
for t in (float(x) for x in sys.argv[2:]):
    time.sleep(max(0, t - (time.time() - t0)))
    r = cmd("screendump", filename="/tmp/shot.ppm")
    if "error" in r:
        out.append(f"t={int(t)}s error={r['error'].get('desc')}")
        continue
    try:
        w, h, pct, n = stats("/tmp/shot.ppm")
        out.append(f"t={int(t)}s {w}x{h} nonblack={pct:.2f}% colors={n}")
    except Exception as e:   # noqa: BLE001
        out.append(f"t={int(t)}s stats-error={e}")
try:
    rows = art("/tmp/shot.ppm")
    used = [i for i, r in enumerate(rows) if "#" in r]
    out.append(f"art rows with content={len(used)} of {len(rows)} first={used[:1]} last={used[-1:]}")
    print("\n".join(rows))
    print("::notice::art :: " + "/".join(rows))
except Exception as e:   # noqa: BLE001
    out.append(f"art-error={e}")
print("\n".join(out))
print("::notice::display probe :: " + " | ".join(out))
