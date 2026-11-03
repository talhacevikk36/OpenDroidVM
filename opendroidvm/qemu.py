"""QEMU bulma ve kurma."""
import platform
import shutil
import subprocess


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


def install_command():
    """Isletim sistemine gore QEMU kurulum komutu (liste) dondurur."""
    sysname = platform.system()
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
        print("Paket yoneticisi bulunamadi; QEMU'yu elle kurun: https://www.qemu.org/download/")
        return 1
    print("Calistirilacak:", " ".join(cmd))
    if dry_run:
        return 0
    return subprocess.call(cmd)


def host_accel(arch):
    """Konuk mimarisi konakla ayniysa donanim hizlandirmasi dondurur."""
    m = platform.machine().lower()
    host64 = m in ("aarch64", "arm64")
    host_arm = host64 or m.startswith("arm")
    if not host_arm or (arch == "aarch64" and not host64):
        return None
    return {"Linux": "kvm", "Windows": "whpx", "Darwin": "hvf"}.get(platform.system())
