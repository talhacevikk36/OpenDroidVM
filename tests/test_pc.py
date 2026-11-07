import json
import os
import socket
import struct
import sys
import threading
import zlib

import pytest

from opendroidvm import (avd, bootimg, cli, compat, compat_data, config, extras, kernelscan, keys,
                         launcher, paths, profiles, qemu, recovery, screen, selftest, state)


# ---------- bugs found on real images / real machines
def test_samsung_header_version_garbage_is_not_v3():
    page = 2048
    h = bytearray(page); h[:8] = b"ANDROID!"
    struct.pack_into("<III", h, 8, 1024, 0, 1024)
    struct.pack_into("<I", h, 36, page)
    struct.pack_into("<I", h, 40, 579584)                 # real value seen in the Galaxy S7 TWRP
    img = bytes(h) + b"K" * 1024 + b"\0" * 1024 + b"R" * 1024 + b"\0" * 1024
    k, r = bootimg.parse(img)
    assert k == b"K" * 1024 and r == b"R" * 1024


def test_adb_forward_is_local_only():
    c = launcher.build(profiles.find("pixel"), launcher.Options(adb_port=5555))
    assert any("hostfwd=tcp:127.0.0.1:5555-:5555" in x for x in c)
    assert not any("hostfwd=tcp::" in x for x in c)         # never exposed to the network


def test_commas_in_paths_are_escaped(tmp_path):
    d = tmp_path / "a,b"; d.mkdir(); f = d / "sys.img"; f.write_bytes(b"0")
    c = launcher.build(profiles.find("pixel"), launcher.Options(rom=str(f)))
    drive = next(x for x in c if x.startswith("file="))
    assert "a,,b" in drive


def test_windows_command_quoting(monkeypatch):
    monkeypatch.setattr(launcher.os, "name", "nt")
    out = launcher.fmt(["C:\\Program Files\\qemu\\qemu-system-aarch64.exe", "-name", "My Phone"])
    assert out.startswith('"C:\\Program Files') and '"My Phone"' in out and "'" not in out


def test_ram_is_capped_on_small_machines(monkeypatch):
    monkeypatch.setattr(qemu, "host_ram_mb", lambda: 1000)
    p = profiles.find("s10")                                # wants 8192
    ram, capped = launcher.effective_ram(p, launcher.Options())
    assert capped and ram == 448
    c = launcher.build(p, launcher.Options())
    assert c[c.index("-m") + 1] == "448"
    assert launcher.effective_ram(p, launcher.Options(ram=256)) == (256, False)
    monkeypatch.setattr(qemu, "host_ram_mb", lambda: 64000)
    assert launcher.effective_ram(p, launcher.Options()) == (8192, False)


def test_vm_state_gives_ports_to_key_commands(monkeypatch):
    state.write("pixel", 5601, 5602, -1)
    assert state.read()["monitor_port"] == 5601

    class A: port = None
    assert cli._port(A()) == 5601
    state.clear()
    assert cli._port(A()) == keys.DEFAULT_MONITOR_PORT


def test_os_folders(monkeypatch):
    monkeypatch.setenv("XDG_CACHE_HOME", "/x/cache")
    assert str(paths.cache_root()).replace("\\", "/") == "/x/cache/opendroidvm"
    monkeypatch.setenv("ODVM_HOME", "/x/home")
    assert str(paths.data_root()).replace("\\", "/") == "/x/home"


