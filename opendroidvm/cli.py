import argparse
import json
import os
import platform
import shlex
import subprocess
import sys
import time
import urllib.error
from pathlib import Path
from dataclasses import asdict

from . import (__version__, avd, bootimg, compat, config, extras, i18n, kernelscan, keys, launcher,
                   panel, profiles, qemu, recovery, screen, selftest, state, ui, updater)
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
        tag = compat.label(p.id)
        print(f"{p.id:14} {p.codename:12} {p.name} [{p.soc}, {p.arch}, {p.ram_mb}MB]"
              + (f"  <{tag}>" if tag else ""))
    print(t("n_profiles", n=len(items)))
    return 0


def _not_found(pid):
    print(t("profile_not_found", x=pid), file=sys.stderr)
    near = profiles.suggest(pid)
    if near:
        print(t("did_you_mean", x=", ".join(near)), file=sys.stderr)


def _info(a):
    p = profiles.find(a.device)
    if not p:
        _not_found(a.device)
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


def _qemu_ready(arch, explicit=None, assume_yes=False):
    """True if QEMU exists; otherwise offer to install it (asks unless assume_yes)."""
    if qemu.find_qemu(arch, explicit):
        return True
    if assume_yes or (sys.stdin.isatty() and ui.yes(t("ask_install"))):
        qemu.install()
        if qemu.find_qemu(arch, explicit):
            return True
        print(t("install_failed"), file=sys.stderr)
    else:
        print(t("qemu_missing"), file=sys.stderr)
    return False


def print_scan(r):
    print(t("chk_head", arch=r.arch, comp=r.compression))
    for key in ("virt_machine", "uart", "virtio_mmio", "virtio_pci", "virtio_gpu", "virtio_input"):
        if key == "virt_machine" and r.arch != "arm32":
            continue
        print(f"  [{'x' if r.found.get(key) else ' '}] {t('chk_item_' + key)}")
    if r.vendor:
        print(t("chk_vendor", v=r.vendor))
    if r.verdict == "no":
        print(t("chk_v_no", why=t("chk_why_" + r.reason)))
    elif r.verdict == "unknown":
        print(t("chk_v_unknown", comp=r.compression))
    else:
        print(t("chk_v_" + r.verdict))


def _check(a):
    target = a.target
    if not os.path.isfile(target):
        local = recovery.find_local(target)
        if not local:
            print(t("chk_usage"), file=sys.stderr)
            return 1
        target = str(local)
    try:
        r = kernelscan.scan_file(target)
    except (OSError, bootimg.CorruptImage) as e:
        print(t("bad_image", x=e), file=sys.stderr)
        return 1
    print(target)
    print_scan(r)
    return 0 if r.verdict in ("yes", "serial") else 2


def _boot_warnings(p, cmd):
    """Explain up front why a VM would stay black."""
    if "-kernel" not in cmd:
        print(t("warn_no_kernel"), file=sys.stderr)
        return None
    kpath = cmd[cmd.index("-kernel") + 1]
    kind = bootimg.kernel_kind(kpath)
    if kind == "arm32" and p.arch == "aarch64":
        print(t("warn_k32"), file=sys.stderr)
    elif kind == "arm64" and p.arch == "arm":
        print(t("warn_k64"), file=sys.stderr)
    try:
        r = kernelscan.scan_file(kpath)
    except OSError:
        return None
    if r.verdict == "no":
        print(t("chk_v_no", why=t("chk_why_" + r.reason)), file=sys.stderr)
    elif r.verdict == "serial":
        print(t("chk_v_serial"), file=sys.stderr)
    elif r.verdict == "unknown" and kind == "unknown":
        print(t("warn_kunk"), file=sys.stderr)
    return r.verdict


def launch(p, o, dry_run=False, assume_yes=False):
    """Resolve ports, build the QEMU command, print it and (unless dry_run) run it."""
    if not dry_run and not _resolve_ports(o):
        return 1
    try:
        cmd = launcher.build(p, o)
    except bootimg.CorruptImage as e:
        print(t("bad_image", x=e), file=sys.stderr)
        return 1
    print(launcher.fmt(cmd))
    ram, capped = launcher.effective_ram(p, o)
    if capped:
        print(t("ram_capped", want=o.ram or p.ram_mb, ram=ram), file=sys.stderr)
    verdict = _boot_warnings(p, cmd)
    vnc, reason = launcher.effective_vnc(o)
    if reason:
        print(t("termux_vnc" if reason == "termux" else "nodisplay_vnc", port=5900 + vnc),
              file=sys.stderr)
    if vnc >= 0 and not dry_run:
        print(t("display_hint"), file=sys.stderr)
    if dry_run:
        return 0
    if verdict == "no" and not assume_yes and sys.stdin.isatty() \
            and not ui.yes(t("ask_anyway"), default=False):
        return 1
    if not _qemu_ready(p.arch, o.qemu_path or None, assume_yes):
        return 1
    cmd = launcher.build(p, o)          # path may have changed after installing QEMU
    state.write(p.id, o.monitor_port, o.adb_port, vnc)
    try:
        return subprocess.call(cmd)
    finally:
        state.clear()


