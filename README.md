**English** | [Türkçe](README.tr.md)

# OpenDroidVM

Try Android recoveries (TWRP, OrangeFox, ...) and ROMs on QEMU using device profiles. Ships with 70 device profiles. Profile browser: https://talhacevikk36.github.io/OpenDroidVM/

How it works under the hood: [docs/how-it-works.md](docs/how-it-works.md)

`odvm` is short for **O**pen**D**roid**VM**; the long name `opendroidvm` works too.

## Quick start (easiest)

```
odvm                      # guided: pick your phone, TWRP is downloaded for you, then it starts
odvm start s10 --yes      # one command: installs QEMU if missing, downloads TWRP, starts the phone
```

Windows: just double-click `odvm-windows-x64.exe` from the releases page and follow the questions. Mistyped a name? You get suggestions ("Did you mean: pixel3?").

## Install

```
pip install git+https://github.com/talhacevikk36/OpenDroidVM.git
odvm install-qemu      # installs QEMU via winget / apt / dnf / pacman / brew / pkg
odvm doctor            # checks QEMU and acceleration
```

### Android (Termux)

Runs on a phone through Termux (F-Droid build recommended):

```
curl -fsSL https://raw.githubusercontent.com/talhacevikk36/OpenDroidVM/main/scripts/install-termux.sh | bash
odvm run pixel --recovery twrp.img
```

Phones have no KVM, so the slow TCG emulation is used. The screen is served over VNC: connect a VNC client to `localhost:5900`.

## Usage

```
odvm list [query] --arch arm --soc snapdragon --min-ram 4096 --json
odvm info s10
odvm run s10 --recovery twrp.img --mode fast
odvm run pixel --boot boot.img --rom system.img --userdata ud.img
odvm run pixel --recovery twrp.img --dry-run     # only prints the QEMU command
odvm extract twrp.img --out out                  # kernel + ramdisk
odvm create-disk userdata.img 4096               # empty disk
odvm new mydevice --soc "X SoC" --ram 4096       # your own profile
odvm validate                                    # validate profiles
odvm fetch-recovery --all                        # download official TWRP images
odvm key volup                                   # volume up on the running VM
odvm key power --hold 1000                       # long press: power menu
odvm panel                                       # key panel (tkinter)
```

- **Recovery and ROM are supplied separately.** Nothing is bundled: use `--recovery`, `--boot`, `--rom`, `--userdata`.
- Android boot/recovery images (v0-v4) are unpacked automatically; the kernel and ramdisk are passed to QEMU (and cached).
- `--mode accurate`: the profile's CPU model, core count and RAM are applied as-is.
- `--mode fast`: KVM/WHPX/HVF on a matching 64-bit host, otherwise multi-threaded TCG (`-cpu max`).
- `--ram`, `--cores` override the profile. `--adb-port` (default 5555, 0 = off), `--vnc N`, `--snapshot`.
- Your own profiles live in `~/.config/opendroidvm/profiles/` (Windows: `%APPDATA%\opendroidvm\profiles`) and override built-ins with the same id.

## Recovery images (TWRP)

Nothing is bundled in the repository. `odvm fetch-recovery` downloads **official TWRP** images from twrp.me on request into a `recovery/` folder (`recovery/<id>/twrp-....img` + `SOURCE.txt`). TWRP is GPL-3.0 software.

```
odvm fetch-recovery s10 pixel3          # specific devices
odvm fetch-recovery --all               # the 20 recommended devices
odvm fetch-recovery s7 --version 3.6.0  # a specific TWRP version
odvm run s10 --recovery auto            # newest image from recovery/s10/
```

Recommended 20: pixel, pixel2, pixel3, nexus5, nexus5x, nexus6p, s4, s5, s7, s8, s9, s10, note4, oneplus3, oneplus5, oneplus6, oneplus7pro, pocof1, mia2, redminote7. A device without an official TWRP page reports a clear error and the rest continue. Samsung `.img.tar` files are unpacked automatically. The folder is git-ignored (each image is tens of MB).

The **fetch-recovery** GitHub Action can also download them on GitHub's servers and offer a zip (Actions tab → fetch-recovery → Run workflow).

## Ready-made executables (no Python needed)

Each release contains `odvm-windows-x64.exe`, `odvm-linux-x64` and `odvm-macos` (built by the **exe** workflow with PyInstaller, one file, profiles included). QEMU is still required: run `odvm install-qemu` first.

## Keys (volume, power, home...)

`odvm run` starts the VM with a QEMU monitor on `127.0.0.1:5556` (`--monitor-port`, 0 = off). `odvm key` sends keys through it; no adb needed:

`volup`, `voldown`, `mute`, `power`, `home`, `back`, `menu`, `wake`, `sleep`. `recents` and `camera` work through adb only: `odvm key recents --via adb`. `odvm key --list` shows all. Use `--hold 1000` for the power menu. `odvm panel` gives the same keys as buttons (needs `python3-tk` on Linux).

What a key does inside Android depends on the image's key layout (e.g. in a recovery, volume keys move the menu and power selects).

## Speed

`--mode fast` uses `cache=unsafe,aio=threads` for disks (risk: the disk can be corrupted if the VM is killed; pair it with `--snapshot` to be safe). Profile lookup no longer reads every JSON file. With TCG (no acceleration) the gain is small; the big speed-up comes from KVM/WHPX/HVF on a 64-bit host.

## Language

The CLI speaks English and Turkish: `odvm --lang tr list` or `ODVM_LANG=tr`. If unset, the system locale decides (Turkish locale → Turkish, otherwise English).

## Updates

`odvm` checks GitHub for a new release when you start it (at most every 12 hours, only in a terminal, silent when offline) and asks: "A new version is available ... Update now? [Y/n]". The `.exe`/binary replaces itself, the pip install upgrades itself. Manual: `odvm update` (`--check` only looks). Turn it off: `ODVM_NO_UPDATE_CHECK=1`.

## Troubleshooting: "Display output is not active" (VNC / Termux)

That message means the **guest kernel has not started a display driver yet**; VNC itself works. Typical reasons:

1. **No kernel was given** (no `--recovery`/`--boot`): nothing boots. odvm now warns about this.
2. **A device kernel (TWRP's) was given**: it is built for the real SoC and usually has no `virtio-gpu` driver for QEMU's `virt` machine, so the screen can stay blank even though it runs. This is the main limit of the whole idea (see Limits).
3. **Wrong architecture** (32-bit kernel on a 64-bit profile or the reverse): odvm warns and tells you which kind of profile to pick.

The boot log goes to the terminal you started odvm in (serial console), so you can see whether the kernel boots at all. Quit QEMU with Ctrl+A then X.

## Limits

QEMU does not emulate real SoCs (Exynos/Snapdragon/Kirin...). Profiles only apply parameters such as CPU model, RAM and screen. Device-specific recovery/ROM images expect their own drivers and bootloader and mostly will not boot on the generic `virt` machine. Generic AOSP/GSI images are the good fit.

## C++ version

```
cmake -S . -B build -A x64
cmake --build build --config Release
```
