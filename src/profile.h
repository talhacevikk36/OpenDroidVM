#pragma once
#include <filesystem>
#include <string>
#include <vector>

namespace odw {

struct DeviceProfile {
    std::string id;          // dosya adı / komut satırı kimliği
    std::string name;        // görünen ad
    std::string soc;         // bilgi amaçlı
    std::string arch;        // "aarch64" veya "arm"
    std::string cpu;         // QEMU -cpu değeri
    std::string machine = "virt";
    int ram_mb = 2048;
    int cpu_cores = 4;
    int width = 720;
    int height = 1280;
    int dpi = 320;
    std::string cmdline;     // çekirdek komut satırı
    std::string notes;
};

DeviceProfile loadProfile(const std::filesystem::path& file);
std::vector<DeviceProfile> loadAllProfiles(const std::filesystem::path& dir);
const DeviceProfile* findProfile(const std::vector<DeviceProfile>& all, const std::string& id);

}  // namespace odw
