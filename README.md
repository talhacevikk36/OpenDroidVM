# OpenDroidWm

Android cihaz profilleri ile QEMU üzerinde ROM ve recovery (TWRP, OrangeFox vb.) denemek için Windows komut satırı aracı.

## Kullanım

```
opendroidwm list
opendroidwm info note8
opendroidwm run note8 --recovery twrp.img --dry-run
opendroidwm run pixel --boot boot.img --system system.img
```

QEMU ayrı kurulmalıdır (`qemu-system-aarch64` / `qemu-system-arm` PATH'te olmalı veya `--qemu` ile verilmeli). OpenDroidWm QEMU'yu ayrı bir süreç olarak çalıştırır, kaynak kodunu içermez.

## Profiller

`profiles/*.json` dosyaları: ad, SoC, mimari, QEMU CPU modeli, RAM, çekirdek sayısı, ekran. Yeni cihaz eklemek için yeni bir JSON dosyası yeterli.

## Sınırlar (önemli)

QEMU `virt` makinesi, Exynos/Snapdragon/Kirin gibi gerçek SoC'leri taklit etmez. Profiller CPU, RAM ve ekran gibi parametreleri uygular, ancak cihaza özel (ör. Note 8 için derlenmiş) recovery/ROM imajları kendi sürücülerini ve bootloader'ını bekler ve çoğunlukla genel sanal makinede açılmaz. Genel AOSP/GSI imajları ve cihazdan bağımsız davranış için uygundur.

## Derleme

```
cmake -S . -B build -A x64
cmake --build build --config Release
```

GitHub Actions: `.github/workflows/build.yml`
