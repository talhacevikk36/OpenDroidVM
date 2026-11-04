"""Builds the QEMU command line. Two modes:

* accurate: the profile's CPU model, cores and RAM are applied as-is.
* fast: hardware acceleration (KVM/WHPX/HVF) on a matching 64-bit host,
  otherwise multi-threaded TCG; cores are capped to the host, `-cpu max`.
"""
import os
import platform
import shlex
from dataclasses import dataclass

from . import bootimg, qemu


@dataclass
class Options:
    mode: str = "accurate"      # accurate | fast
    recovery: str = ""
    boot: str = ""
    rom: str = ""               # system image (ROM is supplied separately)
    userdata: str = ""
    qemu_path: str = ""
    headless: bool = False
    ram: int = 0                # MB, 0 = profile value
    cores: int = 0              # 0 = profile value
    adb_port: int = 5555        # 0 = no adb forward
    vnc: int = -1               # >=0: VNC display number (5900+n)
    snapshot: bool = False      # do not write to disk
    monitor_port: int = 5556    # for odvm key; 0 = off, 127.0.0.1 only


def effective_vnc(o):
    """(vnc display, reason). Falls back to VNC when there is no window system."""
    if o.vnc >= 0 or o.headless:
        return o.vnc, None
    if qemu.is_termux():
        return 0, "termux"
    if platform.system() == "Linux" and not (os.environ.get("DISPLAY")
                                             or os.environ.get("WAYLAND_DISPLAY")):
        return 0, "nodisplay"
    return -1, None


def build(profile, o, workdir=None):
    arch = profile.arch
    exe = qemu.find_qemu(arch, o.qemu_path or None) or qemu.binary_name(arch)
    cpu, cores = profile.cpu, o.cores or profile.cpu_cores
    ram = o.ram or profile.ram_mb
    accel = "tcg"
    if o.mode == "fast":
        hw = qemu.host_accel(arch)
        if hw:
            accel, cpu = hw, "host"
        else:
            accel, cpu = "tcg,thread=multi,tb-size=512", "max"
        cores = max(1, min(cores, os.cpu_count() or 2))
    cmd = [exe, "-machine", profile.machine, "-accel", accel,
           "-cpu", cpu, "-smp", str(cores), "-m", str(ram),
           "-name", profile.name]
    img = o.recovery or o.boot
    if img:
        kernel, ramdisk = img, None
        try:
            kernel, ramdisk = bootimg.extract(img, workdir or bootimg.cache_dir(img))
        except bootimg.NotBootImage:
            pass  # probably a raw kernel (Image) already
        cmd += ["-kernel", str(kernel)]
        if ramdisk:
            cmd += ["-initrd", str(ramdisk)]
        cmd += ["-append", profile.cmdline]
    for i, path in enumerate(p for p in (o.rom, o.userdata) if p):
        opts = ",cache=unsafe,aio=threads" if o.mode == "fast" else ""
        cmd += ["-drive", f"file={path},format=raw,if=none,id=d{i}{opts}",
                "-device", f"virtio-blk-device,drive=d{i}"]
    cmd += ["-device", f"virtio-gpu-pci,xres={profile.width},yres={profile.height}",
            "-device", "virtio-tablet-pci", "-device", "virtio-keyboard-pci"]
    net = "user,id=n0" + (f",hostfwd=tcp::{o.adb_port}-:5555" if o.adb_port else "")
    cmd += ["-netdev", net, "-device", "virtio-net-pci,netdev=n0"]
    if o.monitor_port:
        cmd += ["-monitor", f"tcp:127.0.0.1:{o.monitor_port},server,nowait"]
    if o.snapshot:
        cmd += ["-snapshot"]
    vnc, _ = effective_vnc(o)
    if vnc >= 0:
        cmd += ["-display", f"vnc=:{vnc}"]
    elif o.headless:
        cmd += ["-display", "none", "-serial", "stdio"]
    return cmd


def fmt(cmd):
    return " ".join(shlex.quote(c) for c in cmd)
