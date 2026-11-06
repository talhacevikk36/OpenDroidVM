# Changelog

## 0.9.1-alpha.1
- **Alpha versioning:** all releases are alpha until a phone image really boots (then 1.0.0, see ROADMAP.md). `odvm --version`, the wizard and the README say so; older tags are marked as pre-releases
- Updater understands alpha/beta/rc versions (`0.9.1a1 < 0.9.1`), reads the release *list* (GitHub's "latest" ignores pre-releases) and has a pre-release-aware atom-feed fallback; stable installs stay on stable unless `odvm config set channel alpha`
- Release workflow flags `*-alpha*`/`*-beta*`/`*-rc*` tags as pre-releases (this first alpha is a normal release on purpose, so existing installs find it)

## 0.9.0 - honest about phone images, many PC fixes, 11 new commands
**Finding:** 20 official TWRP images were downloaded and every kernel inspected: none can boot on QEMU `virt` (18 measured, 2 unreadable). `odvm list/start/wizard` now say so up front.
- New: `check` (looks inside a kernel: drivers, SoC, verdict), `selftest` (boots Alpine ARM64; verified in CI), `avd create/run/doctor` (Android Emulator with a profile's specs, experimental), `vm stop|reset|pause|resume|status`, `screenshot`, `run --log`, `run --export` (.sh/.bat), `clone`, `config`, `clean`, `completion`
- Fix: Samsung/old Qualcomm recovery images were rejected as "corrupt" (garbage in the header-version field) and could not be opened at all
- Fix (security): adb port forwarding listened on all network interfaces; now 127.0.0.1 only
- Fix: paths with commas broke `-drive`; Windows shows cmd.exe-quoted commands; RAM capped when the machine has less than the profile wants (QEMU "cannot allocate memory")
- Fix: cache/data folders follow each OS (LOCALAPPDATA, ~/Library, XDG); recoveries are no longer tied to the current folder; atomic extraction (two odvm runs cannot clash)
- `odvm key/vm/screenshot` find the running VM's ports automatically; LZ4 kernels (Pixel) are decoded; `odvm list | head` no longer prints a traceback

## 0.8.1
- Fix: update check no longer depends on the GitHub API (anonymous limit is 60/hour per IP, so shared networks got 403 and "offline"); falls back to the public release page

## 0.8.0
- **Auto-update:** `odvm` asks to update when a newer GitHub release exists (checked at most every 12 h, terminal only); the executable replaces itself (SHA-256 checked), pip installs upgrade via pip; `odvm update [--check]`; `ODVM_NO_UPDATE_CHECK=1` disables
- **Fix (Termux/VNC):** the guest's serial console was not connected in VNC mode, so you could not see any boot output; it now prints in the terminal (Ctrl+A X quits)
- Warns when no kernel is given, or when the kernel architecture does not match the profile; explains "Display output is not active"
- C++ project named OpenDroidVM (was a typo, OpenDroidWm)

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
