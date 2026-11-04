"""Cihaz profilleri (opendroidvm/profiles/*.json)."""
import json
import os
from dataclasses import dataclass, field
from pathlib import Path

PROFILE_DIR = Path(__file__).parent / "profiles"


def user_dir():
    base = os.environ.get("APPDATA") or os.environ.get("XDG_CONFIG_HOME") \
        or str(Path.home() / ".config")
    return Path(base) / "opendroidvm" / "profiles"


@dataclass
class Profile:
    id: str
    name: str
    soc: str = ""
    arch: str = "aarch64"
    cpu: str = "cortex-a57"
    machine: str = "virt"
    ram_mb: int = 2048
    cpu_cores: int = 4
    width: int = 720
    height: int = 1280
    dpi: int = 320
    cmdline: str = "console=ttyAMA0 androidboot.hardware=ranchu"
    codename: str = ""
    recovery: dict = field(default_factory=dict)
    notes: str = ""


def load_profile(path):
    path = Path(path)
    j = json.loads(path.read_text(encoding="utf-8"))
    s = j.get("screen", {})
    arch = j.get("arch", "aarch64")
    return Profile(
        id=path.stem,
        name=j.get("name", path.stem),
        soc=j.get("soc", ""),
        arch=arch,
        cpu=j.get("cpu", "cortex-a15" if arch == "arm" else "cortex-a57"),
        machine=j.get("machine", "virt"),
        ram_mb=j.get("ram_mb", 2048),
        cpu_cores=j.get("cpu_cores", 4),
        width=s.get("width", 720),
        height=s.get("height", 1280),
        dpi=s.get("dpi", 320),
        cmdline=j.get("cmdline", Profile.cmdline),
        codename=j.get("codename", ""),
        recovery=j.get("recovery", {}),
        notes=j.get("notes", ""),
    )


def load_all(directory=None):
    """Yerlesik profiller + kullanici profilleri (ayni id ise kullanici kazanir)."""
    dirs = [Path(directory)] if directory else [PROFILE_DIR, user_dir()]
    found = {}
    for d in dirs:
        for f in sorted(d.glob("*.json")) if d.is_dir() else []:
            found[f.stem] = load_profile(f)
    return sorted(found.values(), key=lambda p: p.id)


def find(pid, directory=None):
    pid = pid.lower()
    dirs = [Path(directory)] if directory else [user_dir(), PROFILE_DIR]  # kullanici oncelikli
    for d in dirs:                       # hizli yol: <id>.json dogrudan
        f = d / f"{pid}.json"
        if f.is_file():
            return load_profile(f)
    for p in load_all(directory):        # yavas yol: kod adi ile ara
        if p.codename and p.codename.lower() == pid:
            return p
    return None
