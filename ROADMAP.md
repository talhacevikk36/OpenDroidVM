# Roadmap: from alpha to 1.0.0

**All versions are alpha (`0.9.x-alpha.N`) until the main promise works. Then 1.0.0.**

## What "works" means (the 1.0.0 definition)
`odvm start <device>` (or the wizard) leads to a **visible, interactive screen** (VNC or a window) of a
recovery or Android for a phone profile, on **Windows/Linux and on Android (Termux)**, and a CI job proves it
(screenshot with real picture content, not QEMU's "Display output is not active" placeholder).

## Where we are (measured, see README)
- QEMU, serial console, VNC server, keys, ports, updates: **work** (`odvm selftest` passes in CI).
- Official TWRP images of real phones: **do not boot** on QEMU `virt` (18/20 measured, 2 unreadable). They contain
  drivers for the phone's own chip only. Nothing in odvm can change that.

## Steps
1. [x] Measure instead of guess (`odvm check`, compatibility table from real images)
2. [x] Prove the toolchain on a known-good guest (`odvm selftest`)
3. [x] Show a real picture on VNC with a GPU driver: `odvm linux` / `odvm selftest --display` (CI looks at the virtual screen: a real console with 21 text rows appears). **So the display chain works; a black screen means the guest kernel has no GPU driver.**
4. [ ] One phone profile that boots **something interactive**: candidates (each needs an image built for `virt`/virtio):
   - AOSP *Cuttlefish* / GSI with a virtio kernel (ARM64)
   - Android-x86 / generic x86_64 Android on PCs (QEMU + KVM/WHPX)
   - Android Emulator AVDs from profiles (`odvm avd`, PC only)
   - a recovery rebuilt for `virt` (own kernel config with `virtio` + PL011)
5. [ ] Same path on Termux (slow TCG, but visible)
6. [ ] CI verifies 4 and 5 -> **1.0.0**

Releases before 1.0.0 are tagged `v0.9.x-alpha.N`; older tags (`v0.2.0`-`v0.9.0`) were pre-alpha numbering and are marked as pre-releases.
