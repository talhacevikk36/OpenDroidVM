# Changelog

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
