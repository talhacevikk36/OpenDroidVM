import gzip
import lzma
import struct

from opendroidvm import cli, kernelscan

PAD = b"\0" * 200_000


def _arm32_head():
    h = bytearray(64); h[36:40] = (0x016F2818).to_bytes(4, "little"); return bytes(h)


def _arm64_head():
    h = bytearray(64); h[56:60] = b"ARMd"; return bytes(h)


def _kernel(head, payload, compress="gzip"):
    blob = payload + PAD
    if compress == "gzip":
        blob = gzip.compress(blob)
    elif compress == "xz":
        blob = lzma.compress(blob, format=lzma.FORMAT_XZ)
    return head + b"\0" * 200 + blob


GOOD64 = b"arm,pl011 virtio_mmio virtio_gpu virtio_input virtio_blk"


def test_phone_kernel_without_virt_support_will_not_boot():
    # typical Qualcomm 32-bit kernel: its own UART and SoC strings, no mach-virt
    msm = b"qcom,msm8960 qcom,apq8064 " * 10 + b"msm_serial"
    r = kernelscan.scan_bytes(_kernel(_arm32_head(), msm))
    assert (r.arch, r.verdict, r.reason, r.vendor) == ("arm32", "no", "no_virt", "Qualcomm")
    assert r.compression == "gzip"


def test_arm32_with_everything_may_boot():
    r = kernelscan.scan_bytes(_kernel(_arm32_head(), b"linux,dummy-virt " + GOOD64))
    assert r.verdict == "yes"


def test_arm64_without_gpu_is_serial_only():
    r = kernelscan.scan_bytes(_kernel(_arm64_head(), b"arm,pl011 virtio_mmio virtio_blk", "none"))
    assert (r.verdict, r.reason) == ("serial", "no_gpu")


def test_arm64_without_uart_or_virtio():
    assert kernelscan.scan_bytes(_kernel(_arm64_head(), b"qcom,sdm845 " * 9, "xz")).reason == "no_uart"
    r = kernelscan.scan_bytes(_kernel(_arm64_head(), b"arm,pl011", "gzip"))
    assert (r.verdict, r.reason) == ("no", "no_virtio") and r.compression == "gzip"


def test_xz_payload_is_read():
    r = kernelscan.scan_bytes(_kernel(_arm64_head(), GOOD64, "xz"))
    assert r.verdict == "yes" and r.compression == "xz"


def test_unreadable_lz4_gives_no_verdict():
    r = kernelscan.scan_bytes(b"\x02\x21\x4c\x18" + b"\x55" * 5000)
    assert (r.verdict, r.reason) == ("unknown", "unreadable")


def test_scan_file_reads_boot_image(tmp_path):
    page = 2048
    kernel = _kernel(_arm64_head(), GOOD64)
    h = bytearray(page); h[:8] = b"ANDROID!"
    struct.pack_into("<III", h, 8, len(kernel), 0, 0); struct.pack_into("<I", h, 36, page)
    pad = (-len(kernel)) % page
    img = tmp_path / "rec.img"; img.write_bytes(bytes(h) + kernel + b"\0" * pad)
    assert kernelscan.scan_file(str(img)).verdict == "yes"


def test_check_command_and_exit_codes(tmp_path, capsys):
    bad = tmp_path / "msm.img"
    bad.write_bytes(_kernel(_arm32_head(), b"qcom,apq8064 " * 9))
    ok = tmp_path / "ok.img"
    ok.write_bytes(_kernel(_arm64_head(), GOOD64))
    assert cli.main(["check", str(bad)]) == 2
    out = capsys.readouterr().out
    assert "will NOT boot" in out and "Qualcomm" in out and "[ ] QEMU 'virt' machine support" in out
    assert cli.main(["check", str(ok)]) == 0
    assert cli.main(["check", "nosuchdevice"]) == 1


def test_launch_asks_before_starting_a_kernel_that_cannot_boot(tmp_path, monkeypatch):
    img = tmp_path / "msm.img"; img.write_bytes(_kernel(_arm32_head(), b"qcom,apq8064 " * 9))
    ran = []
    monkeypatch.setattr(cli.subprocess, "call", lambda cmd: ran.append(cmd) or 0)
    monkeypatch.setattr(cli.qemu, "find_qemu", lambda a, e=None: "/usr/bin/q")
    monkeypatch.setattr(cli.sys.stdin, "isatty", lambda: True)
    answers = iter(["n", "y"])
    monkeypatch.setattr("builtins.input", lambda p="": next(answers))
    args = ["run", "s5", "--boot", str(img), "--adb-port", "0", "--monitor-port", "0"]
    assert cli.main(args) == 1 and not ran              # answered "no": not started
    assert cli.main(args) == 0 and len(ran) == 1        # answered "yes": started anyway
