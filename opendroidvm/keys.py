"""Donanim tuslari: ses +/-, guc, ana ekran, geri, menu...

Iki yol: QEMU monitor (varsayilan, adb gerekmez) veya adb keyevent.
"""
import shutil
import socket
import subprocess
import time

# ad: (QEMU qcode, Android KEYCODE)
KEYS = {
    "volup":   ("volumeup", 24),
    "voldown": ("volumedown", 25),
    "mute":    ("audiomute", 164),
    "power":   ("power", 26),
    "home":    ("ac_home", 3),
    "back":    ("ac_back", 4),
    "menu":    ("menu", 82),
    "recents": (None, 187),      # QEMU'da karsiligi yok: yalnizca adb
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
        raise KeyError(f"Bilinmeyen tus: {name} (gecerli: {', '.join(sorted(KEYS))})")
    return n


def send_monitor(name, port=DEFAULT_MONITOR_PORT, hold_ms=0, host="127.0.0.1"):
    qcode = KEYS[canon(name)][0]
    if not qcode:
        raise KeyError(f"'{name}' tusu monitor ile gonderilemez; --via adb kullan")
    cmd = f"sendkey {qcode}" + (f" {int(hold_ms)}" if hold_ms else "")
    with socket.create_connection((host, port), timeout=3) as s:
        s.settimeout(1.0)
        try:
            s.recv(4096)            # monitor bannerini at
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
        raise RuntimeError("adb bulunamadi (platform-tools kurun)")
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
