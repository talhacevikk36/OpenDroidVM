# Degisiklikler

## 0.5.0
- Donanim tuslari: `odvm key` (ses +/-, guc, home, back, menu...) ve `odvm panel`; monitor uzerinden, adb gerekmez
- Hizli mod: disk onbellegi (`cache=unsafe`), profil aramada hiz artisi

## 0.4.0
- Android (Termux) destegi: `scripts/install-termux.sh`, KVM olmadan TCG, ekran VNC
- Yeni komutlar: `odvm new`, `odvm validate`
- Hata duzeltmeleri: 32-bit konuk icin hatali donanim hizlandirma, bozuk boot imaji algilama, her calistirmada tekrar acilan gecici klasorler (artik onbellekte)
- GitHub Pages sitesi (profil arama), CI ve otomatik release

## 0.3.0
- `list` filtreleri, `doctor`, `extract`, `create-disk`, `--ram/--cores/--adb-port/--vnc/--snapshot`, kullanici profilleri

## 0.2.0
- pip paketi, 51 profil, `fast`/`accurate` mod, QEMU kurulumu, boot imaji acma
