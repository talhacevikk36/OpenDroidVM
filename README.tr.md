[English](README.md) | **Türkçe**

# OpenDroidVM

Android cihaz profilleriyle QEMU uzerinde recovery (TWRP, OrangeFox vb.) ve ROM denemek icin arac. 70 cihaz profili icerir. Profil arama sitesi: https://talhacevikk36.github.io/OpenDroidVM/

`odvm`, **O**pen**D**roid**VM**'in kisaltmasidir; uzun hali `opendroidvm` de calisir.

> **ALPHA.** Bir telefonun recovery'si/Android'i odvm altinda etkilesimli bir ekranla acilana kadar tum surumler alpha'dir (`0.9.x-alpha.N`); sonra 1.0.0. Bkz. [ROADMAP.md](ROADMAP.md).
>
> **Once oku (olculdu):** gercek telefonlarin resmi TWRP imajlari QEMU'da **acilmaz**. 20 tanesini indirip her kernel'in icine baktik (`odvm check`): 18'i acilamaz (`virt` makine destegi ya da PL011 seri suruculusu yok), 2'sinin (Pixel 2/3) sikistirmasi okunamadi. Telefonun kendi cipi icin derlenmisler. Calisanlar: `odvm selftest` (bilinen iyi ARM64 Linux), genel kernel'ler ve `odvm avd` ile Android Emulator. Ayrintilar asagida.

## Neler calisir, neler calismaz (olculdu)

