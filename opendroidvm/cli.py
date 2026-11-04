import argparse
import json
import os
import platform
import subprocess
import sys
from dataclasses import asdict

from . import __version__, bootimg, i18n, keys, launcher, panel, profiles, qemu
from .i18n import t


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
    print(t("n_profiles", n=len(items)))
    return 0


def _info(a):
    p = profiles.find(a.device)
    if not p:
        print(t("profile_not_found", x=a.device), file=sys.stderr)
        return 1
    for k, v in vars(p).items():
        print(f"{k}: {v}")
    return 0


def _resolve_ports(o):
    """Avoid colliding with another VM / a real emulator on the same ports."""
    for attr, what in (("adb_port", t("port_adb")), ("monitor_port", None)):
        old = getattr(o, attr)
        other = o.monitor_port if attr == "adb_port" else o.adb_port
        if old and (not qemu.port_free(old) or old == other):
            new = qemu.free_port(old + 1, exclude={other, old})
            if new is None:
                print(t("no_free_port", x=old), file=sys.stderr)
                return False
            setattr(o, attr, new)
            print(t("port_moved", old=old, new=new,
                    what=what or t("port_monitor", new=new)), file=sys.stderr)
    return True


def _run(a):
    p = profiles.find(a.device)
    if not p:
        print(t("profile_not_found", x=a.device), file=sys.stderr)
        return 1
    for f in (a.recovery, a.boot, a.rom, a.userdata):
        if f and not os.path.isfile(f):
            print(t("file_not_found", x=f), file=sys.stderr)
            return 1
    o = launcher.Options(mode=a.mode, recovery=a.recovery or "", boot=a.boot or "",
                         rom=a.rom or "", userdata=a.userdata or "",
                         qemu_path=a.qemu or "", headless=a.headless,
                         ram=a.ram, cores=a.cores, adb_port=a.adb_port,
                         vnc=a.vnc, snapshot=a.snapshot, monitor_port=a.monitor_port)
    if not a.dry_run and not _resolve_ports(o):
        return 1
    try:
        cmd = launcher.build(p, o)
    except bootimg.CorruptImage as e:
        print(t("bad_image", x=e), file=sys.stderr)
        return 1
    print(launcher.fmt(cmd))
    vnc, reason = launcher.effective_vnc(o)
    if reason:
        print(t("termux_vnc" if reason == "termux" else "nodisplay_vnc", port=5900 + vnc),
              file=sys.stderr)
    if a.dry_run:
        return 0
    if not qemu.find_qemu(p.arch, a.qemu):
        print(t("qemu_missing"), file=sys.stderr)
        return 1
    return subprocess.call(cmd)


def _extract(a):
    try:
        k, r = bootimg.extract(a.image, a.out)
    except (ValueError, OSError) as e:
        print(t("bad_image", x=e), file=sys.stderr)
        return 1
    print("kernel :", k)
    print("ramdisk:", r)
    return 0


def _disk(a):
    if os.path.exists(a.path) and not a.force:
        print(t("disk_exists", x=a.path), file=sys.stderr)
        return 1
    with open(a.path, "wb") as f:   # raw sparse file, no qemu-img needed
        f.truncate(a.size_mb * 1024 * 1024)
    print(t("disk_created", path=a.path, mb=a.size_mb))
    return 0


def _doctor(a):
    print("OpenDroidVM", __version__)
    if qemu.is_termux():
        print(t("doctor_termux"))
    print("Python :", platform.python_version(), platform.system(), platform.machine())
    print("CPU    :", t("doctor_cpu", n=os.cpu_count()))
    for arch in ("aarch64", "arm"):
        path = qemu.find_qemu(arch)
        ver = ""
        if path:
            try:
                ver = subprocess.check_output([path, "--version"], text=True).splitlines()[0]
            except (OSError, subprocess.CalledProcessError):
                ver = t("doctor_ver")
        print(f"{qemu.binary_name(arch):20}:", path or t("missing"), ver)
        print(t("doctor_accel", arch=arch, x=qemu.host_accel(arch) or t("doctor_none")))
    print(t("doctor_profiles", n=len(profiles.load_all()), d=profiles.user_dir()))
    if platform.system() == "Linux" and not qemu.is_termux() \
            and not os.access("/dev/kvm", os.R_OK | os.W_OK):
        print(t("doctor_nokvm"))
    return 0


def _validate(a):
    bad = 0
    items = profiles.load_all()
    for p in items:
        errs = []
        if p.arch not in ("aarch64", "arm"):
            errs.append(t("err_arch", x=p.arch))
        if p.ram_mb < 256 or p.cpu_cores < 1:
            errs.append(t("err_ram"))
        if min(p.width, p.height, p.dpi) <= 0:
            errs.append(t("err_screen"))
        if not p.soc or not p.name:
            errs.append(t("err_name"))
        if errs:
            bad += 1
            print(f"ERROR {p.id}: " + "; ".join(errs))
    print(t("validated", n=len(items), bad=bad))
    return 1 if bad else 0


def _new(a):
    if not profiles.SAFE_ID.match(a.id) or a.id.startswith("."):
        print(t("bad_id"), file=sys.stderr)
        return 1
    d = profiles.user_dir()
    d.mkdir(parents=True, exist_ok=True)
    path = d / f"{a.id.lower()}.json"
    if path.exists() and not a.force:
        print(t("exists", x=path), file=sys.stderr)
        return 1
    data = {"name": a.name or a.id, "codename": a.codename or a.id, "soc": a.soc,
            "arch": a.arch, "cpu": "cortex-a15" if a.arch == "arm" else "cortex-a57",
            "ram_mb": a.ram, "cpu_cores": a.cores,
            "screen": {"width": a.width, "height": a.height, "dpi": a.dpi},
            "recovery": {"codename": a.codename or a.id, "projects": ["twrp", "orangefox"]}}
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(t("created", x=path))
    return 0


