"""QEMU komut satiri olusturma. Iki mod:

* accurate: profilin CPU modeli, cekirdek ve RAM'i birebir uygulanir.
* fast: ayni mimaride donanim hizlandirma (KVM/WHPX/HVF), degilse cok
  iplikli TCG; cekirdek sayisi konaga gore sinirlanir, `-cpu max` kullanilir.
"""
import os
import shlex
from dataclasses import dataclass
from pathlib import Path

from . import bootimg, qemu


@dataclass
class Options:
    mode: str = "accurate"      # accurate | fast
    recovery: str = ""
    boot: str = ""
    rom: str = ""               # system imaji (ROM ayri verilir)
    userdata: str = ""
    qemu_path: str = ""
    headless: bool = False
    ram: int = 0                # MB, 0 = profil degeri
    cores: int = 0              # 0 = profil degeri
    adb_port: int = 5555        # 0 = adb yonlendirme yok
    vnc: int = -1               # >=0: VNC ekran numarasi (5900+n)
    snapshot: bool = False      # diske yazmadan calis


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
            pass  # zaten ham kernel (Image) olabilir
        cmd += ["-kernel", str(kernel)]
        if ramdisk:
            cmd += ["-initrd", str(ramdisk)]
        cmd += ["-append", profile.cmdline]
    for i, path in enumerate(p for p in (o.rom, o.userdata) if p):
        cmd += ["-drive", f"file={path},format=raw,if=none,id=d{i}",
                "-device", f"virtio-blk-device,drive=d{i}"]
    cmd += ["-device", f"virtio-gpu-pci,xres={profile.width},yres={profile.height}",
            "-device", "virtio-tablet-pci", "-device", "virtio-keyboard-pci"]
    net = "user,id=n0" + (f",hostfwd=tcp::{o.adb_port}-:5555" if o.adb_port else "")
    cmd += ["-netdev", net, "-device", "virtio-net-pci,netdev=n0"]
    if o.snapshot:
        cmd += ["-snapshot"]
    vnc = o.vnc
    if vnc < 0 and not o.headless and qemu.is_termux():
        vnc = 0  # Termux'ta pencere yok: VNC (localhost:5900) kullan
    if vnc >= 0:
        cmd += ["-display", f"vnc=:{vnc}"]
    elif o.headless:
        cmd += ["-display", "none", "-serial", "stdio"]
    return cmd


def fmt(cmd):
    return " ".join(shlex.quote(c) for c in cmd)