def _run(a):
    p = profiles.find(a.device)
    if not p:
        _not_found(a.device)
        return 1
    if a.recovery == "auto":
        a.recovery = recovery.find_local(p.id)
        if not a.recovery:
            print(t("auto_missing", id=p.id, out=recovery.default_dir()), file=sys.stderr)
            return 1
        a.recovery = str(a.recovery)
    for f in (a.recovery, a.boot, a.rom, a.userdata):
        if f and not os.path.isfile(f):
            print(t("file_not_found", x=f), file=sys.stderr)
            return 1
    o = launcher.Options(mode=a.mode, recovery=a.recovery or "", boot=a.boot or "",
                         rom=a.rom or "", userdata=a.userdata or "",
                         qemu_path=a.qemu or "", headless=a.headless,
                         ram=a.ram, cores=a.cores, adb_port=a.adb_port,
                         vnc=a.vnc, snapshot=a.snapshot, monitor_port=a.monitor_port,
                         log=a.log or "")
    if a.export:
        dest = extras.write_script(launcher.build(p, o), a.export)
        print(t("export_ok", x=dest))
        return 0
    return launch(p, o, a.dry_run)


def progress_bar():
    """Progress callback for downloads; silent when output is not a terminal."""
    if not sys.stderr.isatty():
        return None
    state = {"last": -1}

    def cb(name, done, total):
        pct = int(done * 100 / total) if total else 0
        if pct != state["last"]:
            state["last"] = pct
            sys.stderr.write("\r" + t("dl_progress", name=name, pct=pct,
                                      done=round(done / 1048576, 1),
                                      total=round(total / 1048576, 1) if total else "?"))
            sys.stderr.flush()
    return cb


def compat_note(p):
    """Message when the measured data says this phone's official TWRP cannot boot in QEMU."""
    m = compat.get(p.id)
    if m and m["verdict"] == "no":
        return t("compat_no", name=p.name, why=t("chk_why_" + m["reason"]), id=p.id)
    return ""


def _compat_ok(p, assume_yes, interactive=False):
    note = compat_note(p)
    if not note:
        return True
    print(note, file=sys.stderr)
    if assume_yes or not (interactive or sys.stdin.isatty()):
        return True
    return ui.yes(t("ask_continue"), default=False)


def _start(a):
    """One command: QEMU if needed -> TWRP if needed -> run."""
    p = profiles.find(a.device)
    if not p:
        _not_found(a.device)
        return 1
    if not a.dry_run and not _qemu_ready(p.arch, None, a.yes):
        print(t("start_need_qemu"), file=sys.stderr)
        return 1
    img = a.recovery or recovery.find_local(p.id)
    if not img and not _compat_ok(p, a.yes):
        return 1
    if not img:
        try:
            img = recovery.fetch_profile(p, None, a.version, progress_bar())
            sys.stderr.write("\n") if sys.stderr.isatty() else None
        except recovery.FetchError as e:
            print(t("fetch_fail", id=p.id, why=e), file=sys.stderr)
            return 1
    o = launcher.Options(mode=a.mode, recovery=str(img))
    return launch(p, o, a.dry_run, a.yes)


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


def _port(a):
    return getattr(a, "port", None) or state.read().get("monitor_port") or keys.DEFAULT_MONITOR_PORT


def _vm(a):
    port = _port(a)
    cmds = {"stop": "quit", "reset": "system_reset", "pause": "stop", "resume": "cont",
            "status": "info status"}
    try:
        reply = keys.monitor_cmd(cmds[a.action], port)
    except OSError as e:
        print(t("key_fail", e=e, port=port), file=sys.stderr)
        return 1
    print(reply or t("vm_done", x=a.action))
    return 0


