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
print("\n".join(out))
print("::notice::display probe :: " + " | ".join(out))
