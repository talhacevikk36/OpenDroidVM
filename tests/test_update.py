import hashlib
import json
import os
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from opendroidvm import bootimg, cli, launcher, profiles, updater

EXE = b"NEWEXE" * 50000
DIGEST = "sha256:" + hashlib.sha256(EXE).hexdigest()


class Fake(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        base = f"http://127.0.0.1:{self.server.server_address[1]}"
        if self.path == "/latest":
            body = json.dumps({"tag_name": "v9.9.9", "assets": [
                {"name": "odvm-linux-x64", "browser_download_url": base + "/exe", "size": len(EXE), "digest": DIGEST},
                {"name": "odvm-windows-x64.exe", "browser_download_url": base + "/exe", "size": len(EXE), "digest": DIGEST},
                {"name": "odvm-macos", "browser_download_url": base + "/exe", "size": len(EXE), "digest": DIGEST},
                {"name": "opendroidvm-9.9.9-py3-none-any.whl", "browser_download_url": base + "/whl", "size": 1},
            ]}).encode()
        elif self.path == "/web/releases/latest":
            self.send_response(302); self.send_header("Location", "/web/releases/tag/v9.9.9")
            self.send_header("Content-Length", "0"); self.end_headers(); return
        elif self.path == "/forbidden":
            self.send_response(403); self.send_header("Content-Length", "0"); self.end_headers(); return
        elif self.path == "/exe":
            body = EXE
        else:
            self.send_response(404); self.end_headers(); return
        self.send_response(200); self.send_header("Content-Length", str(len(body))); self.end_headers()
        self.wfile.write(body)


@pytest.fixture()
def api(monkeypatch):
    srv = HTTPServer(("127.0.0.1", 0), Fake)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    monkeypatch.setenv("ODVM_UPDATE_API", f"http://127.0.0.1:{srv.server_address[1]}/latest")
    yield
    srv.shutdown()


def test_version_compare():
    assert updater.is_newer("v0.8.0", "0.7.5") and not updater.is_newer("v0.7.5", "0.7.5")
    assert updater.is_newer("v0.10.0", "0.9.9") and not updater.is_newer("0.7.4", "0.7.5")


def test_latest_release_and_offline(api, monkeypatch):
    info = updater.latest_release()
    assert info["tag"] == "v9.9.9" and "odvm-linux-x64" in info["assets"]
    monkeypatch.setenv("ODVM_UPDATE_API", "http://127.0.0.1:9/none")
    monkeypatch.setenv("ODVM_UPDATE_WEB", "http://127.0.0.1:9/web")
    assert updater.latest_release(timeout=1) is None          # offline: silent


def test_frozen_self_update_replaces_and_verifies(api, tmp_path, monkeypatch):
    fake_exe = tmp_path / "odvm"; fake_exe.write_bytes(b"OLD")
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(fake_exe))
    monkeypatch.setattr(updater.platform, "system", lambda: "Linux")
    ok, msg = updater.apply_update(updater.latest_release())
    assert ok and fake_exe.read_bytes() == EXE and os.access(fake_exe, os.X_OK)
    assert not (tmp_path / "odvm.new").exists()


def test_bad_checksum_is_rejected(api, tmp_path, monkeypatch):
    fake_exe = tmp_path / "odvm"; fake_exe.write_bytes(b"OLD")
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(fake_exe))
    monkeypatch.setattr(updater.platform, "system", lambda: "Linux")
    info = updater.latest_release()
    info["assets"]["odvm-linux-x64"]["digest"] = "sha256:" + "0" * 64
    ok, msg = updater.apply_update(info)
    assert not ok and "checksum" in msg and fake_exe.read_bytes() == b"OLD"


def test_windows_swap_keeps_old_aside(tmp_path, monkeypatch):
    cur = tmp_path / "odvm.exe"; cur.write_bytes(b"OLD")
    new = tmp_path / "odvm.exe.new"; new.write_bytes(b"NEW")
    monkeypatch.setattr(updater.os, "name", "nt")
    updater.replace_running_exe(str(new), cur)
    assert cur.read_bytes() == b"NEW" and (tmp_path / "odvm.exe.old").read_bytes() == b"OLD"


def test_pip_path_retries_with_break_system_packages(api, monkeypatch):
    calls = []
    monkeypatch.setattr(updater.subprocess, "call", lambda cmd: calls.append(cmd) or (1 if len(calls) == 1 else 0))
    ok, _ = updater.apply_update(updater.latest_release())
    assert ok and "--break-system-packages" in calls[1] and calls[0][-1].endswith("/whl")


