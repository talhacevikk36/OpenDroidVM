import struct
from opendroidvm import profiles, launcher, bootimg


def test_profile_count():
    assert len(profiles.load_all()) >= 40


def test_modes():
    p = profiles.find("pixel")
    acc = launcher.build(p, launcher.Options(mode="accurate"))
    fast = launcher.build(p, launcher.Options(mode="fast"))
    assert acc[acc.index("-cpu") + 1] == p.cpu
    assert fast[fast.index("-cpu") + 1] in ("host", "max")


def test_bootimg_v0():
    page = 2048
    hdr = bytearray(page)
    hdr[:8] = b"ANDROID!"
    struct.pack_into("<III", hdr, 8, 4, 0, 4)
    struct.pack_into("<I", hdr, 36, page)
    data = bytes(hdr) + b"KERN" + b"\0" * (page - 4) + b"RAMD"
    k, r = bootimg.parse(data)
    assert k == b"KERN" and r == b"RAMD"


def test_overrides_and_net():
    p = profiles.find("pixel")
    c = launcher.build(p, launcher.Options(ram=1024, cores=2, adb_port=6000, vnc=1, snapshot=True))
    assert c[c.index("-m") + 1] == "1024"
    assert any("hostfwd=tcp:127.0.0.1:6000-:5555" in x for x in c)
    assert "-snapshot" in c and "vnc=:1" in c


def test_user_profile(tmp_path, monkeypatch):
    import json
    monkeypatch.setenv("APPDATA", str(tmp_path))
    d = tmp_path / "opendroidvm" / "profiles"
    d.mkdir(parents=True)
    (d / "mydev.json").write_text(json.dumps({"name": "My Dev", "ram_mb": 999}))
    assert profiles.find("mydev").ram_mb == 999


def test_corrupt_and_raw(tmp_path):
    import pytest
    page = 2048
    hdr = bytearray(page); hdr[:8] = b"ANDROID!"
    import struct
    struct.pack_into("<III", hdr, 8, 999999, 0, 4); struct.pack_into("<I", hdr, 36, page)
    with pytest.raises(bootimg.CorruptImage):
        bootimg.parse(bytes(hdr))
    with pytest.raises(bootimg.NotBootImage):
        bootimg.parse(b"RAWKERNEL" * 10)


def test_32bit_guest_never_hw_accel():
    from opendroidvm import qemu
    assert qemu.host_accel("arm") is None


def test_validate_all_profiles():
    from opendroidvm import cli
    assert cli.main(["validate"]) == 0


def test_keys_and_monitor_flag():
    from opendroidvm import keys
    import pytest
    assert keys.canon("Vol+") == "volup" and keys.KEYS["power"][1] == 26
    with pytest.raises(KeyError):
        keys.canon("nope")
    c = launcher.build(profiles.find("pixel"), launcher.Options())
    assert "tcp:127.0.0.1:5556,server,nowait" in c
    c = launcher.build(profiles.find("pixel"), launcher.Options(monitor_port=0))
    assert "-monitor" not in c


def test_fast_drive_cache(tmp_path):
    f = tmp_path / "s.img"; f.write_bytes(b"0")
    c = launcher.build(profiles.find("pixel"), launcher.Options(mode="fast", rom=str(f)))
    assert any("cache=unsafe" in x for x in c)


def test_i18n_switch():
    from opendroidvm import i18n
    i18n.set_lang("tr"); assert "bulunamadi" in i18n.t("profile_not_found", x="a")
    i18n.set_lang("en"); assert "not found" in i18n.t("profile_not_found", x="a")
    i18n.set_lang(None)


def test_path_traversal_blocked(tmp_path, monkeypatch):
    from opendroidvm import cli
    monkeypatch.setenv("APPDATA", str(tmp_path))
    assert profiles.find("../../etc/passwd") is None
    assert profiles.find("..") is None
    assert cli.main(["new", "../evil"]) == 1
    assert not list(tmp_path.rglob("evil*"))


def test_no_display_falls_back_to_vnc(monkeypatch):
    import platform
    from opendroidvm import qemu
    monkeypatch.setattr(platform, "system", lambda: "Linux")
    monkeypatch.setattr(qemu, "is_termux", lambda: False)
    monkeypatch.delenv("DISPLAY", raising=False); monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)
    assert launcher.effective_vnc(launcher.Options()) == (0, "nodisplay")
    assert launcher.effective_vnc(launcher.Options(headless=True)) == (-1, None)
    monkeypatch.setenv("DISPLAY", ":0")
    assert launcher.effective_vnc(launcher.Options()) == (-1, None)


def test_busy_port_is_skipped():
    import socket
    from opendroidvm import qemu
    s = socket.socket(); s.bind(("127.0.0.1", 0)); s.listen(1)
    busy = s.getsockname()[1]
    try:
        assert not qemu.port_free(busy)
        assert qemu.free_port(busy) != busy
    finally:
        s.close()


def test_ports_never_collide(monkeypatch):
    from opendroidvm import cli, qemu
    monkeypatch.setattr(qemu, "port_free", lambda p, host="127.0.0.1": p not in (5555, 5556))
    o = launcher.Options()
    assert cli._resolve_ports(o)
    assert o.adb_port != o.monitor_port and 5555 not in (o.adb_port, o.monitor_port) \
        and 5556 not in (o.adb_port, o.monitor_port)


def test_zero_page_size_is_corrupt_not_crash():
    import pytest
    hdr = bytearray(4096); hdr[:8] = b"ANDROID!"
    struct.pack_into("<III", hdr, 8, 100, 0, 100)   # page size left at 0
    with pytest.raises(bootimg.CorruptImage):
        bootimg.parse(bytes(hdr))
