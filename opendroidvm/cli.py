import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
from dataclasses import asdict

from . import __version__, bootimg, launcher, profiles, qemu


def _list(a):
    items = profiles.load_all()
    if a.arch:
        items = [p for p in items if p.arch == a.arch]
    if a.soc:
        items = [p for p in items if a.soc.lower() in p.soc.lower()]
    if a.query:
        q = a.query.lower()
        items = [p for p in items if q in (p.id + p.codename + p.name).lower()]
    if a.min_ram:
        items = [p for p in items if p.ram_mb >= a.min_ram]
    if a.json:
        print(json.dumps([asdict(p) for p in items], ensure_ascii=False, indent=2))
        return 0
    for p in items:
        print(f"{p.id:14} {p.codename:12} {p.name} [{p.soc}, {p.arch}, {p.ram_mb}MB]")
    print(f"-- {len(items)} profil")
    return 0


def _info(a):
    p = profiles.find(a.device)
    if not p:
        print("Profil bulunamadi:", a.device, file=sys.stderr)
        return 1
    for k, v in vars(p).items():
        print(f"{k}: {v}")
    return 0


def _run(a):
    p = profiles.find(a.device)
    if not p:
        print("Profil bulunamadi:", a.device, file=sys.stderr)
        return 1
    for f in (a.recovery, a.boot, a.rom, a.userdata):
        if f and not os.path.isfile(f):
            print("Dosya bulunamadi:", f, file=sys.stderr)
            return 1
    o = launcher.Options(mode=a.mode, recovery=a.recovery or "", boot=a.boot or "",
                         rom=a.rom or "", userdata=a.userdata or "",
                         qemu_path=a.qemu or "", headless=a.headless,
                         ram=a.ram, cores=a.cores, adb_port=a.adb_port,
                         vnc=a.vnc, snapshot=a.snapshot)
    try:
        cmd = launcher.build(p, o)
    except bootimg.CorruptImage as e:
        print("Hata:", e, file=sys.stderr)
        return 1
    print(launcher.fmt(cmd))
    if qemu.is_termux() and not a.headless and a.vnc < 0:
        print("Not: Termux'ta ekran VNC ile acilir; bir VNC istemcisiyle localhost:5900'e baglan.",
              file=sys.stderr)
    if a.dry_run:
        return 0
    if not qemu.find_qemu(p.arch, a.qemu):
        print("QEMU bulunamadi. Kurmak icin: odvm install-qemu", file=sys.stderr)
        return 1
    return subprocess.call(cmd)


def _extract(a):
    try:
        k, r = bootimg.extract(a.image, a.out)
    except (ValueError, OSError) as e:
        print("Hata:", e, file=sys.stderr)
        return 1
    print("kernel :", k)
    print("ramdisk:", r)
    return 0


def _disk(a):
    if os.path.exists(a.path) and not a.force:
        print("Dosya zaten var (--force ile ustune yaz):", a.path, file=sys.stderr)
        return 1
    with open(a.path, "wb") as f:   # ham (raw) seyrek dosya, qemu-img gerekmez
        f.truncate(a.size_mb * 1024 * 1024)
    print(f"{a.path} olusturuldu ({a.size_mb} MB, raw, seyrek)")
    return 0


def _doctor(a):
    print("OpenDroidVM", __version__)
    if qemu.is_termux():
        print("Ortam  : Android (Termux) - KVM yok, TCG kullanilir, ekran VNC")
    print("Python :", platform.python_version(), platform.system(), platform.machine())
    print("CPU    :", os.cpu_count(), "mantiksal cekirdek")
    for arch in ("aarch64", "arm"):
        path = qemu.find_qemu(arch)
        ver = ""
        if path:
            try:
                ver = subprocess.check_output([path, "--version"], text=True).splitlines()[0]
            except (OSError, subprocess.CalledProcessError):
                ver = "(surum okunamadi)"
        print(f"{qemu.binary_name(arch):20}:", path or "YOK", ver)
        print(f"  hizlandirma ({arch}):", qemu.host_accel(arch) or "yok (TCG kullanilir)")
    print("Profil :", len(profiles.load_all()), "adet; kullanici klasoru:", profiles.user_dir())
    if platform.system() == "Linux" and not os.access("/dev/kvm", os.R_OK | os.W_OK):
        print("Not: /dev/kvm erisilebilir degil (KVM yok ya da kullanici 'kvm' grubunda degil).")
    return 0


REQUIRED = {"arch": ("aarch64", "arm"), "int": ("ram_mb", "cpu_cores")}