def _shot(a):
    port = _port(a)
    out = a.out or time.strftime("odvm-%Y%m%d-%H%M%S.png")
    try:
        w, h = screen.take(out, port)
    except OSError as e:
        print(t("key_fail", e=e, port=port), file=sys.stderr)
        return 1
    except (RuntimeError, ValueError) as e:
        print(e, file=sys.stderr)
        return 1
    print(t("shot_ok", x=out, w=w, h=h))
    return 0


def _selftest(a):
    exe = a.qemu or qemu.find_qemu("aarch64")
    if not exe and not _qemu_ready("aarch64", None, a.yes):
        return 1
    print(t("st_start"))
    try:
        ok, text = selftest.run(a.qemu or None, a.kernel, a.initrd, a.expect, a.timeout, progress_bar())
    except (OSError, urllib.error.URLError) as e:
        print(t("st_net", e=e), file=sys.stderr)
        return 1
    if sys.stderr.isatty():
        sys.stderr.write("\n")
    lines = [x for x in text.splitlines() if x.strip()]
    print("\n".join(lines[-6:]))
    print(t("st_pass") if ok else t("st_fail"))
    return 0 if ok else 1


def _avd(a):
    if a.action == "doctor":
        for k, v in avd.doctor().items():
            print(f"{k:11}: {v or t('missing')}")
        return 0
    p = profiles.find(a.device or "")
    if not p:
        _not_found(a.device or "")
        return 1
    try:
        if a.action == "create":
            print(t("avd_created", x=avd.create(p, a.image)))
            return 0
        cmd = avd.run_cmd(p, shlex.split(a.emu_args))
    except RuntimeError as e:
        print(e, file=sys.stderr)
        print(t("avd_need_sdk"), file=sys.stderr)
        return 1
    print(launcher.fmt(cmd))
    return 0 if a.dry_run else subprocess.call(cmd)


def _clone(a):
    dest = extras.clone(a.src, a.new, a.name, a.ram, a.cores)
    if not dest:
        _not_found(a.src) if not profiles.find(a.src) else print(t("bad_id"), file=sys.stderr)
        return 1
    print(t("created", x=dest))
    return 0


def _config(a):
    try:
        if a.action == "set":
            print(f"{a.key} = {config.set_value(a.key, a.value)}")
        elif a.action == "unset":
            config.unset(a.key)
        elif a.action == "get":
            print(config.get(a.key, ""))
        else:
            for k, v in sorted(config.load().items()):
                print(f"{k} = {v}")
    except KeyError:
        print(t("cfg_unknown", x=a.key, v=", ".join(config.SCHEMA)), file=sys.stderr)
        return 1
    except (ValueError, TypeError):
        print(t("cfg_bad", k=a.key, v=a.value), file=sys.stderr)
        return 1
    return 0


def _clean(a):
    for label, path, size in extras.clean(a.recovery, a.dry_run):
        print(t("clean_line", label=label, path=path, mb=round(size / 1048576, 1),
                what=t("clean_would") if a.dry_run else t("clean_removed")))
    return 0


def _completion(a):
    cmds = [c for c in _SUBCOMMANDS]
    print(extras.completion(a.shell, cmds, [p.id for p in profiles.load_all()]))
    return 0


_SUBCOMMANDS = []


def _key(a):
    if a.list or not a.name:
        for k, (q, code) in sorted(keys.KEYS.items()):
            print(f"{k:9} qemu={q or '-':12} android={code}")
        return 0
    try:
        sent = keys.press(a.name, a.via, _port(a), a.hold, a.serial)
    except KeyError as e:
        print(e.args[0], file=sys.stderr)
        return 1
    except (OSError, RuntimeError, subprocess.CalledProcessError) as e:
        print(t("key_fail", e=e, port=_port(a)), file=sys.stderr)
        return 1
    print(t("key_sent", x=sent))
    return 0


def _panel(a):
    try:
        panel.run(_port(a), a.via, a.serial)
    except RuntimeError as e:
        print(e, file=sys.stderr)
        return 1
    return 0


