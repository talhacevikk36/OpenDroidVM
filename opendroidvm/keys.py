"""Hardware keys: volume +/-, power, home, back, menu...

Two paths: QEMU monitor (default, no adb needed) or adb keyevent.
"""
import shutil
import socket
import subprocess
import time

from .i18n import t

# name: (QEMU qcode, Android KEYCODE)
KEYS = {
    "volup":   ("volumeup", 24),
    "voldown": ("volumedown", 25),
    "mute":    ("audiomute", 164),
    "power":   ("power", 26),
    "home":    ("ac_home", 3),
    "back":    ("ac_back", 4),
    "menu":    ("menu", 82),
    "recents": (None, 187),      # no QEMU equivalent: adb only
    "camera":  (None, 27),
    "wake":    ("wake", 224),
    "sleep":   ("sleep", 223),
}
ALIASES = {"vol+": "volup", "vol-": "voldown", "volume_up": "volup",
           "volume_down": "voldown", "pwr": "power", "apps": "recents"}
DEFAULT_MONITOR_PORT = 5556


def canon(name):
    n = name.lower().strip()
    n = ALIASES.get(n, n)
    if n not in KEYS:
        raise KeyError(t("key_unknown", x=name, v=", ".join(sorted(KEYS))))
    return n


def send_monitor(name, port=DEFAULT_MONITOR_PORT, hold_ms=0, host="127.0.0.1"):
    qcode = KEYS[canon(name)][0]
    if not qcode:
        raise KeyError(t("key_no_monitor", x=name))
    cmd = f"sendkey {qcode}" + (f" {int(hold_ms)}" if hold_ms else "")
    with socket.create_connection((host, port), timeout=3) as s:
        s.settimeout(1.0)
        try:
            s.recv(4096)            # discard the monitor banner
        except socket.timeout:
            pass
        s.sendall((cmd + "\n").encode())
        time.sleep(0.15 + hold_ms / 1000.0)
        try:
            reply = s.recv(4096).decode(errors="replace")
        except socket.timeout:
            reply = ""
    for line in reply.replace("\r", "\n").splitlines():
        if "invalid" in line.lower() or "unknown" in line.lower():
            raise RuntimeError(line.strip())
    return cmd


def send_adb(name, serial="localhost:5555", hold_ms=0):
    adb = shutil.which("adb")
    if not adb:
        raise RuntimeError(t("adb_missing"))
    code = str(KEYS[canon(name)][1])
    args = [adb, "-s", serial, "shell", "input", "keyevent"]
    if hold_ms >= 500:
        args.append("--longpress")
    subprocess.check_call(args + [code])
    return " ".join(args + [code])


def press(name, via="monitor", port=DEFAULT_MONITOR_PORT, hold_ms=0, serial="localhost:5555"):
    if via == "adb":
        return send_adb(name, serial, hold_ms)
    return send_monitor(name, port, hold_ms)


def monitor_cmd(cmd, port=DEFAULT_MONITOR_PORT, host="127.0.0.1", wait=0.3):
    """Send any QEMU monitor (HMP) command and return the reply text."""
    with socket.create_connection((host, port), timeout=3) as s:
        s.settimeout(0.5)
        try:
            s.recv(4096)
        except socket.timeout:
            pass
        s.sendall((cmd + "\n").encode())
        time.sleep(wait)
        chunks = b""
        try:
            while True:
                part = s.recv(4096)
                if not part:
                    break
                chunks += part
        except (socket.timeout, OSError):
            pass
    lines = [render_terminal(x) for x in chunks.decode(errors="replace").replace("\r", "").split("\n")]
    return "\n".join(x for x in lines if x.strip() and not x.startswith("(qemu)")
                     and x.strip() != cmd).strip()


def render_terminal(line):
    """The HMP monitor echoes typed text with cursor codes (ESC[K erase, ESC[D left).
    Replay them to get the text a terminal would finally show."""
    buf, cur, i = [], 0, 0
    while i < len(line):
        ch = line[i]
        if ch == "\x1b" and line[i + 1:i + 2] == "[":
            j = i + 2
            while j < len(line) and (line[j].isdigit() or line[j] in ";?"):
                j += 1
            code = line[j:j + 1]
            n = int(line[i + 2:j].split(";")[0] or 1) if line[i + 2:j][:1].isdigit() else 1
            if code == "K":
                del buf[cur:]
            elif code == "D":
                cur = max(0, cur - n)
            elif code == "C":
                cur = min(len(buf), cur + n)
            i = j + 1
            continue
        if ch >= " ":
            if cur < len(buf):
                buf[cur] = ch
            else:
                buf.append(ch)
            cur += 1
        i += 1
    return "".join(buf)
