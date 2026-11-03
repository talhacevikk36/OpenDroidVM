#include "profile.h"

#include <algorithm>
#include <fstream>
#include <stdexcept>

#include <nlohmann/json.hpp>

namespace fs = std::filesystem;
using json = nlohmann::json;

namespace odw {

DeviceProfile loadProfile(const fs::path& file) {
    std::ifstream in(file);
    if (!in) throw std::runtime_error("Profil acilamadi: " + file.string());
    json j = json::parse(in);

    DeviceProfile p;
    p.id = file.stem().string();
    p.name = j.value("name", p.id);
    p.soc = j.value("soc", "");
    p.arch = j.value("arch", "aarch64");
    p.cpu = j.value("cpu", p.arch == "arm" ? "cortex-a15" : "cortex-a57");
    p.machine = j.value("machine", "virt");
    p.ram_mb = j.value("ram_mb", 2048);
    p.cpu_cores = j.value("cpu_cores", 4);
    if (j.contains("screen")) {
        p.width = j["screen"].value("width", p.width);
        p.height = j["screen"].value("height", p.height);
        p.dpi = j["screen"].value("dpi", p.dpi);
    }
    p.cmdline = j.value("cmdline", "console=ttyAMA0 androidboot.hardware=ranchu");
    p.notes = j.value("notes", "");
    return p;
}

std::vector<DeviceProfile> loadAllProfiles(const fs::path& dir) {
    std::vector<DeviceProfile> all;
    if (!fs::exists(dir)) return all;
    for (const auto& e : fs::directory_iterator(dir)) {
        if (e.path().extension() == ".json") {
            try {
                all.push_back(loadProfile(e.path()));
            } catch (const std::exception&) {
                // bozuk profili atla
            }
        }
    }
    std::sort(all.begin(), all.end(),
              [](const DeviceProfile& a, const DeviceProfile& b) { return a.id < b.id; });
    return all;
}

const DeviceProfile* findProfile(const std::vector<DeviceProfile>& all, const std::string& id) {
    for (const auto& p : all)
        if (p.id == id) return &p;
    return nullptr;
}

}  // namespace odw
