OpenDroidVM
Android cihaz profilleri ile QEMU uzerinde recovery (TWRP, OrangeFox vb.) ve ROM denemek icin arac. 50+ cihaz profili icerir.
Kurulum (pip)
pip install git+https://github.com/talhacevikk36/OpenDroidVM.git
odvm install-qemu      # QEMU'yu winget / apt / dnf / pacman / brew ile kurar
Kullanim
odvm list
odvm info s10
odvm run s10 --recovery twrp.img --mode fast
odvm run pixel --boot boot.img --rom system.img --mode accurate
odvm run pixel --recovery twrp.img --dry-run   # sadece QEMU komutunu yazdirir
Recovery ve ROM ayri verilir. Pakete hicbir recovery/ROM dahil degildir; --recovery, --boot, --rom, --userdata ile kendi dosyalarinizi verirsiniz.
Android boot/recovery imajlari (v0-v4) otomatik acilir: kernel ve ramdisk cikarilip QEMU'ya -kernel/-initrd olarak verilir.
--mode accurate: profilin CPU modeli, cekirdek sayisi ve RAM'i birebir uygulanir.
--mode fast: konak mimarisi ayniysa KVM/WHPX/HVF, degilse cok iplikli TCG (-cpu max).
--ram, --cores: profil degerlerini ezer. --adb-port (varsayilan 5555, 0 = kapali), --vnc N, --snapshot (diske yazmaz).
odvm list [ara] --arch --soc --min-ram --json: profil filtreleme. odvm extract img: kernel+ramdisk cikarir. odvm create-disk userdata.img 4096: bos disk. odvm doctor: QEMU/hizlandirma kontrolu.
Kendi profilini ~/.config/opendroidvm/profiles/ (Windows: %APPDATA%\opendroidvm\profiles) icine JSON olarak koy; ayni isimde yerlesik profili ezer.
Profiller
opendroidvm/profiles/*.json: ad, kod adi, SoC, mimari, QEMU CPU modeli, RAM, cekirdek, ekran, recovery bilgisi. Yeni cihaz icin yeni bir JSON yeterli.
Sinirlar (onemli)
QEMU Exynos/Snapdragon/Kirin gibi gercek SoC'leri taklit etmez; profiller yalnizca CPU modeli, RAM ve ekran gibi parametreleri uygular. Cihaza ozel recovery/ROM imajlari kendi surucu ve bootloader'ini bekler ve cogunlukla genel virt makinesinde acilmaz. Genel AOSP/GSI imajlari icin uygundur.
C++ surumu
cmake -S . -B build -A x64
cmake --build build --config Release
