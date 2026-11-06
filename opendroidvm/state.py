"""Remembers the ports of the VM that odvm started, so `odvm key/vm/screenshot` just work
even when odvm had to move a busy port."""
import json
import os
import time

from . import paths


def _file():
    return paths.cache_root() / "vm.json"


def write(device, monitor_port, adb_port, vnc):
    try:
        f = _file()
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps({"device": device, "monitor_port": monitor_port,
                                 "adb_port": adb_port, "vnc": vnc, "pid": os.getpid(),
                                 "started": int(time.time())}), encoding="utf-8")
    except OSError:
        pass


def read():
    try:
        return json.loads(_file().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def clear():
    try:
        _file().unlink()
    except OSError:
        pass
