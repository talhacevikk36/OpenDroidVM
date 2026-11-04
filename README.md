# OpenDroidVM

Android cihaz profilleriyle QEMU uzerinde recovery (TWRP, OrangeFox vb.) ve ROM denemek icin arac. 51 cihaz profili icerir. Profil arama sitesi: https://talhacevikk36.github.io/OpenDroidVM/

## Kurulum

```
pip install git+https://github.com/talhacevikk36/OpenDroidVM.git
odvm install-qemu      # winget / apt / dnf / pacman / brew / pkg ile QEMU kurar
odvm doctor            # kurulum ve hizlandirma kontrolu
```

### Android (Termux)

Telefonda Termux ile calisir (F-Droid surumu onerilir):

```
curl -fsSL https://raw.githubusercontent.com/talhacevikk36/OpenDroidVM/main/scripts/install-termux.sh | bash
odvm run pixel --recovery twrp.img
```

Android'de KVM yoktur, bu yuzden yavas TCG kullanilir. Ekran VNC ile acilir: bir VNC istemcisiyle `localhost:5900`'e baglan.

## Kullanim

```
odvm list [ara] --arch arm --soc snapdragon --min-ram 4096 --json
odvm info s10
odvm run s10 --recovery twrp.img --mode fast
odvm run pixel --boot boot.img --rom system.img --userdata ud.img
odvm run pixel --recovery twrp.img --dry-run     # sadece QEMU komutunu yazdirir
odvm extract twrp.img --out cikti                # kernel + ramdisk
odvm create-disk userdata.img 4096               # bos disk
odvm new mycihaz --soc "X SoC" --ram 4096        # kendi profilin
odvm validate                                    # profilleri dogrula
```

- **Recovery ve ROM ayri verilir.** Pakete recovery/ROM dahil degildir: `--recovery`, `--boot`, `--rom`, `--userdata`.
- Android boot/recovery imajlari (v0-v4) otomatik acilir, kernel ve ramdisk QEMU'ya verilir (onbellege alinir).
- `--mode accurate`: profilin CPU modeli, cekirdek sayisi ve RAM'i birebir uygulanir.
- `--mode fast`: 64-bit ayni mimaride KVM/WHPX/HVF, degilse cok iplikli TCG (`-cpu max`).
- `--ram`, `--cores` profili ezer. `--adb-port` (varsayilan 5555, 0 = kapali), `--vnc N`, `--snapshot`.
- Kendi profillerin `~/.config/opendroidvm/profiles/` (Windows: `%APPDATA%\opendroidvm\profiles`) icinde durur ve ayni isimdeki yerlesik profili ezer.

## Sinirlar

QEMU Exynos/Snapdragon/Kirin gibi gercek SoC'leri taklit etmez; profiller yalnizca CPU modeli, RAM ve ekran gibi parametreleri uygular. Cihaza ozel recovery/ROM imajlari kendi surucu ve bootloader'ini bekler ve cogunlukla genel `virt` makinesinde acilmaz. Genel AOSP/GSI imajlari icin uygundur.

## C++ surumu

```
cmake -S . -B build -A x64
cmake --build build --config Release
```
