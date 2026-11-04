#!/data/data/com.termux/files/usr/bin/bash
# OpenDroidVM - Android (Termux) kurulumu
set -e
pkg update -y
pkg install -y python git qemu-system-aarch64-headless qemu-system-arm-headless
pip install --upgrade git+https://github.com/talhacevikk36/OpenDroidVM.git
echo
odvm doctor
echo
echo "Hazir. Ornek: odvm run pixel --recovery twrp.img --vnc 0"
echo "Sonra bir VNC istemcisiyle localhost:5900 adresine baglan."