def _fetch(a):
    ids = list(recovery.RECOMMENDED) if a.all else list(a.devices)
    a.out = a.out or str(recovery.default_dir())
    if not ids:
        print(t("fetch_none"), file=sys.stderr)
        return 1
    ok, lines = 0, []
    for pid in ids:
        p = profiles.find(pid)
        good, why = None, ""
        if not p:
            why = t("profile_not_found", x=pid)
        else:
            try:
                good = recovery.fetch_profile(p, a.out, a.version, progress_bar())
                if sys.stderr.isatty():
                    sys.stderr.write("\n")
            except recovery.FetchError as e:
                why = str(e)
        if good:
            ok += 1
            mb = round(os.path.getsize(good) / 1048576, 1)
            print(t("fetch_ok", id=pid, path=good, mb=mb))
            extra = ""
            if a.check or a.annotate:
                try:
                    r = kernelscan.scan_file(good)
                    extra = f" | boot={r.verdict}:{r.reason or '-'} arch={r.arch} soc={r.vendor or '-'}"
                    if a.check:
                        print_scan(r)
                except (OSError, bootimg.CorruptImage) as e:
                    extra = f" | boot=error:{e}"
            lines.append(f"{pid} OK {good.name} {mb}MB{extra}")
        else:
            print(t("fetch_fail", id=pid, why=why), file=sys.stderr)
            lines.append(f"{pid} FAIL {why}")
            if not p:
                near = profiles.suggest(pid)
                if near:
                    print(t("did_you_mean", x=", ".join(near)), file=sys.stderr)
    print(t("fetch_summary", ok=ok, n=len(ids), out=a.out))
    if a.annotate:   # GitHub limits annotations per step, so send ONE line + a summary file
        print("::notice::" + " | ".join(lines)[:3500])
        Path(a.out).mkdir(parents=True, exist_ok=True)
        (Path(a.out) / "REPORT.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
        summary = os.environ.get("GITHUB_STEP_SUMMARY")
        if summary:
            with open(summary, "a", encoding="utf-8") as f:
                f.write("### fetch-recovery\n" + "\n".join("- " + x for x in lines) + "\n")
    return 0 if ok else 1


def _wizard(a=None):
    from . import wizard
    return wizard.run()


def _update(a):
    updater.check_and_offer(force=True, assume_yes=a.yes, only_check=a.check)
    return 0


def _install(a):
    return qemu.install(a.dry_run)


def _pre_lang(argv):
    """Language must be known before building --help texts."""
    argv = sys.argv[1:] if argv is None else argv
    if not os.environ.get("ODVM_LANG") and config.get("lang"):
        i18n.set_lang(config.get("lang"))
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
    sp = ap.add_subparsers(dest="cmd")

    s = sp.add_parser("list", help=t("h_list"))
    s.add_argument("query", nargs="?")
    s.add_argument("--arch", choices=["aarch64", "arm"])
    s.add_argument("--soc"); s.add_argument("--min-ram", type=int, default=0)
    s.add_argument("--json", action="store_true")
    s.set_defaults(f=_list)

    s = sp.add_parser("info"); s.add_argument("device"); s.set_defaults(f=_info)

    s = sp.add_parser("run", help=t("h_run"))
    s.add_argument("device")
    s.add_argument("--mode", choices=["accurate", "fast"], default=config.get("mode", "accurate"))
    s.add_argument("--recovery", help="image path, or 'auto' = newest downloaded recovery")
    s.add_argument("--boot")
    s.add_argument("--rom", help=t("h_rom"))
    s.add_argument("--userdata"); s.add_argument("--qemu", default=config.get("qemu"))
    s.add_argument("--ram", type=int, default=0, help=t("h_ram"))
    s.add_argument("--cores", type=int, default=0, help=t("h_cores"))
    s.add_argument("--adb-port", type=int, default=config.get("adb_port", 5555), help=t("h_adbport"))
    s.add_argument("--vnc", type=int, default=-1, help=t("h_vnc"))
    s.add_argument("--snapshot", action="store_true", help=t("h_snap"))
    s.add_argument("--monitor-port", type=int, default=keys.DEFAULT_MONITOR_PORT,
                   help=t("h_monitor"))
    s.add_argument("--headless", action="store_true")
    s.add_argument("--log", metavar="FILE", help="also save the serial console to FILE")
    s.add_argument("--export", metavar="FILE", help="write a .sh/.bat launch script instead of running")
    s.add_argument("--dry-run", action="store_true")
    s.set_defaults(f=_run)

    s = sp.add_parser("start", help=t("h_start"))
    s.add_argument("device")
    s.add_argument("--mode", choices=["accurate", "fast"], default=config.get("mode", "fast"))
    s.add_argument("--recovery", help="use this image instead of the downloaded TWRP")
    s.add_argument("--version", help="TWRP version, e.g. 3.7.0")
    s.add_argument("--yes", "-y", action="store_true", help=t("h_yes"))
    s.add_argument("--dry-run", action="store_true")
    s.set_defaults(f=_start)
    s = sp.add_parser("update", help=t("h_update"))
    s.add_argument("--check", action="store_true", help="only report")
    s.add_argument("--yes", "-y", action="store_true", help=t("h_yes"))
    s.set_defaults(f=_update)
    s = sp.add_parser("check", help=t("h_check"))
    s.add_argument("target", help="image file or device id")
    s.set_defaults(f=_check)
    sp.add_parser("wizard", help=t("h_wizard")).set_defaults(f=_wizard)

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
        s.add_argument("--port", type=int, default=None, help="monitor port (default: the running VM's)")
        s.add_argument("--serial", default="localhost:5555")
        s.set_defaults(f=fn)

    s = sp.add_parser("fetch-recovery", help=t("h_fetch"))
    s.add_argument("devices", nargs="*")
    s.add_argument("--all", action="store_true", help=t("h_fetch_all"))
    s.add_argument("--out", default=None, help=t("h_fetch_out"))
    s.add_argument("--version", help="e.g. 3.7.0")
    s.add_argument("--check", action="store_true", help="also check whether each kernel can boot on QEMU")
    s.add_argument("--annotate", action="store_true", help=argparse.SUPPRESS)
    s.set_defaults(f=_fetch)
    s = sp.add_parser("vm", help=t("h_vm"))
    s.add_argument("action", choices=["stop", "reset", "pause", "resume", "status"])
    s.add_argument("--port", type=int, default=None)
    s.set_defaults(f=_vm)
    s = sp.add_parser("screenshot", help=t("h_shot"))
    s.add_argument("--out", help="PNG file name")
    s.add_argument("--port", type=int, default=None)
    s.set_defaults(f=_shot)
    s = sp.add_parser("selftest", help=t("h_selftest"))
    s.add_argument("--kernel"); s.add_argument("--initrd"); s.add_argument("--qemu")
    s.add_argument("--expect", default="Linux version", help="regex that must appear on the serial console")
    s.add_argument("--timeout", type=int, default=150)
    s.add_argument("--yes", "-y", action="store_true", help=t("h_yes"))
    s.set_defaults(f=_selftest)
    s = sp.add_parser("avd", help=t("h_avd"))
    s.add_argument("action", choices=["doctor", "create", "run"])
    s.add_argument("device", nargs="?")
    s.add_argument("--image", help="e.g. system-images;android-34;google_apis;x86_64")
    s.add_argument("--dry-run", action="store_true")
    s.add_argument("--emu-args", default="", help='extra emulator arguments, e.g. "--emu-args=-no-snapshot -gpu host"')
    s.set_defaults(f=_avd)
    s = sp.add_parser("clone", help=t("h_clone"))
    s.add_argument("src"); s.add_argument("new"); s.add_argument("--name")
    s.add_argument("--ram", type=int, default=0); s.add_argument("--cores", type=int, default=0)
    s.set_defaults(f=_clone)
    s = sp.add_parser("config", help=t("h_config"))
    s.add_argument("action", nargs="?", default="list", choices=["list", "get", "set", "unset"])
    s.add_argument("key", nargs="?"); s.add_argument("value", nargs="?")
    s.set_defaults(f=_config)
    s = sp.add_parser("clean", help=t("h_clean"))
    s.add_argument("--recovery", action="store_true", help="also delete downloaded recoveries")
    s.add_argument("--dry-run", action="store_true")
    s.set_defaults(f=_clean)
    s = sp.add_parser("completion", help=t("h_completion"))
    s.add_argument("shell", choices=["bash", "zsh", "powershell"])
    s.set_defaults(f=_completion)
    sp.add_parser("validate", help=t("h_validate")).set_defaults(f=_validate)
    sp.add_parser("doctor", help=t("h_doctor")).set_defaults(f=_doctor)
    s = sp.add_parser("install-qemu", help=t("h_install")); s.add_argument("--dry-run", action="store_true")
    s.set_defaults(f=_install)

    _SUBCOMMANDS[:] = list(sp.choices)
    a = ap.parse_args(argv)
    updater.cleanup_old()
    if a.cmd not in ("update", "key") and updater.check_and_offer():
        return 0                        # updated: ask the user to start odvm again
    if not a.cmd:                       # plain `odvm`: guided start in a terminal, else help
        if sys.stdin.isatty():
            return _wizard()
        ap.print_help()
        return 0
    try:
        return a.f(a)
    except BrokenPipeError:              # e.g. `odvm list | head`
        try:
            os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno())
        except (OSError, ValueError):
            pass
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