| Su cihazin resmi TWRP'si | QEMU `virt` sonucu |
|---|---|
| Galaxy S4/S5/Note 4, Nexus 5 (32-bit) | acilmaz - kernel'de `virt` makine destegi yok |
| Galaxy S7/S8/S9/S10 (Exynos), Pixel, Nexus 5X/6P, OnePlus 3/5/6/7 Pro, Poco F1, Mi A2, Redmi Note 7 | acilmaz - PL011 seri suruculusu yok (sadece kendi cipinin UART'ini bilir) |
| Pixel 2, Pixel 3 | `odvm check` kernel sikistirmasini okuyamadi (Qualcomm kernel'i, ayni sonuc beklenir) |

Neden: QEMU'nun `virt` kartinda Snapdragon/Exynos donanimi yok ve telefon kernel'i sadece kendi telefonunun suruculerini icerir. Bu odvm'de bir hata degil, hicbir ayar duzeltmez. Herhangi bir imaj icin `odvm check <cihaz veya imaj>` kullan; `odvm list` olculen cihazlarda `<twrp:no-boot>` gosterir.

Gercekten acilanlar:
- `odvm selftest` Alpine Linux (ARM64) acar ve QEMU'nun, seri konsolun, cihazinin calistigini kanitlar (GitHub sunucularinda dogrulandi).
- `virt` icin derlenmis kernel'ler (dagitim kernel'leri, AOSP *Cuttlefish*/GKI) `--boot`/`--recovery` ile.
- **Android Emulator:** `odvm avd create s10` o profilin ekran, yogunluk, RAM ve cekirdegiyle bir AVD olusturur, `odvm avd run s10` gercek bir Android baslatir (Android SDK gerekir; deneysel, telefonda/Termux'ta yok).

## Diger komutlar

```
odvm check s10                 # bir imaj neden aciliyor/acilmiyor (kernel icerigine bakar)
odvm selftest                  # bilinen iyi bir Linux ac
odvm vm status|pause|resume|reset|stop      # calisan VM'i yonet (portlar otomatik bulunur)
odvm screenshot --out shot.png
odvm run s10 --log boot.txt    # seri konsolu dosyaya da kaydet
odvm run s10 --recovery x.img --export go.sh   # baslatma betigi yaz (.sh / .bat)
odvm clone s10 s10big --ram 12288 --name "Benim S10"
odvm config set mode fast      # lang, mode, qemu, adb_port, recovery_dir, update_check
odvm clean --recovery          # onbellegi (+ indirilen recovery'leri) sil
odvm completion bash|zsh|powershell
```

## Hizli baslangic (en kolayi)

```
odvm                      # adim adim: telefonu sec, TWRP otomatik indirilir, sonra baslar
odvm start s10 --yes      # tek komut: QEMU yoksa kurar, TWRP'yi indirir, telefonu baslatir
```

Windows: surumler sayfasindan `odvm-windows-x64.exe`'ye cift tikla ve sorulari cevapla. Ismi yanlis yazarsan oneri alirsin ("Bunu mu demek istedin: pixel3?").

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
odvm fetch-recovery --all                        # resmi TWRP imajlarini indir
odvm key volup                                   # calisan VM'e ses +
odvm key power --hold 1000                       # uzun bas: guc menusu
odvm panel                                       # tus paneli (tkinter)
```

- **Recovery ve ROM ayri verilir.** Pakete recovery/ROM dahil degildir: `--recovery`, `--boot`, `--rom`, `--userdata`.
- Android boot/recovery imajlari (v0-v4) otomatik acilir, kernel ve ramdisk QEMU'ya verilir (onbellege alinir).
- `--mode accurate`: profilin CPU modeli, cekirdek sayisi ve RAM'i birebir uygulanir.
- `--mode fast`: 64-bit ayni mimaride KVM/WHPX/HVF, degilse cok iplikli TCG (`-cpu max`).
- `--ram`, `--cores` profili ezer. `--adb-port` (varsayilan 5555, 0 = kapali), `--vnc N`, `--snapshot`.
- Kendi profillerin `~/.config/opendroidvm/profiles/` (Windows: `%APPDATA%\opendroidvm\profiles`) icinde durur ve ayni isimdeki yerlesik profili ezer.

## Recovery imajlari (TWRP)

Depoda hicbir imaj yoktur. `odvm fetch-recovery` istek uzerine **resmi TWRP** imajlarini twrp.me'den `recovery/` klasorune indirir (`recovery/<id>/twrp-....img` + `SOURCE.txt`). TWRP GPL-3.0 lisansli yazilimdir.

```
odvm fetch-recovery s10 pixel3          # belirli cihazlar
odvm fetch-recovery --all               # onerilen 20 cihaz
odvm fetch-recovery s7 --version 3.6.0  # belirli TWRP surumu
odvm run s10 --recovery auto            # recovery/s10/ icindeki en yeni imaj
```

Onerilen 20: pixel, pixel2, pixel3, nexus5, nexus5x, nexus6p, s4, s5, s7, s8, s9, s10, note4, oneplus3, oneplus5, oneplus6, oneplus7pro, pocof1, mia2, redminote7. Resmi TWRP sayfasi olmayan cihaz net bir hata verir, digerleri devam eder. Samsung `.img.tar` dosyalari otomatik acilir. Klasor git tarafindan yok sayilir (her imaj onlarca MB).

**fetch-recovery** GitHub Action'i ayni indirmeyi GitHub sunucularinda yapip zip olarak sunabilir (Actions sekmesi -> fetch-recovery -> Run workflow).

## Hazir calistirilabilir dosyalar (Python gerekmez)

Her surumde `odvm-windows-x64.exe`, `odvm-linux-x64` ve `odvm-macos` bulunur (**exe** workflow'u PyInstaller ile uretir, tek dosya, profiller dahil). QEMU yine gerekir: once `odvm install-qemu` calistir.

## Tuslar (ses, guc, home...)

`odvm run` VM'i `127.0.0.1:5556` uzerinde bir QEMU monitor ile baslatir (`--monitor-port`, 0 = kapali). `odvm key` bu monitor uzerinden tus gonderir, adb gerekmez:

`volup`, `voldown`, `mute`, `power`, `home`, `back`, `menu`, `wake`, `sleep`. `recents` ve `camera` yalnizca adb ile: `odvm key recents --via adb`. `odvm key --list` hepsini gosterir. Guc menusu icin `--hold 1000`. `odvm panel` ayni tuslari dugmelerle verir (Linux'ta `python3-tk` gerekir).

Tuslarin Android'de ne yaptigi imajin tus haritasina baglidir (ornegin recovery'de ses tuslari menu gezer, guc secer).

## Hiz

`--mode fast` diskler icin `cache=unsafe,aio=threads` kullanir (veri kaybi riski: VM aniden kapanirsa disk bozulabilir, `--snapshot` ile birlikte guvenli). Profil arama artik tum JSON'lari okumaz. TCG (hizlandirmasiz) calisan cihazlarda kazanc sinirlidir; en buyuk hiz farki 64-bit konakta KVM/WHPX/HVF ile gelir.

## Dil

Arayuz Ingilizce ve Turkce destekler: `odvm --lang tr list` ya da `ODVM_LANG=tr`. Ayarlanmazsa sistem diline bakilir (Turkce degilse Ingilizce).

## Guncelleme

`odvm` acilirken GitHub'da yeni surum var mi bakar (en fazla 12 saatte bir, sadece terminalde, internet yoksa sessiz) ve sorar: "Yeni surum var ... Simdi guncellensin mi? [E/h]". `.exe`/binary kendini degistirir, pip kurulumu kendini yukseltir. Elle: `odvm update` (`--check` sadece bakar). Kapatmak icin: `ODVM_NO_UPDATE_CHECK=1`.

## Sorun giderme: "Display output is not active" (VNC / Termux)

Bu yazi **misafir kernel'in henuz bir ekran suruculusu baslatmadigi** anlamina gelir; VNC'nin kendisi calisiyordur. Tipik nedenler:

1. **Kernel verilmedi** (`--recovery`/`--boot` yok): hicbir sey acilmaz. odvm artik bunu uyarir.
2. **Cihaz kernel'i (TWRP) verildi**: gercek SoC icin derlenmistir, QEMU'nun `virt` makinesi icin `virtio-gpu` suruculusu genelde yoktur; calissa bile ekran bos kalabilir. Fikrin ana siniri budur (Sinirlar bolumune bak).
3. **Yanlis mimari** (64-bit profile 32-bit kernel ya da tersi): odvm uyarir ve hangi tur profil sececegini soyler.

Acilis kaydi odvm'yi baslattigin terminale yazilir (seri konsol), boylece kernel'in hic acilip acilmadigini gorursun. QEMU'dan cikis: Ctrl+A sonra X.

## Sinirlar

QEMU Exynos/Snapdragon/Kirin gibi gercek SoC'leri taklit etmez; profiller yalnizca CPU modeli, RAM ve ekran gibi parametreleri uygular. Cihaza ozel recovery/ROM imajlari kendi surucu ve bootloader'ini bekler ve cogunlukla genel `virt` makinesinde acilmaz. Genel AOSP/GSI imajlari icin uygundur.

## C++ surumu

```
cmake -S . -B build -A x64
cmake --build build --config Release
```
