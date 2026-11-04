import io
import struct
import tarfile
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from opendroidvm import cli, profiles, recovery

def _make_img():
    page = 2048
    h = bytearray(page); h[:8] = b"ANDROID!"
    struct.pack_into("<III", h, 8, 1024, 0, 1024); struct.pack_into("<I", h, 36, page)
    return bytes(h) + b"K" * 1024 + b"\0" * (page - 1024) + b"R" * 1024 + b"\0" * (page - 1024)


IMG = _make_img()


def _tar_bytes():
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w") as tf:
        ti = tarfile.TarInfo("recovery.img"); ti.size = len(IMG)
        tf.addfile(ti, io.BytesIO(IMG))
    return buf.getvalue()


class Fake(BaseHTTPRequestHandler):
    """Mimics dl.twrp.me: listing page + image that needs a Referer."""
    def log_message(self, *a):
        pass

    def _send(self, code, body, ctype="text/html"):
        self.send_response(code); self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body))); self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        p = self.path
        if p == "/herolte/":
            page = ('<a href="/herolte/twrp-3.7.0_9-0-herolte.img.html">new</a>'
                    '<a href="/herolte/twrp-3.6.0_9-0-herolte.img.html">old</a>')
            return self._send(200, page.encode())
        if p == "/klte/":
            return self._send(200, b'<a href="/klte/twrp-3.7.0_9-0-klte.img.tar.html">x</a>')
        if p.startswith("/herolte/twrp-") and p.endswith(".img"):
            if ".img.html" not in (self.headers.get("Referer") or ""):
                return self._send(200, b"<!DOCTYPE html><html>blocked</html>")
            return self._send(200, IMG, "application/octet-stream")
        if p == "/klte/twrp-3.7.0_9-0-klte.img.tar":
            return self._send(200, _tar_bytes(), "application/x-tar")
        self._send(404, b"nope")


@pytest.fixture()
def server(monkeypatch):
    srv = HTTPServer(("127.0.0.1", 0), Fake)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    monkeypatch.setenv("ODVM_TWRP_HOST", f"http://127.0.0.1:{srv.server_address[1]}")
    yield
    srv.shutdown()


def test_list_and_download_newest(server, tmp_path):
    assert recovery.list_files("herolte")[0].startswith("twrp-3.7.0")
    out = recovery.download("herolte", tmp_path)
    assert out.read_bytes()[:8] == b"ANDROID!" and "3.7.0" in out.name
    assert "dl.twrp.me" in (tmp_path / "SOURCE.txt").read_text() or "127.0.0.1" in (tmp_path / "SOURCE.txt").read_text()
    assert not list(tmp_path.glob("*.part"))


def test_version_pick(server, tmp_path):
    assert "3.6.0" in recovery.download("herolte", tmp_path, version="3.6.0").name
    with pytest.raises(recovery.FetchError):
        recovery.download("herolte", tmp_path, version="9.9.9")


def test_tar_is_unpacked(server, tmp_path):
    out = recovery.download("klte", tmp_path)
    assert out.name.endswith(".img") and out.read_bytes()[:8] == b"ANDROID!"


def test_missing_page_and_bad_name(server, tmp_path):
    with pytest.raises(recovery.FetchError):
        recovery.list_files("nosuchdevice")
    with pytest.raises(recovery.FetchError):
        recovery.list_files("../etc")


def test_cli_fetch_and_auto(server, tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    assert cli.main(["fetch-recovery", "s7", "--out", "recovery"]) == 0
    assert recovery.find_local("s7", "recovery").exists()
    assert cli.main(["fetch-recovery", "pixel"]) == 1          # 404 on the fake server
    assert cli.main(["fetch-recovery"]) == 1                     # nothing requested
    assert cli.main(["run", "s7", "--recovery", "auto", "--dry-run"]) == 0
    assert cli.main(["run", "s8", "--recovery", "auto", "--dry-run"]) == 1


def test_recommended_are_real_profiles():
    assert len(recovery.RECOMMENDED) == 20
    assert all(profiles.find(i) for i in recovery.RECOMMENDED)
