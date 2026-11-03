#pragma once
#include <string>
#include <vector>

#include "profile.h"

namespace odw {

struct LaunchOptions {
    std::string recovery;   // recovery.img (TWRP, OrangeFox ...)
    std::string boot;       // boot.img
    std::string system;     // system.img (ROM)
    std::string userdata;   // userdata.img (opsiyonel)
    std::string qemuPath;   // qemu-system-xxx yolu (bos ise PATH)
    bool dryRun = false;
    bool headless = false;
};

// Profil ve secenekten QEMU arguman listesi uretir (ilk eleman calistirilabilir dosya).
std::vector<std::string> buildQemuCommand(const DeviceProfile& p, const LaunchOptions& o);

// Komutu calistirir, cikis kodunu dondurur.
int runCommand(const std::vector<std::string>& cmd);

std::string joinCommand(const std::vector<std::string>& cmd);

}  // namespace odw
