"""Per-OS folders (cache, data, config). Env overrides keep tests and portable installs easy."""
import os
import platform
import sys
from pathlib import Path


def _home():
    return Path.home()


def cache_root():
    if os.environ.get("XDG_CACHE_HOME"):
        base = Path(os.environ["XDG_CACHE_HOME"])
    elif platform.system() == "Windows":
        base = Path(os.environ.get("LOCALAPPDATA") or _home() / "AppData" / "Local")
    elif platform.system() == "Darwin":
        base = _home() / "Library" / "Caches"
    else:
        base = _home() / ".cache"
    return base / "opendroidvm"


def data_root():
    """Where downloaded recoveries live unless ./recovery exists (ODVM_HOME overrides)."""
    if os.environ.get("ODVM_HOME"):
        return Path(os.environ["ODVM_HOME"])
    if platform.system() == "Windows":
        return Path(os.environ.get("LOCALAPPDATA") or _home() / "AppData" / "Local") / "OpenDroidVM"
    if platform.system() == "Darwin":
        return _home() / "Library" / "Application Support" / "OpenDroidVM"
    base = Path(os.environ.get("XDG_DATA_HOME") or _home() / ".local" / "share")
    return base / "opendroidvm"


def config_root():
    base = os.environ.get("APPDATA") or os.environ.get("XDG_CONFIG_HOME") or str(_home() / ".config")
    return Path(base) / "opendroidvm"


def is_frozen():
    return bool(getattr(sys, "frozen", False))