def _tty(monkeypatch):
    monkeypatch.delenv("ODVM_NO_UPDATE_CHECK")
    monkeypatch.setattr(updater.sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr(updater.sys.stdout, "isatty", lambda: True)


def test_startup_offers_and_installs(api, monkeypatch, capsys):
    _tty(monkeypatch)
    monkeypatch.setattr("builtins.input", lambda p="": "y")
    monkeypatch.setattr(updater, "apply_update", lambda info: (True, info["tag"]))
    assert updater.check_and_offer() is True
    out = capsys.readouterr().out
    assert "v9.9.9" in out and "Updated to v9.9.9" in out


def test_decline_is_remembered_and_check_is_throttled(api, monkeypatch):
    _tty(monkeypatch)
    asked = []
    monkeypatch.setattr("builtins.input", lambda p="": asked.append(p) or "n")
    assert updater.check_and_offer() is False and len(asked) == 1
    assert updater.check_and_offer() is False and len(asked) == 1     # not asked again today


def test_no_check_without_terminal_or_when_disabled(api, monkeypatch):
    monkeypatch.setattr(updater, "latest_release", lambda *a, **k: pytest.fail("must not call the network"))
    assert updater.check_and_offer() is False                         # env var set by conftest


def test_update_command_check_only(api, capsys):
    assert cli.main(["update", "--check"]) == 0
    assert "v9.9.9" in capsys.readouterr().out


def test_up_to_date_message(monkeypatch, capsys):
    monkeypatch.setattr(updater, "latest_release", lambda *a, **k: {"tag": "v0.0.1", "assets": {}})
    assert cli.main(["update"]) == 0
    assert "latest version" in capsys.readouterr().out


# ---- display / serial diagnostics (Termux "Display output is not active")
def test_vnc_mode_shows_serial_console():
    c = launcher.build(profiles.find("pixel"), launcher.Options(vnc=0))
    assert "vnc=:0" in c and c[c.index("-serial") + 1] == "mon:stdio"


def _kernel(path, kind):
    b = bytearray(64)
    if kind == "arm64":
        b[56:60] = b"ARMd"
    elif kind == "arm32":
        b[36:40] = (0x016F2818).to_bytes(4, "little")
    path.write_bytes(bytes(b) + b"\0" * 100)
    return str(path)


def test_kernel_kind(tmp_path):
    assert bootimg.kernel_kind(_kernel(tmp_path / "a", "arm64")) == "arm64"
    assert bootimg.kernel_kind(_kernel(tmp_path / "b", "arm32")) == "arm32"
    assert bootimg.kernel_kind(_kernel(tmp_path / "c", "x")) == "unknown"


def test_warnings_explain_black_screen(tmp_path, capsys):
    p64, p32 = profiles.find("pixel"), profiles.find("s5")
    cli._boot_warnings(p64, ["qemu"])
    assert "nothing will boot" in capsys.readouterr().err
    cli._boot_warnings(p64, ["qemu", "-kernel", _kernel(tmp_path / "k32", "arm32")])
    assert "32-bit ARM kernel" in capsys.readouterr().err
    cli._boot_warnings(p32, ["qemu", "-kernel", _kernel(tmp_path / "k64", "arm64")])
    assert "64-bit ARM kernel" in capsys.readouterr().err
    good = tmp_path / "kok"
    k = bytearray(64); k[56:60] = b"ARMd"
    good.write_bytes(bytes(k) + b"arm,pl011 virtio_mmio virtio-gpu " * 3)
    cli._boot_warnings(p64, ["qemu", "-kernel", str(good)])
    assert capsys.readouterr().err == ""


def test_api_rate_limited_falls_back_to_web(api, monkeypatch):
    port = os.environ["ODVM_UPDATE_API"].split(":")[-1].split("/")[0]
    monkeypatch.setenv("ODVM_UPDATE_API", f"http://127.0.0.1:{port}/forbidden")     # 403 like a shared IP
    monkeypatch.setenv("ODVM_UPDATE_WEB", f"http://127.0.0.1:{port}/web")
    info = updater.latest_release()
    assert info["tag"] == "v9.9.9"
    assert info["assets"]["odvm-linux-x64"]["url"].endswith("/web/releases/download/v9.9.9/odvm-linux-x64")
    assert "opendroidvm-9.9.9-py3-none-any.whl" in info["assets"]


def test_web_fallback_offline_and_no_release(monkeypatch):
    monkeypatch.setenv("ODVM_UPDATE_API", "http://127.0.0.1:9/x")
    monkeypatch.setenv("ODVM_UPDATE_WEB", "http://127.0.0.1:9/web")
    assert updater.latest_release(timeout=1) is None


def test_tiny_download_without_metadata_is_refused(api, tmp_path, monkeypatch):
    fake_exe = tmp_path / "odvm"; fake_exe.write_bytes(b"OLD")
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(fake_exe))
    monkeypatch.setattr(updater.platform, "system", lambda: "Linux")
    info = updater.latest_release()
    a = info["assets"]["odvm-linux-x64"]; a["size"] = 0; a["digest"] = ""        # as in the web fallback
    ok, msg = updater.apply_update(info)
    assert not ok and fake_exe.read_bytes() == b"OLD"        # 300 KB < 1 MB -> refused
