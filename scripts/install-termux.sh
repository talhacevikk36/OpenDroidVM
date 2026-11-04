#!/data/data/com.termux/files/usr/bin/bash
# OpenDroidVM - Android (Termux) install
set -e
pkg update -y
pkg install -y python git qemu-system-aarch64-headless qemu-system-arm-headless
pip install --upgrade git+https://github.com/talhacevikk36/OpenDroidVM.git
echo
odvm doctor
echo
echo "Ready. Example: odvm run pixel --recovery twrp.img --vnc 0"
echo "Then connect a VNC client to localhost:5900."
