"""Boots a small, known-good ARM64 Linux (Alpine netboot) in QEMU to prove that QEMU, the
serial console and (with VNC) the display chain work on THIS machine - independent of any
phone image."""
import os
import queue
import re
import subprocess
import threading
import time
import urllib.request

from . import paths, qemu

BASE = "https://dl-cdn.alpinelinux.org/alpine/latest-stable/releases/aarch64/netboot"
FILES = ("vmlinuz-virt", "initramfs-virt")


def base_url():
    return os.environ.get("ODVM_ALPINE_BASE", BASE).rstrip("/")


def fetch(name, progress=None):
    dest = paths.cache_root() / "selftest" / name
    if dest.is_file() and dest.stat().st_size > 100_000:
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(".part")
    req = urllib.request.Request(f"{base_url()}/{name}", headers={"User-Agent": "OpenDroidVM"})
    with urllib.request.urlopen(req, timeout=60) as r, open(tmp, "wb") as f:
        total = int(r.headers.get("Content-Length") or 0)
        done = 0
        while True:
            chunk = r.read(1 << 18)
            if not chunk:
                break
            f.write(chunk)
            done += len(chunk)
            if progress:
                progress(name, done, total)
    os.replace(tmp, dest)
    return dest


def command(exe, kernel, initrd):
    hw = qemu.host_accel("aarch64")
    accel, cpu = (hw, "host") if hw else ("tcg,thread=multi", "max")
    return [exe, "-machine", "virt", "-accel", accel, "-cpu", cpu, "-smp", "2", "-m", "512",
            "-kernel", str(kernel), "-initrd", str(initrd),
            "-append", "console=ttyAMA0 earlycon", "-display", "none",
            "-serial", "stdio", "-monitor", "none", "-no-reboot"]


def boot(cmd, expect, timeout):
    """Run QEMU, return (found, serial text). Stops as soon as `expect` shows up."""
    p = subprocess.Popen(cmd, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT)
    q = queue.Queue()

    def reader():
        for line in iter(p.stdout.readline, b""):
            q.put(line.decode(errors="replace"))
        q.put(None)
    threading.Thread(target=reader, daemon=True).start()
    text, found, end = "", False, time.time() + timeout
    rx = re.compile(expect)
    try:
        while time.time() < end:
            try:
                line = q.get(timeout=1)
            except queue.Empty:
                continue
            if line is None:
                break
            text += line
            if rx.search(text):
                found = True
                break
    finally:
        p.kill()
        p.wait()
    return found, text


def run(exe=None, kernel=None, initrd=None, expect=r"Linux version", timeout=120, progress=None):
    exe = exe or qemu.find_qemu("aarch64")
    if not exe:
        raise FileNotFoundError("qemu")
    kernel = kernel or fetch(FILES[0], progress)
    initrd = initrd or fetch(FILES[1], progress)
    return boot(command(exe, kernel, initrd), expect, timeout)