def _key(a):
    if a.list or not a.name:
        for k, (q, code) in sorted(keys.KEYS.items()):
            print(f"{k:9} qemu={q or '-':12} android={code}")
        return 0
    try:
        sent = keys.press(a.name, a.via, a.port, a.hold, a.serial)
    except KeyError as e:
        print(e.args[0], file=sys.stderr)
        return 1
    except (OSError, RuntimeError, subprocess.CalledProcessError) as e:
        print(t("key_fail", e=e, port=a.port), file=sys.stderr)
        return 1
    print(t("key_sent", x=sent))
    return 0


def _panel(a):
    try:
        panel.run(a.port, a.via, a.serial)
    except RuntimeError as e:
        print(e, file=sys.stderr)
        return 1
    return 0


def _install(a):
    return qemu.install(a.dry_run)


def _pre_lang(argv):
    """Language must be known before building --help texts."""
    argv = sys.argv[1:] if argv is None else argv
    for i, x in enumerate(argv):
        if x == "--lang" and i + 1 < len(argv):
            i18n.set_lang(argv[i + 1])
        elif x.startswith("--lang="):
            i18n.set_lang(x.split("=", 1)[1])


def main(argv=None):
    _pre_lang(argv)
    ap = argparse.ArgumentParser(prog="odvm", description="OpenDroidVM")
    ap.add_argument("--version", action="version", version=__version__)
    ap.add_argument("--lang", choices=sorted(i18n.M), help=t("h_lang"))
    sp = ap.add_subparsers(dest="cmd", required=True)

    s = sp.add_parser("list", help=t("h_list"))
    s.add_argument("query", nargs="?")
    s.add_argument("--arch", choices=["aarch64", "arm"])
    s.add_argument("--soc"); s.add_argument("--min-ram", type=int, default=0)
    s.add_argument("--json", action="store_true")
    s.set_defaults(f=_list)

    s = sp.add_parser("info"); s.add_argument("device"); s.set_defaults(f=_info)

    s = sp.add_parser("run", help=t("h_run"))
    s.add_argument("device")
    s.add_argument("--mode", choices=["accurate", "fast"], default="accurate")
    s.add_argument("--recovery"); s.add_argument("--boot")
    s.add_argument("--rom", help=t("h_rom"))
    s.add_argument("--userdata"); s.add_argument("--qemu")
    s.add_argument("--ram", type=int, default=0, help=t("h_ram"))
    s.add_argument("--cores", type=int, default=0, help=t("h_cores"))
    s.add_argument("--adb-port", type=int, default=5555, help=t("h_adbport"))
    s.add_argument("--vnc", type=int, default=-1, help=t("h_vnc"))
    s.add_argument("--snapshot", action="store_true", help=t("h_snap"))
    s.add_argument("--monitor-port", type=int, default=keys.DEFAULT_MONITOR_PORT,
                   help=t("h_monitor"))
    s.add_argument("--headless", action="store_true")
    s.add_argument("--dry-run", action="store_true")
    s.set_defaults(f=_run)

    s = sp.add_parser("extract", help=t("h_extract"))
    s.add_argument("image"); s.add_argument("--out", default="extracted")
    s.set_defaults(f=_extract)

    s = sp.add_parser("create-disk", help=t("h_disk"))
    s.add_argument("path"); s.add_argument("size_mb", type=int, nargs="?", default=4096)
    s.add_argument("--force", action="store_true")
    s.set_defaults(f=_disk)

    s = sp.add_parser("new", help=t("h_new"))
    s.add_argument("id"); s.add_argument("--name"); s.add_argument("--codename")
    s.add_argument("--soc", default="Unknown")
    s.add_argument("--arch", choices=["aarch64", "arm"], default="aarch64")
    s.add_argument("--ram", type=int, default=4096); s.add_argument("--cores", type=int, default=4)
    s.add_argument("--width", type=int, default=1080); s.add_argument("--height", type=int, default=2400)
    s.add_argument("--dpi", type=int, default=420); s.add_argument("--force", action="store_true")
    s.set_defaults(f=_new)

    for nm, fn in (("key", _key), ("panel", _panel)):
        s = sp.add_parser(nm, help=t("h_" + nm))
        if nm == "key":
            s.add_argument("name", nargs="?", help="volup voldown power home back menu mute recents")
            s.add_argument("--list", action="store_true")
            s.add_argument("--hold", type=int, default=0, help=t("h_hold"))
        s.add_argument("--via", choices=["monitor", "adb"], default="monitor")
        s.add_argument("--port", type=int, default=keys.DEFAULT_MONITOR_PORT)
        s.add_argument("--serial", default="localhost:5555")
        s.set_defaults(f=fn)

    sp.add_parser("validate", help=t("h_validate")).set_defaults(f=_validate)
    sp.add_parser("doctor", help=t("h_doctor")).set_defaults(f=_doctor)
    s = sp.add_parser("install-qemu", help=t("h_install")); s.add_argument("--dry-run", action="store_true")
    s.set_defaults(f=_install)

    a = ap.parse_args(argv)
    return a.f(a)


if __name__ == "__main__":
    raise SystemExit(main())
