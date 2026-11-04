"""Finding and installing QEMU."""
import os
import platform
import shutil
import socket
import subprocess

from .i18n import t


def binary_name(arch):
    return "qemu-system-aarch64" if arch == "aarch64" else "qemu-system-arm"


def find_qemu(arch, explicit=None):
    if explicit:
        return explicit
    exe = binary_name(arch)
    found = shutil.which(exe)
    if found:
        return found
    if platform.system() == "Windows":
        for base in (r"C:\Program Files\qemu", r"C:\Program Files (x86)\qemu"):
            cand = shutil.which(exe, path=base)
            if cand:
                return cand
    return None


def is_termux():
    return "TERMUX_VERSION" in os.environ or "com.termux" in os.environ.get("PREFIX", "")


def install_command():
    """Return the QEMU install command (list) for this OS."""
    sysname = platform.system()
    if is_termux():
        return ["pkg", "install", "-y", "qemu-system-aarch64-headless",
                "qemu-system-arm-headless"]
    if sysname == "Windows":
        return ["winget", "install", "-e", "--id", "SoftwareFreedomConservancy.QEMU"]
    if sysname == "Darwin":
        return ["brew", "install", "qemu"]
    if shutil.which("apt-get"):
        return ["sudo", "apt-get", "install", "-y", "qemu-system-arm", "qemu-system-gui"]
    if shutil.which("dnf"):
        return ["sudo", "dnf", "install", "-y", "qemu-system-aarch64", "qemu-system-arm"]
    if shutil.which("pacman"):
        return ["sudo", "pacman", "-S", "--noconfirm", "qemu-system-aarch64", "qemu-system-arm"]
    return None


def install(dry_run=False):
    cmd = install_command()
    if not cmd:
        print(t("pm_missing"))
        return 1
    print(t("will_run"), " ".join(cmd))
    if dry_run:
        return 0
    return subprocess.call(cmd)


def host_accel(arch):
    """Hardware acceleration if the guest matches a 64-bit host.

    Android/Termux has no KVM. 32-bit (arm) guests are never accelerated on a
    64-bit host (most CPUs do not support the 32-bit guest mode).
    """
    m = platform.machine().lower()
    host64 = m in ("aarch64", "arm64")
    if is_termux() or not host64:
        return None
    if arch != "aarch64":
        return None
    system = platform.system()
    if system == "Linux":
        return "kvm" if os.access("/dev/kvm", os.R_OK | os.W_OK) else None
    return {"Windows": "whpx", "Darwin": "hvf"}.get(system)


def port_free(port, host="127.0.0.1"):
    """True if nothing is listening/bound on host:port."""
    for fam, addr in ((socket.AF_INET, host),):
        with socket.socket(fam, socket.SOCK_STREAM) as sk:
            sk.settimeout(0.3)
            if sk.connect_ex((addr, port)) == 0:
                return False
    return True


def free_port(start, span=50, exclude=()):
    """First free port in [start, start+span] not in `exclude`; None if none."""
    for p in range(start, start + span + 1):
        if p not in exclude and port_free(p):
            return p
    return None
