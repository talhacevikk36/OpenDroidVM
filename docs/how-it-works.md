# How OpenDroidVM works

OpenDroidVM does not emulate a specific phone. It builds a QEMU command line from a small JSON description of a device, unpacks the Android image you give it, and starts QEMU.

## 1. Profiles
`opendroidvm/profiles/<id>.json` describes a device: name, codename, SoC, architecture (`aarch64` or `arm`), the closest QEMU CPU model (e.g. `cortex-a76`), RAM, cores and screen size. `odvm list/info` read them; `odvm new` adds your own to `~/.config/opendroidvm/profiles/`, which wins over built-ins. Ids are restricted to `[A-Za-z0-9._-]`, so `../x` cannot escape the folder.

## 2. Boot images
`bootimg.py` reads an Android boot/recovery image header (`ANDROID!`, versions 0-4), cuts out the kernel and ramdisk, gunzips the kernel if needed (arm64 `Image.gz`), and caches the result under `~/.cache/opendroidvm/<hash>/`. The kernel and ramdisk go to QEMU as `-kernel` and `-initrd`. A truncated or corrupt image gives a clear error instead of a silent empty kernel.

## 3. The QEMU command
`launcher.py` assembles `qemu-system-aarch64` (or `qemu-system-arm`) arguments:
- machine `virt`, CPU / cores / RAM from the profile;
- **accurate** mode keeps the profile CPU; **fast** mode uses `-cpu host` with KVM/WHPX/HVF on a matching 64-bit host, otherwise multi-threaded TCG with `-cpu max`, and `cache=unsafe` disks;
- ROM / userdata images become `virtio-blk` drives;
- virtio GPU, tablet, keyboard and network; adb is forwarded from host port 5555 to guest 5555;
- a QEMU monitor on `127.0.0.1:5556` for key presses.

If a port is already taken (another VM, a real emulator), a free one is picked and printed. With no window system (SSH, Termux), the screen switches to VNC automatically.

## 4. Keys
`odvm key volup` connects to the monitor socket and sends `sendkey volumeup`. QEMU's virtio keyboard turns that into a Linux input event (`KEY_VOLUMEUP`), which Android's key layout maps to the volume key. `--hold` sends a held key (long press). Keys QEMU cannot produce (`recents`, `camera`) go through `adb shell input keyevent`.

## 5. Recovery downloader
`recovery.py` reads the TWRP device page (`https://dl.twrp.me/<codename>/`), picks the newest `twrp-*.img` (or the one matching `--version`), and downloads it with the page URL as `Referer` (the site rejects requests without it). The file is streamed to `*.part`, rejected if the server returned an HTML page instead of an image, then renamed. `.img.tar` files are unpacked. The result and its origin URL go to `recovery/<id>/`.

## 6. QEMU installation
`odvm install-qemu` picks the package manager (winget, apt, dnf, pacman, brew, or `pkg` on Termux) and runs it. `odvm doctor` reports what was found and which acceleration is available.

## What it cannot do
QEMU has no Exynos/Snapdragon/Kirin hardware models. A device-specific kernel expects its own SoC drivers, so many of them will not boot on `virt`. Use generic AOSP/GSI images for the best chance.
