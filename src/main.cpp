#include <filesystem>
#include <iostream>
#include <string>
#include <vector>

#include "launcher.h"
#include "profile.h"

namespace fs = std::filesystem;
using namespace odw;

static void usage() {
    std::cout <<
R"(OpenDroidWm 0.1.0 - Android cihaz profili tabanli ROM/recovery deneme araci

Kullanim:
  opendroidwm list
  opendroidwm info <profil>
  opendroidwm run <profil> [--recovery img] [--boot img] [--system img]
                           [--userdata img] [--qemu yol] [--headless] [--dry-run]

Profiller 'profiles' klasorunden okunur (OPENDROIDWM_PROFILES ile degistirilebilir).
)";
}

static fs::path profilesDir(const char* argv0) {
    if (const char* env = std::getenv("OPENDROIDWM_PROFILES")) return env;
    fs::path exeDir = fs::absolute(argv0).parent_path();
    for (const fs::path& c : {exeDir / "profiles", fs::path("profiles")})
        if (fs::exists(c)) return c;
    return "profiles";
}

int main(int argc, char** argv) {
    if (argc < 2) {
        usage();
        return 1;
    }
    const std::string cmd = argv[1];
    const auto profiles = loadAllProfiles(profilesDir(argv[0]));

    if (cmd == "list") {
        if (profiles.empty()) std::cout << "Profil bulunamadi.\n";
        for (const auto& p : profiles)
            std::cout << p.id << "\t" << p.name << "\t[" << p.arch << ", " << p.ram_mb << " MB]\n";
        return 0;
    }

    if (argc < 3) {
        usage();
        return 1;
    }
    const DeviceProfile* p = findProfile(profiles, argv[2]);
    if (!p) {
        std::cerr << "Profil bulunamadi: " << argv[2] << "\n";
        return 2;
    }

    if (cmd == "info") {
        std::cout << "Ad:       " << p->name << "\nSoC:      " << p->soc
                  << "\nMimari:   " << p->arch << "\nCPU:      " << p->cpu << " x" << p->cpu_cores
                  << "\nRAM:      " << p->ram_mb << " MB\nEkran:    " << p->width << "x"
                  << p->height << " @" << p->dpi << " dpi\nNot:      " << p->notes << "\n";
        return 0;
    }

    if (cmd == "run") {
        LaunchOptions o;
        for (int i = 3; i < argc; ++i) {
            const std::string a = argv[i];
            auto next = [&]() -> std::string {
                if (i + 1 >= argc) {
                    std::cerr << a << " icin deger gerekli\n";
                    std::exit(1);
                }
                return argv[++i];
            };
            if (a == "--recovery") o.recovery = next();
            else if (a == "--boot") o.boot = next();
            else if (a == "--system") o.system = next();
            else if (a == "--userdata") o.userdata = next();
            else if (a == "--qemu") o.qemuPath = next();
            else if (a == "--headless") o.headless = true;
            else if (a == "--dry-run") o.dryRun = true;
            else {
                std::cerr << "Bilinmeyen secenek: " << a << "\n";
                return 1;
            }
        }
        const auto qemu = buildQemuCommand(*p, o);
        if (o.dryRun) {
            std::cout << joinCommand(qemu) << "\n";
            return 0;
        }
        return runCommand(qemu);
    }

    usage();
    return 1;
}
