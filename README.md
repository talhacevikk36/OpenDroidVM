**English** | [Türkçe](README.tr.md)

# OpenDroidVM

Try Android recoveries (TWRP, OrangeFox, ...) and ROMs on QEMU using device profiles. Ships with 51 device profiles. Profile browser: https://talhacevikk36.github.io/OpenDroidVM/

How it works under the hood: [docs/how-it-works.md](docs/how-it-works.md)

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

## Keys (volume, power, home...)

`odvm run` starts the VM with a QEMU monitor on `127.0.0.1:5556` (`--monitor-port`, 0 = off). `odvm key` sends keys through it; no adb needed:

`volup`, `voldown`, `mute`, `power`, `home`, `back`, `menu`, `wake`, `sleep`. `recents` and `camera` work through adb only: `odvm key recents --via adb`. `odvm key --list` shows all. Use `--hold 1000` for the power menu. `odvm panel` gives the same keys as buttons (needs `python3-tk` on Linux).

What a key does inside Android depends on the image's key layout (e.g. in a recovery, volume keys move the menu and power selects).

## Speed

`--mode fast` uses `cache=unsafe,aio=threads` for disks (risk: the disk can be corrupted if the VM is killed; pair it with `--snapshot` to be safe). Profile lookup no longer reads every JSON file. With TCG (no acceleration) the gain is small; the big speed-up comes from KVM/WHPX/HVF on a 64-bit host.

## Language

The CLI speaks English and Turkish: `odvm --lang tr list` or `ODVM_LANG=tr`. If unset, the system locale decides (Turkish locale → Turkish, otherwise English).

## Limits

QEMU does not emulate real SoCs (Exynos/Snapdragon/Kirin...). Profiles only apply parameters such as CPU model, RAM and screen. Device-specific recovery/ROM images expect their own drivers and bootloader and mostly will not boot on the generic `virt` machine. Generic AOSP/GSI images are the good fit.

## C++ version

```
cmake -S . -B build -A x64
cmake --build build --config Release
```