def test_recovery_dir_rules(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert recovery.default_dir() == paths.data_root() / "recovery"
    (tmp_path / "recovery").mkdir()
    assert str(recovery.default_dir()) == "recovery"
    monkeypatch.setenv("ODVM_RECOVERY_DIR", str(tmp_path / "elsewhere"))
    assert recovery.default_dir() == tmp_path / "elsewhere"


# ---------- LZ4 (Pixel kernels) + scanner
def _lz4_legacy(data):
    n = len(data) - 15
    ext = bytes([255] * (n // 255)) + bytes([n % 255])
    block = bytes([0xF0]) + ext + data                     # literals-only block
    return b"\x02\x21\x4c\x18" + struct.pack("<I", len(block)) + block


def test_lz4_decoder_handles_matches_and_literals():
    block = bytes([0x44]) + b"abcd" + b"\x04\x00"          # "abcd" + copy 8 bytes from offset 4
    legacy = b"\x02\x21\x4c\x18" + struct.pack("<I", len(block)) + block
    assert kernelscan.lz4_legacy(legacy) == b"abcdabcdabcd"
    big = os.urandom(1000) + b"x" * 5000
    assert kernelscan.lz4_legacy(_lz4_legacy(big)) == big


def test_scan_reads_lz4_kernels():
    head = bytearray(64); head[56:60] = b"ARMd"
    payload = b"arm,pl011 virtio_mmio virtio_gpu " + b"\0" * 200_000
    r = kernelscan.scan_bytes(bytes(head) + _lz4_legacy(payload))
    assert r.verdict == "yes" and r.compression == "lz4"


def test_scan_result_is_cached(tmp_path, monkeypatch):
    f = tmp_path / "k"; f.write_bytes(b"\0" * 56 + b"ARMd" + b"qcom,x " * 20 + b"\0" * 100)
    first = kernelscan.scan_file(str(f))
    monkeypatch.setattr(kernelscan, "scan_bytes", lambda k: pytest.fail("should come from cache"))
    assert kernelscan.scan_file(str(f)) == first


# ---------- new features
def test_compat_label_and_note(monkeypatch, capsys):
    monkeypatch.setitem(compat_data.MEASURED, "s10", {"verdict": "no", "reason": "no_uart", "arch": "arm64", "soc": "x"})
    assert compat.label("s10") == "twrp:no-boot" and compat.label("pixel4a") == ""
    assert "will NOT boot in QEMU" in cli.compat_note(profiles.find("s10"))
    cli.main(["list", "s10"])
    assert "<twrp:no-boot>" in capsys.readouterr().out


def test_export_scripts(tmp_path, capsys):
    sh, bat = tmp_path / "go.sh", tmp_path / "go.bat"
    assert cli.main(["run", "pixel", "--export", str(sh), "--adb-port", "0", "--monitor-port", "0"]) == 0
    assert sh.read_text().startswith("#!/bin/sh\nexec ") and os.access(sh, os.X_OK)
    cli.main(["run", "pixel", "--export", str(bat), "--adb-port", "0", "--monitor-port", "0"])
    data = bat.read_bytes()
    assert data.startswith(b"@echo off\r\n") and b"\r\r" not in data and data.endswith(b"\r\n")
    assert b"\r" not in sh.read_bytes()


def test_clone_profile():
    assert cli.main(["clone", "s10", "s10big", "--ram", "12288", "--name", "My S10"]) == 0
    p = profiles.find("s10big")
    assert (p.ram_mb, p.name, p.soc) == (12288, "My S10", "Exynos 9820")
    assert cli.main(["clone", "s10", "../evil"]) == 1 and cli.main(["clone", "nope", "x"]) == 1


def test_config_roundtrip_and_validation(capsys):
    assert cli.main(["config", "set", "mode", "fast"]) == 0
    assert config.get("mode") == "fast"
    assert cli.main(["config", "set", "mode", "turbo"]) == 1
    assert cli.main(["config", "set", "nonsense", "1"]) == 1
    assert cli.main(["config", "set", "update_check", "off"]) == 0 and config.get("update_check") is False
    assert cli.main(["config", "set", "adb_port", "6000"]) == 0 and config.get("adb_port") == 6000
    capsys.readouterr()
    assert cli.main(["config"]) == 0 and "mode = fast" in capsys.readouterr().out
    cli.main(["config", "unset", "mode"]); assert config.get("mode") is None


def test_config_switches_off_update_check(monkeypatch):
    from opendroidvm import updater
    monkeypatch.delenv("ODVM_NO_UPDATE_CHECK")
    monkeypatch.setattr(updater.sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr(updater.sys.stdout, "isatty", lambda: True)
    monkeypatch.setattr(updater, "latest_release", lambda *a, **k: pytest.fail("network"))
    config.set_value("update_check", "false")
    assert updater.check_and_offer() is False


def test_clean(tmp_path, capsys):
    c = paths.cache_root(); c.mkdir(parents=True); (c / "x").write_bytes(b"1" * 2048)
    r = recovery.default_dir() / "s7"; r.mkdir(parents=True); (r / "a.img").write_bytes(b"1" * 4096)
    assert cli.main(["clean", "--recovery", "--dry-run"]) == 0
    assert (c / "x").exists() and (r / "a.img").exists() and "would remove" in capsys.readouterr().out
    cli.main(["clean"])
    assert not c.exists() and (r / "a.img").exists()          # recoveries survive a plain clean
    cli.main(["clean", "--recovery"]); assert not r.exists()


def test_completion_scripts(capsys):
    assert cli.main(["completion", "bash"]) == 0
    out = capsys.readouterr().out
    assert "complete -F _odvm odvm" in out and "selftest" in out and "pixel3" in out
    cli.main(["completion", "powershell"])
    assert "Register-ArgumentCompleter" in capsys.readouterr().out


def test_ppm_to_png(tmp_path):
    ppm = tmp_path / "a.ppm"
    ppm.write_bytes(b"P6\n# c\n2 2\n255\n" + bytes([255, 0, 0, 0, 255, 0, 0, 0, 255, 9, 9, 9]))
    out = tmp_path / "a.png"
    assert screen.ppm_to_png(str(ppm), str(out)) == (2, 2)
    d = out.read_bytes()
    assert d[:8] == b"\x89PNG\r\n\x1a\n"
    idat = d[d.index(b"IDAT") + 4:d.index(b"IEND") - 8]
    raw = zlib.decompress(idat)
    assert raw[0] == 0 and raw[1:4] == bytes([255, 0, 0]) and len(raw) == 2 * (1 + 6)


class FakeMonitor:
    """Minimal HMP monitor: replies to 'info status' and records commands."""
    def __init__(self):
        self.srv = socket.socket(); self.srv.bind(("127.0.0.1", 0)); self.srv.listen(5)
        self.port = self.srv.getsockname()[1]; self.cmds = []
        threading.Thread(target=self.loop, daemon=True).start()

    def loop(self):
        while True:
            try:
                c, _ = self.srv.accept()
            except OSError:
                return
            c.sendall(b"QEMU monitor\r\n(qemu) ")
            buf = c.recv(4096).decode().strip(); self.cmds.append(buf)
            c.sendall((buf + "\r\n").encode())
            if buf == "info status":
                c.sendall(b"VM status: running\r\n")
            c.sendall(b"(qemu) "); c.close()


def test_vm_control_commands(capsys):
    m = FakeMonitor()
    assert cli.main(["vm", "status", "--port", str(m.port)]) == 0
    assert "VM status: running" in capsys.readouterr().out
    cli.main(["vm", "reset", "--port", str(m.port)]); cli.main(["vm", "stop", "--port", str(m.port)])
    assert m.cmds == ["info status", "system_reset", "quit"]
    assert cli.main(["vm", "status", "--port", "9"]) == 1          # nothing listening


def test_screenshot_reports_missing_display(tmp_path, monkeypatch, capsys):
    m = FakeMonitor()                                              # accepts screendump but writes nothing
    monkeypatch.setattr(screen.time, "sleep", lambda s: None)
    assert cli.main(["screenshot", "--port", str(m.port), "--out", str(tmp_path / "s.png")]) == 1
    assert "has not started a display" in capsys.readouterr().err


def test_avd_config_patching():
    ini = "avd.ini.encoding=UTF-8\nhw.ramSize=2048\nhw.lcd.width = 320\nfoo=bar\n"
    out = avd.patch_ini(ini, {"hw.ramSize": 8192, "hw.lcd.width": 1440, "hw.keyboard": "yes"})
    assert "hw.ramSize=8192" in out and "hw.lcd.width=1440" in out and "foo=bar" in out
    assert out.count("hw.ramSize") == 1 and out.rstrip().endswith("hw.keyboard=yes")
    u = avd.config_updates(profiles.find("s10"))
    assert (u["hw.lcd.width"], u["hw.lcd.height"], u["hw.lcd.density"], u["hw.ramSize"]) == (1440, 3040, 550, 8192)


def test_avd_without_sdk_explains(monkeypatch, capsys):
    monkeypatch.setattr(avd, "tool", lambda n: None)
    assert cli.main(["avd", "create", "s10"]) == 1
    assert "Android SDK" in capsys.readouterr().err
    assert cli.main(["avd", "run", "s10"]) == 1
    assert cli.main(["avd", "doctor"]) == 0


def test_avd_run_command(monkeypatch, capsys):
    monkeypatch.setattr(avd, "tool", lambda n: "/sdk/emulator/emulator")
    assert cli.main(["avd", "run", "s10", "--dry-run", "--emu-args=-no-snapshot"]) == 0
    assert "-avd odvm_s10 -no-snapshot" in capsys.readouterr().out


def test_selftest_logic():
    ok, text = selftest.boot([sys.executable, "-c", "print('boot'); print('Linux version 6.1')"], "Linux version", 20)
    assert ok and "Linux version" in text
    ok, _ = selftest.boot([sys.executable, "-c", "import time; print('x'); time.sleep(30)"], "NEVER", 2)
    assert not ok
    cmd = selftest.command("/q", "/k", "/i")
    assert "-kernel" in cmd and "console=ttyAMA0 earlycon" in cmd


def test_selftest_command_reports_result(monkeypatch, capsys):
    monkeypatch.setattr(cli.qemu, "find_qemu", lambda a, e=None: "/q")
    monkeypatch.setattr(cli.selftest, "run", lambda *a, **k: (True, "Linux version 6.1\n"))
    assert cli.main(["selftest"]) == 0 and "PASS" in capsys.readouterr().out
    monkeypatch.setattr(cli.selftest, "run", lambda *a, **k: (False, "nothing\n"))
    assert cli.main(["selftest"]) == 1


def test_wizard_warns_about_unbootable_recovery(monkeypatch, capsys):
    monkeypatch.setitem(compat_data.MEASURED, "s7", {"verdict": "no", "reason": "no_uart", "arch": "arm64", "soc": ""})
    answers = iter(["galaxy s7 (", "1", "n"])                               # pick S7, then decline "continue anyway"
    monkeypatch.setattr("builtins.input", lambda p="": next(answers))
    from opendroidvm import wizard
    assert wizard.run() == 0
    assert "will NOT boot in QEMU" in capsys.readouterr().err


def test_monitor_echo_with_cursor_codes_is_cleaned():
    raw = "i\x1b[K\x1b[Din\x1b[K\x1b[D\x1b[Dinf\x1b[K\x1b[D\x1b[D\x1b[Dinfo\x1b[K"
    assert keys.render_terminal(raw) == "info"
    assert keys.render_terminal("VM status: running") == "VM status: running"


def test_vendor_hint_only_for_single_vendor_kernels():
    head = bytearray(64); head[56:60] = b"ARMd"
    phone = bytes(head) + b"qcom,x " * 40 + b"samsung,exynos " * 2 + b"\0" * 100
    generic = bytes(head) + b"qcom,x " * 40 + b"mediatek,y " * 30 + b"\0" * 100
    assert kernelscan.scan_bytes(phone).vendor == "Qualcomm"
    assert kernelscan.scan_bytes(generic).vendor == ""         # distro kernels list many vendors


def test_measured_table_matches_what_we_ship():
    assert len(compat_data.MEASURED) == 20
    assert all(profiles.find(i) for i in compat_data.MEASURED)
    assert compat.get("s4")["reason"] == "no_virt" and compat.get("s7")["reason"] == "no_uart"
    assert compat.label("s10") == "twrp:no-boot" and compat.label("pixel2") == "twrp:?"


# ---------- display demo (Alpine with a GPU driver)
def _ppm(path, w=160, h=384, content_rows=6):
    pix = bytearray(w * h * 3)
    for r in range(content_rows):
        for y in range(r * 64, r * 64 + 8):
            for x in range(16, 120):
                pix[(y * w + x) * 3:(y * w + x) * 3 + 3] = b"\xdd\xdd\xdd"
    with open(path, "wb") as f:
        f.write(f"P6\n{w} {h}\n255\n".encode() + bytes(pix))


def test_art_rows_and_picture_detection(tmp_path):
    f = tmp_path / "a.ppm"
    _ppm(str(f), content_rows=6)
    rows = screen.art_rows(str(f))
    assert sum(1 for r in rows if "#" in r) == 6 and screen.has_picture(rows)
    _ppm(str(f), content_rows=1)                         # QEMU's 'Display output is not active' = one line
    assert not screen.has_picture(screen.art_rows(str(f)))


def test_display_command_has_gpu_modloop_and_monitor():
    c = selftest.display_command("/q", "/k", "/i", 8123, vnc=2, monitor_port=5700)
    j = " ".join(c)
    assert "virtio-gpu-pci" in j and "modloop=http://10.0.2.2:8123/modloop-virt" in j
    assert "console=tty0 console=ttyAMA0" in j and "vnc=:2" in j and "tcp:127.0.0.1:5700" in j
    assert "mon:stdio" in " ".join(selftest.display_command("/q", "/k", "/i", 1, interactive=True))
    assert c[c.index("-display") + 1] == "vnc=:2"
    assert selftest.display_command("/q", "/k", "/i", 1)[c.index("-display") + 1] == "none"


def test_check_display_sees_a_picture(tmp_path, monkeypatch):
    import io

    class FakeProc:
        stdout = io.BytesIO(b"booting\nWelcome to Alpine Linux\nlocalhost login: \n")
        def kill(self): pass
        def wait(self): return 0
    monkeypatch.setattr(selftest.subprocess, "Popen", lambda *a, **k: FakeProc())
    monkeypatch.setattr(selftest.time, "sleep", lambda s: None)
    monkeypatch.setattr(selftest.screen, "dump_ppm", lambda path, port: _ppm(path) or path)
    ok, rows, text = selftest.check_display("/q", ["k", "i", "m"], tmp_path, timeout=10)
    assert ok and "login:" in text and any("#" in r for r in rows)
    monkeypatch.setattr(selftest.screen, "dump_ppm", lambda path, port: (_ for _ in ()).throw(RuntimeError("none")))
    FakeProc.stdout = io.BytesIO(b"login:\n")
    ok, rows, _ = selftest.check_display("/q", ["k", "i", "m"], tmp_path, timeout=10)
    assert not ok and rows == []


def test_selftest_display_and_linux_commands(monkeypatch, capsys, tmp_path):
    monkeypatch.setattr(cli.qemu, "find_qemu", lambda a, e=None: "/q")
    monkeypatch.setattr(cli.selftest, "prepare_display", lambda progress=None: (["k", "i", "m"], tmp_path))
    rows = ["#####....", "###......", "######...", "####.....", "#########", "##.......", "........."]
    monkeypatch.setattr(cli.selftest, "check_display", lambda *a, **k: (True, rows, "login:"))
    assert cli.main(["selftest", "--display"]) == 0
    out = capsys.readouterr().out
    assert "PASS" in out and "#####" in out
    monkeypatch.setattr(cli.selftest, "check_display", lambda *a, **k: (False, [], "kernel panic\n"))
    assert cli.main(["selftest", "--display"]) == 1
    ran = []
    monkeypatch.setattr(cli.subprocess, "call", lambda cmd: ran.append(cmd) or 0)
    assert cli.main(["linux", "--vnc", "3"]) == 0
    assert "vnc=:3" in " ".join(ran[0]) and "mon:stdio" in ran[0]
    assert "localhost:5903" in capsys.readouterr().err
