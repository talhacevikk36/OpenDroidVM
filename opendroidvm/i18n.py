"""English / Turkish messages. Language: --lang, $ODVM_LANG, else system locale (tr -> Turkish)."""
import locale
import os

_lang = None

M = {
 "en": {
  "profile_not_found": "Profile not found: {x}",
  "file_not_found": "File not found: {x}",
  "n_profiles": "-- {n} profiles",
  "qemu_missing": "QEMU not found. Install it with: odvm install-qemu",
  "fetch_404": "no TWRP page for '{cn}' (not officially supported?)",
  "fetch_net": "network error: {e}",
  "fetch_html": "the server sent a web page instead of an image",
  "fetch_version": "no image matching version '{v}'",
  "fetch_ok": "OK   {id}: {path} ({mb} MB)",
  "fetch_fail": "FAIL {id}: {why}",
  "fetch_summary": "{ok}/{n} downloaded into {out}/",
  "fetch_none": "Give device ids or use --all (20 recommended devices).",
  "auto_missing": "No recovery for '{id}' in {out}/. Run: odvm fetch-recovery {id}",
  "h_fetch": "download official TWRP images into the recovery/ folder",
  "h_fetch_all": "download the 20 recommended devices", "h_fetch_out": "target folder",
  "bad_image": "Error: {x}",
  "not_boot": "Not an Android boot image (no ANDROID! magic)",
  "corrupt": "Corrupt or truncated image (kernel/ramdisk size does not fit the file)",
  "termux_vnc": "Note: on Termux the screen is served over VNC; connect a VNC client to localhost:{port}.",
  "nodisplay_vnc": "Note: no display found (no $DISPLAY/$WAYLAND_DISPLAY); using VNC, connect to localhost:{port}.",
  "port_moved": "Note: port {old} is busy, using {new} instead ({what}).",
  "port_adb": "adb",
  "port_monitor": "key monitor; use: odvm key --port {new}",
  "no_free_port": "No free port found near {x}.",
  "disk_exists": "File already exists (use --force to overwrite): {x}",
  "disk_created": "{path} created ({mb} MB, raw, sparse)",
  "created": "Created: {x}",
  "exists": "Already exists (use --force): {x}",
  "bad_id": "Invalid id: use only letters, digits, '.', '_' and '-'",
  "validated": "{n} profiles checked, {bad} invalid",
  "err_arch": "invalid arch: {x}",
  "err_ram": "invalid ram_mb/cpu_cores",
  "err_screen": "invalid screen values",
  "err_name": "name/soc is empty",
  "doctor_termux": "Env    : Android (Termux) - no KVM, TCG is used, screen over VNC",
  "doctor_cpu": "{n} logical cores",
  "doctor_accel": "  acceleration ({arch}): {x}",
  "doctor_none": "none (TCG is used)",
  "doctor_profiles": "Profiles: {n}; user folder: {d}",
  "doctor_nokvm": "Note: /dev/kvm is not accessible (no KVM, or your user is not in the 'kvm' group).",
  "doctor_ver": "(version unreadable)",
  "missing": "MISSING",
  "pm_missing": "No package manager found; install QEMU manually: https://www.qemu.org/download/",
  "will_run": "Running:",
  "key_sent": "sent: {x}",
  "key_fail": "Could not send: {e}\nIs the VM started with `odvm run`? (monitor port {port})",
  "key_unknown": "Unknown key: {x} (valid: {v})",
  "key_no_monitor": "'{x}' cannot be sent through the monitor; use --via adb",
  "adb_missing": "adb not found (install platform-tools)",
  "tk_missing": "tkinter is missing (Linux: sudo apt install python3-tk). Use `odvm key volup` from the terminal instead.",
  "panel_title": "OpenDroidVM keys",
  "panel_ready": "Ready. Hold a button for a long press.",
  "panel_sent": "{x} sent",
  "panel_err": "Error: {x}",
  "b_volup": "Vol +", "b_voldown": "Vol -", "b_power": "Power", "b_home": "Home",
  "b_back": "Back", "b_menu": "Menu", "b_mute": "Mute", "b_recents": "Recents",
  "h_list": "list / filter profiles", "h_run": "run a profile with QEMU",
  "h_extract": "extract kernel+ramdisk from a boot/recovery image",
  "h_disk": "create an empty userdata disk", "h_new": "create your own device profile",
  "h_validate": "validate profiles", "h_doctor": "check QEMU / acceleration",
  "h_key": "send a hardware key to a running VM (volume, power, home...)",
  "h_panel": "key panel (tkinter)", "h_install": "install QEMU",
  "h_lang": "language: en or tr",
  "h_rom": "ROM/system image (not bundled)", "h_hold": "ms; long press (1000 for the power menu)",
  "h_adbport": "0 = off", "h_vnc": "VNC display no (5900+N)", "h_snap": "do not write to disk",
  "h_monitor": "key/monitor port on 127.0.0.1, 0 = off",
  "h_ram": "RAM in MB, overrides the profile", "h_cores": "CPU cores, overrides the profile",
 },
 "tr": {
  "profile_not_found": "Profil bulunamadi: {x}",
  "file_not_found": "Dosya bulunamadi: {x}",
  "n_profiles": "-- {n} profil",
  "qemu_missing": "QEMU bulunamadi. Kurmak icin: odvm install-qemu",
  "fetch_404": "'{cn}' icin TWRP sayfasi yok (resmi destek olmayabilir)",
  "fetch_net": "ag hatasi: {e}",
  "fetch_html": "sunucu imaj yerine bir web sayfasi gonderdi",
  "fetch_version": "'{v}' surumune uyan imaj yok",
  "fetch_ok": "OK   {id}: {path} ({mb} MB)",
  "fetch_fail": "HATA {id}: {why}",
  "fetch_summary": "{ok}/{n} indirildi: {out}/",
  "fetch_none": "Cihaz id'si ver ya da --all kullan (onerilen 20 cihaz).",
  "auto_missing": "'{id}' icin {out}/ icinde recovery yok. Calistir: odvm fetch-recovery {id}",
  "h_fetch": "resmi TWRP imajlarini recovery/ klasorune indir",
  "h_fetch_all": "onerilen 20 cihazi indir", "h_fetch_out": "hedef klasor",
  "bad_image": "Hata: {x}",
  "not_boot": "Android boot imaji degil (ANDROID! imzasi yok)",
  "corrupt": "Bozuk ya da eksik imaj (kernel/ramdisk boyutu dosyaya sigmiyor)",
  "termux_vnc": "Not: Termux'ta ekran VNC ile acilir; bir VNC istemcisiyle localhost:{port}'a baglan.",
  "nodisplay_vnc": "Not: ekran bulunamadi ($DISPLAY/$WAYLAND_DISPLAY yok); VNC kullaniliyor, localhost:{port}'a baglan.",
  "port_moved": "Not: {old} portu dolu, onun yerine {new} kullaniliyor ({what}).",
  "port_adb": "adb",
  "port_monitor": "tus monitoru; kullan: odvm key --port {new}",
  "no_free_port": "{x} civarinda bos port bulunamadi.",
  "disk_exists": "Dosya zaten var (--force ile ustune yaz): {x}",
  "disk_created": "{path} olusturuldu ({mb} MB, raw, seyrek)",
  "created": "Olusturuldu: {x}",
  "exists": "Zaten var (--force): {x}",
  "bad_id": "Gecersiz id: yalniz harf, rakam, '.', '_' ve '-' kullan",
  "validated": "{n} profil kontrol edildi, {bad} hatali",
  "err_arch": "arch gecersiz: {x}",
  "err_ram": "ram_mb/cpu_cores gecersiz",
  "err_screen": "ekran degerleri gecersiz",
  "err_name": "name/soc bos",
  "doctor_termux": "Ortam  : Android (Termux) - KVM yok, TCG kullanilir, ekran VNC",
  "doctor_cpu": "{n} mantiksal cekirdek",
  "doctor_accel": "  hizlandirma ({arch}): {x}",
  "doctor_none": "yok (TCG kullanilir)",
  "doctor_profiles": "Profil : {n} adet; kullanici klasoru: {d}",
  "doctor_nokvm": "Not: /dev/kvm erisilebilir degil (KVM yok ya da kullanici 'kvm' grubunda degil).",
  "doctor_ver": "(surum okunamadi)",
  "missing": "YOK",
  "pm_missing": "Paket yoneticisi bulunamadi; QEMU'yu elle kurun: https://www.qemu.org/download/",
  "will_run": "Calistirilacak:",
  "key_sent": "gonderildi: {x}",
  "key_fail": "Gonderilemedi: {e}\nVM `odvm run` ile baslatildi mi? (monitor portu {port})",
  "key_unknown": "Bilinmeyen tus: {x} (gecerli: {v})",
  "key_no_monitor": "'{x}' tusu monitor ile gonderilemez; --via adb kullan",
  "adb_missing": "adb bulunamadi (platform-tools kurun)",
  "tk_missing": "tkinter yok (Linux: sudo apt install python3-tk). Terminalden `odvm key volup` kullanabilirsin.",
  "panel_title": "OpenDroidVM tuslar",
  "panel_ready": "Hazir. Uzun basmak icin dugmeyi basili tut.",
  "panel_sent": "{x} gonderildi",
  "panel_err": "Hata: {x}",
  "b_volup": "Ses +", "b_voldown": "Ses -", "b_power": "Guc", "b_home": "Ana ekran",
  "b_back": "Geri", "b_menu": "Menu", "b_mute": "Sessiz", "b_recents": "Son uyg.",
  "h_list": "profilleri listele/filtrele", "h_run": "profili QEMU ile calistir",
  "h_extract": "boot/recovery imajindan kernel+ramdisk cikar",
  "h_disk": "bos userdata diski olustur", "h_new": "kendi cihaz profilini olustur",
  "h_validate": "profilleri dogrula", "h_doctor": "QEMU/hizlandirma kontrolu",
  "h_key": "calisan VM'e donanim tusu gonder (ses, guc, home...)",
  "h_panel": "tus paneli (tkinter)", "h_install": "QEMU kur",
  "h_lang": "dil: en veya tr",
  "h_rom": "ROM/system imaji (pakete dahil degil)", "h_hold": "ms; uzun basma (guc menusu icin 1000)",
  "h_adbport": "0 = kapali", "h_vnc": "VNC ekran no (5900+N)", "h_snap": "diske yazma",
  "h_monitor": "tus/monitor portu (127.0.0.1), 0 = kapali",
  "h_ram": "RAM (MB), profili ezer", "h_cores": "cekirdek sayisi, profili ezer",
 },
}


def set_lang(lang):
    global _lang
    _lang = lang if lang in M else None


def lang():
    if _lang:
        return _lang
    env = (os.environ.get("ODVM_LANG") or "").lower()[:2]
    if env in M:
        return env
    try:
        loc = (locale.getlocale()[0] or os.environ.get("LANG", "") or "").lower()
    except ValueError:
        loc = ""
    return "tr" if loc.startswith("tr") else "en"


def t(key, **kw):
    s = M[lang()].get(key) or M["en"].get(key, key)
    return s.format(**kw) if kw else s
