#include "launcher.h"

#include <cstdlib>
#include <sstream>

#ifdef _WIN32
#include <windows.h>
#endif

namespace odw {

static std::string quote(const std::string& s) {
    if (s.find_first_of(" \t\"") == std::string::npos) return s;
    std::string r = "\"";
    for (char c : s) {
        if (c == '"') r += '\\';
        r += c;
    }
    return r + "\"";
}

std::string joinCommand(const std::vector<std::string>& cmd) {
    std::ostringstream os;
    for (size_t i = 0; i < cmd.size(); ++i) {
        if (i) os << ' ';
        os << quote(cmd[i]);
    }
    return os.str();
}

std::vector<std::string> buildQemuCommand(const DeviceProfile& p, const LaunchOptions& o) {
    const bool is64 = p.arch == "aarch64";
    std::string exe = o.qemuPath.empty()
                          ? (is64 ? "qemu-system-aarch64" : "qemu-system-arm")
                          : o.qemuPath;

    std::vector<std::string> c = {exe,
                                  "-machine", p.machine,
                                  "-cpu", p.cpu,
                                  "-smp", std::to_string(p.cpu_cores),
                                  "-m", std::to_string(p.ram_mb),
                                  "-name", p.name};

    // Recovery varsa dogrudan kernel/ramdisk olarak degil, boot imaji olarak verilir.
    // Cihaza ozel imajlar genel 'virt' makinesinde acilmayabilir (README'ye bakin).
    const std::string& kernelImg = !o.recovery.empty() ? o.recovery : o.boot;
    if (!kernelImg.empty()) {
        c.insert(c.end(), {"-kernel", kernelImg, "-append", p.cmdline});
    }
    if (!o.system.empty()) {
        c.insert(c.end(), {"-drive", "file=" + o.system + ",format=raw,if=none,id=system",
                           "-device", "virtio-blk-device,drive=system"});
    }
    if (!o.userdata.empty()) {
        c.insert(c.end(), {"-drive", "file=" + o.userdata + ",format=raw,if=none,id=userdata",
                           "-device", "virtio-blk-device,drive=userdata"});
    }

    c.insert(c.end(), {"-device", "virtio-gpu-pci,xres=" + std::to_string(p.width) +
                                      ",yres=" + std::to_string(p.height),
                       "-device", "virtio-tablet-pci",
                       "-device", "virtio-keyboard-pci"});
    if (o.headless) c.insert(c.end(), {"-display", "none", "-serial", "stdio"});
    return c;
}

int runCommand(const std::vector<std::string>& cmd) {
    const std::string line = joinCommand(cmd);
#ifdef _WIN32
    STARTUPINFOA si{};
    si.cb = sizeof(si);
    PROCESS_INFORMATION pi{};
    std::string mutableLine = line;
    if (!CreateProcessA(nullptr, mutableLine.data(), nullptr, nullptr, FALSE, 0, nullptr,
                        nullptr, &si, &pi))
        return -1;
    WaitForSingleObject(pi.hProcess, INFINITE);
    DWORD code = 0;
    GetExitCodeProcess(pi.hProcess, &code);
    CloseHandle(pi.hProcess);
    CloseHandle(pi.hThread);
    return static_cast<int>(code);
#else
    return std::system(line.c_str());
#endif
}

}  // namespace odw
