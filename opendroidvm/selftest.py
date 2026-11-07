"""Boots a small, known-good ARM64 Linux (Alpine netboot) in QEMU to prove that QEMU, the
serial console and (with VNC) the display chain work on THIS machine - independent of any
phone image."""
import functools
import http.server
import os
import queue
import re
import socketserver
import subprocess
import tempfile
import threading
import time
import urllib.request

from . import paths, qemu, screen

BASE = "https://dl-cdn.alpinelinux.org/alpine/latest-stable/releases/aarch64/netboot"
FILES = ("vmlinuz-virt", "initramfs-virt")
DISPLAY_FILES = FILES + ("modloop-virt",)       # modloop holds the virtio-gpu driver module


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


def _pump(stream, q):
    """Forward raw output chunks. NOT line by line: a login prompt has no newline."""
    read = getattr(stream, "read1", None) or (lambda n: stream.read(1))
    while True:
        try:
            chunk = read(4096)
        except (OSError, ValueError):
            break
        if not chunk:
            break
        q.put(chunk.decode(errors="replace"))
    q.put(None)


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
        _pump(p.stdout, q)
    threading.Thread(target=reader, daemon=True).start()
    text, found, end = "", False, time.time() + timeout
    rx = re.compile(expect)
    try:
        while time.time() < end:
            try:
                chunk = q.get(timeout=1)
            except queue.Empty:
                continue
            if chunk is None:
                break
            text += chunk
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


class _Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


def serve_cache(directory):
    """Serves the cached files to the guest (it reaches the host as 10.0.2.2)."""
    handler = functools.partial(_Quiet, directory=str(directory))
    srv = socketserver.ThreadingTCPServer(("127.0.0.1", 0), handler)
    srv.daemon_threads = True
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, srv.server_address[1]


def display_command(exe, kernel, initrd, http_port, vnc=-1, monitor_port=0, interactive=False):
    """Alpine with a GPU driver: kernel log + login on the virtual screen (and the serial console)."""
    hw = qemu.host_accel("aarch64")
    accel, cpu = (hw, "host") if hw else ("tcg,thread=multi", "max")
    append = ("console=tty0 console=ttyAMA0 ip=dhcp "
              "alpine_repo=https://dl-cdn.alpinelinux.org/alpine/latest-stable/main "
              f"modloop=http://10.0.2.2:{http_port}/modloop-virt")
    cmd = [exe, "-machine", "virt", "-accel", accel, "-cpu", cpu, "-smp", "2", "-m", "1024",
           "-kernel", str(kernel), "-initrd", str(initrd), "-append", append,
           "-device", "virtio-gpu-pci", "-device", "virtio-keyboard-pci",
           "-device", "virtio-tablet-pci", "-netdev", "user,id=n0",
           "-device", "virtio-net-pci,netdev=n0",
           "-display", f"vnc=:{vnc}" if vnc >= 0 else "none",
           "-serial", "mon:stdio" if interactive else "stdio"]
    if monitor_port:
        cmd += ["-monitor", f"tcp:127.0.0.1:{monitor_port},server,nowait"]
    elif not interactive:
        cmd += ["-monitor", "none"]
    return cmd


def prepare_display(progress=None):
    files = [fetch(n, progress) for n in DISPLAY_FILES]
    return files, paths.cache_root() / "selftest"


def check_display(exe, files, cache_dir, timeout=360, vnc=-1):
    """Boot the demo and look at the screen. Returns (ok, art rows, serial text)."""
    srv, http_port = serve_cache(cache_dir)
    mon = qemu.free_port(5900 + 100) or 6001
    cmd = display_command(exe, files[0], files[1], http_port, vnc, mon)
    p = subprocess.Popen(cmd, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    q = queue.Queue()

    def reader():
        _pump(p.stdout, q)
    threading.Thread(target=reader, daemon=True).start()
    text, rows, end = "", [], time.time() + timeout
    try:
        while time.time() < end:
            try:
                chunk = q.get(timeout=1)
            except queue.Empty:
                continue
            if chunk is None:
                break
            text += chunk
            if re.search(r"login:", text):
                time.sleep(5)                                  # let the console redraw
                ppm = os.path.join(tempfile.gettempdir(), f"odvm-demo-{os.getpid()}.ppm")
                try:
                    screen.dump_ppm(ppm, mon)
                    rows = screen.art_rows(ppm)
                finally:
                    try:
                        os.remove(ppm)
                    except OSError:
                        pass
                break
    except (OSError, RuntimeError):
        pass
    finally:
        p.kill()
        p.wait()
        srv.shutdown()
    return screen.has_picture(rows), rows, text
