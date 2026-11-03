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
    assert any("hostfwd=tcp::6000-:5555" in x for x in c)
    assert "-snapshot" in c and "vnc=:1" in c


def test_user_profile(tmp_path, monkeypatch):
    import json
    monkeypatch.setenv("APPDATA", str(tmp_path))
    d = tmp_path / "opendroidvm" / "profiles"
    d.mkdir(parents=True)
    (d / "mydev.json").write_text(json.dumps({"name": "My Dev", "ram_mb": 999}))
    assert profiles.find("mydev").ram_mb == 999
