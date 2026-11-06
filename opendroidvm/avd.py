"""Android Emulator (AVD) support.

QEMU's generic machine cannot boot a phone's own recovery kernel, but Google's Android
Emulator boots real Android images. This module turns an odvm profile (screen, density,
RAM, cores) into an AVD so you get a working phone with that profile's specs.
Needs the Android SDK (cmdline-tools + emulator + a system image). Experimental.
"""
import os
import platform
import shutil
import subprocess
from pathlib import Path

DEFAULT_IMAGE = {"x86_64": "system-images;android-34;google_apis;x86_64",
                 "arm64-v8a": "system-images;android-34;google_apis;arm64-v8a"}


def sdk_root():
    for env in ("ANDROID_SDK_ROOT", "ANDROID_HOME"):
        v = os.environ.get(env)
        if v and Path(v).is_dir():
            return Path(v)
    home = Path.home()
    guess = {"Windows": Path(os.environ.get("LOCALAPPDATA", home)) / "Android" / "Sdk",
             "Darwin": home / "Library" / "Android" / "sdk"}.get(platform.system(), home / "Android" / "Sdk")
    return guess if guess.is_dir() else None


def _exe(name):
    return name + (".exe" if name == "emulator" and os.name == "nt" else
                   ".bat" if name in ("avdmanager", "sdkmanager") and os.name == "nt" else "")


def tool(name):
    root = sdk_root()
    cands = []
    if root:
        if name == "emulator":
            cands.append(root / "emulator" / _exe(name))
        else:
            cands.append(root / "cmdline-tools" / "latest" / "bin" / _exe(name))
            cands += sorted((root / "cmdline-tools").glob(f"*/bin/{_exe(name)}")) if (root / "cmdline-tools").is_dir() else []
    for c in cands:
        if c.is_file():
            return str(c)
    return shutil.which(name)


def host_abi():
    return "arm64-v8a" if platform.machine().lower() in ("arm64", "aarch64") else "x86_64"


def avd_home():
    if os.environ.get("ANDROID_AVD_HOME"):
        return Path(os.environ["ANDROID_AVD_HOME"])
    base = Path(os.environ.get("ANDROID_USER_HOME") or Path.home() / ".android")
    return base / "avd"


def avd_name(pid):
    return f"odvm_{pid}"


def config_updates(profile):
    return {"hw.lcd.width": profile.width, "hw.lcd.height": profile.height,
            "hw.lcd.density": profile.dpi, "hw.ramSize": profile.ram_mb,
            "hw.cpu.ncore": max(1, min(profile.cpu_cores, os.cpu_count() or 2)),
            "hw.device.name": profile.name, "hw.keyboard": "yes", "hw.gpu.enabled": "yes",
            "hw.gpu.mode": "auto", "showDeviceFrame": "no", "skin.dynamic": "yes",
            "disk.dataPartition.size": "6G"}


def patch_ini(text, updates):
    """Replace existing `key=value` lines, append the missing ones."""
    left = {k: str(v) for k, v in updates.items()}
    out = []
    for line in text.splitlines():
        key = line.split("=", 1)[0].strip()
        if "=" in line and key in left:
            out.append(f"{key}={left.pop(key)}")
        else:
            out.append(line)
    out += [f"{k}={v}" for k, v in left.items()]
    return "\n".join(out) + "\n"


def create(profile, image=None):
    """Create/refresh the AVD for a profile. Returns the config.ini path."""
    mgr = tool("avdmanager")
    if not mgr:
        raise RuntimeError("avdmanager not found (install Android SDK command-line tools)")
    name = avd_name(profile.id)
    image = image or DEFAULT_IMAGE[host_abi()]
    r = subprocess.run([mgr, "create", "avd", "--force", "-n", name, "-k", image],
                       input="no\n", text=True, capture_output=True)
    if r.returncode != 0:
        raise RuntimeError((r.stderr or r.stdout or "avdmanager failed").strip().splitlines()[-1])
    cfg = avd_home() / f"{name}.avd" / "config.ini"
    cfg.write_text(patch_ini(cfg.read_text(encoding="utf-8") if cfg.exists() else "",
                             config_updates(profile)), encoding="utf-8")
    return cfg


def run_cmd(profile, extra=()):
    emu = tool("emulator")
    if not emu:
        raise RuntimeError("emulator not found (install the Android Emulator via sdkmanager)")
    return [emu, "-avd", avd_name(profile.id), *extra]


def doctor():
    return {"sdk": str(sdk_root() or ""), "emulator": tool("emulator") or "",
            "avdmanager": tool("avdmanager") or "", "sdkmanager": tool("sdkmanager") or "",
            "image": DEFAULT_IMAGE[host_abi()]}
