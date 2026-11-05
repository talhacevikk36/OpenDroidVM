"""Device profiles (opendroidvm/profiles/*.json)."""
import difflib
import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path

SAFE_ID = re.compile(r"^[A-Za-z0-9._-]+$")
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
    """Built-in + user profiles (the user profile wins on the same id)."""
    dirs = [Path(directory)] if directory else [PROFILE_DIR, user_dir()]
    found = {}
    for d in dirs:
        for f in sorted(d.glob("*.json")) if d.is_dir() else []:
            found[f.stem] = load_profile(f)
    return sorted(found.values(), key=lambda p: p.id)


def find(pid, directory=None):
    if not SAFE_ID.match(pid or "") or pid.startswith("."):
        return None           # blocks path tricks like ../x
    pid = pid.lower()
    dirs = [Path(directory)] if directory else [user_dir(), PROFILE_DIR]  # user first
    for d in dirs:                       # fast path: <id>.json directly
        f = d / f"{pid}.json"
        if f.is_file():
            return load_profile(f)
    for p in load_all(directory):        # slow path: match by codename
        if p.codename and p.codename.lower() == pid:
            return p
    return None


def suggest(pid, n=3):
    """Closest profile ids to a mistyped name (for 'did you mean')."""
    items = load_all()
    names = {}
    for p in items:
        for key in (p.id, p.codename, p.name):
            if key:
                names[key.lower()] = p.id
    hits = difflib.get_close_matches((pid or "").lower(), list(names), n=n * 3, cutoff=0.6)
    out = []
    for h in hits:
        if names[h] not in out:
            out.append(names[h])
    sub = [p.id for p in items if (pid or "").lower() in (p.id + p.codename + p.name).lower()]
    for i in sub:
        if i not in out:
            out.append(i)
    return out[:n]