def _validate(a):
    bad = 0
    for p in profiles.load_all():
        errs = []
        if p.arch not in REQUIRED["arch"]:
            errs.append(f"arch gecersiz: {p.arch}")
        if p.ram_mb < 256 or p.cpu_cores < 1:
            errs.append("ram_mb/cpu_cores gecersiz")
        if min(p.width, p.height, p.dpi) <= 0:
            errs.append("ekran degerleri gecersiz")
        if not p.soc or not p.name:
            errs.append("name/soc bos")
        if errs:
            bad += 1
            print(f"HATA {p.id}: " + "; ".join(errs))
    print(f"{len(profiles.load_all())} profil kontrol edildi, {bad} hatali")
    return 1 if bad else 0


def _new(a):
    d = profiles.user_dir()
    d.mkdir(parents=True, exist_ok=True)
    path = d / f"{a.id.lower()}.json"
    if path.exists() and not a.force:
        print("Zaten var (--force):", path, file=sys.stderr)
        return 1
    data = {"name": a.name or a.id, "codename": a.codename or a.id, "soc": a.soc,
            "arch": a.arch, "cpu": "cortex-a15" if a.arch == "arm" else "cortex-a57",
            "ram_mb": a.ram, "cpu_cores": a.cores,
            "screen": {"width": a.width, "height": a.height, "dpi": a.dpi},
            "recovery": {"codename": a.codename or a.id, "projects": ["twrp", "orangefox"]}}
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    print("Olusturuldu:", path)
    return 0


def _install(a):
    return qemu.install(a.dry_run)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="odvm", description="OpenDroidVM")
    ap.add_argument("--version", action="version", version=__version__)
    sp = ap.add_subparsers(dest="cmd", required=True)

    s = sp.add_parser("list", help="profilleri listele/filtrele")
    s.add_argument("query", nargs="?", help="ad/kod adi icinde ara")
    s.add_argument("--arch", choices=["aarch64", "arm"])
    s.add_argument("--soc"); s.add_argument("--min-ram", type=int, default=0)
    s.add_argument("--json", action="store_true")
    s.set_defaults(f=_list)

    s = sp.add_parser("info"); s.add_argument("device"); s.set_defaults(f=_info)

    s = sp.add_parser("run", help="profili QEMU ile calistir")
    s.add_argument("device")
    s.add_argument("--mode", choices=["accurate", "fast"], default="accurate")
    s.add_argument("--recovery"); s.add_argument("--boot")
    s.add_argument("--rom", help="ROM/system imaji (pakete dahil degil)")
    s.add_argument("--userdata"); s.add_argument("--qemu")
    s.add_argument("--ram", type=int, default=0, help="RAM (MB), profili ezer")
    s.add_argument("--cores", type=int, default=0, help="cekirdek sayisi, profili ezer")
    s.add_argument("--adb-port", type=int, default=5555, help="0 = kapali")
    s.add_argument("--vnc", type=int, default=-1, help="VNC ekran no (5900+N)")
    s.add_argument("--snapshot", action="store_true", help="diske yazma")
    s.add_argument("--headless", action="store_true")
    s.add_argument("--dry-run", action="store_true")
    s.set_defaults(f=_run)

    s = sp.add_parser("extract", help="boot/recovery imajindan kernel+ramdisk cikar")
    s.add_argument("image"); s.add_argument("--out", default="extracted")
    s.set_defaults(f=_extract)

    s = sp.add_parser("create-disk", help="bos userdata diski olustur")
    s.add_argument("path"); s.add_argument("size_mb", type=int, nargs="?", default=4096)
    s.add_argument("--force", action="store_true")
    s.set_defaults(f=_disk)

    s = sp.add_parser("new", help="kendi cihaz profilini olustur")
    s.add_argument("id"); s.add_argument("--name"); s.add_argument("--codename")
    s.add_argument("--soc", default="Unknown"); s.add_argument("--arch", choices=["aarch64", "arm"], default="aarch64")
    s.add_argument("--ram", type=int, default=4096); s.add_argument("--cores", type=int, default=4)
    s.add_argument("--width", type=int, default=1080); s.add_argument("--height", type=int, default=2400)
    s.add_argument("--dpi", type=int, default=420); s.add_argument("--force", action="store_true")
    s.set_defaults(f=_new)
    sp.add_parser("validate", help="profilleri dogrula").set_defaults(f=_validate)
    sp.add_parser("doctor", help="QEMU/hizlandirma durumunu kontrol et").set_defaults(f=_doctor)
    s = sp.add_parser("install-qemu"); s.add_argument("--dry-run", action="store_true")
    s.set_defaults(f=_install)

    a = ap.parse_args(argv)
    return a.f(a)


if __name__ == "__main__":
    raise SystemExit(main())
