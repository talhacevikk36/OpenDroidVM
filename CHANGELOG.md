# Changelog

## 0.7.5 - easier to use
- Plain `odvm` (or double-click the .exe) starts a guided wizard: pick the phone, download TWRP, choose speed, start
- `odvm start <device> --yes`: one command does everything (QEMU install, TWRP download, launch)
- "Did you mean ...?" suggestions for mistyped device names
- Download progress bar; asks to install QEMU when it is missing
- TWRP lookup tries alternate codenames (Pixel -> sailfish, Mi A2 -> jasmine_sprout, Note 4 -> trltexx)
- `fetch-recovery` Action reports every device in one summary (GitHub cut annotations to 10) and writes REPORT.txt
- CI: macOS runs one Python version (macOS runners were queued for 15+ minutes); `exe` workflow can attach to an existing release by tag

## 0.7.0
- `odvm fetch-recovery`: downloads official TWRP images into `recovery/` (20 recommended devices with `--all`); `odvm run --recovery auto`
- 19 new device profiles (70 total): Pixel 3a/4/4 XL/6a, Note 9/10, S20 FE, S21, A71, M31, OnePlus 9/Nord, Redmi Note 8 Pro, Poco F3, Mi 11, Xperia 1, Nothing Phone (1), Fairphone 3/4
- GitHub Actions: `exe` (Windows/Linux/macOS single-file executables attached to releases), `fetch-recovery` (manual)
- Fix: boot image with page size 0 crashed with ZeroDivisionError; now reported as corrupt

## 0.6.0
- English interface and docs (Turkish kept: `--lang tr`, `README.tr.md`); `docs/how-it-works.md`
- Fix: two VMs / a real emulator on the same host ports (adb 5555, monitor 5556) now get free ports automatically
- Fix: no window system (SSH, containers) no longer crashes QEMU; falls back to VNC
- Fix: `odvm new ../x` and similar ids could write or read outside the profile folder
- Pages site in English

## 0.5.0
- Hardware keys: `odvm key` (volume +/-, power, home, back, menu...) and `odvm panel`; via the QEMU monitor, no adb needed
- Fast mode: disk cache (`cache=unsafe`), faster profile lookup

## 0.4.0
- Android (Termux) support: `scripts/install-termux.sh`, TCG without KVM, screen over VNC
- New commands: `odvm new`, `odvm validate`
- Fixes: wrong hardware acceleration for 32-bit guests, corrupt boot image detection, temp folders re-created on every run (now cached)
- GitHub Pages site (profile search), CI and release workflow

## 0.3.0
- `list` filters, `doctor`, `extract`, `create-disk`, `--ram/--cores/--adb-port/--vnc/--snapshot`, user profiles

## 0.2.0
- pip package, 51 profiles, `fast`/`accurate` modes, QEMU installer, boot image unpacking
